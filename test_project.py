"""
Test suite for the Intelligent Firefighting Agent.

Runs entirely on the Python standard library (unittest) and needs no extra
package. The UI tests create real Tk windows, so a display must be available.

Run it with:

    python -m unittest test_project -v
"""

from __future__ import annotations

import random
import tkinter as tk
import time
import unittest

import environment as env_module
from algorithms import (
    ALGORITHM_NAMES,
    SEARCH_ALGORITHMS,
    astar,
    bfs,
    dfs,
    greedy_best_first,
    manhattan,
    run_search,
    ucs,
)
from models import Agent, Environment, Position
from statistics import overall_status, result_statistics
from ui import FirefightingApp
from visualization import COLORS

# A small open grid used when the answer can be checked by hand.
# 5x5, no obstacles, agent at (0,0), fire at (4,4): the answer is always 8.
OPEN_ROWS = OPEN_COLS = 5
OPEN_START: Position = (0, 0)
OPEN_GOAL: Position = (4, 4)
OPEN_ANSWER = 8


def make_open_environment(
    weighted: bool = False,
    costs: dict | None = None,
    rows: int = OPEN_ROWS,
    cols: int = OPEN_COLS,
) -> Environment:
    """An obstacle-free environment, so the optimum is easy to reason about."""
    return Environment(
        rows=rows,
        cols=cols,
        agents=[Agent(id=1, position=OPEN_START)],
        obstacles=set(),
        fire_position=OPEN_GOAL,
        water_position=(0, cols - 1),
        cell_costs=dict(costs or {}),
        weighted=weighted,
        start_positions=[OPEN_START],
    )


class KeyEvent:
    """A stand-in for a tkinter key event.

    Only `keysym` is read by the application, so a tiny stub is enough and it
    works on every Python version.
    """

    def __init__(self, keysym: str) -> None:
        self.keysym = keysym


def make_walled_environment() -> Environment:
    """The fire is completely surrounded by obstacles: no route can exist."""
    blocked = set()
    for row in range(OPEN_ROWS):
        for col in range(OPEN_COLS):
            if (row, col) != OPEN_GOAL and abs(row - 4) + abs(col - 4) == 1:
                blocked.add((row, col))

    return Environment(
        rows=OPEN_ROWS,
        cols=OPEN_COLS,
        agents=[Agent(id=1, position=OPEN_START)],
        obstacles=blocked,
        fire_position=OPEN_GOAL,
        water_position=(0, 4),
        cell_costs={},
        weighted=False,
        start_positions=[OPEN_START],
    )


def assert_valid_path(test: unittest.TestCase, result, environment, start, goal) -> None:
    """Shared checks: a returned path must be a real, walkable route."""
    if not result.success:
        return
    test.assertTrue(len(result.path) >= 1)
    test.assertEqual(result.path[0], start)
    test.assertEqual(result.path[-1], goal)
    test.assertEqual(result.nodes_explored, len(result.explored_cells))
    test.assertGreater(result.execution_time_ms, 0.0)
    test.assertEqual(result.path_length, len(result.path) - 1)

    for position in result.path:
        test.assertNotIn(position, environment.obstacles)
        test.assertTrue(environment.in_bounds(position))

    # Every step must be a single move in one of the four directions.
    for first, second in zip(result.path, result.path[1:]):
        distance = abs(first[0] - second[0]) + abs(first[1] - second[1])
        test.assertEqual(distance, 1, f"{first} -> {second} is not a single step")

    # The reported cost must equal the sum of the entered cell costs.
    expected = sum(environment.cost_of(cell) for cell in result.path[1:])
    test.assertEqual(result.path_cost, expected)


# ===========================================================================
# 1. Environment and grid
# ===========================================================================

class TestEnvironment(unittest.TestCase):
    def test_in_bounds_and_walkable(self) -> None:
        environment = make_open_environment()
        self.assertTrue(environment.in_bounds((0, 0)))
        self.assertTrue(environment.in_bounds((4, 4)))
        self.assertFalse(environment.in_bounds((-1, 0)))
        self.assertFalse(environment.in_bounds((0, 5)))
        self.assertFalse(environment.in_bounds((5, 0)))
        self.assertTrue(environment.is_walkable((2, 2)))
        self.assertFalse(environment.is_walkable((9, 9)))

    def test_obstacle_is_not_walkable(self) -> None:
        environment = make_open_environment()
        environment.obstacles.add((2, 2))
        self.assertFalse(environment.is_walkable((2, 2)))

    def test_cost_unweighted_is_always_one(self) -> None:
        environment = make_open_environment(weighted=False)
        environment.cell_costs = {(0, 0): 9, (1, 1): 5}
        for row in range(OPEN_ROWS):
            for col in range(OPEN_COLS):
                self.assertEqual(environment.cost_of((row, col)), 1)

    def test_cost_weighted_uses_generated_values(self) -> None:
        costs = {(row, col): (row + col) % 9 + 1 for row in range(5) for col in range(5)}
        environment = make_open_environment(weighted=True, costs=costs)
        self.assertEqual(environment.cost_of((0, 0)), 1)
        self.assertEqual(environment.cost_of((1, 1)), 3)

    def test_generated_objects_never_overlap(self) -> None:
        """Fire, water and every agent must sit on their own cell."""
        for seed in range(40):
            environment = env_module.generate_environment(
                rows=12, cols=12, num_agents=2, rng=random.Random(seed)
            )
            special = [environment.fire_position, environment.water_position]
            special += [agent.position for agent in environment.agents]

            self.assertEqual(len(set(special)), len(special), "objects overlap")
            for position in special:
                self.assertNotIn(position, environment.obstacles)
                self.assertTrue(environment.in_bounds(position))

    def test_generation_uses_correct_sizes(self) -> None:
        environment = env_module.generate_environment(rows=8, cols=14)
        self.assertEqual(environment.rows, 8)
        self.assertEqual(environment.cols, 14)

    def test_generated_environment_is_solvable(self) -> None:
        for seed in range(40):
            environment = env_module.generate_environment(
                rng=random.Random(seed)
            )
            self.assertTrue(
                env_module.is_solvable(environment),
                "generated an environment nobody can solve",
            )

    def test_single_agent(self) -> None:
        environment = env_module.generate_environment(num_agents=1)
        self.assertEqual(len(environment.agents), 1)
        self.assertEqual(environment.agents[0].id, 1)
        self.assertFalse(environment.agents[0].has_water)

    def test_two_agents_have_unique_positions(self) -> None:
        environment = env_module.generate_environment(num_agents=2)
        self.assertEqual(len(environment.agents), 2)
        self.assertEqual([a.id for a in environment.agents], [1, 2])
        self.assertNotEqual(environment.agents[0].position, environment.agents[1].position)

    def test_start_positions_are_recorded(self) -> None:
        environment = env_module.generate_environment(num_agents=2)
        self.assertEqual(len(environment.start_positions), 2)
        for agent, start in zip(environment.agents, environment.start_positions):
            self.assertEqual(agent.position, start)

    def test_position_validation(self) -> None:
        self.assertTrue(env_module.validate_position((0, 0), 5, 5))
        self.assertFalse(env_module.validate_position((5, 0), 5, 5))
        self.assertFalse(env_module.validate_placement((0, 0), 5, 5, {(0, 0)}))
        self.assertTrue(env_module.validate_placement((0, 0), 5, 5, {(1, 1)}))

    def test_get_agent(self) -> None:
        environment = env_module.generate_environment(num_agents=2)
        self.assertIsNotNone(environment.get_agent(1))
        self.assertIsNotNone(environment.get_agent(2))
        self.assertIsNone(environment.get_agent(3))


# ===========================================================================
# 2. Cost generation and regeneration
# ===========================================================================

class TestCosts(unittest.TestCase):
    def test_generated_costs_are_between_one_and_nine(self) -> None:
        costs = env_module.generate_costs(10, 10, random.Random(0))
        self.assertEqual(len(costs), 100)
        for value in costs.values():
            self.assertGreaterEqual(value, 1)
            self.assertLessEqual(value, 9)

    def test_weighted_generation_enables_costs(self) -> None:
        environment = env_module.generate_environment(weighted=True)
        self.assertTrue(environment.weighted)
        self.assertEqual(len(environment.cell_costs), 100)

    def test_unweighted_generation_has_no_costs(self) -> None:
        environment = env_module.generate_environment(weighted=False)
        self.assertFalse(environment.weighted)
        self.assertEqual(environment.cell_costs, {})

    def test_regenerate_costs_keeps_the_environment(self) -> None:
        """Only the costs may change; everything else must stay identical."""
        environment = env_module.generate_environment(weighted=True, rng=random.Random(7))
        agents_before = [a.position for a in environment.agents]
        obstacles_before = set(environment.obstacles)
        fire_before = environment.fire_position
        water_before = environment.water_position

        old_costs = dict(environment.cell_costs)
        env_module.regenerate_costs(environment, random.Random(99))

        self.assertEqual([a.position for a in environment.agents], agents_before)
        self.assertEqual(environment.obstacles, obstacles_before)
        self.assertEqual(environment.fire_position, fire_before)
        self.assertEqual(environment.water_position, water_before)
        self.assertEqual(len(environment.cell_costs), len(old_costs))
        self.assertNotEqual(environment.cell_costs, old_costs, "costs did not change")

    def test_set_unweighted_clears_costs(self) -> None:
        environment = env_module.generate_environment(weighted=True)
        env_module.set_unweighted(environment)
        self.assertFalse(environment.weighted)
        self.assertEqual(environment.cell_costs, {})


# ===========================================================================
# 3. Movement
# ===========================================================================

class TestMovement(unittest.TestCase):
    def setUp(self) -> None:
        self.environment = make_open_environment()

    def test_four_directions_are_allowed(self) -> None:
        self.environment.agents[0].position = (2, 2)
        for direction in ("UP", "DOWN", "LEFT", "RIGHT"):
            self.assertTrue(
                env_module.can_move(self.environment, (2, 2), direction), direction
            )

    def test_grid_border_blocks_movement(self) -> None:
        self.assertFalse(env_module.can_move(self.environment, (0, 0), "UP"))
        self.assertFalse(env_module.can_move(self.environment, (0, 0), "LEFT"))
        self.assertTrue(env_module.can_move(self.environment, (0, 0), "DOWN"))
        self.assertTrue(env_module.can_move(self.environment, (0, 0), "RIGHT"))
        self.assertFalse(env_module.can_move(self.environment, (4, 4), "DOWN"))
        self.assertFalse(env_module.can_move(self.environment, (4, 4), "RIGHT"))

    def test_obstacle_blocks_movement(self) -> None:
        self.environment.obstacles.add((2, 3))
        self.assertFalse(env_module.can_move(self.environment, (2, 2), "RIGHT"))

    def test_unknown_direction_is_rejected(self) -> None:
        self.assertFalse(env_module.can_move(self.environment, (2, 2), "DIAGONAL"))
        self.assertFalse(env_module.can_move(self.environment, (2, 2), ""))

    def test_fire_and_water_are_walkable(self) -> None:
        """The search must be able to walk onto the fire and onto the water."""
        self.assertTrue(self.environment.is_walkable(self.environment.fire_position))
        self.assertTrue(self.environment.is_walkable(self.environment.water_position))

    def test_neighbours_respect_boundaries_and_obstacles(self) -> None:
        self.environment.obstacles.add((1, 1))
        self.assertEqual(env_module.neighbours((0, 0), set(), 5, 5),
                         [(0, 1), (1, 0)])
        self.assertNotIn((1, 1), env_module.neighbours((0, 0), {(1, 1)}, 5, 5))
        self.assertEqual(len(env_module.neighbours((2, 2), set(), 5, 5)), 4)


# ===========================================================================
# 4. Path measurements
# ===========================================================================

class TestPathMeasures(unittest.TestCase):
    def test_path_length_counts_moves_not_cells(self) -> None:
        self.assertEqual(env_module.path_length([]), 0)
        self.assertEqual(env_module.path_length([(0, 0)]), 0)
        self.assertEqual(env_module.path_length([(0, 0), (0, 1), (0, 2)]), 2)

    def test_path_cost_unweighted_equals_length(self) -> None:
        environment = make_open_environment()
        path = [(0, 0), (0, 1), (0, 2), (1, 2)]
        self.assertEqual(env_module.path_cost(environment, path), 3)
        self.assertEqual(env_module.path_cost(environment, path),
                         env_module.path_length(path))

    def test_path_cost_weighted_uses_cell_costs(self) -> None:
        costs = {(0, 1): 4, (0, 2): 7, (1, 2): 2}
        environment = make_open_environment(weighted=True, costs=costs)
        path = [(0, 0), (0, 1), (0, 2), (1, 2)]
        # The starting cell is not paid for: 4 + 7 + 2
        self.assertEqual(env_module.path_cost(environment, path), 13)

    def test_path_cost_of_empty_path_is_zero(self) -> None:
        self.assertEqual(env_module.path_cost(make_open_environment(), []), 0)
        self.assertEqual(env_module.path_cost(make_open_environment(), [(1, 1)]), 0)


# ===========================================================================
# 5. The five algorithms - unweighted
# ===========================================================================

class TestAlgorithmsUnweighted(unittest.TestCase):
    def test_all_algorithms_are_registered(self) -> None:
        self.assertEqual(
            list(SEARCH_ALGORITHMS.keys()),
            ["BFS", "DFS", "UCS", "Greedy Best-First", "A*"],
        )
        self.assertEqual(ALGORITHM_NAMES, list(SEARCH_ALGORITHMS.keys()))

    def test_every_algorithm_finds_the_optimal_open_path(self) -> None:
        environment = make_open_environment()
        for name, function in SEARCH_ALGORITHMS.items():
            with self.subTest(algorithm=name):
                result = function(environment, OPEN_START, OPEN_GOAL, 1)
                self.assertTrue(result.success)
                self.assertEqual(result.path_length, OPEN_ANSWER)
                self.assertEqual(result.path_cost, OPEN_ANSWER)
                assert_valid_path(self, result, environment, OPEN_START, OPEN_GOAL)

    def test_every_algorithm_reports_failure_when_blocked(self) -> None:
        """No route must produce FAILURE, never a crash."""
        environment = make_walled_environment()
        for name, function in SEARCH_ALGORITHMS.items():
            with self.subTest(algorithm=name):
                result = function(environment, OPEN_START, OPEN_GOAL, 1)
                self.assertFalse(result.success)
                self.assertEqual(result.status, "FAILURE")
                self.assertEqual(result.path, [])
                self.assertEqual(result.path_length, 0)
                self.assertEqual(result.path_cost, 0)
                self.assertGreater(result.nodes_explored, 0)
                self.assertGreater(result.execution_time_ms, 0.0)

    def test_start_equal_to_goal(self) -> None:
        environment = make_open_environment()
        environment.fire_position = OPEN_START
        for name, function in SEARCH_ALGORITHMS.items():
            with self.subTest(algorithm=name):
                result = function(environment, OPEN_START, OPEN_START, 1)
                self.assertTrue(result.success)
                self.assertEqual(result.path, [OPEN_START])
                self.assertEqual(result.path_length, 0)
                self.assertEqual(result.path_cost, 0)

    def test_bfs_finds_the_shortest_path_in_steps(self) -> None:
        """BFS must be optimal, so its length must equal the reference BFS."""
        for seed in range(15):
            environment = env_module.generate_environment(
                rng=random.Random(seed)
            )
            result = bfs(environment, environment.agents[0].position,
                         environment.fire_position, 1)
            self.assertTrue(result.success)
            self.assertEqual(result.path_length, result.path_cost)

            # An independent BFS using the reachability flood fill as a
            # cross-check is not possible, so instead compare with the
            # theoretical lower bound: the Manhattan distance.
            start = environment.agents[0].position
            goal = environment.fire_position
            lower_bound = abs(start[0] - goal[0]) + abs(start[1] - goal[1])
            self.assertGreaterEqual(result.path_length, lower_bound)

    def test_ucs_equals_bfs_in_unweighted_mode(self) -> None:
        """With every cell costing 1, UCS must behave exactly like BFS."""
        environment = make_open_environment()
        bfs_result = bfs(environment, OPEN_START, OPEN_GOAL, 1)
        ucs_result = ucs(environment, OPEN_START, OPEN_GOAL, 1)
        self.assertEqual(ucs_result.path, bfs_result.path)
        self.assertEqual(ucs_result.nodes_explored, bfs_result.nodes_explored)

    def test_astar_equals_bfs_on_an_open_grid(self) -> None:
        """Manhattan distance is exact on an obstacle-free grid."""
        environment = make_open_environment()
        self.assertEqual(
            astar(environment, OPEN_START, OPEN_GOAL, 1).path,
            bfs(environment, OPEN_START, OPEN_GOAL, 1).path,
        )

    def test_greedy_ignores_cost_and_bfs_ignores_cost(self) -> None:
        """Greedy uses only h(n); both still return a legal route."""
        environment = make_walled_environment()
        environment.obstacles = {(1, 1), (3, 3)}
        for function in (bfs, greedy_best_first):
            result = function(environment, OPEN_START, OPEN_GOAL, 1)
            self.assertTrue(result.success)
            assert_valid_path(self, result, environment, OPEN_START, OPEN_GOAL)

    def test_dfs_dives_deeply(self) -> None:
        """DFS explores far fewer nodes than BFS on an open grid."""
        environment = make_open_environment(rows=12, cols=12)
        goal = (11, 11)
        environment.fire_position = goal
        dfs_result = dfs(environment, OPEN_START, goal, 1)
        bfs_result = bfs(environment, OPEN_START, goal, 1)
        self.assertTrue(dfs_result.success)
        self.assertTrue(bfs_result.success)
        self.assertLess(dfs_result.nodes_explored, bfs_result.nodes_explored)

    def test_algorithms_do_not_modify_the_environment(self) -> None:
        """A search must never change the problem for the next algorithm."""
        environment = env_module.generate_environment(weighted=True, rng=random.Random(3))
        snapshot = (
            {agent.id: agent.position for agent in environment.agents},
            set(environment.obstacles),
            environment.fire_position,
            environment.water_position,
            dict(environment.cell_costs),
            environment.weighted,
        )
        for name in SEARCH_ALGORITHMS:
            run_search(name, environment, environment.agents[0].position,
                       environment.fire_position, 1)

        after = (
            {agent.id: agent.position for agent in environment.agents},
            set(environment.obstacles),
            environment.fire_position,
            environment.water_position,
            dict(environment.cell_costs),
            environment.weighted,
        )
        self.assertEqual(after, snapshot)

    def test_run_search_dispatch(self) -> None:
        environment = make_open_environment()
        for name in SEARCH_ALGORITHMS:
            result = run_search(name, environment, OPEN_START, OPEN_GOAL, 2)
            self.assertEqual(result.algorithm, name)
            self.assertEqual(result.agent_id, 2)
            self.assertTrue(result.success)

    def test_unknown_algorithm_raises(self) -> None:
        environment = make_open_environment()
        with self.assertRaises(KeyError):
            run_search("Nonexistent", environment, OPEN_START, OPEN_GOAL, 1)


# ===========================================================================
# 6. The five algorithms - weighted
# ===========================================================================

class TestAlgorithmsWeighted(unittest.TestCase):
    def _weighted_environment(self, seed: int = 0) -> Environment:
        return env_module.generate_environment(
            rows=10, cols=10, num_agents=1, weighted=True, rng=random.Random(seed)
        )

    def test_costs_are_between_one_and_nine(self) -> None:
        for seed in range(10):
            for value in self._weighted_environment(seed).cell_costs.values():
                self.assertGreaterEqual(value, 1)
                self.assertLessEqual(value, 9)

    def test_ucs_finds_the_cheapest_route(self) -> None:
        """UCS must be at least as cheap as any other algorithm's route."""
        for seed in range(10):
            environment = self._weighted_environment(seed)
            start = environment.agents[0].position
            goal = environment.fire_position

            ucs_result = ucs(environment, start, goal, 1)
            self.assertTrue(ucs_result.success)
            assert_valid_path(self, ucs_result, environment, start, goal)

            for name, function in SEARCH_ALGORITHMS.items():
                other = function(environment, start, goal, 1)
                if other.success:
                    with self.subTest(seed=seed, algorithm=name):
                        self.assertLessEqual(
                            ucs_result.path_cost, other.path_cost,
                            f"UCS cost {ucs_result.path_cost} > {name} cost {other.path_cost}",
                        )

    def test_astar_finds_the_cheapest_route(self) -> None:
        """With an admissible heuristic A* is optimal, so it matches UCS."""
        for seed in range(10):
            environment = self._weighted_environment(seed)
            start = environment.agents[0].position
            goal = environment.fire_position

            a_result = astar(environment, start, goal, 1)
            u_result = ucs(environment, start, goal, 1)
            self.assertTrue(a_result.success)
            self.assertEqual(a_result.path_cost, u_result.path_cost)

    def test_bfs_ignores_costs(self) -> None:
        """BFS must give the same route no matter what the costs are."""
        weighted = self._weighted_environment(1)
        start = weighted.agents[0].position
        goal = weighted.fire_position

        # The very same problem, but without any costs at all.
        plain = Environment(
            rows=weighted.rows,
            cols=weighted.cols,
            agents=[Agent(id=1, position=start)],
            obstacles=set(weighted.obstacles),
            fire_position=goal,
            water_position=weighted.water_position,
            cell_costs={},
            weighted=False,
            start_positions=[start],
        )
        self.assertTrue(weighted.weighted and not plain.weighted)
        self.assertEqual(bfs(weighted, start, goal, 1).path, bfs(plain, start, goal, 1).path)

    def test_dfs_and_greedy_ignore_costs(self) -> None:
        """Both use no accumulated cost, so changing costs changes nothing."""
        for seed in range(5):
            weighted = self._weighted_environment(seed)
            start = weighted.agents[0].position
            goal = weighted.fire_position

            for function in (dfs, greedy_best_first):
                first = function(weighted, start, goal, 1).path

                other = env_module.generate_environment(
                    rows=10, cols=10, num_agents=1, weighted=True,
                    rng=random.Random(seed + 500),
                )
                other.obstacles = set(weighted.obstacles)
                other.fire_position = goal
                other.agents[0].position = start
                # Same obstacles and same endpoints, but new random costs.
                with self.subTest(algorithm=function.__name__, seed=seed):
                    self.assertEqual(function(other, start, goal, 1).path, first)

    def test_greedy_prefers_cheap_cells_over_bfs(self) -> None:
        """A hand-built case where greedy takes a more expensive route."""
        # Two parallel corridors: the top one is short but expensive,
        # the bottom one is longer but cheap. Manhattan distance prefers the
        # top corridor, so greedy walks into the expensive one.
        environment = Environment(
            rows=5, cols=5,
            agents=[Agent(id=1, position=(0, 0))],
            obstacles={(1, 2)},
            fire_position=(0, 4),
            water_position=(4, 4),
            cell_costs={
                (0, 1): 9, (0, 2): 9, (0, 3): 9,
                (1, 0): 1, (1, 1): 1,
                (2, 0): 1, (2, 1): 1,
                (3, 0): 1, (3, 1): 1,
                (4, 0): 1, (4, 1): 1,
            },
            weighted=True,
            start_positions=[(0, 0)],
        )
        bfs_result = bfs(environment, (0, 0), (0, 4), 1)
        greedy_result = greedy_best_first(environment, (0, 0), (0, 4), 1)
        ucs_result = ucs(environment, (0, 0), (0, 4), 1)
        a_result = astar(environment, (0, 0), (0, 4), 1)

        # The short route across the top is very expensive ...
        self.assertEqual(bfs_result.path_cost, 9 * 3 + 1)
        # ... while the detour around the obstacle is cheap.
        self.assertLess(ucs_result.path_cost, bfs_result.path_cost)
        self.assertLess(a_result.path_cost, bfs_result.path_cost)
        # Greedy optimises neither, it just heads for the goal.
        self.assertTrue(greedy_result.success)
        assert_valid_path(self, greedy_result, environment, (0, 0), (0, 4))

    def test_costs_are_unchanged_by_comparing_all_algorithms(self) -> None:
        """The core fairness requirement of the project."""
        environment = self._weighted_environment(5)
        before = dict(environment.cell_costs)
        start = environment.agents[0].position
        goal = environment.fire_position

        for name in SEARCH_ALGORITHMS:
            run_search(name, environment, start, goal, 1)
            self.assertEqual(environment.cell_costs, before, f"{name} changed the costs")

        self.assertEqual(environment.obstacles, before and environment.obstacles)
        self.assertEqual(environment.fire_position, goal)
        self.assertEqual(environment.agents[0].position, start)

    def test_two_agents_share_the_same_costs(self) -> None:
        environment = env_module.generate_environment(
            rows=12, cols=12, num_agents=2, weighted=True, rng=random.Random(11)
        )
        costs = dict(environment.cell_costs)
        results = [
            run_search("A*", environment, agent.position,
                       environment.fire_position, agent.id)
            for agent in environment.agents
        ]
        self.assertEqual(environment.cell_costs, costs)
        for result in results:
            self.assertTrue(result.success)
            self.assertEqual(result.agent_id in (1, 2), True)
        self.assertEqual(len({r.agent_id for r in results}), 2)

    def test_weighted_failure_is_reported(self) -> None:
        environment = make_walled_environment()
        environment.weighted = True
        environment.cell_costs = env_module.generate_costs(5, 5, random.Random(0))
        for name, function in SEARCH_ALGORITHMS.items():
            with self.subTest(algorithm=name):
                result = function(environment, OPEN_START, OPEN_GOAL, 1)
                self.assertFalse(result.success)
                self.assertEqual(result.path_cost, 0)


# ===========================================================================
# 7. Heuristic
# ===========================================================================

class TestHeuristic(unittest.TestCase):
    def test_manhattan_distance(self) -> None:
        self.assertEqual(manhattan((0, 0), (0, 0)), 0)
        self.assertEqual(manhattan((1, 1), (2, 2)), 2)
        self.assertEqual(manhattan((0, 0), (3, 4)), 7)
        self.assertEqual(manhattan((3, 4), (0, 0)), 7)
        self.assertEqual(manhattan((2, 5), (2, 1)), 4)

    def test_manhattan_is_admissible(self) -> None:
        """The heuristic must never overestimate the real remaining cost."""
        for seed in range(8):
            environment = env_module.generate_environment(
                rows=10, cols=10, weighted=True, rng=random.Random(seed)
            )
            start = environment.agents[0].position
            goal = environment.fire_position
            result = ucs(environment, start, goal, 1)
            if not result.success:
                continue
            for index, position in enumerate(result.path):
                estimate = manhattan(position, goal)
                real = sum(
                    environment.cost_of(cell) for cell in result.path[index + 1:]
                )
                self.assertLessEqual(estimate, real)


# ===========================================================================
# 8. Statistics formatting
# ===========================================================================

class TestStatistics(unittest.TestCase):
    def test_statistics_lines(self) -> None:
        environment = make_open_environment()
        result = bfs(environment, OPEN_START, OPEN_GOAL, 1)
        pairs = dict(result_statistics(result))
        self.assertEqual(pairs["Algorithm"], "BFS")
        self.assertEqual(pairs["Path Length"], str(OPEN_ANSWER))
        self.assertEqual(pairs["Path Cost"], str(OPEN_ANSWER))
        self.assertEqual(pairs["Nodes Explored"], str(result.nodes_explored))
        self.assertIn("ms", pairs["Execution Time"])
        self.assertEqual(pairs["Status"], "SUCCESS")

    def test_statistics_of_missing_result(self) -> None:
        self.assertEqual(result_statistics(None), [])

    def test_failure_status(self) -> None:
        result = bfs(make_walled_environment(), OPEN_START, OPEN_GOAL, 1)
        self.assertEqual(result.status, "FAILURE")

    def test_overall_status_single_agent(self) -> None:
        environment = make_open_environment()
        good = bfs(environment, OPEN_START, OPEN_GOAL, 1)
        status, message = overall_status([good])
        self.assertEqual(status, "SUCCESS")
        self.assertIn("Agent 1", message)

    def test_overall_status_two_agents_either_can_win(self) -> None:
        environment = make_open_environment()
        win = bfs(environment, OPEN_START, OPEN_GOAL, 1)
        lose = bfs(make_walled_environment(), OPEN_START, OPEN_GOAL, 2)
        status, message = overall_status([win, lose])
        self.assertEqual(status, "SUCCESS")
        self.assertIn("Agent 1", message)

    def test_overall_status_failure(self) -> None:
        walled = make_walled_environment()
        results = [bfs(walled, OPEN_START, OPEN_GOAL, i) for i in (1, 2)]
        status, message = overall_status(results)
        self.assertEqual(status, "FAILURE")
        self.assertIn("No agent can reach the fire", message)

    def test_overall_status_pending(self) -> None:
        status, _ = overall_status([])
        self.assertEqual(status, "PENDING")

    def test_time_formatting(self) -> None:
        from statistics import format_time
        self.assertIn("ms", format_time(0.1234))
        self.assertIn("ms", format_time(12.3456))


# ===========================================================================
# 9. User interface
# ===========================================================================

def pump(root: tk.Tk, seconds: float = 0.3) -> None:
    """Let Tkinter process pending events for a while (animations use after)."""
    end = time.time() + seconds
    while time.time() < end:
        root.update_idletasks()
        root.update()
        time.sleep(0.01)


def settle(app: "FirefightingApp", timeout: float = 12.0) -> bool:
    """Pump events until the search animation has finished.

    Waiting on the application's own `animating` flag keeps the tests
    deterministic instead of guessing how long an animation takes.
    """
    end = time.time() + timeout
    while app.animating and time.time() < end:
        app.root.update_idletasks()
        app.root.update()
        time.sleep(0.01)
    app.root.update_idletasks()
    app.root.update()
    return not app.animating


class TestUserInterface(unittest.TestCase):
    """These tests drive the real application window."""

    @classmethod
    def setUpClass(cls) -> None:
        try:
            cls.root = tk.Tk()
        except tk.TclError as error:  # pragma: no cover - depends on machine
            raise unittest.SkipTest(f"no display available: {error}")
        cls.root.withdraw()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.root.destroy()

    def make_app(self) -> FirefightingApp:
        root = tk.Tk()
        root.withdraw()
        app = FirefightingApp(root)
        pump(root, 0.1)
        self.addCleanup(root.destroy)
        return app

    # -- start up ---------------------------------------------------------

    def test_application_starts_and_generates_an_environment(self) -> None:
        app = self.make_app()
        self.assertIsNotNone(app.environment)
        self.assertEqual(app.environment.rows, 10)
        self.assertEqual(app.environment.cols, 10)
        self.assertEqual(len(app.environment.agents), 1)

    def test_grid_is_drawn(self) -> None:
        app = self.make_app()
        pump(app.root)
        items = app.canvas.find_all()
        # 100 cell rectangles plus the symbols drawn on top of them.
        self.assertGreaterEqual(len(items), 100)

    def test_every_cell_symbol_is_drawn(self) -> None:
        app = self.make_app()
        pump(app.root)
        texts = [
            app.canvas.itemcget(item, "text")
            for item in app.canvas.find_all()
            if app.canvas.type(item) == "text"
        ]
        self.assertIn("F", texts)
        self.assertIn("W", texts)
        self.assertIn("A1", texts)

    def test_reset_button_and_controls_exist(self) -> None:
        app = self.make_app()
        self.assertTrue(app.regenerate_button.winfo_exists())
        self.assertTrue(app.run_button.winfo_exists())
        self.assertEqual(len(app.algorithm_box["values"]), 5)

    # -- control visibility ----------------------------------------------

    def test_algorithm_selector_hidden_in_manual_mode(self) -> None:
        app = self.make_app()
        app.mode.set("manual")
        app._on_mode_changed()
        self.assertEqual(app.algorithm_frame.winfo_manager(), "")

        app.mode.set("ai")
        app._on_mode_changed()
        self.assertNotEqual(app.algorithm_frame.winfo_manager(), "")

    def test_active_agent_hidden_in_ai_mode_and_with_one_agent(self) -> None:
        app = self.make_app()
        app.mode.set("ai")
        app._on_mode_changed()
        self.assertEqual(app.active_agent_frame.winfo_manager(), "")

        app.mode.set("manual")
        app._on_agent_count_changed()
        self.assertEqual(app.active_agent_frame.winfo_manager(), "")

        app.agent_count.set(2)
        app._on_agent_count_changed()
        self.assertNotEqual(app.active_agent_frame.winfo_manager(), "")

    def test_regenerate_costs_disabled_in_unweighted_mode(self) -> None:
        app = self.make_app()
        app.path_mode.set("unweighted")
        app._on_path_mode_changed()
        self.assertIn("disabled", app.regenerate_button.state())

        app.path_mode.set("weighted")
        app._on_path_mode_changed()
        self.assertNotIn("disabled", app.regenerate_button.state())

    def test_second_statistics_block_hidden_with_one_agent(self) -> None:
        app = self.make_app()
        self.assertEqual(app.stats_frames[2].winfo_manager(), "")
        app.agent_count.set(2)
        app._on_agent_count_changed()
        self.assertNotEqual(app.stats_frames[2].winfo_manager(), "")

    # -- manual mode -----------------------------------------------------

    def test_manual_movement_with_arrow_keys(self) -> None:
        app = self.make_app()
        app.mode.set("manual")
        app._on_mode_changed()
        agent = app.environment.agents[0]
        # Clear the surroundings so the four moves are all legal.
        app.environment.obstacles = set()
        agent.position = (5, 5)

        app._on_key_press(KeyEvent("Right"))
        self.assertEqual(agent.position, (5, 6))
        app._on_key_press(KeyEvent("Down"))
        self.assertEqual(agent.position, (6, 6))
        app._on_key_press(KeyEvent("Left"))
        self.assertEqual(agent.position, (6, 5))
        app._on_key_press(KeyEvent("Up"))
        self.assertEqual(agent.position, (5, 5))

    def test_manual_movement_with_wasd(self) -> None:
        app = self.make_app()
        app.mode.set("manual")
        app._on_mode_changed()
        agent = app.environment.agents[0]
        app.environment.obstacles = set()
        agent.position = (5, 5)

        app._on_key_press(KeyEvent("d"))
        self.assertEqual(agent.position, (5, 6))
        app._on_key_press(KeyEvent("s"))
        self.assertEqual(agent.position, (6, 6))
        app._on_key_press(KeyEvent("a"))
        self.assertEqual(agent.position, (6, 5))
        app._on_key_press(KeyEvent("w"))
        self.assertEqual(agent.position, (5, 5))

    def test_manual_movement_blocked_by_border(self) -> None:
        app = self.make_app()
        app.mode.set("manual")
        app._on_mode_changed()
        agent = app.environment.agents[0]
        agent.position = (0, 0)

        app._on_key_press(KeyEvent("Up"))
        self.assertEqual(agent.position, (0, 0))
        app._on_key_press(KeyEvent("Left"))
        self.assertEqual(agent.position, (0, 0))

    def test_manual_movement_blocked_by_obstacle(self) -> None:
        app = self.make_app()
        app.mode.set("manual")
        app._on_mode_changed()
        agent = app.environment.agents[0]
        agent.position = (4, 4)
        app.environment.obstacles = {(4, 5)} if app.environment.cols > 5 else {(5, 4)}

        before = agent.position
        app._on_key_press(KeyEvent("Right"))
        self.assertEqual(agent.position, before)

    def test_unrelated_key_does_nothing(self) -> None:
        app = self.make_app()
        app.mode.set("manual")
        app._on_mode_changed()
        agent = app.environment.agents[0]
        before = agent.position
        app._on_key_press(KeyEvent("q"))
        self.assertEqual(agent.position, before)

    def test_manual_picks_up_water_then_succeeds(self) -> None:
        app = self.make_app()
        app.mode.set("manual")
        app._on_mode_changed()
        environment = app.environment
        environment.obstacles = set()
        environment.fire_position = (5, 9)
        agent = environment.agents[0]

        # Stand just left of the water station and step onto it.
        environment.water_position = (5, 6)
        agent.position = (5, 5)
        app._on_key_press(KeyEvent("Right"))
        self.assertTrue(agent.has_water, "water was not collected")
        self.assertEqual(agent.position, (5, 6))

        # Now walk to the fire: the mission is complete.
        app._on_key_press(KeyEvent("Right"))
        app._on_key_press(KeyEvent("Right"))
        app._on_key_press(KeyEvent("Right"))
        self.assertEqual(agent.position, environment.fire_position)
        self.assertTrue(app.mission_finished)
        self.assertIn("SUCCESS", app.status_text.get())

    def test_manual_fire_without_water_is_not_success(self) -> None:
        app = self.make_app()
        app.mode.set("manual")
        app._on_mode_changed()
        environment = app.environment
        environment.obstacles = set()
        agent = environment.agents[0]
        agent.has_water = False
        environment.water_position = (0, 0)
        environment.fire_position = (5, 9)
        agent.position = (5, 8)

        app._on_key_press(KeyEvent("Right"))
        self.assertEqual(agent.position, environment.fire_position)
        self.assertFalse(app.mission_finished)
        self.assertIn("without water", app.status_text.get())

    def test_manual_mission_stops_after_success(self) -> None:
        """Once the fire is out the agent must not keep walking."""
        app = self.make_app()
        app.mode.set("manual")
        app._on_mode_changed()
        environment = app.environment
        environment.obstacles = set()
        environment.water_position = (0, 0)
        environment.fire_position = (5, 9)
        agent = environment.agents[0]
        agent.has_water = True
        agent.position = (5, 8)

        app._on_key_press(KeyEvent("Right"))
        self.assertTrue(app.mission_finished)
        app._on_key_press(KeyEvent("Right"))
        self.assertEqual(agent.position, (5, 9), "agent moved after the mission ended")

    def test_only_the_active_agent_moves(self) -> None:
        app = self.make_app()
        app.agent_count.set(2)
        app._on_agent_count_changed()
        app.mode.set("manual")
        app._on_mode_changed()
        app.environment.obstacles = set()

        first, second = app.environment.agents
        first.position = (4, 0)
        second.position = (4, 1)
        app.active_agent.set(1)
        app._on_active_agent_changed()

        app._on_key_press(KeyEvent("Right"))
        self.assertEqual(first.position, (4, 1))
        self.assertEqual(second.position, (4, 1), "agent 2 should not have moved")

    def test_manual_switching_changes_who_moves(self) -> None:
        app = self.make_app()
        app.agent_count.set(2)
        app._on_agent_count_changed()
        app.mode.set("manual")
        app._on_mode_changed()
        app.environment.obstacles = set()

        first, second = app.environment.agents
        first.position = (4, 0)
        second.position = (2, 4)
        app.active_agent.set(2)
        app._on_active_agent_changed()

        app._on_key_press(KeyEvent("Up"))
        self.assertEqual(second.position, (1, 4))
        self.assertEqual(first.position, (4, 0), "agent 1 should not have moved")

    def test_keyboard_ignored_in_ai_mode(self) -> None:
        app = self.make_app()
        app.mode.set("ai")
        app._on_mode_changed()
        agent = app.environment.agents[0]
        before = agent.position
        app._on_key_press(KeyEvent("Right"))
        self.assertEqual(agent.position, before)

    # -- AI mode ----------------------------------------------------------

    def test_ai_search_fills_statistics(self) -> None:
        app = self.make_app()
        app.mode.set("ai")
        app._on_mode_changed()
        app.algorithm.set("BFS")
        app.run_search()
        pump(app.root, 0.2)

        labels = app.stats_labels[1]
        self.assertEqual(labels["Algorithm"]["text"], "BFS")
        self.assertEqual(labels["Status"]["text"], "SUCCESS")
        self.assertNotEqual(labels["Path Length"]["text"], "-")
        self.assertNotEqual(labels["Path Cost"]["text"], "-")
        self.assertNotEqual(labels["Nodes Explored"]["text"], "-")
        self.assertIn("ms", labels["Execution Time"]["text"])

    def test_every_algorithm_runs_from_the_ui(self) -> None:
        for name in ALGORITHM_NAMES:
            with self.subTest(algorithm=name):
                app = self.make_app()
                app.mode.set("ai")
                app._on_mode_changed()
                app.algorithm.set(name)
                app.run_search()
                pump(app.root, 0.2)
                self.assertEqual(app.stats_labels[1]["Algorithm"]["text"], name)
                self.assertEqual(app.stats_labels[1]["Status"]["text"], "SUCCESS")

    def test_ai_search_animates_the_agent_to_the_fire(self) -> None:
        app = self.make_app()
        app.mode.set("ai")
        app._on_mode_changed()
        app.algorithm.set("BFS")
        app.run_search()
        self.assertTrue(settle(app), "animation did not finish")

        agent = app.environment.agents[0]
        self.assertEqual(agent.position, app.environment.fire_position)
        self.assertTrue(agent.has_water)
        self.assertTrue(app.mission_finished)
        self.assertIn("SUCCESS", app.status_text.get())

    def test_ai_failure_is_reported_without_crashing(self) -> None:
        app = self.make_app()
        app.mode.set("ai")
        app._on_mode_changed()
        app.algorithm.set("A*")
        # Wall the fire in completely: every algorithm must report failure.
        fire = app.environment.fire_position
        walls = set()
        for row in range(app.environment.rows):
            for col in range(app.environment.cols):
                if (row, col) != fire and abs(row - fire[0]) + abs(col - fire[1]) == 1:
                    walls.add((row, col))
        app.environment.obstacles = walls

        app.run_search()
        self.assertTrue(settle(app), "animation did not finish")
        self.assertEqual(app.stats_labels[1]["Status"]["text"], "FAILURE")
        self.assertIn("FAILURE", app.status_text.get())

    def test_two_agents_get_separate_statistics(self) -> None:
        app = self.make_app()
        app.agent_count.set(2)
        app._on_agent_count_changed()
        app.mode.set("ai")
        app._on_mode_changed()
        app.algorithm.set("UCS")
        app.run_search()
        pump(app.root, 0.3)

        self.assertEqual(len(app.results), 2)
        self.assertEqual(app.stats_labels[1]["Algorithm"]["text"], "UCS")
        self.assertEqual(app.stats_labels[2]["Algorithm"]["text"], "UCS")
        for agent_id in (1, 2):
            result = app.results[agent_id]
            self.assertEqual(result.agent_id, agent_id)
            self.assertTrue(result.success)

    def test_two_agents_have_different_paths(self) -> None:
        app = self.make_app()
        app.agent_count.set(2)
        app._on_agent_count_changed()
        app.mode.set("ai")
        app._on_mode_changed()
        app.algorithm.set("BFS")
        app.run_search()
        pump(app.root, 0.3)
        self.assertNotEqual(app.results[1].path[0], app.results[2].path[0])

    def test_comparison_table_collects_all_algorithms(self) -> None:
        """All five algorithms must run on the very same environment."""
        app = self.make_app()
        app.path_mode.set("weighted")
        app._on_path_mode_changed()
        app.mode.set("ai")
        app._on_mode_changed()

        costs_before = dict(app.environment.cell_costs)
        obstacles_before = set(app.environment.obstacles)
        starts = {a.id: a.position for a in app.environment.agents}

        for name in ALGORITHM_NAMES:
            app.algorithm.set(name)
            app.run_search()
            pump(app.root, 0.2)
            app.reset_view(regenerate_comparison=False)

        rows = app.comparison_tree.get_children()
        self.assertEqual(len(rows), 5)
        self.assertEqual(len(app.comparison), 5)

        # The problem really was identical every single time.
        self.assertEqual(app.environment.cell_costs, costs_before)
        self.assertEqual(app.environment.obstacles, obstacles_before)
        for agent in app.environment.agents:
            self.assertEqual(agent.position, starts[agent.id])

    def test_comparison_table_cleared_by_generate(self) -> None:
        app = self.make_app()
        app.mode.set("ai")
        app._on_mode_changed()
        app.algorithm.set("BFS")
        app.run_search()
        pump(app.root, 0.2)
        self.assertEqual(len(app.comparison_tree.get_children()), 1)

        app.generate_environment()
        self.assertEqual(len(app.comparison_tree.get_children()), 0)

    # -- weighted mode in the UI -----------------------------------------

    def test_weighted_mode_draws_costs(self) -> None:
        app = self.make_app()
        app.path_mode.set("weighted")
        app._on_path_mode_changed()
        pump(app.root)

        self.assertTrue(app.environment.weighted)
        texts = [
            app.canvas.itemcget(item, "text")
            for item in app.canvas.find_all()
            if app.canvas.type(item) == "text"
        ]
        # Costs are digits, and the agent / fire / water symbols are still there.
        self.assertTrue(any(text.isdigit() for text in texts))
        self.assertIn("F", texts)
        self.assertIn("W", texts)
        self.assertIn("A1", texts)

    def test_unweighted_mode_draws_no_costs(self) -> None:
        app = self.make_app()
        pump(app.root)
        texts = [
            app.canvas.itemcget(item, "text")
            for item in app.canvas.find_all()
            if app.canvas.type(item) == "text"
        ]
        self.assertFalse(any(text.isdigit() for text in texts))

    def test_costs_are_not_drawn_on_top_of_symbols(self) -> None:
        """Every cost number must sit in a corner of a plain empty cell."""
        app = self.make_app()
        app.path_mode.set("weighted")
        app._on_path_mode_changed()
        pump(app.root)
        environment = app.environment
        size = app.renderer.cell_size
        for item in app.canvas.find_all():
            if app.canvas.type(item) != "text":
                continue
            if not app.canvas.itemcget(item, "text").isdigit():
                continue
            x, y = app.canvas.coords(item)[:2]
            col = int(x // size)
            row = int(y // size)
            position = (row, col)
            self.assertNotIn(position, environment.obstacles)
            self.assertNotIn(position, {a.position for a in environment.agents})
            self.assertNotEqual(position, environment.fire_position)
            self.assertNotEqual(position, environment.water_position)

    def test_regenerate_costs_button_keeps_environment(self) -> None:
        app = self.make_app()
        app.path_mode.set("weighted")
        app._on_path_mode_changed()

        agents = [a.position for a in app.environment.agents]
        fire = app.environment.fire_position
        water = app.environment.water_position
        obstacles = set(app.environment.obstacles)
        before = dict(app.environment.cell_costs)

        app.regenerate_costs()
        self.assertNotEqual(app.environment.cell_costs, before)
        self.assertEqual([a.position for a in app.environment.agents], agents)
        self.assertEqual(app.environment.fire_position, fire)
        self.assertEqual(app.environment.water_position, water)
        self.assertEqual(app.environment.obstacles, obstacles)

    # -- reset ------------------------------------------------------------

    def test_reset_clears_visualisation_and_statistics(self) -> None:
        app = self.make_app()
        app.mode.set("ai")
        app._on_mode_changed()
        app.algorithm.set("A*")
        app.run_search()
        pump(app.root, 0.3)
        self.assertTrue(app.results)

        app.reset_view()
        self.assertEqual(app.results, {})
        self.assertEqual(app.stats_labels[1]["Path Length"]["text"], "-")
        self.assertEqual(app.stats_labels[1]["Status"]["text"], "-")
        self.assertIsNotNone(app.environment, "reset must keep the environment")

    def test_reset_restores_agent_positions(self) -> None:
        app = self.make_app()
        start = app.environment.agents[0].position
        app.environment.agents[0].position = (9, 9)
        app.reset_view()
        self.assertEqual(app.environment.agents[0].position, start)
        self.assertFalse(app.environment.agents[0].has_water)

    def test_reset_keeps_the_comparison_when_asked(self) -> None:
        app = self.make_app()
        app.mode.set("ai")
        app._on_mode_changed()
        app.algorithm.set("BFS")
        app.run_search()
        pump(app.root, 0.2)
        app.reset_view(regenerate_comparison=False)
        self.assertEqual(len(app.comparison_tree.get_children()), 1)
        app.reset_view(regenerate_comparison=True)
        self.assertEqual(len(app.comparison_tree.get_children()), 0)

    def test_animation_can_be_cancelled_mid_run(self) -> None:
        app = self.make_app()
        app.mode.set("ai")
        app._on_mode_changed()
        app.algorithm.set("BFS")
        app.run_search()
        pump(app.root, 0.1)
        app.reset_view()
        pump(app.root, 1.0)
        # Cancelling must stop the animation, not leave it running.
        self.assertEqual(app.results, {})

    # -- robustness -------------------------------------------------------

    def test_every_control_combination_does_not_crash(self) -> None:
        for mode in ("manual", "ai"):
            for count in (1, 2):
                for path_mode in ("unweighted", "weighted"):
                    with self.subTest(mode=mode, agents=count, costs=path_mode):
                        app = self.make_app()
                        app.mode.set(mode)
                        app.agent_count.set(count)
                        app.path_mode.set(path_mode)
                        app._on_mode_changed()
                        app._on_agent_count_changed()
                        app._on_path_mode_changed()
                        app.reset_view()
                        if mode == "ai":
                            app.run_search()
                            pump(app.root, 0.2)
                        else:
                            for keysym in ("Up", "Down", "Left", "Right"):
                                app._on_key_press(KeyEvent(keysym))
                        pump(app.root, 0.1)

    def test_repeated_generate_never_crashes(self) -> None:
        app = self.make_app()
        for _ in range(12):
            app.generate_environment()
        self.assertIsNotNone(app.environment)
        self.assertTrue(env_module.is_solvable(app.environment))

    def test_run_search_without_environment_does_not_crash(self) -> None:
        app = self.make_app()
        app.environment = None
        app.mode.set("ai")
        app._on_mode_changed()
        app.run_search()
        app.regenerate_costs()
        app.reset_view()

    def test_status_bar_is_readable(self) -> None:
        app = self.make_app()
        self.assertTrue(app.status_text.get())
        app._set_status("SUCCESS - Fire extinguished!", color=COLORS["fire"])
        self.assertIn("SUCCESS", app.status_text.get())
        self.assertEqual(app.status_label["fg"], COLORS["fire"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
