"""Base classes and protocols for style adapters."""

from contextlib import suppress
from typing import Protocol
from uuid import UUID

# Oneiric imports
from oneiric.core.config import OneiricSettings
from oneiric.core.resolution import Resolver

# Oneiric resolver for dependency injection
depends = Resolver()


class StyleBaseSettings(OneiricSettings):
    """Base settings for style adapters using OneiricSettings."""

    cdn_url: str | None = None
    version: str = "latest"
    additional_stylesheets: list[str] = []

    def __init__(self, **data: dict) -> None:
        super().__init__(**data)


class StyleProtocol(Protocol):
    """Protocol for style adapter implementations."""

    def get_stylesheet_links(self) -> list[str]: ...
    def get_component_class(self, component: str) -> str: ...


class StyleBase:
    """Base class for style adapters using Oneiric patterns."""

    # Oneiric-compatible metadata
    MODULE_ID: UUID = UUID("01937d86-4f2a-7b3c-8d9e-f3b4d3c2b1a2")  # Static UUID7
    MODULE_STATUS = "stable"

    def __init__(self) -> None:
        """Initialize style adapter."""
        # Register with Oneiric resolver (fail gracefully if not supported)
        with suppress(Exception):
            depends.set(self)

    def get_stylesheet_links(self) -> list[str]:
        """Generate stylesheet link tags."""
        raise NotImplementedError()

    def get_component_class(self, component: str) -> str:
        """Get style-specific class names for components."""
        raise NotImplementedError()
