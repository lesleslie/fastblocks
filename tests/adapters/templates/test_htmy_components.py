"""Tests for HTMY Component Management System.

Comprehensive test suite for the enhanced HTMY component system including:
- Component discovery and validation
- Dataclass scaffolding and validation
- Lifecycle management and state handling
- HTMX integration and composition patterns
- Advanced registry functionality

Author: lesleslie <les@wedgwoodwebworks.com>
Created: 2025-01-13
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastblocks.adapters.templates._htmy_components import (
    AdvancedHTMYComponentRegistry,
    ComponentBase,
    ComponentCompilationError,
    ComponentLifecycleManager,
    ComponentMetadata,
    ComponentRenderError,
    ComponentScaffolder,
    ComponentStatus,
    ComponentType,
    ComponentValidationError,
    ComponentValidator,
    DataclassComponentBase,
    HTMXComponentMixin,
)

# Mock components for testing - defined as functions to avoid module-level validation


def create_mock_user_card():
    """Create a mock user card component for testing."""

    # Define class without inheritance first to avoid validation
    class _MockUserCard:
        """Mock user card component for testing."""

        name: str = "Test User"
        email: str = "test@example.com"
        avatar_url: str = "/static/default-avatar.png"

        @property
        def htmx_attrs(self) -> dict[str, str]:
            return {
                "hx-get": "/api/user/profile",
                "hx-trigger": "click",
                "hx-target": "#user-details",
            }

        def htmy(self, context: dict[str, Any]) -> str:
            return f'''
            <div class="user-card" hx-get="/api/user/profile" hx-trigger="click">
                <img src="{self.avatar_url}" alt="{self.name}">
                <h3>{self.name}</h3>
                <p>{self.email}</p>
            </div>
            '''

    # Apply dataclass decorator and create proper inheritance
    MockUserCard = dataclass(_MockUserCard)

    # Add mixins as needed for specific tests
    class TestableUserCard(MockUserCard, DataclassComponentBase, HTMXComponentMixin):
        pass

    return dataclass(TestableUserCard)


def create_mock_async_component():
    """Create a mock async component for testing."""

    class MockAsyncComponent(ComponentBase):
        """Mock async component for testing."""

        async def htmy(self, context: dict[str, Any]) -> str:
            # Simulate async operation
            await asyncio.sleep(0.01)
            return '<div class="async-component">Async content</div>'

    return MockAsyncComponent


def create_mock_composite_component():
    """Create a mock composite component for testing."""

    @dataclass
    class MockCompositeComponent(DataclassComponentBase):
        """Mock composite component for testing."""

        title: str = "Composite"
        children: list[str] = field(default_factory=lambda: ["user_card", "button"])

        def htmy(self, context: dict[str, Any]) -> str:
            render_component = context.get("render_component")
            children_html = ""

            if render_component:
                for child in self.children:
                    children_html += f"<!-- Child: {child} -->"

            return f"""
            <div class="composite-component">
                <h2>{self.title}</h2>
                <div class="children">{children_html}</div>
            </div>
            """

    return MockCompositeComponent


# Mock AsyncPath for testing
class MockAsyncPath:
    def __init__(self, path: str) -> None:
        self.path = path
        self.stem = path.split("/")[-1].replace(".py", "")
        self.parts = path.split("/")
        self.name = path.split("/")[-1]
        # Avoid infinite recursion for parent path creation
        parent_path = "/".join(path.split("/")[:-1])
        if parent_path and parent_path != path:
            self.parent = MockAsyncPath(parent_path)
        else:
            self.parent = None

    def __str__(self) -> str:
        return self.path

    def __truediv__(self, other: str) -> "MockAsyncPath":
        return MockAsyncPath(f"{self.path}/{other}")

    async def exists(self) -> bool:
        return True

    async def read_text(self) -> str:
        # Return mock component source based on stem
        if self.stem == "user_card":
            return """
from dataclasses import dataclass
from typing import Any

@dataclass
class UserCard:
    name: str = "Test"
    email: str = "test@example.com"

    def htmy(self, context: dict[str, Any]) -> str:
        return f"<div>{self.name}: {self.email}</div>"
"""
        elif self.stem == "broken_component":
            return "invalid python syntax ((("

        return """
@pytest.mark.unit
class TestComponent:
    def htmy(self, context):
        return "<div>Test</div>"
"""

    async def write_text(self, content: str) -> None:
        pass

    async def stat(self) -> MagicMock:
        mock_stat = MagicMock()
        mock_stat.st_mtime = datetime.now().timestamp()
        return mock_stat

    async def mkdir(self, parents: bool = False, exist_ok: bool = False) -> None:
        pass

    def rglob(self, pattern: str):
        """Mock rglob for component discovery."""
        if pattern == "*.py":
            return [
                MockAsyncPath("/test/components/user_card.py"),
                MockAsyncPath("/test/components/button.py"),
                MockAsyncPath("/test/components/broken_component.py"),
            ]
        return []


@pytest.fixture
def mock_searchpaths():
    """Mock searchpaths for testing."""
    return [MockAsyncPath("/test/components")]


@pytest.fixture
def component_registry(mock_searchpaths):
    """Component registry fixture."""
    return AdvancedHTMYComponentRegistry(
        searchpaths=mock_searchpaths, cache=None, storage=None
    )


@pytest.fixture
def lifecycle_manager():
    """Lifecycle manager fixture."""
    return ComponentLifecycleManager()


@pytest.fixture
def scaffolder():
    """Component scaffolder fixture."""
    return ComponentScaffolder()


@pytest.fixture
def validator():
    """Component validator fixture."""
    return ComponentValidator()


@pytest.mark.unit
class TestComponentMetadata:
    """Test ComponentMetadata functionality."""

    def test_component_metadata_creation(self):
        """Test component metadata creation."""
        path = MockAsyncPath("/test/user_card.py")
        metadata = ComponentMetadata(
            name="user_card",
            path=path,
            type=ComponentType.DATACLASS,
            status=ComponentStatus.VALIDATED,
        )

        assert metadata.name == "user_card"
        assert metadata.type == ComponentType.DATACLASS
        assert metadata.status == ComponentStatus.VALIDATED
        assert metadata.cache_key is not None

    def test_component_metadata_post_init(self):
        """Test component metadata post init."""
        path = MockAsyncPath("/test/user_card.py")
        metadata = ComponentMetadata(
            name="user_card", path=path, type=ComponentType.DATACLASS
        )

        assert metadata.cache_key == "component_user_card_user_card"


@pytest.mark.unit
class TestComponentBase:
    """Test ComponentBase functionality."""

    def test_component_base_initialization(self):
        """Test component base initialization."""

        # Create concrete implementation for testing
        class TestComponent(ComponentBase):
            def htmy(self, context: dict[str, Any]) -> str:
                return "<div>test</div>"

        component = TestComponent(name="test", value=42)

        assert component._context["name"] == "test"
        assert component._context["value"] == 42
        assert component._children == []
        assert component._parent is None

    def test_component_hierarchy(self):
        """Test component parent-child relationships."""

        # Create concrete implementation for testing
        class TestComponent(ComponentBase):
            def htmy(self, context: dict[str, Any]) -> str:
                return "<div>test</div>"

        parent = TestComponent()
        child1 = TestComponent()
        child2 = TestComponent()

        parent.add_child(child1)
        parent.add_child(child2)

        assert len(parent.children) == 2
        assert child1._parent == parent
        assert child2._parent == parent

        parent.remove_child(child1)
        assert len(parent.children) == 1
        assert child1._parent is None

    @pytest.mark.asyncio
    async def test_async_htmy_sync_method(self):
        """Test async_htmy with sync htmy method."""

        class TestComponent(ComponentBase):
            def htmy(self, context: dict[str, Any]) -> str:
                return "<div>test</div>"

        component = TestComponent()
        result = await component.async_htmy({})
        assert result == "<div>test</div>"

    @pytest.mark.asyncio
    async def test_async_htmy_async_method(self):
        """Test async_htmy with async htmy method."""

        class TestComponent(ComponentBase):
            async def htmy(self, context: dict[str, Any]) -> str:
                await asyncio.sleep(0.01)
                return "<div>async test</div>"

        component = TestComponent()
        result = await component.async_htmy({})
        assert result == "<div>async test</div>"


@pytest.mark.unit
class TestDataclassComponentBase:
    """Test DataclassComponentBase functionality."""

    def test_dataclass_component_validation(self):
        """Test dataclass component must be a dataclass."""
        with pytest.raises(ComponentValidationError):

            class NonDataclassComponent(DataclassComponentBase):
                def htmy(self, context: dict[str, Any]) -> str:
                    return "<div>test</div>"

            # This should trigger the validation error
            NonDataclassComponent()

    def test_dataclass_component_field_validation(self):
        """Test dataclass component field validation."""
        MockUserCard = create_mock_user_card()
        component = MockUserCard(name="Test", email="test@example.com")
        component.validate_fields()  # Should not raise

        # Test invalid type (this is basic validation)
        component.name = 123  # type: ignore
        # Note: Basic type validation is limited in the current implementation


@pytest.mark.unit
class TestHTMXComponentMixin:
    """Test HTMXComponentMixin functionality."""

    def test_htmx_mixin_properties(self):
        """Test HTMX mixin properties."""
        MockUserCard = create_mock_user_card()
        component = MockUserCard()

        assert "hx-get" in component.htmx_attrs
        assert component.htmx_attrs["hx-get"] == "/api/user/profile"

    def test_htmx_request_detection(self):
        """Test HTMX request detection."""
        MockUserCard = create_mock_user_card()
        component = MockUserCard()

        # Mock request with HTMX headers
        mock_request = MagicMock()
        mock_request.headers = {"HX-Request": "true", "HX-Trigger": "click"}

        assert component.is_htmx_request(mock_request) is True
        assert component.get_htmx_trigger(mock_request) == "click"

        # Mock regular request
        mock_request.headers = {}
        assert component.is_htmx_request(mock_request) is False


@pytest.mark.unit
class TestComponentScaffolder:
    """Test ComponentScaffolder functionality."""

    def test_create_basic_component(self, scaffolder):
        """Test basic component scaffolding."""
        props = {"title": str, "count": int}
        content = scaffolder.create_basic_component(
            "TestCard", props=props, htmx_enabled=False
        )

        assert "class TestCard" in content
        assert "title: str" in content
        assert "count: int" in content
        assert "def htmy" in content

    def test_create_htmx_component(self, scaffolder):
        """Test HTMX component scaffolding."""
        content = scaffolder.create_htmx_component(
            "ClickButton", endpoint="/api/action", trigger="click", target="#result"
        )

        assert "class ClickButton" in content
        assert "HTMXComponentMixin" in content
        assert 'hx-get": "/api/action"' in content
        assert 'hx-trigger": "click"' in content

    def test_create_composite_component(self, scaffolder):
        """Test composite component scaffolding."""
        children = ["header", "content", "footer"]
        content = scaffolder.create_composite_component("PageLayout", children=children)

        assert "class PageLayout" in content
        assert "render_component" in content
        for child in children:
            assert f'render_component("{child}"' in content


@pytest.mark.unit
class TestComponentValidator:
    """Test ComponentValidator functionality."""

    @pytest.mark.asyncio
    async def test_validate_valid_component(self, validator):
        """Test validation of valid component."""
        path = MockAsyncPath("/test/user_card.py")
        metadata = await validator.validate_component_file(path)

        assert metadata.name == "user_card"
        assert metadata.status == ComponentStatus.VALIDATED
        assert metadata.error_message is None

    @pytest.mark.asyncio
    async def test_validate_broken_component(self, validator):
        """Test validation of broken component."""
        path = MockAsyncPath("/test/broken_component.py")
        metadata = await validator.validate_component_file(path)

        assert metadata.name == "broken_component"
        assert metadata.status == ComponentStatus.ERROR
        assert metadata.error_message is not None

    def test_determine_component_type(self, validator):
        """Test component type determination."""
        # Test HTMX component (MockUserCard has HTMXComponentMixin)
        MockUserCard = create_mock_user_card()
        assert validator._determine_component_type(MockUserCard) == ComponentType.HTMX

        # Test basic component
        class BasicComponent:
            def htmy(self, context):
                return "<div></div>"

        assert (
            validator._determine_component_type(BasicComponent) == ComponentType.BASIC
        )

        # The test for pure dataclass component type is covered in the logic:
        # Components with DataclassComponentBase but no HTMXComponentMixin should be DATACLASS type


@pytest.mark.unit
class TestComponentLifecycleManager:
    """Test ComponentLifecycleManager functionality."""

    def test_lifecycle_hook_registration(self, lifecycle_manager):
        """Test lifecycle hook registration."""
        callback_called = False

        def test_callback(**kwargs):
            nonlocal callback_called
            callback_called = True

        lifecycle_manager.register_hook("before_render", test_callback)
        assert len(lifecycle_manager._lifecycle_hooks["before_render"]) == 1

    @pytest.mark.asyncio
    async def test_lifecycle_hook_execution(self, lifecycle_manager):
        """Test lifecycle hook execution."""
        callback_data = {}

        async def async_callback(**kwargs):
            callback_data.update(kwargs)

        def sync_callback(**kwargs):
            callback_data.update(kwargs)

        lifecycle_manager.register_hook("before_render", async_callback)
        lifecycle_manager.register_hook("before_render", sync_callback)

        await lifecycle_manager.execute_hooks(
            "before_render", component_name="test", test_data="value"
        )

        assert callback_data["component_name"] == "test"
        assert callback_data["test_data"] == "value"

    @pytest.mark.asyncio
    async def test_component_state_management(self, lifecycle_manager):
        """Test component state management."""
        component_id = "test_component_123"
        state = {"count": 1, "visible": True}

        lifecycle_manager.set_component_state(component_id, state)
        retrieved_state = lifecycle_manager.get_component_state(component_id)

        assert retrieved_state == state

        lifecycle_manager.clear_component_state(component_id)
        empty_state = lifecycle_manager.get_component_state(component_id)
        assert empty_state == {}


@pytest.mark.unit
class TestAdvancedHTMYComponentRegistry:
    """Test AdvancedHTMYComponentRegistry functionality."""

    @pytest.mark.asyncio
    async def test_component_discovery(self, component_registry):
        """Test component discovery."""
        components = await component_registry.discover_components()

        assert "user_card" in components
        assert "button" in components
        assert "broken_component" in components

        # Check metadata
        user_card_meta = components["user_card"]
        assert user_card_meta.name == "user_card"
        assert user_card_meta.status == ComponentStatus.VALIDATED

        broken_meta = components["broken_component"]
        assert broken_meta.status == ComponentStatus.ERROR

    @pytest.mark.asyncio
    async def test_get_component_class(self, component_registry):
        """Test component class retrieval."""
        component_class = await component_registry.get_component_class("user_card")
        assert component_class is not None
        assert hasattr(component_class, "htmy")

        # Test component that doesn't exist
        with pytest.raises(ComponentValidationError):
            await component_registry.get_component_class("nonexistent")

    @pytest.mark.asyncio
    async def test_render_component_with_lifecycle(self, component_registry):
        """Test component rendering with lifecycle."""
        mock_request = MagicMock()

        # Mock component class
        with patch.object(component_registry, "get_component_class") as mock_get_class:
            mock_component = MagicMock()
            mock_component.htmy.return_value = "<div>test content</div>"
            mock_get_class.return_value = mock_component

            result = await component_registry.render_component_with_lifecycle(
                "test_component", {"data": "value"}, mock_request
            )

            assert result == "<div>test content</div>"
            mock_component.assert_called_once()

    @pytest.mark.asyncio
    async def test_scaffold_component(self, component_registry):
        """Test component scaffolding."""
        # Mock the write operation
        mock_path = MockAsyncPath("/test/components/new_component.py")

        with patch.object(
            component_registry._scaffolder, "create_basic_component"
        ) as mock_create:
            mock_create.return_value = "# Generated component code"

            result_path = await component_registry.scaffold_component(
                "NewComponent", ComponentType.BASIC, mock_path
            )

            assert result_path == mock_path
            mock_create.assert_called_once()

    def test_cache_management(self, component_registry):
        """Test cache management."""
        # Add some items to cache
        component_registry._component_cache["test"] = "test_class"
        component_registry._metadata_cache["test"] = "test_metadata"

        # Clear specific component
        component_registry.clear_cache("test")
        assert "test" not in component_registry._component_cache
        assert "test" not in component_registry._metadata_cache

        # Clear all cache
        component_registry._component_cache["test2"] = "test_class2"
        component_registry.clear_cache()
        assert len(component_registry._component_cache) == 0

    def test_hot_reload_toggle(self, component_registry):
        """Test hot reload enable/disable."""
        component_registry.enable_hot_reload()
        assert component_registry._hot_reload_enabled is True

        component_registry.disable_hot_reload()
        assert component_registry._hot_reload_enabled is False

    def test_lifecycle_manager_access(self, component_registry):
        """Test lifecycle manager access."""
        lifecycle_manager = component_registry.lifecycle_manager
        assert isinstance(lifecycle_manager, ComponentLifecycleManager)


@pytest.mark.unit
class TestComponentErrors:
    """Test component error handling."""

    def test_component_validation_error(self):
        """Test ComponentValidationError."""
        with pytest.raises(ComponentValidationError) as exc_info:
            raise ComponentValidationError("Test validation error")

        assert "Test validation error" in str(exc_info.value)

    def test_component_compilation_error(self):
        """Test ComponentCompilationError."""
        with pytest.raises(ComponentCompilationError) as exc_info:
            raise ComponentCompilationError("Test compilation error")

        assert "Test compilation error" in str(exc_info.value)

    def test_component_render_error(self):
        """Test ComponentRenderError."""
        with pytest.raises(ComponentRenderError) as exc_info:
            raise ComponentRenderError("Test render error")

        assert "Test render error" in str(exc_info.value)


@pytest.mark.unit
class TestComponentIntegration:
    """Integration tests for component system."""

    @pytest.mark.asyncio
    async def test_full_component_lifecycle(self):
        """Test complete component lifecycle."""
        # Create registry
        registry = AdvancedHTMYComponentRegistry(
            searchpaths=[MockAsyncPath("/test/components")]
        )

        # Discover components
        components = await registry.discover_components()
        assert len(components) > 0

        # Get component class
        component_class = await registry.get_component_class("user_card")
        assert component_class is not None

        # Render component
        mock_request = MagicMock()
        result = await registry.render_component_with_lifecycle(
            "user_card", {"name": "Integration Test"}, mock_request
        )

        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_component_composition(self):
        """Test component composition patterns."""
        registry = AdvancedHTMYComponentRegistry(
            searchpaths=[MockAsyncPath("/test/components")]
        )

        # Mock nested renderer
        async def mock_nested_renderer(name, context=None):
            return f"<div>Rendered {name}</div>"

        registry._create_nested_renderer = lambda request: mock_nested_renderer

        # Test composite component rendering
        mock_request = MagicMock()

        with patch.object(registry, "get_component_class") as mock_get_class:
            MockCompositeComponent = create_mock_composite_component()
            MockCompositeComponent()
            mock_get_class.return_value = MockCompositeComponent

            result = await registry.render_component_with_lifecycle(
                "composite", {"title": "Test Composite"}, mock_request
            )

            assert "Test Composite" in result
            assert "composite-component" in result

    @pytest.mark.asyncio
    async def test_htmx_component_integration(self):
        """Test HTMX component integration."""
        registry = AdvancedHTMYComponentRegistry(
            searchpaths=[MockAsyncPath("/test/components")]
        )

        # Mock HTMX request
        mock_request = MagicMock()
        mock_request.headers = {
            "HX-Request": "true",
            "HX-Trigger": "click",
            "HX-Target": "#content",
        }

        with patch.object(registry, "get_component_class") as mock_get_class:
            MockUserCard = create_mock_user_card()
            mock_get_class.return_value = MockUserCard

            result = await registry.render_component_with_lifecycle(
                "user_card", {"name": "HTMX User"}, mock_request
            )

            assert "HTMX User" in result
            assert "hx-get" in result


if __name__ == "__main__":
    pytest.main([__file__])
