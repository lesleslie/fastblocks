"""Comprehensive tests for HTMY component registry and templates.

Focuses on:
- HTMYComponentRegistry discovery and caching
- HTMYTemplates initialization and rendering
- Component source and bytecode management
- Integration with storage and cache layers
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from anyio import Path as AsyncPath
from fastblocks.adapters.templates.htmy import (
    ComponentCompilationError,
    ComponentNotFound,
    HTMYComponentRegistry,
    HTMYTemplates,
    HTMYTemplatesSettings,
)


class TestHTMYComponentRegistry:
    """Test HTMYComponentRegistry functionality."""

    def test_initialization_defaults(self):
        """Test registry initialization with defaults."""
        registry = HTMYComponentRegistry()

        assert registry.searchpaths == []
        assert registry.cache is None
        assert registry.storage is None
        assert registry._component_cache == {}
        assert registry._source_cache == {}

    def test_initialization_with_searchpaths(self):
        """Test registry initialization with searchpaths."""
        paths = [AsyncPath("/templates/components")]
        registry = HTMYComponentRegistry(searchpaths=paths)

        assert registry.searchpaths == paths

    def test_initialization_with_cache_and_storage(self):
        """Test registry initialization with cache and storage."""
        mock_cache = MagicMock()
        mock_storage = MagicMock()

        registry = HTMYComponentRegistry(cache=mock_cache, storage=mock_storage)

        assert registry.cache == mock_cache
        assert registry.storage == mock_storage

    def test_get_cache_key_source(self):
        """Test get_cache_key for source type."""
        path = AsyncPath("templates/user_card.py")
        key = HTMYComponentRegistry.get_cache_key(path, "source")

        assert "htmy_component_source:" in key
        assert "user_card.py" in key

    def test_get_cache_key_bytecode(self):
        """Test get_cache_key for bytecode type."""
        path = AsyncPath("templates/button.py")
        key = HTMYComponentRegistry.get_cache_key(path, "bytecode")

        assert "htmy_component_bytecode:" in key
        assert "button.py" in key

    def test_get_storage_path(self):
        """Test get_storage_path returns same path."""
        path = AsyncPath("templates/components/card.py")
        storage_path = HTMYComponentRegistry.get_storage_path(path)

        assert storage_path == path

    @pytest.mark.asyncio
    async def test_discover_components_no_searchpaths(self):
        """Test discover_components with no searchpaths."""
        registry = HTMYComponentRegistry()

        components = await registry.discover_components()

        assert components == {}

    @pytest.mark.asyncio
    async def test_discover_components_nonexistent_path(self):
        """Test discover_components with nonexistent searchpath."""
        path = AsyncPath("/nonexistent/components")
        registry = HTMYComponentRegistry(searchpaths=[path])

        components = await registry.discover_components()

        assert components == {}

    @pytest.mark.asyncio
    async def test_discover_components_success(self, tmp_path):
        """Test discover_components finds component files."""
        # Create test component directory
        comp_dir = tmp_path / "components"
        comp_dir.mkdir()
        (comp_dir / "user_card.py").write_text("# component")
        (comp_dir / "button.py").write_text("# component")
        (comp_dir / "__init__.py").write_text("# init")

        registry = HTMYComponentRegistry(searchpaths=[AsyncPath(comp_dir)])
        components = await registry.discover_components()

        # Should find 2 components (not __init__.py)
        assert len(components) == 2
        assert "user_card" in components
        assert "button" in components
        assert "__init__" not in components

    @pytest.mark.asyncio
    async def test_cache_component_source_with_cache(self):
        """Test _cache_component_source caches when cache available."""
        mock_cache = AsyncMock()
        mock_cache.set = AsyncMock()

        registry = HTMYComponentRegistry(cache=mock_cache)
        path = AsyncPath("user_card.py")
        source = "class UserCard: pass"

        await registry._cache_component_source(path, source)

        mock_cache.set.assert_called_once()
        # Check that source was encoded to bytes
        call_args = mock_cache.set.call_args
        assert isinstance(call_args[0][1], bytes)

    @pytest.mark.asyncio
    async def test_cache_component_source_no_cache(self):
        """Test _cache_component_source when no cache."""
        registry = HTMYComponentRegistry()
        path = AsyncPath("user_card.py")
        source = "class UserCard: pass"

        # Should not raise exception
        await registry._cache_component_source(path, source)

    @pytest.mark.asyncio
    async def test_cache_component_bytecode_with_cache(self):
        """Test _cache_component_bytecode caches when cache available."""
        mock_cache = AsyncMock()
        mock_cache.set = AsyncMock()

        registry = HTMYComponentRegistry(cache=mock_cache)
        path = AsyncPath("button.py")
        bytecode = b"compiled bytecode"

        await registry._cache_component_bytecode(path, bytecode)

        mock_cache.set.assert_called_once()
        call_args = mock_cache.set.call_args
        assert call_args[0][1] == bytecode

    @pytest.mark.asyncio
    async def test_cache_component_bytecode_no_cache(self):
        """Test _cache_component_bytecode when no cache."""
        registry = HTMYComponentRegistry()
        path = AsyncPath("button.py")
        bytecode = b"compiled bytecode"

        # Should not raise exception
        await registry._cache_component_bytecode(path, bytecode)

    @pytest.mark.asyncio
    async def test_get_cached_source_with_cache_hit(self):
        """Test _get_cached_source retrieves from cache."""
        mock_cache = AsyncMock()
        mock_cache.get = AsyncMock(return_value=b"cached source")

        registry = HTMYComponentRegistry(cache=mock_cache)
        path = AsyncPath("card.py")

        result = await registry._get_cached_source(path)

        assert result == "cached source"
        mock_cache.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_cached_source_cache_miss(self):
        """Test _get_cached_source when cache misses."""
        mock_cache = AsyncMock()
        mock_cache.get = AsyncMock(return_value=None)

        registry = HTMYComponentRegistry(cache=mock_cache)
        path = AsyncPath("card.py")

        result = await registry._get_cached_source(path)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_cached_source_no_cache(self):
        """Test _get_cached_source when no cache."""
        registry = HTMYComponentRegistry()
        path = AsyncPath("card.py")

        result = await registry._get_cached_source(path)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_cached_bytecode_with_cache(self):
        """Test _get_cached_bytecode retrieves from cache."""
        mock_cache = AsyncMock()
        mock_bytecode = b"bytecode data"
        mock_cache.get = AsyncMock(return_value=mock_bytecode)

        registry = HTMYComponentRegistry(cache=mock_cache)
        path = AsyncPath("form.py")

        result = await registry._get_cached_bytecode(path)

        assert result == mock_bytecode

    @pytest.mark.asyncio
    async def test_get_cached_bytecode_no_cache(self):
        """Test _get_cached_bytecode when no cache."""
        registry = HTMYComponentRegistry()
        path = AsyncPath("form.py")

        result = await registry._get_cached_bytecode(path)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_component_source_not_found(self):
        """Test get_component_source raises when component not found."""
        registry = HTMYComponentRegistry()

        with pytest.raises(ComponentNotFound, match="not found"):
            await registry.get_component_source("nonexistent")

    @pytest.mark.asyncio
    async def test_get_component_source_from_source_cache(self, tmp_path):
        """Test get_component_source returns from source cache."""
        comp_dir = tmp_path / "components"
        comp_dir.mkdir()
        comp_file = comp_dir / "cached.py"
        comp_file.write_text("# cached component")

        registry = HTMYComponentRegistry(searchpaths=[AsyncPath(comp_dir)])

        # Pre-populate source cache
        cache_key = str(comp_file)
        cached_source = "# cached source"
        registry._source_cache[cache_key] = cached_source

        source, path = await registry.get_component_source("cached")

        assert source == cached_source
        assert "cached.py" in str(path)


class TestHTMYTemplatesSettings:
    """Test HTMYTemplatesSettings configuration."""

    def test_defaults(self):
        """Test default settings values."""
        settings = HTMYTemplatesSettings()

        assert settings.searchpaths == []
        assert settings.cache_timeout == 300
        assert settings.enable_bidirectional is True
        assert settings.debug_components is False
        assert settings.enable_hot_reload is True
        assert settings.enable_lifecycle_hooks is True
        assert settings.enable_component_validation is True
        assert settings.enable_advanced_registry is True

    def test_custom_values(self):
        """Test custom settings values."""
        settings = HTMYTemplatesSettings(
            searchpaths=["/custom/path"],
            cache_timeout=600,
            debug_components=True,
            enable_hot_reload=False,
        )

        assert settings.searchpaths == ["/custom/path"]
        assert settings.cache_timeout == 600
        assert settings.debug_components is True
        assert settings.enable_hot_reload is False


class TestHTMYTemplates:
    """Test HTMYTemplates adapter class."""

    def test_initialization(self):
        """Test HTMYTemplates initialization."""
        templates = HTMYTemplates()

        assert templates.htmy_registry is None
        assert templates.advanced_registry is None
        assert templates.component_searchpaths == []
        assert templates.jinja_templates is None
        assert isinstance(templates.settings, HTMYTemplatesSettings)

    def test_initialization_with_kwargs(self):
        """Test HTMYTemplates initialization with kwargs."""
        templates = HTMYTemplates(cache_timeout=600, debug_components=True)

        assert templates.settings.cache_timeout == 600
        assert templates.settings.debug_components is True

    @pytest.mark.asyncio
    async def test_get_component_searchpaths_no_app_adapter(self):
        """Test get_component_searchpaths with no app adapter."""
        with patch(
            "fastblocks.adapters.templates.htmy.root_path", return_value="/project"
        ):
            templates = HTMYTemplates()

            searchpaths = await templates.get_component_searchpaths(None)

            assert searchpaths == []

    @pytest.mark.asyncio
    async def test_get_component_searchpaths_with_app_adapter(self):
        """Test get_component_searchpaths with app adapter."""
        mock_app = MagicMock()
        mock_app.category = "app"

        with patch(
            "fastblocks.adapters.templates.htmy.root_path", return_value="/project"
        ):
            templates = HTMYTemplates()

            with patch.object(
                templates,
                "get_searchpath",
                return_value=[AsyncPath("/project/templates/app")],
            ):
                searchpaths = await templates.get_component_searchpaths(mock_app)

                assert len(searchpaths) == 1
                assert "components" in str(searchpaths[0])

    @pytest.mark.asyncio
    async def test_get_component_searchpaths_callable_root_path(self):
        """Test get_component_searchpaths with callable root_path."""
        mock_app = MagicMock()
        mock_app.category = "admin"

        def mock_root_path():
            return "/custom/root"

        with patch("fastblocks.adapters.templates.htmy.root_path", mock_root_path):
            templates = HTMYTemplates()

            with patch.object(
                templates,
                "get_searchpath",
                return_value=[AsyncPath("/custom/root/templates/admin")],
            ):
                searchpaths = await templates.get_component_searchpaths(mock_app)

                assert len(searchpaths) == 1

    def test_settings_property(self):
        """Test settings property returns HTMYTemplatesSettings."""
        templates = HTMYTemplates()

        assert isinstance(templates.settings, HTMYTemplatesSettings)
        assert templates.settings.enable_bidirectional is True

    def test_jinja_templates_integration(self):
        """Test jinja_templates can be set for bidirectional integration."""
        templates = HTMYTemplates()
        mock_jinja = MagicMock()

        templates.jinja_templates = mock_jinja

        assert templates.jinja_templates == mock_jinja


class TestComponentExceptions:
    """Test component exception classes."""

    def test_component_not_found_exception(self):
        """Test ComponentNotFound exception."""
        exc = ComponentNotFound("TestComponent not found")

        assert str(exc) == "TestComponent not found"
        assert isinstance(exc, Exception)

    def test_component_compilation_error_exception(self):
        """Test ComponentCompilationError exception."""
        exc = ComponentCompilationError("Compilation failed")

        assert str(exc) == "Compilation failed"
        assert isinstance(exc, Exception)


class TestHTMYRegistryIntegration:
    """Test integration between registry, cache, and storage."""

    @pytest.mark.asyncio
    async def test_registry_with_full_stack(self, tmp_path):
        """Test registry with cache and storage integration."""
        # Setup
        comp_dir = tmp_path / "components"
        comp_dir.mkdir()
        (comp_dir / "integrated.py").write_text("class Integrated: pass")

        mock_cache = AsyncMock()
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock()

        mock_storage = AsyncMock()

        # Create registry
        registry = HTMYComponentRegistry(
            searchpaths=[AsyncPath(comp_dir)], cache=mock_cache, storage=mock_storage
        )

        # Discover components
        components = await registry.discover_components()

        assert "integrated" in components
        assert mock_cache is not None
        assert mock_storage is not None

    @pytest.mark.asyncio
    async def test_component_lifecycle_with_caching(self, tmp_path):
        """Test complete component lifecycle with caching."""
        # Setup component directory
        comp_dir = tmp_path / "components"
        comp_dir.mkdir()
        source_code = """
class TestComponent:
    def htmy(self, context):
        return "<div>Test</div>"
"""
        (comp_dir / "test_comp.py").write_text(source_code)

        mock_cache = AsyncMock()
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock()

        registry = HTMYComponentRegistry(
            searchpaths=[AsyncPath(comp_dir)], cache=mock_cache
        )

        # First access - should cache
        source, path = await registry.get_component_source("test_comp")

        assert "class TestComponent" in source
        # Should have called cache.set to store the source
        assert mock_cache.set.call_count > 0
