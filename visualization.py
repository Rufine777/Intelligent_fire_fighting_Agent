"""
Grid drawing for the Intelligent Firefighting Agent.

Everything visual lives here, so the algorithms never have to know that a GUI
exists. The renderer is a plain class that owns one tkinter.Canvas and knows
how to paint:

    * the empty cells
    * the obstacles
    * the explored cells
    * the final path of each agent
    * the agents, the fire and the water station
    * the random cell costs (weighted mode only)

Cell representation:

    A1 / A2 = agent 1 / agent 2
    F       = fire
    W       = water station
    X       = obstacle
    1-9     = movement cost of the cell (weighted mode only)
"""

from __future__ import annotations

import tkinter as tk

from models import Agent, Environment, Position

# A small, readable colour scheme.
COLORS = {
    "background": "#eef1f5",
    "cell": "#ffffff",
    "cell_border": "#b0bec5",
    "obstacle": "#455a64",
    "obstacle_text": "#ffffff",
    "explored": "#ffe082",
    "path_1": "#1e88e5",
    "path_2": "#8e24aa",
    "agent_1": "#0d47a1",
    "agent_2": "#4a148c",
    "agent_active_border": "#00e676",
    "fire": "#e53935",
    "water": "#039be5",
    "extinguished": "#2e7d32",
    "cost_text": "#455a64",
    "legend_text": "#37474f",
}

# Colour used for the path of each agent (index 0 -> agent 1, index 1 -> agent 2).
PATH_COLORS = [COLORS["path_1"], COLORS["path_2"]]
AGENT_COLORS = [COLORS["agent_1"], COLORS["agent_2"]]

# Font sizes, kept in one place so the look stays consistent.
CELL_FONT = ("Consolas", 13, "bold")
COST_FONT = ("Consolas", 9)


class GridRenderer:
    """Draws the environment on a tkinter.Canvas."""

    def __init__(self, canvas: tk.Canvas, cell_size: int = 48) -> None:
        self.canvas = canvas
        self.cell_size = cell_size
        self.rows = 0
        self.cols = 0

    # -- geometry helpers --------------------------------------------------

    def cell_origin(self, position: Position) -> tuple[int, int]:
        """Top-left corner (x, y) of a cell."""
        row, col = position
        return col * self.cell_size, row * self.cell_size

    def cell_center(self, position: Position) -> tuple[float, float]:
        """Centre point (x, y) of a cell - used for drawing path lines."""
        x, y = self.cell_origin(position)
        return x + self.cell_size / 2, y + self.cell_size / 2

    def configure(self, environment: Environment) -> None:
        """Resize the canvas so it exactly fits the given environment."""
        self.rows = environment.rows
        self.cols = environment.cols
        self.canvas.config(
            width=environment.cols * self.cell_size,
            height=environment.rows * self.cell_size,
        )

    # -- drawing -----------------------------------------------------------

    def draw(
        self,
        environment: Environment,
        explored_cells: list[Position] | set[Position] | None = None,
        paths: dict[int, list[Position]] | None = None,
        active_agent_id: int | None = None,
        fire_extinguished: bool = False,
    ) -> None:
        """Redraw the whole grid from scratch.

        Args:
            environment: the environment to show.
            explored_cells: cells the search already looked at.
            paths: {agent_id: path} so each agent gets its own colour.
            active_agent_id: which agent is selected in manual mode.
            fire_extinguished: True once an agent has put the fire out, which
                adds a small tick so the fire cell stays visible underneath
                the agent that is standing on it.
        """
        self.configure(environment)
        canvas = self.canvas
        canvas.delete("all")

        explored = set(explored_cells or [])
        paths = paths or {}
        agent_positions = {agent.position: agent for agent in environment.agents}

        # 1. Cell backgrounds (walkable / obstacle).
        for row in range(environment.rows):
            for col in range(environment.cols):
                position = (row, col)
                x, y = self.cell_origin(position)
                is_obstacle = position in environment.obstacles
                fill = COLORS["obstacle"] if is_obstacle else COLORS["cell"]
                canvas.create_rectangle(
                    x, y, x + self.cell_size, y + self.cell_size,
                    fill=fill, outline=COLORS["cell_border"], width=1,
                )

        # 2. Explored cells (light highlight), only on walkable ground.
        for position in explored:
            if position in environment.obstacles or not environment.in_bounds(position):
                continue
            x, y = self.cell_origin(position)
            canvas.create_rectangle(
                x + 1, y + 1, x + self.cell_size - 1, y + self.cell_size - 1,
                fill=COLORS["explored"], outline="",
            )

        # 3. Final paths, one colour per agent.
        for agent_id, path in paths.items():
            self._draw_path(path, self._agent_color(agent_id))

        # 4. Objects: water station, fire, then the agents on top.
        self._draw_marker(environment.water_position, "W", COLORS["water"], "#ffffff")
        self._draw_marker(
            environment.fire_position, "F", COLORS["fire"], "#ffffff"
        )

        for agent in environment.agents:
            self._draw_agent(agent, active_agent_id)

        if fire_extinguished:
            self._draw_extinguished_badge(environment.fire_position)

        # 5. Cell costs, only in weighted mode and only on plain empty cells.
        if environment.weighted:
            self._draw_costs(environment, agent_positions)

    # -- private drawing helpers ------------------------------------------

    def _agent_color(self, agent_id: int) -> str:
        """Agent 1 uses colour 0, agent 2 uses colour 1."""
        return PATH_COLORS[(agent_id - 1) % len(PATH_COLORS)]

    def _draw_path(self, path: list[Position], color: str) -> None:
        """Draw a path as a connected line through the cell centres."""
        if len(path) < 2:
            return
        points: list[float] = []
        for position in path:
            x, y = self.cell_center(position)
            points.extend([x, y])
        self.canvas.create_line(
            *points, fill=color, width=max(4, self.cell_size // 7),
            capstyle=tk.ROUND, joinstyle=tk.ROUND,
        )

    def _draw_marker(
        self, position: Position, symbol: str, fill: str, text_color: str
    ) -> None:
        """Draw a simple coloured square with a symbol (fire, water)."""
        x, y = self.cell_origin(position)
        inset = self.cell_size // 6
        self.canvas.create_rectangle(
            x + inset, y + inset, x + self.cell_size - inset, y + self.cell_size - inset,
            fill=fill, outline="",
        )
        self.canvas.create_text(
            x + self.cell_size / 2, y + self.cell_size / 2,
            text=symbol, fill=text_color, font=CELL_FONT,
        )

    def _draw_agent(self, agent: Agent, active_agent_id: int | None) -> None:
        """Draw one agent as a coloured square labelled A1 / A2.

        The agent that is currently selected in manual mode gets a green
        outline so the user can see who is being controlled.
        """
        x, y = self.cell_origin(agent.position)
        color = AGENT_COLORS[(agent.id - 1) % len(AGENT_COLORS)]
        inset = self.cell_size // 6

        outline = COLORS["agent_active_border"] if agent.id == active_agent_id else color
        outline_width = 3 if agent.id == active_agent_id else 1

        self.canvas.create_rectangle(
            x + inset, y + inset, x + self.cell_size - inset, y + self.cell_size - inset,
            fill=color, outline=outline, width=outline_width,
        )
        self.canvas.create_text(
            x + self.cell_size / 2, y + self.cell_size / 2,
            text=agent.label, fill="#ffffff", font=CELL_FONT,
        )

    def _draw_extinguished_badge(self, position: Position) -> None:
        """A small green tick on the fire cell once the fire is out.

        The agent is drawn on top of the fire, so without this badge the
        symbol would disappear and it would be unclear what happened.
        """
        x, y = self.cell_origin(position)
        radius = self.cell_size / 3
        self.canvas.create_oval(
            x + self.cell_size - radius - 1, y + 1,
            x + self.cell_size - 1, y + radius + 1,
            fill=COLORS["extinguished"], outline="#ffffff", width=1,
        )
        self.canvas.create_text(
            x + self.cell_size - radius / 2 - 1, y + radius / 2 + 1,
            text="OK", fill="#ffffff", font=("Segoe UI", 6, "bold"),
        )
    def _draw_costs(
        self,
        environment: Environment,
        agent_positions: dict[Position, Agent],
    ) -> None:
        """Write the cost number inside each walkable cell.

        Costs are never drawn on top of an agent, the fire, the water station
        or an obstacle, so the symbols stay readable.
        """
        for row in range(environment.rows):
            for col in range(environment.cols):
                position = (row, col)
                if position in environment.obstacles:
                    continue
                if position in agent_positions:
                    continue
                if position == environment.fire_position:
                    continue
                if position == environment.water_position:
                    continue

                x, y = self.cell_origin(position)
                self.canvas.create_text(
                    x + self.cell_size - 7, y + self.cell_size - 7,
                    text=str(environment.cell_costs.get(position, 1)),
                    fill=COLORS["cost_text"], font=COST_FONT, anchor="se",
                )


def build_legend(parent: tk.Misc) -> tk.Frame:
    """A small colour legend shown under the grid.

    Keeps the grid readable without adding any extra dependency.
    """
    legend = tk.Frame(parent, bg=COLORS["background"])
    entries = [
        ("A1 / A2", COLORS["agent_1"]),
        ("F  Fire", COLORS["fire"]),
        ("W  Water", COLORS["water"]),
        ("X  Obstacle", COLORS["obstacle"]),
        ("Explored", COLORS["explored"]),
        ("Path", COLORS["path_1"]),
    ]
    for text, color in entries:
        swatch = tk.Canvas(legend, width=14, height=14, highlightthickness=0, bg=COLORS["background"])
        swatch.create_rectangle(1, 1, 13, 13, fill=color, outline=COLORS["cell_border"])
        swatch.pack(side=tk.LEFT, padx=(6, 2))
        label = tk.Label(legend, text=text, bg=COLORS["background"],
                         fg=COLORS["legend_text"], font=("Segoe UI", 8))
        label.pack(side=tk.LEFT, padx=(0, 8))
    return legend
