"""
Intelligent Firefighting Agent - entry point.

Run the application with:

    python main.py

It is a local desktop application built with Tkinter. No server, no
internet connection and no third-party package is required.
"""

from __future__ import annotations

import sys
import tkinter as tk

from ui import FirefightingApp


def main() -> int:
    """Create the window and run the Tkinter event loop."""
    try:
        root = tk.Tk()
    except tk.TclError as error:
        # A clear message is friendlier than a traceback when there is no
        # display available (for example on a headless machine).
        print("Could not open a window. Is a display available?", file=sys.stderr)
        print(f"Tkinter reported: {error}", file=sys.stderr)
        return 1

    FirefightingApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
