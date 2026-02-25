"""Timing and display constants — ported from src/constants.ts."""

# Timing (seconds)
TOOL_DONE_DELAY_S = 0.3
PERMISSION_TIMER_DELAY_S = 7.0
TEXT_IDLE_DELAY_S = 5.0
LAYOUT_FILE_POLL_INTERVAL_S = 2.0

# Display truncation
BASH_COMMAND_DISPLAY_MAX_LENGTH = 30
TASK_DESCRIPTION_DISPLAY_MAX_LENGTH = 40

# Layout file
LAYOUT_FILE_DIR = ".pixel-agents"
LAYOUT_FILE_NAME = "layout.json"

# Asset parsing (for server-side furniture PNG loading)
PNG_ALPHA_THRESHOLD = 128

# Tools exempt from permission timer
EXEMPT_TOOLS = frozenset({"Task", "AskUserQuestion"})
