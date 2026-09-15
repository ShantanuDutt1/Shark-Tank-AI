"""
Standalone Windows launcher for Shark Tank AI (Release 1.0).

This is a thin packaging layer only -- it contains no agent,
orchestration, or UI logic of its own. Its only job is to make the
existing `app.py` Streamlit application runnable as a double-clickable
Windows executable: pick a working directory so relative paths
(`.env`, `logs/app.log`) resolve predictably regardless of where the
user launched it from, find a free local port, launch Streamlit's own
CLI entry point programmatically, and open the user's browser to it.

Never embeds or generates an API key. The user's own `ANTHROPIC_API_KEY`
is read the exact same way it always has been -- from a `.env` file
(via `config.settings.Settings`, `pydantic-settings`) or the real OS
environment -- this launcher only decides *where* `.env` is looked
for (next to the executable, not wherever Explorer's CWD happens to
be), never how it's parsed or used.
"""

from __future__ import annotations

import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path


def _user_facing_dir() -> Path:
    """Directory a user would naturally look in for `.env` / `logs/` --
    the folder containing `SharkTankAI.exe` itself when frozen (not
    PyInstaller's internal `_internal/` data directory, which most
    users never open), or this file's own project root otherwise (so
    `python packaging/windows_launcher.py` also works unpackaged, for
    testing the launcher itself without a full PyInstaller build)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def _find_app_script() -> Path:
    """Locate the real `app.py` source file Streamlit's CLI needs to
    read from disk (it execs the actual file, not an importable
    module -- pointing it at a frozen/bundled module path does not
    work). `packaging/build_windows.py` bundles a real copy of `app.py`
    as a data file (`--add-data`), which PyInstaller's onedir layout
    places under `_internal/` next to the executable -- checked first;
    falls back to checking right next to the executable in case a
    future PyInstaller version changes that layout, and finally to the
    real project root when running unfrozen."""
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        for candidate in (exe_dir / "_internal" / "app.py", exe_dir / "app.py"):
            if candidate.exists():
                return candidate
        raise FileNotFoundError(
            f"Could not find app.py bundled next to {sys.executable} "
            "(checked _internal/app.py and app.py). The package may be "
            "corrupt or incorrectly built -- see packaging/README.md."
        )
    return Path(__file__).resolve().parent.parent / "app.py"


# Make the project root importable, then force PyInstaller's static
# import-graph analysis to discover and bundle every first-party
# module `app.py` transitively imports at runtime.
# `windows_launcher.py` never calls `app.py`'s code directly -- it
# only hands Streamlit's CLI a *path string* to exec (see
# `_find_app_script()` and `main()` below) -- so without a real import
# somewhere in this file, PyInstaller has no static reference to
# `agents/`, `orchestrator/`, `models/`, `providers/`, `config/`,
# `utils/`, `memory/` and would silently omit all of them, only
# failing at runtime once Streamlit actually execs app.py. Deliberately
# the exact same import `app.py` itself uses (`from ui.layout import
# render_app`) rather than a broader guess -- `ui/layout.py` already
# imports every other first-party package transitively
# (`ui.controls` -> `orchestrator.orchestrator` -> every agent/model/
# provider), so this one import's real transitive closure matches
# production exactly. Guarded by `sys.path` setup so this also works
# when run unfrozen from any working directory (e.g. testing this
# launcher directly with `python packaging/windows_launcher.py`,
# which -- unlike a normal `streamlit run app.py` invocation -- does
# not put the project root on `sys.path` by itself); when frozen,
# PyInstaller's own import machinery already makes every bundled
# top-level package importable regardless of `sys.path`, so this is a
# no-op safety measure in that case, not a requirement.
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from ui.layout import render_app  # noqa: E402,F401


def _find_free_port(preferred: int = 8501, attempts: int = 20) -> int:
    """Prefer 8501 (Shark Tank AI's documented default port); fall
    back to the next few ports if something else on this machine is
    already using it, rather than failing outright (spec Part 11:
    "port already occupied" must be handled, not crash)."""
    for port in range(preferred, preferred + attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.25)
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise RuntimeError(
        f"Could not find a free port in {preferred}-{preferred + attempts - 1}. "
        "Close other applications using these ports and try again."
    )


def _open_browser_when_ready(url: str, timeout_seconds: float = 20.0) -> None:
    """Poll the local server until it responds, then open the user's
    default browser -- avoids opening a browser tab to a connection
    error during Streamlit's brief startup window."""
    import urllib.request

    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(url, timeout=0.5)  # noqa: S310 (local-only, fixed scheme)
            webbrowser.open(url)
            return
        except Exception:
            time.sleep(0.3)
    # If Streamlit is unusually slow to start, open anyway -- the
    # browser will simply retry the connection until it's ready.
    webbrowser.open(url)


def main() -> None:
    # `.env`, and the default relative `logs/app.log`, resolve against
    # the current working directory (config/settings.py,
    # config/logging_config.py) -- anchoring it at the executable's own
    # folder, rather than trusting whatever directory Windows launched
    # the .exe from, keeps both predictable across every launch method
    # (double-click, a desktop shortcut, `cmd.exe`, a pinned taskbar
    # icon, ...), and is where a user would naturally create `.env`.
    os.chdir(_user_facing_dir())

    app_script = _find_app_script()

    port = _find_free_port()
    url = f"http://localhost:{port}"

    threading.Thread(target=_open_browser_when_ready, args=(url,), daemon=True).start()

    # Programmatic equivalent of:
    #   streamlit run app.py --server.port <port> --server.address localhost
    #     --server.headless true --browser.gatherUsageStats false
    # `--server.headless true` stops Streamlit from trying to manage
    # the browser itself (this launcher does that instead, only once
    # the server is actually ready) and suppresses the "you can now
    # view your app" console prompt, which has no terminal to print to
    # once this is a windowed .exe.
    sys.argv = [
        "streamlit",
        "run",
        str(app_script),
        "--server.port",
        str(port),
        "--server.address",
        "localhost",
        "--server.headless",
        "true",
        "--browser.gatherUsageStats",
        "false",
        "--global.developmentMode",
        "false",
    ]

    import streamlit.web.cli as stcli

    sys.exit(stcli.main())


if __name__ == "__main__":
    main()
