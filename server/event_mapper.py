"""Map TakopiEvents to pixel-agents WebSocket messages."""

from __future__ import annotations

from typing import Any

from takopi.model import (
    ActionEvent,
    CompletedEvent,
    StartedEvent,
    TakopiEvent,
)

from .constants import EXEMPT_TOOLS


def _is_exempt_tool(detail: dict[str, Any]) -> bool:
    name = detail.get("name", "")
    return name in EXEMPT_TOOLS


def map_event(event: TakopiEvent, agent_id: int) -> list[dict[str, Any]]:
    """Convert a TakopiEvent into a list of pixel-agents message dicts."""
    if isinstance(event, StartedEvent):
        return [{"type": "agentStatus", "id": agent_id, "status": "active"}]

    if isinstance(event, ActionEvent):
        action = event.action
        detail = action.detail
        parent = detail.get("parent_tool_use_id")

        if event.phase == "started":
            status = action.title
            if action.kind == "subagent":
                status = f"Subtask: {status}"

            if parent:
                return [{
                    "type": "subagentToolStart",
                    "id": agent_id,
                    "parentToolId": parent,
                    "toolId": action.id,
                    "status": status,
                }]

            msgs: list[dict[str, Any]] = [{
                "type": "agentToolStart",
                "id": agent_id,
                "toolId": action.id,
                "status": status,
            }]
            return msgs

        if event.phase == "completed":
            # Sub-agent task completed — clear the sub-agent character
            if action.kind == "subagent" and not parent:
                return [{
                    "type": "subagentClear",
                    "id": agent_id,
                    "parentToolId": action.id,
                }]
            if parent:
                return [{
                    "type": "subagentToolDone",
                    "id": agent_id,
                    "parentToolId": parent,
                    "toolId": action.id,
                }]
            return [{
                "type": "agentToolDone",
                "id": agent_id,
                "toolId": action.id,
            }]

    if isinstance(event, CompletedEvent):
        msgs = [
            {"type": "agentToolsClear", "id": agent_id},
            {"type": "agentStatus", "id": agent_id, "status": "waiting"},
        ]
        # Include the answer text for chat display
        if event.answer:
            msgs.append({
                "type": "agentAnswer",
                "id": agent_id,
                "text": event.answer,
            })
        return msgs

    return []


def needs_permission_timer(event: TakopiEvent) -> bool:
    """Check if this event should trigger a permission timer start.

    Fires for non-exempt tools at both parent and sub-agent level.
    """
    if not isinstance(event, ActionEvent):
        return False
    if event.phase != "started":
        return False
    return not _is_exempt_tool(event.action.detail)


def cancels_permission_timer(event: TakopiEvent) -> bool:
    """Check if this event should cancel any pending permission timer."""
    if isinstance(event, StartedEvent):
        return True
    if isinstance(event, CompletedEvent):
        return True
    if isinstance(event, ActionEvent):
        # Any event data arriving means things are moving
        return True
    return False
