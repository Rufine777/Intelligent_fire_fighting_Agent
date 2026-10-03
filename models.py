"""
Data structures for the Intelligent Firefighting Agent project.

This module holds the simple "models" used by the whole application:

    Agent          - one firefighting agent
    Environment    - the grid world (obstacles, fire, costs)
    SearchResult   - the outcome of one search run

Nothing in this module performs any work; it only describes the data.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Simple configuration constants (easy to change)
# ---------------------------------------------------------------------------

# Default grid size. Change these two numbers to resize the environment.
DEFAULT_ROWS = 10
DEFAULT_COLS = 10

# Fraction of the grid that is filled with obstacles when generating.
DEFAULT_OBSTACLE_RATIO = 0.15

# Minimum / maximum number of agents supported by the application.
MIN_AGENTS = 1
MAX_AGENTS = 2

# Range used when generating random cell costs in weighted mode.
MIN_CELL_COST = 1
MAX_CELL_COST = 9

# A position inside the grid. row first, then column (like matrix[row][col]).
Position = tuple[int, int]


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

@dataclass
class Agent:
    """A single firefighting agent.

    The agent is deliberately simple. It only needs to know where it is.
    """

    id: int
    position: Position

    @property
    def label(self) -> str:
        """Short label used on the grid and in the statistics panel."""
        return f"A{self.id}"


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

@dataclass
class Environment:
    """The grid world in which the agents move.

    A cell is walkable when it is inside the grid and is not an obstacle.
    Every walkable cell has a movement cost:
        * unweighted mode -> cost is always 1
        * weighted mode   -> cost is a random number between 1 and 9

    The fire and the obstacles are all treated as ordinary walkable cells for
    the search algorithms. The search only has to avoid the obstacles; the
    single problem being solved is Agent -> Fire.
    """

    rows: int
    cols: int
    agents: list[Agent] = field(default_factory=list)
    obstacles: set[Position] = field(default_factory=set)
    fire_position: Position = (0, 0)
    cell_costs: dict[Position, int] = field(default_factory=dict)
    weighted: bool = False
    # Where each agent started. Keeping this lets Reset put the agents back
    # without changing the problem, so every algorithm faces the same one.
    start_positions: list[Position] = field(default_factory=list)

    # -- basic grid queries ------------------------------------------------

    def in_bounds(self, pos: Position) -> bool:
        """True when the position lies inside the grid."""
        row, col = pos
        return 0 <= row < self.rows and 0 <= col < self.cols

    def is_walkable(self, pos: Position) -> bool:
        """True when the agent is allowed to stand on this cell."""
        return self.in_bounds(pos) and pos not in self.obstacles

    def cost_of(self, pos: Position) -> int:
        """Movement cost of entering a cell.

        In unweighted mode every cell costs 1. In weighted mode the random
        cost that was generated for that cell is returned.
        """
        if not self.weighted:
            return 1
        return self.cell_costs.get(pos, 1)

    def get_agent(self, agent_id: int) -> Agent | None:
        """Return the agent with the given id, or None if it does not exist."""
        for agent in self.agents:
            if agent.id == agent_id:
                return agent
        return None
