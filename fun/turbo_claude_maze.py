"""Perfect/imperfect maze generation, solving and rendering.

Each cell is a :class:`Cell` object wrapping a single integer in the range
0-15. A set bit means the wall on that side is *closed*::

    bit 0 (value 1) -> North
    bit 1 (value 2) -> East
    bit 2 (value 4) -> South
    bit 3 (value 8) -> West

A freshly created cell starts at 0xF (all four walls closed). Carving the
maze means clearing bits to open passages between cells. This module is the
reusable generation/solving core; ``a_maze_ing.py`` is the entry point.

The code below is grouped into behavioural sections:

    1. Data model        - the Cell object plus grid/coordinate types
    2. Obstacle ("42")   - the block-letter shape carved around
    3. Generation        - building perfect and imperfect mazes
    4. Solving           - DFS/BFS pathfinding over the grid
    5. Colours           - ANSI palette for the overlay markers
    6. 2D render         - turning a grid into block ASCII art
    7. Animation         - frame-by-frame terminal playback
    8. File IO           - reading config and writing the hex maze
    9. Entry point       - wiring it all together
"""

import random
import sys
import time
from collections import deque
from dataclasses import dataclass
from typing import Callable, Deque, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# 1. Data model: the Cell object plus grid/coordinate types
# ---------------------------------------------------------------------------

# All four walls closed: North | East | South | West.
ALL_WALLS: int = 0xF

# direction -> (dx, dy, bit_here, bit_there)
#   dx, dy     : how (x, y) changes when stepping that way (y grows downward)
#   bit_here   : wall bit to clear in the current cell
#   bit_there  : matching wall bit to clear in the neighbour cell
DIRS: Dict[str, Tuple[int, int, int, int]] = {
    "N": (0, -1, 1, 4),
    "E": (1, 0, 2, 8),
    "S": (0, 1, 4, 1),
    "W": (-1, 0, 8, 2),
}

# An (x, y) position on the grid (x is the column, y is the row).
Coord = Tuple[int, int]


@dataclass
class Cell:
    """A single maze cell, tracking which of its four walls are closed.

    ``walls`` is a bitmask (see the module docstring): a set bit means that
    wall is closed, a clear bit means it is carved open. A freshly created
    cell starts fully walled in.

    Attributes:
        walls: The wall bitmask for this cell.
    """

    walls: int = ALL_WALLS

    def is_open(self, wall: int) -> bool:
        """Return ``True`` if the wall(s) in ``wall`` are carved open.

        Args:
            wall: One of the direction bits (1/2/4/8).
        """
        return not self.walls & wall

    def open(self, wall: int) -> None:
        """Carve the given wall(s) open by clearing their bits.

        Args:
            wall: One of the direction bits (1/2/4/8).
        """
        self.walls &= ~wall

    def close(self, wall: int) -> None:
        """Close the given wall(s) by setting their bits.

        Args:
            wall: One of the direction bits (1/2/4/8).
        """
        self.walls |= wall


Grid = List[List[Cell]]

# (dx, dy) -> direction letter, used to turn a path into an N/E/S/W string.
DIR_BY_DELTA: Dict[Coord, str] = {
    (dx, dy): letter for letter, (dx, dy, _bh, _bt) in DIRS.items()
}


# ---------------------------------------------------------------------------
# 2. Obstacle: the "42" block-letter shape the maze is carved around
# ---------------------------------------------------------------------------

# Block-letter patterns for the "42" obstacle ("X" = a blocked maze cell).
DIGITS: Dict[str, List[str]] = {
    "4": [
        "X X",
        "X X",
        "XXX",
        "  X",
        "  X",
    ],
    "2": [
        "XXX",
        "  X",
        "XXX",
        "X  ",
        "XXX",
    ],
}


def obstacle_cells(width: int, height: int, text: str = "42") -> Set[Coord]:
    """Compute the cells blocked out to spell ``text`` in the maze centre.

    The block-letter ``text`` is centred on the grid; the returned cells are
    treated as a solid obstacle the generator must carve around. If the grid
    is too small to hold the pattern (with a one-cell margin so the maze can
    still wrap around it), an empty set is returned and the caller is expected
    to print an error and carry on without the obstacle.

    Args:
        width: Grid width (the x axis).
        height: Grid height (the y axis).
        text: Characters to draw; each must have an entry in ``DIGITS``.

    Returns:
        The set of ``(x, y)`` positions that form the obstacle, or an empty
        set if the maze is too small to fit it.
    """
    pattern: List[str] = []
    for row in range(len(DIGITS[text[0]])):
        pattern.append(" ".join(DIGITS[char][row] for char in text))

    pat_h = len(pattern)
    pat_w = len(pattern[0])
    if width < pat_w + 2 or height < pat_h + 2:
        return set()

    off_x = (width - pat_w) // 2
    off_y = (height - pat_h) // 2

    blocked: Set[Coord] = set()
    for row in range(pat_h):
        for col in range(pat_w):
            if pattern[row][col] == "X":
                blocked.add((off_x + col, off_y + row))
    return blocked


# ---------------------------------------------------------------------------
# 3. Generation: building perfect and imperfect mazes
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# 4. Solving: DFS/BFS pathfinding over the grid
# ---------------------------------------------------------------------------

def _reconstruct(came_from: Dict[Coord, Coord], entry: Coord,
                 exit_: Coord) -> List[Coord]:
    """Rebuild the entry-to-exit path from a search's parent map.

    Args:
        came_from: Maps each visited position to the one it was reached from.
        entry: The start position.
        exit_: The goal position.

    Returns:
        The list of positions from ``entry`` to ``exit_``, or empty if
        unreached.
    """
    if exit_ != entry and exit_ not in came_from:
        return []
    path: List[Coord] = [exit_]
    while path[-1] != entry:
        path.append(came_from[path[-1]])
    path.reverse()
    return path


def solve_dfs(grid: Grid, entry: Coord, exit_: Coord) -> List[Coord]:
    """Find a path from entry to exit with depth-first search.

    DFS explores as far as it can down each corridor before backtracking, so
    it returns *a* valid path (not necessarily the shortest one). It only
    steps through open passages, so obstacle cells are avoided automatically.

    Args:
        grid: The maze grid of :class:`Cell` objects.
        entry: Start position as ``(x, y)``.
        exit_: Goal position as ``(x, y)``.

    Returns:
        The list of positions from ``entry`` to ``exit_`` inclusive, or an
        empty list if no path exists.
    """
    stack: List[Coord] = [entry]
    visited: Set[Coord] = {entry}
    came_from: Dict[Coord, Coord] = {}

    while stack:
        x, y = stack.pop()
        if (x, y) == exit_:
            break
        for _direction, (dx, dy, bit_here, _bt) in DIRS.items():
            if not grid[y][x].is_open(bit_here):
                continue  # wall closed, cannot step this way
            nxt = (x + dx, y + dy)
            if nxt not in visited:
                visited.add(nxt)
                came_from[nxt] = (x, y)
                stack.append(nxt)

    return _reconstruct(came_from, entry, exit_)


def solve_bfs(grid: Grid, entry: Coord, exit_: Coord) -> List[Coord]:
    """Find the shortest path from entry to exit with breadth-first search.

    BFS expands cells in order of distance, so the first time it reaches the
    exit it has found a shortest path. It only steps through open passages,
    so obstacle cells are avoided automatically.

    Args:
        grid: The maze grid of :class:`Cell` objects.
        entry: Start position as ``(x, y)``.
        exit_: Goal position as ``(x, y)``.

    Returns:
        A shortest list of positions from ``entry`` to ``exit_`` inclusive, or
        an empty list if no path exists.
    """
    queue: Deque[Coord] = deque([entry])
    visited: Set[Coord] = {entry}
    came_from: Dict[Coord, Coord] = {}

    while queue:
        x, y = queue.popleft()
        if (x, y) == exit_:
            break
        for _direction, (dx, dy, bit_here, _bt) in DIRS.items():
            if not grid[y][x].is_open(bit_here):
                continue  # wall closed, cannot step this way
            nxt = (x + dx, y + dy)
            if nxt not in visited:
                visited.add(nxt)
                came_from[nxt] = (x, y)
                queue.append(nxt)

    return _reconstruct(came_from, entry, exit_)


def path_to_directions(path: List[Coord]) -> str:
    """Convert a list of positions into an N/E/S/W move string.

    Args:
        path: Positions from entry to exit, each adjacent to the next.

    Returns:
        One letter per step (``N``/``E``/``S``/``W``); empty for a 0/1-cell
        path.
    """
    letters: List[str] = []
    for (x, y), (nx, ny) in zip(path, path[1:]):
        letters.append(DIR_BY_DELTA[(nx - x, ny - y)])
    return "".join(letters)


# ---------------------------------------------------------------------------
# 5. Colours: ANSI palette for the overlay markers
# ---------------------------------------------------------------------------

# TEMP: ANSI colours used to draw the overlay markers.
LABEL_COLOR: str = "\033[34m"        # "42" obstacle (deep blue)
ENTRY_COLOR: str = "\033[32m"        # entry block (green)
EXIT_COLOR: str = "\033[31m"         # exit block (red)
PATH_COLOR: str = "\033[38;5;208m"   # solved path (orange)
COLOR_RESET: str = "\033[0m"


# ---------------------------------------------------------------------------
# 6. 2D render: turning a grid into block ASCII art
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# 7. Animation: frame-by-frame terminal playback
# ---------------------------------------------------------------------------

# TEMP: animation control codes and frame delays (seconds).
CLEAR_SCREEN: str = "\033[2J\033[H"
CURSOR_HOME: str = "\033[H"
HIDE_CURSOR: str = "\033[?25l"
SHOW_CURSOR: str = "\033[?25h"
GEN_DELAY: float = 0.02
SOLVE_DELAY: float = 0.04


def _draw(grid: Grid, entry: Coord, exit_: Coord, blocked: Set[Coord],
          path: Optional[List[Coord]], delay: float) -> None:
    """Redraw a single animation frame in place and pause briefly.

    Args:
        grid: The maze grid of :class:`Cell` objects.
        entry: Entry position, drawn as the green block.
        exit_: Exit position, drawn as the red block.
        blocked: Obstacle positions (the "42").
        path: Optional path/cell highlight for this frame.
        delay: Seconds to sleep after drawing.
    """
    sys.stdout.write(CURSOR_HOME)
    sys.stdout.write(render(grid, entry, exit_, blocked, path))
    sys.stdout.write("\n")
    sys.stdout.flush()
    if delay:
        time.sleep(delay)


def animate(width: int, height: int, entry: Coord, exit_: Coord,
            blocked: Set[Coord], perfect: bool) -> Grid:
    """Animate building the maze and then solving it, frame by frame.

    Args:
        width: Grid width.
        height: Grid height.
        entry: Entry position.
        exit_: Exit position.
        blocked: Obstacle positions (the "42").
        perfect: If ``False``, loops are added after carving.

    Returns:
        The finished maze grid.
    """
    sys.stdout.write(HIDE_CURSOR + CLEAR_SCREEN)
    try:
        grid = generate(
            width, height, entry, blocked,
            lambda g, current: _draw(
                g, entry, exit_, blocked, [current], GEN_DELAY),
        )
        if not perfect:
            make_imperfect(grid, blocked)
            _draw(grid, entry, exit_, blocked, None, 0.0)

        solution = solve_bfs(grid, entry, exit_)
        for length in range(1, len(solution) + 1):
            _draw(grid, entry, exit_, blocked, solution[:length], SOLVE_DELAY)
        _draw(grid, entry, exit_, blocked, solution, 0.0)
    finally:
        sys.stdout.write(SHOW_CURSOR)
        sys.stdout.flush()
    return grid


# ---------------------------------------------------------------------------
# 8. File IO: reading config and writing the hex maze
# ---------------------------------------------------------------------------

def write_maze(filename: str, grid: Grid, entry: Coord, exit_: Coord,
               path: List[Coord]) -> None:
    """Write the maze to ``filename`` in the hexadecimal wall format.

    The file holds one hex digit per cell (rows line by line), then a blank
    line, then the entry coordinates, the exit coordinates and the shortest
    path as an N/E/S/W string. Every line ends with ``\\n``.

    Args:
        filename: Destination path.
        grid: The maze grid of :class:`Cell` objects.
        entry: Entry position as ``(x, y)``.
        exit_: Exit position as ``(x, y)``.
        path: Shortest entry-to-exit path used for the final line.

    Raises:
        OSError: If the file cannot be written.
    """
    with open(filename, "w", encoding="utf-8") as handle:
        for row in grid:
            handle.write("".join(format(cell.walls, "X") for cell in row)
                         + "\n")
        handle.write("\n")
        handle.write(f"{entry[0]},{entry[1]}\n")
        handle.write(f"{exit_[0]},{exit_[1]}\n")
        handle.write(path_to_directions(path) + "\n")


# Keys every configuration file must define.
MANDATORY_KEYS: Tuple[str, ...] = (
    "WIDTH", "HEIGHT", "ENTRY", "EXIT", "OUTPUT_FILE", "PERFECT",
)


@dataclass
class Config:
    """Validated maze configuration loaded from a config file.

    Attributes:
        width: Maze width in cells (the x axis).
        height: Maze height in cells (the y axis).
        entry: Entry position as ``(x, y)``.
        exit_: Exit position as ``(x, y)``.
        output_file: Path the hex maze is written to.
        perfect: Whether the maze must be perfect (single path).
        seed: Optional RNG seed for reproducibility.
    """

    width: int
    height: int
    entry: Coord
    exit_: Coord
    output_file: str
    perfect: bool
    seed: Optional[int]


def parse_coord(value: str) -> Coord:
    """Parse an ``"x,y"`` string into an ``(x, y)`` integer tuple.

    Args:
        value: Coordinate text such as ``"19, 14"`` (spaces are ignored).

    Returns:
        The parsed ``(x, y)`` position.

    Raises:
        ValueError: If ``value`` is not two comma-separated integers.
    """
    parts = value.split(",")
    if len(parts) != 2:
        raise ValueError(f"expected 'x,y', got {value!r}")
    return int(parts[0].strip()), int(parts[1].strip())


def _validate(config: Config) -> None:
    """Check that a configuration describes a buildable maze.

    Args:
        config: The configuration to validate.

    Raises:
        ValueError: If the dimensions, entry or exit are invalid, or if entry
            or exit would fall inside the sealed '42' pattern.
    """
    if config.width < 1 or config.height < 1:
        raise ValueError("WIDTH and HEIGHT must be positive")
    for name, (cx, cy) in (("ENTRY", config.entry), ("EXIT", config.exit_)):
        if not (0 <= cx < config.width and 0 <= cy < config.height):
            raise ValueError(f"{name} {cx},{cy} is outside the maze bounds")
    if config.entry == config.exit_:
        raise ValueError("ENTRY and EXIT must be different cells")

    blocked = obstacle_cells(config.width, config.height, "42")
    for name, cell in (("ENTRY", config.entry), ("EXIT", config.exit_)):
        if cell in blocked:
            raise ValueError(
                f"{name} {cell[0]},{cell[1]} cannot be inside the '42' "
                "pattern (the cell would be sealed off)")


def load_config(path: str) -> Config:
    """Read and validate a maze configuration file.

    The file holds one ``KEY=VALUE`` pair per line. Blank lines and lines
    starting with ``#`` are ignored. All keys in ``MANDATORY_KEYS`` must be
    present; an optional ``SEED`` key makes generation reproducible.

    Args:
        path: Path to the configuration file.

    Returns:
        The validated :class:`Config`.

    Raises:
        OSError: If the file cannot be read.
        ValueError: If a line is malformed, a key is missing or invalid.
    """
    raw: Dict[str, str] = {}
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                raise ValueError(f"expected KEY=VALUE, got {line!r}")
            key, value = line.split("=", 1)
            raw[key.strip()] = value.strip()

    missing = [key for key in MANDATORY_KEYS if key not in raw]
    if missing:
        raise ValueError(f"missing mandatory keys: {', '.join(missing)}")

    try:
        config = Config(
            width=int(raw["WIDTH"]),
            height=int(raw["HEIGHT"]),
            entry=parse_coord(raw["ENTRY"]),
            exit_=parse_coord(raw["EXIT"]),
            output_file=raw["OUTPUT_FILE"],
            perfect=raw["PERFECT"].strip().lower() in ("true", "1", "yes"),
            seed=int(raw["SEED"]) if "SEED" in raw else None,
        )
    except ValueError as err:
        raise ValueError(f"invalid value in config: {err}") from err

    _validate(config)
    return config


# ---------------------------------------------------------------------------
# 9. Entry point: wiring it all together
# ---------------------------------------------------------------------------

def build_maze(config: Config,
               blocked: Set[Coord], animated: bool) -> Grid:
    """Generate the maze for ``config``, optionally animating the build.

    Args:
        config: The validated configuration.
        blocked: Obstacle positions (the "42").
        animated: Whether to animate generation and solving.

    Returns:
        The finished maze grid.
    """
    if animated:
        return animate(config.width, config.height, config.entry,
                       config.exit_, blocked, config.perfect)
    grid = generate(config.width, config.height, config.entry, blocked)
    if not config.perfect:
        make_imperfect(grid, blocked)
    return grid


def main() -> None:
    """Load the config, build and solve the maze, then write/print it."""
    flags = {arg for arg in sys.argv[1:] if arg.startswith("-")}
    positional = [arg for arg in sys.argv[1:] if not arg.startswith("-")]
    path = positional[0] if positional else "config.txt"

    try:
        config = load_config(path)
    except (OSError, ValueError) as err:
        print(f"Config error: {err}", file=sys.stderr)
        return

    if config.seed is not None:
        random.seed(config.seed)

    blocked = obstacle_cells(config.width, config.height, "42")
    if not blocked:
        print(
            "Warning: maze too small for the '42' pattern; "
            "drawing without it.",
            file=sys.stderr,
        )

    animated = "--static" not in flags
    grid = build_maze(config, blocked, animated)

    solution = solve_bfs(grid, config.entry, config.exit_)
    if not solution:
        print("Warning: no path from entry to exit.", file=sys.stderr)

    if not animated:
        print(render(grid, config.entry, config.exit_, blocked, solution))

    try:
        write_maze(config.output_file, grid, config.entry, config.exit_,
                   solution)
    except OSError as err:
        print(f"Could not write '{config.output_file}': {err}",
              file=sys.stderr)

    if is_perfect(grid, blocked):
        print("The maze is perfect.")
    else:
        print("The maze is not perfect.")


if __name__ == "__main__":
    main()
