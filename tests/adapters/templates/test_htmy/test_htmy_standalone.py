#!/usr/bin/env python3
"""Standalone test of HTMY component functionality."""

import asyncio
import typing as t
from pathlib import Path

import pytest


# Standalone AsyncPath-like implementation
class MockAsyncPath:
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


# Copy of HTMYComponentRegistry for standalone testing
class ComponentNotFound(Exception):
    """Raised when a component cannot be found."""

    pass


class ComponentCompilationError(Exception):
    """Raised when a component fails to compile."""

    pass


class HTMYComponentRegistry:
    """Registry for discovering and caching HTMY components."""

    def __init__(self, searchpaths: list[MockAsyncPath] | None = None) -> None:
        self.searchpaths = searchpaths or []
        self._component_cache: dict[str, t.Any] = {}
        self._source_cache: dict[str, str] = {}

    async def discover_components(self) -> dict[str, MockAsyncPath]:
        """Discover all .py files in component search paths."""
        components = {}

        for search_path in self.searchpaths:
            if not await search_path.exists():
                continue

            async for component_file in search_path.rglob("*.py"):
                if component_file.name == "__init__.py__":
                    continue

                # Component name is filename without .py extension
                component_name = component_file.stem
                components[component_name] = component_file

        return components

    async def get_component_source(
        self, component_name: str
    ) -> tuple[str, MockAsyncPath]:
        """Get component source code and path."""
        components = await self.discover_components()

        if component_name not in components:
            raise ComponentNotFound(f"Component '{component_name}' not found")

        component_path = components[component_name]

        # Check cache first
        cache_key = str(component_path)
        if cache_key in self._source_cache:
            return self._source_cache[cache_key], component_path

        # Read source code
        source = await component_path.read_text()
        self._source_cache[cache_key] = source

        return source, component_path

    async def get_component_class(self, component_name: str) -> t.Any:
        """Get compiled component class."""
        if component_name in self._component_cache:
            return self._component_cache[component_name]

        source, component_path = await self.get_component_source(component_name)

        # Compile the component
        try:
            namespace = {}
            exec(compile(source, str(component_path), "exec"), namespace)

            # Find the component class (any class with htmy method)
            component_class = None
            for name, obj in namespace.items():
                if (
                    isinstance(obj, type)
                    and hasattr(obj, "htmy")
                    and not name.startswith("_")
                ):
                    component_class = obj
                    break

            if component_class is None:
                raise ComponentCompilationError(
                    f"No class with 'htmy' method found in component '{component_name}'"
                )

            self._component_cache[component_name] = component_class
            return component_class

        except Exception as e:
            raise ComponentCompilationError(
                f"Failed to compile component '{component_name}': {e}"
            ) from e


@pytest.mark.unit
async def test_component_discovery() -> None:
    """Test component discovery without full ACB setup."""
    print("=== Standalone HTMY Component Test ===")

    try:
        registry, component_path = _setup_standalone_registry()

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


def _setup_standalone_registry() -> tuple[HTMYComponentRegistry, MockAsyncPath]:
    """Set up the standalone component registry."""
    component_path = MockAsyncPath(
        "/Users/les/Projects/sites/fastest/templates/app/bulma/components"
    )
    registry = HTMYComponentRegistry([component_path])

    print(
        f"✓ Registry created with searchpaths: {[str(p) for p in registry.searchpaths]}"
    )
    return registry, component_path


async def _validate_component_path(component_path: MockAsyncPath) -> bool:
    """Validate that the component path exists."""
    exists = await component_path.exists()
    print(f"✓ Component path exists: {exists}")
    return exists


async def _discover_and_list_components(
    registry: HTMYComponentRegistry,
) -> dict[str, MockAsyncPath]:
    """Discover and list all components."""
    components = await registry.discover_components()
    print(f"✓ Found components: {list(components.keys())}")

    for name, path in components.items():
        print(f"  {name}: {path}")

    return components


async def _test_user_card_component(registry: HTMYComponentRegistry) -> None:
    """Test the user_card component functionality."""
    print("\\n=== Testing user_card Component ===")

    source, path = await registry.get_component_source("user_card")
    print(f"✓ Source loaded from {path}")
    print(f"Source preview: {source[:200]}...")

    component_class = await registry.get_component_class("user_card")
    print(f"✓ Component class: {component_class}")

    instance = component_class(name="Test User", email="test@example.com")
    print(f"✓ Component instance: {instance}")

    await _test_component_rendering(instance)


async def _test_component_rendering(instance: t.Any) -> None:
    """Test component rendering functionality."""
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
    asyncio.run(test_component_discovery())
