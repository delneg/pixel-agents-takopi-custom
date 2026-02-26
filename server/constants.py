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

# Telegram
TELEGRAM_MAX_MESSAGE_LENGTH = 4096
TELEGRAM_EMOJI_CREATED = "\U0001f7e2"   # 🟢
TELEGRAM_EMOJI_CLOSED = "\U0001f534"    # 🔴
TELEGRAM_EMOJI_ANSWER = "\U0001f4ac"    # 💬
TELEGRAM_EMOJI_PERMISSION = "\U0001f6a8"  # 🚨
TELEGRAM_EMOJI_ACTIVE = "\u26a1"        # ⚡
TELEGRAM_EMOJI_WAITING = "\u23f3"       # ⏳
TELEGRAM_EMOJI_TOOL = "\U0001f527"      # 🔧
TELEGRAM_EMOJI_TOOL_DONE = "\u2705"     # ✅
