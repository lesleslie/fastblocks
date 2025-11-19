"""Base classes and protocols for icon adapters."""

from contextlib import suppress
from typing import Any, Protocol
from uuid import UUID

from acb.config import AdapterBase, Settings
from acb.depends import depends


class IconsBaseSettings(Settings):
    """Base settings for icon adapters."""

    cdn_url: str | None = None
    version: str = "latest"
    default_prefix: str = ""
    icon_mapping: dict[str, str] = {}


class IconsProtocol(Protocol):
    """Protocol for icon adapter implementations."""

    def get_icon_class(self, icon_name: str) -> str: ...
    def get_icon_tag(self, icon_name: str, **attributes: Any) -> str: ...


class IconsBase(AdapterBase):
    """Base class for icon adapters."""

    # Required ACB 0.19.0+ metadata
    MODULE_ID: UUID = UUID("01937d86-4f2a-7b3c-8d9e-f3b4d3c2b1a3")  # Static UUID7
    MODULE_STATUS = "stable"

    def __init__(self) -> None:
        """Initialize icon adapter."""
        # Register with ACB dependency system
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
