"""Block 9 - Entry point: wiring it all together.

Glues the other blocks into a runnable program: load the config, build and
solve the maze (animated or static), write the hex file and report whether
the result is perfect.
"""

import random
import sys
from typing import Set

from .animation import animate
from .data_model import Coord, Grid
from .fileio import Config, load_config, write_maze
from .generation import generate, is_perfect, make_imperfect
from .obstacle import obstacle_cells
from .render import render
from .solving import solve_bfs


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
