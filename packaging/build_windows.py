"""
Build script for the standalone Windows package (Release 1.0).

Wraps a single PyInstaller invocation so the build is reproducible
from a clean checkout and documented in one place, rather than a
command a developer has to remember or reconstruct. This script
contains no packaging logic of its own beyond argument assembly --
PyInstaller does the actual bundling.

Usage (from the repository root, in an environment with this
project's requirements *and* `pyinstaller` installed):

    python packaging/build_windows.py

Output: dist_windows/SharkTankAI/ (a onedir build -- SharkTankAI.exe
plus its dependencies as loose files, not a single self-extracting
binary). Onedir was chosen over onefile deliberately -- see
packaging/README.md for why.

Never bundles a `.env` file or any API key. The build only ever reads
this project's own source and its installed dependencies.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = ROOT / "dist_windows"
WORK_DIR = ROOT / "build_windows_work"
APP_NAME = "SharkTankAI"


def main() -> int:
    if sys.platform != "win32":
        print(
            "Warning: this produces a Windows executable and is normally run "
            "on Windows. Continuing anyway (PyInstaller does not cross-compile, "
            "so a non-Windows run will build a package for the current OS "
            "instead, not for Windows).",
            file=sys.stderr,
        )

    # A clean build every time -- PyInstaller's own incremental cache
    # has produced stale-resource bugs in the past for projects with
    # data files (like our prompts/*.txt); reproducibility matters
    # more than build speed for a release artifact.
    for stale_dir in (DIST_DIR, WORK_DIR):
        if stale_dir.exists():
            shutil.rmtree(stale_dir)

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onedir",
        "--name",
        APP_NAME,
        "--distpath",
        str(DIST_DIR),
        "--workpath",
        str(WORK_DIR),
        "--specpath",
        str(ROOT / "packaging"),
        "--add-data",
        f"{ROOT / 'prompts'}{';' if sys.platform == 'win32' else ':'}prompts",
        # A real, on-disk copy of app.py -- Streamlit's CLI execs the
        # actual source file, so it must exist as a genuine file next
        # to the bundled data (see windows_launcher.py::_find_app_script()),
        # not merely be reachable through PyInstaller's frozen import
        # machinery the way agents/orchestrator/ui/etc. are.
        "--add-data",
        f"{ROOT / 'app.py'}{';' if sys.platform == 'win32' else ':'}.",
        # Deliberately NOT `--collect-all streamlit`: that forces
        # PyInstaller to bundle every optional integration Streamlit
        # merely *supports* (matplotlib, tkinter, sqlalchemy, win32com,
        # scipy, ...) whether or not this application ever imports it,
        # producing a bloated, very-slow-to-build package. Streamlit
        # only needs its own static frontend assets and its installed
        # package metadata (it reads its own version via
        # importlib.metadata at runtime) -- `--collect-data` +
        # `--copy-metadata` provide exactly that, while this app's own
        # actual imports (pydantic, anthropic, pypdf, reportlab, ...)
        # are found by PyInstaller's normal import-graph analysis.
        "--copy-metadata",
        "streamlit",
        "--collect-data",
        "streamlit",
        # Streamlit's script-runner imports this dynamically (to support
        # "magic" expression-display), not through a top-level import
        # statement PyInstaller's static analysis can see -- confirmed
        # missing via a real launch test (`ModuleNotFoundError:
        # streamlit.runtime.scriptrunner.magic_funcs`), not guessed
        # preemptively.
        "--hidden-import",
        "streamlit.runtime.scriptrunner.magic_funcs",
        "--hidden-import",
        "pydantic_settings",
        "--hidden-import",
        "anthropic",
        "--hidden-import",
        "pypdf",
        "--hidden-import",
        "reportlab",
        "--console",  # keep a console window -- see packaging/README.md
        str(ROOT / "packaging" / "windows_launcher.py"),
    ]

    print("Running:", " ".join(cmd))
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        print("Build failed.", file=sys.stderr)
        return result.returncode

    app_dir = DIST_DIR / APP_NAME
    print(f"\nBuild complete: {app_dir}")
    print(f"Launch with: {app_dir / (APP_NAME + '.exe')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
