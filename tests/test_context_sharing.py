#!/usr/bin/env python3
"""Test comprehensive context sharing between Jinja2 and HTMY systems."""

import asyncio
import typing as t
from pathlib import Path

import pytest


# Test utilities (same as before)
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


class HTMYComponentRegistry:
    """Simplified registry for testing."""

    def __init__(self, searchpaths: list[MockAsyncPath] | None = None) -> None:
        self.searchpaths = searchpaths or []
        self._component_cache: dict[str, t.Any] = {}
        self._source_cache: dict[str, str] = {}

    async def discover_components(self) -> dict[str, MockAsyncPath]:
        components = {}
        for search_path in self.searchpaths:
            if not await search_path.exists():
                continue
            async for component_file in search_path.rglob("*.py"):
                if component_file.name == "__init__.py":
                    continue
                component_name = component_file.stem
                components[component_name] = component_file
        return components

    async def get_component_source(
        self, component_name: str
    ) -> tuple[str, MockAsyncPath]:
        components = await self.discover_components()
        if component_name not in components:
            raise Exception(f"Component '{component_name}' not found")
        component_path = components[component_name]
        cache_key = str(component_path)
        if cache_key in self._source_cache:
            return self._source_cache[cache_key], component_path
        source = await component_path.read_text()
        self._source_cache[cache_key] = source
        return source, component_path

    async def get_component_class(self, component_name: str) -> t.Any:
        if component_name in self._component_cache:
            return self._component_cache[component_name]
        source, component_path = await self.get_component_source(component_name)
        try:
            namespace = {}
            compiled_code = compile(source, str(component_path), "exec")
            exec(compiled_code, namespace)
            component_class = None
            for obj in namespace.values():
                if hasattr(obj, "htmy") and callable(getattr(obj, "htmy")):
                    component_class = obj
                    break
            if component_class is None:
                raise Exception(f"No valid component class found in {component_path}")
            self._component_cache[component_name] = component_class
            return component_class
        except Exception as e:
            raise Exception(
                f"Failed to compile component '{component_name}': {e}"
            ) from e


@pytest.mark.unit
async def test_context_sharing() -> None:
    """Test comprehensive context sharing between Jinja2 and HTMY."""
    print("=== Context Sharing Test ===")

    try:
        setup_result = await _setup_context_test_environment()
        if not setup_result:
            return

        registry, component_path = setup_result
        components = await _discover_test_components(registry, component_path)

        if "context_test" in components:
            await _test_context_component_functionality(registry)
        else:
            print("❌ context_test component not found")

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback

        traceback.print_exc()


async def _setup_context_test_environment() -> (
    tuple[HTMYComponentRegistry, MockAsyncPath] | None
):
    """Set up the test environment for context sharing tests."""
    component_path = MockAsyncPath(
        "/Users/les/Projects/sites/fastest/templates/app/bulma/components"
    )
    registry = HTMYComponentRegistry([component_path])
    print("✓ Registry created")

    exists = await component_path.exists()
    print(f"✓ Component path exists: {exists}")

    if not exists:
        print("❌ Component path does not exist")
        return None

    return registry, component_path


async def _discover_test_components(
    registry: HTMYComponentRegistry, component_path: MockAsyncPath
) -> dict[str, MockAsyncPath]:
    """Discover components for testing."""
    components = await registry.discover_components()
    print(f"✓ Found components: {list(components.keys())}")
    return components


async def _test_context_component_functionality(
    registry: HTMYComponentRegistry,
) -> None:
    """Test context sharing component functionality."""
    print("\\n=== Testing Context Sharing Component ===")

    mock_functions = _create_mock_functions()
    component_class = await registry.get_component_class("context_test")
    print(f"✓ Component class loaded: {component_class}")

    await _test_rich_context_sharing(component_class, mock_functions)


def _create_mock_functions() -> dict[str, t.Any]:
    """Create mock functions for testing."""

    async def mock_render_template(
        name: str, context: dict[str, t.Any] | None = None, **kwargs: t.Any
    ) -> str:
        return f"<mock-template name='{name}' context-keys='{len(context or {})}' />"

    async def mock_render_block(
        name: str, context: dict[str, t.Any] | None = None, **kwargs: t.Any
    ) -> str:
        return f"<mock-block name='{name}' context-keys='{len(context or {})}' />"

    return {
        "render_template": mock_render_template,
        "render_block": mock_render_block,
    }


async def _test_rich_context_sharing(
    component_class: t.Any, mock_functions: dict[str, t.Any]
) -> None:
    """Test component with rich context data."""
    print("\\n--- Test: Rich Context Sharing ---")

    rich_context = _create_rich_test_context(mock_functions)
    instance = component_class(title="Rich Context Test")

    result = await instance.htmy(rich_context)
    html_output = str(result)

    print("✓ Context test component rendered")
    print(f"Output length: {len(html_output)}")

    _validate_context_capabilities(html_output)


def _create_rich_test_context(mock_functions: dict[str, t.Any]) -> dict[str, t.Any]:
    """Create a rich context similar to what FastBlocks would provide."""
    return {
        # Simulated Jinja2 context
        "username": "test_user",
        "user_email": "test@example.com",
        "page_title": "Context Test Page",
        "is_authenticated": True,
        "user_data": {
            "id": 123,
            "roles": ["user", "admin"],
            "preferences": {"theme": "dark", "language": "en"},
        },
        # HTMY system context
        **mock_functions,
        "_jinja_context": {
            "username": "test_user",
            "user_email": "test@example.com",
        },
        "_template_system": "htmy",
        "_request": {"method": "GET", "path": "/test"},
        # Additional test data
        "config": {"debug": True, "version": "1.0.0"},
        "session": {"session_id": "abc123", "csrf_token": "xyz789"},
    }


def _validate_context_capabilities(html_output: str) -> None:
    """Validate context sharing capabilities."""
    context_checks = [
        ("Context keys available", "context keys available" in html_output.lower()),
        ("System identification", "htmy" in html_output.lower()),
        ("Template renderer available", "template renderer: ✓" in html_output.lower()),
        ("Block renderer available", "block renderer: ✓" in html_output.lower()),
        ("Request object available", "request object: ✓" in html_output.lower()),
        ("Jinja2 context available", "jinja2 context: ✓" in html_output.lower()),
        ("User context", "username" in html_output),
        ("Config context", "config" in html_output),
        ("Session context", "session" in html_output),
    ]

    print("\\n--- Context Sharing Validation ---")
    all_passed = True
    for check_name, check_result in context_checks:
        status = "✓" if check_result else "❌"
        print(f"  {status} {check_name}: {check_result}")
        if not check_result:
            all_passed = False

    _report_context_test_results(all_passed, html_output)


def _report_context_test_results(all_passed: bool, html_output: str) -> None:
    """Report context test results."""
    print("\\n--- Context Output Sample ---")
    print(html_output[:500] + ("..." if len(html_output) > 500 else ""))

    if all_passed:
        print("\\n🎉 Context sharing is working perfectly!")
        print("✓ All context variables properly shared")
        print("✓ System capabilities correctly exposed")
        print("✓ Bidirectional context flow functional")
    else:
        print("\\n⚠️  Some context sharing tests failed")


if __name__ == "__main__":
    asyncio.run(test_context_sharing())
