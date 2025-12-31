# Oneiric imports
from oneiric.core.config import OneiricSettings


class RoutesBaseSettings(OneiricSettings):
    """Routes base settings using OneiricSettings."""

    def __init__(self, **data: dict) -> None:
        super().__init__(**data)


class RoutesBase:
    """Routes base adapter using Oneiric patterns."""

    pass
