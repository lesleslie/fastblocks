"""ImageKit image adapter implementation."""

from contextlib import suppress
from typing import Any
from uuid import UUID

from oneiric.core.resolution import Resolver

from ..oneiric_helper import register_candidate
from ._base import ImagesBase, ImagesBaseSettings

# Oneiric resolver for dependency injection
depends = Resolver()


class ImageKitImagesSettings(ImagesBaseSettings):
    """ImageKit-specific settings."""

    public_key: str = ""
    private_key: str = ""
    endpoint_url: str = ""
    upload_folder: str = "fastblocks"


class ImageKitImages(ImagesBase):
    """ImageKit image adapter implementation."""

    # Required ACB 0.19.0+ metadata
    MODULE_ID: UUID = UUID("01937d86-4f2a-7b3c-8d9e-f3b4d3c2b2a2")  # Static UUID7
    MODULE_STATUS = "stable"

    def __init__(self) -> None:
        """Initialize ImageKit adapter."""
        super().__init__()
        self.settings = ImageKitImagesSettings()

        # Register with Oneiric resolver
        register_candidate(
            depends,
            domain="fastblocks",
            key="images",
            factory=lambda: self,
            metadata={
                "adapter": "imagekit",
                "class": "ImageKitImages",
                "module": "fastblocks.adapters.images.imagekit",
            },
        )

    async def upload_image(self, file_data: bytes, filename: str) -> dict[str, Any]:
        """Upload image to ImageKit and return result dict."""
        try:
            import imagekit

            # Upload using imagekit library
            result = imagekit.upload_file(
                file=file_data,
                file_name=filename,
                folder=self.settings.upload_folder,
            )
            return result
        except ImportError:
            # Mock implementation if imagekit is not available
            file_id = filename.rsplit(".", 1)[0]
            return {
                "file_id": f"{self.settings.upload_folder}/{file_id}",
                "url": f"{self.settings.endpoint_url}/{self.settings.upload_folder}/{file_id}.jpg"
                if self.settings.endpoint_url
                else "",
            }

    async def get_image_url(
        self,
        image_id: str,
        transformations: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> str:
        """Generate ImageKit URL with optional transformations.

        Can accept either a transformations dict or keyword arguments.
        """
        # Combine transformations dict with kwargs (kwargs take precedence)
        if transformations is None:
            transformations = {}
        transformations = {**transformations, **kwargs}
        return self._build_image_url(image_id, transformations)

    def get_sync_image_url(
        self,
        image_id: str,
        transformations: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> str:
        """Synchronous version of get_image_url for template filters.

        Can accept either a transformations dict or keyword arguments.
        """
        # Combine transformations dict with kwargs (kwargs take precedence)
        if transformations is None:
            transformations = {}
        transformations = {**transformations, **kwargs}
        return self._build_image_url(image_id, transformations)

    def _build_image_url(self, image_id: str, transformations: dict[str, Any]) -> str:
        """Helper method to build ImageKit URL."""
        base_url = self.settings.endpoint_url.rstrip("/")

        if transformations:
            # Build transformation string (ImageKit format)
            transform_parts = []
            for key, value in transformations.items():
                if key == "width":
                    transform_parts.append(f"w-{value}")
                elif key == "height":
                    transform_parts.append(f"h-{value}")
                elif key == "crop":
                    transform_parts.append(f"c-{value}")
                elif key == "quality":
                    transform_parts.append(f"q-{value}")
                elif key == "format":
                    transform_parts.append(f"f-{value}")

            if transform_parts:
                transform_str = ",".join(transform_parts)
                return f"{base_url}/tr:{transform_str}/{image_id}"

        return f"{base_url}/{image_id}"

    def get_img_tag(self, image_id: str, alt: str, **attributes: Any) -> str:
        # Convert class_ to class (Python keyword handling)
        if "class_" in attributes:
            attributes["class"] = attributes.pop("class_")

        url = self.get_sync_image_url(image_id, attributes.pop("transformations", None))

        # Build attributes string
        attr_parts = [f'src="{url}"', f'alt="{alt}"']

        for key, value in attributes.items():
            if key in ("width", "height", "class", "id", "style"):
                attr_parts.append(f'{key}="{value}"')

        # Add lazy loading by default
        if "loading" not in attributes:
            attr_parts.append('loading="lazy"')

        return f"<img {' '.join(attr_parts)}>"


ImagesSettings = ImageKitImagesSettings
Images = ImageKitImages

# Register with Oneiric resolver
register_candidate(
    depends,
    domain="fastblocks",
    key="images",
    factory=Images,
    metadata={
        "adapter": "imagekit",
        "class": "Images",
        "module": "fastblocks.adapters.images.imagekit",
    },
)

__all__ = ["ImageKitImages", "ImageKitImagesSettings", "Images", "ImagesSettings"]
