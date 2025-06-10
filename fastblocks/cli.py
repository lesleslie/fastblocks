import asyncio
import os
import signal
import sys
import typing as t
from enum import Enum
from pathlib import Path
from subprocess import DEVNULL
from subprocess import run as execute
from typing import Annotated

import nest_asyncio
import typer
import uvicorn
from acb.actions.encode import dump, load
from acb.console import console
from anyio import Path as AsyncPath
from granian import Granian

nest_asyncio.apply()
__all__ = ("create", "run", "dev", "cli")
default_adapters = dict(
    routes="default", templates="jinja2", auth="basic", sitemap="asgi"
)
fastblocks_path = Path(__file__).parent
apps_path = Path.cwd()
if Path.cwd() == fastblocks_path:
    raise SystemExit(
        "FastBlocks can not be run in the same directory as FastBlocks itself. Run `python -m fastblocks create`. Move into the app directory and try again."
    )
cli = typer.Typer(rich_markup_mode="rich")


class Styles(str, Enum):
    bulma = "bulma"
    webawesome = "webawesome"
    custom = "custom"

    def __str__(self) -> str:
        return self.value


run_args = dict(app="main:app")
dev_args = run_args | dict(port=8000, reload=True)
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
    def handle_signal(sig: int, _: t.Any) -> None:
        print(f"\nReceived signal {sig}. Shutting down gracefully...")
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)


@cli.command()
def run(docker: bool = False, granian: bool = False, host: str = "127.0.0.1") -> None:
    if docker:
        execute(f"docker run -it -ePORT=8080 -p8080:8080 {Path.cwd().stem}".split())
    else:
        setup_signal_handlers()
        if granian:
            from granian.constants import Interfaces

            Granian("main:app", address=host, interface=Interfaces.ASGI).serve()
        else:
            uvicorn.run(app=run_args["app"], host=host, lifespan="on")


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
        )


@cli.command()
def create(
    app_name: Annotated[
        str, typer.Option(prompt=True, help="Name of your application")
    ],
    style: Annotated[
        Styles,
        typer.Option(
            prompt=True,
            help="The style (css, or web component, framework) you want to use[{','.join(Styles._member_names_)}]",
        ),
    ] = Styles.bulma,
    domain: Annotated[
        str, typer.Option(prompt=True, help="Application domain")
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
            (fastblocks_path / p).read_text().replace("APP_NAME", app_name)
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
        await update_settings("debug", dict(fastblocks=False))
        await update_settings("adapters", default_adapters)
        await update_settings("app", dict(title="Welcome to FastBlocks", domain=domain))

    asyncio.run(update_configs())
    console.print(
        f"\n[bold][white]Project is initialized. Please configure [green]'adapters.yml'[/] and [green]'app.yml'[/] in the [blue]'{app_name}/settings'[/] directory before running [magenta]`python -m fastblocks dev`[/] or [magenta]`python -m fastblocks run`[/] from the [blue]'{app_name}'[/] directory.[/][/]"
    )
    raise SystemExit()
