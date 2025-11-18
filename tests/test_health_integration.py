"""Tests for ACB HealthService integration.

This module tests the bridge between FastBlocks components and ACB's comprehensive
health monitoring system.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastblocks._health_integration import (
    ACB_HEALTH_AVAILABLE,
    CacheHealthCheck,
    DatabaseHealthCheck,
    FastBlocksHealthCheck,
    RoutesHealthCheck,
    TemplatesHealthCheck,
    get_fastblocks_health_summary,
    register_fastblocks_health_checks,
)


@pytest.fixture
def mock_health_service():
    """Mock ACB HealthService."""
    service = MagicMock()
    service.register_component = AsyncMock()
    service.get_component_health = AsyncMock()
    return service


@pytest.fixture
def mock_templates_adapter():
    """Mock templates adapter with required attributes."""
    templates = MagicMock()
    templates.app = MagicMock()
    templates.app.env = MagicMock()
    templates.app.env.loader = MagicMock()
    return templates


@pytest.fixture
def mock_cache_adapter():
    """Mock cache adapter with operations."""
    cache = AsyncMock()
    cache.set = AsyncMock()
    cache.get = AsyncMock(return_value="health_check_ok")
    cache.delete = AsyncMock()
    cache.get_stats = AsyncMock()
    return cache


@pytest.fixture
def mock_routes_adapter():
    """Mock routes adapter with routes."""
    routes = MagicMock()
    routes.routes = ["route1", "route2", "route3"]
    return routes


@pytest.fixture
def mock_sql_adapter():
    """Mock SQL adapter for database checks."""
    sql = AsyncMock()
    sql.execute = AsyncMock()
    sql.get_connection_info = AsyncMock(return_value={"pool_size": 10})
    return sql


@pytest.mark.asyncio
@pytest.mark.skipif(not ACB_HEALTH_AVAILABLE, reason="ACB HealthService not available")
@pytest.mark.integration
async def test_templates_health_check_healthy(mock_templates_adapter):
    """Test templates health check when system is healthy."""
    from acb.services.health import HealthCheckType, HealthStatus

    with patch("fastblocks._health_integration.depends.get") as mock_depends:
        mock_depends.side_effect = lambda name: (
            mock_templates_adapter if name == "templates" else MagicMock()
        )

        check = TemplatesHealthCheck()
        result = await check._perform_health_check(HealthCheckType.READINESS)

        assert result.status == HealthStatus.HEALTHY
        assert result.component_id == "templates"
        assert result.component_name == "Template System"
        assert "operational" in result.message.lower()
        assert result.details.get("jinja_env_initialized") is True
        assert result.details.get("loader_available") is True


@pytest.mark.asyncio
@pytest.mark.skipif(not ACB_HEALTH_AVAILABLE, reason="ACB HealthService not available")
@pytest.mark.integration
async def test_templates_health_check_degraded():
    """Test templates health check when adapter not initialized."""
    from acb.services.health import HealthCheckType, HealthStatus

    with patch("fastblocks._health_integration.depends.get") as mock_depends:
        mock_depends.return_value = None  # Templates adapter not available

        check = TemplatesHealthCheck()
        result = await check._perform_health_check(HealthCheckType.READINESS)

        assert result.status == HealthStatus.DEGRADED
        assert "not initialized" in result.message.lower()


@pytest.mark.asyncio
@pytest.mark.skipif(not ACB_HEALTH_AVAILABLE, reason="ACB HealthService not available")
@pytest.mark.integration
async def test_cache_health_check_healthy(mock_cache_adapter):
    """Test cache health check when system is healthy."""
    from acb.services.health import HealthCheckType, HealthStatus

    with patch("fastblocks._health_integration.depends.get") as mock_depends:
        mock_depends.return_value = mock_cache_adapter

        check = CacheHealthCheck()
        result = await check._perform_health_check(HealthCheckType.READINESS)

        assert result.status == HealthStatus.HEALTHY
        assert result.component_id == "cache"
        assert result.component_name == "Cache System"
        assert "operational" in result.message.lower()
        assert result.details.get("write_test") == "passed"
        assert result.details.get("read_test") == "passed"

        # Verify cache operations were called
        mock_cache_adapter.set.assert_called_once()
        mock_cache_adapter.get.assert_called_once()
        mock_cache_adapter.delete.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.skipif(not ACB_HEALTH_AVAILABLE, reason="ACB HealthService not available")
@pytest.mark.integration
async def test_cache_health_check_degraded():
    """Test cache health check when cache not available."""
    from acb.services.health import HealthCheckType, HealthStatus

    with patch("fastblocks._health_integration.depends.get") as mock_depends:
        mock_depends.return_value = None  # Cache adapter not available

        check = CacheHealthCheck()
        result = await check._perform_health_check(HealthCheckType.READINESS)

        assert result.status == HealthStatus.DEGRADED
        assert "not available" in result.message.lower()
        assert result.details.get("reason") == "cache_disabled_or_not_configured"


@pytest.mark.asyncio
@pytest.mark.skipif(not ACB_HEALTH_AVAILABLE, reason="ACB HealthService not available")
@pytest.mark.integration
async def test_routes_health_check_healthy(mock_routes_adapter):
    """Test routes health check when system is healthy."""
    from acb.services.health import HealthCheckType, HealthStatus

    with patch("fastblocks._health_integration.depends.get") as mock_depends:
        mock_depends.return_value = mock_routes_adapter

        check = RoutesHealthCheck()
        result = await check._perform_health_check(HealthCheckType.READINESS)

        assert result.status == HealthStatus.HEALTHY
        assert result.component_id == "routes"
        assert result.component_name == "Routing System"
        assert "3 routes registered" in result.message
        assert result.details.get("route_count") == 3


@pytest.mark.asyncio
@pytest.mark.skipif(not ACB_HEALTH_AVAILABLE, reason="ACB HealthService not available")
@pytest.mark.integration
async def test_routes_health_check_degraded_no_routes():
    """Test routes health check when no routes registered."""
    from acb.services.health import HealthCheckType, HealthStatus

    mock_routes = MagicMock()
    mock_routes.routes = []

    with patch("fastblocks._health_integration.depends.get") as mock_depends:
        mock_depends.return_value = mock_routes

        check = RoutesHealthCheck()
        result = await check._perform_health_check(HealthCheckType.READINESS)

        assert result.status == HealthStatus.DEGRADED
        assert "no routes registered" in result.message.lower()
        assert result.details.get("route_count") == 0


@pytest.mark.asyncio
@pytest.mark.skipif(not ACB_HEALTH_AVAILABLE, reason="ACB HealthService not available")
@pytest.mark.integration
async def test_database_health_check_healthy(mock_sql_adapter):
    """Test database health check when system is healthy."""
    from acb.services.health import HealthCheckType, HealthStatus

    with patch("fastblocks._health_integration.depends.get") as mock_depends:
        mock_depends.return_value = mock_sql_adapter

        check = DatabaseHealthCheck()
        result = await check._perform_health_check(HealthCheckType.READINESS)

        assert result.status == HealthStatus.HEALTHY
        assert result.component_id == "database"
        assert result.component_name == "Database"
        assert "operational" in result.message.lower()
        assert result.details.get("connectivity_test") == "passed"

        # Verify database query was executed
        mock_sql_adapter.execute.assert_called_once_with("SELECT 1")


@pytest.mark.asyncio
@pytest.mark.skipif(not ACB_HEALTH_AVAILABLE, reason="ACB HealthService not available")
@pytest.mark.integration
async def test_database_health_check_degraded():
    """Test database health check when adapter not configured."""
    from acb.services.health import HealthCheckType, HealthStatus

    with patch("fastblocks._health_integration.depends.get") as mock_depends:
        mock_depends.return_value = None  # SQL adapter not available

        check = DatabaseHealthCheck()
        result = await check._perform_health_check(HealthCheckType.READINESS)

        assert result.status == HealthStatus.DEGRADED
        assert "not configured" in result.message.lower()
        assert result.details.get("reason") == "sql_adapter_not_available"


@pytest.mark.asyncio
@pytest.mark.skipif(not ACB_HEALTH_AVAILABLE, reason="ACB HealthService not available")
@pytest.mark.integration
async def test_register_fastblocks_health_checks(mock_health_service):
    """Test registration of all FastBlocks health checks."""
    with patch("fastblocks._health_integration.depends.get") as mock_depends:
        mock_depends.return_value = mock_health_service

        result = await register_fastblocks_health_checks()

        assert result is True
        assert mock_health_service.register_component.call_count == 4

        # Verify each health check type was registered
        registered_types = [
            call.args[0].__class__.__name__
            for call in mock_health_service.register_component.call_args_list
        ]
        assert "TemplatesHealthCheck" in registered_types
        assert "CacheHealthCheck" in registered_types
        assert "RoutesHealthCheck" in registered_types
        assert "DatabaseHealthCheck" in registered_types


@pytest.mark.asyncio
@pytest.mark.skipif(not ACB_HEALTH_AVAILABLE, reason="ACB HealthService not available")
@pytest.mark.integration
async def test_register_health_checks_service_unavailable():
    """Test graceful degradation when HealthService unavailable."""
    with patch("fastblocks._health_integration.depends.get") as mock_depends:
        mock_depends.return_value = None  # HealthService not available

        result = await register_fastblocks_health_checks()

        assert result is False


@pytest.mark.asyncio
@pytest.mark.skipif(not ACB_HEALTH_AVAILABLE, reason="ACB HealthService not available")
@pytest.mark.integration
async def test_get_health_summary_all_healthy(mock_health_service):
    """Test health summary when all components are healthy."""
    # Mock health check results
    mock_result = MagicMock()
    mock_result.to_dict.return_value = {
        "status": "healthy",
        "message": "Component operational",
    }
    mock_health_service.get_component_health = AsyncMock(return_value=mock_result)

    with patch("fastblocks._health_integration.depends.get") as mock_depends:
        mock_depends.return_value = mock_health_service

        summary = await get_fastblocks_health_summary()

        assert summary["status"] == "healthy"
        assert "healthy" in summary["message"].lower()
        assert "templates" in summary["components"]
        assert "cache" in summary["components"]
        assert "routes" in summary["components"]
        assert "database" in summary["components"]


@pytest.mark.asyncio
@pytest.mark.skipif(not ACB_HEALTH_AVAILABLE, reason="ACB HealthService not available")
@pytest.mark.integration
async def test_get_health_summary_degraded(mock_health_service):
    """Test health summary when some components are degraded."""

    async def mock_get_health(component_id: str):
        result = MagicMock()
        if component_id == "cache":
            result.to_dict.return_value = {
                "status": "degraded",
                "message": "Cache unavailable",
            }
        else:
            result.to_dict.return_value = {
                "status": "healthy",
                "message": "Component operational",
            }
        return result

    mock_health_service.get_component_health = mock_get_health

    with patch("fastblocks._health_integration.depends.get") as mock_depends:
        mock_depends.return_value = mock_health_service

        summary = await get_fastblocks_health_summary()

        assert summary["status"] == "degraded"
        assert summary["components"]["cache"]["status"] == "degraded"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_health_checks_without_acb():
    """Test graceful degradation when ACB HealthService not available."""
    if ACB_HEALTH_AVAILABLE:
        pytest.skip("ACB HealthService is available")

    # Registration should return False
    result = await register_fastblocks_health_checks()
    assert result is False

    # Summary should indicate unavailability
    summary = await get_fastblocks_health_summary()
    assert summary["status"] == "unknown"
    assert "not available" in summary["message"].lower()
    assert summary["components"] == {}


@pytest.mark.asyncio
@pytest.mark.skipif(not ACB_HEALTH_AVAILABLE, reason="ACB HealthService not available")
@pytest.mark.integration
async def test_base_health_check():
    """Test FastBlocksHealthCheck base class."""
    from acb.services.health import HealthCheckType, HealthStatus

    check = FastBlocksHealthCheck(component_id="test", component_name="Test Component")

    assert check.component_id == "test"
    assert check.component_name == "Test Component"

    result = await check._perform_health_check(HealthCheckType.READINESS)

    assert result.status == HealthStatus.HEALTHY
    assert result.component_id == "test"
    assert result.component_name == "Test Component"
    assert "operational" in result.message.lower()


@pytest.mark.asyncio
@pytest.mark.skipif(not ACB_HEALTH_AVAILABLE, reason="ACB HealthService not available")
@pytest.mark.integration
async def test_cache_health_check_with_stats(mock_cache_adapter):
    """Test cache health check includes stats when available."""
    from acb.services.health import HealthCheckType

    stats = MagicMock()
    stats.hit_ratio = 0.85
    mock_cache_adapter.get_stats = AsyncMock(return_value=stats)

    with patch("fastblocks._health_integration.depends.get") as mock_depends:
        mock_depends.return_value = mock_cache_adapter

        check = CacheHealthCheck()
        result = await check._perform_health_check(HealthCheckType.READINESS)

        assert result.details.get("cache_hit_ratio") == 0.85


@pytest.mark.asyncio
@pytest.mark.skipif(not ACB_HEALTH_AVAILABLE, reason="ACB HealthService not available")
@pytest.mark.integration
async def test_cache_health_check_operation_failure(mock_cache_adapter):
    """Test cache health check when operations fail."""
    from acb.services.health import HealthCheckType, HealthStatus

    # Make cache operations fail
    mock_cache_adapter.set = AsyncMock(side_effect=Exception("Cache error"))

    with patch("fastblocks._health_integration.depends.get") as mock_depends:
        mock_depends.return_value = mock_cache_adapter

        check = CacheHealthCheck()
        result = await check._perform_health_check(HealthCheckType.READINESS)

        assert result.status == HealthStatus.DEGRADED
        assert "failed" in result.message.lower()
        assert "operation_error" in result.details


@pytest.mark.asyncio
@pytest.mark.skipif(not ACB_HEALTH_AVAILABLE, reason="ACB HealthService not available")
@pytest.mark.integration
async def test_database_health_check_query_failure(mock_sql_adapter):
    """Test database health check when query fails."""
    from acb.services.health import HealthCheckType, HealthStatus

    # Make database query fail
    mock_sql_adapter.execute = AsyncMock(side_effect=Exception("Connection error"))

    with patch("fastblocks._health_integration.depends.get") as mock_depends:
        mock_depends.return_value = mock_sql_adapter

        check = DatabaseHealthCheck()
        result = await check._perform_health_check(HealthCheckType.READINESS)

        assert result.status == HealthStatus.UNHEALTHY
        assert "failed" in result.message.lower()
        assert result.details.get("connectivity_test") == "failed"
