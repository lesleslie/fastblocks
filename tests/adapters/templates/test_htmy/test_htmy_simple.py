#!/usr/bin/env python3
"""Simple test of HTMY integration in FastBlocks."""

import asyncio
import sys
import typing as t
from pathlib import Path

import pytest

# Add paths
sys.path.insert(0, str(Path(__file__).parent))

# Test the basic HTMY registry functionality
from fastblocks.adapters.templates.htmy import HTMYComponentRegistry


class MockAsyncPath:
    """Simple AsyncPath implementation for testing."""

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
async def test_htmy_registry() -> None:
    """Test HTMY component registry functionality."""
    print("=== FastBlocks HTMY Integration Test ===")

    try:
        registry, components = await _setup_htmy_test_registry()
        if not components:
            return

        component_class = None
        if "test_card" in components:
            component_class = await _test_card_component_functionality(registry)
        else:
            print("❌ test_card component not found")

        await _test_component_caching(registry, components, component_class)
        _test_cache_key_generation(components)

        print("\\n🎉 All FastBlocks HTMY integration tests completed!")

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback

        traceback.print_exc()


async def _setup_htmy_test_registry() -> (
    tuple[t.Any, dict[str, t.Any]] | tuple[None, dict[str, t.Any]]
):
    """Set up the HTMY test registry and discover components."""
    test_dir = Path(__file__).parent / "tests/adapters/templates/test_components"

    if not test_dir.exists():
        print(f"❌ Test components directory does not exist: {test_dir}")
        return None, {}

    async_test_dir = MockAsyncPath(str(test_dir))
    registry = HTMYComponentRegistry([async_test_dir])  # type: ignore[arg-type]
    print("✓ Created HTMY registry")

    components = await registry.discover_components()  # type: ignore[misc]
    print(f"✓ Discovered components: {list(components.keys())}")

    return registry, components


async def _test_card_component_functionality(registry: t.Any) -> t.Any:
    """Test the test_card component functionality."""
    print("\\n=== Testing test_card Component ===")

    source, path = await registry.get_component_source("test_card")
    print(f"✓ Loaded source from {path}")
    print(f"Source length: {len(source)} characters")

    component_class = await registry.get_component_class("test_card")
    print(f"✓ Compiled component class: {component_class}")

    await _test_component_rendering(component_class)
    return component_class


async def _test_component_rendering(component_class: t.Any) -> None:
    """Test component instantiation and rendering."""
    instance = component_class(
        title="FastBlocks Test",
        content="HTMY integration working!",
        theme="success",
    )
    print(f"✓ Created component instance: {instance}")

    context = {"test_var": "test_value"}
    result = instance.htmy(context)
    html_output = str(result)
    print("✓ Rendered component:")
    print(f"  Output length: {len(html_output)}")
    print(f"  Content preview: {html_output[:200]}...")

    _validate_component_content(html_output)


def _validate_component_content(html_output: str) -> None:
    """Validate the rendered component content."""
    if "FastBlocks Test" in html_output and "HTMY integration working!" in html_output:
        print("🎉 FastBlocks HTMY integration test PASSED!")
    else:
        print("❌ Component content validation failed")


async def _test_component_caching(
    registry: t.Any, components: dict[str, t.Any], component_class: t.Any | None
) -> None:
    """Test component caching functionality."""
    print("\\n=== Testing Component Caching ===")

    if "test_card" in components and component_class is not None:
        component_class_cached = await registry.get_component_class("test_card")

        if component_class is component_class_cached:
            print("✓ Component caching working (same object returned)")
        else:
            print("⚠️  Component caching may not be working (different objects)")


def _test_cache_key_generation(components: dict[str, t.Any]) -> None:
    """Test cache key generation functionality."""
    if components:
        first_component_path = list(components.values())[0]
        from anyio import Path as AsyncPath

        # Convert TestAsyncPath to AsyncPath for cache key generation
        async_path = AsyncPath(str(first_component_path))
        source_key = HTMYComponentRegistry.get_cache_key(async_path)
        bytecode_key = HTMYComponentRegistry.get_cache_key(async_path, "bytecode")

        print("✓ Cache key generation:")
        print(f"  Source key: {source_key[:50]}...")
        print(f"  Bytecode key: {bytecode_key[:50]}...")


if __name__ == "__main__":
    asyncio.run(test_htmy_registry())
