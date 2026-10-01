"""
Environment handling for the Intelligent Firefighting Agent.

Responsible for:

    * creating the grid
    * random generation of obstacles, agents, fire and water station
    * generating and regenerating the random cell costs (weighted mode)
    * checking that positions are valid
    * checking valid movement
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

# The four legal actions. Diagonal movement is not allowed.
DIRECTIONS: dict[str, Position] = {
    "UP": (-1, 0),
    "DOWN": (1, 0),
    "LEFT": (0, -1),
    "RIGHT": (0, 1),
}


# ---------------------------------------------------------------------------
# Position validation
# ---------------------------------------------------------------------------

def validate_position(position: Position, rows: int, cols: int) -> bool:
    """True when the position lies inside a rows x cols grid."""
    row, col = position
    return 0 <= row < rows and 0 <= col < cols


def validate_placement(
    position: Position,
    rows: int,
    cols: int,
    taken: set[Position],
) -> bool:
    """True when the position is inside the grid AND not already taken.

    `taken` holds every cell already used by the fire, the water station, an
    agent or an obstacle. This is what guarantees that objects never overlap.
    """
    return validate_position(position, rows, cols) and position not in taken


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
        row, col = queue.popleft()
        for delta_row, delta_col in DIRECTIONS.values():
            neighbour = (row + delta_row, col + delta_col)
            if neighbour in seen or neighbour in obstacles:
                continue
            if not validate_position(neighbour, rows, cols):
                continue
            seen.add(neighbour)
            queue.append(neighbour)

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


def apply_weighted_costs(environment: Environment, rng: random.Random) -> None:
    """Turn weighted mode on and generate fresh random cell costs."""
    environment.weighted = True
    environment.cell_costs = generate_costs(
        environment.rows, environment.cols, rng
    )


def regenerate_costs(environment: Environment, rng: random.Random) -> None:
    """Generate new random cell costs but keep the whole environment.

    Obstacles, agents, fire and water station are left untouched. This is what
    makes a fair algorithm comparison possible: the terrain stays the same and
    only the costs change.
    """
    if not environment.weighted:
        # Nothing to show in unweighted mode, so simply turn costs on.
        apply_weighted_costs(environment, rng)
        return

    environment.cell_costs = generate_costs(
        environment.rows, environment.cols, rng
    )


def set_unweighted(environment: Environment) -> None:
    """Turn weighted mode off. Every cell then costs 1."""
    environment.weighted = False
    environment.cell_costs = {}


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

    The order matters: the special objects (fire, water, agents) are placed
    first, then obstacles are added in the remaining free cells. Because the
    special cells are never turned into obstacles, the objects can never
    overlap. If the result happens to be unsolvable it is simply generated
    again.
    """
    if rng is None:
        rng = random.Random()

    num_agents = max(MIN_AGENTS, min(MAX_AGENTS, num_agents))
    total_cells = rows * cols

    # A few guard rails so generation never asks for something impossible.
    max_obstacles = max(0, min(total_cells - num_agents - 2, int(total_cells * obstacle_ratio)))
    min_required_cells = num_agents + 2  # fire + water station

    for _ in range(max_attempts):
        free_cells = [
            (row, col) for row in range(rows) for col in range(cols)
        ]
        rng.shuffle(free_cells)

        taken: set[Position] = set()

        # 1. Place the fire.
        fire_position = free_cells.pop()
        taken.add(fire_position)

        # 2. Place the water station on a different cell.
        water_position = free_cells.pop()
        taken.add(water_position)

        # 3. Place the agents, each on its own unique cell.
        agents = [
            Agent(id=index + 1, position=free_cells.pop(), has_water=False)
            for index in range(num_agents)
        ]
        for agent in agents:
            taken.add(agent.position)

        # 4. Fill some of the remaining cells with obstacles.
        obstacles: set[Position] = set()
        for _ in range(max_obstacles):
            candidate = free_cells.pop()
            obstacles.add(candidate)
        taken.update(obstacles)

        environment = Environment(
            rows=rows,
            cols=cols,
            agents=agents,
            obstacles=obstacles,
            fire_position=fire_position,
            water_position=water_position,
            cell_costs={},
            weighted=False,
            start_positions=[agent.position for agent in agents],
        )

        if weighted:
            apply_weighted_costs(environment, rng)

        # 5. Keep the environment only if somebody can actually reach the fire.
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
    agents = [
        Agent(id=index + 1, position=(rows - 1, index), has_water=False)
        for index in range(num_agents)
    ]
    environment = Environment(
        rows=rows,
        cols=cols,
        agents=agents,
        obstacles=set(),
        fire_position=(0, cols - 1),
        water_position=(0, 0),
        cell_costs={},
        weighted=False,
        start_positions=[agent.position for agent in agents],
    )
    if weighted:
        apply_weighted_costs(environment, rng)
    return environment


# ---------------------------------------------------------------------------
# Movement
# ---------------------------------------------------------------------------

def can_move(environment: Environment, position: Position, direction: str) -> bool:
    """True when the agent may move one step in the given direction.

    A move is valid when the destination is inside the grid and is not an
    obstacle. Everything else (invalid direction, out of bounds, obstacle)
    is simply not allowed, and the caller does nothing.
    """
    delta = DIRECTIONS.get(direction.upper())
    if delta is None:
        return False

    row, col = position
    target = (row + delta[0], col + delta[1])
    return environment.is_walkable(target)


def neighbours(position: Position, obstacles: set[Position], rows: int, cols: int) -> list[Position]:
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
