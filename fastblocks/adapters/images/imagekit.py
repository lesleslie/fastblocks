"""ImageKit image adapter implementation."""

from contextlib import suppress
from typing import Any
from uuid import UUID

from acb.depends import depends

from ._base import ImagesBase, ImagesBaseSettings


class ImageKitImagesSettings(ImagesBaseSettings):
    """ImageKit-specific settings."""

    public_key: str
    private_key: str
    endpoint_url: str
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

        # Register with ACB dependency system
        with suppress(Exception):
            depends.set(self)

    async def upload_image(self, file_data: bytes, filename: str) -> str:
        """Upload image to ImageKit and return file_id."""
        # Basic implementation - would integrate with imagekit library
        # For now, return a mock file_id based on filename
        file_id = filename.rsplit(".", 1)[0]  # Remove extension
        return f"{self.settings.upload_folder}/{file_id}"

    async def get_image_url(
        self, image_id: str, transformations: dict[str, Any] | None = None
    ) -> str:
        """Generate ImageKit URL with optional transformations."""
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


ImagesSettings = ImageKitImagesSettings
Images = ImageKitImages

depends.set(Images, "imagekit")

__all__ = ["ImageKitImages", "ImageKitImagesSettings", "Images", "ImagesSettings"]
