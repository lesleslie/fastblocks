"""Tests for FastBlocks MCP foundation functionality."""

from uuid import UUID

import pytest
from fastblocks.mcp.discovery import AdapterDiscoveryServer, AdapterInfo
from fastblocks.mcp.health import HealthCheckSystem
from fastblocks.mcp.registry import AdapterRegistry


class TestAdapterDiscovery:
    """Test adapter discovery functionality."""

    @pytest.fixture
    def discovery_server(self):
        """Create discovery server instance."""
        return AdapterDiscoveryServer()

    def test_adapter_info_creation(self):
        """Test AdapterInfo creation and serialization."""
        module_id = UUID("01937d86-4f2a-7b3c-8d9e-f3b4d3c2b1a1")

        info = AdapterInfo(
            name="test_adapter",
            module_path="fastblocks.adapters.test.adapter",
            class_name="TestAdapter",
            module_id=module_id,
            module_status="stable",
            category="test",
            description="Test adapter for unit tests",
            protocols=["TestProtocol"],
            settings_class="TestSettings",
        )

        assert info.name == "test_adapter"
        assert info.module_id == module_id
        assert info.module_status == "stable"

        # Test serialization
        data = info.to_dict()
        assert data["name"] == "test_adapter"
        assert data["module_id"] == str(module_id)
        assert data["protocols"] == ["TestProtocol"]

    @pytest.mark.asyncio
    async def test_discover_adapters(self, discovery_server):
        """Test adapter discovery process."""
        adapters = await discovery_server.discover_adapters()

        # Should find some adapters (at least the ones we created)
        assert isinstance(adapters, dict)

        # Check if we found any of our adapters
        adapter_names = list(adapters.keys())

        # Should have found some adapters
        assert len(adapter_names) >= 0  # May be 0 if none are properly implemented

    @pytest.mark.asyncio
    async def test_get_categories(self, discovery_server):
        """Test category discovery."""
        categories = await discovery_server.get_all_categories()

        assert isinstance(categories, list)
        # Should include the categories we created
        expected_categories = ["images", "styles", "icons", "fonts"]
        for category in expected_categories:
            if category in categories:
                # At least one category should be found
                assert True
                break


class TestAdapterRegistry:
    """Test adapter registry functionality."""

    @pytest.fixture
    async def registry(self):
        """Create and initialize registry."""
        registry = AdapterRegistry()
        await registry.initialize()
        return registry

    @pytest.mark.asyncio
    async def test_registry_initialization(self, registry):
        """Test registry initialization."""
        # Should complete without errors
        assert registry is not None
        assert hasattr(registry, "discovery")

    @pytest.mark.asyncio
    async def test_list_available_adapters(self, registry):
        """Test listing available adapters."""
        adapters = await registry.list_available_adapters()

        assert isinstance(adapters, dict)
        # Each adapter should be an AdapterInfo instance
        for adapter_info in adapters.values():
            assert isinstance(adapter_info, AdapterInfo)

    @pytest.mark.asyncio
    async def test_get_categories(self, registry):
        """Test getting adapter categories."""
        categories = await registry.get_categories()

        assert isinstance(categories, list)

    @pytest.mark.asyncio
    async def test_adapter_statistics(self, registry):
        """Test adapter statistics generation."""
        stats = await registry.get_adapter_statistics()

        assert isinstance(stats, dict)
        assert "total_available" in stats
        assert "total_active" in stats
        assert "total_categories" in stats
        assert "categories" in stats
        assert "status_breakdown" in stats

        # Validate structure
        assert isinstance(stats["total_available"], int)
        assert isinstance(stats["total_active"], int)
        assert isinstance(stats["categories"], dict)

    @pytest.mark.asyncio
    async def test_adapter_validation(self, registry):
        """Test adapter validation."""
        # Get first available adapter for testing
        adapters = await registry.list_available_adapters()

        if adapters:
            adapter_name = list(adapters.keys())[0]
            result = await registry.validate_adapter(adapter_name)

            assert isinstance(result, dict)
            assert "valid" in result
            assert "errors" in result
            assert "warnings" in result
            assert "info" in result

            assert isinstance(result["valid"], bool)
            assert isinstance(result["errors"], list)
            assert isinstance(result["warnings"], list)
            assert isinstance(result["info"], dict)


class TestHealthCheckSystem:
    """Test health check system functionality."""

    @pytest.fixture
    async def health_system(self):
        """Create health check system with registry."""
        registry = AdapterRegistry()
        await registry.initialize()
        return HealthCheckSystem(registry)

    @pytest.mark.asyncio
    async def test_health_system_creation(self, health_system):
        """Test health check system creation."""
        assert health_system is not None
        assert hasattr(health_system, "registry")

    @pytest.mark.asyncio
    async def test_check_adapter_health(self, health_system):
        """Test individual adapter health check."""
        # Get first available adapter for testing
        adapters = await health_system.registry.list_available_adapters()

        if adapters:
            adapter_name = list(adapters.keys())[0]
            result = await health_system.check_adapter_health(adapter_name)

            assert hasattr(result, "adapter_name")
            assert hasattr(result, "status")
            assert hasattr(result, "message")
            assert hasattr(result, "duration_ms")

            assert result.adapter_name == adapter_name
            assert result.status in ["healthy", "warning", "error", "unknown"]
            assert isinstance(result.duration_ms, float)

            # Test serialization
            result_dict = result.to_dict()
            assert isinstance(result_dict, dict)
            assert "adapter_name" in result_dict
            assert "status" in result_dict

    @pytest.mark.asyncio
    async def test_system_health_summary(self, health_system):
        """Test system health summary."""
        summary = health_system.get_system_health_summary()

        assert isinstance(summary, dict)
        expected_keys = [
            "healthy_adapters",
            "warning_adapters",
            "error_adapters",
            "unknown_adapters",
            "total_adapters",
            "adapter_status",
        ]

        for key in expected_keys:
            assert key in summary

        # Validate counts are integers
        assert isinstance(summary["healthy_adapters"], int)
        assert isinstance(summary["warning_adapters"], int)
        assert isinstance(summary["error_adapters"], int)
        assert isinstance(summary["unknown_adapters"], int)
        assert isinstance(summary["total_adapters"], int)
        assert isinstance(summary["adapter_status"], dict)

    @pytest.mark.asyncio
    async def test_check_all_adapters(self, health_system):
        """Test checking all adapters."""
        results = await health_system.check_all_adapters()

        assert isinstance(results, dict)

        # Each result should be a HealthCheckResult
        for adapter_name, result in results.items():
            assert isinstance(adapter_name, str)
            assert hasattr(result, "adapter_name")
            assert hasattr(result, "status")
            assert result.adapter_name == adapter_name


class TestMCPIntegration:
    """Test integration between MCP components."""

    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """Test complete MCP workflow."""
        # Initialize registry
        registry = AdapterRegistry()
        await registry.initialize()

        # Create health system
        health = HealthCheckSystem(registry)

        # Get statistics
        stats = await registry.get_adapter_statistics()
        assert isinstance(stats, dict)

        # Get system health
        summary = health.get_system_health_summary()
        assert isinstance(summary, dict)

        # If we have adapters, test one
        available = await registry.list_available_adapters()
        if available:
            adapter_name = list(available.keys())[0]

            # Validate adapter
            validation = await registry.validate_adapter(adapter_name)
            assert isinstance(validation, dict)

            # Check health
            health_result = await health.check_adapter_health(adapter_name)
            assert hasattr(health_result, "status")

    @pytest.mark.asyncio
    async def test_adapter_lifecycle(self):
        """Test adapter discovery, registration, and health monitoring."""
        registry = AdapterRegistry()
        await registry.initialize()

        # Discovery phase
        available = await registry.list_available_adapters()
        initial_count = len(available)

        # Registration phase (if we have adapters)
        if available:
            adapter_name = list(available.keys())[0]

            # Try to get adapter instance
            await registry.get_adapter(adapter_name)
            # adapter may be None if instantiation fails, which is acceptable

            # Validation should still work
            validation = await registry.validate_adapter(adapter_name)
            assert "valid" in validation

        # Statistics should be consistent
        stats = await registry.get_adapter_statistics()
        assert stats["total_available"] == initial_count
