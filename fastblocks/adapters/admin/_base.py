# Oneiric imports
from oneiric.core.config import OneiricSettings


class AdminBaseSettings(OneiricSettings):  # type: ignore[misc]
    """Admin base settings using OneiricSettings."""

    style: str = "bootstrap"
    title: str = "FastBlocks Dashboard"


class AdminBase:
    """Admin base adapter using Oneiric."""

    def __init__(self, settings: AdminBaseSettings | None = None):
        self.settings = settings or AdminBaseSettings()
