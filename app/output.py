"""Serialization of a generated maze to the project's output file format."""

from __future__ import annotations

from mazegen import MazeGenerator


class OutputError(Exception):
    """Raised when the output file cannot be written."""


def render_output(maze: MazeGenerator) -> str:
    """Return the full textual dump of ``maze`` in the output file format.

    The layout is::

        <one hex digit per cell, one row per line>
        <empty line>
        <entry x,y>
        <exit x,y>
        <shortest path as N/E/S/W letters>

    Every line, including the last, ends with ``\\n``.

    Args:
        maze: A generated maze.

    Returns:
        The serialized maze as a single string.
    """
    lines: list[str] = []
    for row in maze.grid:
        lines.append("".join(format(cell, "X") for cell in row))
    lines.append("")  # mandatory empty separator line
    lines.append(f"{maze.entry[0]},{maze.entry[1]}")
    lines.append(f"{maze.exit[0]},{maze.exit[1]}")
    lines.append("".join(maze.solution))
    return "\n".join(lines) + "\n"


def write_output(path: str, maze: MazeGenerator) -> None:
    """Write ``maze`` to ``path`` using the output file format.

    Args:
        path: Destination file path.
        maze: A generated maze.

    Raises:
        OutputError: If the file cannot be written.
    """
    try:
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(render_output(maze))
    except OSError as exc:
        raise OutputError(f"cannot write {path}: {exc}") from exc
