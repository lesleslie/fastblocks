# Repository Guidelines

## Project Structure & Module Organization

- `fastblocks/` contains the framework runtime, with `applications.py`, `cli.py`, and middleware wiring the Starlette app entry points.
- `fastblocks/actions`, `fastblocks/adapters`, and `fastblocks/mcp` expose pluggable building blocks; keep new modules colocated with their family and register them via the existing initializer patterns.
- `tests/` mirrors the runtime layout (`actions/`, `adapters/`, `mcp/`, performance suites) so place new test files beside the feature they cover.
- `docs/`, `images/`, and generated `build/` or `dist/` assets support packaging and marketing; avoid editing generated artifacts directly.

## Build, Test, and Development Commands

- `uv sync` installs locked dependencies; run after modifying `pyproject.toml` or `uv.lock`.
- `uv run python -m fastblocks --help` surfaces the Typer CLI; use `uv run python -m fastblocks serve` to launch the demo app.
- `uv run python -m pytest` executes the full test suite; add `--cov=fastblocks` to respect the default coverage gate.
- `uv run python -m crackerjack -t --ai-fix` runs the house quality gate (pytest, lint, type checks) and auto-applies safe fixes.
- `uv build` produces distributable wheels and source archives in `dist/`.

## Coding Style & Naming Conventions

- Format with `ruff format`; lint with `ruff check --fix` before sending a review.
- Write modern Python 3.13 using 4-space indentation, type hints, and dataclasses or Pydantic models where idiomatic.
- Follow `snake_case` for functions and module globals, `PascalCase` for classes, and `SCREAMING_SNAKE_CASE` for constants.
- Prefer dependency-injected services over direct imports; extend existing adapters instead of duplicating logic.

## Testing Guidelines

- Use `pytest` markers (`@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.benchmark`) to classify coverage; keep slow tests opt-in.
- Mirror runtime structure inside `tests/`, and lean on the provided mock adapters and `MockAsyncPath` helpers to avoid filesystem I/O.
- Target at least the configured `fail_under` 31% coverage and document intentional gaps in the PR description.
- When adding async code, include both happy-path and cancellation tests to satisfy `pytest-asyncio`'s strict mode.

## Commit & Pull Request Guidelines

- Follow the existing Conventional Commit style: `type(scope): summary` (for example, `fix(middleware): prevent stale cache headers`).
- Keep commits focused; refactor-only changes belong in separate `refactor(*)` commits.
- Pull requests should summarize the change, link related issues, paste key command output (`uv run python -m pytest`), and note any configuration updates.
- Include screenshots or cURL transcripts when updating HTMX fragments or adapter responses, and update `docs/` navigation when adding public features.
