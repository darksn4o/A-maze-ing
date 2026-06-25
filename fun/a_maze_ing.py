"""A-Maze-ing entry point: ``python3 a_maze_ing.py config.txt``.

The maze generation, solving and rendering logic lives in the reusable
``turbo_claude_maze`` module; this file is the thin command-line front end.
"""

from turbo_claude_maze import main

if __name__ == "__main__":
    main()
