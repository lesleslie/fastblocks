"""Base classes and protocols for font adapters."""

from contextlib import suppress
from typing import Protocol
from uuid import UUID

# Oneiric imports
from oneiric.core.config import OneiricSettings
from oneiric.core.resolution import Resolver

# Oneiric resolver for dependency injection
depends = Resolver()


class FontsBaseSettings(OneiricSettings):
    """Base settings for font adapters using OneiricSettings."""

    primary_font: str = "Arial, sans-serif"
    secondary_font: str = "Georgia, serif"
    cdn_url: str | None = None
    font_weights: list[str] = ["400", "700"]

    def __init__(self, **data: dict) -> None:
        super().__init__(**data)


class FontsProtocol(Protocol):
    """Protocol for font adapter implementations."""

    async def get_font_import(self) -> str: ...
    def get_font_family(self, font_type: str) -> str: ...


class FontsBase:
    """Base class for font adapters using Oneiric patterns."""

    # Oneiric-compatible metadata
    MODULE_ID: UUID = UUID("01937d86-4f2a-7b3c-8d9e-f3b4d3c2b1a4")  # Static UUID7
    MODULE_STATUS = "stable"

    def __init__(self) -> None:
        """Initialize font adapter."""
        # Register with Oneiric resolver (fail gracefully if not supported)
        with suppress(Exception):
            depends.set(self)

    async def get_font_import(self) -> str:
        """Generate font import statements."""
        raise NotImplementedError()

    def get_font_family(self, font_type: str) -> str:
        """Get font family CSS values."""
        raise NotImplementedError()
