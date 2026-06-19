from typing import Any

# Oneiric imports
from oneiric.core.config import OneiricSettings


class RoutesBaseSettings(OneiricSettings):  # type: ignore[misc]
    """Routes base settings using OneiricSettings."""

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)


class RoutesBase:
    """Routes base adapter using Oneiric patterns."""

    pass
