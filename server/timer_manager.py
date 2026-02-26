"""Async permission timers — replaces timerManager.ts."""

from __future__ import annotations

import logging
from typing import Any, Callable, Awaitable, TYPE_CHECKING

import anyio

from .constants import PERMISSION_TIMER_DELAY_S, EXEMPT_TOOLS

if TYPE_CHECKING:
    from .agent_manager import AgentSession

logger = logging.getLogger(__name__)

Broadcast = Callable[[dict[str, Any]], Awaitable[None]]


class TimerManager:
    """Manages permission timers for all agents, running in a shared task group.

    When the timer fires, it checks both parent-level and sub-agent-level tools
    for non-exempt ones. Emits ``agentToolPermission`` for the parent and
    ``subagentToolPermission`` for each stuck sub-agent Task.
    """

    def __init__(self, broadcast: Broadcast) -> None:
        self._broadcast = broadcast
        self._scopes: dict[int, anyio.CancelScope] = {}

    async def start_permission_timer(
        self,
        agent_id: int,
        tg: anyio.abc.TaskGroup,
        session: AgentSession,
    ) -> None:
        """Start a permission timer in the given task group."""
        self.cancel_permission_timer(agent_id)
        scope = anyio.CancelScope()
        self._scopes[agent_id] = scope

        async def _run() -> None:
            with scope:
                await anyio.sleep(PERMISSION_TIMER_DELAY_S)
                if scope.cancel_called:
                    return

                # Check parent-level tools for non-exempt
                has_non_exempt = False
                for tool_id, tool_name in session.active_tool_names.items():
                    if tool_name not in EXEMPT_TOOLS:
                        has_non_exempt = True
                        break

                # Check sub-agent tools for non-exempt
                stuck_parent_tool_ids: list[str] = []
                for parent_tool_id, sub_names in session.active_subagent_tool_names.items():
                    for tool_name in sub_names.values():
                        if tool_name not in EXEMPT_TOOLS:
                            stuck_parent_tool_ids.append(parent_tool_id)
                            has_non_exempt = True
                            break

                if has_non_exempt:
                    session.permission_sent = True
                    logger.info("Permission timer fired for agent %d", agent_id)
                    await self._broadcast({
                        "type": "agentToolPermission",
                        "id": agent_id,
                    })
                    # Notify stuck sub-agents
                    for parent_tool_id in stuck_parent_tool_ids:
                        await self._broadcast({
                            "type": "subagentToolPermission",
                            "id": agent_id,
                            "parentToolId": parent_tool_id,
                        })

        tg.start_soon(_run)

    def cancel_permission_timer(self, agent_id: int) -> None:
        scope = self._scopes.pop(agent_id, None)
        if scope is not None:
            scope.cancel()

    def cancel_all(self) -> None:
        for scope in self._scopes.values():
            scope.cancel()
        self._scopes.clear()
