"""Interactive terminal (ASCII/ANSI) rendering of a maze."""

from __future__ import annotations

import sys
import time
from typing import Callable, Optional

from mazegen import E, MazeGenerator, N, S, W

from app.output import write_output

RESET = "\033[0m"
CLEAR = "\033[2J\033[H"
HIDE_CURSOR = "\033[?25l"
SHOW_CURSOR = "\033[?25h"

# Pause between two animation frames at speed 1.0 (seconds).
DEFAULT_FRAME_DELAY = 0.012

# Pixel kinds used by the canvas before colouring.
_OPEN = 0
_WALL = 1
_ENTRY = 2
_EXIT = 3
_PATH = 4
_PATTERN = 5         # interior of a "42" cell
_PATTERN_BORDER = 6  # walls of a "42" cell

# Rotatable wall colour palette (xterm-256 codes).
_WALL_COLOURS = [15, 11, 51, 46, 201, 208]
_KIND_COLOURS = {
    _ENTRY: 201,           # magenta
    _EXIT: 196,            # red
    _PATH: 45,             # cyan
    _PATTERN: 19,          # deep blue (42 interior)
    _PATTERN_BORDER: 15,   # white (42 borders)
}


def _block(colour: Optional[int]) -> str:
    """Return a two-character coloured block, or blank space when open."""
    if colour is None:
        return "  "
    return f"\033[48;5;{colour}m  {RESET}"


class TerminalDisplay:
    """Render a maze in the terminal and handle the user interaction loop.

    Args:
        maze: A maze to display (generated lazily by :meth:`start`).
        output_file: Path rewritten whenever the maze is re-generated, so the
            file stays in sync with what is shown. ``None`` disables rewriting.
        animate: Animate the carving while generating. Automatically disabled
            when stdout is not a terminal.
        frame_delay: Seconds paused between two animation frames.
        frame_step: Number of carving steps between two drawn frames (a larger
            value makes a big maze animate faster).
    """

    def __init__(self, maze: MazeGenerator,
                 output_file: Optional[str] = None,
                 animate: bool = False,
                 frame_delay: float = DEFAULT_FRAME_DELAY,
                 frame_step: int = 1) -> None:
        self.maze = maze
        self.output_file = output_file
        self.animate = animate and sys.stdout.isatty()
        self.frame_delay = frame_delay
        self.frame_step = max(1, frame_step)
        self.show_path = True
        self.colour_index = 0

    # ------------------------------------------------------------------ #
    # Rendering
    # ------------------------------------------------------------------ #
    def _build_canvas(self) -> list[list[int]]:
        """Build the ``(2H+1) x (2W+1)`` matrix of pixel kinds."""
        maze = self.maze
        rows, cols = 2 * maze.height + 1, 2 * maze.width + 1
        canvas = [[_OPEN] * cols for _ in range(rows)]
        for r in range(0, rows, 2):
            for c in range(0, cols, 2):
                canvas[r][c] = _WALL  # corner posts
        for y in range(maze.height):
            for x in range(maze.width):
                mask = maze.grid[y][x]
                cy, cx = 2 * y + 1, 2 * x + 1
                if mask & N:
                    canvas[cy - 1][cx] = _WALL
                if mask & S:
                    canvas[cy + 1][cx] = _WALL
                if mask & W:
                    canvas[cy][cx - 1] = _WALL
                if mask & E:
                    canvas[cy][cx + 1] = _WALL
        self._overlay_pattern(canvas)
        if self.show_path:
            self._overlay_path(canvas)
        self._overlay_endpoints(canvas)
        return canvas

    def _overlay_pattern(self, canvas: list[list[int]]) -> None:
        """Draw the reserved "42" cells: white walls, red interior."""
        for (x, y) in self.maze.reserved:
            cy, cx = 2 * y + 1, 2 * x + 1
            for r in range(2 * y, 2 * y + 3):
                for c in range(2 * x, 2 * x + 3):
                    if r == cy and c == cx:
                        canvas[r][c] = _PATTERN          # interior (red)
                    else:
                        canvas[r][c] = _PATTERN_BORDER   # walls (white)

    def _overlay_path(self, canvas: list[list[int]]) -> None:
        """Draw the shortest path, including the gaps between path cells."""
        cells = self.maze.path_cells()
        for (x, y) in cells:
            canvas[2 * y + 1][2 * x + 1] = _PATH
        for (ax, ay), (bx, by) in zip(cells, cells[1:]):
            canvas[ay + by + 1][ax + bx + 1] = _PATH

    def _overlay_endpoints(self, canvas: list[list[int]]) -> None:
        """Mark the entry and exit cells on top of everything else."""
        ex, ey = self.maze.entry
        xx, xy = self.maze.exit
        canvas[2 * ey + 1][2 * ex + 1] = _ENTRY
        canvas[2 * xy + 1][2 * xx + 1] = _EXIT

    def render(self) -> str:
        """Return the maze as a coloured multi-line string."""
        wall_colour = _WALL_COLOURS[self.colour_index % len(_WALL_COLOURS)]
        canvas = self._build_canvas()
        lines: list[str] = []
        for row in canvas:
            pixels: list[str] = []
            for kind in row:
                if kind == _OPEN:
                    pixels.append(_block(None))
                elif kind == _WALL:
                    pixels.append(_block(wall_colour))
                else:
                    pixels.append(_block(_KIND_COLOURS[kind]))
            lines.append("".join(pixels))
        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    # Generation (with optional animation)
    # ------------------------------------------------------------------ #
    def _animation_callback(self) -> Callable[[], None]:
        """Build the per-step callback that draws animation frames."""
        counter = {"n": 0}

        def on_step() -> None:
            counter["n"] += 1
            if counter["n"] % self.frame_step:
                return
            print(CLEAR, end="")
            print(self.render())
            print("\ngenerating...", end="", flush=True)
            time.sleep(self.frame_delay)

        return on_step

    def _generate_and_save(self) -> None:
        """(Re)generate the maze, optionally animated, then save the output."""
        if self.animate:
            self.show_path = False
            print(HIDE_CURSOR, end="")
            try:
                self.maze.generate(on_step=self._animation_callback())
            finally:
                print(SHOW_CURSOR, end="")
            self.show_path = True
        else:
            self.maze.generate()
        if self.maze.pattern_skipped:
            print("warning: maze too small for the '42' pattern, "
                  "it was skipped.", file=sys.stderr)
        if self.output_file is not None:
            write_output(self.output_file, self.maze)

    def start(self) -> None:
        """Generate the first maze (animated) and run the interaction loop."""
        self._generate_and_save()
        self.run()

    # ------------------------------------------------------------------ #
    # Interaction loop
    # ------------------------------------------------------------------ #
    MENU = (
        "=== A-Maze-ing ===\n"
        "1. Re-generate a new maze\n"
        "2. Show/Hide path from entry to exit\n"
        "3. Rotate maze colors\n"
        "4. Quit\n"
        "Choice? (1-4): "
    )

    def _draw(self) -> None:
        """Clear the screen and print the maze followed by the menu."""
        print(CLEAR, end="")
        print(self.render())
        if self.maze.pattern_skipped:
            print("note: maze too small for the '42' pattern, it was skipped.")
        print()
        print(self.MENU, end="", flush=True)

    def run(self) -> None:
        """Run the interactive menu until the user quits.

        Handles ``Ctrl-C`` and end-of-input cleanly so the program never
        crashes on unexpected terminal conditions.
        """
        while True:
            self._draw()
            try:
                choice = input().strip()
            except (EOFError, KeyboardInterrupt):
                print()
                return
            if choice == "1":
                self._generate_and_save()
            elif choice == "2":
                self.show_path = not self.show_path
            elif choice == "3":
                self.colour_index += 1
            elif choice == "4":
                return
            # any other input simply redraws the menu
