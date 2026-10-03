# Learn.md — a step-by-step curriculum

A course for understanding this codebase from zero. Work through it in order;
each session builds on the last. By session 14 you will be able to read any
function in the project and explain why it exists.

**Time needed:** roughly 6–10 hours total. Sessions 1–10 are pure Python and
AI theory and need no GUI. Sessions 11–13 touch Tkinter and the tests.

---

## How to use this guide

Every session has the same four parts:

| Part | What it means |
| --- | --- |
| **Read** | The exact files and line numbers. Don't skim — these are short. |
| **Key ideas** | The concepts, explained plainly. This is the theory. |
| **Try it** | Copy-pasteable commands you run in your terminal. Always verify. |
| **Exercise** | Small changes that make the code yours. Break it, then fix it. |

Two rules that make this work:

1. **Never skip "Try it."** Reading about code teaches you almost nothing.
   Running it teaches you everything.
2. **Do the exercises badly on purpose first.** Predict what breaks, then break
   it, then explain why. That is how debugging intuition forms.

### Commands used throughout

Run everything from inside the project folder:

```bash
cd intelligent-firefighting-agent
```

Python files must be run from this directory, because they import each other by
plain module name (`from models import Environment`).

---

## The 14 sessions

| # | Topic | Needs GUI? |
| ---: | --- | :---: |
| 1 | What problem is this actually solving? | No |
| 2 | Running the app | Yes |
| 3 | `models.py` — the vocabulary | No |
| 4 | `environment.py` — building the world | No |
| 5 | Search fundamentals — states and neighbours | No |
| 6 | BFS — uninformed search | No |
| 7 | DFS — and the data structures behind both | No |
| 8 | Weighted grids and UCS | No |
| 9 | Heuristics — the Manhattan distance | No |
| 10 | Greedy vs A\* | No |
| 11 | Path reconstruction and the metrics | No |
| 12 | Design decisions worth defending | No |
| 13 | The GUI and the animation | Yes |
| 14 | Tests and the full experiment | Partly |

---

# Session 1 — What problem is this actually solving?

**Goal:** be able to describe the problem precisely, in AI terms, without
mentioning the code.

## Read

Nothing yet. Just `README.md`.

## Key ideas

This is an **agent**: anything that perceives its environment and acts on it.

Every intelligent agent is described with **PEAS**:

| Element | Question | Answer here |
| --- | --- | --- |
| **P**erformance measure | What counts as doing well? | Reach the fire. Minimise path cost and cells explored. |
| **E**nvironment | Where does it operate? | A 2D grid of obstacles, a fire, per-cell costs |
| **A**ctuators | What can it do? | Four moves: `UP`, `DOWN`, `LEFT`, `RIGHT` |
| **S**ensors | What can it see? | Its position, obstacles, fire, grid edges, neighbour costs |

The environment is **discrete, finite, static, fully observable and
deterministic**. That matters enormously:

- *discrete* — states are cells, not coordinates
- *finite* — at most 100 cells, so exhaustive search terminates
- *static* — nothing moves, so a plan made now is still valid later
- *fully observable* — the agent knows the whole map
- *deterministic* — one action has one predictable result

Because it is **static** and **fully observable**, the agent can plan its entire
route in one go and then just execute it. That is why `ui.py` never re-plans
mid-animation. In a dynamic world it would have to.

### The one-sentence version

> *Find the cheapest sequence of four-way moves from the agent's cell to the fire
> cell, never entering an obstacle.*

### Why this needs an AI agent at all

A random-walking robot would usually fail, or take forever. An intelligent one
**looks ahead before acting**: it builds a picture of all the futures reachable
from here and commits to the best one.

Choosing *which future to look at first* is the entire subject of this project.
BFS, DFS, UCS, Greedy and A\* are five different answers to that one question.

## Try it

Write down your own PEAS table in a scratch file. Then check it against the one
above. Anything you got wrong, the code will teach you.

## Check yourself

- Why is the fire a walkable cell rather than an obstacle?
- The environment is *deterministic*. What would change if it wasn't?

## Exercise

The project supports at most 2 agents (`MAX_AGENTS` in `models.py`).
Read `models.py:29-30`. What would you have to change to support 5?

*(Don't actually change it yet — just find every place that would break. Try
grepping for `MAX_AGENTS` and for `PATH_COLORS`.)*

---

# Session 2 — Running the app

**Goal:** see the thing working before reading any code.

## Read

`main.py` (all 37 lines) and `models.py:20-26`.

## Key ideas

```python
def main() -> int:
    try:
        root = tk.Tk()
    except tk.TclError as error:
        print("Could not open a window. Is a display available?", file=sys.stderr)
        return 1
    FirefightingApp(root)
    root.mainloop()
    return 0
```

Four things to notice:

1. **`tk.Tk()` creates the window.** Everything else is drawn inside it.
2. **`mainloop()` blocks.** This is not your loop — it is Tkinter's. Your code
   registers callbacks and returns control. This inverts how console programs
   work, and it is the single biggest mental adjustment in Tkinter.
3. **The `try/except` is real error handling.** On a headless machine you get a
   readable message and exit code `1` instead of a traceback.
4. **`main.py` has no logic.** If you ever edit it, something has gone wrong.

`models.py:20-26` holds the constants you can change immediately:

```python
DEFAULT_ROWS = 10
DEFAULT_COLS = 10
DEFAULT_OBSTACLE_RATIO = 0.15
```

## Try it

```bash
python main.py
```

Now experiment:

1. Change `DEFAULT_ROWS` and `DEFAULT_COLS` to `16`. Restart. What happens to
   the window? Why is it exactly that size?
2. Change `DEFAULT_OBSTACLE_RATIO` to `0.40`. Restart. Does generation still
   succeed? Why might it start rejecting maps?
3. Set it back to `10`, `10`, `0.15`.

Then run the algorithms by hand:

```bash
python - <<'PY'
from environment import generate_environment
from algorithms import run_search

env = generate_environment(10, 10, 1, weighted=True)
print("agents:", [a.position for a in env.agents])
print("fire:", env.fire_position)
print("obstacles:", sorted(env.obstacles))

for name in ("BFS", "DFS", "UCS", "Greedy Best-First", "A*"):
    r = run_search(name, env, env.agents[0].position, env.fire_position, 1)
    print(f"{name:20} status={r.status:8} moves={r.path_length:3} "
          f"cost={r.path_cost:4} explored={r.nodes_explored}")
PY
```

Everything the GUI does, it does by calling these same functions.

## Check yourself

- Why is the window a fixed size, not resizable? (Hint: `ui.py` sets
  `root.resizable(False, False)`.)
- What is the exit code if there is no display? Why bother returning one?
- In that script, which algorithm found the cheapest path?

## Exercise

Delete the `try/except` from `main.py` and run it on a headless machine (or
just read the traceback). Which is better for a user, and why does the choice
matter for anything that runs unattended?

---

# Session 3 — `models.py` — the vocabulary

**Goal:** be able to describe the entire problem using only types from this file.

## Read

`models.py` — all 118 lines. It is the smallest file and the most important
vocabulary.

## Key ideas

### One alias, used everywhere

```python
Position = tuple[int, int]   # row first, then column, like matrix[row][col]
```

Note **row, column** — not x, y. This trips people up constantly when they reach
the drawing code, because canvas coordinates are `(x, y)` = `(col, row)`. The
inversion is handled in exactly one place, `visualization.py:67-69`.

### Two dataclasses

```python
@dataclass
class Agent:
    id: int
    position: Position

    @property
    def label(self) -> str:
        return f"A{self.id}"
```

```python
@dataclass
class Environment:
    rows: int
    cols: int
    agents: list[Agent] = field(default_factory=list)
    obstacles: set[Position] = field(default_factory=set)
    fire_position: Position = (0, 0)
    cell_costs: dict[Position, int] = field(default_factory=dict)
    weighted: bool = False
    start_positions: list[Position] = field(default_factory=list)
```

Read the field choices carefully, because each one carries a reason:

| Field | Type | Why |
| --- | --- | --- |
| `obstacles` | `set` | You only ever ask "is this cell an obstacle?" — `set` gives O(1) |
| `cell_costs` | `dict` | Only walkable cells need an entry; you ask "what does this cell cost?" |
| `weighted` | `bool` | Tells `cost_of` whether to use the dict or always return 1 |
| `start_positions` | `list` | Remembered so **Reset** restores agents *without changing the problem* |

### The `default_factory` trap

```python
obstacles: set[Position] = field(default_factory=set)     # correct
obstacles: set[Position] = set()                          # BUG
```

The second line would give **every** `Environment` the *same* set object. Add an
obstacle to one map and every other map changes too. `default_factory` calls the
factory once per instance.

### The four methods that are the whole API

```python
in_bounds(pos)    # is it inside the grid?
is_walkable(pos)  # in bounds AND not an obstacle?
cost_of(pos)      # 1, or the generated cost
get_agent(id)     # find an agent, or None
```

Every other module talks to the environment only through these four. That
narrow surface is why the tests are easy to write.

## Try it

```bash
python - <<'PY'
from models import Environment, Agent, Position

env = Environment(rows=5, cols=5,
                  agents=[Agent(id=1, position=(0, 0))],
                  obstacles={(2, 2)}, fire_position=(4, 4))

print("label of agent 1   :", env.agents[0].label)
print("(0,0) in bounds    :", env.in_bounds((0, 0)))
print("(5,5) in bounds    :", env.in_bounds((5, 5)))
print("(2,2) walkable     :", env.is_walkable((2, 2)))
print("(0,0) cost (off)  :", env.cost_of((0, 0)))
print("get_agent(1)       :", env.get_agent(1))
print("get_agent(9)       :", env.get_agent(9))

# Default-argument sharing demo
a = Environment(rows=3, cols=3)
b = Environment(rows=3, cols=3)
a.obstacles.add((1, 1))
print("b's obstacles      :", b.obstacles)   # empty -> default_factory is correct
PY
```

## Check yourself

- Why is `obstacles` a `set` rather than a `list`? What would the search loop
  cost?
- Why does `Environment` store `start_positions` *and* `agents[].position`?
- `cost_of` returns `1` when `weighted` is False. What is the return value if
  `weighted` is True but a cell is missing from `cell_costs`?

## Exercise

Break it deliberately. Change `field(default_factory=set)` to `= set()` for
`obstacles` in a **copy** of `models.py`, generate two environments, and confirm
they share state. Then fix it. Knowing the symptom makes you able to spot this
bug in code you didn't write.

---

# Session 4 — `environment.py` — building the world

**Goal:** understand why the generated map is always solvable, and why objects
never overlap.

## Read

- `environment.py:156-211` — `generate_environment`
- `environment.py:84-119` — `reachable_cells` and `is_solvable`
- `environment.py:45-77` — `neighbours`, `path_cost`, `path_length`

## Key ideas

### Placement order makes overlap impossible

```python
free_cells = all_cells_shuffled()

fire_position = free_cells[0]                      # 1. fire
start_positions = free_cells[1:1 + num_agents]      # 2. agents
obstacles = set(free_cells[1 + num_agents:][:max_obstacles])  # 3. leftovers
```

The shuffled list is **dealt out in order**: the fire, then one cell per agent,
then the obstacles. Every cell is handed out exactly once, so overlap is not
prevented by a check — it is *unrepresentable*. This is much stronger than
validating after the fact, because there is no code path where it could happen.

### Rejection sampling

```python
for _ in range(500):            # max_attempts
    ...build a map...
    if is_solvable(env):
        return env
return _fallback_environment(...)   # guarantee: always return something
```

Draw a random map, test a property, redraw if it fails. Bounded by 500 attempts,
with a guaranteed-safe fallback (no obstacles at all) if all of them fail.

### The solvability check is its own BFS

`reachable_cells` is a plain flood fill. `environment.py` deliberately does
**not** import BFS from `algorithms.py`. Saving 8 lines would have coupled
environment generation to the search algorithms — a worse architecture.

### `neighbours` — the successor function

```python
def neighbours(position, obstacles, rows, cols):
    row, col = position
    result = []
    for dr, dc in ((-1, 0), (0, 1), (1, 0), (0, -1)):    # UP, RIGHT, DOWN, LEFT
        target = (row + dr, col + dc)
        if validate_position(target, rows, cols) and target not in obstacles:
            result.append(target)
    return result
```

Two things to notice:

1. **The fixed order is load-bearing.** Always UP, RIGHT, DOWN, LEFT. That makes
   expansion order deterministic, which makes node counts reproducible, which
   makes the comparison table trustworthy.
2. **There is no adjacency list.** The graph is *regular* — every cell has at
   most 4 neighbours by construction. Generating them on demand beats storing
   them.

### Path length vs path cost

```python
def path_cost(environment, path):
    if len(path) < 2:
        return 0
    return sum(environment.cost_of(cell) for cell in path[1:])

def path_length(path):
    return max(0, len(path) - 1)
```

`path[1:]` — **the starting cell is excluded**. The agent doesn't "enter" the
cell it already occupies. Consequence: in unweighted mode
`path_cost == path_length` exactly, always.

## Try it

```bash
python - <<'PY'
import random
from environment import (generate_environment, is_solvable, neighbours,
                         path_cost, path_length, reachable_cells)
from algorithms import bfs

# 1. Non-overlap, across many seeds
for seed in range(50):
    env = generate_environment(12, 12, 2, rng=random.Random(seed))
    taken = {env.fire_position}
    taken |= {a.position for a in env.agents}
    assert len(taken) == 1 + len(env.agents), f"overlap at seed {seed}"
    assert not (taken & env.obstacles), f"obstacle overlap at seed {seed}"
print("50 seeds: no overlap, and all solvable:",
      all(is_solvable(generate_environment(12, 12, 2, rng=random.Random(s)))
          for s in range(50)))

# 2. Neighbour order is fixed
print("neighbours of (5,5):", neighbours((5, 5), set(), 10, 10))

# 3. Length and cost agree when unweighted
env = generate_environment(8, 8, 1, weighted=False, rng=random.Random(1))
r = bfs(env, env.agents[0].position, env.fire_position, 1)
print(f"unweighted: length={r.path_length} cost={r.path_cost} "
      f"-> equal? {r.path_length == r.path_cost}")

# 4. They diverge when weighted
env = generate_environment(8, 8, 1, weighted=True, rng=random.Random(1))
r = bfs(env, env.agents[0].position, env.fire_position, 1)
print(f"weighted:   length={r.path_length} cost={r.path_cost}")
print("path:", r.path)
print("costs of cells entered:", [env.cost_of(c) for c in r.path[1:]])
PY
```

## Check yourself

- Why is the obstacle count clamped to `total_cells - num_agents - 1`?
  What would break without it?
- How would the results change if `neighbours` returned a random order?
- `is_solvable` returns `True` if **any** agent can reach the fire. Why
  `any` and not `all`?

## Exercise

Make the map deliberately hard: raise `DEFAULT_OBSTACLE_RATIO` to `0.35` and
generate 200 maps, counting how many retries each takes. Write a small loop to
count them. Then try `0.45`. At what point does `_fallback_environment` start
kicking in, and how would you detect that?

---

# Session 5 — Search fundamentals

**Goal:** be able to define states, actions, costs and goals for this problem in
your own words.

## Read

- `algorithms.py:1-27` — the module docstring. Read it twice; it is the best
  summary in the project.
- `algorithms.py:41` — `ALGORITHM_NAMES`
- `algorithms.py:49-71` — `SearchResult`

## Key ideas

### The search problem

| Element | Here |
| --- | --- |
| States | walkable grid cells |
| Actions | the four moves |
| Transition model | `neighbours()` |
| Goal states | the fire cell |
| Path cost | `path_cost()` — 1 per cell, or the random cost |

### Every algorithm has one signature

```python
search(environment, start, goal, agent_id) -> SearchResult
```

and **returns the same type**. That is why the UI and statistics code are never
duplicated — one display path handles all five.

### Two functions, one meaning

```
g(n) = cost actually paid so far, from start to n
h(n) = estimate of cost still to come, from n to goal
```

Everything below is a different answer to *which state should I expand next?*

| Algorithm | Expands the state with… |
| --- | --- |
| BFS | smallest depth |
| DFS | the deepest one available |
| UCS | smallest `g(n)` |
| Greedy | smallest `h(n)` |
| A\* | smallest `g(n) + h(n)` |

### Graph search, not tree search

All five keep a set or dict of states already reached, so each cell is expanded
at most once. Consequences:

- search terminates (at most 100 expansions on a 10×10 grid)
- DFS and Greedy are **complete** here — on a finite grid with a closed set they
  will eventually find any route that exists
- but they are **never optimal**

### Cost-blind vs cost-aware

This is the single most important split, and the code makes it explicit:

```python
# Cost-blind (BFS, DFS, Greedy): first arrival wins, permanently.
if neighbour not in discovered:
    discovered.add(neighbour)
    came_from[neighbour] = current

# Cost-aware (UCS, A*): cheapest arrival wins, and opinions can be revised.
if new_cost < best_cost.get(neighbour, float("inf")):
    best_cost[neighbour] = new_cost
    came_from[neighbour] = current
```

Greedy uses the first form, so it can *never* discover that a cheaper route to a
cell exists. That is why it returns poor paths. BFS makes the same simplification
and it is safe there — with uniform costs the first arrival genuinely is
cheapest. Same code, safe in one algorithm and wrong in the other.

## Try it

```bash
python - <<'PY'
import random
from environment import generate_environment
from algorithms import SEARCH_ALGORITHMS, ALGORITHM_NAMES

print("registered algorithms:", list(SEARCH_ALGORITHMS))
print("dropdown order        :", ALGORITHM_NAMES)

# The graph is regular: at most 4 neighbours per cell, no exceptions.
env = generate_environment(10, 10, 1, rng=random.Random(5))
walkable = env.rows * env.cols - len(env.obstacles)
print(f"walkable cells={walkable}, so at most {walkable} expansions per search")
PY
```

## Check yourself

- Explain why "first arrival wins" is safe in BFS but not in Greedy.
- If a state can be expanded at most once, what is the maximum number of
  expansions for any algorithm on a 10×10 grid?
- What is the difference between completeness and optimality? Give an algorithm
  from this project that has one but not the other.

## Exercise

Pick a state representation other than `(row, col)`. Could you solve the same
problem with a linear index `row * cols + col`? What would you gain and lose?
You don't have to implement it — just reason it through.

---

# Session 6 — BFS — uninformed search

**Goal:** trace BFS by hand on a small grid, then explain why it is optimal for
step-count but not for cost.

## Read

`algorithms.py:147-187` — the `bfs` function, in full. It is 40 lines.

## Key ideas

```python
queue = deque([start])
came_from = {}
visited = {start}
explored = []
found = False

while queue:
    current = queue.popleft()          # OLDEST first, not best
    explored.append(current)            # counted here = a real expansion
    if current == goal:
        found = True
        break
    for neighbour in neighbours(current, ...):
        if neighbour in visited:
            continue
        visited.add(neighbour)         # marked when QUEUED, not when dequeued
        came_from[neighbour] = current
        queue.append(neighbour)
```

Four decisions:

1. **`deque.popleft()` is FIFO** — first in, first out. That is what makes it
   breadth-first.
2. **Mark visited when queuing.** Correct *specifically because* all edges cost
   1, so the first arrival at a node is already the cheapest arrival. UCS and A\*
   cannot do this; they must compare costs.
3. **`explored.append` sits after the pop.** So `nodes_explored` counts genuine
   expansions, not merely discovered states. This makes the metric honest.
4. **`break` on finding the goal.** Nothing after expansion is needed.

### Why BFS is optimal here (unweighted only)

Depth and cost are the same number when every move costs 1. BFS expands in
non-decreasing depth order, so when the goal pops, no unexplored path could be
shorter.

### Why that argument fails in weighted mode

BFS still ignores costs, so it still returns the fewest-*moves* route. That
route may be far more expensive than a longer detour through cheap cells.

Measured: BFS finds 8.8-move routes costing 26.2. UCS finds 9.0-move routes
costing 22.9. **One extra step saves money.**

## Try it

Trace BFS manually on this 5×5 open grid from `(0,0)` to `(4,4)`, then check
your answer:

```bash
python - <<'PY'
from models import Environment, Agent
from algorithms import bfs

def grid(rows=5, cols=5, weighted=False, costs=None):
    return Environment(rows=rows, cols=cols,
                       agents=[Agent(id=1, position=(0, 0))],
                       obstacles=set(), fire_position=(rows-1, cols-1),
                       cell_costs=dict(costs or {}),
                       weighted=weighted, start_positions=[(0, 0)])

env = grid()
r = bfs(env, (0, 0), (4, 4), 1)
print("status :", r.status)
print("moves  :", r.path_length, "(expected exactly 8)")
print("explored in this order:")
print(" ", r.explored_cells)
PY
```

`explored` is the expansion order. Write out the grid by hand, mark cells in that
order, and confirm you get the same sequence. Doing this once teaches the
algorithm better than reading about it ten times.

Now the case that separates them. One fixed 5×5 map, one goal, one start —
only the algorithm differs:

```bash
python - <<'PY'
from models import Environment, Agent
from algorithms import bfs, ucs, astar

# A verified layout: start bottom-left, fire top-right, 5 obstacles,
# and hand-picked costs so that two equally-short routes differ wildly in price.
costs = {
    (0,0):8, (0,1):9, (0,2):6, (0,3):9, (0,4):5,
    (1,0):5, (1,1):8, (1,2):8, (1,3):2, (1,4):1,
    (2,0):6, (2,1):7, (2,2):2, (2,3):3, (2,4):8,
    (3,0):4, (3,1):1, (3,2):2, (3,3):7, (3,4):5,
    (4,0):1, (4,1):2, (4,2):5, (4,3):6, (4,4):6,
}
env = Environment(rows=5, cols=5, agents=[Agent(id=1, position=(4, 0))],
                  obstacles={(1,1), (3,2), (4,1), (4,2), (4,3)},
                  fire_position=(0, 4),
                  cell_costs=costs, weighted=True, start_positions=[(4, 0)])

for name, fn in (("BFS", bfs), ("UCS", ucs), ("A*", astar)):
    r = fn(env, (4, 0), (0, 4), 1)
    print(f"{name:4} moves={r.path_length}  cost={r.path_cost:3}  {r.path}")
PY
```

Read that output carefully. **All three take exactly 8 moves** — the start and
goal are the same, so the shortest route length is fixed. But BFS pays **52**
while UCS and A\* pay **25**, over twice as much, for the same number of steps.

BFS climbed the left edge and the top row, which happens to run straight through
the most expensive cells on the map. UCS and A\* took the diagonal-ish route
through the cheap middle. Same length, half the price.

**Same map, same goal, same number of steps, and a completely different
quality of answer.** That is the entire argument for cost-aware search, in one
example.

## Check yourself

- Why must BFS mark `visited` at enqueue time? What breaks if it marks at
  dequeue time?
- In the second experiment, which is correct — the expensive direct route or the
  longer cheap detour? What is BFS's criterion for "correct"?
- Why does `explored.append(current)` sit *before* the goal check?

## Exercise

Add `print(current)` inside the BFS loop and re-run both experiments. Watch
BFS's frontier expand as a widening wave. Then do the same in DFS and compare
the two shapes. That visual difference is the whole reason DFS returns a 26-move
path where BFS returns 8.

---

# Session 7 — DFS — and the data structures

**Goal:** understand why a stack changes everything, and learn the three data
structures that underpin all five algorithms.

## Read

`algorithms.py:194-235` — the `dfs` function.

## Key ideas

```python
stack = [start]
visited = {start}

while stack:
    current = stack.pop()                       # LIFO, not FIFO
    explored.append(current)
    if current == goal:
        found = True
        break
    for neighbour in reversed(neighbours(current, ...)):
        if neighbour not in visited:
            visited.add(neighbour)
            stack.append(neighbour)
```

Three deliberate choices:

1. **`reversed(...)`** — a stack returns the **last** item pushed. Without
   reversing, the exploration order would be silently inverted and the animated
   path would be hard to follow. With it, the effective pop order is
   UP → RIGHT → DOWN → LEFT, matching the natural reading order.
2. **`visited` on push, not on pop** — this turns DFS from a *tree* search into
   a *graph* search. It prevents re-expansion and guarantees termination. The
   price is that DFS can miss a shorter route to a node it reaches late.
3. **An explicit stack, not recursion** — Python's default recursion limit is
   ~1000. A recursive DFS along a long corridor would raise `RecursionError`. An
   explicit list has no limit.

### The three data structures

| Structure | Used by | Behaviour | Why |
| --- | --- | --- | --- |
| `deque` queue | BFS | FIFO | shallowest first |
| `list` stack | DFS | LIFO | deepest first |
| `heapq` priority queue | UCS, Greedy, A\* | smallest key first | best-first |

Everything else — `closed`, `best_cost`, `came_from`, `explored` — is bookkeeping
common to all of them.

## Try it

Compare the shapes directly on the same problem:

```bash
python - <<'PY'
import random
from environment import generate_environment
from algorithms import bfs, dfs

env = generate_environment(12, 12, 1, weighted=False, rng=random.Random(3))
start, goal = env.agents[0].position, env.fire_position

for name, fn in (("BFS", bfs), ("DFS", dfs)):
    r = fn(env, start, goal, 1)
    first_10 = r.explored_cells[:10]
    print(f"{name}: {r.path_length:2} moves, {r.nodes_explored:3} explored")
    print(f"      first 10 expanded: {first_10}")
PY
```

BFS's first ten are all *adjacent to the start* — it spreads outward. DFS's
first ten march in a line. That shape difference is the algorithm.

Now find the case where DFS actually wins on node count:

```bash
python - <<'PY'
from models import Environment, Agent
from algorithms import bfs, dfs

# Fire in the very next cell: DFS walks straight to it.
env = Environment(rows=10, cols=10, agents=[Agent(id=1, position=(0, 0))],
                  obstacles=set(), fire_position=(0, 1),
                  start_positions=[(0, 0)])
for name, fn in (("BFS", bfs), ("DFS", dfs)):
    r = fn(env, (0, 0), (0, 1), 1)
    print(f"{name}: moves={r.path_length} explored={r.nodes_explored}")
PY
```

## Check yourself

- What happens if you delete `reversed(...)`? Does the answer change, or only
  the path it happens to pick?
- Why must DFS mark `visited` on push? What would `RecursionError` or an infinite
  loop suggest if you didn't?
- BFS explored 66.5 cells on average, DFS 61.4. DFS is *cheaper* yet finds a
  26-move path. Why does exploring fewer cells not mean a better answer?

## Exercise

Turn DFS into a recursive function in a scratch file. Get it working on a 5×5
grid, then try a 50×50 grid with a corridor maze. Catch the `RecursionError`.
Then convert it back to an explicit stack. This is why the code uses a stack.

---

# Session 8 — Weighted grids and UCS

**Goal:** understand Dijkstra's algorithm, and see why `best_cost` must be
revisable.

## Read

`algorithms.py:242-299` — the `ucs` function.

## Key ideas

```python
frontier = [(environment.cost_of(start), 0, start)]
best_cost = {start: environment.cost_of(start)}
closed = set()

while frontier:
    cost_so_far, _, current = heapq.heappop(frontier)
    if current in closed:
        continue
    closed.add(current)
    explored.append(current)
    if current == goal:
        found = True
        break
    for neighbour in neighbours(current, ...):
        if neighbour in closed:
            continue
        new_cost = cost_so_far + environment.cost_of(neighbour)
        if new_cost < best_cost.get(neighbour, float("inf")):
            best_cost[neighbour] = new_cost
            came_from[neighbour] = current
            heappush(frontier, (new_cost, counter, neighbour))
```

### UCS *is* Dijkstra

Same algorithm. Expand the cheapest known state; when the goal pops, no
cheaper route exists, because any cheaper route would have had to pass through a
state with a lower `g`, and that state would have been expanded first.

### The one critical line

```python
if new_cost < best_cost.get(neighbour, float("inf")):
```

UCS must be willing to **revise its opinion**. If a cheaper route to a
cell it has already seen appears later, UCS accepts it. That is why UCS needs a
`best_cost` dict and not just a `visited` set — and it is the exact line BFS/DFS
can safely omit.

Delete this comparison and replace it with `if neighbour not in discovered:` and
watch UCS stop being optimal. This single experiment teaches the difference
between cost-blind and cost-aware search better than any explanation.

### Why unweighted UCS ≡ BFS

With every cost `1`, `g(n)` equals depth, so a priority queue on `g` behaves
exactly like a FIFO queue. The test suite asserts this. It's an important
consistency check: UCS is a strict generalisation of BFS.

## Try it

```bash
python - <<'PY'
import random
from environment import generate_environment
from algorithms import bfs, ucs

# Unweighted: BFS and UCS must agree exactly.
for seed in range(5):
    env = generate_environment(10, 10, 1, weighted=False, rng=random.Random(seed))
    s, g = env.agents[0].position, env.fire_position
    a, b = bfs(env, s, g, 1), ucs(env, s, g, 1)
    print(f"seed {seed}: BFS cost={a.path_cost:3} UCS cost={b.path_cost:3} "
          f"identical={a.path == b.path}")

print()
# Weighted: now they diverge, and UCS must always be <= BFS.
print("seed | BFS cost | UCS cost | UCS saved")
for seed in range(6):
    env = generate_environment(10, 10, 1, weighted=True, rng=random.Random(seed))
    s, g = env.agents[0].position, env.fire_position
    a, b = bfs(env, s, g, 1), ucs(env, s, g, 1)
    print(f"{seed:4} | {a.path_cost:9} | {b.path_cost:9} | {a.path_cost - b.path_cost:10}")
PY
```

Now verify UCS is genuinely optimal by brute force with an independent
implementation:

```bash
python - <<'PY'
import heapq, random
from environment import generate_environment, neighbours
from algorithms import ucs

def true_min_cost(env, start, goal):
    """Independent Dijkstra, written from scratch as the oracle."""
    best = {start: env.cost_of(start)}
    pq = [(best[start], start)]
    seen = set()
    while pq:
        c, node = heapq.heappop(pq)
        if node in seen:
            continue
        seen.add(node)
        if node == goal:
            return c - env.cost_of(start)      # match path_cost's convention
        for n in neighbours(node, env.obstacles, env.rows, env.cols):
            nc = c + env.cost_of(n)
            if nc < best.get(n, float("inf")):
                best[n] = nc
                heapq.heappush(pq, (nc, n))
    return None

bad = 0
for seed in range(100):
    env = generate_environment(12, 12, 1, weighted=True, rng=random.Random(seed))
    s, g = env.agents[0].position, env.fire_position
    mine = ucs(env, s, g, 1).path_cost
    truth = true_min_cost(env, s, g)
    if truth is not None and mine != truth:
        bad += 1
        print("MISMATCH", seed, mine, truth)
print(f"checked 100 maps, mismatches: {bad}")
PY
```

Zero mismatches means UCS is provably correct on this problem class.

## Check yourself

- Why must UCS use `best_cost` rather than `visited`?
- When BFS and UCS produce the same answer, what does that tell you about the
  map?
- In the oracle, why did `true_min_cost` subtract `env.cost_of(start)` at the
  end? (Clue: read `path_cost` in `environment.py:63`.)

## Exercise

Set `MIN_CELL_COST = 0` in a copy of `models.py`, regenerate a weighted map, and
re-run the oracle comparison. Does UCS stay correct? Does the Manhattan
heuristic stay admissible? Write down what breaks and why. This is the
experiment that proves *why* `MIN_CELL_COST` must be `1`.

---

# Session 9 — Heuristics — the Manhattan distance

**Goal:** prove that the heuristic is admissible, in your own words.

## Read

`algorithms.py:78-85` — the `manhattan` function (8 lines).

## Key ideas

```python
def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])
```

It estimates "how many steps are still needed", because with four-way movement
you need at least `|Δrow| + |Δcol|` moves.

### Admissibility — the guarantee that makes it safe

`h` is **admissible** if it never overestimates the true remaining cost.

**Prove it for this project.** The argument is one line:

> Any route from `n` to the goal needs at least `h(n)` moves, because each move
> changes row or column by exactly 1. Every move costs at least `1`, because
> `MIN_CELL_COST = 1`. Therefore the true remaining cost is at least
> `h(n)`. ∎

The load-bearing assumption is `MIN_CELL_COST = 1`. The heuristic ignores costs
while the true cost includes them, and the *minimum cell cost of 1* is what
guarantees the heuristic can never exceed it.

### Consistency — the guarantee that makes it efficient

`h` is **consistent** if `h(n) ≤ cost(n, n') + h(n')` for every neighbour `n'`.

For Manhattan: `|h(n) − h(n')| ≤ 1` for adjacent cells, and `cost(n, n') ≥ 1`,
so `h(n) ≤ 1 + h(n') ≤ cost(n, n') + h(n')`. ∎

| Property | Guarantees |
| --- | --- |
| **Admissible** | the answer is optimal |
| **Consistent** | the closed set is safe — no re-expansion needed |

## Try it

Verify admissibility empirically — check the heuristic against the true
remaining cost on *every* cell of many random maps:

```bash
python - <<'PY'
import random
from environment import generate_environment
from algorithms import manhattan

violations = 0
checked = 0
for seed in range(60):
    env = generate_environment(12, 12, 1, weighted=True, rng=random.Random(seed))
    goal = env.fire_position
    for cell in [(r, c) for r in range(env.rows) for c in range(env.cols)]:
        if cell in env.obstacles:
            continue
        # True remaining cost: UCS forward from cell to goal
        import heapq
        from environment import neighbours
        best = {cell: env.cost_of(cell)}
        pq = [(best[cell], cell)]
        seen, truth = set(), None
        while pq:
            c, node = heapq.heappop(pq)
            if node in seen: continue
            seen.add(node)
            if node == goal:
                truth = c - env.cost_of(cell); break
            for n in neighbours(node, env.obstacles, env.rows, env.cols):
                nc = c + env.cost_of(n)
                if nc < best.get(n, float("inf")):
                    best[n] = nc; heapq.heappush(pq, (nc, n))
        if truth is None: continue
        h = manhattan(cell, goal)
        checked += 1
        if h > truth:
            violations += 1
print(f"checked h(n) <= true cost on {checked} cells")
print(f"admissibility violations: {violations}")
PY
```

Zero violations means the heuristic never lies in the dangerous direction.

Watch how *loose* the heuristic is — this is the raw material for session 10:

```bash
python - <<'PY'
import heapq, random
from environment import generate_environment, neighbours
from algorithms import manhattan, bfs

env = generate_environment(12, 12, 1, weighted=True, rng=random.Random(3))
start, goal = env.agents[0].position, env.fire_position

# true remaining cost from start
best = {start: env.cost_of(start)}
pq = [(best[start], start)]; seen = set(); truth = None
while pq:
    c, n = heapq.heappop(pq)
    if n in seen: continue
    seen.add(n)
    if n == goal: truth = c - env.cost_of(start); break
    for m in neighbours(n, env.obstacles, env.rows, env.cols):
        nc = c + env.cost_of(m)
        if nc < best.get(m, float("inf")):
            best[m] = nc; heapq.heappush(pq, (nc, m))

print(f"start cell      : {start}   goal: {goal}")
print(f"h(start) estimate: {manhattan(start, goal):3}")
print(f"true cost to goal : {truth:3}")
print(f"-> the heuristic underestimates by {truth - manhattan(start, goal):3}")
PY
```

## Check yourself

- State the admissibility proof in one sentence without looking.
- Which single constant, if changed, breaks the proof? Why?
- Does the proof depend on whether the map has obstacles?

## Exercise

Prove Manhattan is **not** an admissible heuristic for 8-way (diagonal) movement.
Work out the true cost of a single diagonal step under both metrics. Then decide:
if you added diagonals to `DIRECTIONS`, would you also need to change `manhattan`?
Try it — add diagonals to the tuple in `neighbours` (`environment.py:52`) in a
copy and see what breaks in
the algorithms.

---

# Session 10 — Greedy vs A\*

**Goal:** see the two informed algorithms side by side and explain the
difference in one sentence.

## Read

`algorithms.py:306-363` (`greedy_best_first`) and `algorithms.py:370-432`
(`astar`). Compare them side by side — they are almost identical, and that is the
point.

## Key ideas

### The difference is one line

| | Priority | Keeps `best_cost`? | Revises parents? |
| --- | --- | --- | --- |
| **Greedy** | `h(n)` | No | No — `discovered` set |
| **A\*** | `g(n) + h(n)` | Yes | Yes |

Greedy has **no `best_cost` dict at all**. Because it never compares costs, the
*first* parent to reach a cell is kept forever. It has no way to learn that a
cheaper route to that cell exists. That is the entire problem.

### What each one is good at

- **Greedy** is fast and blind. It looks only at "which cell is nearest the fire".
- **A\*** balances "what I've spent" against "what I still estimate to need".
  It prunes cells that provably can't lead to a cheap solution.

### The headline result

Measured over 300 random 12×12 maps:

| Algorithm | avg cost | avg explored |
| --- | ---: | ---: |
| UCS | **22.9** | 65.7 |
| Greedy | 27.0 | **10.9** |
| A\* | **22.9** | **37.2** |

A\* returns the **same optimal cost as UCS** while exploring **43% fewer cells**.
Greedy explores only 16% as many cells but returns a **worse** path than BFS
(27.0 vs 26.2) — it bought a massive speedup with a bad answer.

> **The heuristic does not make the answer better — it makes finding the answer
> cheaper.** Quality comes from cost-awareness; efficiency comes from guidance.
> A\* is the only algorithm here that gets both.

## Try it

Run all five on the same frozen map, several times, and watch the rows line up:

```bash
python - <<'PY'
import random
from environment import generate_environment
from algorithms import ALGORITHM_NAMES, run_search

env = generate_environment(12, 12, 1, weighted=True, rng=random.Random(11))
print(f"map frozen: {len(env.obstacles)} obstacles, weighted costs 1..9\n")
print(f"{'Algorithm':20} {'cost':>5} {'moves':>6} {'explored':>9} {'status':>8}")

results = {}
for name in ALGORITHM_NAMES:
    r = run_search(name, env, env.agents[0].position, env.fire_position, 1)
    results[name] = r
    print(f"{name:20} {r.path_cost:5} {r.path_length:6} {r.nodes_explored:9} {r.status:>8}")

print()
best = min(r.path_cost for r in results.values())
print("optimal cost      :", best)
for n, r in results.items():
    flag = "OPTIMAL" if r.path_cost == best else "suboptimal"
    print(f"  {n:20} {r.path_cost:5}  {flag}  "
          f"({100 * (r.nodes_explored - results['UCS'].nodes_explored) / results['UCS'].nodes_explored:+.0f}% cells vs UCS)")
PY
```

Now compare *expansion patterns* — the visual signature of each algorithm. Run this on a real weighted map with obstacles (seed 3):

```bash
python - <<'PY'
import random
from environment import generate_environment
from algorithms import bfs, ucs, greedy_best_first, astar

env = generate_environment(9, 9, 1, weighted=True, rng=random.Random(3))
s, g = env.agents[0].position, env.fire_position
print(f"9x9 weighted map: start={s} goal={g}  ({len(env.obstacles)} obstacles)")
for row in range(9):
    print("   " + "".join("X" if (row, c) in env.obstacles else "." for c in range(9)))

for name, fn in (("BFS", bfs), ("UCS", ucs),
                 ("Greedy", greedy_best_first), ("A*", astar)):
    r = fn(env, s, g, 1)
    print(f"\n{name}: cost={r.path_cost} moves={r.path_length} expanded={r.nodes_explored}")
    for row in range(9):
        line = ""
        for col in range(9):
            cell = (row, col)
            if cell in env.obstacles:      line += "X"
            elif cell in r.path:           line += "*"
            elif cell in r.explored_cells: line += "."
            else:                          line += " "
        print("   " + line)
print("\n* = path,  . = expanded then abandoned,  X = obstacle,  (blank) = never touched")
PY
```

The four numbers, and the four shapes:

| | expanded | cost |
| --- | ---: | ---: |
| Greedy | **8** | 38 |
| BFS | 39 | 38 |
| UCS | 45 | **36** |
| A\* | 40 | **36** |

- **Greedy** touched only 8 cells - a thin streak aimed straight at the fire. It
  barely explored, and it paid 38 for it. Fast, and wrong.
- **BFS** swept a broad wavefront and also paid 38. Wide, and wrong.
- **UCS** fanned out widest, checking everything that might be cheap. Optimal 36.
- **A\*** explored *less* than UCS (40 vs 45) for the *same* optimal cost. The
  heuristic let it skip regions it could prove were too expensive to matter.

### A trap worth knowing about

Run the same visualisation on an **empty, unweighted** grid - start in one
corner, fire in the opposite - and BFS, UCS and A\* all expand **every single
cell**, with identical counts.

Not a bug, and worth understanding. On an obstacle-free unweighted grid the
Manhattan heuristic is *exact*, so `f(n)` is the same constant for every cell on
any shortest route. Everything ties, `f` gives no ranking, nothing is pruned, and
A\* degenerates to UCS and BFS.

**A heuristic only pays off where cost and distance disagree** - with obstacles,
with weighted costs, or both. Demonstrate A\* on a blank grid and you will
"prove" the opposite of the truth.

## Check yourself

- In one sentence: why does A\* return the same cost as UCS?
- Why can Greedy not revise a parent pointer?
- On the empty unweighted grid, why does A\* prune nothing? What does that
  tell you about when a heuristic is worth having at all?

## Exercise

Prove A\* ≡ UCS when `h ≡ 0`. Change `astar` so that `f_value = new_cost`
(ignore the heuristic entirely) in a copy, and confirm it produces identical
results to `ucs` on 50 maps. Then do the same for `h ≡ distance/2` and confirm
optimality survives but node counts drop. This is the admissibility cliff —
find the multiplier where it breaks by trying 2.0, 1.1, 1.0.

---

# Session 11 — Path reconstruction and the metrics

**Goal:** understand how a search becomes an actual path, and what each of the
six reported numbers really measures.

## Read

- `algorithms.py:88-102` — `_reconstruct_path`
- `algorithms.py:105-140` — `_build_result`
- `statistics.py` — all 87 lines

## Key ideas

### Path reconstruction via parent pointers

```python
def _reconstruct_path(came_from, goal):
    path = [goal]
    while path[-1] in came_from:      # stop at the node with no parent
        path.append(came_from[path[-1]])
    path.reverse()
    return path
```

**The subtle part:** `came_from` stores `neighbour → current` only for
*discovered* nodes. The start never gets a parent — a node that is its own parent
would create a cycle and the loop would never end. So the walk halts naturally
when it returns to the start.

Guarantees:
- no cycles (parents always point to earlier-discovered states)
- `path[0] == start`, `path[-1] == goal`
- `start == goal` works: `path == [start]`, length 0, cost 0

### `_build_result` — the single place statistics are computed

Every algorithm funnels through it, so all five report numbers identically.
There is no per-algorithm metric code, and therefore no chance of one algorithm
measuring something slightly differently.

### The six metrics

| Metric | Definition | Reads as |
| --- | --- | --- |
| **Path Length** | `len(path) - 1` | how far it walked |
| **Path Cost** | `sum(cost_of(c) for c in path[1:])` | how much it spent |
| **Nodes Explored** | `len(explored_cells)` | how hard it worked |
| **Execution Time** | `perf_counter()` delta | wall clock |
| **Status** | `SUCCESS` / `FAILURE` | did it find anything |
| **Algorithm** | its own name | provenance |

**Length vs cost** is the distinction that matters. Identical when unweighted,
which hides the issue entirely. In weighted mode they decouple: fewer moves can
cost more.

**Nodes explored is the reliable comparative metric.** Execution time on a
100-cell problem is dominated by interpreter overhead, not algorithmic work.
Report node counts; treat milliseconds as decoration.

## Try it

Check the invariant that `path_cost` sums *entered* cells, and confirm the
start cell is excluded:

```bash
python - <<'PY'
import random
from environment import generate_environment
from algorithms import run_search

env = generate_environment(10, 10, 1, weighted=True, rng=random.Random(4))
r = run_search("A*", env, env.agents[0].position, env.fire_position, 1)

manual = sum(env.cost_of(c) for c in r.path[1:])
print(f"start cell          : {r.path[0]}  cost_of(start) = {env.cost_of(r.path[0])}")
print(f"reported path_cost  : {r.path_cost}")
print(f"recomputed by hand  : {manual}   match: {manual == r.path_cost}")
print(f"length = len-1      : {r.path_length == len(r.path) - 1}")
print(f"nodes == explored   : {r.nodes_explored == len(r.explored_cells)}")
print(f"time is positive    : {r.execution_time_ms > 0}")

# Every consecutive pair must be exactly one orthogonal step apart.
bad = [1 for a, b in zip(r.path, r.path[1:])
       if abs(a[0]-b[0]) + abs(a[1]-b[1]) != 1]
print(f"non-adjacent steps  : {len(bad)}  (must be 0)")
PY
```

`statistics.py` exists so the UI never has to know *how* a number is computed —
it just asks for the text:

```bash
python - <<'PY'
import random
from environment import generate_environment
from algorithms import run_search
from statistics import result_statistics, comparison_row, overall_status

env = generate_environment(10, 10, 1, weighted=True, rng=random.Random(2))
r = run_search("A*", env, env.agents[0].position, env.fire_position, 1)

print("as displayed in the Agent panel:")
for label, value in result_statistics(r):
    print(f"  {label:16} : {value}")

print("\nas a comparison-table row:", comparison_row(r))
print("no search run yet      :", result_statistics(None))
print("mission verdict        :", overall_status([r]))
PY
```

## Check yourself

- Why is the start cell excluded from `path_cost`?
- Why must `_reconstruct_path` stop rather than loop forever?
- Why does `result_statistics(None)` return `[]` instead of raising?

## Exercise

Reproduce the README benchmark table from scratch: 300 maps of 12×12, half
weighted, all five algorithms. Print averages for cost, length and nodes. Your
numbers should match the README exactly — and when they do, you have proved the
whole system is deterministic. Then change the order of neighbours in
`regenerate_costs` in `environment.py` and re-run. Which numbers change, and
which don't?

---

# Session 12 — Design decisions worth defending

**Goal:** be able to justify the project's architecture. These are the questions
a viva will actually ask.

## Read

- `main.py:20-33`
- `environment.py:84-105` (the local flood fill)
- `algorithms.py:49-71` (`SearchResult`), `439-461` (the registry)
- `environment.py:156-211` (placement order), `170-172` (the clamp)
- `models.py:86-90` (`start_positions`)

## Key ideas

### 1. Layering

```
models.py  ←  environment.py  ←  ui.py  ←  main.py
     ↑             algorithms.py
```

`algorithms.py` never imports `tkinter`. The search has no idea a GUI exists.
Proof it's a real separation, not just a comment: **you can run all 97 tests'
logic half without a display.**

### 2. Purity — why the comparison is trustworthy

Every search function only **reads** the environment. Enforced by
`test_algorithms_do_not_modify_the_environment`, which snapshots every mutable
field, runs all five algorithms, and asserts the snapshot is byte-identical.

This is why a fair comparison is *structural* rather than something you have to
remember to do by pressing Reset.

### 3. Duplicate the flood fill, don't couple the modules

`environment.py` writes its own 8-line BFS instead of importing `bfs` from
`algorithms.py`. Saving 8 lines would have created a dependency between two
logically independent modules. The duplication is cheaper than the coupling.

### 4. The registry pattern

```python
SEARCH_ALGORITHMS = {"BFS": bfs, "DFS": dfs, ...}

def run_search(algorithm_name, environment, start, goal, agent_id=1):
    return SEARCH_ALGORITHMS[algorithm_name](environment, start, goal, agent_id)
```

The UI calls `run_search(name, ...)` and never changes. Adding an algorithm
means writing one function and adding one dict entry. No `if algorithm == ...`
chain anywhere.

### 5. Why the fire is walkable

The search problem stays *Agent → Fire*. If the fire blocked movement, two
agents would have to route around each other's objectives, and the comparison
would be measuring task decomposition rather than search.

### 6. Clamping over validating

```python
max_obstacles = max(0, min(total_cells - num_agents - 1, int(total_cells * obstacle_ratio)))
```

`total_cells - num_agents - 1` reserves enough cells that the shuffled cell list
can never run out. The invariant is enforced where it's established, not checked
afterwards.

### 7. Defensive returns instead of exceptions

| Bad input | Response |
| --- | --- |
| No display | friendly message, exit code 1 |
| 500 failed generations | guaranteed-solvable fallback map |
| No route exists | normal `SearchResult(success=False)` |
| Agent count out of range | clamped |
| Cancel during window teardown | `except tk.TclError` |

In a GUI app an exception means a traceback and a lost session. A default means
the app keeps working.

## Try it

Make each design decision visible with a quick experiment. Start by adding a
sixth algorithm using only the registry:

```bash
# Add to algorithms.py:
#   def dijkstra(environment, start, goal, agent_id=1):
#       return ucs(environment, start, goal, agent_id)
# and to SEARCH_ALGORITHMS:  "Dijkstra": dijkstra
# and to ALGORITHM_NAMES:     "Dijkstra"

python - <<'PY'
import random
from environment import generate_environment
from algorithms import ucs

# Show that "Dijkstra" IS "UCS" - same object, same results.
env = generate_environment(10, 10, 1, weighted=True, rng=random.Random(7))
a = ucs(env, env.agents[0].position, env.fire_position, 1)
b = ucs(env, env.agents[0].position, env.fire_position, 1)
print("identical results:", a.path == b.path and a.path_cost == b.path_cost)
PY
```

Then verify the "fair comparison" claim directly:

```bash
python - <<'PY'
import random
from environment import generate_environment
from algorithms import ALGORITHM_NAMES, run_search

env = generate_environment(12, 12, 1, weighted=True, rng=random.Random(9))
snapshot = (sorted(env.obstacles), dict(env.cell_costs),
            env.fire_position,
            {a.id: a.position for a in env.agents})

for name in ALGORITHM_NAMES:
    run_search(name, env, env.agents[0].position, env.fire_position, 1)

after = (sorted(env.obstacles), dict(env.cell_costs),
         env.fire_position,
         {a.id: a.position for a in env.agents})
print("environment unchanged after all 5 algorithms:", snapshot == after)
PY
```

## Check yourself

- Why is duplicating the flood fill better than importing BFS?
- The app supports 2 agents. Why is that not "multi-agent AI"? What would real
  multi-agent AI require?
- Why is wall-clock time a poor metric here, and what would you use instead?

## Exercise

Pick one design decision you disagree with and write a 200-word argument
against it. Good candidates:

- Should each agent get its own search instead of all agents racing to the
  same fire cell?
- Should `statistics.py` be renamed to avoid shadowing the stdlib module?
- Should grid size be user-configurable rather than hard-coded?

---

# Session 13 — The GUI and the animation

**Goal:** understand the Tkinter event model well enough to change the UI
without breaking it.

## Read

- `ui.py:48-51` — animation timing constants
- `ui.py:57-91` — `__init__` and all application state
- `ui.py:307-337` — `_sync_controls`, `_set_visible`, `_set_state`
- `ui.py:411-455` — `run_search`
- `ui.py:457-487` — `_animate_exploration`
- `ui.py:514-558` — `_animate_movement`
- `ui.py:727-735` — `_cancel_animation`
- `visualization.py:91-154` — `GridRenderer.draw`

## Key ideas

### You don't write the loop — Tkinter does

```
Create widgets  →  register callbacks  →  root.mainloop()
                                              ↓
                              Tkinter calls you back forever
```

Every `command=` and `variable=` is a callback registration.

### Animation with `after()`, never `time.sleep()`

```python
# WRONG - freezes the entire window
for cell in cells:
    self._draw(cell)
    time.sleep(0.05)

# RIGHT - returns immediately, window stays responsive
self.animation_job = self.root.after(18, step)
```

`after(ms, fn)` schedules `fn` on the event loop and returns at once. `step`
draws a little more and reschedules itself. The window can still be dragged,
and the animation can be cancelled at all.

### The token pattern — race-free cancellation

A user can hit **Reset** or **Run Search** while an animation is running. The
old `after()` callback may already be queued. Cancelling the job isn't
*sufficient*, because of the window between "due" and "runs".

```python
def _cancel_animation(self):
    self.animation_token += 1          # every old callback is now stale
    if self.animation_job is not None:
        try:
            self.root.after_cancel(self.animation_job)
        except tk.TclError:
            pass

def step():
    if token != self.animation_token:   # stale? leave immediately
        return
    ...
```

Each animation captures `token` when it starts. Cancelling increments the
counter, so every previously captured token mismatches and those callbacks
return before touching anything. **No locks, no globals, no race.**

### `pack_forget` forgets its options

```python
@staticmethod
def _set_visible(widget, visible, **pack_options):
    if visible:
        if not widget.winfo_manager():      # currently not laid out?
            widget.pack(**pack_options)     # always re-supply the options
    else:
        widget.pack_forget()
```

Tkinter does **not** remember how a widget was packed. After `pack_forget()`, a
bare `pack()` restores it with *default* options and the layout breaks. Hence
options are passed explicitly at every call site.

### `tk` vs `ttk`

`Radiobutton` and `Label` stay classic `tk` because the project sets explicit
background colours to match its palette, and themed widgets ignore those.
`Combobox`, `Treeview`, `Button` are `ttk` because there's no classic equivalent
with the same capability.

### Painting order *is* the layering

`GridRenderer.draw()` (`visualization.py:91-154`) repaints everything in a fixed
order:

```
1. cell backgrounds
2. explored cells (amber)
3. paths (one colour per agent)
4. fire
5. agents            <- last, so they sit on top
6. extinguished badge
7. cell costs        <- but skipped over symbols
```

Later items paint over earlier ones. That's why the agent stays visible on the
fire cell, and why the green `OK` badge exists at all — without it the agent
would completely hide the fire.

The whole canvas is deleted and rebuilt each time (`canvas.delete("all")`).
At 10×10 that's a few hundred items — far below any threshold where rebuilding
hurts, and it removes an entire category of state-sync bugs. There is no way for
the display to disagree with the model, because the display is thrown away and
rebuilt from the model every frame.

## Try it

Make the animation visible and tunable. Change `MOVE_FRAME_MS` from `110` to
`20` — the agent now walks 5× faster:

```bash
grep -n "MOVE_FRAME_MS\|EXPLORE_FRAME_MS\|EXPLORE_CELLS_PER_FRAME" ui.py
```

Then try the fragile part. Add a **sixth** button to `_build_buttons` that
cancels a running animation, and confirm no error dialog appears when you spam it
mid-animation:

```python
# temporary experiment in ui.py
ttk.Button(bar, text="Panic Cancel", command=self._cancel_animation).pack(side=tk.LEFT, padx=3)
```

Press **Run Search**, then mash **Panic Cancel**. No traceback should appear.

Then break the layout rule deliberately. Change `_set_visible` to this and click
between 1 and 2 agents:

```python
@staticmethod
def _set_visible(widget, visible, **pack_options):
    if visible:
        widget.pack()          # BUG: options dropped
    else:
        widget.pack_forget()
```

The control panel visibly falls apart. Then restore it and confirm you understand
why the real version passes `**pack_options`.

Finally, inspect what was actually drawn — this is what the UI tests do:

```bash
python -c "
import re
src = open('visualization.py').read()
for m in re.finditer(r'canvas\.create_(\w+)\(', src):
    print(m.group(1))
" | sort | uniq -c
```

## Check yourself

- Why does `_animate_movement` slice the path with `[1:]`?
- Why does `_cancel_animation` wrap `after_cancel` in `try/except`?
- If you called `time.sleep` in the animation loop, what would break?

## Exercise

Change `EXPLORE_CELLS_PER_FRAME` from `2` to `12` and `EXPLORE_FRAME_MS` from
`18` to `1`. The animation should now be effectively instant. Then find the
combination where exploration is *faster* than movement and explain why the app
looks broken. Finally, add a keyboard shortcut (say `R` to run the search) using
`root.bind("<KeyPress-r>", ...)` and confirm it works while an animation is
running — read `_cancel_animation` to see why it stays safe.

---

# Session 14 — Tests and the full experiment

**Goal:** read the tests as executable documentation, then run the definitive
comparison experiment yourself.

## Read

- `test_project.py:44-118` — the three fixtures and helpers
- `test_project.py:732-754` — `pump` and `settle`
- `test_project.py:96-118` — `assert_valid_path`
- One test class end to end: `test_project.py:646-676` (`TestHeuristic`)

## Key ideas

### Two fixtures whose answers you know by hand

```python
def make_open_environment(...):   # 5x5, no obstacles, (0,0) -> (4,4)
                                   # the answer is always exactly 8
def make_walled_environment():    # fire fully walled in
                                   # the answer is always: no path
```

When a test fails on one of these, you can verify the expected answer by hand in
seconds. Tests built on provably-known answers are worth far more than tests
asserting numbers the implementation produced itself.

### `assert_valid_path` — invariants, not examples

```python
def assert_valid_path(test, result, environment, start, goal):
    ...
    for first, second in zip(result.path, result.path[1:]):
        distance = abs(first[0]-second[0]) + abs(first[1]-second[1])
        test.assertEqual(distance, 1, f"{first} -> {second} is not a single step")

    expected = sum(environment.cost_of(cell) for cell in result.path[1:])
    test.assertEqual(result.path_cost, expected)
```

Instead of asserting one specific expected path, this asserts the properties
*every* valid path must satisfy — then runs it against all five algorithms on
many maps. One wrong line in this helper checks everything at once.

**The key property:** the cost is **recomputed independently**, not by calling
`environment.path_cost()`. If both the algorithm and `path_cost()` shared a bug,
reusing it would make the test pass anyway. Independent recomputation is what
makes it a real check.

The `distance == 1` assertion proves the path is *connected*, not merely that its
endpoints are right — a subtle bug an endpoints-only check would miss.

### Deterministic GUI testing

```python
def settle(app, timeout=12.0):
    end = time.time() + timeout
    while app.animating and time.time() < end:   # wait on STATE, not on time
        app.root.update_idletasks()
        app.root.update()
        time.sleep(0.01)
    return not app.animating
```

`root.update()` processes pending events including due `after()` timers — without
it, a scheduled callback never fires and the test hangs. `update_idletasks()`
handles geometry only.

`settle` polls the app's own `animating` flag rather than sleeping a fixed time.
A `time.sleep(2)` would be too slow on a fast machine and flaky on a loaded CI
machine. This is the correct way to test asynchronous code.

And windows are never shown:

```python
root = tk.Tk()
root.withdraw()      # create it, don't display it
```

Widgets exist, lay out correctly, canvas items get created — the user just never
sees a window. That makes the suite CI-friendly.

## Try it

Run the suite, in both halves, so you see the ordering pay off:

```bash
# Everything
python -m unittest test_project -v 2>&1 | tail -20

# Just the logic (no display needed, finishes in about a second)
python -m unittest \
  test_project.TestEnvironment \
  test_project.TestCosts \
  test_project.TestMovement \
  test_project.TestPathMeasures \
  test_project.TestAlgorithmsUnweighted \
  test_project.TestAlgorithmsWeighted \
  test_project.TestHeuristic \
  test_project.TestStatistics -v 2>&1 | tail -8

# Count them
grep -c "    def test" test_project.py
```

On this machine the GUI tests will skip or the suite will fail to import,
because Tk's shared library is missing. Fix with `sudo pacman -S tk`, then
`xvfb-run -a python -m unittest test_project -v` to exercise them headlessly.

Now the definitive experiment. Everything you've learned, in one table:

```bash
python - <<'PY'
import random
from environment import generate_environment
from algorithms import ALGORITHM_NAMES, run_search

def mean(xs): return sum(xs) / len(xs)

samples = {n: {"cost": [], "len": [], "nodes": []} for n in ALGORITHM_NAMES}

for seed in range(300):
    env = generate_environment(12, 12, 1, weighted=(seed % 2 == 0),
                               rng=random.Random(seed))
    for name in ALGORITHM_NAMES:
        r = run_search(name, env, env.agents[0].position, env.fire_position, 1)
        if r.success:
            samples[name]["cost"].append(r.path_cost)
            samples[name]["len"].append(r.path_length)
            samples[name]["nodes"].append(r.nodes_explored)

print(f"{'Algorithm':20} {'avg cost':>9} {'avg moves':>10} {'avg cells':>10}")
for name in ALGORITHM_NAMES:
    s = samples[name]
    print(f"{name:20} {mean(s['cost']):9.1f} {mean(s['len']):10.1f} "
          f"{mean(s['nodes']):10.1f}")

best = min(mean(samples[n]["cost"]) for n in ALGORITHM_NAMES)
ucs_nodes = mean(samples["UCS"]["nodes"])
astar_nodes = mean(samples["A*"]["nodes"])
print(f"\nA* vs UCS: same cost? "
      f"{abs(mean(samples['A*']['cost']) - mean(samples['UCS']['cost'])) < 0.05}")
print(f"A* explores {100 * (ucs_nodes - astar_nodes) / ucs_nodes:.0f}% fewer cells")
print(f"Greedy explores {100 * mean(samples['Greedy Best-First']['nodes']) / ucs_nodes:.0f}% "
      f"of UCS's cells, at a worse cost "
      f"({mean(samples['Greedy Best-First']['cost']):.1f} vs {best:.1f})")
PY
```

Your numbers should match `README.md` exactly. When they do, you have proved the
system is deterministic and every claim in the documentation is true.

## Check yourself

- Why does `assert_valid_path` recompute the cost instead of calling
  `path_cost()`?
- Why does `settle` poll a flag instead of sleeping?
- The suite has 97 tests. How would you split them so a fast inner loop is
  possible?

## Exercise

Write your own test class and add it to `test_project.py`:

```python
class TestMyExperiment(unittest.TestCase):
    def test_astar_is_never_worse_than_bfs(self):
        for seed in range(40):
            env = generate_environment(12, 12, 1, weighted=True,
                                       rng=random.Random(seed))
            s, g = env.agents[0].position, env.fire_position
            b = bfs(env, s, g, 1)
            a = astar(env, s, g, 1)
            if b.success:
                self.assertLessEqual(a.path_cost, b.path_cost,
                                     f"A* worse than BFS on seed {seed}")
```

Then find a property that **fails**, and figure out whether it's your property or
a bug. `test_dfs_dives_deeply` only asserts DFS explores *fewer* nodes than BFS
on an empty grid — can you construct a map where DFS explores *more*? What does
that tell you about how fragile that test is?

---

## You've finished when you can answer these

1. Why is the comparison between the five algorithms *structurally* fair, not
   just procedurally?
2. What's the difference between completeness and optimality, and which
   algorithm in this project has one without the other?
3. Why is the Manhattan heuristic admissible here, and which single constant
   makes that true?
4. Why does `if new_cost < best_cost.get(neighbour, inf)` appear in UCS and A\*
   but nowhere in BFS, DFS or Greedy?
5. Explain the `n == goal` case. Why does `path_cost` skip `path[0]`?
6. Why is `time.sleep` unusable for animation, and what is `after()` used for
   instead?
7. Where is instance state held, and what breaks if it were a module global?
8. If you were reviewing this PR, what's the single most valuable improvement?

---

## Where to go next

- **Make the grid configurable** — move `DEFAULT_ROWS`/`DEFAULT_COLS` into the
  UI. Watch A\*'s advantage grow as the map gets larger; it's a compelling demo.
- **A real two-leg search** — plan `Agent → Water`, then `Water → Fire`, using
  `run_search` twice and drawing both segments. Makes the water requirement a
  genuine planning problem. (Session 12, exercise 1.)
- **Benchmark mode in the app** — a button that runs all five algorithms over N
  generated maps and plots the averages. Turns the session 14 table interactive.
- **Move `import tkinter` into the GUI test class** — so the 58 non-GUI tests
  run on any machine, with no Tk installed. The highest-value small fix in the
  project.
- **Rename `statistics.py`** — it shadows the stdlib module and will confuse
  anyone who writes a scratch script in this folder.
