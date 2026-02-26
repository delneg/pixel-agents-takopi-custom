"""Layout persistence — read/write/watch ~/.pixel-agents/layout.json."""

from __future__ import annotations

import json
import logging
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Awaitable

from .constants import LAYOUT_FILE_DIR, LAYOUT_FILE_NAME

logger = logging.getLogger(__name__)

LayoutDict = dict[str, Any]

# Timestamp of our last own write — used to skip watcher re-reads
_last_own_write: float = 0.0
_OWN_WRITE_GRACE_S = 1.0  # ignore file changes within 1s of our own write


def _layout_file_path() -> Path:
    return Path.home() / LAYOUT_FILE_DIR / LAYOUT_FILE_NAME


def read_layout() -> LayoutDict | None:
    fp = _layout_file_path()
    try:
        if not fp.exists():
            return None
        return json.loads(fp.read_text("utf-8"))
    except Exception:
        logger.exception("Failed to read layout file")
        return None


def write_layout(layout: LayoutDict) -> None:
    global _last_own_write
    fp = _layout_file_path()
    fp.parent.mkdir(parents=True, exist_ok=True)
    try:
        data = json.dumps(layout, indent=2)
        # Atomic write via temp + rename
        fd, tmp = tempfile.mkstemp(dir=str(fp.parent), suffix=".tmp")
        try:
            os.write(fd, data.encode("utf-8"))
            os.close(fd)
            os.replace(tmp, str(fp))
            _last_own_write = time.monotonic()
        except BaseException:
            os.close(fd) if not os.get_inheritable(fd) else None
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise
    except Exception:
        logger.exception("Failed to write layout file")


def load_default_layout(assets_root: Path) -> LayoutDict | None:
    """Load bundled default-layout.json from assets/."""
    layout_path = assets_root / "assets" / "default-layout.json"
    if not layout_path.exists():
        return None
    try:
        layout = json.loads(layout_path.read_text("utf-8"))
        logger.info("Loaded default layout (%sx%s)", layout.get("cols"), layout.get("rows"))
        return layout
    except Exception:
        logger.exception("Failed to load default layout")
        return None


def ensure_layout(assets_root: Path) -> LayoutDict | None:
    """Load layout from file, falling back to bundled default."""
    layout = read_layout()
    if layout:
        return layout
    default = load_default_layout(assets_root)
    if default:
        write_layout(default)
        return default
    return None


async def watch_layout_file(
    broadcast: Callable[[dict[str, Any]], Awaitable[None]],
) -> None:
    """Watch the layout file for external changes and broadcast updates.

    Skips changes that were caused by our own writes (within _OWN_WRITE_GRACE_S).
    Runs forever — call from a task group.
    """
    from watchfiles import awatch, Change

    fp = _layout_file_path()
    fp.parent.mkdir(parents=True, exist_ok=True)

    logger.info("Watching layout file: %s", fp)
    async for changes in awatch(fp.parent):
        for change_type, changed_path in changes:
            if Path(changed_path) != fp:
                continue
            if change_type not in (Change.modified, Change.added):
                continue
            # Skip our own writes
            if time.monotonic() - _last_own_write < _OWN_WRITE_GRACE_S:
                continue
            layout = read_layout()
            if layout:
                logger.info("External layout change detected, broadcasting")
                await broadcast({"type": "layoutLoaded", "layout": layout})
