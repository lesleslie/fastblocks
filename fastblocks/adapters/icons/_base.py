"""Base classes and protocols for icon adapters."""

from contextlib import suppress
from typing import Any, Protocol
from uuid import UUID

# Oneiric imports
from oneiric.core.config import OneiricSettings
from oneiric.core.resolution import Resolver

# Oneiric resolver for dependency injection
depends = Resolver()


class IconsBaseSettings(OneiricSettings):  # type: ignore[misc]
    """Base settings for icon adapters using OneiricSettings."""

    cdn_url: str | None = None
    version: str = "latest"
    default_prefix: str = ""
    icon_mapping: dict[str, str] = {}

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)


class IconsProtocol(Protocol):
    """Protocol for icon adapter implementations."""

    def get_icon_class(self, icon_name: str) -> str: ...
    def get_icon_tag(self, icon_name: str, **attributes: Any) -> str: ...


class IconsBase:
    """Base class for icon adapters using Oneiric patterns."""

    # Oneiric-compatible metadata
    MODULE_ID: UUID = UUID("01937d86-4f2a-7b3c-8d9e-f3b4d3c2b1a3")  # Static UUID7
    MODULE_STATUS = "stable"

    def __init__(self) -> None:
        """Initialize icon adapter."""
        # Register with Oneiric resolver (fail gracefully if not supported)
        with suppress(Exception):
            depends.set(self)

    def get_icon_class(self, icon_name: str) -> str:
        """Get icon-specific class names."""
        raise NotImplementedError()

    def get_icon_tag(self, icon_name: str, **attributes: Any) -> str:
        """Generate complete icon tags with attributes."""
        raise NotImplementedError()

    def get_stylesheet_links(self) -> list[str]:
        """Get stylesheet link tags for the icon library."""
        raise NotImplementedError()
