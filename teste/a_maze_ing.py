#!/usr/bin/env python3
"""A-Maze-ing -- command line entry point.

Usage::

    python3 a_maze_ing.py config.txt

Reads the maze options from the configuration file, generates the maze, writes
the hexadecimal output file and opens the interactive terminal display.
"""

from __future__ import annotations

import sys

from mazegen import MazeError, MazeGenerator

from app.config import ConfigError, load_config
from app.display import DEFAULT_FRAME_DELAY, TerminalDisplay
from app.output import OutputError


def build_display(config_path: str) -> TerminalDisplay:
    """Load a config and build the (not yet generated) terminal display.

    Generation and output writing happen in :meth:`TerminalDisplay.start`, so
    the first maze can be animated.

    Args:
        config_path: Path to the configuration file.

    Returns:
        A ready-to-run :class:`TerminalDisplay`.

    Raises:
        ConfigError: On any configuration problem.
        MazeError: On any invalid maze parameter.
    """
    config = load_config(config_path)
    maze = MazeGenerator(
        width=config.width,
        height=config.height,
        entry=config.entry,
        exit=config.exit,
        perfect=config.perfect,
        seed=config.seed,
        draw_42=config.draw_42,
    )
    return TerminalDisplay(
        maze,
        config.output_file,
        animate=config.animate,
        frame_delay=DEFAULT_FRAME_DELAY / config.animation_speed,
    )


def main(argv: list[str]) -> int:
    """Program entry point.

    Args:
        argv: Command line arguments (excluding the program name).

    Returns:
        ``0`` on success, ``1`` on any handled error.
    """
    if len(argv) != 1:
        print("usage: python3 a_maze_ing.py config.txt", file=sys.stderr)
        return 1
    try:
        build_display(argv[0]).start()
    except (ConfigError, MazeError, OutputError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\ninterrupted.", file=sys.stderr)
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
