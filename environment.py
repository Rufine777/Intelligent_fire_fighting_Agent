"""
Environment handling for the Intelligent Firefighting Agent.

Responsible for:

    * creating the grid
    * random generation of obstacles, agents and the fire
    * generating and regenerating the random cell costs (weighted mode)
    * the rules of the grid: legal neighbours, path length, path cost
    * simple retry logic so the generated environment is actually solvable

The module never uses the search algorithms from algorithms.py. The
solvability check below is a plain flood fill, which is enough for validation.
"""

from __future__ import annotations

import random
from collections import deque

from models import (
    DEFAULT_COLS,
    DEFAULT_OBSTACLE_RATIO,
    DEFAULT_ROWS,
    MAX_AGENTS,
    MAX_CELL_COST,
    MIN_AGENTS,
    MIN_CELL_COST,
    Agent,
    Environment,
    Position,
)


# ---------------------------------------------------------------------------
# Grid rules
# ---------------------------------------------------------------------------

def validate_position(position: Position, rows: int, cols: int) -> bool:
    """True when the position lies inside a rows x cols grid."""
    row, col = position
    return 0 <= row < rows and 0 <= col < cols


def neighbours(
    position: Position, obstacles: set[Position], rows: int, cols: int
) -> list[Position]:
    """The walkable up/down/left/right neighbours of a cell.

    The order is fixed (UP, RIGHT, DOWN, LEFT) so that every algorithm
    explores the grid in a predictable order. This makes the visualisation
    easy to follow and the results reproducible.
    """
    row, col = position
    result: list[Position] = []
    for delta_row, delta_col in ((-1, 0), (0, 1), (1, 0), (0, -1)):
        target = (row + delta_row, col + delta_col)
        if validate_position(target, rows, cols) and target not in obstacles:
            result.append(target)
    return result


def path_cost(environment: Environment, path: list[Position]) -> int:
    """Total cost of a path.

    The cost of a path is the sum of the movement costs of every cell entered,
    which means the starting cell is not counted. In unweighted mode this is
    exactly the number of moves.
    """
    if len(path) < 2:
        return 0
    return sum(environment.cost_of(cell) for cell in path[1:])


def path_length(path: list[Position]) -> int:
    """Number of moves in a path. The starting cell is not a move."""
    return max(0, len(path) - 1)


# ---------------------------------------------------------------------------
# Reachability (used only to validate a generated environment)
# ---------------------------------------------------------------------------

def reachable_cells(
    start: Position,
    rows: int,
    cols: int,
    obstacles: set[Position],
) -> set[Position]:
    """Simple flood fill returning every cell reachable from `start`.

    This is plain BFS used only for generation/validation. It is deliberately
    kept here so that environment.py does not depend on algorithms.py.
    """
    seen = {start}
    queue = deque([start])

    while queue:
        for target in neighbours(queue.popleft(), obstacles, rows, cols):
            if target not in seen:
                seen.add(target)
                queue.append(target)

    return seen


def is_solvable(environment: Environment) -> bool:
    """True when at least one agent can reach the fire.

    The generated environment should preferably be solvable, so this is the
    condition the generation loop retries on.
    """
    for agent in environment.agents:
        reachable = reachable_cells(
            agent.position, environment.rows, environment.cols, environment.obstacles
        )
        if environment.fire_position in reachable:
            return True
    return False


# ---------------------------------------------------------------------------
# Cost generation
# ---------------------------------------------------------------------------

def generate_costs(
    rows: int,
    cols: int,
    rng: random.Random,
) -> dict[Position, int]:
    """Give every cell of the grid a random cost between MIN and MAX_COST."""
    return {
        (row, col): rng.randint(MIN_CELL_COST, MAX_CELL_COST)
        for row in range(rows)
        for col in range(cols)
    }


def regenerate_costs(environment: Environment, rng: random.Random) -> None:
    """Turn weighted mode on and give every cell a fresh random cost.

    Obstacles, agents and the fire are left untouched. That is what makes a
    fair algorithm comparison possible: the terrain stays the same and only
    the costs change.
    """
    environment.weighted = True
    environment.cell_costs = generate_costs(
        environment.rows, environment.cols, rng
    )


# ---------------------------------------------------------------------------
# Environment generation
# ---------------------------------------------------------------------------

def generate_environment(
    rows: int = DEFAULT_ROWS,
    cols: int = DEFAULT_COLS,
    num_agents: int = 1,
    weighted: bool = False,
    obstacle_ratio: float = DEFAULT_OBSTACLE_RATIO,
    rng: random.Random | None = None,
    max_attempts: int = 500,
) -> Environment:
    """Generate a random, solvable environment.

    A shuffled list of cells is dealt out in order: the fire, then one cell per
    agent, then the obstacles. Because the cells are dealt without replacement
    the objects can never overlap. If the result happens to be unsolvable it is
    simply generated again.
    """
    if rng is None:
        rng = random.Random()

    num_agents = max(MIN_AGENTS, min(MAX_AGENTS, num_agents))
    total_cells = rows * cols

    # Leave enough room for the fire and the agents, never filling the grid.
    max_obstacles = max(
        0, min(total_cells - num_agents - 1, int(total_cells * obstacle_ratio))
    )

    for _ in range(max_attempts):
        free_cells = [(row, col) for row in range(rows) for col in range(cols)]
        rng.shuffle(free_cells)

        fire_position = free_cells[0]
        start_positions = free_cells[1:1 + num_agents]
        obstacles = set(free_cells[1 + num_agents:1 + num_agents + max_obstacles])

        environment = Environment(
            rows=rows,
            cols=cols,
            agents=[
                Agent(id=index + 1, position=position)
                for index, position in enumerate(start_positions)
            ],
            obstacles=obstacles,
            fire_position=fire_position,
            start_positions=list(start_positions),
        )

        if weighted:
            regenerate_costs(environment, rng)

        # Keep the environment only if somebody can actually reach the fire.
        if is_solvable(environment):
            return environment

    # Extremely unlikely fallback: an empty grid is always solvable.
    return _fallback_environment(rows, cols, num_agents, weighted, rng)


def _fallback_environment(
    rows: int,
    cols: int,
    num_agents: int,
    weighted: bool,
    rng: random.Random,
) -> Environment:
    """A guaranteed-safe environment with no obstacles at all."""
    environment = Environment(
        rows=rows,
        cols=cols,
        agents=[
            Agent(id=index + 1, position=(rows - 1, index))
            for index in range(num_agents)
        ],
        obstacles=set(),
        fire_position=(0, cols - 1),
        start_positions=[(rows - 1, index) for index in range(num_agents)],
    )
    if weighted:
        regenerate_costs(environment, rng)
    return environment