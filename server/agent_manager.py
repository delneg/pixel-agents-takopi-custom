"""Agent lifecycle management — uses takopi ClaudeRunner."""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Awaitable

import anyio

from takopi.runners.claude import ClaudeRunner
from takopi.model import (
    ActionEvent,
    CompletedEvent,
    ResumeToken,
    StartedEvent,
)
from takopi.utils.paths import set_run_base_dir, reset_run_base_dir

from .event_mapper import map_event, needs_permission_timer, cancels_permission_timer
from .timer_manager import TimerManager
from .constants import TOOL_DONE_DELAY_S, EXEMPT_TOOLS

logger = logging.getLogger(__name__)

Broadcast = Callable[[dict[str, Any]], Awaitable[None]]

# 6 character palettes (indices 0-5)
NUM_PALETTES = 6


@dataclass
class AgentSession:
    id: int
    resume_token: ResumeToken | None = None
    active_tools: dict[str, str] = field(default_factory=dict)  # tool_id -> status
    is_running: bool = False
    palette: int = 0
    hue_shift: int = 0
    seat_id: str | None = None


class AgentManager:
    """Manages agent sessions and their Claude subprocess runners."""

    def __init__(self, broadcast: Broadcast, cwd: Path) -> None:
        self.agents: dict[int, AgentSession] = {}
        self._next_id = 1
        self._broadcast = broadcast
        self._cwd = cwd
        self._timers = TimerManager(broadcast)
        self._tg: anyio.abc.TaskGroup | None = None

    def set_task_group(self, tg: anyio.abc.TaskGroup) -> None:
        """Set the shared task group for running agent tasks."""
        self._tg = tg

    def _pick_diverse_palette(self) -> tuple[int, int]:
        """Pick a palette that's least used among current agents."""
        counts = [0] * NUM_PALETTES
        for agent in self.agents.values():
            counts[agent.palette] += 1

        min_count = min(counts)
        candidates = [i for i, c in enumerate(counts) if c == min_count]
        palette = random.choice(candidates)

        # Beyond first 6 agents, add a hue shift for visual distinction
        hue_shift = 0
        if min_count > 0:
            hue_shift = random.randint(1, 6) * 45  # 45-315 degrees
        return palette, hue_shift

    async def create_agent(self) -> int:
        """Create a new agent and broadcast its creation."""
        agent_id = self._next_id
        self._next_id += 1

        palette, hue_shift = self._pick_diverse_palette()
        session = AgentSession(id=agent_id, palette=palette, hue_shift=hue_shift)
        self.agents[agent_id] = session

        await self._broadcast({
            "type": "agentCreated",
            "id": agent_id,
            "palette": palette,
            "hueShift": hue_shift,
        })

        logger.info("Created agent %d (palette=%d, hueShift=%d)", agent_id, palette, hue_shift)
        return agent_id

    async def remove_agent(self, agent_id: int) -> None:
        """Remove an agent and broadcast its closure."""
        session = self.agents.pop(agent_id, None)
        if session is None:
            return

        self._timers.cancel_permission_timer(agent_id)

        await self._broadcast({
            "type": "agentClosed",
            "id": agent_id,
        })
        logger.info("Removed agent %d", agent_id)

    async def send_prompt(self, agent_id: int, prompt: str) -> None:
        """Send a prompt to an agent, running the Claude subprocess."""
        session = self.agents.get(agent_id)
        if session is None:
            logger.warning("send_prompt for unknown agent %d", agent_id)
            return
        if session.is_running:
            logger.warning("Agent %d is already running", agent_id)
            return

        session.is_running = True
        session.active_tools.clear()

        # Clear previous waiting state
        await self._broadcast({
            "type": "agentStatus",
            "id": agent_id,
            "status": "active",
        })

        if self._tg is None:
            logger.error("No task group set — cannot run agent")
            return

        self._tg.start_soon(self._run_agent, agent_id, prompt)

    async def _run_agent(self, agent_id: int, prompt: str) -> None:
        """Run a single Claude interaction for the agent."""
        session = self.agents.get(agent_id)
        if session is None:
            return

        runner = ClaudeRunner(dangerously_skip_permissions=True)
        token = set_run_base_dir(self._cwd)

        try:
            async for event in runner.run(prompt, session.resume_token):
                # Update resume token from started event
                if isinstance(event, StartedEvent):
                    session.resume_token = event.resume

                # Cancel permission timer on any data
                if cancels_permission_timer(event):
                    self._timers.cancel_permission_timer(agent_id)

                # Map event to pixel-agents messages
                messages = map_event(event, agent_id)

                # Track active tools
                if isinstance(event, ActionEvent):
                    if event.phase == "started" and not event.action.detail.get("parent_tool_use_id"):
                        session.active_tools[event.action.id] = event.action.title
                    elif event.phase == "completed" and event.action.id in session.active_tools:
                        del session.active_tools[event.action.id]

                # Start permission timer for non-exempt tools
                if needs_permission_timer(event) and self._tg is not None:
                    await self._timers.start_permission_timer(agent_id, self._tg)

                # Apply tool-done delay to prevent flicker
                if isinstance(event, ActionEvent) and event.phase == "completed":
                    if not event.action.detail.get("parent_tool_use_id"):
                        await anyio.sleep(TOOL_DONE_DELAY_S)

                # Broadcast messages
                for msg in messages:
                    await self._broadcast(msg)

                # Mark completed
                if isinstance(event, CompletedEvent):
                    session.is_running = False
                    session.active_tools.clear()

        except Exception:
            logger.exception("Error running agent %d", agent_id)
            session.is_running = False
            session.active_tools.clear()
            # Notify waiting state on error
            await self._broadcast({
                "type": "agentToolsClear",
                "id": agent_id,
            })
            await self._broadcast({
                "type": "agentStatus",
                "id": agent_id,
                "status": "waiting",
            })
        finally:
            reset_run_base_dir(token)

    def get_existing_agents_message(self) -> dict[str, Any]:
        """Build the existingAgents message for a newly connected client."""
        agent_ids = sorted(self.agents.keys())
        meta: dict[int, dict[str, Any]] = {}
        for agent in self.agents.values():
            meta[agent.id] = {
                "palette": agent.palette,
                "hueShift": agent.hue_shift,
                "seatId": agent.seat_id,
            }
        return {
            "type": "existingAgents",
            "agents": agent_ids,
            "agentMeta": meta,
        }
