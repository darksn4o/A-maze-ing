"""Block 3 - Generation: building perfect and imperfect mazes.

Carves a perfect maze with the recursive backtracker, optionally adds loops
to make it imperfect, and provides a checker that confirms whether a finished
grid is still perfect.
"""

import random
from typing import Callable, List, Optional, Set, Tuple

from .data_model import DIRS, Cell, Coord, Grid


def new_grid(width: int, height: int) -> Grid:
    """Create a grid where every cell has all four walls closed.

    Args:
        width: Number of cells per row (the x axis).
        height: Number of rows (the y axis).

    Returns:
        A ``height`` x ``width`` grid of fully-walled :class:`Cell` objects.
    """
    return [[Cell() for _ in range(width)] for _ in range(height)]


def unvisited_neighbours(
    x: int,
    y: int,
    width: int,
    height: int,
    visited: Set[Coord],
) -> List[Tuple[str, int, int, int, int]]:
    """Return the in-bounds, not-yet-visited neighbours of a cell.

    Args:
        x: Column of the current cell.
        y: Row of the current cell.
        width: Grid width, used for the bounds check.
        height: Grid height, used for the bounds check.
        visited: Set of positions already carved into.

    Returns:
        A list of ``(direction, nx, ny, bit_here, bit_there)`` tuples, one
        per reachable, unvisited neighbour.
    """
    found: List[Tuple[str, int, int, int, int]] = []
    for direction, (dx, dy, bit_here, bit_there) in DIRS.items():
        nx, ny = x + dx, y + dy
        if 0 <= nx < width and 0 <= ny < height and (nx, ny) not in visited:
            found.append((direction, nx, ny, bit_here, bit_there))
    return found


def carve(grid: Grid, x: int, y: int, nx: int, ny: int,
          bit_here: int, bit_there: int) -> None:
    """Open the wall between two adjacent cells.

    Clears ``bit_here`` in cell ``(x, y)`` and the matching ``bit_there`` in
    its neighbour ``(nx, ny)`` so both sides of the shared wall agree.

    Args:
        grid: The maze grid to mutate.
        x: Column of the current cell.
        y: Row of the current cell.
        nx: Column of the neighbour cell.
        ny: Row of the neighbour cell.
        bit_here: Wall bit to clear in the current cell.
        bit_there: Wall bit to clear in the neighbour cell.
    """
    grid[y][x].open(bit_here)
    grid[ny][nx].open(bit_there)


def generate(width: int, height: int, entry: Coord = (0, 0),
             blocked: Optional[Set[Coord]] = None,
             on_step: Optional[Callable[[Grid, Coord], None]] = None) -> Grid:
    """Generate a perfect maze with the recursive backtracker algorithm.

    A perfect maze has exactly one path between any two cells: every cell is
    reachable and there are no loops. The algorithm walks the grid carving
    passages into unvisited cells and backtracks whenever it hits a dead end.

    Any cells in ``blocked`` are treated as a solid obstacle: they are never
    carved into, so the maze is generated around them while staying perfect
    over the remaining free cells.

    Args:
        width: Number of cells per row (the x axis).
        height: Number of rows (the y axis).
        entry: Position to start carving from, as ``(x, y)``.
        blocked: Positions to leave sealed as an obstacle; ``None`` means none.
        on_step: Optional callback invoked with ``(grid, current_pos)`` after
            every carve and backtrack, used to drive an animation.

    Returns:
        A finished maze grid of :class:`Cell` objects.
    """
    blocked = blocked or set()
    grid = new_grid(width, height)
    # Seeding visited with the obstacle keeps the carver from entering it.
    visited: Set[Coord] = {entry} | blocked
    stack: List[Coord] = [entry]

    while stack:
        x, y = stack[-1]
        neighbours = unvisited_neighbours(x, y, width, height, visited)

        if neighbours:
            _direction, nx, ny, bit_here, bit_there = random.choice(neighbours)
            carve(grid, x, y, nx, ny, bit_here, bit_there)
            visited.add((nx, ny))
            stack.append((nx, ny))
            if on_step is not None:
                on_step(grid, (nx, ny))
        else:
            stack.pop()
            if on_step is not None and stack:
                on_step(grid, stack[-1])

    return grid


def _block_fully_open(grid: Grid, bx: int, by: int) -> bool:
    """Return True if the 3x3 cell block at ``(bx, by)`` has no inner walls.

    Args:
        grid: The maze grid of :class:`Cell` objects.
        bx: Column of the block's top-left cell.
        by: Row of the block's top-left cell.

    Returns:
        ``True`` if every wall inside the 3x3 block is open.
    """
    for d_y in range(3):
        for d_x in range(2):
            if not grid[by + d_y][bx + d_x].is_open(2):  # east wall closed
                return False
    for d_y in range(2):
        for d_x in range(3):
            if not grid[by + d_y][bx + d_x].is_open(4):  # south wall closed
                return False
    return True


def _creates_open_3x3(grid: Grid, x: int, y: int) -> bool:
    """Return True if any 3x3 block touching ``(x, y)`` is fully open.

    Only the blocks whose top-left corner can include ``(x, y)`` are checked,
    which is enough to validate a wall that was just opened at that cell.

    Args:
        grid: The maze grid of :class:`Cell` objects.
        x: Column of the cell whose wall changed.
        y: Row of the cell whose wall changed.

    Returns:
        ``True`` if opening that wall formed a forbidden 3x3 open area.
    """
    height = len(grid)
    width = len(grid[0])
    for by in range(max(0, y - 2), min(height - 3, y) + 1):
        for bx in range(max(0, x - 2), min(width - 3, x) + 1):
            if _block_fully_open(grid, bx, by):
                return True
    return False


def make_imperfect(grid: Grid, blocked: Optional[Set[Coord]] = None,
                   fraction: float = 0.15) -> Grid:
    """Add loops to a perfect maze without creating a 3x3 open area.

    Walls between two free cells are knocked down in random order. A wall is
    only opened if doing so does not form a forbidden 3x3 fully-open block, so
    corridors never grow wider than two cells.

    Args:
        grid: A finished perfect maze; mutated in place.
        blocked: Obstacle positions to never carve into; ``None`` means none.
        fraction: Share of the closed interior walls to try to open.

    Returns:
        The same grid, now imperfect (it contains loops).
    """
    blocked = blocked or set()
    height = len(grid)
    width = len(grid[0])

    candidates: List[Tuple[int, int, int, int, int, int]] = []
    for y in range(height):
        for x in range(width):
            if (x, y) in blocked:
                continue
            if (x + 1 < width and (x + 1, y) not in blocked
                    and not grid[y][x].is_open(2)):
                candidates.append((x, y, 2, x + 1, y, 8))
            if (y + 1 < height and (x, y + 1) not in blocked
                    and not grid[y][x].is_open(4)):
                candidates.append((x, y, 4, x, y + 1, 1))

    random.shuffle(candidates)
    target = int(len(candidates) * fraction)
    opened = 0
    for x, y, bit_here, nx, ny, bit_there in candidates:
        if opened >= target:
            break
        grid[y][x].open(bit_here)
        grid[ny][nx].open(bit_there)
        if _creates_open_3x3(grid, x, y):
            grid[y][x].close(bit_here)  # revert: would make a 3x3 open area
            grid[ny][nx].close(bit_there)
        else:
            opened += 1
    return grid


def is_perfect(grid: Grid, blocked: Optional[Set[Coord]] = None) -> bool:
    """Report whether the maze is perfect over its free cells.

    A perfect maze is a spanning tree: every free (non-obstacle) cell is
    reachable and there are no loops. That holds exactly when the free cells
    are all connected *and* the number of open passages equals the number of
    free cells minus one.

    Args:
        grid: The maze grid of :class:`Cell` objects.
        blocked: Positions excluded as an obstacle; ``None`` means none.

    Returns:
        ``True`` if the maze is perfect, ``False`` otherwise.
    """
    blocked = blocked or set()
    height = len(grid)
    width = len(grid[0])
    free = [(x, y) for y in range(height) for x in range(width)
            if (x, y) not in blocked]
    if not free:
        return True

    # Count each shared passage once via east and south openings.
    edges = 0
    for x, y in free:
        if grid[y][x].is_open(2):
            edges += 1
        if grid[y][x].is_open(4):
            edges += 1

    # Flood fill from one free cell to measure connectivity.
    start = free[0]
    seen: Set[Coord] = {start}
    stack: List[Coord] = [start]
    while stack:
        x, y = stack.pop()
        for _direction, (dx, dy, bit_here, _bt) in DIRS.items():
            if not grid[y][x].is_open(bit_here):
                continue
            nxt = (x + dx, y + dy)
            if nxt not in seen and nxt not in blocked:
                seen.add(nxt)
                stack.append(nxt)

    return len(seen) == len(free) and edges == len(free) - 1
