"""TwicPics adapter for FastBlocks with real-time image optimization."""

import asyncio
from contextlib import suppress
from typing import Any
from urllib.parse import quote
from uuid import UUID

import httpx
from acb.depends import depends
from pydantic import SecretStr

from ._base import ImagesBase, ImagesBaseSettings


class TwicPicsImagesSettings(ImagesBaseSettings):
    """Settings for TwicPics adapter."""

    # Required ACB 0.19.0+ metadata
    MODULE_ID: UUID = UUID("01937d86-6f4c-8e5d-9a7b-c6d7e8f9a0b1")  # Static UUID7
    MODULE_STATUS: str = "stable"

    # TwicPics configuration
    domain: str = ""  # Your TwicPics domain (e.g., "demo.twic.pics")
    path_prefix: str = ""  # Optional path prefix
    api_key: SecretStr = SecretStr("")  # For upload operations

    # Image optimization defaults
    default_quality: int = 85
    default_format: str = "auto"  # auto, webp, avif, jpeg, png
    enable_placeholder: bool = True
    placeholder_quality: int = 10

    # Performance settings
    enable_lazy_loading: bool = True
    enable_progressive: bool = True
    timeout: int = 30


class TwicPicsImages(ImagesBase):
    """TwicPics adapter with real-time image optimization."""

    # Required ACB 0.19.0+ metadata
    MODULE_ID: UUID = UUID("01937d86-6f4c-8e5d-9a7b-c6d7e8f9a0b1")  # Static UUID7
    MODULE_STATUS: str = "stable"

    def __init__(self) -> None:
        """Initialize TwicPics adapter."""
        super().__init__()
        self.settings: TwicPicsImagesSettings | None = None
        self._client: httpx.AsyncClient | None = None

        # Register with ACB dependency system
        with suppress(Exception):
            depends.set(self)

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if not self._client:
            if not self.settings:
                self.settings = TwicPicsImagesSettings()

            headers = {}
            if self.settings.api_key.get_secret_value():
                headers["Authorization"] = (
                    f"Bearer {self.settings.api_key.get_secret_value()}"
                )

            self._client = httpx.AsyncClient(
                timeout=self.settings.timeout, headers=headers
            )
        return self._client

    async def upload_image(self, file_data: bytes, filename: str) -> str:
        """Upload image to TwicPics (or return reference path)."""
        # Note: TwicPics typically works with existing images via URL references
        # For upload scenarios, you'd typically upload to your own storage
        # and then reference through TwicPics. This is a simplified implementation.

        if not self.settings:
            self.settings = TwicPicsImagesSettings()

        # For demo purposes, we'll create a reference based on filename
        # In real implementation, you'd upload to your storage backend
        # and return the path that TwicPics can access

        # Clean filename for URL
        clean_filename = quote(filename, safe=".-_")

        # Return the path that will be used with TwicPics
        if self.settings.path_prefix:
            return f"{self.settings.path_prefix}/{clean_filename}"
        return clean_filename

    def _build_transform_parts(self, transformations: dict[str, Any]) -> list[str]:
        """Build transformation parameter list for TwicPics."""
        transform_parts = []

        # Resize transformations
        if "width" in transformations:
            transform_parts.append(f"width={transformations['width']}")
        if "height" in transformations:
            transform_parts.append(f"height={transformations['height']}")

        # Fit modes
        if "fit" in transformations:
            fit_mode = transformations["fit"]
            resize_map = {"crop": "fill", "contain": "contain", "cover": "cover"}
            resize_value = resize_map.get(fit_mode, fit_mode)
            transform_parts.append(f"resize={resize_value}")

        # Quality and format
        transform_parts.append(
            f"quality={transformations.get('quality', self.settings.default_quality if self.settings else 80)}"
        )
        output_format = transformations.get(
            "format", self.settings.default_format if self.settings else "auto"
        )
        if output_format != "auto":
            transform_parts.append(f"output={output_format}")

        # Advanced effects
        for effect in ("blur", "brightness", "contrast", "saturation", "rotate"):
            if effect in transformations:
                transform_parts.append(f"{effect}={transformations[effect]}")

        # Focus point
        if "focus" in transformations:
            focus = transformations["focus"]
            if isinstance(focus, dict) and "x" in focus and "y" in focus:
                transform_parts.append(f"focus={focus['x']}x{focus['y']}")
            elif isinstance(focus, str):
                transform_parts.append(f"focus={focus}")

        # Progressive JPEG
        if (
            self.settings
            and self.settings.enable_progressive
            and output_format
            in (
                "jpeg",
                "jpg",
                "auto",
            )
        ):
            transform_parts.append("progressive=true")

        return transform_parts

    async def get_image_url(
        self, image_id: str, transformations: dict[str, Any] | None = None
    ) -> str:
        """Generate TwicPics URL with real-time transformations."""
        if not self.settings:
            self.settings = TwicPicsImagesSettings()

        base_url = f"https://{self.settings.domain}/{image_id}"

        # Apply transformations if provided
        if transformations:
            transform_parts = self._build_transform_parts(transformations)
            if transform_parts:
                transform_string = "/".join(transform_parts)
                return f"{base_url}?twic=v1/{transform_string}"

        # Default optimizations
        default_transforms = [
            f"quality={self.settings.default_quality}",
            f"output={self.settings.default_format}",
        ]
        if self.settings.enable_progressive:
            default_transforms.append("progressive=true")

        return f"{base_url}?twic=v1/{'/'.join(default_transforms)}"

    def get_img_tag(self, image_id: str, alt: str, **attributes: Any) -> str:
        """Generate img tag with TwicPics patterns and optimization."""
        transformations = attributes.pop("transformations", {})

        # Generate optimized URL
        try:
            loop = asyncio.get_event_loop()
            url = loop.run_until_complete(self.get_image_url(image_id, transformations))
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            url = loop.run_until_complete(self.get_image_url(image_id, transformations))

        # Build base attributes
        img_attrs = {"src": url, "alt": alt} | attributes

        # Add TwicPics-specific optimizations
        if self.settings and self.settings.enable_lazy_loading:
            img_attrs["loading"] = "lazy"

        # Add placeholder for better UX
        if self.settings and self.settings.enable_placeholder:
            placeholder_transforms = {
                **transformations,
                "quality": self.settings.placeholder_quality,
                "width": 20,  # Very small placeholder
            }
            with suppress(Exception):  # Fallback to regular loading
                placeholder_url = loop.run_until_complete(
                    self.get_image_url(image_id, placeholder_transforms)
                )
                # For TwicPics, you might use data-src for lazy loading
                img_attrs["data-src"] = img_attrs["src"]
                img_attrs["src"] = placeholder_url
                img_attrs["class"] = (
                    f"{img_attrs.get('class', '')} twicpics-lazy".strip()
                )

        # Generate tag
        attr_string = " ".join(
            f'{k}="{v}"' for k, v in img_attrs.items() if v is not None
        )
        return f"<img {attr_string}>"

    def get_responsive_img_tag(
        self,
        image_id: str,
        alt: str,
        breakpoints: dict[str, dict[str, Any]] | None = None,
        **attributes: Any,
    ) -> str:
        """Generate responsive img tag with TwicPics breakpoint optimization."""
        if not breakpoints:
            # Default responsive breakpoints
            breakpoints = {
                "320w": {"width": 320},
                "640w": {"width": 640},
                "768w": {"width": 768},
                "1024w": {"width": 1024},
                "1280w": {"width": 1280},
                "1536w": {"width": 1536},
            }

        base_transformations = attributes.pop("transformations", {})

        # Generate srcset
        srcset_parts = []
        for descriptor, transforms in breakpoints.items():
            combined_transforms = base_transformations | transforms
            try:
                loop = asyncio.get_event_loop()
                url = loop.run_until_complete(
                    self.get_image_url(image_id, combined_transforms)
                )
                srcset_parts.append(f"{url} {descriptor}")
            except Exception:
                continue

        # Default src (largest size)
        default_transforms = {**base_transformations, "width": 1024}
        try:
            loop = asyncio.get_event_loop()
            default_src = loop.run_until_complete(
                self.get_image_url(image_id, default_transforms)
            )
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            default_src = loop.run_until_complete(
                self.get_image_url(image_id, default_transforms)
            )

        # Build responsive img tag
        img_attrs = {
            "src": default_src,
            "srcset": ", ".join(srcset_parts),
            "alt": alt,
            "sizes": attributes.pop("sizes", "(max-width: 768px) 100vw, 50vw"),
        } | attributes

        if self.settings and self.settings.enable_lazy_loading:
            img_attrs["loading"] = "lazy"

        attr_string = " ".join(
            f'{k}="{v}"' for k, v in img_attrs.items() if v is not None
        )
        return f"<img {attr_string}>"

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None


# Template filter registration for FastBlocks
def register_twicpics_filters(env: Any) -> None:
    """Register TwicPics filters for Jinja2 templates."""

    @env.filter("twic_url")  # type: ignore[misc]
    async def twic_url_filter(image_id: str, **transformations: Any) -> str:
        """Template filter for TwicPics URLs."""
        images = await depends.get("images")
        if isinstance(images, TwicPicsImages):
            return await images.get_image_url(image_id, transformations)
        return f"#{image_id}"

    @env.filter("twic_img")  # type: ignore[misc]
    def twic_img_filter(image_id: str, alt: str = "", **attributes: Any) -> str:
        """Template filter for TwicPics img tags."""
        images = depends.get_sync("images")
        if isinstance(images, TwicPicsImages):
            return images.get_img_tag(image_id, alt, **attributes)
        return f'<img src="#{image_id}" alt="{alt}">'

    @env.global_("twicpics_responsive")  # type: ignore[misc]
    def twicpics_responsive(
        image_id: str,
        alt: str,
        breakpoints: dict[str, dict[str, Any]] | None = None,
        **attributes: Any,
    ) -> str:
        """Generate responsive image with TwicPics optimization."""
        images = depends.get_sync("images")
        if isinstance(images, TwicPicsImages):
            return images.get_responsive_img_tag(
                image_id, alt, breakpoints, **attributes
            )
        return f'<img src="#{image_id}" alt="{alt}">'

    @env.filter("twic_placeholder")  # type: ignore[misc]
    async def twic_placeholder_filter(
        image_id: str, width: int = 20, quality: int = 10
    ) -> str:
        """Generate ultra-low quality placeholder URL."""
        images = await depends.get("images")
        if isinstance(images, TwicPicsImages):
            return await images.get_image_url(
                image_id, {"width": width, "quality": quality}
            )
        return f"#{image_id}"


ImagesSettings = TwicPicsImagesSettings
Images = TwicPicsImages

depends.set(Images, "twicpics")

# ACB 0.19.0+ compatibility
__all__ = [
    "TwicPicsImages",
    "TwicPicsImagesSettings",
    "register_twicpics_filters",
    "Images",
    "ImagesSettings",
]
