"""Async versions of Jinja2 custom filters for FastBlocks adapter integration."""

from typing import Any

from acb.depends import depends


async def async_image_url(image_id: str, **transformations: Any) -> str:
    """Generate image URL with transformations using configured image adapter (async).

    Usage in templates:
        [[ await async_image_url('product.jpg', width=300, height=200, crop='fill') ]]
    """
    images = await depends.get("images")
    if images and hasattr(images, "get_image_url"):
        result = await images.get_image_url(image_id, **transformations)
        return str(result) if result is not None else image_id

    # Fallback to basic URL
    return image_id


async def async_font_import() -> str:
    """Generate font import statements using configured font adapter (async).

    Usage in templates:
        [% block head %]
            [[ await async_font_import() ]]
        [% endblock %]
    """
    fonts = await depends.get("fonts")
    if fonts and hasattr(fonts, "get_font_import"):
        result = await fonts.get_font_import()
        return str(result) if result is not None else ""

    # Fallback - no custom fonts
    return ""


async def async_image_with_transformations(
    image_id: str,
    alt: str,
    transformations: dict[str, Any] | None = None,
    **attributes: Any,
) -> str:
    """Generate image tag with on-demand transformations (async).

    Usage in templates:
        [[ await async_image_with_transformations('hero.jpg', 'Hero Image',
                                                  {'width': 1200, 'quality': 80},
                                                  class='hero-img') ]]
    """
    images = await depends.get("images")
    if images:
        # Get transformed URL first
        transform_params = transformations or {}
        image_url = await images.get_image_url(image_id, **transform_params)

        # Build img tag with transformed URL
        attr_parts = [f'src="{image_url}"', f'alt="{alt}"']
        for key, value in attributes.items():
            if key in (
                "width",
                "height",
                "class",
                "id",
                "style",
                "loading",
                "decoding",
            ):
                attr_parts.append(f'{key}="{value}"')

        return f"<img {' '.join(attr_parts)}>"

    # Fallback to basic img tag
    attr_parts = [f'src="{image_id}"', f'alt="{alt}"']
    for key, value in attributes.items():
        if key in ("width", "height", "class", "id", "style", "loading", "decoding"):
            attr_parts.append(f'{key}="{value}"')

    return f"<img {' '.join(attr_parts)}>"


async def async_responsive_image(
    image_id: str, alt: str, sizes: dict[str, dict[str, Any]], **attributes: Any
) -> str:
    """Generate responsive image with multiple sizes using image adapter (async).

    Usage in templates:
        [[ await async_responsive_image('article.jpg', 'Article Image', {
            'mobile': {'width': 400, 'quality': 75},
            'tablet': {'width': 800, 'quality': 80},
            'desktop': {'width': 1200, 'quality': 85}
        }) ]]
    """
    images = await depends.get("images")
    if not images:
        # Fallback to basic img tag
        return f'<img src="{image_id}" alt="{alt}">'

    # Generate srcset with different sizes
    srcset_parts = []
    src_url = image_id  # Default fallback

    for size_params in sizes.values():
        width = size_params.get("width", 400)
        size_url = await images.get_image_url(image_id, **size_params)
        srcset_parts.append(f"{size_url} {width}w")

        # Use the largest size as default src
        if width > int(src_url.split("w")[0] if "w" in src_url else "0"):
            src_url = size_url

    # Build img tag with srcset
    attr_parts = [
        f'src="{src_url}"',
        f'alt="{alt}"',
        f'srcset="{", ".join(srcset_parts)}"',
    ]

    # Add sizes attribute if not provided
    if "sizes" not in attributes:
        # Default responsive sizes
        attr_parts.append(
            'sizes="(max-width: 480px) 400px, (max-width: 768px) 800px, 1200px"'
        )

    for key, value in attributes.items():
        if key in (
            "width",
            "height",
            "class",
            "id",
            "style",
            "loading",
            "decoding",
            "sizes",
        ):
            attr_parts.append(f'{key}="{value}"')

    return f"<img {' '.join(attr_parts)}>"


async def async_optimized_font_stack() -> str:
    """Generate optimized font stack with preload and fallback support (async).

    Usage in templates:
        [% block head %]
            [[ await async_optimized_font_stack() ]]
        [% endblock %]
    """
    fonts = await depends.get("fonts")
    if not fonts:
        return ""

    font_html_parts = []

    # Get font imports
    if hasattr(fonts, "get_font_import"):
        font_imports = await fonts.get_font_import()
        if font_imports:
            font_html_parts.append(font_imports)

    # Get preload links for critical fonts
    if hasattr(fonts, "get_preload_links"):
        preload_links = fonts.get_preload_links()
        if preload_links:
            font_html_parts.append(preload_links)

    # Get CSS variables if available
    if hasattr(fonts, "get_css_variables"):
        css_vars = fonts.get_css_variables()
        if css_vars:
            font_html_parts.append(f"<style>\n{css_vars}\n</style>")

    return "\n".join(font_html_parts)


async def async_critical_css_fonts(critical_fonts: list[str] | None = None) -> str:
    """Generate critical font CSS for above-the-fold content (async).

    Usage in templates:
        [% block head %]
            [[ await async_critical_css_fonts(['Inter', 'Roboto']) ]]
        [% endblock %]
    """
    fonts = await depends.get("fonts")
    if not fonts:
        return ""

    # If the adapter supports optimized imports with critical font prioritization
    if hasattr(fonts, "get_optimized_import"):
        result = await fonts.get_optimized_import(critical_fonts)
        return str(result) if result is not None else ""

    # Fallback to regular import
    if hasattr(fonts, "get_font_import"):
        result = await fonts.get_font_import()
        return str(result) if result is not None else ""

    return ""


async def async_image_placeholder(
    width: int,
    height: int,
    text: str = "",
    bg_color: str = "#f0f0f0",
    text_color: str = "#666666",
) -> str:
    """Generate placeholder image URL for loading states (async).

    Usage in templates:
        [[ await async_image_placeholder(400, 300, 'Loading...') ]]
    """
    images = await depends.get("images")

    # If the image adapter supports placeholder generation
    if images and hasattr(images, "get_placeholder_url"):
        result = await images.get_placeholder_url(
            width=width,
            height=height,
            text=text,
            bg_color=bg_color,
            text_color=text_color,
        )
        return (
            str(result)
            if result is not None
            else f"https://via.placeholder.com/{width}x{height}"
        )

    # Fallback to data URL or placeholder service
    if text:
        placeholder_text = text.replace(" ", "%20")
        return f"https://via.placeholder.com/{width}x{height}/{bg_color.lstrip('#')}/{text_color.lstrip('#')}?text={placeholder_text}"

    return f"https://via.placeholder.com/{width}x{height}/{bg_color.lstrip('#')}"


async def async_lazy_image(
    image_id: str, alt: str, placeholder_url: str | None = None, **attributes: Any
) -> str:
    """Generate lazy-loading image with proper placeholder (async).

    Usage in templates:
        [[ await async_lazy_image('hero.jpg', 'Hero Image', loading='lazy') ]]
    """
    images = await depends.get("images")

    # Get the actual image URL
    if images and hasattr(images, "get_image_url"):
        result = await images.get_image_url(image_id, **attributes)
        actual_url = str(result) if result is not None else image_id
    else:
        actual_url = image_id

    # Generate placeholder if not provided
    if not placeholder_url:
        placeholder_url = await async_image_placeholder(
            width=attributes.get("width", 400),
            height=attributes.get("height", 300),
            text="Loading...",
        )

    # Build lazy-loading img tag
    attr_parts = [
        f'src="{placeholder_url}"',
        f'data-src="{actual_url}"',
        f'alt="{alt}"',
        'loading="lazy"',
    ]

    for key, value in attributes.items():
        if key not in ("width", "height") and key in (
            "class",
            "id",
            "style",
            "decoding",
        ):
            attr_parts.append(f'{key}="{value}"')
        elif key in ("width", "height"):
            attr_parts.append(f'{key}="{value}"')

    return f"<img {' '.join(attr_parts)}>"


# Async filter registration mapping
FASTBLOCKS_ASYNC_FILTERS = {
    "async_image_url": async_image_url,
    "async_font_import": async_font_import,
    "async_image_with_transformations": async_image_with_transformations,
    "async_responsive_image": async_responsive_image,
    "async_optimized_font_stack": async_optimized_font_stack,
    "async_critical_css_fonts": async_critical_css_fonts,
    "async_image_placeholder": async_image_placeholder,
    "async_lazy_image": async_lazy_image,
}
