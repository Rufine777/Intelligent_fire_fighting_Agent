"""
The Tkinter user interface for the Intelligent Firefighting Agent.

One single window contains everything:

    * the control panel (mode, number of agents, path mode, algorithm)
    * the grid, drawn on a tkinter.Canvas
    * the buttons
    * the statistics panel
    * the algorithm comparison table

Keyboard control is only active in Manual Mode, and only the selected agent
responds. Search animation uses after() so the window never freezes.
"""

from __future__ import annotations

import random
import tkinter as tk
from tkinter import ttk

import environment as env_module
from algorithms import ALGORITHM_NAMES, SearchResult, run_search
from models import (
    Agent,
    DEFAULT_COLS,
    DEFAULT_ROWS,
    MAX_AGENTS,
    MIN_AGENTS,
    Environment,
    Position,
)
from statistics import (
    COMPARISON_COLUMNS,
    comparison_row,
    overall_status,
    result_statistics,
)
from visualization import COLORS, GridRenderer, build_legend

# --- animation timing -------------------------------------------------------
# Cells revealed per animation frame, and the delay between frames. Small
# values keep the search quick; larger values make it easier to follow.
EXPLORE_CELLS_PER_FRAME = 2
EXPLORE_FRAME_MS = 18
MOVE_FRAME_MS = 110
PATH_FRAME_MS = 60

# Keyboard: arrow keys and WASD both work.
KEY_DIRECTIONS = {
    "Up": "UP",
    "Down": "DOWN",
    "Left": "LEFT",
    "Right": "RIGHT",
    "w": "UP",
    "a": "LEFT",
    "s": "DOWN",
    "d": "RIGHT",
}


class FirefightingApp:
    """The whole application, held in one small class."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Intelligent Firefighting Agent")
        self.root.configure(bg=COLORS["background"])
        self.root.resizable(False, False)

        # --- application state (no global variables are used) -------------
        self.mode = tk.StringVar(value="manual")
        self.agent_count = tk.IntVar(value=1)
        self.path_mode = tk.StringVar(value="unweighted")
        self.algorithm = tk.StringVar(value="BFS")
        self.active_agent = tk.IntVar(value=1)
        self.status_text = tk.StringVar(value="Press 'Generate Environment' to begin.")

        self.environment: Environment | None = None
        self.results: dict[int, SearchResult] = {}
        self.comparison: dict[str, tuple[str, ...]] = {}
        # The visualisation currently painted on the grid.
        self.shown_explored: set[Position] = set()
        self.shown_paths: dict[int, list[Position]] = {}
        self.animation_job: str | None = None
        self.animation_token = 0
        self.animating = False
        self.mission_finished = False

        self._build_widgets()
        self._sync_controls()
        self.generate_environment()

    # =====================================================================
    # Building the interface
    # =====================================================================

    def _build_widgets(self) -> None:
        self._build_header()
        self._build_controls()
        self._build_body()
        self._build_buttons()
        self._build_status_bar()
        self._bind_keys()

    def _build_header(self) -> None:
        header = tk.Label(
            self.root,
            text="INTELLIGENT FIREFIGHTING AGENT",
            bg=COLORS["fire"],
            fg="#ffffff",
            font=("Segoe UI", 16, "bold"),
            pady=12,
        )
        header.pack(fill=tk.X)

        subtitle = tk.Label(
            self.root,
            text="Classical AI search (BFS, DFS, UCS, Greedy, A*) in a grid fire environment",
            bg=COLORS["background"],
            fg=COLORS["legend_text"],
            font=("Segoe UI", 9),
            pady=4,
        )
        subtitle.pack(fill=tk.X)

    def _build_controls(self) -> None:
        outer = tk.Frame(self.root, bg=COLORS["background"])
        outer.pack(fill=tk.X, padx=12, pady=(6, 0))

        # Row 1: Mode | Number of agents | Path mode
        row1 = tk.Frame(outer, bg=COLORS["background"])
        row1.pack(fill=tk.X, pady=3)

        self.mode_frame = self._labeled_group(row1, "MODE", "left")
        for text, value in (("Manual", "manual"), ("AI", "ai")):
            tk.Radiobutton(
                self.mode_frame, text=text, value=value, variable=self.mode,
                command=self._on_mode_changed, bg=COLORS["background"],
                activebackground=COLORS["background"], font=("Segoe UI", 9),
            ).pack(side=tk.LEFT, padx=4)

        self.agent_count_frame = self._labeled_group(row1, "NUMBER OF AGENTS", "left")
        for value in range(MIN_AGENTS, MAX_AGENTS + 1):
            tk.Radiobutton(
                self.agent_count_frame, text=str(value), value=value,
                variable=self.agent_count, command=self._on_agent_count_changed,
                bg=COLORS["background"], activebackground=COLORS["background"],
                font=("Segoe UI", 9),
            ).pack(side=tk.LEFT, padx=4)

        self.path_mode_frame = self._labeled_group(row1, "PATH MODE", "left")
        for text, value in (("Unweighted", "unweighted"), ("Weighted", "weighted")):
            tk.Radiobutton(
                self.path_mode_frame, text=text, value=value, variable=self.path_mode,
                command=self._on_path_mode_changed, bg=COLORS["background"],
                activebackground=COLORS["background"], font=("Segoe UI", 9),
            ).pack(side=tk.LEFT, padx=4)

        # Row 2: Algorithm | Active agent
        row2 = tk.Frame(outer, bg=COLORS["background"])
        row2.pack(fill=tk.X, pady=3)

        self.algorithm_frame = self._labeled_group(row2, "ALGORITHM", "left")
        self.algorithm_box = ttk.Combobox(
            self.algorithm_frame, textvariable=self.algorithm,
            values=ALGORITHM_NAMES, state="readonly", width=18,
        )
        self.algorithm_box.pack(side=tk.LEFT, padx=4)

        self.active_agent_frame = self._labeled_group(row2, "ACTIVE AGENT", "left")
        for value in (1, 2):
            tk.Radiobutton(
                self.active_agent_frame, text=f"Agent {value}", value=value,
                variable=self.active_agent, command=self._on_active_agent_changed,
                bg=COLORS["background"], activebackground=COLORS["background"],
                font=("Segoe UI", 9),
            ).pack(side=tk.LEFT, padx=4)

        ttk.Separator(outer, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=8)

    def _labeled_group(
        self, parent: tk.Misc, title: str, side: str
    ) -> tk.Frame:
        """A group box with a small caption, used for the control rows."""
        group = tk.LabelFrame(
            parent, text=title, bg=COLORS["background"], fg=COLORS["legend_text"],
            font=("Segoe UI", 8, "bold"), padx=6, pady=4,
        )
        group.pack(side=side, padx=(0, 10), anchor="n")
        return group

    def _build_body(self) -> None:
        body = tk.Frame(self.root, bg=COLORS["background"])
        body.pack(fill=tk.BOTH, expand=True, padx=12)

        # --- left: the grid (the main focus of the window) ---------------
        grid_frame = tk.LabelFrame(
            body, text="GRID", bg=COLORS["background"], fg=COLORS["legend_text"],
            font=("Segoe UI", 9, "bold"), padx=8, pady=8,
        )
        grid_frame.pack(side=tk.LEFT, anchor="n")

        self.canvas = tk.Canvas(
            grid_frame, width=DEFAULT_COLS * 48, height=DEFAULT_ROWS * 48,
            bg=COLORS["cell_border"], highlightthickness=0,
        )
        self.canvas.pack()
        self.renderer = GridRenderer(self.canvas, cell_size=48)
        build_legend(grid_frame).pack(pady=(8, 0))

        # --- right: statistics + comparison -------------------------------
        right = tk.Frame(body, bg=COLORS["background"])
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(12, 0))

        self.stats_frames: dict[int, tk.LabelFrame] = {}
        self.stats_labels: dict[int, dict[str, tk.Label]] = {}
        for agent_id in (1, 2):
            frame, labels = self._build_stats_group(right, agent_id)
            self.stats_frames[agent_id] = frame
            self.stats_labels[agent_id] = labels
            frame.pack(fill=tk.X, pady=(0, 8))

        self._build_comparison_table(right)

    def _build_stats_group(
        self, parent: tk.Misc, agent_id: int
    ) -> tuple[tk.LabelFrame, dict[str, tk.Label]]:
        """One statistics block per agent."""
        frame = tk.LabelFrame(
            parent, text=f"AGENT {agent_id}", bg=COLORS["background"],
            fg=COLORS["legend_text"], font=("Segoe UI", 9, "bold"),
            padx=10, pady=6,
        )
        labels: dict[str, tk.Label] = {}

        for name in ("Algorithm", "Path Length", "Path Cost", "Nodes Explored",
                     "Execution Time", "Status"):
            tk.Label(
                frame, text=f"{name}:", bg=COLORS["background"],
                fg=COLORS["legend_text"], font=("Segoe UI", 9), anchor="w",
            ).grid(row=len(labels), column=0, sticky="w", pady=1)
            value_label = tk.Label(
                frame, text="-", bg=COLORS["background"], fg="#000000",
                font=("Segoe UI", 9, "bold"), anchor="w", width=16,
            )
            value_label.grid(row=len(labels), column=1, sticky="w", pady=1)
            labels[name] = value_label

        return frame, labels

    def _build_comparison_table(self, parent: tk.Misc) -> None:
        """Table where every algorithm run on this environment is recorded."""
        frame = tk.LabelFrame(
            parent, text="ALGORITHM COMPARISON (same environment)",
            bg=COLORS["background"], fg=COLORS["legend_text"],
            font=("Segoe UI", 9, "bold"), padx=8, pady=6,
        )
        frame.pack(fill=tk.BOTH, expand=True)

        self.comparison_tree = ttk.Treeview(
            frame, columns=COMPARISON_COLUMNS, show="headings", height=5,
        )
        widths = [110, 55, 50, 55, 70, 60]
        for column, width in zip(COMPARISON_COLUMNS, widths):
            self.comparison_tree.heading(column, text=column)
            self.comparison_tree.column(column, width=width, anchor="w")
        self.comparison_tree.pack(fill=tk.BOTH, expand=True)

    def _build_buttons(self) -> None:
        bar = tk.Frame(self.root, bg=COLORS["background"])
        bar.pack(fill=tk.X, padx=12, pady=10)

        ttk.Button(bar, text="Generate Environment", command=self.generate_environment).pack(
            side=tk.LEFT, padx=3
        )
        self.regenerate_button = ttk.Button(
            bar, text="Regenerate Costs", command=self.regenerate_costs
        )
        self.regenerate_button.pack(side=tk.LEFT, padx=3)
        self.run_button = ttk.Button(bar, text="Run Search", command=self.run_search)
        self.run_button.pack(side=tk.LEFT, padx=3)
        ttk.Button(bar, text="Reset", command=self.reset_view).pack(side=tk.LEFT, padx=3)

    def _build_status_bar(self) -> None:
        bar = tk.Frame(self.root, bg="#37474f")
        bar.pack(fill=tk.X, side=tk.BOTTOM)

        self.status_label = tk.Label(
            bar, textvariable=self.status_text, bg="#37474f", fg="#ffffff",
            font=("Segoe UI", 10, "bold"), anchor="w", padx=12, pady=8,
        )
        self.status_label.pack(fill=tk.X)

    def _bind_keys(self) -> None:
        self.root.bind("<KeyPress>", self._on_key_press)
        # Stop any running animation when the window is closed, otherwise
        # Tkinter would complain about a callback that no longer exists.
        self.root.bind("<Destroy>", self._on_destroy)
        self.root.focus_set()

    def _on_destroy(self, event: tk.Event) -> None:
        if event.widget is self.root:
            self._cancel_animation()

    # =====================================================================
    # Control visibility
    # =====================================================================

    def _sync_controls(self) -> None:
        """Show or hide the controls that do not apply to the current mode.

        This is what keeps the interface clean:
            * no algorithm selector in Manual Mode
            * no active-agent selector in AI Mode or with a single agent
            * no "Regenerate Costs" button in Unweighted Mode
            * no Agent 2 statistics with a single agent
        """
        is_ai = self.mode.get() == "ai"
        is_weighted = self.path_mode.get() == "weighted"
        has_two_agents = self.agent_count.get() == MAX_AGENTS

        self._set_visible(self.algorithm_frame, is_ai, side=tk.LEFT,
                          padx=(0, 10), anchor="n")
        self._set_visible(self.active_agent_frame,
                          not is_ai and has_two_agents,
                          side=tk.LEFT, padx=(0, 10), anchor="n")
        self._set_visible(self.stats_frames[2], has_two_agents,
                          fill=tk.X, pady=(0, 8))
        self._set_state(self.regenerate_button, is_weighted)
        self._set_state(self.run_button, is_ai and self.environment is not None)

    @staticmethod
    def _set_visible(widget: tk.Widget, visible: bool, **pack_options) -> None:
        """Show or hide a widget, remembering how it has to be packed.

        Tkinter forgets the layout options when a widget is hidden, so they
        are passed again here every time the widget becomes visible.
        """
        if visible:
            if not widget.winfo_manager():
                widget.pack(**pack_options)
        else:
            widget.pack_forget()

    @staticmethod
    def _set_state(widget: tk.Widget, enabled: bool) -> None:
        """Enable or disable a ttk widget."""
        widget.state(["!disabled"] if enabled else ["disabled"])

    # =====================================================================
    # Environment
    # =====================================================================

    def generate_environment(self) -> None:
        """Create a brand new environment and show it."""
        self._cancel_animation()
        self.environment = env_module.generate_environment(
            rows=DEFAULT_ROWS,
            cols=DEFAULT_COLS,
            num_agents=self.agent_count.get(),
            weighted=self.path_mode.get() == "weighted",
        )
        self.reset_view(regenerate_comparison=True)
        self._set_status(
            f"New environment generated: {self.environment.rows} x "
            f"{self.environment.cols}, {len(self.environment.obstacles)} obstacles.",
        )
        self._sync_controls()

    def regenerate_costs(self) -> None:
        """New random cell costs, but the exact same environment.

        Obstacles, agents, fire and water station stay where they are, so two
        algorithms can be compared on identical terrain.
        """
        if self.environment is None:
            return
        self._cancel_animation()
        env_module.regenerate_costs(self.environment, random.Random())
        self._redraw()
        self.reset_view(regenerate_comparison=False)
        self._set_status("New random cell costs generated (environment unchanged).")

    def _on_agent_count_changed(self) -> None:
        self._sync_controls()
        self.generate_environment()

    def _on_path_mode_changed(self) -> None:
        self._sync_controls()
        self.generate_environment()

    def _on_mode_changed(self) -> None:
        self.reset_view()
        self._sync_controls()
        if self.mode.get() == "manual":
            self._set_status(
                "Manual Mode: use Arrow keys or W A S D to move the selected agent. "
                "Collect water at W first, then reach F."
            )
        else:
            self._set_status(
                "AI Mode: the agent is dispatched carrying water. The search "
                "problem solved is Agent -> Fire. Pick an algorithm and run it."
            )

    def _on_active_agent_changed(self) -> None:
        self._redraw()

    # =====================================================================
    # Drawing
    # =====================================================================

    def _redraw(
        self,
        explored: set[Position] | None = None,
        paths: dict[int, list[Position]] | None = None,
    ) -> None:
        """Repaint the grid.

        Without arguments the last visualisation (explored cells and the
        found paths) is redrawn, so the finished result stays on screen.
        """
        if self.environment is None:
            return
        active = self.active_agent.get() if self.mode.get() == "manual" else None
        self.renderer.draw(
            self.environment,
            explored_cells=self.shown_explored if explored is None else explored,
            paths=self.shown_paths if paths is None else paths,
            active_agent_id=active,
            fire_extinguished=self.mission_finished,
        )

    # =====================================================================
    # Manual mode
    # =====================================================================

    def _on_key_press(self, event: tk.Event) -> None:
        """Keyboard handler. Only Manual Mode uses the keyboard."""
        if self.mode.get() != "manual" or self.environment is None:
            return

        direction = KEY_DIRECTIONS.get(event.keysym) or KEY_DIRECTIONS.get(
            event.keysym.lower()
        )
        if direction is None:
            return

        self._move_active_agent(direction)

    def _move_active_agent(self, direction: str) -> None:
        """Move the selected agent one step, if that is allowed."""
        if self.environment is None or self.mission_finished:
            return

        agent = self.environment.get_agent(self.active_agent.get())
        if agent is None:
            return

        # An invalid move (out of bounds or into an obstacle) simply does
        # nothing at all.
        if not env_module.can_move(self.environment, agent.position, direction):
            return

        delta_row, delta_col = env_module.DIRECTIONS[direction]
        row, col = agent.position
        agent.position = (row + delta_row, col + delta_col)

        self._redraw()
        self._check_manual_state(agent)

    def _check_manual_state(self, agent: Agent) -> None:
        """Pick up water and detect the fire after a manual move."""
        if self.environment is None:
            return

        if agent.position == self.environment.water_position and not agent.has_water:
            agent.has_water = True
            self._redraw()
            self._set_status(f"Agent {agent.id} picked up water at the water station.")
            return

        if agent.position == self.environment.fire_position:
            if agent.has_water:
                self.mission_finished = True
                self._redraw()
                self._set_status(
                    f"SUCCESS - Fire extinguished by Agent {agent.id}!",
                    color=COLORS["fire"],
                )
            else:
                self._set_status(
                    f"Agent {agent.id} reached the fire without water. "
                    "Go to the water station (W) first.",
                )

    # =====================================================================
    # AI mode: running and animating the search
    # =====================================================================

    def run_search(self) -> None:
        """Run the chosen algorithm for every agent on the same environment.

        The environment is never regenerated between agents or between
        algorithms, so the comparison is always fair.
        """
        if self.environment is None or self.mode.get() != "ai":
            return

        self._cancel_animation()
        self.mission_finished = False
        self.shown_explored = set()
        self.shown_paths = {}

        # In AI Mode the agent leaves the station already carrying water, so
        # the search problem stays the simple one: Agent -> Fire. (If the route
        # happens to pass the water station, the agent refills there anyway.)
        for agent in self.environment.agents:
            agent.has_water = True

        results = [
            run_search(
                self.algorithm.get(),
                self.environment,
                agent.position,
                self.environment.fire_position,
                agent.id,
            )
            for agent in self.environment.agents
        ]
        self.results = {result.agent_id: result for result in results}

        self._update_statistics()
        self._record_comparison()
        self._redraw()

        if any(result.success for result in results):
            self._set_status(
                f"{self.algorithm.get()}: found a route to the fire. "
                "Animating the search..."
            )
        else:
            self._set_status(
                f"{self.algorithm.get()}: no route exists. "
                f"{len(results[0].explored_cells) if results else 0} cells explored.",
                color="#c62828",
            )

        self._animate_exploration(results)

    def _animate_exploration(self, results: list[SearchResult]) -> None:
        """Reveal the explored cells step by step, then draw the paths.

        All agents are animated together, one explored cell per agent per
        frame, so the two searches stay visually comparable.
        """
        self.animation_token += 1
        token = self.animation_token
        self.animating = True
        order = [result.explored_cells for result in results]
        longest = max((len(cells) for cells in order), default=0)
        cursor = 0

        def step() -> None:
            nonlocal cursor
            if token != self.animation_token:
                return

            if cursor >= longest:
                self._finish_search_animation(results)
                return

            explored: set[Position] = set()
            for cells in order:
                for cell in cells[cursor:cursor + EXPLORE_CELLS_PER_FRAME]:
                    explored.add(cell)
            cursor += EXPLORE_CELLS_PER_FRAME

            self.shown_explored = explored
            self._redraw()
            self.animation_job = self.root.after(
                EXPLORE_FRAME_MS, step
            )

        self.animation_job = self.root.after(0, step)

    def _finish_search_animation(self, results: list[SearchResult]) -> None:
        """Exploration finished: draw the final path, then move the agents."""
        explored: set[Position] = set()
        paths: dict[int, list[Position]] = {}
        for result in results:
            explored.update(result.explored_cells)
            if result.success:
                paths[result.agent_id] = result.path

        # Remember the result so it stays on the grid after the animation.
        self.shown_explored = explored
        self.shown_paths = paths
        self._redraw()

        if not paths:
            # Nothing to walk: finish straight away instead of animating.
            self.animation_job = self.root.after(
                PATH_FRAME_MS, lambda: self._complete_mission(results)
            )
            return

        self.animation_job = self.root.after(
            PATH_FRAME_MS, lambda: self._animate_movement(results, paths, explored)
        )

    def _animate_movement(
        self,
        results: list[SearchResult],
        paths: dict[int, list[Position]],
        explored: set[Position],
    ) -> None:
        """Walk each agent along its own path, one cell per frame."""
        self.animation_token += 1
        token = self.animation_token
        if self.environment is None:
            return

        # The moves still to perform. The first cell of a path is the cell the
        # agent already stands on, so it is not a move.
        moves = {
            result.agent_id: paths.get(result.agent_id, [])[1:]
            for result in results
        }
        step_index = 0
        longest = max((len(sequence) for sequence in moves.values()), default=0)

        def step() -> None:
            nonlocal step_index
            if token != self.animation_token or self.environment is None:
                return

            for agent_id, sequence in moves.items():
                if step_index >= len(sequence):
                    continue
                agent = self.environment.get_agent(agent_id)
                if agent is None:
                    continue
                agent.position = sequence[step_index]
                # Passing the water station refills the agent.
                if agent.position == self.environment.water_position:
                    agent.has_water = True

            step_index += 1
            self._redraw()

            if step_index >= longest:
                self._complete_mission(results)
                return

            self.animation_job = self.root.after(MOVE_FRAME_MS, step)

        self.animation_job = self.root.after(0, step)

    def _complete_mission(self, results: list[SearchResult]) -> None:
        """Final message once the animation is over."""
        if self.environment is not None:
            for result in results:
                agent = self.environment.get_agent(result.agent_id)
                if agent is not None and result.success:
                    agent.has_water = True

        self.mission_finished = any(result.success for result in results)
        self.animating = False
        self.animation_job = None
        self._redraw()

        status, message = overall_status(results)
        color = COLORS["fire"] if status == "SUCCESS" else "#c62828"
        self._set_status(f"{status} - {message}", color=color)

    # =====================================================================
    # Statistics
    # =====================================================================

    def _update_statistics(self) -> None:
        """Fill the statistics blocks from the last search results."""
        for agent_id, labels in self.stats_labels.items():
            result = self.results.get(agent_id)
            if result is None:
                for name in labels:
                    labels[name].config(text="-", fg="#000000")
                continue

            for name, value in result_statistics(result):
                labels[name].config(text=value)
            labels["Status"].config(
                fg=COLORS["fire"] if result.success else "#c62828"
            )

    def _record_comparison(self) -> None:
        """Store this run in the comparison table (one row per algorithm).

        With two agents the row of Agent 1 is recorded, and the algorithm
        name is suffixed with the agent id so nothing is ambiguous.
        """
        if not self.results:
            return
        result = self.results[min(self.results)]
        row = list(comparison_row(result))
        if len(self.results) > 1:
            row[0] = f"{row[0]} (A{result.agent_id})"
        self.comparison[result.algorithm] = tuple(row)

        self.comparison_tree.delete(*self.comparison_tree.get_children())
        for entry in self.comparison.values():
            self.comparison_tree.insert("", tk.END, values=entry)

    def _clear_statistics(self) -> None:
        for labels in self.stats_labels.values():
            for name in labels:
                labels[name].config(text="-", fg="#000000")

    def _set_status(self, message: str, color: str = "#ffffff") -> None:
        """Update the coloured status bar at the bottom of the window."""
        self.status_text.set(message)
        self.status_label.config(fg=color)

    # =====================================================================
    # Reset
    # =====================================================================

    def reset_view(self, regenerate_comparison: bool = True) -> None:
        """Clear the search visualisation and the statistics.

        The environment itself is kept, so the same problem can immediately
        be given to another algorithm.
        """
        self._cancel_animation()
        self.mission_finished = False
        self.results = {}
        self.shown_explored = set()
        self.shown_paths = {}
        self._clear_statistics()

        if regenerate_comparison:
            self.comparison = {}
            self.comparison_tree.delete(*self.comparison_tree.get_children())

        self._restore_agent_positions()
        self._redraw()

    def _restore_agent_positions(self) -> None:
        """Put the agents back on their starting cells.

        The starting positions are stored when the environment is created, so
        Reset never changes the problem that the algorithms are given.
        """
        if self.environment is None:
            return
        for index, agent in enumerate(self.environment.agents):
            if index < len(self.environment.start_positions):
                agent.position = self.environment.start_positions[index]
            agent.has_water = False

    def _cancel_animation(self) -> None:
        """Stop any running animation before starting something new."""
        self.animation_token += 1
        self.animating = False
        if self.animation_job is not None:
            try:
                self.root.after_cancel(self.animation_job)
            except tk.TclError:
                pass
            self.animation_job = None
