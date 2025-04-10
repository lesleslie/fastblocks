import os
from enum import Enum
from pathlib import Path
from subprocess import DEVNULL
from subprocess import run as execute

import nest_asyncio
import typer
import uvicorn
from acb.console import console
from granian import Granian
from typing_extensions import Annotated

nest_asyncio.apply()

__all__ = (
    "create",
    "run",
    "dev",
)

fastblocks_path = Path(__file__).parent

apps_path = Path.cwd()

if Path.cwd() == fastblocks_path:
    raise SystemExit(
        "FastBlocks can not be run in the same directory as FastBlocks itself. Run "
        "`python -m fastblocks create`. Move into the app directory and try again."
    )

cli = typer.Typer(rich_markup_mode="rich")


class Styles(str, Enum):
    bulma = "bulma"
    webawesome = "webawesome"
    custom = "custom"

    def __str__(self) -> str:
        return self.value


run_args = dict(
    app="main:app",
)

dev_args = run_args | dict(port=8000, reload=True)

granian_dev_args = dev_args | dict(
    address="127.0.0.1",
    reload_paths=[Path.cwd(), fastblocks_path],
    interface="asgi",
    log_enabled=False,
    log_access=True,
    reload_ignore_dirs=[
        "tmp",
        "settings",
        "templates",
    ],
)

uvicorn_dev_args = run_args | dict(
    host=granian_dev_args["address"],
    reload_includes=[
        "*.py",
        *[str(p) for p in granian_dev_args["reload_paths"]],  # type: ignore
    ],
    reload_excludes=[
        f"{d}/*"
        for d in granian_dev_args["reload_ignore_dirs"]  # type: ignore
    ],
    lifespan="on",
)


@cli.command()
def run(docker: bool = False, granian: bool = False) -> None:
    if docker:
        execute(f"docker run -it -ePORT=8080 -p8080:8080 {Path.cwd().stem}".split())
    elif granian:
        Granian(
            **run_args
            | dict(
                address="0.0.0.0",  # type: ignore  # nosec B104
                interface="asgi",
            )
        ).serve()
    else:
        uvicorn.run(**run_args | dict(host="0.0.0.0"))  # nosec B104  # type: ignore


@cli.command()
def dev(granian: bool = False) -> None:
    if granian:
        Granian(**granian_dev_args).serve()  # type: ignore
    else:
        uvicorn.run(**uvicorn_dev_args)  # type: ignore


@cli.command()
def create(
    app_name: Annotated[
        str, typer.Option(prompt=True, help="Name of your application")
    ],
    style: Annotated[
        Styles,
        typer.Option(
            prompt=True,
            help="The style (css, or web component, framework) you want to use"
            "[{','.join(Styles._member_names_)}]",
        ),
    ] = Styles.bulma,
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
        ["pdm", "info"],
        ["python", "-m", "fastblocks", "run"],
    )
    for command in commands:
        execute(command, stdout=DEVNULL, stderr=DEVNULL)
    console.print(
        "\n[bold][white]Project is initialized. Please configure [green]'adapters.yml'"
        f"[/] and [green]'app.yml'[/] in the [blue]'{app_name}/settings'[/] "
        "directory before running [magenta]`python -m fastblocks dev`[/] or "
        f"[magenta]`python -m fastblocks run`[/] from the [blue]'{app_name}'[/] "
        f"directory.[/][/]"
    )
    raise SystemExit()
