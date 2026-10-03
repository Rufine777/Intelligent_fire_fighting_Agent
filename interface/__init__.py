"""
The interface layer: everything that touches the screen.

    ui.py            the single window - controls, buttons, animation, table
    visualization.py draws the grid, paths and agents on the canvas
    statistics.py    turns numbers into the text the user reads

This package depends on `core`. The reverse never happens: the search has no
idea a GUI exists.
"""