# Project Overview

This project is **FastBlocks**, an asynchronous Python web framework built on [Starlette](https://www.starlette.io/) and inspired by [FastAPI](https://fastapi.tiangolo.com/). It is specifically designed for the rapid delivery of server-side rendered [HTMX](https://htmx.org/)/[Jinja](https://jinja.palletsprojects.com/en/3.1.x/) template blocks.

The framework is modular and component-based, leveraging the [Asynchronous Component Base (ACB)](https://github.com/lesleslie/acb) framework for dependency injection, configuration management, and a pluggable adapter system. This allows for easy swapping of components like templates, authentication, admin interfaces, and storage.

**Key Technologies:**

- **Backend:** Python, Starlette, FastAPI (inspiration)
- **Frontend:** HTMX, Jinja2
- **Core:** Asynchronous Component Base (ACB)
- **Database:** SQL (PostgreSQL, MySQL, SQLite) and NoSQL (MongoDB, Firestore, Redis) with support for SQLModel, SQLAlchemy, Pydantic, msgspec, attrs, and Redis-OM.
- **Tooling:** `uv` (or `pip`), `pytest`, `ruff`, `mypy`, `pyright`, `bandit`, `vulture`, `creosote`, `refurb`, `codespell`, `pyproject-fmt`, `crackerjack`, `excalidraw-mcp`, `penpot-mcp`, `session-mgmt-mcp`.

# Building and Running

## Installation

Install the project and its dependencies using `uv`:

```bash
uv add -e .
```

Or with pip:

```bash
pip install -e .
```

## Running the Application

### Development

To run the application in development mode with hot-reloading:

```bash
python -m fastblocks dev
```

You can also use Granian, a high-performance ASGI server:

```bash
python -m fastblocks dev --granian
```

### Production

To run the application in production mode:

```bash
python -m fastblocks run
```

You can also run the application in a Docker container:

```bash
python -m fastblocks run --docker
```

## Testing

The project uses `pytest` for testing. To run the tests:

```bash
pytest
```

# Development Conventions

## Linting and Formatting

The project uses `ruff` for linting and formatting. To check for linting errors and format the code:

```bash
ruff check . --fix
ruff format .
```

## Static Typing

The project uses `mypy` and `pyright` for static type checking. To run the type checkers:

```bash
mypy .
pyright .
```

## CLI

The project includes a command-line interface (CLI) for managing the application. Here are some of the most common commands:

- `python -m fastblocks create`: Create a new FastBlocks project.
- `python -m fastblocks components`: List available components.
- `python -m fastblocks scaffold`: Scaffold a new HTMY component.
- `python -m fastblocks list`: List all discovered HTMY components.
- `python -m fastblocks validate`: Validate a specific HTMY component.
- `python -m fastblocks info`: Get detailed information about an HTMY component.
- `python -m fastblocks syntax-check`: Check FastBlocks template syntax.
- `python -m fastblocks format-template`: Format a FastBlocks template file.
- `python -m fastblocks generate-ide-config`: Generate IDE configuration files.
- `python -m fastblocks start-language-server`: Start the FastBlocks Language Server.
- `python -m fastblocks version`: Show the FastBlocks version.
- `python -m fastblocks mcp`: Start the FastBlocks MCP (Model Context Protocol) server.
