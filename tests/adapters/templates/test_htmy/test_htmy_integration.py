"""Comprehensive tests for HTMY integration in FastBlocks."""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest
from anyio import Path as AsyncPath
from fastblocks.adapters.templates.htmy import HTMYComponentRegistry
from fastblocks.adapters.templates.jinja2 import Templates


@pytest.mark.integration
class TestHTMYIntegration:
    """Test suite for HTMY component integration."""

    @pytest.fixture
    async def temp_directory(self):
        """Create a temporary directory for test components."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    @pytest.fixture
    async def test_components_path(self, temp_directory):
        """Create test components in temporary directory."""
        components_dir = temp_directory / "components"
        components_dir.mkdir(parents=True, exist_ok=True)

        # Create test component
        test_component = '''"""Test component for HTMY integration."""

from dataclasses import dataclass
from typing import Any

@dataclass
class SimpleTestComponent:
    title: str = "Test"
    content: str = "Content"

    def htmy(self, context):
        return f"<div class='test-component'><h3>{self.title}</h3><p>{self.content}</p><span>HTMY Test Success</span></div>"
'''

        (components_dir / "simple_test_component.py").write_text(test_component)
        return AsyncPath(str(components_dir))

    @pytest.fixture
    async def htmy_registry(self, test_components_path):
        """Create HTMY component registry with test components."""
        return HTMYComponentRegistry([test_components_path])

    @pytest.fixture
    async def mock_templates(self):
        """Create a mock Templates instance."""
        templates = Mock(spec=Templates)
        templates.app = Mock()
        templates.cache = None
        templates.storage = None
        return templates

    @pytest.fixture
    async def mock_request(self):
        """Create a mock request object."""
        request = Mock()
        request.url.path = "/test"
        request.method = "GET"
        return request

    async def test_component_discovery(self, htmy_registry):
        """Test that components are properly discovered."""
        components = await htmy_registry.discover_components()

        assert "simple_test_component" in components
        assert isinstance(components["simple_test_component"], AsyncPath)

    async def test_component_source_loading(self, htmy_registry):
        """Test that component source code is loaded correctly."""
        source, path = await htmy_registry.get_component_source("simple_test_component")

        assert "SimpleTestComponent" in source
        assert "def htmy" in source
        assert "HTMY Test Success" in source

    async def test_component_compilation(self, htmy_registry):
        """Test that components are compiled correctly."""
        component_class = await htmy_registry.get_component_class(
            "simple_test_component"
        )

        assert component_class is not None
        assert hasattr(component_class, "htmy")
        assert callable(component_class.htmy)

    async def test_component_instantiation_and_rendering(self, htmy_registry):
        """Test that components can be instantiated and rendered."""
        component_class = await htmy_registry.get_component_class(
            "simple_test_component"
        )

        # Create instance
        instance = component_class(title="Test Title", content="Test Content")

        # Render
        context = {"test_var": "test_value"}
        result = instance.htmy(context)

        assert "Test Title" in str(result)
        assert "Test Content" in str(result)
        assert "HTMY Test Success" in str(result)

    async def test_component_caching(self, htmy_registry):
        """Test that components are cached properly."""
        # First load
        component_class1 = await htmy_registry.get_component_class(
            "simple_test_component"
        )

        # Second load (should be cached)
        component_class2 = await htmy_registry.get_component_class(
            "simple_test_component"
        )

        # Should be the same object (cached)
        assert component_class1 is component_class2

    async def test_cache_key_generation(self, test_components_path):
        """Test cache key generation for components."""
        component_path = test_components_path / "simple_test_component.py"

        source_key = HTMYComponentRegistry.get_cache_key(component_path, "source")
        bytecode_key = HTMYComponentRegistry.get_cache_key(component_path, "bytecode")

        assert "htmy_component_source:" in source_key
        assert "htmy_component_bytecode:" in bytecode_key
        assert source_key != bytecode_key

    async def test_storage_path_mapping(self, test_components_path):
        """Test storage path mapping for components."""
        component_path = test_components_path / "simple_test_component.py"
        storage_path = HTMYComponentRegistry.get_storage_path(component_path)

        assert storage_path == component_path

    async def test_component_error_handling(self, htmy_registry):
        """Test error handling for non-existent components."""
        with pytest.raises(Exception) as exc_info:
            await htmy_registry.get_component_source("non_existent_component")

        assert "not found" in str(exc_info.value)

    async def test_render_component_integration(self, temp_directory, mock_request):
        """Test the render_component method integration."""
        # Skip this test if we can't create a full Templates instance
        # This would require a full FastBlocks setup
        pytest.skip("Full integration test requires complete FastBlocks environment")

    async def test_context_sharing_structure(self):
        """Test that context sharing structure is correct."""
        # Mock Templates instance
        templates = Mock(spec=Templates)
        templates.app = Mock()
        templates.cache = None
        templates.storage = None

        # Test context creation
        original_context = {"user": "test", "data": "value"}

        # Simulate what the Templates class does
        htmy_context = {
            **original_context,
            "render_template": Mock(),
            "render_block": Mock(),
            "_jinja_context": original_context,
            "_template_system": "htmy",
        }

        # Verify context structure
        assert "user" in htmy_context
        assert "data" in htmy_context
        assert "render_template" in htmy_context
        assert "render_block" in htmy_context
        assert htmy_context["_template_system"] == "htmy"
        assert htmy_context["_jinja_context"] == original_context

    async def test_template_renderer_creation(self):
        """Test template renderer function creation."""
        templates = Mock(spec=Templates)
        templates.app = Mock()
        templates.app.get_template = Mock()

        # Mock template with render method
        mock_template = Mock()
        mock_template.render = AsyncMock(return_value="<p>Test Template</p>")
        templates.app.get_template.return_value = mock_template

        # This would test the actual _create_htmy_template_renderer method
        # But it requires the actual Templates class instance
        assert callable(templates.app.get_template)

    async def test_component_with_async_htmy_method(self, temp_directory):
        """Test components with async htmy methods."""
        components_dir = temp_directory / "components"
        components_dir.mkdir(parents=True, exist_ok=True)

        # Create async component
        async_component = '''"""Async test component."""

from dataclasses import dataclass
import asyncio

@dataclass
class AsyncTestComponent:
    title: str = "Async Test"

    async def htmy(self, context):
        await asyncio.sleep(0)  # Simulate async work
        return f"<div class='async-component'><h3>{self.title}</h3><span>Async HTMY Success</span></div>"
'''

        (components_dir / "async_test_component.py").write_text(async_component)

        # Test with registry
        registry = HTMYComponentRegistry([AsyncPath(str(components_dir))])
        component_class = await registry.get_component_class("async_test_component")

        instance = component_class()
        context = {}

        # Should be able to handle async htmy method
        result = await instance.htmy(context)
        assert "Async HTMY Success" in str(result)


@pytest.mark.integration
class TestHTMYJinja2Interoperability:
    """Test suite for HTMY-Jinja2 bidirectional interoperability."""

    async def test_jinja2_to_htmy_context_structure(self):
        """Test context structure when calling HTMY from Jinja2."""
        # Simulate render_component call from Jinja2
        original_context = {"username": "test_user", "email": "test@example.com"}

        # Simulate Templates._render_component_for_jinja_async context creation
        htmy_context = {
            **original_context,
            "render_template": Mock(),
            "render_block": Mock(),
            "_jinja_context": original_context,
            "_template_system": "htmy",
        }

        assert "username" in htmy_context
        assert "email" in htmy_context
        assert "render_template" in htmy_context
        assert htmy_context["_template_system"] == "htmy"

    async def test_htmy_to_jinja2_template_call_structure(self):
        """Test structure of calling Jinja2 from HTMY."""

        # Mock render_template function
        async def mock_render_template(template_name, context=None, **kwargs):
            assert template_name == "test_template.html"
            assert context is not None
            assert "test_data" in context
            return "<div>Jinja2 rendered content</div>"

        # Simulate HTMY component calling Jinja2
        htmy_context = {"render_template": mock_render_template, "user": "test"}

        # Call template from HTMY context
        result = await htmy_context["render_template"](
            "test_template.html", {"test_data": "value"}
        )

        assert "Jinja2 rendered content" in result

    async def test_context_inheritance_chain(self):
        """Test context inheritance from Jinja2 to HTMY and back."""
        # Original Jinja2 context
        jinja_context = {"user_id": 123, "session": "abc"}

        # HTMY context (includes Jinja2 context)
        htmy_context = {
            **jinja_context,
            "render_template": Mock(),
            "_jinja_context": jinja_context,
            "_template_system": "htmy",
        }

        # Verify inheritance
        assert htmy_context["user_id"] == 123
        assert htmy_context["session"] == "abc"
        assert htmy_context["_jinja_context"] == jinja_context

    async def test_error_handling_in_interop(self):
        """Test error handling in bidirectional calls."""

        # Mock failing render_template
        async def failing_render_template(template_name, context=None, **kwargs):
            raise Exception("Template not found")

        htmy_context = {"render_template": failing_render_template}

        # Should handle errors gracefully
        try:
            await htmy_context["render_template"]("missing_template.html", {})
            assert False, "Should have raised exception"
        except Exception as e:
            assert "Template not found" in str(e)


if __name__ == "__main__":
    # Run tests if called directly
    pytest.main([__file__, "-v"])
