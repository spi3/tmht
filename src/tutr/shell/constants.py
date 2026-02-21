"""Shared constants for shell integration."""

import re

BOLD = "\033[1m"
RED = "\033[31m"
RESET = "\033[0m"

# Invisible OSC escape sequence used as a marker in the PTY output stream.
# Format: \033]7770;<exit_code>;<command>\007
# Terminals ignore unknown OSC sequences, so the user never sees these.
MARKER_RE = re.compile(rb"\033\]7770;(\d+);([^\007]*)\007")

# Rolling buffer size for recent terminal output (used as LLM context).
OUTPUT_BUFFER_SIZE = 4096
