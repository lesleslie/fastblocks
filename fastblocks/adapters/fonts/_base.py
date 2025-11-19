"""Base classes and protocols for font adapters."""

from contextlib import suppress
from typing import Protocol
from uuid import UUID

from acb.config import AdapterBase, Settings
from acb.depends import depends


class FontsBaseSettings(Settings):
    """Base settings for font adapters."""

    primary_font: str = "Arial, sans-serif"
    secondary_font: str = "Georgia, serif"
    cdn_url: str | None = None
    font_weights: list[str] = ["400", "700"]


class FontsProtocol(Protocol):
    """Protocol for font adapter implementations."""

    async def get_font_import(self) -> str: ...
    def get_font_family(self, font_type: str) -> str: ...


class FontsBase(AdapterBase):
    """Base class for font adapters."""

    # Required ACB 0.19.0+ metadata
    MODULE_ID: UUID = UUID("01937d86-4f2a-7b3c-8d9e-f3b4d3c2b1a4")  # Static UUID7
    MODULE_STATUS = "stable"

    def __init__(self) -> None:
        """Initialize font adapter."""
        # Register with ACB dependency system
        with suppress(Exception):
            depends.set(self)

    async def get_font_import(self) -> str:
        """Generate font import statements."""
        raise NotImplementedError()

    def get_font_family(self, font_type: str) -> str:
        """Get font family CSS values."""
        raise NotImplementedError()
