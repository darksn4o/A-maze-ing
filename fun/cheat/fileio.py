"""Block 8 - File IO: reading config and writing the hex maze.

Reads and validates a ``KEY=VALUE`` config file into a :class:`Config`, and
serialises a finished maze to the hexadecimal wall format used downstream.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .data_model import Coord, Grid
from .obstacle import obstacle_cells
from .solving import path_to_directions


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
