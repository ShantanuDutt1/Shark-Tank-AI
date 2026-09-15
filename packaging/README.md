# Building the Windows Package

This produces a standalone, double-clickable Windows build of Shark Tank AI
(`SharkTankAI.exe` plus its dependencies) that a user can run without
installing Python, Git, or any project dependency.

## What this is (and isn't)

This is a **thin packaging layer** around the existing application. It adds
no agent, orchestration, or UI logic — `packaging/windows_launcher.py` only
picks a working directory and a free local port, starts Streamlit's own CLI
programmatically, and opens the browser once the server responds. The actual
application (`app.py`, `agents/`, `orchestrator/`, `ui/`, ...) is completely
unchanged and unaware it's running inside a packaged build.

## Building

From a Windows machine with this project's dependencies and `pyinstaller`
installed:

```bash
pip install -r requirements.txt
pip install pyinstaller
python packaging/build_windows.py
```

Output: `dist_windows/SharkTankAI/` — a **onedir** build (the executable plus
its dependencies as loose files in the same folder), not a single
self-extracting binary. Onedir was chosen deliberately: onefile builds
extract themselves to a temp directory on every launch, which is slower to
start and makes Streamlit's own static-asset serving less reliable in
practice. Distribute the whole `SharkTankAI/` folder (zipped) — the `.exe`
alone will not run correctly without the files next to it.

## Why `--collect-all streamlit` is avoided

An early attempt used `--collect-all streamlit`, which forces PyInstaller to
bundle every *optional* integration Streamlit merely supports — matplotlib,
tkinter, scipy, sqlalchemy, win32com — regardless of whether this
application ever imports them. That produced an extremely slow build and a
needlessly bloated package. `build_windows.py` instead uses
`--copy-metadata streamlit` (Streamlit reads its own version via
`importlib.metadata` at runtime) and `--collect-data streamlit` (bundles
Streamlit's static frontend assets and default config) — the two things
Streamlit actually needs — and lets PyInstaller's normal import-graph
analysis find this application's real dependencies (`pydantic`, `anthropic`,
`pypdf`, `reportlab`, ...).

The trade-off: dropping `--collect-all` also drops Streamlit's own
dynamically-imported modules that no static analysis can see (found via an
actual launch test, not guessed) — `windows_launcher.py` bundling `app.py`
and forcing the real import graph is not quite the whole story, since
Streamlit's script-runner itself imports `streamlit.runtime.scriptrunner
.magic_funcs` (its "magic" expression-display feature) dynamically at
script-run time. `build_windows.py` adds it as an explicit
`--hidden-import`. If a future Streamlit upgrade introduces another such
dynamic import, the symptom is a `ModuleNotFoundError` naming the missing
module the first time the built `.exe` is actually launched (not at build
time) — add it as another `--hidden-import` and rebuild; this is the normal,
expected way to extend this list, not a sign something is fundamentally
broken.

## API key handling

The build never contains an API key. `windows_launcher.py` changes the
working directory to the executable's own folder before starting Streamlit,
so the existing `.env`-file loading (`config/settings.py`, via
`pydantic-settings`) looks for `.env` right next to `SharkTankAI.exe` — the
same mechanism the app has always used, just anchored to a predictable
location instead of whatever directory happened to be current when Windows
launched the `.exe`. Users create this file themselves; it is never bundled,
generated, or logged.

## Testing a build

1. Run `dist_windows/SharkTankAI/SharkTankAI.exe` directly (double-click, or
   from a terminal to see console output).
2. Confirm the browser opens to a working Shark Tank AI session with no
   `.env` present (fallback mode).
3. Add a `.env` with a real `ANTHROPIC_API_KEY` next to the `.exe` and
   confirm real AI-driven analysis.
4. Run a second launch while the first is still open — confirm it picks a
   different port rather than failing.
5. Complete a full session, download the report, reset, and start a second
   session — confirm no leftover state.

## Known limitations

- The executable is **unsigned** — Windows SmartScreen will warn on first
  run. Code signing requires a paid certificate; not pursued for this
  release. See the README's Troubleshooting section for what to tell users.
- Windows-only. macOS/Linux standalone builds are not part of this release.
