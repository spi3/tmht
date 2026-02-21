"""PoC: PTY-based shell wrapper that intercepts errors and asks tutr for help.

Usage:
    uv run python -m tutr.shell

Spawns a real interactive shell inside a PTY. All I/O passes through
transparently — interactive programs (vim, top, etc.) work normally.

A PROMPT_COMMAND hook embeds an invisible OSC marker in the output stream
after each command. The parent process parses these markers to detect
non-zero exit codes and automatically queries tutr with the failed command
plus recent terminal output as context.
"""

import fcntl
import os
import re
import select
import signal
import struct
import sys
import tempfile
import termios
import tty

from tutr.config import load_config, needs_setup
from tutr.setup import run_setup
from tutr.tutr import run

BOLD = "\033[1m"
RED = "\033[31m"
RESET = "\033[0m"

# Invisible OSC escape sequence used as a marker in the PTY output stream.
# Format: \033]7770;<exit_code>;<command>\007
# Terminals ignore unknown OSC sequences, so the user never sees these.
MARKER_RE = re.compile(rb"\033\]7770;(\d+);([^\007]*)\007")

# Rolling buffer size for recent terminal output (used as LLM context).
OUTPUT_BUFFER_SIZE = 4096


def _should_ask_tutor(exit_code: int, command: str) -> bool:
    """Return whether a prompt marker should trigger an LLM suggestion."""
    # Ctrl-C maps to exit code 130 in bash. Treat that as an intentional
    # interruption rather than a command failure that needs assistance.
    if exit_code == 130:
        return False
    return exit_code != 0 and bool(command.strip())


def _winsize(fd: int) -> tuple[int, int, int, int]:
    """Return (rows, cols, xpixel, ypixel) for the given tty fd."""
    return struct.unpack("HHHH", fcntl.ioctl(fd, termios.TIOCGWINSZ, b"\x00" * 8))


def _set_winsize(fd: int, rows: int, cols: int, xp: int = 0, yp: int = 0) -> None:
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, xp, yp))


def _ask_tutor(cmd: str, output: str, config: dict) -> tuple[bytes, str | None]:
    """Query tutr with a failed command and return display text and command."""
    query = f"fix this command: {cmd}"
    if output:
        query += f"\n\nTerminal output:\n{output}"
    try:
        result = run(query.split(), config)
        msg = f"\r\n{BOLD}tutr suggests:{RESET}\r\n  {result.command}\r\n".encode()
        return msg, result.command
    except Exception as e:
        return f"\r\n{RED}tutr error: {e}{RESET}\r\n".encode(), None


def _is_auto_run_accepted(choice: bytes) -> bool:
    """Return whether a one-byte prompt response means "yes"."""
    return choice in {b"y", b"Y"}


def _prompt_auto_run(stdin_fd: int, stdout_fd: int, master_fd: int, command: str) -> None:
    """Prompt for yes/no and optionally execute the suggested command."""
    prompt = "Run suggested command? [y/N] (Esc rejects): "
    os.write(stdout_fd, prompt.encode())
    while True:
        try:
            choice = os.read(stdin_fd, 1)
        except OSError:
            os.write(stdout_fd, b"\r\n")
            return
        if not choice:
            os.write(stdout_fd, b"\r\n")
            return
        if _is_auto_run_accepted(choice):
            os.write(stdout_fd, b"y\r\n")
            os.write(master_fd, command.encode() + b"\n")
            return
        if choice in {b"n", b"N", b"\x03", b"\x1b", b"\r", b"\n"}:
            os.write(stdout_fd, b"n\r\n")
            return


def _write_rcfile() -> str:
    """Write a temporary bashrc that sets up the PROMPT_COMMAND hook."""
    rc = tempfile.NamedTemporaryFile(
        mode="w", prefix="tutr_", suffix=".bashrc", delete=False
    )
    rc.write(
        # Source the user's normal bashrc so the shell feels familiar.
        '[ -f ~/.bashrc ] && source ~/.bashrc\n'
        # PROMPT_COMMAND runs after every command. It emits an OSC marker
        # containing the exit code and the command that was just run.
        "PROMPT_COMMAND='__e=$?; "
        'printf "\\033]7770;%d;%s\\007" "$__e" '
        '"$(history 1 | sed \"s/^[ ]*[0-9]*[ ]*//\")"\'\n'
    )
    rc.close()
    return rc.name


def shell_loop() -> int:
    """Run the PTY-based interactive shell loop."""
    if not sys.stdin.isatty():
        print("Error: stdin must be a terminal", file=sys.stderr)
        return 1

    if needs_setup():
        config = run_setup()
    else:
        config = load_config()

    rcfile = _write_rcfile()
    master_fd, slave_fd = os.openpty()

    # Match the slave PTY size to the real terminal.
    rows, cols, xp, yp = _winsize(sys.stdin.fileno())
    _set_winsize(slave_fd, rows, cols, xp, yp)

    pid = os.fork()
    if pid == 0:
        # --- Child process: exec bash attached to the slave PTY ---
        os.close(master_fd)
        os.setsid()
        fcntl.ioctl(slave_fd, termios.TIOCSCTTY, 0)
        os.dup2(slave_fd, 0)
        os.dup2(slave_fd, 1)
        os.dup2(slave_fd, 2)
        if slave_fd > 2:
            os.close(slave_fd)
        os.execvp("bash", ["bash", "--rcfile", rcfile, "-i"])
        os._exit(1)

    # --- Parent process: shuttle bytes between real terminal and PTY ---
    os.close(slave_fd)

    # Forward window-resize signals to the child.
    def _on_winch(_signum, _frame):
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
                        suggestion, suggested_command = _ask_tutor(command, ctx, config)
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
        try:
            os.unlink(rcfile)
        except OSError:
            pass

    _, status = os.waitpid(pid, 0)
    return os.waitstatus_to_exitcode(status)


def entrypoint() -> None:
    raise SystemExit(shell_loop())
