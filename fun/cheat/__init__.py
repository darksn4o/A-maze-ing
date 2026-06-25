"""``cheat`` - the maze core, split block-by-block into one module each.

The single-file ``turbo_claude_maze.py`` is broken here into nine modules,
one per behavioural block, so each concern can be read in isolation:

    1. data_model  - the Cell object plus grid/coordinate types
    2. obstacle    - the "42" block-letter shape carved around
    3. generation  - building perfect and imperfect mazes
    4. solving     - DFS/BFS pathfinding over the grid
    5. colors      - ANSI palette for the overlay markers
    6. render      - turning a grid into block ASCII art
    7. animation   - frame-by-frame terminal playback
    8. fileio      - reading config and writing the hex maze
    9. app         - the entry point wiring it all together

See ``cheat/README.md`` for the exact behaviour of every function.

Run it with ``python -m cheat [config.txt] [--static]``.
"""

from .data_model import ALL_WALLS, DIR_BY_DELTA, DIRS, Cell, Coord, Grid
from .obstacle import DIGITS, obstacle_cells
from .generation import (
    carve, generate, is_perfect, make_imperfect, new_grid,
    unvisited_neighbours,
)
from .solving import path_to_directions, solve_bfs, solve_dfs
from .render import render
from .animation import animate
from .fileio import Config, load_config, parse_coord, write_maze
from .app import build_maze, main

__all__ = [
    "ALL_WALLS", "DIRS", "DIR_BY_DELTA", "Cell", "Coord", "Grid",
    "DIGITS", "obstacle_cells",
    "new_grid", "unvisited_neighbours", "carve", "generate",
    "make_imperfect", "is_perfect",
    "solve_dfs", "solve_bfs", "path_to_directions",
    "render", "animate",
    "Config", "parse_coord", "load_config", "write_maze",
    "build_maze", "main",
]
