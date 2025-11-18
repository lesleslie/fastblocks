"""Template filter registration system for FastBlocks adapters."""

from contextlib import suppress
from typing import Any

from acb.depends import depends

from ._filters import FASTBLOCKS_FILTERS


def register_fastblocks_filters(template_env: Any) -> None:
    """Register all FastBlocks adapter filters with a Jinja2 environment.

    Args:
        template_env: Jinja2 Environment instance
    """
    for filter_name, filter_func in FASTBLOCKS_FILTERS.items():
        template_env.filters[filter_name] = filter_func


def register_async_fastblocks_filters(template_env: Any) -> None:
    """Register async versions of FastBlocks adapter filters.

    Args:
        template_env: Jinja2 AsyncEnvironment instance
    """
    from ._async_filters import FASTBLOCKS_ASYNC_FILTERS

    # Register both sync and async filters
    register_fastblocks_filters(template_env)

    # Add async-specific filters
    for filter_name, filter_func in FASTBLOCKS_ASYNC_FILTERS.items():
        template_env.filters[filter_name] = filter_func


def get_global_template_context() -> dict[str, Any]:
    """Get global template context with adapter instances.

    Returns:
        Dict of global template variables
    """
    context = {}

    # Add adapter instances to global context
    with suppress(Exception):
        images = depends.get_sync("images")
        if images:
            context["images_adapter"] = images

    with suppress(Exception):
        styles = depends.get_sync("styles")
        if styles:
            context["styles_adapter"] = styles

    with suppress(Exception):
        icons = depends.get_sync("icons")
        if icons:
            context["icons_adapter"] = icons

    with suppress(Exception):
        fonts = depends.get_sync("fonts")
        if fonts:
            context["fonts_adapter"] = fonts

    return context


def register_template_globals(template_env: Any) -> None:
    """Register global template variables and functions.

    Args:
        template_env: Jinja2 Environment instance
    """
    globals_dict = get_global_template_context()
    template_env.globals.update(globals_dict)


def setup_fastblocks_template_environment(
    template_env: Any, async_mode: bool = False
) -> None:
    """Complete setup of FastBlocks template environment.

    Args:
        template_env: Jinja2 Environment instance
        async_mode: Whether to register async filters
    """
    # Register filters
    if async_mode:
        register_async_fastblocks_filters(template_env)
    else:
        register_fastblocks_filters(template_env)

    # Register globals
    register_template_globals(template_env)

    # Configure template environment for FastBlocks
    template_env.trim_blocks = True
    template_env.lstrip_blocks = True

    # Set custom delimiters if not already set
    if not hasattr(template_env, "_fastblocks_delimiters_set"):
        template_env.variable_start_string = "[["
        template_env.variable_end_string = "]]"
        template_env.block_start_string = "[%"
        template_env.block_end_string = "%]"
        template_env._fastblocks_delimiters_set = True
