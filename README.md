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

For a step-by-step walkthrough on **Windows, macOS or Linux** — including
creating and activating a `venv` — see **[`setup.md`](setup.md)**.

---

## Use it

The app has one flow: generate an environment, pick an algorithm, press
**Run Search**. It animates the cells the search explored, the path it chose,
and the agent walking it.

### Comparing algorithms fairly

```
Generate Environment  →  Regenerate Costs (weighted only)
        ↓
   BFS → DFS → UCS → Greedy → A*
        ↓
   read the rows in the COMPARISON table
```

You do **not** need to press Reset between algorithms — every search starts
from the agents' original cells, and the environment is never regenerated.
Search functions only *read* the environment, so the comparison is guaranteed
to be fair.

Every **(algorithm, agent) pair gets its own row**, so with two agents you can
read both agents' execution times directly instead of only Agent 1's:

| Algorithm | Agent | Length | Cost | Nodes | Time (ms) | Result |
| --- | :-: | --: | --: | --: | --: | --- |
| A\* | A1 | 5 | 5 | 9 | 0.036 | Success |
| BFS | A1 | 5 | 5 | 31 | 0.049 | Success |
| A\* | A2 | 7 | 7 | 15 | 0.047 | Success |
| BFS | A2 | 7 | 7 | 54 | 0.079 | Success |

The table holds **only runs made on the current grid**. It is cleared whenever
the grid changes — pressing **Generate Environment**, switching between 1 and 2
agents, or pressing **Regenerate Costs** — so measurements from two different
problems can never end up stacked in the same table and look comparable when they
are not.

Re-running an algorithm **replaces** that row rather than adding a duplicate, so
running all five algorithms twice still leaves exactly five rows per agent.

Nothing is written to disk: the comparison lives for as long as the window is
open.

### Grid symbols

| | |
| --- | --- |
| `A1` `A2` | agents |
| `F` | fire |
| `X` | obstacle |
| `1`–`9` | cell cost (weighted mode only) |
| amber cell | explored by the search |
| blue / purple line | path for agent 1 / agent 2 |

---

## Files

| File | Lines | What it does |
| --- | ---: | --- |
| `main.py` | 37 | Opens the window and starts the app. Nothing else. |
| `models.py` | 115 | The vocabulary: `Agent`, `Environment`, and every tunable constant. |
| `environment.py` | 234 | Builds the world: random maps, obstacles, agents, fire, costs. Also the rules — neighbours, path length, path cost. |
| `algorithms.py` | 461 | **The core.** `bfs`, `dfs`, `ucs`, `greedy_best_first`, `astar` — plus the shared `SearchResult`. |
| `statistics.py` | 87 | Turns numbers into the text you see (stat panels, comparison table, status). |
| `visualization.py` | 268 | All drawing on the tkinter canvas: cells, paths, agents, costs, legend. |
| `ui.py` | 611 | The single window: controls, buttons, the animation, and the comparison table. |
| `Learn.md` | — | **Start here** — a step-by-step curriculum for understanding the code. |
| `setup.md` | — | Installation and `venv` setup for Windows, macOS and Linux. |

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

There is no test suite in the repo right now. To check the algorithms by hand,
the fastest sanity pass is:

```bash
python - <<'PY'
import random
from environment import generate_environment, is_solvable
from algorithms import ALGORITHM_NAMES, run_search

for seed in range(100):
    env = generate_environment(12, 12, 1, weighted=seed % 2 == 0,
                               rng=random.Random(seed))
    assert is_solvable(env)
    for name in ALGORITHM_NAMES:
        r = run_search(name, env, env.agents[0].position, env.fire_position, 1)
        assert r.success and r.path[0] == env.agents[0].position
        assert r.path[-1] == env.fire_position
        assert all(env.is_walkable(c) for c in r.path)
print("100 maps x 5 algorithms: all paths valid")
PY
```

---

## Learn.md

New to the project? Read **[`Learn.md`](Learn.md)** — 14 sessions that take you
from "what is an AI agent" to reading any function in the codebase.

> Session 14 still walks through a `test_project.py` suite that is no longer in
> the repo. The rest of the sessions match the current code.

---

## Notes

- `statistics.py` shadows Python's stdlib module of the same name. Harmless for
  this project, but confusing if you write your own scratch scripts in this
  folder.
- Wall-clock timings are noise at this grid size (every search finishes in under
  a millisecond). Compare **cells explored**, not milliseconds. The time is still
  recorded per row, but treat small differences as meaningless.
- The fire is an ordinary walkable cell for the search — deliberate, so the
  problem stays the classic *Agent → Fire*. `Learn.md` session 12 explains the
  reasoning.
- Nothing is saved to disk. Closing the window loses the comparison, which is the
  trade for never mixing numbers from two different grids into one table.
- Pressing **Regenerate Costs** clears the table, because changing the cell costs
  changes the problem — rows from before and after it are not comparable.
