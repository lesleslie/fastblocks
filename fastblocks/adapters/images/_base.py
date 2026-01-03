"""Base classes and protocols for image adapters."""

from typing import Any, Protocol
from uuid import UUID

# Oneiric imports
from oneiric.core.config import OneiricSettings
from oneiric.core.resolution import Resolver

from ..oneiric_helper import register_candidate

# Oneiric resolver for dependency injection
depends = Resolver()


class ImagesBaseSettings(OneiricSettings):
    """Base settings for image adapters using OneiricSettings."""

    cdn_url: str | None = None
    media_bucket: str = "media"
    default_transformations: dict[str, Any] = {}
    lazy_loading: bool = True

    def __init__(self, **data: dict[str, Any]) -> None:
        super().__init__(**data)


class ImagesProtocol(Protocol):
    """Protocol for image adapter implementations."""

    async def upload_image(self, file_data: bytes, filename: str) -> str: ...
    async def get_image_url(
        self, image_id: str, transformations: dict[str, Any] | None = None
    ) -> str: ...
    def get_img_tag(self, image_id: str, alt: str, **attributes: Any) -> str: ...


class ImagesBase:
    """Base class for image adapters using Oneiric patterns."""

    # Oneiric-compatible metadata
    MODULE_ID: UUID = UUID("01937d86-4f2a-7b3c-8d9e-f3b4d3c2b1a1")  # Static UUID7
    MODULE_STATUS = "stable"

    def __init__(self) -> None:
        """Initialize image adapter."""
        # Register with Oneiric resolver
        register_candidate(
            depends,
            domain="fastblocks",
            key="images",
            factory=lambda: self,
            metadata={
                "class": self.__class__.__name__,
                "module": self.__class__.__module__,
            },
        )

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
