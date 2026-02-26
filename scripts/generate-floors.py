#!/usr/bin/env python3
"""Generate floors.png — 7 grayscale 16×16 floor tile patterns.

Output: webview-ui/public/assets/floors.png (112×16, 7 tiles side by side)
Each tile is grayscale so the webview can colorize it via HSBC sliders.
"""

from pathlib import Path

from PIL import Image

TILE = 16
PATTERNS = 7
WIDTH = TILE * PATTERNS
HEIGHT = TILE

# Base gray values
BG = 140  # background luminance
FG = 100  # foreground (darker) luminance


def solid() -> list[list[int]]:
    """Pattern 0: Uniform solid gray."""
    return [[BG] * TILE for _ in range(TILE)]


def diagonal_stripes() -> list[list[int]]:
    """Pattern 1: 45° diagonal stripes (period 4)."""
    grid = [[BG] * TILE for _ in range(TILE)]
    for y in range(TILE):
        for x in range(TILE):
            if (x + y) % 4 == 0:
                grid[y][x] = FG
    return grid


def checkerboard() -> list[list[int]]:
    """Pattern 2: 2×2 checkerboard."""
    grid = [[BG] * TILE for _ in range(TILE)]
    for y in range(TILE):
        for x in range(TILE):
            if ((x // 2) + (y // 2)) % 2 == 0:
                grid[y][x] = FG + 15  # subtle contrast
    return grid


def small_dots() -> list[list[int]]:
    """Pattern 3: Small dot grid (every 4 pixels)."""
    grid = [[BG] * TILE for _ in range(TILE)]
    for y in range(TILE):
        for x in range(TILE):
            if x % 4 == 1 and y % 4 == 1:
                grid[y][x] = FG
    return grid


def horizontal_lines() -> list[list[int]]:
    """Pattern 4: Horizontal lines (period 4)."""
    grid = [[BG] * TILE for _ in range(TILE)]
    for y in range(TILE):
        if y % 4 == 0:
            for x in range(TILE):
                grid[y][x] = FG
    return grid


def diamond() -> list[list[int]]:
    """Pattern 5: Diamond lattice."""
    grid = [[BG] * TILE for _ in range(TILE)]
    for y in range(TILE):
        for x in range(TILE):
            if (x + y) % 8 == 0 or (x - y) % 8 == 0:
                grid[y][x] = FG
    return grid


def crosshatch() -> list[list[int]]:
    """Pattern 6: Grid lines (period 4)."""
    grid = [[BG] * TILE for _ in range(TILE)]
    for y in range(TILE):
        for x in range(TILE):
            if x % 4 == 0 or y % 4 == 0:
                grid[y][x] = FG + 10
    return grid


def main() -> None:
    patterns = [solid(), diagonal_stripes(), checkerboard(),
                small_dots(), horizontal_lines(), diamond(), crosshatch()]

    img = Image.new("L", (WIDTH, HEIGHT))
    pixels = img.load()

    for i, pattern in enumerate(patterns):
        ox = i * TILE
        for y in range(TILE):
            for x in range(TILE):
                pixels[ox + x, y] = pattern[y][x]

    out_path = Path(__file__).resolve().parent.parent / "webview-ui" / "public" / "assets" / "floors.png"
    img.save(str(out_path))
    print(f"Generated {out_path} ({WIDTH}×{HEIGHT}, {PATTERNS} patterns)")


if __name__ == "__main__":
    main()
