"""
Statistics formatting for the Intelligent Firefighting Agent.

The search algorithms only return numbers. This module turns those numbers
into the exact text shown in the user interface, so the same wording is used
for every algorithm and for both agents.

Keeping this separate means the UI never has to know how a statistic is
calculated - it only asks for the text.
"""

from __future__ import annotations

from algorithms import SearchResult

# The six course metrics, in the order they are displayed.
STAT_LABELS = [
    "Algorithm",
    "Path Length",
    "Path Cost",
    "Nodes Explored",
    "Execution Time",
    "Status",
]

# Columns of the algorithm comparison table.
COMPARISON_COLUMNS = ["Algorithm", "Length", "Cost", "Nodes", "Time (ms)", "Result"]


def format_time(milliseconds: float) -> str:
    """Execution time in a short, readable form."""
    if milliseconds < 1.0:
        return f"{milliseconds:.3f} ms"
    return f"{milliseconds:.2f} ms"


def result_statistics(result: SearchResult | None) -> list[tuple[str, str]]:
    """The (label, value) pairs shown for one agent.

    Returns an empty list when no search has been run yet.
    """
    if result is None:
        return []

    values = {
        "Algorithm": result.algorithm,
        "Path Length": result.path_length,
        "Path Cost": result.path_cost,
        "Nodes Explored": result.nodes_explored,
        "Execution Time": format_time(result.execution_time_ms),
        "Status": result.status,
    }
    return [(label, str(values[label])) for label in STAT_LABELS]


def comparison_row(result: SearchResult) -> tuple[str, ...]:
    """One row of the algorithm comparison table."""
    return (
        result.algorithm,
        str(result.path_length),
        str(result.path_cost),
        str(result.nodes_explored),
        f"{result.execution_time_ms:.3f}",
        "Success" if result.success else "Failure",
    )


def overall_status(results: list[SearchResult]) -> tuple[str, str]:
    """Decide the overall SUCCESS / FAILURE for the whole mission.

    For one agent: that agent must reach the fire.
    For two agents: it is enough that EITHER agent reaches the fire, so the
    second agent does not have to make it.
    """
    if not results:
        return "PENDING", "Run a search to see the result."

    successful = [r for r in results if r.success]

    if successful:
        names = ", ".join(f"Agent {r.agent_id}" for r in successful)
        return "SUCCESS", f"Fire extinguished! Reached by {names}."

    return (
        "FAILURE",
        "No agent can reach the fire.",
    )
