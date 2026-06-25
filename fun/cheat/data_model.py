"""Block 1 - Data model: the Cell object plus grid/coordinate types.

This is the foundation every other module builds on. It defines what a wall
bitmask means, how directions map to coordinate deltas and wall bits, and the
:class:`Cell` object that stores one cell's wall state.
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple

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

    ``walls`` is a bitmask: a set bit means that wall is closed, a clear bit
    means it is carved open. A freshly created cell starts fully walled in.

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


# A maze is a 2D grid (rows of cells) of Cell objects.
Grid = List[List[Cell]]

# (dx, dy) -> direction letter, used to turn a path into an N/E/S/W string.
DIR_BY_DELTA: Dict[Coord, str] = {
    (dx, dy): letter for letter, (dx, dy, _bh, _bt) in DIRS.items()
}
