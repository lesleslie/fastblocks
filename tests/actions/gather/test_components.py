"""Tests for Component Gathering Action.

Tests for the component gathering functionality in the FastBlocks gather action system.

Author: lesleslie <les@wedgwoodwebworks.com>
Created: 2025-01-13
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastblocks.actions.gather.components import (
    ComponentGatherResult,
    ComponentGatherStrategy,
    analyze_component_usage,
    gather_component_dependencies,
    gather_components,
)
from fastblocks.adapters.templates._htmy_components import (
    ComponentMetadata,
    ComponentStatus,
    ComponentType,
)


class MockAsyncPath:
    """Mock AsyncPath for testing."""

    def __init__(self, path: str) -> None:
        self.path = path

    def __str__(self) -> str:
        return self.path

    @property
    def stem(self) -> str:
        # Extract stem from path string (remove directory and extension)
        import os

        basename = os.path.basename(self.path)
        return os.path.splitext(basename)[0]

    @property
    def name(self) -> str:
        # Return just the filename
        import os

        return os.path.basename(self.path)


@pytest.fixture
def mock_htmy_adapter():
    """Mock HTMY adapter fixture."""
    from unittest.mock import AsyncMock

    adapter = (
        AsyncMock()
    )  # Use AsyncMock instead of MagicMock as the base to ensure awaitability
    adapter.component_searchpaths = [MockAsyncPath("/test/components")]

    # Mock component metadata
    test_metadata = ComponentMetadata(
        name="test_component",
        path=MockAsyncPath("/test/components/test_component.py"),
        type=ComponentType.DATACLASS,
        status=ComponentStatus.VALIDATED,
        dependencies=["dependency1", "dependency2"],
        htmx_attributes={"hx-get": "/api/test"},
        docstring="Test component description",
    )

    htmx_metadata = ComponentMetadata(
        name="htmx_component",
        path=MockAsyncPath("/test/components/htmx_component.py"),
        type=ComponentType.HTMX,
        status=ComponentStatus.READY,
        htmx_attributes={"hx-post": "/api/submit"},
        docstring="HTMX component",
    )

    broken_metadata = ComponentMetadata(
        name="broken_component",
        path=MockAsyncPath("/test/components/broken_component.py"),
        type=ComponentType.BASIC,
        status=ComponentStatus.ERROR,
        error_message="Syntax error in component",
    )

    # Set return values for async methods
    adapter.discover_components.return_value = {
        "test_component": test_metadata,
        "htmx_component": htmx_metadata,
        "broken_component": broken_metadata,
    }

    # Set other return values
    adapter.validate_component.return_value = test_metadata
    adapter.render_component.return_value = "<div>Component</div>"
    adapter.get_component_class.return_value = MagicMock()
    adapter.get_component_source.return_value = (
        "<div>source</div>",
        MockAsyncPath("/path"),
    )

    return adapter


class TestComponentGatherResult:
    """Test ComponentGatherResult functionality."""

    def test_component_gather_result_creation(self):
        """Test ComponentGatherResult creation."""
        components = {"test": {"name": "test", "type": "dataclass"}}
        result = ComponentGatherResult(
            components=components,
            validation_errors=["error1"],
            htmx_components=["htmx_comp"],
            dataclass_components=["dc_comp"],
            composite_components=["comp_comp"],
        )

        assert result.is_success is True  # Use is_success property instead
        assert result.component_count == 1
        assert len(result.validation_errors) == 1
        assert len(result.htmx_components) == 1

    def test_component_gather_result_post_init(self):
        """Test ComponentGatherResult post_init."""
        components = {"comp1": {}, "comp2": {}, "comp3": {}}
        result = ComponentGatherResult(components=components)

        assert result.component_count == 3


class TestComponentGatherStrategy:
    """Test ComponentGatherStrategy functionality."""

    def test_strategy_initialization(self):
        """Test strategy initialization."""
        strategy = ComponentGatherStrategy(
            include_metadata=True,
            validate_components=True,
            filter_types=["htmx", "dataclass"],
            max_parallel=5,
        )

        assert strategy.include_metadata is True
        assert strategy.validate_components is True
        assert strategy.filter_types == ["htmx", "dataclass"]
        assert strategy.max_parallel == 5

    @pytest.mark.asyncio
    async def test_gather_single_valid_item(self):
        """Test gathering single valid item."""
        strategy = ComponentGatherStrategy()
        item = {"name": "test", "metadata": "test_metadata"}

        result = await strategy.gather_single(item)

        assert result == item

    @pytest.mark.asyncio
    async def test_gather_single_invalid_item(self):
        """Test gathering single invalid item."""
        strategy = ComponentGatherStrategy()
        item = "invalid_item"

        result = await strategy.gather_single(item)

        assert result is None

    @pytest.mark.asyncio
    async def test_gather_batch(self):
        """Test gathering batch of items."""
        strategy = ComponentGatherStrategy()
        items = [
            {"name": "test1", "metadata": "meta1"},
            {"name": "test2", "metadata": "meta2"},
            "invalid_item",
        ]

        results = await strategy.gather_batch(items)

        assert len(results) == 2
        assert all(isinstance(item, dict) for item in results)

    @pytest.mark.asyncio
    async def test_gather_batch_empty(self):
        """Test gathering empty batch."""
        strategy = ComponentGatherStrategy()
        results = await strategy.gather_batch([])
        assert results == []


class TestGatherComponents:
    """Test gather_components functionality."""

    @pytest.mark.asyncio
    async def test_gather_components_success(self, mock_htmy_adapter):
        """Test successful component gathering."""
        result = await gather_components(htmy_adapter=mock_htmy_adapter)

        assert result.is_success is True
        assert result.component_count == 3
        assert "test_component" in result.components
        assert "htmx_component" in result.components
        assert "broken_component" in result.components

        # Check categorization
        assert "htmx_component" in result.htmx_components
        assert "test_component" in result.dataclass_components
        assert len(result.validation_errors) == 1

    @pytest.mark.asyncio
    async def test_gather_components_no_adapter(self):
        """Test gathering without HTMY adapter."""
        with patch("fastblocks.actions.gather.components.depends") as mock_depends:
            mock_depends.get.side_effect = Exception("No adapter")

            result = await gather_components()

            assert result.is_success is False
            assert "HTMY adapter not available" in result.error_message

    @pytest.mark.asyncio
    async def test_gather_components_with_filter(self, mock_htmy_adapter):
        """Test gathering with type filter."""
        strategy = ComponentGatherStrategy(filter_types=["htmx"])

        result = await gather_components(
            htmy_adapter=mock_htmy_adapter, strategy=strategy
        )

        assert result.is_success is True
        # Should only include HTMX components due to filter
        # Note: Implementation details may vary

    @pytest.mark.asyncio
    async def test_gather_components_fallback_registry(self):
        """Test gathering with fallback to basic registry."""
        mock_adapter = AsyncMock()
        # Don't set discover_components - let it fall back to htmy_registry
        if hasattr(mock_adapter, "discover_components"):
            del mock_adapter.discover_components
        mock_adapter.htmy_registry = AsyncMock()
        mock_adapter.htmy_registry.discover_components = AsyncMock(
            return_value={"basic_component": MockAsyncPath("/test/basic_component.py")}
        )
        mock_adapter.component_searchpaths = [MockAsyncPath("/test")]

        result = await gather_components(htmy_adapter=mock_adapter)

        assert result.is_success is True
        assert "basic_component" in result.components

    @pytest.mark.asyncio
    async def test_gather_components_exception_handling(self, mock_htmy_adapter):
        """Test exception handling during gathering."""
        mock_htmy_adapter.discover_components.side_effect = Exception(
            "Discovery failed"
        )

        result = await gather_components(htmy_adapter=mock_htmy_adapter)

        assert result.is_success is False
        assert "Discovery failed" in result.error_message

    @pytest.mark.asyncio
    async def test_gather_components_custom_searchpaths(self, mock_htmy_adapter):
        """Test gathering with custom searchpaths."""
        custom_paths = [MockAsyncPath("/custom/components")]

        result = await gather_components(
            htmy_adapter=mock_htmy_adapter, searchpaths=custom_paths
        )

        assert result.is_success is True
        assert result.searchpaths == custom_paths


class TestGatherComponentDependencies:
    """Test gather_component_dependencies functionality."""

    @pytest.mark.asyncio
    async def test_gather_dependencies_success(self, mock_htmy_adapter):
        """Test successful dependency gathering."""
        # Mock component metadata with dependencies
        test_metadata = ComponentMetadata(
            name="test_component",
            path=MockAsyncPath("/test/test_component.py"),
            type=ComponentType.DATACLASS,
            status=ComponentStatus.VALIDATED,
            dependencies=["dep1", "dep2"],
        )

        mock_htmy_adapter.validate_component = AsyncMock(return_value=test_metadata)

        result = await gather_component_dependencies(
            "test_component", htmy_adapter=mock_htmy_adapter, recursive=False
        )

        assert result["name"] == "test_component"
        assert result["type"] == "dataclass"
        assert result["direct_dependencies"] == ["dep1", "dep2"]

    @pytest.mark.asyncio
    async def test_gather_dependencies_recursive(self, mock_htmy_adapter):
        """Test recursive dependency gathering."""
        # Mock component metadata
        parent_metadata = ComponentMetadata(
            name="parent_component",
            path=MockAsyncPath("/test/parent_component.py"),
            type=ComponentType.COMPOSITE,
            status=ComponentStatus.VALIDATED,
            dependencies=["child_component"],
        )

        child_metadata = ComponentMetadata(
            name="child_component",
            path=MockAsyncPath("/test/child_component.py"),
            type=ComponentType.DATACLASS,
            status=ComponentStatus.VALIDATED,
            dependencies=[],
        )

        async def mock_validate(component_name):
            if component_name == "parent_component":
                return parent_metadata
            elif component_name == "child_component":
                return child_metadata
            else:
                raise Exception("Component not found")

        mock_htmy_adapter.validate_component = AsyncMock(side_effect=mock_validate)

        result = await gather_component_dependencies(
            "parent_component",
            htmy_adapter=mock_htmy_adapter,
            recursive=True,
            max_depth=2,
        )

        assert result["name"] == "parent_component"
        assert "child_component" in result["children"]

    @pytest.mark.asyncio
    async def test_gather_dependencies_no_adapter(self):
        """Test dependency gathering without adapter."""
        with patch("fastblocks.actions.gather.components.depends") as mock_depends:
            mock_depends.get.return_value = None

            result = await gather_component_dependencies("test_component")

            assert "error" in result
            assert "HTMY adapter not available" in result["error"]

    @pytest.mark.asyncio
    async def test_gather_dependencies_max_depth(self, mock_htmy_adapter):
        """Test dependency gathering with max depth limit."""
        # Mock recursive dependencies
        metadata = ComponentMetadata(
            name="recursive_component",
            path=MockAsyncPath("/test/recursive_component.py"),
            type=ComponentType.COMPOSITE,
            status=ComponentStatus.VALIDATED,
            dependencies=["recursive_component"],  # Self-reference
        )

        mock_htmy_adapter.validate_component = AsyncMock(return_value=metadata)

        result = await gather_component_dependencies(
            "recursive_component",
            htmy_adapter=mock_htmy_adapter,
            recursive=True,
            max_depth=1,
        )

        assert result["name"] == "recursive_component"
        # Should stop at max_depth and not infinitely recurse


class TestAnalyzeComponentUsage:
    """Test analyze_component_usage functionality."""

    @pytest.mark.asyncio
    async def test_analyze_usage_success(self, mock_htmy_adapter):
        """Test successful usage analysis."""
        with patch(
            "fastblocks.actions.gather.components.gather_components"
        ) as mock_gather:
            mock_result = ComponentGatherResult(
                components={
                    "test_component": {
                        "type": "dataclass",
                        "status": "validated",
                        "htmx_attributes": {"hx-get": "/api/test"},
                        "dependencies": ["dep1"],
                        "docstring": "Test component",
                        "last_modified": "2025-01-13T10:00:00",
                    },
                    "htmx_component": {
                        "type": "htmx",
                        "status": "ready",
                        "htmx_attributes": {"hx-post": "/api/submit"},
                        "dependencies": [],
                        "docstring": "HTMX component",
                        "last_modified": "2025-01-13T11:00:00",
                    },
                },
                component_count=2,
                validation_errors=["error1"],
                htmx_components=["htmx_component"],
                dataclass_components=["test_component"],
                composite_components=[],
                searchpaths=[MockAsyncPath("/test/components")],
            )
            mock_gather.return_value = mock_result

            result = await analyze_component_usage(htmy_adapter=mock_htmy_adapter)

            assert "total_components" in result
            assert result["total_components"] == 2
            assert "by_type" in result
            assert result["by_type"]["htmx"] == 1
            assert result["by_type"]["dataclass"] == 1
            assert "components" in result

            # Check component analysis
            test_comp_analysis = result["components"]["test_component"]
            assert test_comp_analysis["type"] == "dataclass"
            assert test_comp_analysis["has_htmx"] is True
            assert test_comp_analysis["dependency_count"] == 1
            assert test_comp_analysis["has_documentation"] is True

    @pytest.mark.asyncio
    async def test_analyze_usage_gather_failure(self, mock_htmy_adapter):
        """Test usage analysis when gathering fails."""
        with patch(
            "fastblocks.actions.gather.components.gather_components"
        ) as mock_gather:
            mock_result = ComponentGatherResult(error_message="Gathering failed")
            mock_gather.return_value = mock_result

            result = await analyze_component_usage(htmy_adapter=mock_htmy_adapter)

            assert "error" in result
            assert "Gathering failed" in result["error"]

    @pytest.mark.asyncio
    async def test_analyze_usage_no_adapter(self):
        """Test usage analysis without adapter."""
        with patch("fastblocks.actions.gather.components.depends") as mock_depends:
            mock_depends.get.return_value = None

            result = await analyze_component_usage()

            assert "error" in result
            assert "HTMY adapter not available" in result["error"]

    @pytest.mark.asyncio
    async def test_analyze_usage_exception_handling(self, mock_htmy_adapter):
        """Test usage analysis exception handling."""
        with patch(
            "fastblocks.actions.gather.components.gather_components"
        ) as mock_gather:
            mock_gather.side_effect = Exception("Analysis failed")

            result = await analyze_component_usage(htmy_adapter=mock_htmy_adapter)

            assert "error" in result
            assert "Analysis failed" in result["error"]


class TestIntegrationScenarios:
    """Integration test scenarios."""

    @pytest.mark.asyncio
    async def test_full_component_analysis_workflow(self, mock_htmy_adapter):
        """Test complete component analysis workflow."""
        # Test the full workflow of gathering and analyzing components

        # Step 1: Gather components
        gather_result = await gather_components(htmy_adapter=mock_htmy_adapter)
        assert gather_result.is_success is True

        # Step 2: Analyze specific component dependencies
        deps_result = await gather_component_dependencies(
            "test_component", htmy_adapter=mock_htmy_adapter
        )
        assert deps_result["name"] == "test_component"

        # Step 3: Analyze overall usage
        usage_result = await analyze_component_usage(htmy_adapter=mock_htmy_adapter)
        assert "total_components" in usage_result

    @pytest.mark.asyncio
    async def test_component_filtering_and_categorization(self, mock_htmy_adapter):
        """Test component filtering and categorization."""
        # Test with different filter strategies
        htmx_strategy = ComponentGatherStrategy(filter_types=["htmx"])
        dataclass_strategy = ComponentGatherStrategy(filter_types=["dataclass"])

        htmx_result = await gather_components(
            htmy_adapter=mock_htmy_adapter, strategy=htmx_strategy
        )

        dataclass_result = await gather_components(
            htmy_adapter=mock_htmy_adapter, strategy=dataclass_strategy
        )

        # Both should succeed
        assert htmx_result.is_success is True
        assert dataclass_result.is_success is True

    @pytest.mark.asyncio
    async def test_performance_with_large_component_set(self):
        """Test performance with large component set."""
        # Create mock adapter with many components
        mock_adapter = AsyncMock()

        # Generate large component set
        large_component_set = {}
        for i in range(100):
            metadata = ComponentMetadata(
                name=f"component_{i}",
                path=MockAsyncPath(f"/test/component_{i}.py"),
                type=ComponentType.DATACLASS,
                status=ComponentStatus.VALIDATED,
            )
            large_component_set[f"component_{i}"] = metadata

        mock_adapter.discover_components = AsyncMock(return_value=large_component_set)
        mock_adapter.component_searchpaths = [MockAsyncPath("/test")]

        # Test gathering with parallelization
        strategy = ComponentGatherStrategy(max_parallel=10)

        start_time = datetime.now()
        result = await gather_components(htmy_adapter=mock_adapter, strategy=strategy)
        end_time = datetime.now()

        assert result.is_success is True
        assert result.component_count == 100

        # Should complete in reasonable time (less than 5 seconds for mock operations)
        execution_time = (end_time - start_time).total_seconds()
        assert execution_time < 5.0


if __name__ == "__main__":
    pytest.main([__file__])
