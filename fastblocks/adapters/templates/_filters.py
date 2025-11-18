"""Jinja2 custom filters for FastBlocks adapter integration."""

from typing import Any

from acb.depends import depends


def img_tag(image_id: str, alt: str, **attributes: Any) -> str:
    """Generate image tag using configured image adapter.

    Usage in templates:
        [[ img_tag('product.jpg', 'Product Image', width=300, class='responsive') ]]
    """
    images = depends.get_sync("images")
    if images:
        result = images.get_img_tag(image_id, alt, **attributes)
        return (
            str(result) if result is not None else f'<img src="{image_id}" alt="{alt}">'
        )

    # Fallback to basic img tag
    attr_parts = [f'src="{image_id}"', f'alt="{alt}"']
    for key, value in attributes.items():
        if key in ("width", "height", "class", "id", "style"):
            attr_parts.append(f'{key}="{value}"')

    return f"<img {' '.join(attr_parts)}>"


def image_url(image_id: str, **transformations: Any) -> str:
    """Generate image URL with transformations using configured image adapter.

    Note: For full functionality with transformations, use async_image_url in async templates.

    Usage in templates:
        [[ image_url('product.jpg', width=300, height=200, crop='fill') ]]
        [[ await async_image_url('product.jpg', width=300, height=200, crop='fill') ]]  # async version
    """
    images = depends.get_sync("images")
    if images and hasattr(images, "get_sync_image_url"):
        # Some adapters may provide sync methods for simple URLs
        result = images.get_sync_image_url(image_id, **transformations)
        return str(result) if result is not None else image_id
    elif images:
        # Return base URL with query parameters as fallback
        if transformations:
            params = "&".join([f"{k}={v}" for k, v in transformations.items()])
            return f"{image_id}?{params}"
        return image_id

    # Fallback to basic URL
    return image_id


def _get_base_component_class(styles: Any, component: str) -> str:
    """Get the base class for a component from styles adapter."""
    base_class = styles.get_component_class(component)
    return str(base_class) if base_class is not None else component.replace("_", "-")


def _apply_utility_modifiers(
    base_class: str, styles: Any, modifiers: dict[str, Any]
) -> str:
    """Apply utility class modifiers to base class if supported."""
    if not hasattr(styles, "get_utility_classes"):
        return base_class

    utilities = styles.get_utility_classes()
    if not utilities:
        return base_class

    for modifier, value in modifiers.items():
        utility_key = f"{modifier}_{value}"
        if utility_key in utilities:
            utility_class = utilities[utility_key]
            if utility_class:
                base_class = f"{base_class} {utility_class}"

    return base_class


def style_class(component: str, **modifiers: Any) -> str:
    """Get style framework class for component.

    Usage in templates:
        [[ style_class('button', variant='primary', size='large') ]]
    """
    styles = depends.get_sync("styles")
    if not styles:
        # Fallback to semantic class name
        return component.replace("_", "-")

    base_class = _get_base_component_class(styles, component)
    return _apply_utility_modifiers(base_class, styles, modifiers)


def icon_tag(icon_name: str, **attributes: Any) -> str:
    """Generate icon tag using configured icon adapter.

    Usage in templates:
        [[ icon_tag('home', class='nav-icon', size='24') ]]
    """
    icons = depends.get_sync("icons")
    if icons:
        result = icons.get_icon_tag(icon_name, **attributes)
        return str(result) if result is not None else f"[{icon_name}]"

    # Fallback to text placeholder
    return f"[{icon_name}]"


def icon_with_text(
    icon_name: str, text: str, position: str = "left", **attributes: Any
) -> str:
    """Generate icon with text using configured icon adapter.

    Usage in templates:
        [[ icon_with_text('save', 'Save Changes', position='left') ]]
    """
    icons = depends.get_sync("icons")
    if icons and hasattr(icons, "get_icon_with_text"):
        result = icons.get_icon_with_text(icon_name, text, position, **attributes)
        return (
            str(result)
            if result is not None
            else f"{icon_tag(icon_name, **attributes)} {text}"
        )

    # Fallback implementation
    icon = icon_tag(icon_name, **attributes)
    if position == "right":
        return f"{text} {icon}"

    return f"{icon} {text}"


def font_import() -> str:
    """Generate font import statements using configured font adapter.

    Note: For full functionality, use async_font_import in async templates.

    Usage in templates:
        [% block head %]
            [[ font_import() ]]
            [[ await async_font_import() ]]  # async version for full functionality
        [% endblock %]
    """
    fonts = depends.get_sync("fonts")
    if fonts and hasattr(fonts, "get_sync_font_import"):
        # Some adapters may provide sync methods for basic imports
        result = fonts.get_sync_font_import()
        return str(result) if result is not None else ""
    elif fonts:
        # Return basic stylesheet links if available
        if hasattr(fonts, "get_stylesheet_links"):
            links = fonts.get_stylesheet_links()
            return "\n".join(links) if links else ""

    # Fallback - no custom fonts
    return ""


def font_family(font_type: str = "primary") -> str:
    """Get font family CSS value using configured font adapter.

    Usage in templates:
        <style>
            body { font-family: [[ font_family('primary') ]]; }
            h1 { font-family: [[ font_family('heading') ]]; }
        </style>
    """
    fonts = depends.get_sync("fonts")
    if fonts:
        result = fonts.get_font_family(font_type)
        return str(result) if result is not None else "inherit"

    # Fallback fonts
    fallbacks = {
        "primary": "-apple-system, BlinkMacSystemFont, sans-serif",
        "secondary": "Georgia, serif",
        "heading": "-apple-system, BlinkMacSystemFont, sans-serif",
        "body": "-apple-system, BlinkMacSystemFont, sans-serif",
        "monospace": "'Courier New', monospace",
    }
    return fallbacks.get(font_type, "inherit")


def stylesheet_links() -> str:
    """Generate all stylesheet links for configured adapters.

    Usage in templates:
        [% block head %]
            [[ stylesheet_links() ]]
        [% endblock %]
    """
    links = []

    # Get style framework links
    styles = depends.get_sync("styles")
    if styles:
        links.extend(styles.get_stylesheet_links())

    # Get icon framework links
    icons = depends.get_sync("icons")
    if icons and hasattr(icons, "get_stylesheet_links"):
        links.extend(icons.get_stylesheet_links())

    return "\n".join(links)


def component_html(component: str, content: str = "", **attributes: Any) -> str:
    """Generate complete HTML component using style adapter.

    Usage in templates:
        [[ component_html('button', 'Click Me', variant='primary', class='my-btn') ]]
    """
    styles = depends.get_sync("styles")
    if styles and hasattr(styles, "build_component_html"):
        result = styles.build_component_html(component, content, **attributes)
        return (
            str(result)
            if result is not None
            else f'<div class="{component}">{content}</div>'
        )

    # Fallback to basic HTML
    css_class = style_class(component)
    if "class" in attributes:
        css_class = f"{css_class} {attributes.pop('class')}"

    attr_parts = [f'class="{css_class}"']
    for key, value in attributes.items():
        attr_parts.append(f'{key}="{value}"')

    attrs_str = " ".join(attr_parts)

    if component.startswith("button"):
        return f"<button {attrs_str}>{content}</button>"

    return f"<div {attrs_str}>{content}</div>"


def htmx_attrs(**htmx_attributes: Any) -> str:
    """Generate HTMX attributes for enhanced interactivity.

    Usage in templates:
        <button [[ htmx_attrs(get='/api/data', target='#content', swap='innerHTML') ]]>
            Load Data
        </button>
    """
    attr_parts = []

    # Map common HTMX attributes with enhanced support
    attr_mapping = {
        "get": "hx-get",
        "post": "hx-post",
        "put": "hx-put",
        "delete": "hx-delete",
        "patch": "hx-patch",
        "target": "hx-target",
        "swap": "hx-swap",
        "trigger": "hx-trigger",
        "indicator": "hx-indicator",
        "confirm": "hx-confirm",
        "vals": "hx-vals",
        "headers": "hx-headers",
        "include": "hx-include",
        "params": "hx-params",
        "boost": "hx-boost",
        "push_url": "hx-push-url",
        "replace_url": "hx-replace-url",
        "ext": "hx-ext",
        "select": "hx-select",
        "select_oob": "hx-select-oob",
        "sync": "hx-sync",
        "history": "hx-history",
        "disabled_elt": "hx-disabled-elt",
        "encoding": "hx-encoding",
        "preserve": "hx-preserve",
    }

    for key, value in htmx_attributes.items():
        htmx_attr = attr_mapping.get(key, f"hx-{key.replace('_', '-')}")
        attr_parts.append(f'{htmx_attr}="{value}"')

    return " ".join(attr_parts)


def htmx_component(component_type: str, **attributes: Any) -> str:
    """Generate HTMX-enabled components with adapter integration.

    Usage in templates:
        <div [[ htmx_component('card', get='/api/details/{id}', target='#details') ]]>
            [[ component_html('card-header', 'Title') ]]
            <div id="details"></div>
        </div>
    """
    # Extract HTMX attributes
    htmx_attrs_dict = {}
    component_attrs = {}

    for key, value in attributes.items():
        if key in (
            "get",
            "post",
            "put",
            "delete",
            "patch",
            "target",
            "swap",
            "trigger",
            "indicator",
            "confirm",
            "vals",
            "headers",
            "include",
            "params",
            "boost",
            "push_url",
            "replace_url",
            "ext",
            "select",
            "select_oob",
            "sync",
            "history",
            "disabled_elt",
            "encoding",
            "preserve",
        ):
            htmx_attrs_dict[key] = value
        else:
            component_attrs[key] = value

    # Get component styling from style adapter
    css_class = style_class(component_type, **component_attrs)

    # Add HTMX attributes if any
    htmx_str = htmx_attrs(**htmx_attrs_dict) if htmx_attrs_dict else ""

    # Build complete attribute string
    attr_parts = [f'class="{css_class}"']
    if htmx_str:
        attr_parts.append(htmx_str)

    return " ".join(attr_parts)


def htmx_form(action: str, **attributes: Any) -> str:
    """Generate HTMX-enabled forms with validation and feedback.

    Usage in templates:
        <form [[ htmx_form('/users/create', target='#form-container',
                          validation_target='#form-errors') ]]>
            <!-- form fields -->
        </form>
    """
    # Set default HTMX behavior for forms
    form_attrs = {
        "post": action,
        "swap": "outerHTML",
        "indicator": "#form-loading",
    } | attributes

    # Handle validation target if specified
    if "validation_target" in form_attrs:
        validation_target = form_attrs.pop("validation_target")
        form_attrs["headers"] = f'{{"HX-Error-Target": "{validation_target}"}}'

    return htmx_attrs(**form_attrs)


def htmx_lazy_load(url: str, placeholder: str = "Loading...", **attributes: Any) -> str:
    """Create lazy-loading containers with intersection observers.

    Usage in templates:
        <div [[ htmx_lazy_load('/api/content', 'Loading content...',
                              trigger='revealed once') ]]>
        </div>
    """
    lazy_attrs = {
        "get": url,
        "trigger": "revealed once",
        "indicator": "this",
    } | attributes

    attrs_str = htmx_attrs(**lazy_attrs)
    return f'{attrs_str} data-placeholder="{placeholder}"'


def htmx_infinite_scroll(
    next_url: str, container: str = "#infinite-container", **attributes: Any
) -> str:
    """Generate infinite scroll triggers.

    Usage in templates:
        <div [[ htmx_infinite_scroll('/api/posts?page=2', '#posts-container') ]]>
            Loading more posts...
        </div>
    """
    scroll_attrs = {
        "get": next_url,
        "trigger": "revealed",
        "target": container,
        "swap": "afterend",
    } | attributes

    return htmx_attrs(**scroll_attrs)


def htmx_search(endpoint: str, debounce: int = 300, **attributes: Any) -> str:
    """Generate debounced search inputs.

    Usage in templates:
        <input type="text" name="q"
               [[ htmx_search('/api/search', 500, target='#results') ]]>
    """
    search_attrs = {
        "get": endpoint,
        "trigger": f"keyup changed delay:{debounce}ms",
        "target": "#search-results",
        "indicator": "#search-loading",
    } | attributes

    return htmx_attrs(**search_attrs)


def htmx_modal(content_url: str, **attributes: Any) -> str:
    """Create modal dialog triggers.

    Usage in templates:
        <button [[ htmx_modal('/modal/user/{id}', target='#modal-container') ]]>
            View Details
        </button>
    """
    modal_attrs = {
        "get": content_url,
        "target": "#modal-container",
        "swap": "innerHTML",
    } | attributes

    return htmx_attrs(**modal_attrs)


def htmx_img_swap(
    image_id: str, transformations: dict[str, Any] | None = None, **attributes: Any
) -> str:
    """Dynamic image swapping with transformations using image adapter.

    Usage in templates:
        <img [[ htmx_img_swap('product.jpg', {'width': 300},
                             trigger='mouseenter once', target='this') ]]>
    """
    images = depends.get_sync("images")
    if not images:
        return htmx_attrs(**attributes)

    # Build transformation URL
    if transformations:
        # This would typically be handled by the image adapter
        transform_url = f"/api/images/{image_id}/transform"
        swap_attrs = {
            "get": transform_url,
            "vals": str(transformations),
            "target": "this",
            "swap": "outerHTML",
        } | attributes
    else:
        swap_attrs = {
            "get": f"/api/images/{image_id}",
            "target": "this",
            "swap": "outerHTML",
        } | attributes

    return htmx_attrs(**swap_attrs)


def htmx_icon_toggle(icon_on: str, icon_off: str, **attributes: Any) -> str:
    """Icon state toggles for interactive elements.

    Usage in templates:
        <button [[ htmx_icon_toggle('heart-filled', 'heart-outline',
                                   post='/favorites/toggle/{id}') ]]>
            [[ icon_tag('heart-outline') ]]
        </button>
    """
    toggle_attrs = {"swap": "outerHTML", "target": "this"} | attributes

    # Add data attributes for icon states
    attrs_str = htmx_attrs(**toggle_attrs)
    return f'{attrs_str} data-icon-on="{icon_on}" data-icon-off="{icon_off}"'


def htmx_ws_connect(endpoint: str, **attributes: Any) -> str:
    """Generate WebSocket connection attributes for real-time features.

    Usage in templates:
        <div [[ htmx_ws_connect('/ws/notifications',
                               listen='notification-received') ]]>
        </div>
    """
    ws_attrs = {"ext": "ws"} | attributes

    # Handle WebSocket-specific attributes
    if "listen" in ws_attrs:
        listen_event = ws_attrs.pop("listen")
        attrs_str = htmx_attrs(**ws_attrs)
        return f'{attrs_str} ws-connect="{endpoint}" sse-listen="{listen_event}"'
    else:
        attrs_str = htmx_attrs(**ws_attrs)
        return f'{attrs_str} ws-connect="{endpoint}"'


def htmx_validation_feedback(field_name: str, **attributes: Any) -> str:
    """Generate real-time validation feedback containers.

    Usage in templates:
        <input name="email"
               [[ htmx_validation_feedback('email',
                                         validate_url='/validate/email') ]]>
    """
    validate_url = attributes.pop("validate_url", f"/validate/{field_name}")

    validation_attrs = {
        "get": validate_url,
        "trigger": "blur, keyup changed delay:500ms",
        "target": f"#{field_name}-feedback",
        "include": "this",
    } | attributes

    return htmx_attrs(**validation_attrs)


def htmx_error_container(container_id: str = "htmx-errors") -> str:
    """Generate error display containers for HTMX responses.

    Usage in templates:
        <div [[ htmx_error_container('form-errors') ]]></div>
    """
    return f'id="{container_id}" class="htmx-error-container" role="alert"'


def htmx_retry_trigger(max_retries: int = 3, backoff: str = "exponential") -> str:
    """Generate retry mechanisms for failed HTMX requests.

    Usage in templates:
        <div [[ htmx_retry_trigger(3, 'exponential') ]]>
    """
    return f'data-max-retries="{max_retries}" data-backoff="{backoff}"'


# Filter registration mapping for template engines
FASTBLOCKS_FILTERS = {
    "img_tag": img_tag,
    "image_url": image_url,
    "style_class": style_class,
    "icon_tag": icon_tag,
    "icon_with_text": icon_with_text,
    "font_import": font_import,
    "font_family": font_family,
    "stylesheet_links": stylesheet_links,
    "component_html": component_html,
    "htmx_attrs": htmx_attrs,
    "htmx_component": htmx_component,
    "htmx_form": htmx_form,
    "htmx_lazy_load": htmx_lazy_load,
    "htmx_infinite_scroll": htmx_infinite_scroll,
    "htmx_search": htmx_search,
    "htmx_modal": htmx_modal,
    "htmx_img_swap": htmx_img_swap,
    "htmx_icon_toggle": htmx_icon_toggle,
    "htmx_ws_connect": htmx_ws_connect,
    "htmx_validation_feedback": htmx_validation_feedback,
    "htmx_error_container": htmx_error_container,
    "htmx_retry_trigger": htmx_retry_trigger,
}
