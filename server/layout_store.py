"""Layout persistence — read/write/watch ~/.pixel-agents/layout.json."""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

from .constants import LAYOUT_FILE_DIR, LAYOUT_FILE_NAME

logger = logging.getLogger(__name__)

LayoutDict = dict[str, Any]


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
