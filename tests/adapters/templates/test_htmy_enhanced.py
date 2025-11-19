"""Tests for Enhanced HTMY Templates Adapter.

Tests for the enhanced HTMY adapter including advanced registry integration,
component discovery, scaffolding, and lifecycle management.

Author: lesleslie <les@wedgwoodwebworks.com>
Created: 2025-01-13
"""

from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.requests import Request
from starlette.responses import HTMLResponse
from fastblocks.adapters.templates._htmy_components import (
    ComponentMetadata,
    ComponentRenderError,
    ComponentStatus,
    ComponentType,
    DataclassComponentBase,
    HTMXComponentMixin,
)
from fastblocks.adapters.templates.htmy import HTMYTemplatesSettings

# Mock components for testing


def create_mock_test_component():
    """Factory function to create mock test component to avoid import-time validation."""

    @dataclass
    class MockTestComponent(DataclassComponentBase, HTMXComponentMixin):
        """Mock test component."""

        title: str = "Test Component"
        content: str = "Test content"

        @property
        def htmx_attrs(self) -> dict[str, str]:
            return {
                "hx-get": "/api/test",
                "hx-trigger": "click",
                "hx-target": "#result",
            }

        def htmy(self, context: dict[str, Any]) -> str:
            return f"""
            <div class="test-component" {" ".join([f'{k}="{v}"' for k, v in self.htmx_attrs.items()])}>
                <h2>{self.title}</h2>
                <p>{self.content}</p>
            </div>
            """

    return MockTestComponent


class MockAsyncPath:
    """Mock AsyncPath for testing."""

    def __init__(self, path: str) -> None:
        self.path = path
        self.stem = path.split("/")[-1].replace(".py", "")

    def __str__(self) -> str:
        return self.path

    def __truediv__(self, other: str) -> "MockAsyncPath":
        return MockAsyncPath(f"{self.path}/{other}")

    async def exists(self) -> bool:
        return True


@pytest.fixture
def htmy_settings():
    """HTMY settings fixture."""
    from unittest.mock import MagicMock

    # Create a mock config to satisfy the dependency injection
    mock_config = MagicMock()
    mock_config.deployed = False

    # Create settings using only the fields that are valid for the base class
    settings = HTMYTemplatesSettings(config=mock_config)

    # Set the additional attributes manually after instantiation
    settings.enable_advanced_registry = True
    settings.enable_hot_reload = True
    settings.enable_lifecycle_hooks = True
    settings.debug_components = True

    return settings


@pytest.fixture
def htmy_adapter(htmy_settings):
    """HTMY adapter fixture."""
    from unittest.mock import MagicMock

    adapter = MagicMock()
    adapter.settings = htmy_settings
    adapter.searchpaths = htmy_settings.searchpaths
    adapter.cache_timeout = htmy_settings.cache_timeout
    adapter.enable_bidirectional = htmy_settings.enable_bidirectional
    adapter.debug_components = htmy_settings.debug_components
    adapter.enable_hot_reload = htmy_settings.enable_hot_reload
    adapter.enable_lifecycle_hooks = htmy_settings.enable_lifecycle_hooks
    adapter.enable_component_validation = htmy_settings.enable_component_validation
    adapter.enable_advanced_registry = htmy_settings.enable_advanced_registry
    adapter.htmy_registry = None
    adapter.advanced_registry = None
    adapter.component_searchpaths = []
    adapter.jinja_templates = None
    return adapter


@pytest.fixture
def mock_request():
    """Mock request fixture."""
    request = MagicMock(spec=Request)
    request.headers = {}
    request.scope = {}
    return request


@pytest.fixture
def mock_htmx_request():
    """Mock HTMX request fixture."""
    request = MagicMock(spec=Request)
    request.headers = {
        "HX-Request": "true",
        "HX-Trigger": "click",
        "HX-Target": "#content",
    }
    request.scope = {"htmx": True}
    return request


@pytest.mark.unit
class TestHTMYTemplatesSettings:
    """Test HTMY Templates Settings."""

    def test_default_settings(self):
        """Test default settings values."""
        settings = HTMYTemplatesSettings()

        assert settings.enable_advanced_registry is True
        assert settings.enable_hot_reload is True
        assert settings.enable_lifecycle_hooks is True
        assert settings.enable_component_validation is True
        assert settings.debug_components is False

    def test_custom_settings(self):
        """Test custom settings values."""
        settings = HTMYTemplatesSettings(
            enable_advanced_registry=False,
            enable_hot_reload=False,
            debug_components=True,
        )

        assert settings.enable_advanced_registry is False
        assert settings.enable_hot_reload is False
        assert settings.debug_components is True


@pytest.mark.unit
class TestHTMYTemplatesInitialization:
    """Test HTMY Templates initialization."""

    def test_adapter_initialization(self, htmy_adapter):
        """Test adapter initialization."""
        assert htmy_adapter.htmy_registry is None
        assert htmy_adapter.advanced_registry is None
        assert htmy_adapter.component_searchpaths == []
        assert htmy_adapter.jinja_templates is None
        assert isinstance(htmy_adapter.settings, HTMYTemplatesSettings)

    @pytest.mark.asyncio
    async def test_registry_initialization(self, htmy_adapter):
        """Test registry initialization."""
        # Mock get_adapter and dependencies
        with patch(
            "fastblocks.adapters.templates.htmy.get_adapter"
        ) as mock_get_adapter:
            mock_app_adapter = MagicMock()
            mock_app_adapter.category = "app"
            mock_get_adapter.return_value = mock_app_adapter

            with patch.object(
                htmy_adapter, "get_component_searchpaths"
            ) as mock_get_paths:
                mock_get_paths.return_value = [MockAsyncPath("/test/components")]

                await htmy_adapter._init_htmy_registry()

                assert htmy_adapter.htmy_registry is not None
                assert htmy_adapter.advanced_registry is not None

    @pytest.mark.asyncio
    async def test_registry_initialization_fallback(self, htmy_adapter):
        """Test registry initialization with fallback."""
        with patch(
            "fastblocks.adapters.templates.htmy.get_adapter"
        ) as mock_get_adapter:
            mock_get_adapter.return_value = None

            with patch("fastblocks.adapters.templates.htmy.depends") as mock_depends:
                mock_depends.get.side_effect = Exception("No app adapter")

                with patch.object(
                    htmy_adapter, "get_component_searchpaths"
                ) as mock_get_paths:
                    mock_get_paths.return_value = [MockAsyncPath("/test/components")]

                    await htmy_adapter._init_htmy_registry()

                    assert htmy_adapter.htmy_registry is not None


@pytest.mark.unit
class TestComponentDiscovery:
    """Test component discovery functionality."""

    @pytest.mark.asyncio
    async def test_discover_components_advanced(self, htmy_adapter):
        """Test component discovery with advanced registry."""
        # Setup advanced registry
        htmy_adapter.advanced_registry = MagicMock()
        expected_components = {
            "test_component": ComponentMetadata(
                name="test_component",
                path=MockAsyncPath("/test/test_component.py"),
                type=ComponentType.DATACLASS,
                status=ComponentStatus.VALIDATED,
            )
        }
        htmy_adapter.advanced_registry.discover_components = AsyncMock(
            return_value=expected_components
        )

        components = await htmy_adapter.discover_components()

        assert components == expected_components
        htmy_adapter.advanced_registry.discover_components.assert_called_once()

    @pytest.mark.asyncio
    async def test_discover_components_fallback(self, htmy_adapter):
        """Test component discovery fallback to basic registry."""
        # Setup basic registry without advanced
        htmy_adapter.advanced_registry = None
        htmy_adapter.htmy_registry = MagicMock()
        htmy_adapter.htmy_registry.discover_components = AsyncMock(
            return_value={"basic_component": MockAsyncPath("/test/basic_component.py")}
        )

        await htmy_adapter._init_htmy_registry()
        components = await htmy_adapter.discover_components()

        assert "basic_component" in components
        assert isinstance(components["basic_component"], ComponentMetadata)
        assert components["basic_component"].type == ComponentType.BASIC


@pytest.mark.unit
class TestComponentRendering:
    """Test component rendering functionality."""

    @pytest.mark.asyncio
    async def test_render_component_advanced(self, htmy_adapter, mock_request):
        """Test component rendering with advanced registry."""
        # Setup advanced registry
        htmy_adapter.advanced_registry = MagicMock()
        htmy_adapter.advanced_registry.render_component_with_lifecycle = AsyncMock(
            return_value="<div>Advanced rendered content</div>"
        )

        response = await htmy_adapter.render_component_advanced(
            mock_request, "test_component", {"data": "value"}
        )

        assert isinstance(response, HTMLResponse)
        assert b"Advanced rendered content" in response.body
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_render_component_advanced_error(self, htmy_adapter, mock_request):
        """Test component rendering error handling."""
        htmy_adapter.advanced_registry = MagicMock()
        htmy_adapter.advanced_registry.render_component_with_lifecycle = AsyncMock(
            side_effect=ComponentRenderError("Test error")
        )
        htmy_adapter.settings.debug_components = True

        response = await htmy_adapter.render_component_advanced(
            mock_request, "test_component"
        )

        assert response.status_code == 500
        assert b"Component test_component error" in response.body

    @pytest.mark.asyncio
    async def test_render_component_fallback_to_advanced(
        self, htmy_adapter, mock_request
    ):
        """Test render_component fallback to advanced registry."""
        htmy_adapter.advanced_registry = MagicMock()
        htmy_adapter.settings.enable_advanced_registry = True

        with patch.object(htmy_adapter, "render_component_advanced") as mock_advanced:
            mock_advanced.return_value = HTMLResponse("Advanced response")

            response = await htmy_adapter.render_component(
                mock_request, "test_component"
            )

            mock_advanced.assert_called_once()
            assert response.body == b"Advanced response"

    @pytest.mark.asyncio
    async def test_render_component_legacy(self, htmy_adapter, mock_request):
        """Test component rendering with legacy registry."""
        htmy_adapter.settings.enable_advanced_registry = False
        htmy_adapter.htmy_registry = MagicMock()
        MockTestComponent = create_mock_test_component()
        htmy_adapter.htmy_registry.get_component_class = AsyncMock(
            return_value=MockTestComponent
        )

        with patch.object(htmy_adapter, "_create_template_renderer") as mock_renderer:
            mock_renderer.return_value = lambda *args, **kwargs: "template_content"

            with patch.object(htmy_adapter, "_create_block_renderer") as mock_block:
                mock_block.return_value = lambda *args, **kwargs: "block_content"

                response = await htmy_adapter.render_component(
                    mock_request, "test_component", {"title": "Test Title"}
                )

                assert isinstance(response, HTMLResponse)
                assert response.status_code == 200


@pytest.mark.unit
class TestComponentScaffolding:
    """Test component scaffolding functionality."""

    @pytest.mark.asyncio
    async def test_scaffold_component(self, htmy_adapter):
        """Test component scaffolding."""
        htmy_adapter.advanced_registry = MagicMock()
        expected_path = MockAsyncPath("/test/components/new_component.py")
        htmy_adapter.advanced_registry.scaffold_component = AsyncMock(
            return_value=expected_path
        )

        result_path = await htmy_adapter.scaffold_component(
            "NewComponent",
            ComponentType.HTMX,
            props={"title": str},
            htmx_enabled=True,
            endpoint="/api/new",
        )

        assert result_path == expected_path
        htmy_adapter.advanced_registry.scaffold_component.assert_called_once()

    @pytest.mark.asyncio
    async def test_scaffold_component_no_advanced_registry(self, htmy_adapter):
        """Test scaffolding without advanced registry."""
        htmy_adapter.advanced_registry = None

        with pytest.raises(ComponentRenderError):
            await htmy_adapter.scaffold_component("NewComponent")


@pytest.mark.unit
class TestComponentValidation:
    """Test component validation functionality."""

    @pytest.mark.asyncio
    async def test_validate_component(self, htmy_adapter):
        """Test component validation."""
        expected_metadata = ComponentMetadata(
            name="test_component",
            path=MockAsyncPath("/test/test_component.py"),
            type=ComponentType.DATACLASS,
            status=ComponentStatus.VALIDATED,
        )

        with patch.object(htmy_adapter, "discover_components") as mock_discover:
            mock_discover.return_value = {"test_component": expected_metadata}

            result = await htmy_adapter.validate_component("test_component")

            assert result == expected_metadata

    @pytest.mark.asyncio
    async def test_validate_component_not_found(self, htmy_adapter):
        """Test validation of non-existent component."""
        with patch.object(htmy_adapter, "discover_components") as mock_discover:
            mock_discover.return_value = {}

            with pytest.raises(Exception):  # ComponentNotFound
                await htmy_adapter.validate_component("nonexistent")


@pytest.mark.unit
class TestLifecycleManagement:
    """Test lifecycle management functionality."""

    def test_get_lifecycle_manager(self, htmy_adapter):
        """Test lifecycle manager access."""
        htmy_adapter.advanced_registry = MagicMock()
        mock_lifecycle_manager = MagicMock()
        htmy_adapter.advanced_registry.lifecycle_manager = mock_lifecycle_manager

        result = htmy_adapter.get_lifecycle_manager()

        assert result == mock_lifecycle_manager

    def test_get_lifecycle_manager_no_registry(self, htmy_adapter):
        """Test lifecycle manager access without advanced registry."""
        htmy_adapter.advanced_registry = None

        result = htmy_adapter.get_lifecycle_manager()

        assert result is None

    def test_register_lifecycle_hook(self, htmy_adapter):
        """Test lifecycle hook registration."""
        mock_lifecycle_manager = MagicMock()
        htmy_adapter.advanced_registry = MagicMock()
        htmy_adapter.advanced_registry.lifecycle_manager = mock_lifecycle_manager

        def callback(**kwargs):
            return None

        htmy_adapter.register_lifecycle_hook("before_render", callback)

        mock_lifecycle_manager.register_hook.assert_called_once_with(
            "before_render", callback
        )


@pytest.mark.unit
class TestHTMXIntegration:
    """Test HTMX integration functionality."""

    @pytest.mark.asyncio
    async def test_render_htmx_component(self, htmy_adapter, mock_htmx_request):
        """Test rendering HTMX-enabled component."""
        htmy_adapter.advanced_registry = MagicMock()
        htmy_adapter.advanced_registry.render_component_with_lifecycle = AsyncMock(
            return_value='<div hx-get="/api/test">HTMX content</div>'
        )

        response = await htmy_adapter.render_component_advanced(
            mock_htmx_request, "htmx_component"
        )

        assert b'hx-get="/api/test"' in response.body

    def test_htmx_component_mixin_integration(self):
        """Test HTMX component mixin integration."""
        MockTestComponent = create_mock_test_component()
        component = MockTestComponent(title="HTMX Test")

        # Test HTMX attributes
        assert "hx-get" in component.htmx_attrs
        assert component.htmx_attrs["hx-get"] == "/api/test"

        # Test request detection
        mock_request = MagicMock()
        mock_request.headers = {"HX-Request": "true"}
        assert component.is_htmx_request(mock_request) is True


@pytest.mark.unit
class TestTemplateIntegration:
    """Test template system integration."""

    @pytest.mark.asyncio
    async def test_render_template_method(self, htmy_adapter, mock_request):
        """Test render_template method."""
        with patch.object(htmy_adapter, "render_component") as mock_render:
            mock_render.return_value = HTMLResponse("Template response")

            await htmy_adapter.render_template(
                mock_request, "test_template", {"data": "value"}
            )

            mock_render.assert_called_once_with(
                request=mock_request,
                component="test_template",
                context={"data": "value"},
                status_code=200,
                headers=None,
            )

    def test_template_renderer_creation(self, htmy_adapter, mock_request):
        """Test template renderer creation."""
        htmy_adapter.jinja_templates = MagicMock()
        htmy_adapter.jinja_templates.app = MagicMock()

        renderer = htmy_adapter._create_template_renderer(mock_request)

        assert callable(renderer)

    def test_block_renderer_creation(self, htmy_adapter, mock_request):
        """Test block renderer creation."""
        htmy_adapter.jinja_templates = MagicMock()
        htmy_adapter.jinja_templates.app = MagicMock()

        renderer = htmy_adapter._create_block_renderer(mock_request)

        assert callable(renderer)


@pytest.mark.unit
class TestCacheManagement:
    """Test cache management functionality."""

    @pytest.mark.asyncio
    async def test_clear_component_cache_advanced(self, htmy_adapter):
        """Test clearing component cache with advanced registry."""
        htmy_adapter.advanced_registry = MagicMock()

        await htmy_adapter.clear_component_cache("test_component")

        htmy_adapter.advanced_registry.clear_cache.assert_called_once_with(
            "test_component"
        )

    @pytest.mark.asyncio
    async def test_clear_component_cache_legacy(self, htmy_adapter):
        """Test clearing component cache with legacy registry."""
        htmy_adapter.advanced_registry = None
        htmy_adapter.htmy_registry = MagicMock()
        htmy_adapter.htmy_registry._component_cache = {"test": "value"}

        await htmy_adapter.clear_component_cache("test")

        # Verify legacy cache clearing logic
        # (Implementation would depend on the specific legacy behavior)


@pytest.mark.unit
class TestErrorHandling:
    """Test error handling scenarios."""

    @pytest.mark.asyncio
    async def test_render_component_registry_not_initialized(
        self, htmy_adapter, mock_request
    ):
        """Test rendering when registry is not initialized."""
        htmy_adapter.htmy_registry = None
        htmy_adapter.advanced_registry = None

        with patch.object(htmy_adapter, "_init_htmy_registry") as mock_init:
            mock_init.side_effect = Exception("Initialization failed")

            # Should handle gracefully and still try to initialize
            await htmy_adapter._init_htmy_registry()

    @pytest.mark.asyncio
    async def test_component_compilation_error_handling(
        self, htmy_adapter, mock_request
    ):
        """Test handling of component compilation errors."""
        htmy_adapter.htmy_registry = MagicMock()
        htmy_adapter.htmy_registry.get_component_class = AsyncMock(
            side_effect=Exception("Compilation failed")
        )
        htmy_adapter.settings.enable_advanced_registry = False

        response = await htmy_adapter.render_component(mock_request, "broken_component")

        assert response.status_code == 404
        assert b"Component broken_component error" in response.body


if __name__ == "__main__":
    pytest.main([__file__])
