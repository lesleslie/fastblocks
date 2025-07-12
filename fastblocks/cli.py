import asyncio
import logging
import os
import signal
import typing as t
from contextlib import suppress
from enum import Enum
from importlib.metadata import version as get_version
from pathlib import Path
from subprocess import DEVNULL
from subprocess import run as execute
from typing import Annotated

with suppress(ImportError):
    from acb.logger import InterceptHandler

    for logger_name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        logger.addHandler(InterceptHandler())
        logger.setLevel(logging.DEBUG)
        logger.propagate = False

import nest_asyncio
import typer
import uvicorn
from acb.actions.encode import dump, load
from acb.console import console
from anyio import Path as AsyncPath
from granian import Granian

nest_asyncio.apply()
__all__ = ("cli", "components", "create", "dev", "run")
default_adapters = {
    "routes": "default",
    "templates": "jinja2",
    "auth": "basic",
    "sitemap": "asgi",
}
fastblocks_path = Path(__file__).parent
apps_path = Path.cwd()
if Path.cwd() == fastblocks_path:
    msg = "FastBlocks can not be run in the same directory as FastBlocks itself. Run `python -m fastblocks create`. Move into the app directory and try again."
    raise SystemExit(
        msg,
    )
cli = typer.Typer(rich_markup_mode="rich")


class Styles(str, Enum):
    bulma = "bulma"
    webawesome = "webawesome"
    custom = "custom"

    def __str__(self) -> str:
        return self.value


run_args = {"app": "main:app"}
dev_args = run_args | {"port": 8000, "reload": True}
granian_dev_args = dev_args | {
    "address": "127.0.0.1",
    "reload_paths": [Path.cwd(), fastblocks_path],
    "interface": "asgi",
    "log_enabled": False,
    "log_access": True,
    "reload_ignore_dirs": ["tmp", "settings", "templates"],
}
uvicorn_dev_args = dev_args | {
    "host": "127.0.0.1",
    "reload_includes": ["*.py", str(Path.cwd()), str(fastblocks_path)],
    "reload_excludes": ["tmp/*", "settings/*", "templates/*"],
    "lifespan": "on",
}


def setup_signal_handlers() -> None:
    import sys

    def signal_handler(_signum: int, _frame: t.Any) -> None:
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


@cli.command()
def run(docker: bool = False, granian: bool = False, host: str = "127.0.0.1") -> None:
    if docker:
        execute(
            f"docker run -it -ePORT=8080 -p8080:8080 {Path.cwd().stem}".split(),
        )
    else:
        setup_signal_handlers()
        if granian:
            from granian.constants import Interfaces

            Granian("main:app", address=host, interface=Interfaces.ASGI).serve()
        else:
            uvicorn.run(app=run_args["app"], host=host, lifespan="on", log_config=None)


@cli.command()
def dev(granian: bool = False) -> None:
    setup_signal_handlers()
    if granian:
        from granian.constants import Interfaces

        Granian(
            "main:app",
            address="127.0.0.1",
            port=8000,
            reload=True,
            reload_paths=[Path.cwd(), fastblocks_path],
            interface=Interfaces.ASGI,
            log_enabled=False,
            log_access=True,
        ).serve()
    else:
        uvicorn.run(
            app="main:app",
            host="127.0.0.1",
            port=8000,
            reload=True,
            reload_includes=["*.py", str(Path.cwd()), str(fastblocks_path)],
            reload_excludes=["tmp/*", "settings/*", "templates/*"],
            lifespan="on",
            log_config=None,
        )


def _display_adapters() -> None:
    from acb.adapters import get_adapters

    console.print("[bold green]Available Adapters:[/bold green]")
    adapters = get_adapters()
    if not adapters:
        console.print("  [dim]No adapters found[/dim]")
        return
    categories = {}
    for adapter in adapters:
        if adapter.category not in categories:
            categories[adapter.category] = []
        categories[adapter.category].append(adapter)
    for category in sorted(categories.keys()):
        console.print(f"\n  [bold cyan]{category.upper()}:[/bold cyan]")
        for adapter in sorted(categories[category], key=lambda a: a.name):
            _display_adapter_info(adapter)


def _display_adapter_info(adapter: t.Any) -> None:
    status = "[green]✓[/green]" if adapter.installed else "[red]✗[/red]"
    enabled = "[yellow]enabled[/yellow]" if adapter.enabled else "[dim]disabled[/dim]"
    console.print(f"    {status} [white]{adapter.name}[/white] - {enabled}")
    if adapter.module:
        console.print(f"      [dim]{adapter.module}[/dim]")


def _display_default_config() -> None:
    console.print("\n[bold green]FastBlocks Default Configuration:[/bold green]")
    for category, default_name in default_adapters.items():
        console.print(f"  [cyan]{category}[/cyan]: [white]{default_name}[/white]")


def _display_actions() -> None:
    console.print("\n[bold green]FastBlocks Actions:[/bold green]")
    try:
        from fastblocks.actions.minify import minify

        console.print("  [cyan]minify[/cyan]:")
        console.print(f"    [white]- css[/white] ([dim]{minify.css.__name__}[/dim])")
        console.print(f"    [white]- js[/white] ([dim]{minify.js.__name__}[/dim])")
    except ImportError:
        console.print("  [dim]Minify actions not available[/dim]")


@cli.command()
def components() -> None:
    try:
        console.print("\n[bold blue]FastBlocks Components[/bold blue]\n")
        _display_adapters()
        _display_default_config()
        _display_actions()
    except Exception as e:
        console.print(f"[red]Error displaying components: {e}[/red]")
        console.print("[dim]Make sure you're in a FastBlocks project directory[/dim]")


@cli.command()
def create(
    app_name: Annotated[
        str,
        typer.Option(prompt=True, help="Name of your application"),
    ],
    style: Annotated[
        Styles,
        typer.Option(
            prompt=True,
            help="The style (css, or web component, framework) you want to use[{','.join(Styles._member_names_)}]",
        ),
    ] = Styles.bulma,
    domain: Annotated[
        str,
        typer.Option(prompt=True, help="Application domain"),
    ] = "example.com",
) -> None:
    app_path = apps_path / app_name
    app_path.mkdir(exist_ok=True)
    os.chdir(app_path)
    templates = Path("templates")
    for p in (
        templates / "base/blocks",
        templates / f"{style}/blocks",
        templates / f"{style}/theme",
        Path("adapters"),
        Path("actions"),
    ):
        p.mkdir(parents=True, exist_ok=True)
    for p in (
        "models.py",
        "routes.py",
        "main.py",
        ".envrc",
        "pyproject.toml",
        "__init__.py",
        "adapters/__init__.py",
        "actions/__init__.py",
    ):
        Path(p).touch()
    for p in ("main.py.tmpl", ".envrc", "pyproject.toml.tmpl", "Procfile.tmpl"):
        Path(p.replace(".tmpl", "")).write_text(
            (fastblocks_path / p).read_text().replace("APP_NAME", app_name),
        )
    commands = (
        ["direnv", "allow", "."],
        ["pdm", "install"],
        ["python", "-m", "fastblocks", "run"],
    )
    for command in commands:
        execute(command, stdout=DEVNULL, stderr=DEVNULL)

    async def update_settings(settings: str, values: dict[str, t.Any]) -> None:
        settings_path = AsyncPath(app_path / "settings")
        settings_dict = await load.yaml(settings_path / f"{settings}.yml")
        settings_dict.update(values)
        await dump.yaml(settings_dict, settings_path / f"{settings}.yml")

    async def update_configs() -> None:
        await update_settings("debug", {"fastblocks": False})
        await update_settings("adapters", default_adapters)
        await update_settings(
            "app", {"title": "Welcome to FastBlocks", "domain": domain}
        )

    asyncio.run(update_configs())
    console.print(
        f"\n[bold][white]Project is initialized. Please configure [green]'adapters.yml'[/] and [green]'app.yml'[/] in the [blue]'{app_name}/settings'[/] directory before running [magenta]`python -m fastblocks dev`[/] or [magenta]`python -m fastblocks run`[/] from the [blue]'{app_name}'[/] directory.[/][/]",
    )
    console.print(
        "\n[dim]Use [white]`python -m fastblocks components`[/white] to see available adapters and actions.[/dim]",
    )
    raise SystemExit


@cli.command()
def version() -> None:
    try:
        __version__ = get_version("fastblocks")
        console.print(f"FastBlocks v{__version__}")
    except Exception:
        console.print("Unable to determine FastBlocks version")
