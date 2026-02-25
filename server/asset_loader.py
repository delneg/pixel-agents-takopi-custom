"""Server-side furniture asset loading — PNG parsing for furniture sprites.

Characters, floors, and walls are loaded client-side from PNGs via canvas.
Only furniture needs server-side parsing because there are many small PNGs.
"""

from __future__ import annotations

import json
import logging
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image

logger = logging.getLogger(__name__)

PNG_ALPHA_THRESHOLD = 128


def _png_to_sprite_data(png_bytes: bytes, width: int, height: int) -> list[list[str]]:
    """Convert PNG bytes to SpriteData (2D hex string array) using Pillow."""
    img = Image.open(BytesIO(png_bytes)).convert("RGBA")
    pixels = img.load()

    sprite: list[list[str]] = []
    for y in range(min(height, img.height)):
        row: list[str] = []
        for x in range(min(width, img.width)):
            r, g, b, a = pixels[x, y]
            if a < PNG_ALPHA_THRESHOLD:
                row.append("")
            else:
                row.append(f"#{r:02X}{g:02X}{b:02X}")
        sprite.append(row)
    return sprite


def load_furniture_assets(assets_root: Path) -> dict[str, Any] | None:
    """Load furniture catalog and sprites from assets/furniture/.

    Returns dict with 'catalog' (list) and 'sprites' (dict of id -> SpriteData).
    """
    catalog_path = assets_root / "assets" / "furniture" / "furniture-catalog.json"
    if not catalog_path.exists():
        logger.info("No furniture catalog found at: %s", catalog_path)
        return None

    logger.info("Loading furniture assets from: %s", catalog_path)
    catalog_data = json.loads(catalog_path.read_text("utf-8"))
    catalog: list[dict[str, Any]] = catalog_data.get("assets", [])

    sprites: dict[str, list[list[str]]] = {}
    for asset in catalog:
        try:
            file_path = asset["file"]
            if not file_path.startswith("assets/"):
                file_path = f"assets/{file_path}"
            full_path = assets_root / file_path

            if not full_path.exists():
                logger.warning("Asset file not found: %s", asset["file"])
                continue

            png_bytes = full_path.read_bytes()
            sprite_data = _png_to_sprite_data(png_bytes, asset["width"], asset["height"])
            sprites[asset["id"]] = sprite_data
        except Exception:
            logger.warning("Error loading asset %s", asset.get("id", "?"), exc_info=True)

    logger.info("Loaded %d / %d furniture sprites", len(sprites), len(catalog))
    return {"catalog": catalog, "sprites": sprites}
