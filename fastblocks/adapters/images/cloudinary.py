"""Cloudinary image adapter implementation."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from oneiric.core.resolution import Resolver

from ..oneiric_helper import register_candidate
from ._base import ImagesBase, ImagesBaseSettings

# Oneiric resolver for dependency injection
depends = Resolver()


class CloudinaryImagesSettings(ImagesBaseSettings):
    """Cloudinary-specific settings."""

    cloud_name: str = ""
    api_key: str = ""
    api_secret: str = ""
    secure: bool = True
    upload_preset: str | None = None


class CloudinaryImages(ImagesBase):
    """Cloudinary image adapter implementation."""

    # Required ACB 0.19.0+ metadata
    MODULE_ID: UUID = UUID("01937d86-4f2a-7b3c-8d9e-f3b4d3c2b2a1")  # Static UUID7
    MODULE_STATUS = "stable"

    def __init__(self) -> None:
        """Initialize Cloudinary adapter."""
        super().__init__()
        self.settings = CloudinaryImagesSettings()

        # Register with Oneiric resolver
        register_candidate(
            depends,
            domain="fastblocks",
            key="images",
            factory=lambda: self,
            metadata={
                "adapter": "cloudinary",
                "class": "CloudinaryImages",
                "module": "fastblocks.adapters.images.cloudinary",
            },
        )

    async def upload_image(self, file_data: bytes, filename: str) -> dict[str, Any]:  # type: ignore[override]
        """Upload image to Cloudinary and return result dict."""
        try:
            import cloudinary.api
            import cloudinary.uploader  # type: ignore[no-redef]

            # Configure cloudinary if credentials are set
            if (
                self.settings.cloud_name
                and self.settings.api_key
                and self.settings.api_secret
            ):
                import cloudinary.config  # type: ignore[no-redef]

                cloudinary.config(
                    cloud_name=self.settings.cloud_name,
                    api_key=self.settings.api_key,
                    api_secret=self.settings.api_secret,
                )

            # Upload using cloudinary library
            result = cloudinary.uploader.upload(
                file_data,
                resource_type="image",
                public_id=filename.rsplit(".", 1)[0],
            )
            return result  # type: ignore
        except ImportError:
            # Mock implementation if cloudinary is not available
            public_id = filename.rsplit(".", 1)[0]
            return {
                "public_id": f"uploads/{public_id}",
                "secure_url": f"https://res.cloudinary.com/{self.settings.cloud_name}/image/upload/uploads/{public_id}.jpg"
                if self.settings.cloud_name
                else "",
            }

    async def get_image_url(
        self,
        image_id: str,
        transformations: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> str:
        """Generate Cloudinary URL with optional transformations.

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
        """Helper method to build Cloudinary URL."""
        # Fallback: return image_id if cloud_name is not configured
        if not self.settings.cloud_name:
            return image_id

        base_url = f"https://res.cloudinary.com/{self.settings.cloud_name}/image/upload"

        if transformations:
            # Build transformation string
            transform_parts = []
            for key, value in transformations.items():
                if key == "width":
                    transform_parts.append(f"w_{value}")
                elif key == "height":
                    transform_parts.append(f"h_{value}")
                elif key == "crop":
                    transform_parts.append(f"c_{value}")
                elif key == "quality":
                    transform_parts.append(f"q_{value}")
                elif key == "format":
                    transform_parts.append(f"f_{value}")

            if transform_parts:
                transform_str = ",".join(transform_parts)
                return f"{base_url}/{transform_str}/{image_id}"

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


ImagesSettings = CloudinaryImagesSettings
Images = CloudinaryImages

# Register with Oneiric resolver
register_candidate(
    depends,
    domain="fastblocks",
    key="images",
    factory=Images,
    metadata={
        "adapter": "cloudinary",
        "class": "Images",
        "module": "fastblocks.adapters.images.cloudinary",
    },
)

__all__ = ["CloudinaryImages", "CloudinaryImagesSettings", "Images", "ImagesSettings"]
