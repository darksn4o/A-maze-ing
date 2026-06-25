"""Block 6 - 2D render: turning a grid into block ASCII art.

Maps the maze onto a double-resolution character canvas (cells on odd
rows/cols, walls between them on even ones), then flattens it to a coloured,
double-width block-art string for the terminal.
"""

from typing import Dict, List, Optional, Set

from .colors import (COLOR_RESET, ENTRY_COLOR, EXIT_COLOR, LABEL_COLOR,
                     PATH_COLOR)
from .data_model import Coord, Grid


def _coloured_canvas(blocked: Set[Coord]) -> Set[Coord]:
    """Return the canvas positions that fill the inside of the obstacle.

    A cell at ``(x, y)`` maps to canvas position ``(2y+1, 2x+1)``. A shared
    wall or corner is only filled when every cell touching it is blocked, so
    the obstacle's interior is solid colour while its boundary with the maze
    keeps a clean white outline.

    Args:
        blocked: The set of blocked maze positions.

    Returns:
        Canvas ``(row, col)`` positions to draw in the obstacle colour.
    """
    filled: Set[Coord] = set()
    for x, y in blocked:
        cy, cx = 2 * y + 1, 2 * x + 1
        filled.add((cy, cx))
        if (x + 1, y) in blocked:
            filled.add((cy, cx + 1))
        if (x, y + 1) in blocked:
            filled.add((cy + 1, cx))
        if {(x + 1, y), (x, y + 1), (x + 1, y + 1)} <= blocked:
            filled.add((cy + 1, cx + 1))
    return filled


def _path_canvas(path: List[Coord]) -> Set[Coord]:
    """Return the canvas positions that trace a solved path.

    Includes each path cell's centre plus the passage midpoint between
    consecutive cells, so the highlight forms one continuous line.

    Args:
        path: The list of positions from entry to exit.

    Returns:
        Canvas ``(row, col)`` positions to draw in the path colour.
    """
    positions: Set[Coord] = set()
    for index, (x, y) in enumerate(path):
        cy, cx = 2 * y + 1, 2 * x + 1
        positions.add((cy, cx))
        if index + 1 < len(path):
            nx, ny = path[index + 1]
            positions.add((cy + (ny - y), cx + (nx - x)))
    return positions


def render(grid: Grid, entry: Optional[Coord] = None,
           exit_: Optional[Coord] = None,
           blocked: Optional[Set[Coord]] = None,
           path: Optional[List[Coord]] = None) -> str:
    """Render a maze as block ASCII art for quick terminal inspection.

    The maze is drawn on a ``(2*height+1)`` by ``(2*width+1)`` canvas where
    every wall is a solid block. Each character is doubled in width so the
    walls look thick and stay roughly square. The obstacle, entry, exit and
    solved path are drawn as coloured blocks.

    Args:
        grid: The maze grid of :class:`Cell` objects.
        entry: Optional entry position, drawn as a green block.
        exit_: Optional exit position, drawn as a red block.
        blocked: Optional obstacle positions, drawn in the obstacle colour.
        path: Optional solved path to highlight in the path colour.

    Returns:
        A multi-line string drawing the maze with solid block walls.
    """
    wall = "█"
    blocked = blocked or set()
    height = len(grid)
    width = len(grid[0])
    rows = 2 * height + 1
    cols = 2 * width + 1
    canvas: List[List[str]] = [[wall] * cols for _ in range(rows)]

    for y in range(height):
        for x in range(width):
            if (x, y) in blocked:
                continue  # leave the obstacle fully solid so it fills in
            cell = grid[y][x]
            cy, cx = 2 * y + 1, 2 * x + 1
            canvas[cy][cx] = " "
            if cell.is_open(1):
                canvas[cy - 1][cx] = " "
            if cell.is_open(2):
                canvas[cy][cx + 1] = " "
            if cell.is_open(4):
                canvas[cy + 1][cx] = " "
            if cell.is_open(8):
                canvas[cy][cx - 1] = " "

    colours: Dict[Coord, str] = {
        pos: LABEL_COLOR for pos in _coloured_canvas(blocked)
    }
    if path:
        for pos in _path_canvas(path):
            canvas[pos[0]][pos[1]] = wall
            colours[pos] = PATH_COLOR
    if entry is not None:
        pos = (2 * entry[1] + 1, 2 * entry[0] + 1)
        canvas[pos[0]][pos[1]] = wall
        colours[pos] = ENTRY_COLOR
    if exit_ is not None:
        pos = (2 * exit_[1] + 1, 2 * exit_[0] + 1)
        canvas[pos[0]][pos[1]] = wall
        colours[pos] = EXIT_COLOR

    lines: List[str] = []
    for r in range(rows):
        parts: List[str] = []
        for c in range(cols):
            block = canvas[r][c] * 2
            colour = colours.get((r, c))
            if colour is not None:
                block = colour + block + COLOR_RESET
            parts.append(block)
        lines.append("".join(parts))

    return "\n".join(lines)
