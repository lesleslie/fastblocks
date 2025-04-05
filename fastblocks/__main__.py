import os
from pathlib import Path
from subprocess import run as execute

import typer
import uvicorn
from acb.console import console
from granian import Granian
from rich.prompt import Prompt

fastblocks_path = Path(__file__).parent

app_name = Path.cwd().stem

if Path.cwd() == fastblocks_path:
    raise SystemExit(
        "FastBlocks can not be run in the same directory as FastBlocks itself."
    )

cli = typer.Typer(rich_markup_mode="rich")


@cli.command()
def create() -> None:
    console.print("Creating new FastBlocks project...")
    app_name = Prompt.ask("Enter project name: ")
    style = Prompt.ask(
        "Choose style: ", choices=["bulma", "webawesome"], default="bulma"
    )
    execute(["pdm", "init", "-p", app_name], shell=True)
    os.chdir(Path(app_name))
    envrc = fastblocks_path / ".envrc"
    Path(".envrc").write_text(envrc.read_text())
    execute("direnv allow .".split())
    execute(["pdm", "add", "fastblocks"])
    main = fastblocks_path / "main.py"
    Path("main.py").write_text(main.read_text())
    templates = fastblocks_path / "templates"
    (templates / "base/blocks").mkdir(parents=True, exist_ok=True)
    (templates / f"{style}/blocks").mkdir(parents=True, exist_ok=True)
    (templates / f"{style}/theme").mkdir(parents=True, exist_ok=True)
    for p in ("models.py", "routes.py"):
        Path.touch(Path(p))
    execute("python -m fastblocks run")


@cli.command()
def run(docker: bool = False, granian: bool = False) -> None:
    os.chdir(Path.cwd())
    try:
        if docker:
            execute(f"docker run -it -ePORT=8080 -p8080:8080 {app_name}".split())
        if granian:
            reload_paths = [Path.cwd(), fastblocks_path]
            Granian(
                "main:app",
                address="127.0.0.1",
                port=8000,
                reload=True,
                interface="asgi",  # type: ignore # Granian typing issue
                log_enabled=False,
                log_access=True,
                reload_paths=reload_paths,
                reload_ignore_patterns=["_version"],
                reload_ignore_dirs=[
                    "tmp",
                    "settings",
                    "templates",
                ],
            ).serve()
        else:
            uvicorn.run(
                "main:app",
                host="127.0.0.1",
                port=8000,
                reload=True,
                reload_includes=["*.py", str(Path.cwd()), str(fastblocks_path)],
                reload_excludes=[
                    "tmp/*",
                    "settings/*",
                    "templates/*",
                ],
                lifespan="on",
            )
    except KeyError:
        console.print(
            "Project initialized. Please configure 'adapters.yml' "
            "and 'app.yml' in the settings directory before running the application "
            "`python -m fastblocks run`"
        )


if __name__ == "__main__":
    cli()
