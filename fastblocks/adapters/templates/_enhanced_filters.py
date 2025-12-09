"""Enhanced Template Filters for Secondary Adapters Integration.

This module provides comprehensive template filters for all FastBlocks secondary adapters:
- Cloudflare Images integration with transformations
- TwicPics integration with smart cropping
- WebAwesome icon integration
- Kelp component integration
- Phosphor, Heroicons, Remix, Material Icons support
- Font loading and optimization
- Advanced HTMX integrations

Requirements:
- All secondary adapter packages as available

Author: lesleslie <les@wedgwoodwebworks.com>
Created: 2025-01-12
"""

import typing as t
from contextlib import suppress
from uuid import UUID

from acb.adapters import AdapterStatus
from acb.depends import depends


# Cloudflare Images Filters
def cf_image_url(image_id: str, **transformations: t.Any) -> str:
    """Generate Cloudflare Images URL with transformations.

    Usage in templates:
        [[ cf_image_url('hero.jpg', width=800, quality=85, format='webp') ]]
    """
    with suppress(Exception):  # Fallback
        cloudflare = depends.get_sync("cloudflare_images")
        if cloudflare:
            result = cloudflare.get_image_url(image_id, **transformations)
            return str(result) if result is not None else image_id

    return image_id


def _build_cf_srcset(
    cloudflare: t.Any, image_id: str, sizes: dict[str, dict[str, t.Any]]
) -> tuple[list[str], str]:
    """Build Cloudflare Images srcset and determine default src URL.

    Args:
        cloudflare: Cloudflare adapter instance
        image_id: Image identifier
        sizes: Size configurations

    Returns:
        Tuple of (srcset_parts, default_src_url)
    """
    srcset_parts = []
    src_url = image_id

    for size_params in sizes.values():
        width = size_params.get("width", 400)
        size_url = cloudflare.get_image_url(image_id, **size_params)
        srcset_parts.append(f"{size_url} {width}w")

        # Use largest as default src
        if width > 800:
            src_url = size_url

    return srcset_parts, src_url


def _build_cf_img_attributes(
    src_url: str,
    alt: str,
    srcset_parts: list[str],
    attributes: dict[str, t.Any],
) -> list[str]:
    """Build HTML image attributes for Cloudflare Images.

    Args:
        src_url: Source URL
        alt: Alt text
        srcset_parts: Srcset components
        attributes: Additional HTML attributes

    Returns:
        List of formatted attribute strings
    """
    attr_parts = [
        f'src="{src_url}"',
        f'alt="{alt}"',
        f'srcset="{", ".join(srcset_parts)}"',
    ]

    # Add default sizes if not provided
    if "sizes" not in attributes:
        attr_parts.append(
            'sizes="(max-width: 480px) 400px, (max-width: 768px) 800px, 1200px"'
        )

    for key, value in attributes.items():
        if key in ("width", "height", "class", "id", "style", "loading", "sizes"):
            attr_parts.append(f'{key}="{value}"')

    return attr_parts


def cf_responsive_image(
    image_id: str, alt: str, sizes: dict[str, dict[str, t.Any]], **attributes: t.Any
) -> str:
    """Generate responsive Cloudflare Images with srcset.

    Usage in templates:
        [[ cf_responsive_image('hero.jpg', 'Hero Image', {
            'mobile': {'width': 400, 'quality': 75},
            'tablet': {'width': 800, 'quality': 80},
            'desktop': {'width': 1200, 'quality': 85}
        }) ]]
    """
    try:
        cloudflare = depends.get_sync("cloudflare_images")
        if not cloudflare:
            return f'<img src="{image_id}" alt="{alt}">'

        srcset_parts, src_url = _build_cf_srcset(cloudflare, image_id, sizes)
        attr_parts = _build_cf_img_attributes(src_url, alt, srcset_parts, attributes)

        return f"<img {' '.join(attr_parts)}>"

    except Exception:
        return f'<img src="{image_id}" alt="{alt}">'


# TwicPics Filters
def twicpics_image(image_id: str, **transformations: t.Any) -> str:
    """Generate TwicPics image URL with smart transformations.

    Usage in templates:
        [[ twicpics_image('product.jpg', resize='400x300', focus='auto') ]]
    """
    with suppress(Exception):
        twicpics = depends.get_sync("twicpics")
        if twicpics:
            result = twicpics.get_image_url(image_id, **transformations)
            return str(result) if result is not None else image_id

    return image_id


def _separate_image_attributes(
    transform_params: dict[str, t.Any],
) -> tuple[dict[str, t.Any], dict[str, t.Any]]:
    """Separate image attributes from transformation parameters."""
    img_attrs = {}
    transform_only = {}

    for key, value in transform_params.items():
        if key in ("class", "id", "style", "loading", "alt"):
            img_attrs[key] = value
        else:
            transform_only[key] = value

    return img_attrs, transform_only


def twicpics_smart_crop(
    image_id: str, width: int, height: int, focus: str = "auto", **attributes: t.Any
) -> str:
    """Generate TwicPics image with smart cropping.

    Usage in templates:
        [[ twicpics_smart_crop('landscape.jpg', 400, 300, 'face', class='hero-img') ]]
    """
    with suppress(Exception):
        twicpics = depends.get_sync("twicpics")
        if twicpics:
            transform_params = {
                "resize": f"{width}x{height}",
                "focus": focus,
            } | attributes

            # Extract img attributes from transform params
            img_attrs, transform_only = _separate_image_attributes(transform_params)

            image_url = twicpics.get_image_url(image_id, **transform_only)

            attr_parts = [f'src="{image_url}"']
            if "alt" not in img_attrs:
                attr_parts.append(f'alt="{image_id}"')

            for key, value in img_attrs.items():
                attr_parts.append(f'{key}="{value}"')

            return f"<img {' '.join(attr_parts)}>"

    return f'<img src="{image_id}" alt="{image_id}" width="{width}" height="{height}">'


# WebAwesome Icon Filters
def wa_icon(icon_name: str, **attributes: t.Any) -> str:
    """Generate WebAwesome icon.

    Usage in templates:
        [[ wa_icon('home', size='24', class='nav-icon') ]]
    """
    with suppress(Exception):  # Fallback
        webawesome = depends.get_sync("webawesome")
        if webawesome:
            result = webawesome.get_icon_tag(icon_name, **attributes)
            return str(result) if result is not None else f"[{icon_name}]"

    css_class = attributes.get("class", "")
    size = attributes.get("size", "16")
    return f'<i class="wa wa-{icon_name} {css_class}" style="font-size: {size}px;"></i>'


def wa_icon_with_text(
    icon_name: str, text: str, position: str = "left", **attributes: t.Any
) -> str:
    """Generate WebAwesome icon with text.

    Usage in templates:
        [[ wa_icon_with_text('save', 'Save Changes', 'left', class='btn-icon') ]]
    """
    with suppress(Exception):  # Fallback
        webawesome = depends.get_sync("webawesome")
        if webawesome and hasattr(webawesome, "get_icon_with_text"):
            result = webawesome.get_icon_with_text(
                icon_name, text, position, **attributes
            )
            return (
                str(result)
                if result is not None
                else f"{wa_icon(icon_name, **attributes)} {text}"
            )

    icon = wa_icon(icon_name, **attributes)
    if position == "right":
        return f"{text} {icon}"

    return f"{icon} {text}"


# Kelp Component Filters
def kelp_component(component_type: str, content: str = "", **attributes: t.Any) -> str:
    """Generate Kelp component.

    Usage in templates:
        [[ kelp_component('button', 'Click Me', variant='primary', size='large') ]]
    """
    with suppress(Exception):  # Fallback
        kelp = depends.get_sync("kelp")
        if kelp:
            result = kelp.build_component(component_type, content, **attributes)
            return (
                str(result)
                if result is not None
                else f'<div class="kelp-{component_type}">{content}</div>'
            )

    css_class = f"kelp-{component_type}"
    variant = attributes.get("variant", "")
    size = attributes.get("size", "")

    if variant:
        css_class += f" kelp-{component_type}--{variant}"
    if size:
        css_class += f" kelp-{component_type}--{size}"

    if "class" in attributes:
        css_class += f" {attributes['class']}"

    if component_type == "button":
        return f'<button class="{css_class}">{content}</button>'

    return f'<div class="{css_class}">{content}</div>'


def kelp_card(title: str = "", content: str = "", **attributes: t.Any) -> str:
    """Generate Kelp card component.

    Usage in templates:
        [[ kelp_card('Card Title', '<p>Card content here</p>', variant='elevated') ]]
    """
    with suppress(Exception):
        kelp = depends.get_sync("kelp")
        if kelp and hasattr(kelp, "build_card"):
            result = kelp.build_card(title, content, **attributes)
            return (
                str(result)
                if result is not None
                else _build_fallback_card(title, content, **attributes)
            )

    return _build_fallback_card(title, content, **attributes)


def _build_fallback_card(title: str, content: str, **attributes: t.Any) -> str:
    """Build fallback card HTML."""
    css_class = "kelp-card"
    variant = attributes.get("variant", "")

    if variant:
        css_class += f" kelp-card--{variant}"
    if "class" in attributes:
        css_class += f" {attributes['class']}"

    card_html = [f'<div class="{css_class}">']

    if title:
        card_html.append(
            f'<div class="kelp-card__header"><h3 class="kelp-card__title">{title}</h3></div>'
        )

    if content:
        card_html.extend((f'<div class="kelp-card__content">{content}</div>', "</div>"))

    return "".join(card_html)


# Phosphor Icons Filters
def phosphor_icon(icon_name: str, weight: str = "regular", **attributes: t.Any) -> str:
    """Generate Phosphor icon.

    Usage in templates:
        [[ phosphor_icon('house', 'bold', size='24', class='nav-icon') ]]
    """
    with suppress(Exception):  # Fallback
        phosphor = depends.get_sync("phosphor")
        if phosphor:
            result = phosphor.get_icon_tag(icon_name, weight=weight, **attributes)
            return str(result) if result is not None else f"[{icon_name}]"

    css_class = f"ph ph-{icon_name}"
    if weight != "regular":
        css_class += f" ph-{weight}"

    if "class" in attributes:
        css_class += f" {attributes['class']}"

    size = attributes.get("size", "16")
    return f'<i class="{css_class}" style="font-size: {size}px;"></i>'


# Heroicons Filters
def heroicon(icon_name: str, style: str = "outline", **attributes: t.Any) -> str:
    """Generate Heroicon.

    Usage in templates:
        [[ heroicon('home', 'solid', size='24', class='nav-icon') ]]
    """
    with suppress(Exception):  # Fallback SVG approach
        heroicons = depends.get_sync("heroicons")
        if heroicons:
            result = heroicons.get_icon_tag(icon_name, style=style, **attributes)
            return str(result) if result is not None else f"[{icon_name}]"

    css_class = attributes.get("class", "")
    size = attributes.get("size", "24")

    return f'''<svg class="heroicon heroicon-{icon_name} {css_class}"
                   width="{size}" height="{size}"
                   fill="{style == "solid" and "currentColor" or "none"}"
                   stroke="currentColor" stroke-width="1.5">
                <use href="#heroicon-{icon_name}-{style}"></use>
              </svg>'''


# Remix Icons Filters
def remix_icon(icon_name: str, **attributes: t.Any) -> str:
    """Generate Remix icon.

    Usage in templates:
        [[ remix_icon('home-line', size='24', class='nav-icon') ]]
    """
    with suppress(Exception):  # Fallback
        remix = depends.get_sync("remix_icons")
        if remix:
            result = remix.get_icon_tag(icon_name, **attributes)
            return str(result) if result is not None else f"[{icon_name}]"

    css_class = f"ri-{icon_name}"
    if "class" in attributes:
        css_class += f" {attributes['class']}"

    size = attributes.get("size", "16")
    return f'<i class="{css_class}" style="font-size: {size}px;"></i>'


# Material Icons Filters
def material_icon(icon_name: str, variant: str = "filled", **attributes: t.Any) -> str:
    """Generate Material Design icon.

    Usage in templates:
        [[ material_icon('home', 'outlined', size='24', class='nav-icon') ]]
    """
    with suppress(Exception):  # Fallback
        material = depends.get_sync("material_icons")
        if material:
            result = material.get_icon_tag(icon_name, variant=variant, **attributes)
            return str(result) if result is not None else f"[{icon_name}]"

    css_class = "material-icons"
    if variant != "filled":
        css_class += f"-{variant}"

    if "class" in attributes:
        css_class += f" {attributes['class']}"

    size = attributes.get("size", "24")
    return f'<span class="{css_class}" style="font-size: {size}px;">{icon_name}</span>'


# Advanced Font Filters
async def async_optimized_font_loading(fonts: list[str], critical: bool = True) -> str:
    """Generate optimized font loading with preload hints.

    Usage in templates:
        [[ await async_optimized_font_loading(['Inter', 'Roboto Mono'], critical=True) ]]
    """
    with suppress(Exception):  # Fallback
        font_adapter = await depends.get("fonts")
        if font_adapter and hasattr(font_adapter, "get_optimized_loading"):
            result = await font_adapter.get_optimized_loading(fonts, critical=critical)
            return str(result) if result is not None else ""

    html_parts = []
    for font in fonts:
        font_family = font.replace(" ", "+")
        if critical:
            html_parts.extend(
                (
                    f'<link rel="preload" href="https://fonts.googleapis.com/css2?family={font_family}&display=swap" as="style">',
                    f'<link href="https://fonts.googleapis.com/css2?family={font_family}&display=swap" rel="stylesheet">',
                )
            )

    return "\n".join(html_parts)


def font_face_declaration(
    font_name: str, font_files: dict[str, str], **attributes: t.Any
) -> str:
    """Generate @font-face CSS declaration.

    Usage in templates:
        [[ font_face_declaration('CustomFont', {
            'woff2': '/fonts/custom.woff2',
            'woff': '/fonts/custom.woff'
        }, weight='400', style='normal') ]]
    """
    with suppress(Exception):  # Fallback
        font_adapter = depends.get_sync("fonts")
        if font_adapter and hasattr(font_adapter, "generate_font_face"):
            result = font_adapter.generate_font_face(
                font_name, font_files, **attributes
            )
            return str(result) if result is not None else ""

    src_parts = []
    format_map = {
        "woff2": "woff2",
        "woff": "woff",
        "ttf": "truetype",
        "otf": "opentype",
    }

    for ext, url in font_files.items():
        format_name = format_map.get(ext, ext)
        src_parts.append(f'url("{url}") format("{format_name}")')

    css_parts = [
        "@font-face {",
        f'  font-family: "{font_name}";',
        f"  src: {', '.join(src_parts)};",
    ]

    for key, value in attributes.items():
        if key in ("weight", "style", "display", "stretch"):
            css_key = f"font-{key}" if key in ("weight", "style", "stretch") else key
            css_parts.extend((f"  {css_key}: {value};", "}"))

    return "\n".join(css_parts)


# Advanced HTMX Integration Filters
def htmx_progressive_enhancement(
    content: str, htmx_attrs: dict[str, str], fallback_action: str = ""
) -> str:
    """Create progressively enhanced element with HTMX.

    Usage in templates:
        [[ htmx_progressive_enhancement('<button>Save</button>', {
            'hx-post': '/api/save',
            'hx-target': '#result'
        }, fallback_action='/save') ]]
    """
    # Add fallback action if provided
    if fallback_action:
        if "<form" in content:
            content = content.replace(
                "<form", f'<form action="{fallback_action}" method="post"'
            )
        elif "<button" in content and "onclick" not in content:
            content = content.replace(
                "<button",
                f"<button onclick=\"window.location.href='{fallback_action}'\"",
            )

    # Add HTMX attributes
    for attr_name, attr_value in htmx_attrs.items():
        # Find the main element and add attributes
        if "<" in content:
            first_tag_end = content.find(">")
            if first_tag_end != -1:
                before_close = content[:first_tag_end]
                after_close = content[first_tag_end:]
                content = f'{before_close} {attr_name}="{attr_value}"{after_close}'

    return content


def htmx_turbo_frame(
    frame_id: str, src: str = "", loading: str = "lazy", **attributes: t.Any
) -> str:
    """Create Turbo Frame-like behavior with HTMX.

    Usage in templates:
        [[ htmx_turbo_frame('user-profile', '/users/123/profile', loading='eager') ]]
    """
    attrs_list = [f'id="{frame_id}"']

    if src:
        attrs_list.extend(
            [
                f'hx-get="{src}"',
                f'hx-trigger="{"load" if loading == "eager" else "revealed"}"',
                'hx-swap="innerHTML"',
            ]
        )

    for key, value in attributes.items():
        if key.startswith("hx-") or key in ("class", "style"):
            attrs_list.append(f'{key}="{value}"')

    attrs_str = " ".join(attrs_list)

    placeholder = "Loading..." if loading == "eager" else "Click to load"
    return f"<div {attrs_str}>{placeholder}</div>"


def htmx_infinite_scroll_sentinel(
    next_url: str, container: str = "#content", threshold: str = "0px"
) -> str:
    """Create intersection observer sentinel for infinite scroll.

    Usage in templates:
        [[ htmx_infinite_scroll_sentinel('/api/posts?page=2', '#posts', '100px') ]]
    """
    return f'''<div hx-get="{next_url}"
                    hx-trigger="revealed"
                    hx-target="{container}"
                    hx-swap="beforeend"
                    style="height: 1px; margin-bottom: {threshold};">
               </div>'''


# Filter registration mapping
ENHANCED_FILTERS = {
    # Cloudflare Images
    "cf_image_url": cf_image_url,
    "cf_responsive_image": cf_responsive_image,
    # TwicPics
    "twicpics_image": twicpics_image,
    "twicpics_smart_crop": twicpics_smart_crop,
    # WebAwesome
    "wa_icon": wa_icon,
    "wa_icon_with_text": wa_icon_with_text,
    # Kelp
    "kelp_component": kelp_component,
    "kelp_card": kelp_card,
    # Icon Libraries
    "phosphor_icon": phosphor_icon,
    "heroicon": heroicon,
    "remix_icon": remix_icon,
    "material_icon": material_icon,
    # Font Management
    "font_face_declaration": font_face_declaration,
    # HTMX Advanced
    "htmx_progressive_enhancement": htmx_progressive_enhancement,
    "htmx_turbo_frame": htmx_turbo_frame,
    "htmx_infinite_scroll_sentinel": htmx_infinite_scroll_sentinel,
}

# Async filters
ENHANCED_ASYNC_FILTERS = {
    "async_optimized_font_loading": async_optimized_font_loading,
}


MODULE_ID = UUID("01937d8a-1234-7890-abcd-1234567890ab")
MODULE_STATUS = AdapterStatus.STABLE
