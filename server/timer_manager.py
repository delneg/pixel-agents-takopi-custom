"""Async permission and waiting timers — replaces timerManager.ts."""

from __future__ import annotations

import logging
from typing import Any, Callable, Awaitable

import anyio

from .constants import PERMISSION_TIMER_DELAY_S

logger = logging.getLogger(__name__)

Broadcast = Callable[[dict[str, Any]], Awaitable[None]]


class PermissionTimer:
    """Manages per-agent permission detection timers.

    When a non-exempt tool starts, we start a timer. If PERMISSION_TIMER_DELAY_S
    elapses without the tool completing or new data arriving, we broadcast a
    permission bubble message.
    """

    def __init__(self, broadcast: Broadcast) -> None:
        self._broadcast = broadcast
        # agent_id -> cancel scope
        self._scopes: dict[int, anyio.CancelScope] = {}

    async def start(self, agent_id: int, tool_id: str) -> None:
        """Start a permission timer for the given agent/tool."""
        self.cancel(agent_id)
        scope = anyio.CancelScope()
        self._scopes[agent_id] = scope

        async def _timer() -> None:
            with scope:
                await anyio.sleep(PERMISSION_TIMER_DELAY_S)
                if not scope.cancel_called:
                    logger.info("Permission timer fired for agent %d tool %s", agent_id, tool_id)
                    await self._broadcast({
                        "type": "agentToolPermission",
                        "id": agent_id,
                    })

        # Fire and forget — runs in the background task group
        import anyio

        # We need to run this in a task group; caller should manage this
        # For simplicity, we use anyio.from_thread or the caller's task group
        # This is a simplified version — the actual timer is started via task group
        pass

    def cancel(self, agent_id: int) -> None:
        """Cancel any pending timer for the agent."""
        scope = self._scopes.pop(agent_id, None)
        if scope is not None:
            scope.cancel()


class TimerManager:
    """Manages permission timers for all agents, running in a shared task group."""

    def __init__(self, broadcast: Broadcast) -> None:
        self._broadcast = broadcast
        self._scopes: dict[int, anyio.CancelScope] = {}

    async def start_permission_timer(self, agent_id: int, tg: anyio.abc.TaskGroup) -> None:
        """Start a permission timer in the given task group."""
        self.cancel_permission_timer(agent_id)
        scope = anyio.CancelScope()
        self._scopes[agent_id] = scope

        async def _run() -> None:
            with scope:
                await anyio.sleep(PERMISSION_TIMER_DELAY_S)
                if not scope.cancel_called:
                    logger.info("Permission timer fired for agent %d", agent_id)
                    await self._broadcast({
                        "type": "agentToolPermission",
                        "id": agent_id,
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
