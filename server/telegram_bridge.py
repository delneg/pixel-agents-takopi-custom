"""Telegram bot bridge — relays agent events and accepts commands."""

from __future__ import annotations

import logging
from typing import Any

from takopi.telegram.client_api import HttpBotClient
from takopi.telegram.client import TelegramClient
from takopi.telegram.parsing import poll_incoming
from takopi.telegram.types import TelegramIncomingMessage, TelegramCallbackQuery

from .constants import (
    TELEGRAM_MAX_MESSAGE_LENGTH,
    TELEGRAM_EMOJI_CREATED,
    TELEGRAM_EMOJI_CLOSED,
    TELEGRAM_EMOJI_ANSWER,
    TELEGRAM_EMOJI_PERMISSION,
    TELEGRAM_EMOJI_ACTIVE,
    TELEGRAM_EMOJI_WAITING,
    TELEGRAM_EMOJI_TOOL,
    TELEGRAM_EMOJI_TOOL_DONE,
)

if False:  # TYPE_CHECKING
    from .agent_manager import AgentManager

logger = logging.getLogger(__name__)

HELP_TEXT = (
    "/create — Create a new agent\n"
    "/close [id] — Close agent (selected if no id)\n"
    "/agents — List active agents\n"
    "/select <id> — Select agent for prompts\n"
    "/help — Show this help"
)

BOT_COMMANDS = [
    {"command": "create", "description": "Create a new agent"},
    {"command": "close", "description": "Close agent (selected if no id)"},
    {"command": "agents", "description": "List active agents"},
    {"command": "select", "description": "Select agent for prompts"},
    {"command": "help", "description": "Show help"},
]


class TelegramBridge:
    """Bridges Telegram chat with the shared AgentManager."""

    def __init__(
        self,
        token: str,
        chat_id: int,
        agent_manager: AgentManager,
        *,
        verbose: bool = True,
    ) -> None:
        self._chat_id = chat_id
        self._agent_manager = agent_manager
        self._verbose = verbose
        self._http_client = HttpBotClient(token)
        self._tg_client = TelegramClient(client=self._http_client)
        # Per-sender selected agent: sender_id -> agent_id
        self._selected: dict[int, int] = {}

    async def run(self) -> None:
        """Poll for incoming messages forever (run in a task group)."""
        # Register bot commands for autocomplete
        await self._http_client.set_my_commands(BOT_COMMANDS)
        logger.info(
            "Telegram bridge started (chat_id=%d, verbose=%s)",
            self._chat_id,
            self._verbose,
        )

        async for update in poll_incoming(
            bot=self._http_client, chat_id=self._chat_id
        ):
            try:
                if isinstance(update, TelegramIncomingMessage):
                    await self._handle_message(update)
                elif isinstance(update, TelegramCallbackQuery):
                    await self._tg_client.answer_callback_query(
                        update.callback_query_id
                    )
            except Exception:
                logger.exception("Error handling Telegram update")

    async def on_broadcast(self, msg: dict[str, Any]) -> None:
        """Called by broadcast() for every event — format and send to Telegram."""
        text = self._format_broadcast(msg)
        if text is None:
            return
        try:
            await self._tg_client.send_message(
                self._chat_id,
                text[:TELEGRAM_MAX_MESSAGE_LENGTH],
            )
        except Exception:
            logger.exception("Failed to send Telegram message")

    async def close(self) -> None:
        """Clean shutdown."""
        await self._tg_client.close()

    # -- Private helpers --

    async def _handle_message(self, msg: TelegramIncomingMessage) -> None:
        """Route an incoming Telegram message to the right handler."""
        text = msg.text.strip()
        sender_id = msg.sender_id or 0

        if text.startswith("/"):
            await self._handle_command(text, sender_id)
        else:
            await self._handle_prompt(text, sender_id)

    async def _handle_command(self, text: str, sender_id: int) -> None:
        """Parse and execute a bot command."""
        # Strip @botname suffix (e.g. /help@MyBot)
        parts = text.split()
        cmd = parts[0].split("@")[0].lower()
        args = parts[1:]

        if cmd in ("/start", "/help"):
            await self._send(HELP_TEXT)

        elif cmd == "/create":
            agent_id = await self._agent_manager.create_agent()
            self._selected[sender_id] = agent_id
            await self._send(f"Created agent #{agent_id} (auto-selected)")

        elif cmd == "/close":
            if args:
                try:
                    agent_id = int(args[0])
                except ValueError:
                    await self._send("Usage: /close [id]")
                    return
            else:
                agent_id = self._selected.get(sender_id)  # type: ignore[assignment]
                if agent_id is None:
                    await self._send("No agent selected. Use /select <id> first.")
                    return

            if agent_id not in self._agent_manager.agents:
                await self._send(f"Agent #{agent_id} not found.")
                return

            await self._agent_manager.remove_agent(agent_id)
            # Clear selection if it was the closed agent
            if self._selected.get(sender_id) == agent_id:
                del self._selected[sender_id]
            await self._send(f"Closed agent #{agent_id}")

        elif cmd == "/agents":
            agents = self._agent_manager.agents
            if not agents:
                await self._send("No active agents.")
                return
            lines: list[str] = []
            for a in agents.values():
                status = "running" if a.is_running else "idle"
                selected_mark = ""
                if self._selected.get(sender_id) == a.id:
                    selected_mark = " [selected]"
                lines.append(f"#{a.id} — {status}{selected_mark}")
            await self._send("Active agents:\n" + "\n".join(lines))

        elif cmd == "/select":
            if not args:
                await self._send("Usage: /select <id>")
                return
            try:
                agent_id = int(args[0])
            except ValueError:
                await self._send("Usage: /select <id>")
                return
            if agent_id not in self._agent_manager.agents:
                await self._send(f"Agent #{agent_id} not found.")
                return
            self._selected[sender_id] = agent_id
            await self._send(f"Selected agent #{agent_id}")

        else:
            await self._send(f"Unknown command: {cmd}\n\n{HELP_TEXT}")

    async def _handle_prompt(self, text: str, sender_id: int) -> None:
        """Send a plain text message as a prompt to the selected agent."""
        if not text:
            return

        agent_id = self._selected.get(sender_id)
        if agent_id is None:
            await self._send(
                "No agent selected. Use /create to create one or /select <id>."
            )
            return

        if agent_id not in self._agent_manager.agents:
            await self._send(
                f"Agent #{agent_id} no longer exists. Use /create or /select <id>."
            )
            del self._selected[sender_id]
            return

        session = self._agent_manager.agents[agent_id]
        if session.is_running:
            await self._send(f"Agent #{agent_id} is busy. Wait for it to finish.")
            return

        await self._agent_manager.send_prompt(agent_id, text)
        await self._send(f"Sent to agent #{agent_id}")

    def _format_broadcast(self, msg: dict[str, Any]) -> str | None:
        """Format a broadcast message for Telegram. Returns None to skip."""
        msg_type = msg.get("type")
        agent_id = msg.get("id")

        # Always sent (key events)
        if msg_type == "agentCreated":
            return f"{TELEGRAM_EMOJI_CREATED} Agent #{agent_id} created"

        if msg_type == "agentClosed":
            return f"{TELEGRAM_EMOJI_CLOSED} Agent #{agent_id} closed"

        if msg_type == "agentAnswer":
            text = msg.get("text", "")
            return f"{TELEGRAM_EMOJI_ANSWER} Agent #{agent_id}:\n{text}"

        if msg_type == "agentToolPermission":
            return f"{TELEGRAM_EMOJI_PERMISSION} Agent #{agent_id} needs permission"

        if msg_type == "subagentToolPermission":
            return f"{TELEGRAM_EMOJI_PERMISSION} Agent #{agent_id} (sub-agent) needs permission"

        # Verbose only
        if not self._verbose:
            return None

        if msg_type == "agentStatus":
            status = msg.get("status")
            if status == "active":
                return f"{TELEGRAM_EMOJI_ACTIVE} Agent #{agent_id} active"
            if status == "waiting":
                return f"{TELEGRAM_EMOJI_WAITING} Agent #{agent_id} waiting"
            return None

        if msg_type == "agentToolStart":
            status = msg.get("status", "")
            return f"{TELEGRAM_EMOJI_TOOL} Agent #{agent_id}: {status}"

        if msg_type == "agentToolDone":
            return f"{TELEGRAM_EMOJI_TOOL_DONE} Agent #{agent_id}: tool done"

        if msg_type == "subagentToolStart":
            status = msg.get("status", "")
            return f"{TELEGRAM_EMOJI_TOOL} Agent #{agent_id} (sub): {status}"

        if msg_type == "subagentToolDone":
            return f"{TELEGRAM_EMOJI_TOOL_DONE} Agent #{agent_id} (sub): tool done"

        # Skip everything else (agentToolsClear, layoutLoaded, etc.)
        return None

    async def _send(self, text: str) -> None:
        """Send a text message to the configured chat."""
        await self._tg_client.send_message(
            self._chat_id,
            text[:TELEGRAM_MAX_MESSAGE_LENGTH],
        )
