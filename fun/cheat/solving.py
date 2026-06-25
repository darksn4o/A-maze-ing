"""Block 4 - Solving: DFS/BFS pathfinding over the grid.

Walks the open passages of a finished maze to find a route from entry to
exit, and turns a route into a compact N/E/S/W direction string.
"""

from collections import deque
from typing import Deque, Dict, List, Set

from .data_model import DIR_BY_DELTA, DIRS, Coord, Grid


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
