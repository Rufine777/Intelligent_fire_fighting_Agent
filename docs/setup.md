# Setup Guide

How to install and run the Intelligent Firefighting Agent on **Windows, macOS
and Linux**.

---

## What you need

| Requirement | Version | Notes |
| --- | --- | --- |
| Python | **3.9 or newer** | 3.12 or 3.13 recommended. |
| Tkinter | any | Ships **with** Python on Windows and macOS. On Linux it is a separate system package (see below). |
| Pip | any | Comes with Python. Used only to create the virtual environment. |

**There are zero third-party packages.** Every import in this project comes from
the Python standard library:

| Module | Used for |
| --- | --- |
| `tkinter` | the GUI |
| `collections` | `deque` — the BFS queue |
| `heapq` | priority queues for UCS, Greedy and A\* |
| `dataclasses` | `Agent`, `Environment`, `SearchResult` |
| `random` | generating maps, obstacles and cell costs |
| `time` | execution timing |
| `pathlib`, `json`, `argparse` | helper scripts |

So `requirements.txt` is intentionally empty. There is nothing to download, and
the app never uses the internet.

> The one dependency that is **not** a pip package is **Tkinter**.
> `pip install tkinter` does not work. Install it with your system package
> manager (Linux) or accept it during the Python installer (Windows/macOS).

---

## 1. Get the code

```bash
git clone <your-repository-url> intelligent-firefighting-agent
cd intelligent-firefighting-agent
```

If you were given a ZIP instead, unzip it and `cd` into the folder that contains
`main.py`.

Confirm you are in the right place:

```bash
ls                    # macOS / Linux
dir                   # Windows CMD
```

You should see:

```
main.py
core/         interface/
docs/
README.md  requirements.txt
```

---

## 2. Check your Python

```bash
python --version          # macOS / Linux
py --version              # Windows (the py launcher)
```

If you get "command not found", Python is not installed — go to
[python.org/downloads](https://www.python.org/downloads/) and install it.

**On Windows**, tick **`Add python.exe to PATH`** in the installer. Without it,
`python` will not be found from a terminal.

---

## 3. Install Tkinter (Linux only)

Skip this section on Windows and macOS — Tkinter is already included.

### Check whether you already have it

```bash
python -c "import tkinter; print('Tk', tkinter.TkVersion)"
```

If it prints something like `Tk 8.6`, you are done. If it raises
`ModuleNotFoundError: No module named 'tkinter'`, install it:

### Debian / Ubuntu / Mint / Kali

```bash
sudo apt update
sudo apt install python3-tk
```

### Fedora / RHEL / CentOS

```bash
sudo dnf install python3-tkinter
```

### Arch / Manjaro / EndeavourOS

```bash
sudo pacman -S tk
```

### openSUSE / SLES

```bash
sudo zypper install python3-tk
```

### Verify

```bash
python -c "import tkinter; print('Tk', tkinter.TkVersion)"
```

> **Important on Debian/Ubuntu:** the package is called `python3-tk`, and it must
> match your Python version (`python3.11-tk` on a system with Python 3.11).
> `sudo apt install python-tk` refers to Python 2 and is the wrong package.

---

## 4. Create a virtual environment

A virtual environment keeps this project's Python packages separate from the
rest of your system. Do it once, then activate it every time you work on the
project.

### Linux / macOS

```bash
python3 -m venv .venv
```

### Windows (PowerShell or CMD)

```bat
py -m venv .venv
```

The folder `.venv` is created inside the project. It is already in
`.gitignore`, so it will never be committed by accident.

---

## 5. Activate the virtual environment

You must activate the environment **every time you open a new terminal**.

### Linux

```bash
source .venv/bin/activate
```

### macOS (zsh — the default since Catalina)

```bash
source .venv/bin/activate
```

If you use Homebrew-installed Python 3.12+ and get
`error: externally-managed-environment`, use a different interpreter:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

### Windows (PowerShell)

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell refuses with *"running scripts is disabled on this system"*, allow
it for your user once:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

### Windows (Command Prompt)

```bat
.venv\Scripts\activate.bat
```

### Confirm it worked

Your prompt should now start with `(.venv)`, and this should print the venv's
path rather than the system one:

```bash
python -c "import sys; print(sys.prefix)"
```

```
/home/you/intelligent-firefighting-agent/.venv      # Linux / macOS
C:\...\intelligent-firefighting-agent\.venv         # Windows
```

---

## 6. Install the packages

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Both commands are safe and fast. Because `requirements.txt` lists no
distributable packages, the second is effectively a **no-op** — there is nothing
to download. It is kept in the project so the setup works unchanged if a
dependency is ever added.

You can confirm there is genuinely nothing installed beyond the standard
library:

```bash
python -m pip list
```

---

## 7. Run the application

```bash
python main.py
```

A window titled **Intelligent Firefighting Agent** should open.

If it does not, see [Troubleshooting](#troubleshooting) below.

---

## 8. Verify the install

Run this from the project folder with the venv active. It checks the
environment, Tkinter, and the search algorithms, then prints the version of
every file:

```bash
python - <<'PY'
import random
import sys
import tkinter

from core import algorithms
from core import environment
from core import models
from interface import statistics
from interface import ui
from interface import visualization

print("Python  ", sys.version.split()[0])
print("Tk       ", tkinter.TkVersion)
print("modules  ", "all imported OK")

# 20 random grids, every algorithm, single and dual agent.
for seed in range(20):
    env = environment.generate_environment(12, 12, 2,
                                          weighted=seed % 2 == 0,
                                          rng=random.Random(seed))
    for name in algorithms.ALGORITHM_NAMES:
        for agent in env.agents:
            r = algorithms.run_search(name, env, agent.position,
                                      env.fire_position, agent.id)
            assert r.path[0] == agent.position
            assert r.path[-1] == env.fire_position
            assert all(env.is_walkable(cell) for cell in r.path)

print("searches  20 grids x 5 algorithms x 2 agents: all paths valid")
print("\nSetup is complete. Run:  python main.py")
PY
```

Expected output:

```
Python   3.13.2
Tk        8.6
modules   all imported OK
searches  20 grids x 5 algorithms x 2 agents: all paths valid

Setup is complete. Run:  python main.py
```

### On Windows (PowerShell or CMD)

PowerShell has no heredoc. Save the snippet above as `check_install.py`, then:

```powershell
python check_install.py
```

```bat
python check_install.py
```

---

## 9. Daily use

Every new terminal, two commands are enough:

```bash
cd intelligent-firefighting-agent
source .venv/bin/activate     # Windows: .venv\Scripts\activate
python main.py
```

### Deactivate when you are done

```bash
deactivate
```

This leaves the virtual environment but does not delete it.

### Delete the virtual environment

To start completely fresh:

```bash
rm -rf .venv                  # Linux / macOS
```

```powershell
Remove-Item -Recurse -Force .venv     # Windows PowerShell
```

```bat
rmdir /s /q .venv            # Windows CMD
```

Then repeat steps 4–6.

---

## How the pieces fit together

The project is split into two layers, and imports only ever point one way:

```
                       main.py                 opens the window, starts the app
                          |
     interface/  ─────────┼─────────────────
        ui.py            |                   controls, buttons, animation, table
        visualization.py  |                   draws the grid on the canvas
        statistics.py     |                   numbers turned into text
     ─────────────────────┼─────────────────
          core/  ─────────┴─────────────────
        models.py                            Agent, Environment, constants
        environment.py                       builds the world, its rules
        algorithms.py                        bfs, dfs, ucs, greedy, astar
```

`core/algorithms.py` never imports `tkinter` and never imports `interface`, so
the search can be tested and scripted without opening a window:

```bash
python -c "from core.algorithms import run_search; print('no GUI needed')"
```

**Always run commands from the project root** — the folder containing
`main.py`. Python puts that folder on `sys.path`, which is what makes `core` and
`interface` importable.

---

## Troubleshooting

### `ModuleNotFoundError: No module named 'tkinter'`

Tkinter is missing. Install the system package for your distribution
([step 3](#3-install-tkinter-linux-only)).

### `TclError: no display name and no $DISPLAY environment variable`

No graphical display is available. This app is a desktop GUI and needs one — it
cannot run in a plain terminal session on a server.

- **Linux, no physical screen:** use X11 forwarding over SSH
  (`ssh -X user@host`), or run a virtual display with `xvfb-run -a python main.py`.
- **Windows or macOS:** run it from a normal desktop terminal, not an
  unattended service.
- **WSL:** Tkinter cannot open a Windows window from WSL. Run the project in
  Windows Python instead, or use WSLg (Windows 11) with a Linux GUI app.

### `error: externally-managed-environment` (macOS / Debian)

Your OS refuses to install into the system Python. This is expected — it is why
we use a virtual environment. Either activate `.venv` first, or create it with
an explicit interpreter:

```bash
python3.12 -m venv .venv
```

### `The term 'python' is not recognized` (Windows)

Python is not on your PATH. Reinstall and tick **Add python.exe to PATH**, then
open a **new** terminal. Use `py` instead of `python` as a workaround.

### `cannot load the required image file` or a font warning on Linux

Tk is installed but its default fonts are not. Install a font package:

```bash
sudo apt install fonts-dejavu        # Debian / Ubuntu
sudo dnf install dejavu-fonts        # Fedora
```

### The window opens but looks wrong

Tk falls back to a default font if the one the UI asks for is missing. Install
the DejaVu fonts (above) and restart the app.

### `from ui import FirefightingApp` fails when running `python main.py`

You started Python from the wrong directory. `main.py` imports sibling modules
from the project folder, so `cd` into the folder containing it and run
`python main.py` there.

### Still stuck

1. `python --version` — is Python 3.9+?
2. `python -c "import tkinter; print(tkinter.TkVersion)"` — is Tk present?
3. `python -c "import sys; print(sys.prefix)"` — are you inside `.venv`?
4. `cd` — are you in the folder containing `main.py`?