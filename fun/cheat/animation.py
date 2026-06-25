"""Block 7 - Animation: frame-by-frame terminal playback.

Drives the generator's ``on_step`` callback and the solver to repaint the
maze in place, so building and solving play out as a live animation in the
terminal.
"""

import sys
import time
from typing import List, Optional, Set

from .data_model import Coord, Grid
from .generation import generate, make_imperfect
from .render import render
from .solving import solve_bfs

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
