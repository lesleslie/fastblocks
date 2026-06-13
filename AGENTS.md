# Repository Guidelines

## Project Structure & Module Organization

- `fastblocks/` contains the core framework package, including the application layer, adapters, actions, middleware, shell integration, and MCP support under `mcp/`.
- Supporting docs live in `docs/`, adapter-specific guidance in `fastblocks/adapters/README.md`, and action references in `fastblocks/actions/README.md`.
- Tests live in `tests/`; mirror the package structure when adding new coverage.
- Generated artifacts such as `dist/`, `htmlcov/`, and local runtime data should not be edited manually.

## Build, Test, and Development Commands

- `uv sync --group dev` installs development dependencies.
- `uv run pytest` runs the full test suite; use `-k <pattern>` for targeted runs.
- `uv run pytest --cov=fastblocks --cov-report=html` regenerates local coverage reports.
- `uv run ruff check fastblocks tests` and `uv run ruff format fastblocks tests` cover linting and formatting.
- Use the documented CLI or server commands from `README.md` when smoke-testing the framework or MCP layer locally.
- Use Crackerjack as the repo-wide quality and CI/CD gate before merging framework changes.

## Coding Style & Naming Conventions

- Use Python 3.13+ features with explicit type hints and small composable modules.
- Preserve the Oneiric-driven adapter architecture; avoid adding shortcuts that bypass adapters, configuration, or dependency resolution patterns.
- Keep modules snake_case, classes PascalCase, and public framework APIs stable and well-typed.

## Testing Guidelines

- Add tests for framework behavior changes, especially around adapters, middleware, template rendering, MCP resources, and websocket flows.
- Prefer deterministic fixtures and isolated app setups over broad integration scripts when a smaller test will prove the behavior.
- Review coverage after larger framework changes to avoid regressions in cross-cutting modules.

## Commit & Pull Request Guidelines

- Use focused commits such as `feat(mcp): add config health resource` or `fix(templates): preserve async fragment context`.
- PRs should describe the affected subsystem, commands run for validation, and any framework-level compatibility impact.

## Security & Configuration Tips

- Keep secrets, deployment-specific settings, and local runtime paths out of version control.
- Validate MCP inputs, config discovery paths, and shell-adjacent features carefully.
