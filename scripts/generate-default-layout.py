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

# Grid dimensions — wider to fit 4 workstations per row
COLS = 20
ROWS = 14

# TileType constants
WALL = 0
FLOOR_1 = 1  # main wood floor
FLOOR_2 = 2  # aisle / accent
VOID = 8

# Floor colors (HSB for Colorize mode)
WOOD_FLOOR = {"h": 30, "s": 40, "b": -20, "c": -30}   # warm wood
CARPET = {"h": 220, "s": 25, "b": -40, "c": -40}       # blue-gray carpet
WALL_COLOR = {"h": 214, "s": 30, "b": -100, "c": -55}  # dark wall tint


def make_grid() -> list[int]:
    """Create the tile grid.

    Layout:
      Row 0:        VOID (above walls)
      Row 1:        WALL
      Rows 2-12:    Floor (wood + carpet aisle)
      Row 13:       VOID (below)
    """
    grid = [[VOID] * COLS for _ in range(ROWS)]

    # Row 1: wall across the top
    for c in range(1, COLS - 1):
        grid[1][c] = WALL

    # Rows 2-12: floor area
    for r in range(2, ROWS - 1):
        for c in range(1, COLS - 1):
            grid[r][c] = FLOOR_1  # wood floor

    # Center aisle carpet (2 tiles wide)
    for r in range(2, ROWS - 1):
        grid[r][9] = FLOOR_2
        grid[r][10] = FLOOR_2

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
    """Place furniture mimicking a real office layout.

    Original style:
      - Bookshelves along the back wall
      - Rows of desks facing down, chairs directly below
      - Plants between sections and in corners
      - PCs next to desks
      - Lamps for ambiance
    """
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

    # ══════════════════════════════════════════════════════
    # BACK WALL — bookshelves and whiteboards (row 1-2)
    # ══════════════════════════════════════════════════════

    # Left section bookshelves (along wall)
    add("bookshelf", 1, 1)    # col 1
    add("bookshelf", 2, 1)    # col 2
    add("bookshelf", 3, 1)    # col 3

    # Left whiteboard
    add("whiteboard", 5, 1)   # cols 5-6

    # Right whiteboard
    add("whiteboard", 13, 1)  # cols 13-14

    # Right section bookshelves (along wall)
    add("bookshelf", 16, 1)   # col 16
    add("bookshelf", 17, 1)   # col 17
    add("bookshelf", 18, 1)   # col 18

    # ══════════════════════════════════════════════════════
    # LEFT WING — workstations (cols 2-8)
    # ══════════════════════════════════════════════════════

    # Row A: top desks (near wall)
    add("desk", 2, 3)         # desk at (2,3), 2×2
    add("pc", 4, 3)           # PC next to desk
    add("desk", 6, 3)         # desk at (6,3), 2×2
    add("pc", 5, 3)           # PC next to desk

    # Row A: chairs below top desks
    add("chair", 3, 5)        # chair for desk at (2,3)
    add("chair", 7, 5)        # chair for desk at (6,3)

    # Row B: bottom desks
    add("desk", 2, 8)         # desk at (2,8), 2×2
    add("pc", 4, 8)           # PC next to desk
    add("desk", 6, 8)         # desk at (6,8), 2×2
    add("pc", 5, 8)           # PC next to desk

    # Row B: chairs below bottom desks
    add("chair", 3, 10)       # chair for desk at (2,8)
    add("chair", 7, 10)       # chair for desk at (6,8)

    # ══════════════════════════════════════════════════════
    # RIGHT WING — workstations (cols 11-17)
    # ══════════════════════════════════════════════════════

    # Row A: top desks
    add("desk", 11, 3)        # desk at (11,3)
    add("pc", 13, 3)          # PC next to desk
    add("desk", 15, 3)        # desk at (15,3)
    add("pc", 14, 3)          # PC next to desk

    # Row A: chairs below top desks
    add("chair", 12, 5)       # chair for desk at (11,3)
    add("chair", 16, 5)       # chair for desk at (15,3)

    # Row B: bottom desks
    add("desk", 11, 8)        # desk at (11,8)
    add("pc", 13, 8)          # PC next to desk
    add("desk", 15, 8)        # desk at (15,8)
    add("pc", 14, 8)          # PC next to desk

    # Row B: chairs below bottom desks
    add("chair", 12, 10)      # chair for desk at (11,8)
    add("chair", 16, 10)      # chair for desk at (15,8)

    # ══════════════════════════════════════════════════════
    # PLANTS — corners and dividers
    # ══════════════════════════════════════════════════════

    # Corner plants
    add("plant", 1, 12)       # bottom-left
    add("plant", 18, 12)      # bottom-right

    # Plants as section dividers (near aisle)
    add("plant", 8, 3)        # left of aisle, top
    add("plant", 8, 11)       # left of aisle, bottom
    add("plant", 11, 11)      # right of aisle, bottom

    # ══════════════════════════════════════════════════════
    # ACCENT FURNITURE
    # ══════════════════════════════════════════════════════

    # Cooler in the aisle (break area)
    add("cooler", 10, 3)      # top of aisle

    # Lamps for ambiance
    add("lamp", 1, 6)         # left side
    add("lamp", 18, 6)        # right side
    add("lamp", 9, 11)        # center aisle bottom

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
