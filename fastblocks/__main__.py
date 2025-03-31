import os
from pathlib import Path
from subprocess import run as execute

import typer
import uvicorn
from acb import pkg_registry
from acb.console import console
from acb.depends import depends
from granian import Granian
from rich.traceback import install

cli = typer.Typer()

install(console=console)

config = depends.get()


@cli.command()
def run(docker: bool = False, granian: bool = False) -> None:
    os.chdir(Path.cwd())
    try:
        if docker:
            execute(f"docker run -it -ePORT=8080 -p8080:8080 {config.app.name}".split())
        if granian:
            reload_paths = [
                *[Path(p.path) for p in pkg_registry.get()],
                Path.cwd(),
                Path(__file__).parent,
            ]

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
                reload_includes=[
                    "*.py",
                    *[str(p.path) for p in pkg_registry.get()],
                    str(Path.cwd()),
                ],
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
            "and 'app.yml' before running the application."
        )


if __name__ == "__main__":
    cli()
