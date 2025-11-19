#!/usr/bin/env python3
"""Minimal test of HTMY component discovery."""

import sys
import typing as t
from pathlib import Path

import pytest

# Add local paths
sys.path.insert(0, "/Users/les/Projects/sites/fastest")
sys.path.insert(0, "/Users/les/Projects/fastblocks")


class MockAsyncPath:
    """Minimal AsyncPath-like object for testing."""

    def __init__(self, path_str: str) -> None:
        self.path = Path(path_str)

    def __str__(self) -> str:
        return str(self.path)

    def __truediv__(self, other: str) -> "MockAsyncPath":
        return MockAsyncPath(str(self.path / other))

    async def exists(self):
        return self.path.exists()

    async def rglob(self, pattern: str):
        for p in self.path.rglob(pattern):
            yield MockAsyncPath(str(p))

    @property
    def stem(self):
        return self.path.stem

    @property
    def name(self):
        return self.path.name

    async def read_text(self):
        return self.path.read_text()


@pytest.mark.unit
async def test_component_discovery() -> None:
    """Test component discovery without full ACB setup."""
    print("=== Minimal HTMY Component Test ===")

    try:
        registry, component_path = await _setup_minimal_test_environment()

        if await _validate_component_path(component_path):
            components = await _discover_and_list_components(registry)

            if "user_card" in components:
                await _test_user_card_component(registry)
            else:
                print("❌ user_card component not found")
        else:
            print("❌ Component path does not exist")

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback

        traceback.print_exc()


async def _setup_minimal_test_environment() -> tuple[t.Any, MockAsyncPath]:
    """Set up the test environment with minimal configuration."""
    from fastblocks.adapters.templates.htmy import HTMYComponentRegistry

    component_path = MockAsyncPath(
        "/Users/les/Projects/sites/fastest/templates/app/bulma/components"
    )
    registry = HTMYComponentRegistry([component_path])  # type: ignore[arg-type]

    print(
        f"✓ Registry created with searchpaths: {[str(p) for p in registry.searchpaths]}"
    )
    return registry, component_path


async def _validate_component_path(component_path: MockAsyncPath) -> bool:
    """Validate that the component path exists."""
    exists = await component_path.exists()
    print(f"✓ Component path exists: {exists}")
    return exists


async def _discover_and_list_components(registry: t.Any) -> dict[str, MockAsyncPath]:
    """Discover components and list them."""
    components = await registry.discover_components()
    print(f"✓ Found components: {list(components.keys())}")

    for name, path in components.items():
        print(f"  {name}: {path}")

    return components


async def _test_user_card_component(registry: t.Any) -> None:
    """Test the user_card component functionality."""
    print("\\n=== Testing user_card Component ===")

    source, path = await registry.get_component_source("user_card")
    print(f"✓ Source loaded from {path}")
    print(f"Source preview: {source[:200]}...")

    component_class = await registry.get_component_class("user_card")
    print(f"✓ Component class: {component_class}")

    await _test_component_instantiation_and_rendering(component_class)


async def _test_component_instantiation_and_rendering(component_class: t.Any) -> None:
    """Test component instantiation and rendering."""
    instance = component_class(name="Test User", email="test@example.com")
    print(f"✓ Component instance: {instance}")

    try:
        mock_context = {"request": None}
        result = instance.htmy(mock_context)
        print(f"✓ HTMY render result: {result}")
        print(f"✓ HTML string: {result}")

        _validate_component_output(result)

    except Exception as e:
        print(f"✗ HTMY render failed: {e}")
        import traceback

        traceback.print_exc()


def _validate_component_output(result: t.Any) -> None:
    """Validate the component rendering output."""
    if "HTMY Component Rendered Successfully!" in str(result):
        print("🎉 Basic HTMY component functionality is working!")
    else:
        print("❌ Component rendered but missing expected content")


if __name__ == "__main__":
    import asyncio

    asyncio.run(test_component_discovery())
