"""
Classical AI search algorithms for the Intelligent Firefighting Agent.

All five algorithms share one simple interface:

    search(environment, start, goal, agent_id) -> SearchResult

Every algorithm:
    * only READS the environment (it never modifies it, so the same
      environment can be reused for a fair comparison)
    * returns exactly the same SearchResult structure, so the UI and the
      statistics code never have to be duplicated

How each algorithm decides which state to expand next:

    BFS                -> depth / number of steps      (no cost, no heuristic)
    DFS                -> deepest unexplored state    (no cost, no heuristic)
    UCS                -> g(n) accumulated path cost  (cost, no heuristic)
    Greedy Best-First  -> h(n) heuristic distance     (no cost, heuristic)
    A*                 -> f(n) = g(n) + h(n)          (cost, heuristic)

Definitions used throughout:

    g(n) = actual accumulated cost from the start to n
    h(n) = Manhattan distance from n to the goal
         = |row(n) - row(goal)| + |col(n) - col(goal)|
"""

from __future__ import annotations

import heapq
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Callable

from environment import neighbours, path_cost, path_length
from models import Environment, Position

# The five selectable algorithms, in the order they appear in the dropdown.
ALGORITHM_NAMES = ["BFS", "DFS", "UCS", "Greedy Best-First", "A*"]


# ---------------------------------------------------------------------------
# Result structure
# ---------------------------------------------------------------------------

@dataclass
class SearchResult:
    """The outcome of one search run.

    The same structure is returned by every algorithm, so the user interface
    only needs one piece of code to display any of them.
    """

    algorithm: str
    agent_id: int
    start: Position
    goal: Position
    path: list[Position] = field(default_factory=list)
    explored_cells: list[Position] = field(default_factory=list)
    path_length: int = 0
    path_cost: int = 0
    nodes_explored: int = 0
    execution_time_ms: float = 0.0
    success: bool = False

    @property
    def status(self) -> str:
        """Short SUCCESS / FAILURE word used in the statistics panel."""
        return "SUCCESS" if self.success else "FAILURE"


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def manhattan(a: Position, b: Position) -> int:
    """Heuristic h(n): Manhattan distance between two cells.

    This is the estimate of how many steps are still needed. In weighted mode
    it stays a valid (admissible) estimate because the cheapest possible cell
    still costs 1.
    """
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _reconstruct_path(
    came_from: dict[Position, Position],
    goal: Position,
) -> list[Position]:
    """Walk the parent links backwards to rebuild start -> ... -> goal.

    The start cell is deliberately not stored in `came_from` (a cell that is
    its own parent would create a loop), so the walk stops by itself when it
    arrives back at the start.
    """
    path = [goal]
    while path[-1] in came_from:
        path.append(came_from[path[-1]])
    path.reverse()
    return path


def _build_result(
    algorithm: str,
    agent_id: int,
    start: Position,
    goal: Position,
    environment: Environment,
    came_from: dict[Position, Position],
    explored_cells: list[Position],
    found: bool,
    start_time: float,
) -> SearchResult:
    """Turn the raw search data into a finished SearchResult.

    This is the single place where the statistics are calculated, so every
    algorithm reports its numbers in exactly the same way.
    """
    execution_time_ms = (time.perf_counter() - start_time) * 1000.0

    if found:
        path = _reconstruct_path(came_from, goal)
    else:
        path = []

    return SearchResult(
        algorithm=algorithm,
        agent_id=agent_id,
        start=start,
        goal=goal,
        path=path,
        explored_cells=explored_cells,
        path_length=path_length(path),
        path_cost=path_cost(environment, path),
        nodes_explored=len(explored_cells),
        execution_time_ms=execution_time_ms,
        success=found,
    )


# ---------------------------------------------------------------------------
# BFS - Breadth-First Search
# ---------------------------------------------------------------------------

def bfs(
    environment: Environment,
    start: Position,
    goal: Position,
    agent_id: int = 1,
) -> SearchResult:
    """Breadth-First Search using a queue.

    Explores level by level, so the first time the goal is reached it is
    reached in the fewest possible number of steps. Cell costs and the
    heuristic are both ignored.
    """
    start_time = time.perf_counter()

    queue = deque([start])
    came_from: dict[Position, Position] = {}
    visited = {start}
    explored: list[Position] = []
    found = False

    while queue:
        current = queue.popleft()
        explored.append(current)

        if current == goal:
            found = True
            break

        for neighbour in neighbours(
            current, environment.obstacles, environment.rows, environment.cols
        ):
            if neighbour in visited:
                continue
            visited.add(neighbour)
            came_from[neighbour] = current
            queue.append(neighbour)

    return _build_result(
        "BFS", agent_id, start, goal, environment,
        came_from, explored, found, start_time,
    )


# ---------------------------------------------------------------------------
# DFS - Depth-First Search
# ---------------------------------------------------------------------------

def dfs(
    environment: Environment,
    start: Position,
    goal: Position,
    agent_id: int = 1,
) -> SearchResult:
    """Depth-First Search using a stack.

    Dives as deep as possible and backtracks only when it gets stuck. The path
    it returns is a valid route but NOT necessarily a short or cheap one,
    which is exactly the point of including DFS in the comparison.
    """
    start_time = time.perf_counter()

    stack = [start]
    came_from: dict[Position, Position] = {}
    visited = {start}
    explored: list[Position] = []
    found = False

    while stack:
        current = stack.pop()
        explored.append(current)

        if current == goal:
            found = True
            break

        # Reversed, because a stack returns the LAST item that was added.
        for neighbour in reversed(
            neighbours(current, environment.obstacles, environment.rows, environment.cols)
        ):
            if neighbour in visited:
                continue
            visited.add(neighbour)
            came_from[neighbour] = current
            stack.append(neighbour)

    return _build_result(
        "DFS", agent_id, start, goal, environment,
        came_from, explored, found, start_time,
    )


# ---------------------------------------------------------------------------
# UCS - Uniform-Cost Search
# ---------------------------------------------------------------------------

def ucs(
    environment: Environment,
    start: Position,
    goal: Position,
    agent_id: int = 1,
) -> SearchResult:
    """Uniform-Cost Search using a priority queue.

    Always expands the cheapest known state (lowest g(n)), so in weighted mode
    it prefers a longer route over a shorter but more expensive one. In
    unweighted mode every cell costs 1 and UCS behaves like BFS.
    """
    start_time = time.perf_counter()

    # Heap entries are (cost, tie_breaker, position). The tie breaker keeps
    # the heap entries comparable and makes the order reproducible.
    counter = 0
    frontier: list[tuple[int, int, Position]] = [
        (environment.cost_of(start), counter, start)
    ]

    came_from: dict[Position, Position] = {}
    best_cost: dict[Position, int] = {start: environment.cost_of(start)}
    closed: set[Position] = set()
    explored: list[Position] = []
    found = False

    while frontier:
        cost_so_far, _, current = heapq.heappop(frontier)

        if current in closed:
            continue
        closed.add(current)
        explored.append(current)

        if current == goal:
            found = True
            break

        for neighbour in neighbours(
            current, environment.obstacles, environment.rows, environment.cols
        ):
            if neighbour in closed:
                continue

            new_cost = cost_so_far + environment.cost_of(neighbour)

            # Only push a state again if we found a cheaper way to reach it.
            if new_cost < best_cost.get(neighbour, float("inf")):
                best_cost[neighbour] = new_cost
                came_from[neighbour] = current
                counter += 1
                heapq.heappush(frontier, (new_cost, counter, neighbour))

    return _build_result(
        "UCS", agent_id, start, goal, environment,
        came_from, explored, found, start_time,
    )


# ---------------------------------------------------------------------------
# Greedy Best-First Search
# ---------------------------------------------------------------------------

def greedy_best_first(
    environment: Environment,
    start: Position,
    goal: Position,
    agent_id: int = 1,
) -> SearchResult:
    """Greedy Best-First Search using a priority queue.

    Always expands the state that LOOKS closest to the goal (lowest h(n)) and
    completely ignores the accumulated cost g(n). It is fast but its path is
    often longer or more expensive than necessary.
    """
    start_time = time.perf_counter()

    counter = 0
    frontier: list[tuple[int, int, Position]] = [
        (manhattan(start, goal), counter, start)
    ]

    came_from: dict[Position, Position] = {}
    discovered: set[Position] = {start}
    closed: set[Position] = set()
    explored: list[Position] = []
    found = False

    while frontier:
        _, _, current = heapq.heappop(frontier)

        if current in closed:
            continue
        closed.add(current)
        explored.append(current)

        if current == goal:
            found = True
            break

        for neighbour in neighbours(
            current, environment.obstacles, environment.rows, environment.cols
        ):
            if neighbour in closed:
                continue

            # Greedy does not compare costs, so the first parent that reaches
            # a cell is kept - the same rule BFS uses.
            if neighbour not in discovered:
                discovered.add(neighbour)
                came_from[neighbour] = current

            counter += 1
            heapq.heappush(
                frontier, (manhattan(neighbour, goal), counter, neighbour)
            )

    return _build_result(
        "Greedy Best-First", agent_id, start, goal, environment,
        came_from, explored, found, start_time,
    )


# ---------------------------------------------------------------------------
# A* Search
# ---------------------------------------------------------------------------

def astar(
    environment: Environment,
    start: Position,
    goal: Position,
    agent_id: int = 1,
) -> SearchResult:
    """A* search.

    Combines the real accumulated cost with the estimated remaining distance:

        f(n) = g(n) + h(n)

    In weighted mode g(n) really does include the random cell costs, which is
    what makes A* interesting: it balances what has been spent against what is
    still estimated to be needed.
    """
    start_time = time.perf_counter()

    counter = 0
    start_cost = environment.cost_of(start)
    frontier: list[tuple[int, int, int, Position]] = [
        (start_cost + manhattan(start, goal), counter, start_cost, start)
    ]

    came_from: dict[Position, Position] = {}
    best_cost: dict[Position, int] = {start: start_cost}
    closed: set[Position] = set()
    explored: list[Position] = []
    found = False

    while frontier:
        _, _, cost_so_far, current = heapq.heappop(frontier)

        if current in closed:
            continue
        closed.add(current)
        explored.append(current)

        if current == goal:
            found = True
            break

        for neighbour in neighbours(
            current, environment.obstacles, environment.rows, environment.cols
        ):
            if neighbour in closed:
                continue

            new_cost = cost_so_far + environment.cost_of(neighbour)

            if new_cost < best_cost.get(neighbour, float("inf")):
                best_cost[neighbour] = new_cost
                came_from[neighbour] = current
                counter += 1
                f_value = new_cost + manhattan(neighbour, goal)
                heapq.heappush(
                    frontier, (f_value, counter, new_cost, neighbour)
                )

    return _build_result(
        "A*", agent_id, start, goal, environment,
        came_from, explored, found, start_time,
    )


# ---------------------------------------------------------------------------
# Algorithm registry
# ---------------------------------------------------------------------------

SEARCH_ALGORITHMS: dict[str, Callable[..., SearchResult]] = {
    "BFS": bfs,
    "DFS": dfs,
    "UCS": ucs,
    "Greedy Best-First": greedy_best_first,
    "A*": astar,
}


def run_search(
    algorithm_name: str,
    environment: Environment,
    start: Position,
    goal: Position,
    agent_id: int = 1,
) -> SearchResult:
    """Run one named algorithm on the given problem.

    This single function is what the user interface calls, so adding a new
    algorithm only means writing it here and adding it to the registry.
    """
    search_function = SEARCH_ALGORITHMS[algorithm_name]
    return search_function(environment, start, goal, agent_id)
