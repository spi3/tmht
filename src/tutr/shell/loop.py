"""PTY shell loop implementation."""

import fcntl
import json
import os
import select
import shutil
import signal
import struct
import sys
import termios
import tty
from types import FrameType

from tutr.config import TutrConfig

from tutr.shell.constants import MARKER_RE, OUTPUT_BUFFER_SIZE
from tutr.shell.detection import _build_shell_launch_config
from tutr.shell.shell import _ask_tutor, _prompt_auto_run, _should_ask_tutor, load_shell_config


def _ask_tutor_with_cancel(
    command: str, output: str, config: TutrConfig, stdin_fd: int
) -> tuple[bytes, str | None]:
    """Run tutor query in a child process so Esc/Ctrl-C can cancel it."""
    read_fd, write_fd = os.pipe()
    pid = os.fork()
    if pid == 0:
        os.close(read_fd)
        suggestion, suggested_command = _ask_tutor(command, output, config)
        payload = json.dumps(
            {
                "suggestion": suggestion.decode(errors="replace"),
                "suggested_command": suggested_command,
            }
        ).encode()
        try:
            os.write(write_fd, payload)
        finally:
            os.close(write_fd)
        os._exit(0)

    os.close(write_fd)
    payload = b""
    canceled = False
    try:
        while True:
            try:
                rfds, _, _ = select.select([stdin_fd, read_fd], [], [], 0.1)
            except OSError:
                break

            if stdin_fd in rfds:
                try:
                    choice = os.read(stdin_fd, 1)
                except OSError:
                    choice = b""
                if choice in {b"\x03", b"\x1b"}:
                    canceled = True
                    break

            if read_fd in rfds:
                try:
                    chunk = os.read(read_fd, 4096)
                except OSError:
                    break
                if not chunk:
                    break
                payload += chunk
    finally:
        os.close(read_fd)
        if canceled:
            try:
                os.kill(pid, signal.SIGTERM)
            except OSError:
                pass
        try:
            os.waitpid(pid, 0)
        except OSError:
            pass

    if canceled:
        return b"\r\ntutr canceled.\r\n", None

    try:
        data = json.loads(payload.decode())
        suggestion = data["suggestion"].encode()
        suggested_command = data["suggested_command"]
        return suggestion, suggested_command
    except (json.JSONDecodeError, KeyError, UnicodeDecodeError):
        return b"\r\ntutr error: failed to parse tutor response\r\n", None


def _winsize(fd: int) -> tuple[int, int, int, int]:
    """Return (rows, cols, xpixel, ypixel) for the given tty fd."""
    return struct.unpack("HHHH", fcntl.ioctl(fd, termios.TIOCGWINSZ, b"\x00" * 8))


def _set_winsize(fd: int, rows: int, cols: int, xp: int = 0, yp: int = 0) -> None:
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, xp, yp))


def shell_loop() -> int:
    """Run the PTY-based interactive shell loop."""
    if not sys.stdin.isatty():
        print("Error: stdin must be a terminal", file=sys.stderr)
        return 1
    if not hasattr(os, "fork"):
        print("Error: interactive shell mode requires a POSIX environment", file=sys.stderr)
        return 1

    config = load_shell_config()

    try:
        launch = _build_shell_launch_config()
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    master_fd, slave_fd = os.openpty()

    # Match the slave PTY size to the real terminal.
    rows, cols, xp, yp = _winsize(sys.stdin.fileno())
    _set_winsize(slave_fd, rows, cols, xp, yp)

    pid = os.fork()
    if pid == 0:
        # Child process: exec detected shell attached to the slave PTY.
        os.close(master_fd)
        os.setsid()
        fcntl.ioctl(slave_fd, termios.TIOCSCTTY, 0)
        os.dup2(slave_fd, 0)
        os.dup2(slave_fd, 1)
        os.dup2(slave_fd, 2)
        if slave_fd > 2:
            os.close(slave_fd)
        os.execvpe(launch.executable, launch.argv, launch.env)
        os._exit(1)

    # Parent process: shuttle bytes between real terminal and PTY.
    os.close(slave_fd)

    # Forward window-resize signals to the child.
    def _on_winch(_signum: int, _frame: FrameType | None) -> None:
        try:
            r, c, xp, yp = _winsize(sys.stdin.fileno())
            _set_winsize(master_fd, r, c, xp, yp)
            os.kill(pid, signal.SIGWINCH)
        except OSError:
            pass

    signal.signal(signal.SIGWINCH, _on_winch)

    # Put the real terminal into raw mode so keystrokes pass through directly.
    old_attrs = termios.tcgetattr(sys.stdin.fileno())
    tty.setraw(sys.stdin.fileno())

    recent_output = b""
    stdin_fd = sys.stdin.fileno()
    stdout_fd = sys.stdout.fileno()

    try:
        while True:
            try:
                rfds, _, _ = select.select([stdin_fd, master_fd], [], [])
            except (OSError, ValueError):
                break

            # Stdin -> PTY master (user keystrokes)
            if stdin_fd in rfds:
                try:
                    data = os.read(stdin_fd, 1024)
                except OSError:
                    break
                if not data:
                    break
                os.write(master_fd, data)

            # PTY master -> stdout (shell output)
            if master_fd in rfds:
                try:
                    data = os.read(master_fd, 4096)
                except OSError:
                    break
                if not data:
                    break

                # Scan for exit-code markers before displaying.
                for match in MARKER_RE.finditer(data):
                    exit_code = int(match.group(1))
                    command = match.group(2).decode(errors="replace").strip()

                    if _should_ask_tutor(exit_code, command):
                        ctx = recent_output.decode(errors="replace")[-2048:]
                        suggestion, suggested_command = _ask_tutor_with_cancel(
                            command, ctx, config, stdin_fd
                        )
                        os.write(stdout_fd, suggestion)
                        if suggested_command:
                            _prompt_auto_run(
                                stdin_fd=stdin_fd,
                                stdout_fd=stdout_fd,
                                master_fd=master_fd,
                                command=suggested_command,
                            )

                    # Reset the buffer after each prompt (successful or not).
                    recent_output = b""

                # Strip markers so the user never sees them.
                clean = MARKER_RE.sub(b"", data)
                if clean:
                    os.write(stdout_fd, clean)

                # Keep a rolling window of recent output for error context.
                recent_output = (recent_output + clean)[-OUTPUT_BUFFER_SIZE:]
    finally:
        termios.tcsetattr(sys.stdin.fileno(), termios.TCSAFLUSH, old_attrs)
        for cleanup_path in launch.cleanup_paths:
            try:
                if os.path.isdir(cleanup_path):
                    shutil.rmtree(cleanup_path)
                else:
                    os.unlink(cleanup_path)
            except OSError:
                pass

    _, status = os.waitpid(pid, 0)
    return os.waitstatus_to_exitcode(status)
