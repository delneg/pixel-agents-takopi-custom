"""FastAPI application — serves webview static files and WebSocket endpoint."""

from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import anyio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

from .agent_manager import AgentManager
from .asset_loader import load_furniture_assets
from .layout_store import ensure_layout, write_layout, read_layout

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Resolve paths relative to project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
WEBVIEW_DIST = PROJECT_ROOT / "dist" / "webview"  # Vite builds to ../dist/webview
ASSETS_ROOT = PROJECT_ROOT / "webview-ui" / "public"

# Shared state
clients: set[WebSocket] = set()
agent_manager: AgentManager | None = None
furniture_data: dict[str, Any] | None = None
settings: dict[str, Any] = {"soundEnabled": True}


async def broadcast(msg: dict[str, Any]) -> None:
    """Send a message to all connected WebSocket clients."""
    data = json.dumps(msg)
    dead: list[WebSocket] = []
    for ws in clients:
        try:
            await ws.send_text(data)
        except Exception:
            dead.append(ws)
    for ws in dead:
        clients.discard(ws)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — initialize shared state."""
    global agent_manager, furniture_data

    # Determine CWD for Claude — use current working directory
    cwd = Path.cwd().resolve()
    logger.info("Project CWD: %s", cwd)

    agent_manager = AgentManager(broadcast, cwd)

    # Load furniture assets (server-side PNG parsing)
    # Try dist first, then public, then project root
    for root in [WEBVIEW_DIST, ASSETS_ROOT, PROJECT_ROOT]:
        data = load_furniture_assets(root)
        if data:
            furniture_data = data
            break
    if furniture_data:
        logger.info("Loaded %d furniture assets", len(furniture_data["catalog"]))
    else:
        logger.warning("No furniture assets found")

    # Run with a background task group for agent runners
    async with anyio.create_task_group() as tg:
        agent_manager.set_task_group(tg)
        yield
        # Cleanup
        agent_manager = None


app = FastAPI(lifespan=lifespan)


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    clients.add(ws)
    logger.info("WebSocket client connected (%d total)", len(clients))

    try:
        # Wait for webviewReady
        # Send initial data in the right order:
        # 1. settings
        # 2. furniture assets (catalog + sprites)
        # 3. layout
        # 4. existing agents

        await ws.send_text(json.dumps({
            "type": "settingsLoaded",
            "soundEnabled": settings.get("soundEnabled", True),
        }))

        if furniture_data:
            await ws.send_text(json.dumps({
                "type": "furnitureAssetsLoaded",
                "catalog": furniture_data["catalog"],
                "sprites": furniture_data["sprites"],
            }))

        # Load and send layout
        layout = ensure_layout(ASSETS_ROOT) or ensure_layout(WEBVIEW_DIST) or ensure_layout(PROJECT_ROOT)
        if layout:
            await ws.send_text(json.dumps({
                "type": "layoutLoaded",
                "layout": layout,
            }))

        # Send existing agents
        if agent_manager:
            await ws.send_text(json.dumps(
                agent_manager.get_existing_agents_message()
            ))

        # Message loop
        while True:
            raw = await ws.receive_text()
            msg = json.loads(raw)
            await handle_message(ws, msg)

    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("WebSocket error")
    finally:
        clients.discard(ws)
        logger.info("WebSocket client disconnected (%d remaining)", len(clients))


async def handle_message(ws: WebSocket, msg: dict[str, Any]) -> None:
    """Handle an incoming WebSocket message from the client."""
    msg_type = msg.get("type")

    if msg_type == "webviewReady":
        # Already handled in connection setup
        pass

    elif msg_type == "openClaude":
        if agent_manager:
            await agent_manager.create_agent()

    elif msg_type == "closeAgent":
        agent_id = msg.get("id")
        if agent_manager and agent_id is not None:
            await agent_manager.remove_agent(agent_id)

    elif msg_type == "sendPrompt":
        agent_id = msg.get("id")
        text = msg.get("text", "")
        if agent_manager and agent_id is not None and text.strip():
            await agent_manager.send_prompt(agent_id, text)

    elif msg_type == "focusAgent":
        # In webapp mode, just broadcast selection to all clients
        agent_id = msg.get("id")
        if agent_id is not None:
            await broadcast({"type": "agentSelected", "id": agent_id})

    elif msg_type == "saveLayout":
        layout = msg.get("layout")
        if layout:
            write_layout(layout)

    elif msg_type == "saveAgentSeats":
        seats = msg.get("seats")
        if agent_manager and seats:
            for id_str, seat_data in seats.items():
                agent_id = int(id_str)
                session = agent_manager.agents.get(agent_id)
                if session:
                    session.seat_id = seat_data.get("seatId")
                    session.palette = seat_data.get("palette", session.palette)
                    session.hue_shift = seat_data.get("hueShift", session.hue_shift)

    elif msg_type == "exportLayout":
        # Read current layout and send it back for download
        layout = read_layout()
        if layout:
            await ws.send_text(json.dumps({
                "type": "exportLayoutData",
                "layout": layout,
            }))

    elif msg_type == "importLayout":
        layout = msg.get("layout")
        if layout and isinstance(layout, dict) and layout.get("version") == 1 and "tiles" in layout:
            write_layout(layout)
            await broadcast({"type": "layoutLoaded", "layout": layout})

    elif msg_type == "setSoundEnabled":
        enabled = msg.get("enabled", True)
        settings["soundEnabled"] = enabled

    else:
        logger.debug("Unhandled message type: %s", msg_type)


# Mount static files AFTER the WebSocket route
# Serve the entire dist directory (includes index.html, JS/CSS, and assets/)
if WEBVIEW_DIST.exists():
    app.mount("/", StaticFiles(directory=str(WEBVIEW_DIST), html=True), name="webview")
