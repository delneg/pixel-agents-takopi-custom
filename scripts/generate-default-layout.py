#!/usr/bin/env python3
"""Generate default-layout.json using only the 8 hardcoded furniture types.

Furniture types available (from FurnitureType in types.ts):
  desk       — 2×2 tiles, isDesk=true
  bookshelf  — 1×2 tiles
  plant      — 1×1 tile
  cooler     — 1×1 tile
  whiteboard — 2×1 tiles
  chair      — 1×1 tile
  pc         — 1×1 tile
  lamp       — 1×1 tile

TileType values:
  0 = WALL, 1-7 = FLOOR_1..FLOOR_7, 8 = VOID

Output: webview-ui/public/assets/default-layout.json
"""

import json
from pathlib import Path

# Grid dimensions
COLS = 16
ROWS = 11

# TileType constants
WALL = 0
FLOOR_1 = 1
FLOOR_2 = 2
VOID = 8

# Floor colors (HSB for Colorize mode)
WOOD_FLOOR = {"h": 30, "s": 40, "b": -20, "c": -30}   # warm wood
CARPET = {"h": 220, "s": 25, "b": -40, "c": -40}       # blue-gray carpet
WALL_COLOR = {"h": 214, "s": 30, "b": -100, "c": -55}  # dark wall tint


def make_grid() -> list[int]:
    """Create the tile grid."""
    grid = [[VOID] * COLS for _ in range(ROWS)]

    # Row 0: all VOID (above wall)
    # Row 1: wall row
    for c in range(1, COLS - 1):
        grid[1][c] = WALL

    # Rows 2-9: floor area
    for r in range(2, ROWS - 1):
        for c in range(1, COLS - 1):
            # Main area: wood floor, center aisle: carpet
            if 7 <= c <= 8:
                grid[r][c] = FLOOR_2  # carpet aisle
            else:
                grid[r][c] = FLOOR_1  # wood floor

    # Flatten
    return [grid[r][c] for r in range(ROWS) for c in range(COLS)]


def make_tile_colors(tiles: list[int]) -> list[dict | None]:
    """Create per-tile color settings."""
    colors: list[dict | None] = []
    for t in tiles:
        if t == WALL:
            colors.append(WALL_COLOR)
        elif t == FLOOR_1:
            colors.append(WOOD_FLOOR)
        elif t == FLOOR_2:
            colors.append(CARPET)
        else:
            colors.append(None)
    return colors


def make_furniture() -> list[dict]:
    """Place furniture for a cozy office."""
    items: list[dict] = []
    uid_counter = 0

    def add(ftype: str, col: int, row: int, color: dict | None = None) -> str:
        nonlocal uid_counter
        uid = f"{ftype}-{uid_counter}"
        uid_counter += 1
        item: dict = {"uid": uid, "type": ftype, "col": col, "row": row}
        if color:
            item["color"] = color
        items.append(item)
        return uid

    # === Left wing (cols 1-6) — 2 workstations ===

    # Workstation 1: top-left
    add("desk", 2, 3)        # 2×2 desk at (2,3)
    add("chair", 3, 5)       # chair below desk
    add("pc", 2, 2)          # PC on/near desk

    # Workstation 2: bottom-left
    add("desk", 2, 7)        # 2×2 desk at (2,7)
    add("chair", 3, 6)       # chair above desk
    add("pc", 4, 7)          # PC near desk

    # Left wall decor
    add("bookshelf", 1, 2)   # bookshelf on left wall
    add("bookshelf", 1, 4)   # another bookshelf
    add("plant", 1, 6)       # plant
    add("lamp", 5, 2)        # lamp near top

    # === Right wing (cols 9-14) — 2 workstations ===

    # Workstation 3: top-right
    add("desk", 11, 3)       # 2×2 desk
    add("chair", 11, 5)      # chair below
    add("pc", 13, 3)         # PC

    # Workstation 4: bottom-right
    add("desk", 11, 7)       # 2×2 desk
    add("chair", 12, 6)      # chair above
    add("lamp", 10, 7)       # lamp near desk

    # Right wall decor
    add("bookshelf", 14, 2)  # bookshelf
    add("bookshelf", 14, 4)  # bookshelf
    add("plant", 14, 6)      # plant
    add("plant", 14, 8)      # plant

    # === Center aisle decor ===
    add("cooler", 8, 2)      # water cooler near wall
    add("whiteboard", 5, 1)  # whiteboard on wall (row 1)
    add("whiteboard", 10, 1) # whiteboard on wall

    # === Bottom row decor ===
    add("plant", 1, 9)       # corner plant
    add("plant", 14, 9)      # corner plant
    add("lamp", 7, 9)        # lamp in aisle

    return items


def main() -> None:
    tiles = make_grid()
    tile_colors = make_tile_colors(tiles)
    furniture = make_furniture()

    layout = {
        "version": 1,
        "cols": COLS,
        "rows": ROWS,
        "tiles": tiles,
        "furniture": furniture,
        "tileColors": tile_colors,
    }

    out_path = (
        Path(__file__).resolve().parent.parent
        / "webview-ui" / "public" / "assets" / "default-layout.json"
    )
    out_path.write_text(json.dumps(layout, indent=2) + "\n")
    print(f"Generated {out_path}")
    print(f"  Grid: {COLS}×{ROWS}")
    print(f"  Furniture: {len(furniture)} items")
    print(f"  Types used: {sorted(set(f['type'] for f in furniture))}")


if __name__ == "__main__":
    main()
