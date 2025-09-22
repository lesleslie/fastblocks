#!/usr/bin/env python3
"""Debug HTMY component discovery."""

import asyncio
import os
import sys
import typing as t

# Add the current directory to sys.path
sys.path.insert(0, "/Users/les/Projects/sites/fastest")
sys.path.insert(0, "/Users/les/Projects/fastblocks")
sys.path.insert(0, "/Users/les/Projects/acb")

# Disable ACB library mode
os.environ["ACB_LIBRARY_MODE"] = "false"


async def debug_htmy_discovery() -> None:
    print("=== HTMY Component Discovery Debug ===")

    try:
        templates = await _setup_debug_environment()
        await _debug_search_paths(templates)
        components = await _discover_and_list_components(templates)

        if "user_card" in components:
            await _test_user_card_debug(templates)
        else:
            print("❌ user_card component not found")

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback

        traceback.print_exc()


async def _setup_debug_environment() -> t.Any:
    """Set up the debug environment with ACB and templates."""
    from acb import register_pkg

    register_pkg()

    from acb.config import Config
    from acb.depends import depends
    from fastblocks.adapters.templates.jinja2 import Templates

    config = Config()
    depends.set("config", config)
    config.init()
    print("✓ Config initialized")

    templates = Templates()
    await templates.init()
    print("✓ Templates initialized")

    # Initialize HTMY registry via adapter interface
    if hasattr(templates, "htmy_registry"):
        print("✓ HTMY registry initialized")
        print(
            f"Component search paths: {getattr(templates, 'component_searchpaths', [])}"
        )
    else:
        print("No HTMY registry available")

    return templates


async def _debug_search_paths(templates: t.Any) -> None:
    """Debug the search paths and their contents."""
    for i, path in enumerate(templates.component_searchpaths):
        exists = await path.exists()
        print(f"  Path {i}: {path} (exists: {exists})")

        if exists:
            await _list_path_contents(path)


async def _list_path_contents(path: t.Any) -> None:
    """List contents of a path."""
    print("    Contents:")
    async for item in path.iterdir():
        is_file = await item.is_file()
        print(f"      {item.name} ({'file' if is_file else 'dir'})")


async def _discover_and_list_components(templates: t.Any) -> dict[str, t.Any]:
    """Discover and list all components."""
    print("\\n=== Component Discovery ===")
    components = await templates.htmy_registry.discover_components()
    print(f"Found components: {list(components.keys())}")

    for name, path in components.items():
        print(f"  {name}: {path}")

    return components


async def _test_user_card_debug(templates: t.Any) -> None:
    """Test the user_card component in debug mode."""
    print("\\n=== Testing user_card Component ===")
    try:
        source, path = await templates.htmy_registry.get_component_source("user_card")
        print(f"✓ Source loaded from {path}")
        print(f"Source preview: {source[:200]}...")

        component_class = await templates.htmy_registry.get_component_class("user_card")
        print(f"✓ Component class: {component_class}")

        instance = component_class(name="Test User", email="test@example.com")
        print(f"✓ Component instance: {instance}")

    except Exception as e:
        print(f"✗ Component test failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(debug_htmy_discovery())
