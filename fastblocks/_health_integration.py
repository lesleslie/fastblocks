"""ACB HealthService integration for FastBlocks.

This module bridges FastBlocks components with ACB's comprehensive health monitoring system.
It registers FastBlocks-specific health checks while maintaining existing MCP health checks.

Author: lesleslie <les@wedgwoodwebworks.com>
Created: 2025-10-01
"""

import typing as t
from contextlib import suppress
from uuid import UUID

from acb.adapters import AdapterStatus
from acb.depends import Inject, depends

# Optional ACB health imports (graceful degradation if not available)
try:
    from acb.services.health import (
        HealthCheckMixin,
        HealthCheckResult,
        HealthStatus,
    )

    acb_health_available = True
except ImportError:
    acb_health_available = False
    HealthCheckMixin = object  # Fallback base class
    HealthCheckResult = None
    HealthCheckType = None
    HealthStatus = None


class FastBlocksHealthCheck(HealthCheckMixin):  # type: ignore[misc]
    """Base health check implementation for FastBlocks components."""

    @depends.inject  # type: ignore[misc]  # ACB untyped decorator
    def __init__(
        self,
        config: Inject[t.Any],
        component_id: str | None = None,
        component_name: str | None = None,
    ) -> None:
        if acb_health_available:
            super().__init__()
        self.config = config
        self._component_id: str = component_id or self.__class__.__name__.lower()
        self._component_name: str = component_name or self.__class__.__name__

    @property
    def component_id(self) -> str:
        """Get unique identifier for this component."""
        return self._component_id

    @property
    def component_name(self) -> str:
        """Get human-readable name for this component."""
        return self._component_name

    async def _perform_health_check(
        self,
        check_type: t.Any,  # HealthCheckType when available
    ) -> t.Any:  # HealthCheckResult when available
        """Default health check - override in subclasses."""
        if not acb_health_available:
            return None

        return HealthCheckResult(
            component_id=self.component_id,
            component_name=self.component_name,
            status=HealthStatus.HEALTHY,
            check_type=check_type,
            message=f"{self.component_name} is operational",
        )


class TemplatesHealthCheck(FastBlocksHealthCheck):
    """Health check for FastBlocks template system."""

    def __init__(self) -> None:
        super().__init__(
            component_id="templates",
            component_name="Template System",
        )

    def _check_template_adapter_status(
        self, templates: t.Any, details: dict[str, t.Any]
    ) -> tuple[t.Any, str]:
        """Check templates adapter status and update details."""
        if not hasattr(templates, "app") or templates.app is None:
            return HealthStatus.DEGRADED, "Template app not initialized"

        details["jinja_env_initialized"] = True

        # Check template directory accessibility
        if hasattr(templates.app, "env") and templates.app.env.loader:
            details["loader_available"] = True
            return HealthStatus.HEALTHY, "Template system operational"
        return HealthStatus.DEGRADED, "Template loader not configured"

    async def _check_cache_availability(self, details: dict[str, t.Any]) -> None:
        """Check cache availability and update details."""
        try:
            cache = await depends.get("cache")
            details["cache_available"] = cache is not None
        except Exception:
            details["cache_available"] = False

    async def _perform_health_check(
        self,
        check_type: t.Any,
    ) -> t.Any:
        """Check template system health."""
        if not acb_health_available:
            return None

        details: dict[str, t.Any] = {}
        status = HealthStatus.HEALTHY
        message = "Template system operational"

        try:
            # Try to get templates adapter
            templates = await depends.get("templates")

            if templates is None:
                status = HealthStatus.DEGRADED
                message = "Templates adapter not initialized"
            else:
                status, message = self._check_template_adapter_status(
                    templates, details
                )

            # Check cache availability
            await self._check_cache_availability(details)

        except Exception as e:
            status = HealthStatus.UNHEALTHY
            message = f"Template health check failed: {e}"
            details["error"] = str(e)

        return HealthCheckResult(
            component_id=self.component_id,
            component_name=self.component_name,
            status=status,
            check_type=check_type,
            message=message,
            details=details,
        )


class CacheHealthCheck(FastBlocksHealthCheck):
    """Health check for FastBlocks cache system."""

    def __init__(self) -> None:
        super().__init__(
            component_id="cache",
            component_name="Cache System",
        )

    async def _test_cache_operations(
        self, cache: t.Any, details: dict[str, t.Any]
    ) -> tuple[t.Any, str]:  # Returns (status, message)
        """Test cache read/write operations and update details."""
        test_key = "__fastblocks_health_check__"
        test_value = "health_check_ok"

        try:
            # Test set operation
            await cache.set(test_key, test_value, ttl=10)
            details["write_test"] = "passed"

            # Test get operation
            retrieved = await cache.get(test_key)
            if retrieved == test_value:
                details["read_test"] = "passed"
                await cache.delete(test_key)
                return HealthStatus.HEALTHY, "Cache system operational"

            details["read_test"] = "failed"
            return HealthStatus.DEGRADED, "Cache read verification failed"

        except Exception as e:
            details["operation_error"] = str(e)
            return HealthStatus.DEGRADED, f"Cache operations failed: {e}"

    async def _collect_cache_stats(
        self, cache: t.Any, details: dict[str, t.Any]
    ) -> None:
        """Collect cache statistics if available."""
        if hasattr(cache, "get_stats"):
            with suppress(Exception):  # Stats not critical
                stats = await cache.get_stats()
                if hasattr(stats, "hit_ratio"):
                    details["cache_hit_ratio"] = stats.hit_ratio

    async def _perform_health_check(
        self,
        check_type: t.Any,
    ) -> t.Any:
        """Check cache system health."""
        if not acb_health_available:
            return None

        details: dict[str, t.Any] = {}
        status = HealthStatus.HEALTHY
        message = "Cache system operational"

        try:
            # Try to get cache adapter
            cache = await depends.get("cache")

            if cache is None:
                status = HealthStatus.DEGRADED
                message = "Cache adapter not available (degraded mode)"
                details["reason"] = "cache_disabled_or_not_configured"
            else:
                # Test cache operations
                status, message = await self._test_cache_operations(cache, details)

                # Collect stats if available
                await self._collect_cache_stats(cache, details)

        except Exception as e:
            status = HealthStatus.UNHEALTHY
            message = f"Cache health check failed: {e}"
            details["error"] = str(e)

        return HealthCheckResult(
            component_id=self.component_id,
            component_name=self.component_name,
            status=status,
            check_type=check_type,
            message=message,
            details=details,
        )


class RoutesHealthCheck(FastBlocksHealthCheck):
    """Health check for FastBlocks routing system."""

    def __init__(self) -> None:
        super().__init__(
            component_id="routes",
            component_name="Routing System",
        )

    def _check_routes_adapter(
        self, routes: t.Any, details: dict[str, t.Any]
    ) -> tuple[t.Any, str]:  # Returns (status, message)
        """Check routes adapter status and update details."""
        if not hasattr(routes, "routes"):
            return HealthStatus.DEGRADED, "Routes collection not available"

        route_count = len(routes.routes) if routes.routes else 0
        details["route_count"] = route_count

        if route_count == 0:
            return HealthStatus.DEGRADED, "No routes registered"

        return HealthStatus.HEALTHY, f"{route_count} routes registered"

    async def _perform_health_check(
        self,
        check_type: t.Any,
    ) -> t.Any:
        """Check routing system health."""
        if not acb_health_available:
            return None

        details: dict[str, t.Any] = {}
        status = HealthStatus.HEALTHY
        message = "Routing system operational"

        try:
            # Try to get routes adapter
            routes = await depends.get("routes")

            if routes is None:
                status = HealthStatus.DEGRADED
                message = "Routes adapter not initialized"
            else:
                status, message = self._check_routes_adapter(routes, details)

        except Exception as e:
            status = HealthStatus.UNHEALTHY
            message = f"Routes health check failed: {e}"
            details["error"] = str(e)

        return HealthCheckResult(
            component_id=self.component_id,
            component_name=self.component_name,
            status=status,
            check_type=check_type,
            message=message,
            details=details,
        )


class DatabaseHealthCheck(FastBlocksHealthCheck):
    """Health check for database connectivity."""

    def __init__(self) -> None:
        super().__init__(
            component_id="database",
            component_name="Database",
        )

    async def _perform_health_check(
        self,
        check_type: t.Any,
    ) -> t.Any:
        """Check database health."""
        if not acb_health_available:
            return None

        details: dict[str, t.Any] = {}
        status = HealthStatus.HEALTHY
        message = "Database operational"

        try:
            # Try to get sql adapter
            sql = await depends.get("sql")

            if sql is None:
                status = HealthStatus.DEGRADED
                message = "Database adapter not configured"
                details["reason"] = "sql_adapter_not_available"
            else:
                # Try a simple database query
                try:
                    # Most databases support SELECT 1 as a ping query
                    await sql.execute("SELECT 1")
                    details["connectivity_test"] = "passed"

                    # Check if we have connection pool info
                    if hasattr(sql, "get_connection_info"):
                        with suppress(Exception):  # Connection info not critical
                            conn_info = await sql.get_connection_info()
                            details["connection_info"] = conn_info

                except Exception as e:
                    status = HealthStatus.UNHEALTHY
                    message = f"Database query failed: {e}"
                    details["connectivity_test"] = "failed"
                    details["error"] = str(e)

        except Exception as e:
            status = HealthStatus.DEGRADED
            message = f"Database health check failed: {e}"
            details["error"] = str(e)

        return HealthCheckResult(
            component_id=self.component_id,
            component_name=self.component_name,
            status=status,
            check_type=check_type,
            message=message,
            details=details,
        )


async def register_fastblocks_health_checks() -> bool:
    """Register all FastBlocks components with ACB HealthService.

    Returns:
        True if registration successful, False if ACB HealthService unavailable
    """
    if not acb_health_available:
        return False

    try:
        # Get ACB HealthService from the service registry
        health_service = await depends.get("health_service")

        if health_service is None:
            return False

        # Register all FastBlocks health checks
        await health_service.register_component(TemplatesHealthCheck())
        await health_service.register_component(CacheHealthCheck())
        await health_service.register_component(RoutesHealthCheck())
        await health_service.register_component(DatabaseHealthCheck())

        return True

    except Exception:
        # Graceful degradation if registration fails
        return False


def _determine_overall_health_status(results: dict[str, t.Any]) -> str:
    """Determine overall health status from individual component results."""
    statuses = [r.get("status", "unknown") for r in results.values()]

    if "unhealthy" in statuses or "critical" in statuses:
        return "unhealthy"
    elif "degraded" in statuses:
        return "degraded"
    elif all(s == "healthy" for s in statuses):
        return "healthy"
    return "unknown"


async def _get_component_health_results(health_service: t.Any) -> dict[str, t.Any]:
    """Get health results for all components."""
    component_ids = ["templates", "cache", "routes", "database"]
    results = {}

    for component_id in component_ids:
        try:
            result = await health_service.get_component_health(component_id)
            if result:
                results[component_id] = result.to_dict()
        except Exception:
            results[component_id] = {
                "status": "unknown",
                "message": "Health check failed",
            }

    return results


async def get_fastblocks_health_summary() -> dict[str, t.Any]:
    """Get comprehensive health summary for all FastBlocks components.

    Returns:
        Dictionary with health status for each component
    """
    if not acb_health_available:
        return {
            "status": "unknown",
            "message": "ACB HealthService not available",
            "components": {},
        }

    try:
        health_service = await depends.get("health_service")

        if health_service is None:
            return {
                "status": "unknown",
                "message": "ACB HealthService not initialized",
                "components": {},
            }

        # Get health status for all registered components
        results = await _get_component_health_results(health_service)

        # Determine overall status
        overall_status = _determine_overall_health_status(results)

        return {
            "status": overall_status,
            "message": f"FastBlocks health status: {overall_status}",
            "components": results,
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Health check failed: {e}",
            "components": {},
        }


# Module metadata for ACB discovery
MODULE_ID = UUID("01937d88-0000-7000-8000-000000000001")
MODULE_STATUS = AdapterStatus.STABLE

# Auto-register health checks on module import
# Note: Registration happens during application startup via depends.set()
# This ensures proper async context is available
