"""
The core layer: the problem and the search, with no user interface.

    models.py        the vocabulary - Agent, Environment, constants
    environment.py   builds the world and defines its rules
    algorithms.py    bfs, dfs, ucs, greedy_best_first, astar

Nothing in this package imports tkinter. That is deliberate: it lets the search
be read, tested and scripted without ever opening a window.
"""