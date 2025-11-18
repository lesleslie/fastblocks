"""Base classes and protocols for image adapters."""

from contextlib import suppress
from typing import Any, Protocol
from uuid import UUID

from acb.config import AdapterBase, Settings
from acb.depends import depends


class ImagesBaseSettings(Settings):
    """Base settings for image adapters."""

    cdn_url: str | None = None
    media_bucket: str = "media"
    default_transformations: dict[str, Any] = {}
    lazy_loading: bool = True


class ImagesProtocol(Protocol):
    """Protocol for image adapter implementations."""

    async def upload_image(self, file_data: bytes, filename: str) -> str: ...
    async def get_image_url(
        self, image_id: str, transformations: dict[str, Any] | None = None
    ) -> str: ...
    def get_img_tag(self, image_id: str, alt: str, **attributes: Any) -> str: ...


class ImagesBase(AdapterBase):
    """Base class for image adapters."""

    # Required ACB 0.19.0+ metadata
    MODULE_ID: UUID = UUID("01937d86-4f2a-7b3c-8d9e-f3b4d3c2b1a1")  # Static UUID7
    MODULE_STATUS = "stable"

    def __init__(self) -> None:
        """Initialize image adapter."""
        # Register with ACB dependency system
        with suppress(Exception):
            depends.set(self)

    async def upload_image(self, file_data: bytes, filename: str) -> str:
        """Upload image and return image ID."""
        raise NotImplementedError()

    async def get_image_url(
        self, image_id: str, transformations: dict[str, Any] | None = None
    ) -> str:
        """Generate image URL with optional transformations."""
        raise NotImplementedError()

    def get_img_tag(self, image_id: str, alt: str, **attributes: Any) -> str:
        """Generate complete img tag with attributes."""
        raise NotImplementedError()
