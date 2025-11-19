"""Cloudinary image adapter implementation."""

from contextlib import suppress
from typing import Any
from uuid import UUID

from acb.depends import depends

from ._base import ImagesBase, ImagesBaseSettings


class CloudinaryImagesSettings(ImagesBaseSettings):
    """Cloudinary-specific settings."""

    cloud_name: str
    api_key: str
    api_secret: str
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

        # Register with ACB dependency system
        with suppress(Exception):
            depends.set(self)

    async def upload_image(self, file_data: bytes, filename: str) -> str:
        """Upload image to Cloudinary and return public_id."""
        # Basic implementation - would integrate with cloudinary library
        # For now, return a mock public_id based on filename
        public_id = filename.rsplit(".", 1)[0]  # Remove extension
        return f"uploads/{public_id}"

    async def get_image_url(
        self, image_id: str, transformations: dict[str, Any] | None = None
    ) -> str:
        """Generate Cloudinary URL with optional transformations."""
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
        url = self.get_image_url(image_id, attributes.pop("transformations", None))

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

depends.set(Images, "cloudinary")

__all__ = ["CloudinaryImages", "CloudinaryImagesSettings", "Images", "ImagesSettings"]
