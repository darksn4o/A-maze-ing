"""Block 2 - Obstacle: the "42" block-letter shape the maze is carved around.

Holds the block-letter pixel art for each digit and computes which grid
positions must stay sealed so the finished maze spells "42" in its centre.
"""

from typing import Dict, List, Set

from .data_model import Coord

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
