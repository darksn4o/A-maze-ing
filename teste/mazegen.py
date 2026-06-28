"""mazegen -- a small, dependency-free, reusable maze generator.

This single module is the reusable core of the *A-Maze-ing* project. It can be
installed with ``pip`` (see ``pyproject.toml``) and imported by any other
project that needs to generate, inspect and solve mazes.

Wall encoding
-------------
Every cell stores a 4-bit integer. **A set bit means the wall is closed.**

============  =====  =============
Direction     Bit    Value
============  =====  =============
North          0     ``1``
East           1     ``2``
South          2     ``4``
West           3     ``8``
============  =====  =============

A fully closed cell is therefore ``0xF`` (15) and a fully open one is ``0``.
This is exactly the convention used by the project's output file, so the
structure exposed here maps directly onto the hexadecimal dump.

Coordinates
-----------
Cells are addressed as ``(x, y)`` with ``x`` the column (``0`` on the left,
growing East) and ``y`` the row (``0`` on top, growing South). ``grid[y][x]``
holds the wall mask of a cell.

Quick start
-----------
>>> from mazegen import MazeGenerator
>>> maze = MazeGenerator(20, 15, entry=(0, 0), exit=(19, 14), seed=42)
>>> maze.generate()                       # doctest: +ELLIPSIS
<mazegen.MazeGenerator object at ...>
>>> maze.grid[0][0]                        # wall mask of the entry cell
14
>>> "".join(maze.solution)[:6]             # first moves of the shortest path
'SESESE'

Pass custom parameters
----------------------
``width``/``height`` set the size, ``seed`` makes the result reproducible,
``perfect=False`` adds loops (imperfect maze) and ``draw_42=False`` disables
the embedded "42" pattern::

    maze = MazeGenerator(40, 30, perfect=False, seed=7, draw_42=True)
    maze.generate()

Access the structure and the solution
------------------------------------
``maze.grid`` is the raw ``height x width`` matrix of wall masks,
``maze.solution`` is the shortest path from entry to exit as a list of
``"N"/"E"/"S"/"W"`` letters, and ``maze.path_cells()`` returns that same path
as ``(x, y)`` coordinates.
"""

from __future__ import annotations

import random
from collections import deque
from typing import Callable, Iterator, Optional

__all__ = ["MazeGenerator", "MazeError", "N", "E", "S", "W"]
__version__ = "1.0.0"

# Called after every carving step, e.g. to animate the generation.
StepCallback = Optional[Callable[[], None]]

# Wall bit flags. A set bit means the wall is *closed*.
N: int = 1
E: int = 2
S: int = 4
W: int = 8

# Movement vector applied to (x, y) when crossing each wall.
_DELTAS: dict[int, tuple[int, int]] = {
    N: (0, -1),
    E: (1, 0),
    S: (0, 1),
    W: (-1, 0),
}
# The wall a neighbour shares with us (its side of the same wall).
_OPPOSITE: dict[int, int] = {N: S, E: W, S: N, W: E}
# Letter used in the textual path.
_LETTER: dict[int, str] = {N: "N", E: "E", S: "S", W: "W"}

Cell = tuple[int, int]


class MazeError(Exception):
    """Raised when the generator is given invalid or impossible parameters."""


# 5x3 bitmaps of the digits "4" and "2" used to draw the mandatory pattern.
_DIGITS: dict[str, list[str]] = {
    "4": [
        "101",
        "101",
        "111",
        "001",
        "001",
    ],
    "2": [
        "111",
        "001",
        "111",
        "100",
        "111",
    ],
}
# Size of the "42" stencil: two 3-wide digits plus a 1-cell gap.
_PATTERN_W: int = 3 + 1 + 3
_PATTERN_H: int = 5


class MazeGenerator:
    """Generate, inspect and solve a rectangular maze.

    Args:
        width: Number of cells per row (must be >= 1).
        height: Number of cells per column (must be >= 1).
        entry: ``(x, y)`` coordinates of the entrance.
        exit: ``(x, y)`` coordinates of the exit. Defaults to the
            bottom-right cell when ``None``.
        perfect: When ``True`` the maze is a spanning tree (exactly one path
            between any two cells). When ``False`` extra passages are carved to
            create loops, while keeping corridors at most two cells wide.
        seed: Optional seed for the internal random generator. The same seed
            and parameters always produce the same maze.
        draw_42: When ``True`` a "42" made of fully closed cells is embedded in
            the centre. It is silently skipped (with ``pattern_skipped`` set)
            if the maze is too small to hold it.

    Raises:
        MazeError: If the parameters are invalid (non-positive size, entry or
            exit out of bounds, entry equal to exit).
    """

    def __init__(
        self,
        width: int,
        height: int,
        entry: Cell = (0, 0),
        exit: Optional[Cell] = None,
        *,
        perfect: bool = True,
        seed: Optional[int] = None,
        draw_42: bool = True,
    ) -> None:
        if width < 1 or height < 1:
            raise MazeError("width and height must be positive integers")
        self.width: int = width
        self.height: int = height
        self.entry: Cell = entry
        self.exit: Cell = exit if exit is not None else (width - 1, height - 1)
        self.perfect: bool = perfect
        self.seed: Optional[int] = seed
        self.draw_42: bool = draw_42
        self._rng: random.Random = random.Random(seed)
        # grid[y][x] is the bitmask of *closed* walls; start fully closed.
        self.grid: list[list[int]] = []
        self.reserved: set[Cell] = set()
        self.solution: list[str] = []
        self.pattern_skipped: bool = False
        self._validate_endpoints()

    # ------------------------------------------------------------------ #
    # Validation
    # ------------------------------------------------------------------ #
    def _validate_endpoints(self) -> None:
        """Check that entry and exit are distinct and inside the bounds."""
        for name, (x, y) in (("ENTRY", self.entry), ("EXIT", self.exit)):
            if not (0 <= x < self.width and 0 <= y < self.height):
                raise MazeError(f"{name} {(x, y)} is outside the maze bounds")
        if self.entry == self.exit:
            raise MazeError("ENTRY and EXIT must be different cells")

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def generate(self, on_step: StepCallback = None) -> "MazeGenerator":
        """Build the maze in place and return ``self``.

        Calling :meth:`generate` again reuses the same random stream, so each
        call produces a fresh maze (useful for a "re-generate" action) while
        the very first call after construction stays reproducible per ``seed``.

        Args:
            on_step: Optional zero-argument callback invoked after every wall
                is carved. The partially built maze is readable from
                :attr:`grid` inside the callback, which makes it possible to
                animate the generation.

        Returns:
            The generator itself, to allow call chaining.

        Raises:
            MazeError: If the carved maze is not fully connected.
        """
        self.grid = [[N | E | S | W for _ in range(self.width)]
                     for _ in range(self.height)]
        self.reserved = set()
        self.pattern_skipped = False
        if self.draw_42:
            self._place_pattern()
        self._carve_backtracker(on_step)
        if not self.perfect:
            self._add_loops(on_step=on_step)
        self._assert_connected()
        self.solution = self.solve()
        return self

    def solve(self) -> list[str]:
        """Return the shortest path from entry to exit.

        Uses a breadth-first search over open passages.

        Returns:
            The path as a list of ``"N"/"E"/"S"/"W"`` letters, or an empty
            list when no path exists.
        """
        start, goal = self.entry, self.exit
        came_from: dict[Cell, Optional[tuple[Cell, int]]] = {start: None}
        queue: deque[Cell] = deque([start])
        while queue:
            current = queue.popleft()
            if current == goal:
                break
            x, y = current
            for wall, nx, ny in self._neighbours(x, y):
                if self.grid[y][x] & wall:  # wall closed -> cannot pass
                    continue
                if (nx, ny) in came_from:
                    continue
                came_from[(nx, ny)] = (current, wall)
                queue.append((nx, ny))
        if goal not in came_from:
            return []
        path: list[str] = []
        node: Cell = goal
        step = came_from[node]
        while step is not None:
            parent, wall = step
            path.append(_LETTER[wall])
            node = parent
            step = came_from[node]
        path.reverse()
        return path

    def path_cells(self) -> list[Cell]:
        """Return the shortest path as a list of ``(x, y)`` coordinates."""
        x, y = self.entry
        cells: list[Cell] = [(x, y)]
        for letter in self.solution:
            wall = next(w for w, ltr in _LETTER.items() if ltr == letter)
            dx, dy = _DELTAS[wall]
            x, y = x + dx, y + dy
            cells.append((x, y))
        return cells

    # ------------------------------------------------------------------ #
    # Carving algorithm
    # ------------------------------------------------------------------ #
    def _carve_backtracker(self, on_step: StepCallback = None) -> None:
        """Carve a perfect maze with an iterative recursive backtracker."""
        start = self._start_cell()
        visited: set[Cell] = {start}
        stack: list[Cell] = [start]
        while stack:
            x, y = stack[-1]
            choices = [
                (wall, nx, ny)
                for wall, nx, ny in self._neighbours(x, y)
                if (nx, ny) not in visited and (nx, ny) not in self.reserved
            ]
            if not choices:
                stack.pop()
                continue
            wall, nx, ny = self._rng.choice(choices)
            self._open_wall(x, y, wall, nx, ny)
            visited.add((nx, ny))
            stack.append((nx, ny))
            if on_step is not None:
                on_step()

    def _add_loops(self, ratio: float = 0.08,
                   on_step: StepCallback = None) -> None:
        """Remove some internal walls to make the maze imperfect.

        Walls are only removed when doing so does not create a 3x3 fully open
        area, keeping corridors at most two cells wide.

        Args:
            ratio: Fraction of the still-closed internal walls to try to open.
        """
        candidates: list[tuple[int, int, int, int, int]] = []
        for y in range(self.height):
            for x in range(self.width):
                if (x, y) in self.reserved:
                    continue
                for wall, nx, ny in self._neighbours(x, y):
                    if wall not in (E, S):  # count each wall once
                        continue
                    if (nx, ny) in self.reserved:
                        continue
                    if self.grid[y][x] & wall:
                        candidates.append((x, y, wall, nx, ny))
        self._rng.shuffle(candidates)
        target = int(len(candidates) * ratio)
        removed = 0
        for x, y, wall, nx, ny in candidates:
            if removed >= target:
                break
            self._open_wall(x, y, wall, nx, ny)
            if self._creates_open_3x3(x, y) or self._creates_open_3x3(nx, ny):
                self.grid[y][x] |= wall
                self.grid[ny][nx] |= _OPPOSITE[wall]
            else:
                removed += 1
                if on_step is not None:
                    on_step()

    # ------------------------------------------------------------------ #
    # The mandatory "42" pattern
    # ------------------------------------------------------------------ #
    def _place_pattern(self) -> None:
        """Reserve the centred "42" cells, keeping them fully closed.

        If the maze is too small to host the stencil, the pattern is skipped
        and :attr:`pattern_skipped` is set instead of raising.
        """
        if self.width < _PATTERN_W + 2 or self.height < _PATTERN_H + 2:
            self.pattern_skipped = True
            return
        off_x = (self.width - _PATTERN_W) // 2
        off_y = (self.height - _PATTERN_H) // 2
        columns = ["4"] * 1 + ["gap"] + ["2"] * 1
        for row in range(_PATTERN_H):
            cursor = off_x
            for token in columns:
                if token == "gap":
                    cursor += 1
                    continue
                bitmap = _DIGITS[token][row]
                for col, bit in enumerate(bitmap):
                    if bit == "1":
                        cell = (cursor + col, off_y + row)
                        if cell not in (self.entry, self.exit):
                            self.reserved.add(cell)
                cursor += len(bitmap)

    # ------------------------------------------------------------------ #
    # Geometry helpers
    # ------------------------------------------------------------------ #
    def _neighbours(self, x: int, y: int) -> Iterator[tuple[int, int, int]]:
        """Yield ``(wall, nx, ny)`` for every in-bounds neighbour of a cell."""
        for wall, (dx, dy) in _DELTAS.items():
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.width and 0 <= ny < self.height:
                yield wall, nx, ny

    def _open_wall(self, x: int, y: int, wall: int, nx: int, ny: int) -> None:
        """Open ``wall`` between ``(x, y)`` and its neighbour ``(nx, ny)``."""
        self.grid[y][x] &= ~wall
        self.grid[ny][nx] &= ~_OPPOSITE[wall]

    def _start_cell(self) -> Cell:
        """Pick a start cell: the entry, or the first non-reserved cell."""
        if self.entry not in self.reserved:
            return self.entry
        for y in range(self.height):
            for x in range(self.width):
                if (x, y) not in self.reserved:
                    return (x, y)
        raise MazeError("every cell is reserved by the pattern")

    def _creates_open_3x3(self, x: int, y: int) -> bool:
        """Return ``True`` if a 3x3 open block touches cell ``(x, y)``."""
        for by in range(y - 2, y + 1):
            for bx in range(x - 2, x + 1):
                if self._window_is_open(bx, by):
                    return True
        return False

    def _window_is_open(self, bx: int, by: int) -> bool:
        """Return ``True`` if the 3x3 block at ``(bx, by)`` is fully open."""
        if bx < 0 or by < 0 or bx + 2 >= self.width or by + 2 >= self.height:
            return False
        for dy in range(3):
            for dx in range(2):
                if self.grid[by + dy][bx + dx] & E:
                    return False
        for dy in range(2):
            for dx in range(3):
                if self.grid[by + dy][bx + dx] & S:
                    return False
        return True

    def _assert_connected(self) -> None:
        """Ensure every non-reserved cell is reachable from the start."""
        start = self._start_cell()
        seen: set[Cell] = {start}
        queue: deque[Cell] = deque([start])
        while queue:
            x, y = queue.popleft()
            for wall, nx, ny in self._neighbours(x, y):
                if self.grid[y][x] & wall:
                    continue
                if (nx, ny) not in seen:
                    seen.add((nx, ny))
                    queue.append((nx, ny))
        free = self.width * self.height - len(self.reserved)
        if len(seen) != free:
            raise MazeError("generated maze is not fully connected")
