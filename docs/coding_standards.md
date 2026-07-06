# Coding Standards

These standards apply to every future release. Where the current
codebase already follows a standard, that is noted as **already
followed**. Where a standard describes a convention not yet exercised
by any existing code (because the relevant feature doesn't exist yet),
that is noted as **not yet exercised**.

## Python

- **Version:** 3.12, matching `pyproject.toml`'s
  `requires-python = ">=3.12"`. Do not use syntax requiring a newer
  version without updating that constraint deliberately.
- Every module begins with a module-level docstring stating its
  purpose. *(Already followed — every existing module does this.)*
- `from __future__ import annotations` is used in every module that
  has type annotations, to keep annotation evaluation lazy and
  consistent. *(Already followed.)*

## Formatting

- **Black**, line length 100, target version `py312`, per
  `pyproject.toml`'s `[tool.black]` section. *(Already configured;
  run `black .` before committing.)*
- **Ruff**, line length 100, target version `py312`, per
  `pyproject.toml`'s `[tool.ruff]` section, used for linting (not
  formatting). *(Already configured; run `ruff check .`.)*

## Typing

- **mypy**, configured in `pyproject.toml`'s `[tool.mypy]` section
  (`python_version = "3.12"`, `ignore_missing_imports = true`).
  *(Already configured.)*
- Every public function and method has a full type signature,
  including return type. *(Already followed in existing code; a
  future release adding untyped public functions is a regression.)*
- Prefer concrete types from `models/` over `dict`/`Any` wherever a
  pydantic model already exists for that shape — see
  `agent_contract.md` → *Inputs* and *Outputs* for how this applies to
  agents specifically.

## Imports

- Standard library imports, then third-party, then local — each group
  separated by a blank line. *(Already followed; enforced going
  forward via `ruff`.)*
- No wildcard imports (`from x import *`).
- A package's `__init__.py` stays empty unless a future release
  deliberately decides to re-export a public API from it — do not add
  re-exports incidentally.

## Logging

- Every module that logs obtains its logger via
  `config.logging_config.get_logger(__name__)` — never
  `logging.getLogger(__name__)` directly, and never `print()` for
  anything other than throwaway local debugging. *(Already followed
  in `app.py`; binding for all future backend modules.)*
- `setup_logging()` is called exactly once, at process startup
  (`app.py`). No other module should call it.
- Log level and destination (console vs. rotating file) are controlled
  exclusively through `Settings.log_level` / `Settings.log_to_file` /
  `Settings.log_file_path` — never hardcoded in a logging call.

## Error Handling

- **Not yet exercised** by current code (existing placeholders raise
  `NotImplementedError` as a scaffolding marker, not as designed error
  handling). When real logic is implemented:
  - Catch specific exceptions, never a bare `except Exception:` that
    silently swallows an error.
  - See `agent_contract.md` → *Error Handling* for the
    recoverable-vs-unrecoverable distinction agents must follow
    specifically.
  - User-facing errors surfaced in the UI must be actionable
    (tell the founder what to do next), not a raw stack trace or
    exception message.

## Naming

- Modules and functions: `snake_case`. Classes: `PascalCase`. Constants
  and module-level lookup tables: `UPPER_SNAKE_CASE` (e.g.,
  `PHASE_LABELS`, `PROPOSAL_TYPES`). *(Already followed.)*
- Private, module-internal helper functions are prefixed with a single
  underscore (e.g., `ui/proposal.py`'s `_render_text_input`).
  *(Already followed throughout `ui/`.)*
- Enum values are lowercase strings matching their Python identifier's
  meaning (e.g., `SessionPhase.PROPOSAL_UPLOADED = "proposal_uploaded"`)
  so they serialize predictably to JSON/session state. *(Already
  followed in `models/enums.py`.)*

## Dependency Injection

- A component depends on an abstraction, never a concrete
  implementation, wherever an abstraction already exists: agents
  depend on `BaseProvider` and `BaseMemory`, not on
  `AnthropicProvider` or `InMemoryStore` directly. *(Already
  established as the pattern via `agents/base_agent.py`'s
  constructor signature; binding for all future agent
  implementations — see `agent_contract.md`.)*
- Concrete implementations are selected at the composition boundary
  (today, that boundary doesn't exist yet since nothing is wired
  together; when it does, it belongs in `orchestrator/`, not
  scattered across call sites).

## Configuration

- All configuration flows through `config.settings.get_settings()`.
  No module reads `os.environ` directly. *(Already followed.)*
- Every setting has a safe default — the application must always be
  able to start with zero configuration (no `.env`, no API keys). This
  is a hard constraint verified by `tests/test_config.py`.
  *(Already followed and tested.)*

## Session State

- All Streamlit session state keys are defined in one place,
  `ui/session_state.py`'s `_default_state()`. No other `ui/` module
  invents a new top-level state key without adding it there first.
  *(Already followed.)*
- Widget-specific keys (e.g., a text area's `key=` argument) are
  scoped to the component that owns that widget and are not read by
  other components. *(Already followed — e.g.,
  `ui/response.py`'s rotating `user_response_input_{nonce}` key is
  only ever read inside that same module.)*
- Follow Progressive Disclosure (`architecture.md`): new session state
  that represents advanced/diagnostic information should be gated
  behind an explicit toggle (following the existing `verbose_mode` /
  `developer_mode` pattern in `ui/sidebar.py`), not surfaced
  unconditionally.

## JSON Schemas

- **Not yet exercised** — no component currently serializes agent
  output to JSON for an external boundary (e.g., an API response or
  an MCP tool call). When one is added, its schema must be defined as
  a pydantic model in `models/schemas.py` first; the JSON shape is
  derived from that model (via `.model_dump()` /
  `.model_json_schema()`), not hand-written separately and kept in
  sync manually.

## Prompt Management

- Every prompt is a plain-text `.txt` file in `prompts/`, loaded via
  `prompts.loader.load_prompt(name)`. *(Already followed for the
  three existing templates.)*
- No prompt text is embedded as a Python string literal inside agent
  or provider code, even for a short one-off prompt — it still belongs
  in `prompts/` so it can be edited without touching code.
- A prompt template name passed to `load_prompt()` must correspond to
  an actual file; there is no silent fallback to a default prompt.
  *(Already the behavior of `load_prompt()`, which raises
  `FileNotFoundError` if the file is missing.)*

## Modularity — No Duplicated Logic

- Shared vocabulary (state values, speaker roles, provider identifiers)
  is defined exactly once in `models/enums.py` and imported everywhere
  it's needed — never redefined locally as a string literal or a
  second enum. *(Already followed — e.g., `ui/header.py`,
  `ui/proposal.py`, and `ui/conversation.py` all import from
  `models.enums` rather than each defining their own phase or speaker
  constants.)*
- Session state defaults are defined exactly once
  (`ui/session_state.py`), never duplicated as a fallback default
  inline in a component that reads a key expected to already exist.
- Page composition happens exactly once, in `ui/layout.py`. Individual
  `ui/` components do not import and render each other directly —
  `layout.py` is the only place components are wired together.
  *(Already followed.)*
- Documentation duplication follows the same rule: each of these
  documents owns one concern (`architecture.md` for system design,
  `state_machines.md` for state, `event_catalog.md` for messages,
  `agent_contract.md` for the agent interface, `folder_structure.md`
  for ownership, this document for engineering conventions). A future
  edit that needs to touch more than one of these to stay consistent
  is a signal the content was duplicated across them and should be
  consolidated into whichever document owns that concern, with the
  others linking to it instead.
