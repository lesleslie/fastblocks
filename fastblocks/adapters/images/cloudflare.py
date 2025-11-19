"""Cloudflare Images adapter for FastBlocks."""

import asyncio
from contextlib import suppress
from typing import Any
from uuid import UUID, uuid4

import httpx
from acb.depends import depends
from pydantic import SecretStr

from ._base import ImagesBase, ImagesBaseSettings


class CloudflareImagesSettings(ImagesBaseSettings):
    """Settings for Cloudflare Images adapter."""

    # Required ACB 0.19.0+ metadata
    MODULE_ID: UUID = UUID("01937d86-5e3b-7f4c-9e8e-a5b6c7d8e9f0")  # Static UUID7
    MODULE_STATUS: str = "stable"

    # Cloudflare API configuration
    account_id: str = ""
    api_token: SecretStr = SecretStr("")
    delivery_url: str = ""  # https://imagedelivery.net/{account_hash}

    # Image configuration
    default_variant: str = "public"
    require_signed_urls: bool = False
    timeout: int = 30

    # R2 storage configuration (optional)
    r2_bucket: str | None = None
    r2_public_url: str | None = None


class CloudflareImages(ImagesBase):
    """Cloudflare Images adapter with R2 storage integration."""

    # Required ACB 0.19.0+ metadata
    MODULE_ID: UUID = UUID("01937d86-5e3b-7f4c-9e8e-a5b6c7d8e9f0")  # Static UUID7
    MODULE_STATUS: str = "stable"

    def __init__(self) -> None:
        """Initialize Cloudflare Images adapter."""
        super().__init__()
        self.settings: CloudflareImagesSettings | None = None
        self._client: httpx.AsyncClient | None = None

        # Register with ACB dependency system
        with suppress(Exception):
            depends.set(self)

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if not self._client:
            if not self.settings:
                self.settings = CloudflareImagesSettings()

            self._client = httpx.AsyncClient(
                timeout=self.settings.timeout,
                headers={
                    "Authorization": f"Bearer {self.settings.api_token.get_secret_value()}",
                    "Content-Type": "application/json",
                },
            )
        return self._client

    async def upload_image(self, file_data: bytes, filename: str) -> str:
        """Upload image to Cloudflare Images."""
        if not self.settings:
            self.settings = CloudflareImagesSettings()

        client = await self._get_client()

        # Generate unique ID for the image
        str(uuid4())

        # Prepare upload data

        # Upload to Cloudflare Images
        url = f"https://api.cloudflare.com/client/v4/accounts/{self.settings.account_id}/images/v1"

        # Format files for httpx - each value is a tuple of (filename, file_content, content_type)
        files_data: dict[str, tuple[str, bytes, str]] = {
            "file": (filename, file_data, "image/*"),
        }

        response = await client.post(url, files=files_data)
        response.raise_for_status()

        result = response.json()
        if not result.get("success"):
            raise RuntimeError(
                f"Upload failed: {result.get('errors', 'Unknown error')}"
            )

        # Return the image ID for future reference
        uploaded_image_id: str = result["result"]["id"]
        return uploaded_image_id

    async def get_image_url(
        self, image_id: str, transformations: dict[str, Any] | None = None
    ) -> str:
        """Generate Cloudflare Images URL with transformations."""
        if not self.settings:
            self.settings = CloudflareImagesSettings()

        base_url = self._build_base_url(image_id)

        if transformations:
            transform_parts = self._build_transformation_parts(transformations)
            if transform_parts:
                return self._build_transformed_url(
                    base_url, transformations, transform_parts
                )

        return f"{base_url}/{self.settings.default_variant}"

    def _build_base_url(self, image_id: str) -> str:
        """Build base URL for Cloudflare image."""
        if not self.settings:
            raise RuntimeError("Cloudflare Images settings not configured")

        if self.settings.delivery_url:
            return f"{self.settings.delivery_url}/{image_id}"
        return f"https://api.cloudflare.com/client/v4/accounts/{self.settings.account_id}/images/v1/{image_id}"

    @staticmethod
    def _build_transformation_parts(transformations: dict[str, Any]) -> list[str]:
        """Build transformation query parameters."""
        # Common transformations
        common_parts = [
            f"{key}={transformations[key]}"
            for key in ("width", "height", "quality", "format", "fit")
            if key in transformations
        ]

        # Advanced transformations
        advanced_parts = [
            f"{key}={transformations[key]}"
            for key in ("blur", "brightness", "contrast", "gamma", "sharpen")
            if key in transformations
        ]

        return common_parts + advanced_parts

    def _build_transformed_url(
        self, base_url: str, transformations: dict[str, Any], transform_parts: list[str]
    ) -> str:
        """Build final URL with transformations."""
        if not self.settings:
            raise RuntimeError("Cloudflare Images settings not configured")

        variant = transformations.get("variant", self.settings.default_variant)
        transform_string = ",".join(transform_parts)
        return f"{base_url}/{variant}?{transform_string}"

    def get_img_tag(self, image_id: str, alt: str, **attributes: Any) -> str:
        """Generate img tag with Cloudflare Images patterns."""
        # Generate base URL
        transformations = attributes.pop("transformations", {})

        # Use async context for URL generation (in real usage)
        try:
            loop = asyncio.get_event_loop()
            url = loop.run_until_complete(self.get_image_url(image_id, transformations))
        except RuntimeError:
            # Create new event loop if none exists
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            url = loop.run_until_complete(self.get_image_url(image_id, transformations))

        # Build attributes
        img_attrs = {
            "src": url,
            "alt": alt,
            "loading": "lazy"
            if self.settings and self.settings.lazy_loading
            else "eager",
        } | attributes

        # Generate tag
        attr_string = " ".join(
            f'{k}="{v}"' for k, v in img_attrs.items() if v is not None
        )
        return f"<img {attr_string}>"

    async def delete_image(self, image_id: str) -> bool:
        """Delete image from Cloudflare Images."""
        if not self.settings:
            self.settings = CloudflareImagesSettings()

        client = await self._get_client()

        url = f"https://api.cloudflare.com/client/v4/accounts/{self.settings.account_id}/images/v1/{image_id}"

        response = await client.delete(url)
        response.raise_for_status()

        result = response.json()
        success: bool = result.get("success", False)
        return success

    async def list_images(self, page: int = 1, per_page: int = 50) -> dict[str, Any]:
        """List images in Cloudflare Images."""
        if not self.settings:
            self.settings = CloudflareImagesSettings()

        client = await self._get_client()

        url = f"https://api.cloudflare.com/client/v4/accounts/{self.settings.account_id}/images/v1"
        params = {"page": page, "per_page": per_page}

        response = await client.get(url, params=params)
        response.raise_for_status()

        result: dict[str, Any] = response.json()
        return result

    async def get_usage_stats(self) -> dict[str, Any]:
        """Get Cloudflare Images usage statistics."""
        if not self.settings:
            self.settings = CloudflareImagesSettings()

        client = await self._get_client()

        url = f"https://api.cloudflare.com/client/v4/accounts/{self.settings.account_id}/images/v1/stats"

        response = await client.get(url)
        response.raise_for_status()

        stats: dict[str, Any] = response.json()
        return stats

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None


# Template filter registration for FastBlocks
def register_cloudflare_filters(env: Any) -> None:
    """Register Cloudflare Images filters for Jinja2 templates."""

    @env.filter("cf_image_url")  # type: ignore[misc]
    async def cf_image_url_filter(image_id: str, **transformations: Any) -> str:
        """Template filter for Cloudflare Images URLs."""
        images = await depends.get("images")
        if isinstance(images, CloudflareImages):
            return await images.get_image_url(image_id, transformations)
        return f"#{image_id}"  # Fallback

    @env.filter("cf_img_tag")  # type: ignore[misc]
    def cf_img_tag_filter(image_id: str, alt: str = "", **attributes: Any) -> str:
        """Template filter for complete Cloudflare img tags."""
        images = depends.get_sync("images")
        if isinstance(images, CloudflareImages):
            return images.get_img_tag(image_id, alt, **attributes)
        return f'<img src="#{image_id}" alt="{alt}">'  # Fallback

    @env.global_("cloudflare_responsive_img")  # type: ignore[misc]
    def cloudflare_responsive_img(
        image_id: str,
        alt: str,
        sizes: str = "(max-width: 768px) 100vw, 50vw",
        **attributes: Any,
    ) -> str:
        """Generate responsive image with multiple sizes."""
        images = depends.get_sync("images")
        if not isinstance(images, CloudflareImages):
            return f'<img src="#{image_id}" alt="{alt}">'

        # Generate srcset for different screen sizes
        srcset_parts = []
        widths = [320, 640, 768, 1024, 1280, 1536]

        for width in widths:
            try:
                loop = asyncio.get_event_loop()
                url = loop.run_until_complete(
                    images.get_image_url(
                        image_id, {"width": width, "fit": "scale-down"}
                    )
                )
                srcset_parts.append(f"{url} {width}w")
            except Exception:
                continue

        # Build img tag with srcset
        base_url = asyncio.get_event_loop().run_until_complete(
            images.get_image_url(image_id, {"width": 1024, "fit": "scale-down"})
        )

        img_attrs = {
            "src": base_url,
            "alt": alt,
            "sizes": sizes,
            "srcset": ", ".join(srcset_parts),
            "loading": "lazy",
        } | attributes

        attr_string = " ".join(
            f'{k}="{v}"' for k, v in img_attrs.items() if v is not None
        )
        return f"<img {attr_string}>"


ImagesSettings = CloudflareImagesSettings
Images = CloudflareImages


# ACB 0.19.0+ compatibility
__all__ = [
    "CloudflareImages",
    "CloudflareImagesSettings",
    "register_cloudflare_filters",
    "Images",
    "ImagesSettings",
]
