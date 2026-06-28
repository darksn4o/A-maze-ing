"""Unit tests for the reusable :mod:`mazegen` module."""

from __future__ import annotations

import pytest

from mazegen import E, MazeError, MazeGenerator, N, S, W

_OPPOSITE = {N: S, S: N, E: W, W: E}
_DELTAS = {N: (0, -1), S: (0, 1), E: (1, 0), W: (-1, 0)}


def test_invalid_size() -> None:
    """Non-positive dimensions are rejected."""
    with pytest.raises(MazeError):
        MazeGenerator(0, 5)


def test_endpoints_out_of_bounds() -> None:
    """An exit outside the grid is rejected."""
    with pytest.raises(MazeError):
        MazeGenerator(5, 5, exit=(5, 5))


def test_same_entry_exit() -> None:
    """Entry equal to exit is rejected."""
    with pytest.raises(MazeError):
        MazeGenerator(5, 5, entry=(1, 1), exit=(1, 1))


def test_reproducible_with_seed() -> None:
    """Same seed and parameters give an identical maze."""
    a = MazeGenerator(15, 12, seed=123).generate()
    b = MazeGenerator(15, 12, seed=123).generate()
    assert a.grid == b.grid
    assert a.solution == b.solution


def test_borders_are_closed() -> None:
    """All external borders keep their walls closed."""
    maze = MazeGenerator(12, 9, seed=1).generate()
    for x in range(maze.width):
        assert maze.grid[0][x] & N
        assert maze.grid[maze.height - 1][x] & S
    for y in range(maze.height):
        assert maze.grid[y][0] & W
        assert maze.grid[y][maze.width - 1] & E


def test_walls_are_coherent() -> None:
    """Two neighbouring cells always agree on their shared wall."""
    maze = MazeGenerator(20, 16, seed=7, perfect=False).generate()
    for y in range(maze.height):
        for x in range(maze.width):
            for wall, (dx, dy) in _DELTAS.items():
                nx, ny = x + dx, y + dy
                if 0 <= nx < maze.width and 0 <= ny < maze.height:
                    here = bool(maze.grid[y][x] & wall)
                    there = bool(maze.grid[ny][nx] & _OPPOSITE[wall])
                    assert here == there


def test_solution_is_walkable() -> None:
    """The reported path actually leads from entry to exit through openings."""
    maze = MazeGenerator(18, 14, seed=5).generate()
    x, y = maze.entry
    letter_to_wall = {"N": N, "E": E, "S": S, "W": W}
    for letter in maze.solution:
        wall = letter_to_wall[letter]
        assert not (maze.grid[y][x] & wall)  # must be open to move
        dx, dy = _DELTAS[wall]
        x, y = x + dx, y + dy
    assert (x, y) == maze.exit


def test_perfect_has_no_open_2x2() -> None:
    """A perfect maze (spanning tree) cannot contain a 2x2 open block."""
    maze = MazeGenerator(20, 20, seed=9, draw_42=False).generate()
    for y in range(maze.height - 1):
        for x in range(maze.width - 1):
            open_right = not (maze.grid[y][x] & E)
            open_down = not (maze.grid[y][x] & S)
            open_right_down = not (maze.grid[y + 1][x] & E)
            open_down_right = not (maze.grid[y][x + 1] & S)
            assert not (open_right and open_down
                        and open_right_down and open_down_right)


def test_no_open_3x3_when_imperfect() -> None:
    """Even with loops, no 3x3 fully open area is created."""
    maze = MazeGenerator(25, 25, seed=3, perfect=False).generate()
    for by in range(maze.height - 2):
        for bx in range(maze.width - 2):
            full = True
            for dy in range(3):
                for dx in range(2):
                    if maze.grid[by + dy][bx + dx] & E:
                        full = False
            for dy in range(2):
                for dx in range(3):
                    if maze.grid[by + dy][bx + dx] & S:
                        full = False
            assert not full


def test_pattern_reserved_cells_are_closed() -> None:
    """Every reserved '42' cell stays fully closed and isolated."""
    maze = MazeGenerator(30, 20, seed=2, draw_42=True).generate()
    assert maze.reserved
    for (x, y) in maze.reserved:
        assert maze.grid[y][x] == (N | E | S | W)


def test_pattern_skipped_when_too_small() -> None:
    """A tiny maze flags the pattern as skipped instead of crashing."""
    maze = MazeGenerator(5, 5, seed=1, draw_42=True).generate()
    assert maze.pattern_skipped is True
    assert not maze.reserved


def test_solution_endpoints() -> None:
    """The solved path starts at the entry and ends at the exit."""
    maze = MazeGenerator(16, 16, seed=4).generate()
    assert maze.solution
    assert maze.path_cells()[0] == maze.entry
    assert maze.path_cells()[-1] == maze.exit
