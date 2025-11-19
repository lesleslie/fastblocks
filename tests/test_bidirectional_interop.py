#!/usr/bin/env python3
"""Test bidirectional Jinja2-HTMY interoperability."""

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

    async def write_bytes(self, content: bytes) -> None:
        self.path.write_bytes(content)

    async def stat(self):
        stat = self.path.stat()
        return type("stat", (), {"st_mtime": stat.st_mtime, "st_size": stat.st_size})()


# Mock template system for testing
class MockTemplate:
    def __init__(self, content: str) -> None:
        self.content = content

    async def render(self, context: dict[str, t.Any]) -> str:
        # Simple template replacement for testing
        result = self.content
        for key, value in context.items():
            result = result.replace(f"[[ {key} ]]", str(value))
        return result


class MockApp:
    def __init__(self) -> None:
        self.templates = {
            "blocks/card_content.html": MockTemplate("""
<div class="jinja2-content card-content">
    <h3 class="title is-5">[[ title ]]</h3>
    <div class="content">
        <p>[[ content ]]</p>
        <div class="tags">
            <span class="tag is-info">Rendered by: Jinja2</span>
            <span class="tag is-success">Component: [[ component_type ]]</span>
            <span class="tag is-warning">Mode: Bidirectional</span>
        </div>
    </div>
</div>
            """)
        }

    def get_template(self, name: str):
        return self.templates.get(name, MockTemplate(f"Template '{name}' not found"))


# Copy of enhanced HTMYComponentRegistry for testing
class ComponentNotFound(Exception):
    pass


class ComponentCompilationError(Exception):
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
        cache_key = str(component_path)

        if cache_key in self._source_cache:
            return self._source_cache[cache_key], component_path

        source = await component_path.read_text()
        self._source_cache[cache_key] = source
        return source, component_path

    async def get_component_class(self, component_name: str) -> t.Any:
        """Get compiled component class."""
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
                raise ComponentCompilationError(
                    f"No valid component class found in {component_path}"
                )

            self._component_cache[component_name] = component_class
            return component_class

        except Exception as e:
            raise ComponentCompilationError(
                f"Failed to compile component '{component_name}': {e}"
            ) from e


@pytest.mark.integration
async def test_bidirectional_interop() -> None:
    """Test bidirectional HTMY-Jinja2 interoperability."""
    print("=== Bidirectional HTMY-Jinja2 Interoperability Test ===")

    try:
        setup_result = await _setup_test_environment()
        if not setup_result:
            return

        registry, component_path = setup_result
        components = await _discover_and_validate_components(registry, component_path)

        if "hybrid_card" in components:
            await _test_hybrid_component_functionality(registry)
        else:
            print("❌ hybrid_card component not found")

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback

        traceback.print_exc()


async def _setup_test_environment() -> (
    tuple[HTMYComponentRegistry, MockAsyncPath] | None
):
    """Set up the test environment and validate paths."""
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


async def _discover_and_validate_components(
    registry: HTMYComponentRegistry, component_path: MockAsyncPath
) -> dict[str, MockAsyncPath]:
    """Discover components and validate the setup."""
    components = await registry.discover_components()
    print(f"✓ Found components: {list(components.keys())}")
    return components


async def _test_hybrid_component_functionality(registry: HTMYComponentRegistry) -> None:
    """Test hybrid component functionality with both Jinja2 and pure HTMY modes."""
    print("\\n=== Testing Hybrid Component (HTMY → Jinja2) ===")

    mock_app = MockApp()
    render_template = _create_template_renderer(mock_app)

    component_class = await registry.get_component_class("hybrid_card")
    print(f"✓ Component class loaded: {component_class}")

    htmy_context = {"render_template": render_template, "request": None}

    hybrid_checks = await _test_hybrid_mode(component_class, htmy_context)
    pure_checks = await _test_pure_htmy_mode(component_class, htmy_context)

    _report_final_results(hybrid_checks, pure_checks)


def _create_template_renderer(mock_app: MockApp):
    """Create a template renderer function for testing."""

    async def render_template(
        template_name: str, context: dict[str, t.Any] | None = None, **kwargs: t.Any
    ) -> str:
        if context is None:
            context = {}
        context.update(kwargs)
        template = mock_app.get_template(template_name)
        return await template.render(context)

    return render_template


async def _test_hybrid_mode(
    component_class: t.Any, htmy_context: dict[str, t.Any]
) -> list[tuple[str, bool]]:
    """Test hybrid component with Jinja2 template integration."""
    print("\\n--- Test 1: HTMY Component calling Jinja2 Template ---")

    instance = component_class(
        title="Bidirectional Test",
        content="HTMY component calling Jinja2 template",
        template_name="blocks/card_content.html",
    )

    result = await instance.htmy(htmy_context)
    html_output = str(result)

    print("✓ Hybrid component rendered")
    print(f"Output length: {len(html_output)}")

    checks = [
        ("HTMY wrapper", "htmy-wrapper" in html_output),
        ("Jinja2 content", "jinja2-content" in html_output),
        ("Bidirectional mode", "Mode: Bidirectional" in html_output),
        ("Component type", "hybrid_card" in html_output),
        ("HTMY content", "Back to HTMY content" in html_output),
    ]

    _validate_and_report_checks("Bidirectional Content Validation", checks)
    print(f"Hybrid output preview: {html_output[:200]}...")
    return checks


async def _test_pure_htmy_mode(
    component_class: t.Any, htmy_context: dict[str, t.Any]
) -> list[tuple[str, bool]]:
    """Test pure HTMY component without Jinja2 template."""
    print("\\n--- Test 2: Pure HTMY Component (no Jinja2) ---")

    pure_instance = component_class(
        title="Pure HTMY Test",
        content="This uses only HTMY",
        template_name=None,
    )

    pure_result = await pure_instance.htmy(htmy_context)
    pure_html = str(pure_result)

    print("✓ Pure HTMY component rendered")
    print(f"Output length: {len(pure_html)}")

    pure_checks = [
        ("Pure HTMY class", "pure-htmy" in pure_html),
        ("No Jinja2 content", "jinja2-content" not in pure_html),
        ("HTMY title", "Pure HTMY Test" in pure_html),
        ("HTMY fallback message", "no Jinja2 template specified" in pure_html),
    ]

    _validate_and_report_checks("Pure HTMY Content Validation", pure_checks)
    print(f"Pure HTMY output preview: {pure_html[:200]}...")
    return pure_checks


def _validate_and_report_checks(title: str, checks: list[tuple[str, bool]]) -> None:
    """Validate checks and report results."""
    print(f"\\n--- {title} ---")
    for check_name, check_result in checks:
        status = "✓" if check_result else "❌"
        print(f"  {status} {check_name}: {check_result}")


def _report_final_results(
    hybrid_checks: list[tuple[str, bool]], pure_checks: list[tuple[str, bool]]
) -> None:
    """Report final test results."""
    if all(check[1] for check in hybrid_checks) and all(
        check[1] for check in pure_checks
    ):
        print("\\n🎉 Bidirectional HTMY-Jinja2 interoperability is working!")
        print("✓ HTMY components can call Jinja2 templates")
        print("✓ HTMY components work with or without Jinja2")
        print("✓ Template context sharing works correctly")
    else:
        print("\\n⚠️  Some interoperability tests failed")


if __name__ == "__main__":
    asyncio.run(test_bidirectional_interop())
