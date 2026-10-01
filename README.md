# Intelligent Firefighting Agent

One or two agents navigate a grid to reach a fire, comparing five classical AI
search algorithms on the **same** problem.

**Classical AI only** — no machine learning, no neural networks. Every decision
comes from a hand-written search algorithm.

---

## Run it

```bash
python main.py
```

That's all. No server, no database, no internet.

```bash
pip install -r requirements.txt   # no-op, there are zero pip dependencies
```

**Requires** Python 3.9+ and Tkinter. Tkinter ships with Python on Windows and
macOS. On Linux:

```bash
sudo pacman -S tk              # Arch
sudo apt install python3-tk    # Debian / Ubuntu
sudo dnf install python3-tkinter   # Fedora
```

Check it works: `python -c "import tkinter; print(tkinter.TkVersion)"`

---

## Use it

**Manual Mode** — you drive with `↑ ↓ ← →` or `W A S D`. Collect water at `W`,
then reach the fire at `F`.

**AI Mode** — pick an algorithm and press **Run Search**. The app animates the
cells it explored, the path it chose, and the agent walking it.

### Comparing algorithms fairly

```
Generate Environment  →  Regenerate Costs (weighted only)
        ↓
   BFS → Reset → DFS → Reset → UCS → Reset → Greedy → Reset → A*
        ↓
   read the five rows in the COMPARISON table
```

The environment is never regenerated between algorithms — search functions only
*read* it, so the comparison is guaranteed to be fair.

### Grid symbols

| | |
| --- | --- |
| `A1` `A2` | agents (green outline = currently controlled) |
| `F` | fire |
| `W` | water station |
| `X` | obstacle |
| `1`–`9` | cell cost (weighted mode only) |
| amber cell | explored by the search |
| blue / purple line | path for agent 1 / agent 2 |

---

## Files

| File | Lines | What it does |
| --- | ---: | --- |
| `main.py` | 37 | Opens the window and starts the app. Nothing else. |
| `models.py` | 118 | The vocabulary: `Agent`, `Environment`, and every tunable constant. |
| `environment.py` | 326 | Builds the world: random maps, obstacles, agents, fire, water, costs. Also the rules — legal moves, path length, path cost. |
| `algorithms.py` | 461 | **The core.** `bfs`, `dfs`, `ucs`, `greedy_best_first`, `astar` — plus the shared `SearchResult`. |
| `statistics.py` | 87 | Turns numbers into the text you see (stat panels, comparison table, status). |
| `visualization.py` | 284 | All drawing on the tkinter canvas: cells, paths, agents, costs, legend. |
| `ui.py` | 771 | The single window: controls, buttons, keyboard, and the animation. |
| `test_project.py` | 1 330 | 97 tests covering the algorithms and the GUI. |
| `Learn.md` | — | **Start here** — a step-by-step curriculum for understanding the code. |

### How the modules depend on each other

```
        main.py
           ↓
         ui.py ──── visualization.py
        ╱    ╲ ──── statistics.py
environment.py  algorithms.py
        ╲      ╱
       models.py
```

`algorithms.py` never imports `tkinter` — the search has no idea a GUI exists.

---

## The algorithms

| Algorithm | Uses cost | Uses heuristic | Best for |
| --- | :---: | :---: | --- |
| **BFS** | No | No | Fewest *moves* |
| **DFS** | No | No | Nothing — included as a baseline |
| **UCS** | Yes | No | Cheapest *cost* |
| **Greedy** | No | Yes | Fast but careless |
| **A\*** | Yes | Yes | Cheapest **and** fast |

Measured over 300 random 12×12 maps:

| Algorithm | avg cost | avg moves | avg cells explored |
| --- | ---: | ---: | ---: |
| BFS | 26.2 | **8.8** | 66.5 |
| DFS | 84.7 | 29.0 | 61.4 |
| UCS | **22.9** | 9.0 | 65.7 |
| Greedy | 27.0 | 9.1 | **10.9** |
| A\* | **22.9** | 9.0 | **37.2** |

A\* finds the same optimal cost as UCS using ~43% fewer cells. Greedy explores
a fraction of the cells but returns a worse path. BFS finds the shortest route
in steps yet still pays more for it. These numbers are not hard-coded — they
come from running the real algorithms.

---

## Tests

```bash
python -m unittest test_project -v      # all 97
xvfb-run -a python -m unittest test_project -v   # headless machine
```

On a machine with no display, the 39 GUI tests skip themselves and the other 58
still run.

---

## Learn.md

New to the project? Read **[`Learn.md`](Learn.md)** — 14 sessions that take you
from "what is an AI agent" to reading any function in the codebase.

---

## Notes

- `statistics.py` shadows Python's stdlib module of the same name. Harmless for
  this project, but confusing if you write your own scratch scripts in this
  folder.
- Wall-clock timings are noise at this grid size (every search finishes in under
  a millisecond). Compare **cells explored**, not milliseconds.
- The water station and the fire are ordinary walkable cells for the search —
  deliberate, so the problem stays the classic *Agent → Fire*. `Learn.md`
  session 12 explains the reasoning.
