*This project has been created as part of the 42 curriculum by gnogueir, tsimao-g.*

# A-Maze-ing — *This is the way*

> Create your own maze generator and display its result.

---

## Description

**A-Maze-ing** is a maze generator written in Python. It reads a plain-text
configuration file, generates a random (but reproducible) maze, writes it to an
output file using a compact hexadecimal wall encoding, and offers an
interactive terminal display of the result.

The maze can be **perfect** (exactly one path between the entry and the exit, i.e.
a spanning tree) or **imperfect** (extra passages create loops, while corridors
never grow wider than two cells). Every maze hides a visible **"42"** drawn with
fully closed cells in its centre.

The generation logic lives in a **standalone, reusable module** (`mazegen.py`)
that can be installed with `pip` and imported by any other project.

---

## Table of contents

- [Quick start](#quick-start)
- [Behaviour](#behaviour) — *what the program does*
- [Logic](#logic) — *how the program works inside*
- [Configuration file format](#configuration-file-format)
- [Output file format](#output-file-format)
- [Reusable module (`mazegen`)](#reusable-module-mazegen)
- [Project layout](#project-layout)
- [Team & project management](#team--project-management)
- [Resources & use of AI](#resources--use-of-ai)

---

## Quick start

```bash
make install          # create .venv and install tooling + the mazegen package
make run              # generate from config.txt and open the display
# or directly:
python3 a_maze_ing.py config.txt
```

Other Make targets: `make test`, `make lint`, `make lint-strict`,
`make debug`, `make build`, `make clean`, `make fclean`.

Requires **Python 3.10+**.

---

## Behaviour

*This section describes **what** the program does, from the user's point of
view. The internal **how** is in [Logic](#logic).*

### Command line

```bash
python3 a_maze_ing.py config.txt
```

- `a_maze_ing.py` is the single entry point.
- `config.txt` is the only argument: the maze description (see
  [Configuration file format](#configuration-file-format)).

### What happens on a run

1. The configuration file is read and validated.
2. A maze is generated according to the configuration (the carving is animated
   on screen when `ANIMATE=True` and the output is a terminal).
3. The maze is written to `OUTPUT_FILE` in the hexadecimal format.
4. The interactive terminal display opens.

Every error (missing file, bad syntax, out-of-bounds entry/exit, impossible
parameters, write failure…) is caught and reported with a clear message on
`stderr`. **The program never crashes with a traceback** and returns a non-zero
exit code on failure.

### Interactive display

The maze is drawn with coloured blocks. The entry is **magenta**, the exit is
**red**, the shortest path is **cyan**, and the "42" pattern is shown as solid
blocks. A menu drives the interaction:

```
=== A-Maze-ing ===
1. Re-generate a new maze
2. Show/Hide path from entry to exit
3. Rotate maze colors
4. Quit
Choice? (1-4):
```

| Key | Action                                                          |
|-----|-----------------------------------------------------------------|
| `1` | Generate a brand-new maze and redraw it (also rewrites the file) |
| `2` | Toggle the shortest path overlay                                |
| `3` | Cycle through the wall colour palettes                           |
| `4` | Quit                                                            |

`Ctrl-C` and end-of-input also quit cleanly.

> If the maze is too small to hold the "42" pattern, a message is printed and
> the pattern is omitted (the rest of the maze is still produced normally).

---

## Logic

*This section describes **how** the maze is built and solved internally.*

### Data model

Each cell is a 4-bit integer; **a set bit means the wall is closed.**

| Bit | Direction | Value |
|-----|-----------|-------|
| 0   | North     | `1`   |
| 1   | East      | `2`   |
| 2   | South     | `4`   |
| 3   | West      | `8`   |

A fully closed cell is `0xF` (15), a fully open one is `0`. The maze is a
`height × width` matrix `grid[y][x]` of these masks. Coordinates are `(x, y)`
with `x` growing East and `y` growing South. This is **the same encoding used in
the output file**, so the structure maps directly onto the hex dump.

### Generation algorithm — *recursive backtracker*

Generation uses the **recursive backtracker** (randomized depth-first search,
DFS), implemented iteratively with an explicit stack to avoid recursion limits
on large mazes:

1. Start every cell fully closed (`0xF`).
2. Start from the entry cell, mark it visited.
3. From the current cell, pick a random unvisited neighbour, **open the wall
   between them** (clear the bit on *both* cells), move there and push it on the
   stack.
4. If there is no unvisited neighbour, pop the stack (backtrack).
5. Repeat until the stack is empty.

**Why this algorithm?** It is simple, fast (linear in the number of cells),
needs no extra data structures beyond a stack, and naturally produces a
**spanning tree** — a *perfect* maze with exactly one path between any two
cells. It also tends to produce long, winding corridors, which look great.

### Guarantees and how they are enforced

- **Full connectivity, no isolated cells** — the backtracker visits every
  non-reserved cell. A final BFS asserts that every reachable-by-design cell is
  actually reachable.
- **Closed external borders** — walls are never opened toward cells outside the
  grid, so the outer border stays closed automatically.
- **Coherent shared walls** — opening a wall always clears the matching bit on
  *both* neighbouring cells, so two adjacent cells can never disagree.
- **No area wider than 2 cells** — a perfect maze (spanning tree) has no cycles,
  hence no 2×2 open block at all. When `PERFECT=False`, loops are added by
  removing extra walls, but only if the removal does **not** create a 3×3 fully
  open area (checked on every candidate, otherwise reverted).
- **Reproducibility** — all randomness comes from a single seeded
  `random.Random`. Same seed + same parameters ⇒ identical maze.

### The "42" pattern

Two 5×3 bitmaps ("4" and "2") are stamped in the centre of the grid. The cells
that make up the digits are **reserved**: they are kept fully closed and
excluded from carving, so the generator routes corridors *around* them. They
are the only allowed "isolated" cells. If the grid is smaller than the stencil
(`7×5` plus a one-cell margin), the pattern is skipped and flagged.

### Solving — *breadth-first search*

The shortest path is found with a **BFS** from entry to exit over open passages.
BFS on an unweighted graph guarantees the shortest path. The path is returned
both as a list of `N/E/S/W` letters (for the output file) and as `(x, y)`
coordinates (for the display overlay).

---

## Configuration file format

One `KEY=VALUE` pair per line. Lines starting with `#` are comments; inline
comments after a value are also ignored. Keys are case-insensitive.

### Mandatory keys

| Key           | Description                       | Example               |
|---------------|-----------------------------------|-----------------------|
| `WIDTH`       | Maze width (cells, x axis)        | `WIDTH=20`            |
| `HEIGHT`      | Maze height (cells, y axis)       | `HEIGHT=15`           |
| `ENTRY`       | Entry coordinates `x,y`           | `ENTRY=0,0`           |
| `EXIT`        | Exit coordinates `x,y`            | `EXIT=19,14`          |
| `OUTPUT_FILE` | Output filename                   | `OUTPUT_FILE=maze.txt`|
| `PERFECT`     | Single path entry→exit?           | `PERFECT=True`        |

### Optional keys

| Key         | Description                                  | Default         |
|-------------|----------------------------------------------|-----------------|
| `SEED`      | Random seed for reproducibility              | random          |
| `PATTERN`   | Draw the centred "42" (`True`/`False`)       | `True`          |
| `ANIMATE`   | Animate the carving on screen (`True`/`False`) | `True`        |
| `ANIMATION_SPEED` | Speed multiplier (`<1` slower, `>1` faster) | `1.0`       |

A default `config.txt` is provided at the repository root.

---

## Output file format

The output file (`OUTPUT_FILE`) is written as:

```
<one hex digit per cell, one row per line>
            <-- single empty line
<entry x,y>
<exit x,y>
<shortest path, letters N E S W>
```

Each hex digit is the cell's mask of **closed** walls (see
[Logic → Data model](#logic)). For example `3` (binary `0011`) means North and
East are closed (South and West open); `A` (`1010`) means East and West closed.
Cells are stored row by row. Every line, including the last, ends with `\n`.

Example:

```
D539553955553D517913
97C693C69553C53C56AA
...
EC545457C547C6C5546E

0,0
19,14
EESENEEESENEEEEESEESSENEEENNESSSSWWWSWNWSSSENESSSWSESSESSENNNESSS
```

---

## Reusable module (`mazegen`)

The generation logic is a single class, `MazeGenerator`, in the standalone
`mazegen.py` module. It has **no third-party dependencies** and is packaged so
it can be installed with `pip` and reused in a future project.

### Build & install the package

```bash
make build                       # produces dist/mazegen-1.0.0-py3-none-any.whl
                                 #      and dist/mazegen-1.0.0.tar.gz
pip install dist/mazegen-1.0.0-py3-none-any.whl
```

### Instantiate and use it — basic example

```python
from mazegen import MazeGenerator

maze = MazeGenerator(20, 15, entry=(0, 0), exit=(19, 14), seed=42)
maze.generate()

print(maze.grid)          # the raw structure: list[list[int]] of wall masks
print(maze.solution)      # shortest path, e.g. ['E', 'E', 'S', ...]
```

### Pass custom parameters

```python
# Imperfect maze (with loops), no "42", fixed seed.
maze = MazeGenerator(
    width=40, height=30,
    entry=(0, 0), exit=(39, 29),
    perfect=False,
    seed=7,
    draw_42=False,
)
maze.generate()
```

### Access the structure and a solution

| Member               | What it gives                                          |
|----------------------|--------------------------------------------------------|
| `maze.grid`          | `height × width` matrix of wall masks (the structure)  |
| `maze.solution`      | shortest path as a list of `N/E/S/W` letters           |
| `maze.path_cells()`  | the same path as a list of `(x, y)` coordinates        |
| `maze.solve()`       | recompute and return the shortest path                 |
| `maze.reserved`      | the set of "42" cells                                  |

> The module grants access to the maze structure; note this is not necessarily
> the same layout as the output file (which is produced by the application
> layer in `app/output.py`).

---

## Project layout

```
.
├── a_maze_ing.py        # CLI entry point: config → generate → output → display
├── mazegen.py           # REUSABLE single-file module (MazeGenerator class)
├── config.txt           # default configuration
├── pyproject.toml       # builds the mazegen-* package
├── Makefile             # install / run / debug / lint / test / build / clean
├── requirements.txt     # dev tooling (flake8, mypy, pytest, build)
├── app/                 # application layer (not part of the package)
│   ├── config.py        #   parse & validate the config file
│   ├── output.py        #   serialize a maze to the output format
│   └── display.py       #   interactive terminal rendering
└── tests/               # pytest suite (not graded)
```

---

## Team & project management

**Roles**

| Member     | Focus                                                       |
|------------|-------------------------------------------------------------|
| gnogueir   | Generation & solving logic (`mazegen.py`), packaging        |
| tsimao-g   | Config parsing, output format, terminal display, tests      |

Both members reviewed each other's code and walked through the algorithms
together before the defence.

**Planning & evolution.** We first agreed on the wall-bit data model (so the
in-memory structure and the output file would match), then built the generator,
the output writer, and finally the interactive display. The "42" pattern and
the imperfect-maze loops were added once the perfect maze was solid.

**What worked well.** Choosing the bitmask encoding early made the output format
almost free. The recursive backtracker was quick to get right and gave good
mazes immediately.

**What could be improved.** A graphical MiniLibX (MLX) front-end and an
animated generation mode are natural next steps (both listed as bonuses).

**Tools used.** Python 3.12, `flake8` + `mypy` (strict) for quality, `pytest`
for tests, `build`/`setuptools` for packaging, `git` for collaboration.

---

## Resources & use of AI

**Classic references**

- Jamis Buck, *Mazes for Programmers* — the recursive backtracker algorithm.
- Wikipedia: [Maze generation algorithm](https://en.wikipedia.org/wiki/Maze_generation_algorithm).
- Spanning trees & graph connectivity (perfect mazes ⇔ spanning trees).
- BFS for shortest paths on unweighted graphs.

**How AI was used.** AI assistance was used to *explore* options and to draft
boilerplate, then everything was reviewed, tested and adapted by us:

- Brainstorming maze-generation approaches and their trade-offs (we chose the
  recursive backtracker for its simplicity and perfect-maze guarantee).
- Drafting docstrings and the Makefile skeleton.
- Suggesting the 3×3-open-area check strategy for the imperfect mode.

All algorithmic decisions, the data model, and the final code are ours: we can
explain and justify every part of the project.

---

## Bonuses implemented

- **Imperfect mazes** with loops while respecting the 2-cell corridor limit.
- **Animated generation** — the carving is drawn step by step on startup and on
  every re-generate (`ANIMATE` key; auto-disabled when output is piped). It is
  powered by the `on_step` callback of `MazeGenerator.generate()`, so the
  reusable module exposes the hook without depending on the display.
