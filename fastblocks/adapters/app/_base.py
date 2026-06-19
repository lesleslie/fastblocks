import typing as t

# Oneiric imports
from oneiric.core.config import OneiricSettings
from starlette.routing import Router


class AppBaseSettings(OneiricSettings):  # type: ignore[misc]
    """App base settings using OneiricSettings."""

    name: str = "fastblocks"
    style: str = "vanilla"
    theme: str = "light"


class AppProtocol(t.Protocol):
    def __init__(self) -> None: ...

    async def lifespan(self) -> t.AsyncIterator[None]: ...


class AppBase:
    """App base adapter using Oneiric."""

    router: Router | None

    def __init__(self) -> None:
        self.router = None
