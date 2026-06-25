# `cheat/` — the maze core, one block per file

This package is `turbo_claude_maze.py` split into nine modules, one per
behavioural block. Same logic, same output — just separated so each concern
reads on its own. Modules only import from the blocks *above* them, so the
dependency arrows all point one way (no cycles):

```
data_model ── obstacle ── generation ── solving ── colors ── render ── animation ── fileio ── app
   (1)          (2)          (3)          (4)        (5)        (6)         (7)         (8)      (9)
```

Run it with:

```bash
python -m cheat config.txt          # animated build + solve
python -m cheat config.txt --static # one static frame, no animation
```

The wall bitmask, shared by every block: each cell is an integer 0–15. A
**set** bit means that wall is **closed**.

| bit | value | side  |
|-----|-------|-------|
| 0   | 1     | North |
| 1   | 2     | East  |
| 2   | 4     | South |
| 3   | 8     | West  |

A new cell is `0xF` (all four closed). Carving = clearing bits.

---

## 1. `data_model.py` — the Cell object and shared types

The vocabulary every other block speaks.

- **`ALL_WALLS = 0xF`** — the "all four walls closed" bitmask; the default
  state of a fresh cell.
- **`DIRS`** — maps each direction letter to `(dx, dy, bit_here, bit_there)`.
  `dx, dy` is the coordinate step (note `y` grows **downward**); `bit_here` is
  the wall to clear in the current cell and `bit_there` is the *matching* wall
  in the neighbour. The pairing is what keeps both sides of a shared wall in
  agreement (e.g. stepping North clears my bit 1 and the neighbour's bit 4).
- **`Coord`** — type alias for an `(x, y)` position tuple.
- **`Cell`** — a dataclass wrapping one cell's `walls` bitmask, with three
  methods that replace raw bit-twiddling:
  - **`is_open(wall)`** → `True` if those wall bits are clear (carved open).
  - **`open(wall)`** → clears the bits (`walls &= ~wall`): carve the wall.
  - **`close(wall)`** → sets the bits (`walls |= wall`): seal the wall.
- **`Grid`** — type alias for `List[List[Cell]]` (rows of cells).
- **`DIR_BY_DELTA`** — the reverse of `DIRS`: maps `(dx, dy)` back to its
  letter, used to turn a path into an N/E/S/W string.

## 2. `obstacle.py` — the "42" shape

- **`DIGITS`** — block-letter pixel art for `"4"` and `"2"`, five rows tall,
  where `"X"` marks a cell that must stay sealed.
- **`obstacle_cells(width, height, text="42")`** — builds the full pattern by
  joining each digit's rows with a one-column gap, centres it on the grid, and
  returns the set of `(x, y)` positions the `"X"`s land on. **If the grid is
  too small** to hold the pattern plus a one-cell margin, it returns an **empty
  set** (the caller warns and carries on without the obstacle).

## 3. `generation.py` — building the maze

- **`new_grid(width, height)`** — a `height × width` grid of fresh, fully
  walled `Cell()` objects.
- **`unvisited_neighbours(x, y, width, height, visited)`** — the in-bounds
  neighbours of `(x, y)` not yet in `visited`, each as
  `(direction, nx, ny, bit_here, bit_there)`.
- **`carve(grid, x, y, nx, ny, bit_here, bit_there)`** — opens the shared wall
  by calling `.open()` on **both** cells, keeping the two sides consistent.
- **`generate(width, height, entry, blocked, on_step)`** — the **recursive
  backtracker**. Starts a stack at `entry`; while the stack is non-empty it
  looks at the top cell: if it has unvisited neighbours it carves into a random
  one and pushes it; otherwise it pops (backtracks). Seeding `visited` with the
  `blocked` set makes the carver route *around* the obstacle, so the result is
  a **perfect** maze over the free cells. `on_step(grid, current)` (optional)
  fires after every carve and backtrack — that's the animation hook.
- **`_block_fully_open(grid, bx, by)`** — `True` if the 3×3 cell block whose
  top-left is `(bx, by)` has **no interior walls** (checks the inner east and
  south walls).
- **`_creates_open_3x3(grid, x, y)`** — `True` if any 3×3 block that could
  contain `(x, y)` is now fully open. Used to reject a just-opened wall that
  would create too-wide an opening.
- **`make_imperfect(grid, blocked, fraction=0.15)`** — adds **loops**. Collects
  every closed interior wall between two free cells, shuffles them, and opens up
  to `fraction` of them — but **reverts** (`.close()` both sides) any opening
  that would form a forbidden 3×3 open area, so corridors never exceed two
  cells wide.
- **`is_perfect(grid, blocked)`** — checks the maze is a spanning tree over its
  free cells: it counts open passages (each shared wall once, via east/south
  openings) and flood-fills from one free cell, returning `True` only if **all**
  free cells are reached **and** `edges == free_count − 1`.

## 4. `solving.py` — finding a route

- **`_reconstruct(came_from, entry, exit_)`** — walks the parent map backwards
  from `exit_` to `entry` and reverses it; returns `[]` if the exit was never
  reached.
- **`solve_dfs(grid, entry, exit_)`** — depth-first search; returns *a* path
  (not necessarily shortest). Only steps through open walls, so the obstacle is
  avoided automatically.
- **`solve_bfs(grid, entry, exit_)`** — breadth-first search; returns a
  **shortest** path because it expands cells in distance order. Same open-wall
  rule. This is the solver the app actually uses.
- **`path_to_directions(path)`** — turns consecutive cells into an N/E/S/W
  string by looking each step's `(dx, dy)` up in `DIR_BY_DELTA`.

## 5. `colors.py` — the palette

Five ANSI escape strings, nothing else: `LABEL_COLOR` (obstacle, blue),
`ENTRY_COLOR` (green), `EXIT_COLOR` (red), `PATH_COLOR` (orange) and
`COLOR_RESET`. The renderer wraps a block in one of these + reset to tint it.

## 6. `render.py` — drawing the maze

Everything is drawn on a **double-resolution** canvas of size
`(2·height+1) × (2·width+1)`: a cell `(x, y)` sits at canvas `(2y+1, 2x+1)`
(odd/odd = cell centres), and the slots between them (even indices) are the
walls and corners.

- **`_coloured_canvas(blocked)`** — the canvas slots to fill for the obstacle's
  **interior**. A shared wall/corner slot is only filled when **every** cell
  touching it is blocked, which leaves a clean white outline between the "42"
  and the maze.
- **`_path_canvas(path)`** — the canvas slots tracing the solution: each cell's
  centre **plus** the midpoint slot between consecutive cells, so the highlight
  is one continuous line instead of dots.
- **`render(grid, entry, exit_, blocked, path)`** — fills the canvas solid,
  then for each non-blocked cell clears its centre and any **open** wall slot
  (`cell.is_open(bit)`). Colours are tracked in a **separate dict** keyed by
  canvas position, layered obstacle → path → entry → exit (entry/exit win).
  Finally each slot is emitted **two characters wide** (so blocks look square),
  wrapped in its colour if any, and rows are joined with newlines. Returns the
  finished multi-line string.

## 7. `animation.py` — live playback

- Control codes (`CLEAR_SCREEN`, `CURSOR_HOME`, `HIDE_CURSOR`, `SHOW_CURSOR`)
  and frame delays (`GEN_DELAY`, `SOLVE_DELAY`).
- **`_draw(grid, entry, exit_, blocked, path, delay)`** — moves the cursor home,
  writes one `render(...)` frame, flushes, and sleeps `delay` seconds. Drawing
  over the same region (rather than scrolling) is what makes it animate.
- **`animate(width, height, entry, exit_, blocked, perfect)`** — hides the
  cursor, runs `generate` with `_draw` as the `on_step` callback (one frame per
  carve/backtrack), optionally `make_imperfect`, then `solve_bfs` and replays
  the solution **one cell longer each frame** so the path grows to the exit. A
  `finally` always restores the cursor. Returns the finished grid.

## 8. `fileio.py` — config in, maze out

- **`write_maze(filename, grid, entry, exit_, path)`** — writes one hex digit
  per cell (`format(cell.walls, "X")`) per row, a blank line, then the entry
  coords, exit coords and the N/E/S/W path string. Raises `OSError` on failure.
- **`MANDATORY_KEYS`** — the config keys that must be present.
- **`Config`** — a dataclass holding the validated settings (`width`, `height`,
  `entry`, `exit_`, `output_file`, `perfect`, optional `seed`).
- **`parse_coord("x,y")`** — parses a coordinate; raises `ValueError` if it
  isn't exactly two comma-separated integers.
- **`_validate(config)`** — rejects non-positive sizes, out-of-bounds or equal
  entry/exit, and an entry/exit that lands **inside the sealed "42"**.
- **`load_config(path)`** — parses `KEY=VALUE` lines (ignoring blanks and `#`
  comments), checks all mandatory keys are present, builds the `Config`
  (`PERFECT` is truthy for `true/1/yes`; `SEED` is optional), validates it, and
  returns it. Raises `ValueError` on any malformed/missing/invalid value.

## 9. `app.py` — the entry point

- **`build_maze(config, blocked, animated)`** — if `animated`, delegates to
  `animate`; otherwise `generate` (+ `make_imperfect` when not perfect) with no
  animation. Returns the grid.
- **`main()`** — the CLI: splits argv into flags and a config path (default
  `config.txt`), loads the config (printing and bailing on error), seeds the RNG
  if `SEED` was given, computes the obstacle (warning if the maze is too small),
  builds the maze (animated unless `--static`), solves it with BFS (warning if
  there's no path), prints the static render when not animating, writes the hex
  file, and finally prints whether the maze is perfect.
