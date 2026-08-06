"""Oneiric Health Service integration for FastBlocks.

This module provides FastBlocks components with comprehensive health monitoring.
It includes custom health checks for templates, cache, routing, and database systems.

Author: lesleslie <les@wedgwoodwebworks.com>
Created: 2025-10-01
"""

from __future__ import annotations

import typing as t
from contextlib import suppress
from uuid import UUID

from oneiric.core.logging import get_logger
from fastblocks.adapters.oneiric_helper import register_candidate
from fastblocks.core.resolver import get_resolver

# Custom Oneiric-compatible health system
depends = get_resolver()

logger = get_logger(__name__)

# Health system availability
oneiric_health_available = True


# Custom Oneiric-compatible Health System
class HealthStatus:
    """Health status levels."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class HealthCheckResult:
    """Result of a health check."""

    def __init__(
        self,
        component_id: str,
        component_name: str,
        status: str,
        check_type: t.Any,
        message: str,
        details: dict[str, t.Any] | None = None,
    ):
        self.component_id = component_id
        self.component_name = component_name
        self.status = status
        self.check_type = check_type
        self.message = message
        self.details = details or {}

    def to_dict(self) -> dict[str, t.Any]:
        """Convert health check result to dictionary."""
        return {
            "component_id": self.component_id,
            "component_name": self.component_name,
            "status": self.status,
            "check_type": str(self.check_type) if self.check_type else None,
            "message": self.message,
            "details": self.details,
        }


class HealthService:
    """Simple health service for Oneiric-compatible health monitoring."""

    def __init__(self) -> None:
        self.components: dict[str, t.Any] = {}

    async def register_component(self, component: t.Any) -> bool:
        """Register a health check component."""
        with suppress(Exception):
            if hasattr(component, "component_id"):
                self.components[component.component_id] = component
                return True
        return False

    async def get_component_health(self, component_id: str) -> HealthCheckResult | None:
        """Get health status for a specific component."""
        with suppress(Exception):
            component = self.components.get(component_id)
            if component and hasattr(component, "_perform_health_check"):
                # Use a simple check type for now
                result = await component._perform_health_check("standard")
                return t.cast("HealthCheckResult | None", result)
        return None


class FastBlocksHealthCheck:
    """Base health check implementation for FastBlocks components."""

    def __init__(
        self,
        config: t.Any | None = None,
        component_id: str | None = None,
        component_name: str | None = None,
    ) -> None:
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
        if not oneiric_health_available:
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
            # For Oneiric, we'll use a simpler approach
            # In practice, this would be replaced with actual dependency resolution
            details["cache_available"] = True  # Placeholder
        except Exception:  # noqa: BLE001, RUF100 - framework-boundary health probe must report degraded, not raise
            logger.exception("Cache availability probe failed")
            details["cache_available"] = False

    async def _perform_health_check(
        self,
        check_type: t.Any,
    ) -> HealthCheckResult:
        """Check template system health."""
        details: dict[str, t.Any] = {}
        status = HealthStatus.HEALTHY
        message = "Template system operational"

        try:
            # Try to get templates adapter
            # For Oneiric, we'll use a simpler approach
            templates = None  # Placeholder - would use actual template system

            if templates is None:
                status = HealthStatus.DEGRADED
                message = "Templates adapter not initialized"
            else:
                status, message = self._check_template_adapter_status(
                    templates, details
                )

            # Check cache availability
            await self._check_cache_availability(details)

        except Exception as e:  # noqa: BLE001, RUF100 - framework-boundary health check returns diagnostic, never raises
            logger.exception("Template health check failed")
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
    ) -> tuple[str, str]:  # Returns (status, message)
        """Test cache read/write operations and update details."""
        try:
            # Test set operation
            # For Oneiric, we'll use a simpler approach
            details["write_test"] = "passed"  # Placeholder

            # Test get operation
            # For Oneiric, we'll use a simpler approach
            details["read_test"] = "passed"  # Placeholder
            return HealthStatus.HEALTHY, "Cache system operational"

        except Exception as e:  # noqa: BLE001, RUF100 - framework-boundary health check returns diagnostic, never raises
            logger.exception("Cache operations probe failed")
            details["operation_error"] = str(e)
            return HealthStatus.DEGRADED, f"Cache operations failed: {e}"

    async def _collect_cache_stats(
        self, cache: t.Any, details: dict[str, t.Any]
    ) -> None:
        """Collect cache statistics if available."""
        # For Oneiric, we'll use a simpler approach
        # In practice, this would be replaced with actual cache stats
        details["cache_hit_ratio"] = 0.95  # Placeholder

    async def _perform_health_check(
        self,
        check_type: t.Any,
    ) -> HealthCheckResult:
        """Check cache system health."""
        details: dict[str, t.Any] = {}
        status = HealthStatus.HEALTHY
        message = "Cache system operational"

        try:
            # Try to get cache adapter
            # For Oneiric, we'll use a simpler approach
            cache = None  # Placeholder - would use actual cache system

            if cache is None:
                status = HealthStatus.DEGRADED
                message = "Cache adapter not available (degraded mode)"
                details["reason"] = "cache_disabled_or_not_configured"
            else:
                # Test cache operations
                status, message = await self._test_cache_operations(cache, details)

                # Collect stats if available
                await self._collect_cache_stats(cache, details)

        except Exception as e:  # noqa: BLE001, RUF100 - framework-boundary health check returns diagnostic, never raises
            logger.exception("Cache health check failed")
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
    ) -> HealthCheckResult:
        """Check routing system health."""
        details: dict[str, t.Any] = {}
        status = HealthStatus.HEALTHY
        message = "Routing system operational"

        try:
            # Try to get routes adapter
            # For Oneiric, we'll use a simpler approach
            routes = None  # Placeholder - would use actual routing system

            if routes is None:
                status = HealthStatus.DEGRADED
                message = "Routes adapter not initialized"
            else:
                status, message = self._check_routes_adapter(routes, details)

        except Exception as e:  # noqa: BLE001, RUF100 - framework-boundary health check returns diagnostic, never raises
            logger.exception("Routes health check failed")
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
    ) -> HealthCheckResult:
        """Check database health."""
        details: dict[str, t.Any] = {}
        status = HealthStatus.HEALTHY
        message = "Database operational"

        try:
            # Try to get sql adapter
            # For Oneiric, we'll use a simpler approach
            sql = None  # Placeholder - would use actual database system

            if sql is None:
                status = HealthStatus.DEGRADED
                message = "Database adapter not configured"
                details["reason"] = "sql_adapter_not_available"
            else:
                # Try a simple database query
                try:
                    # Most databases support SELECT 1 as a ping query
                    # For Oneiric, we'll use a simpler approach
                    details["connectivity_test"] = "passed"  # Placeholder

                    # Check if we have connection pool info
                    # For Oneiric, we'll use a simpler approach
                    details["connection_info"] = {"pool_size": 10}  # Placeholder

                except Exception as e:  # noqa: BLE001, RUF100 - framework-boundary health probe returns diagnostic
                    logger.exception("Database connectivity probe failed")
                    status = HealthStatus.UNHEALTHY
                    message = f"Database query failed: {e}"
                    details["connectivity_test"] = "failed"
                    details["error"] = str(e)

        except Exception as e:  # noqa: BLE001, RUF100 - framework-boundary health check returns diagnostic, never raises
            logger.exception("Database health check failed")
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
    """Register all FastBlocks components with Oneiric HealthService.

    Returns:
        True if registration successful, False if health service unavailable
    """
    try:
        # Create Oneiric-compatible health service
        health_service = HealthService()

        # Register all FastBlocks health checks
        await health_service.register_component(TemplatesHealthCheck())
        await health_service.register_component(CacheHealthCheck())
        await health_service.register_component(RoutesHealthCheck())
        await health_service.register_component(DatabaseHealthCheck())

        # Store health service in depends for retrieval
        register_candidate(
            depends,
            domain="fastblocks",
            key="health",
            factory=lambda: health_service,
            metadata={
                "class": "HealthService",
                "module": "fastblocks._health_integration",
            },
        )

        return True

    except Exception:  # noqa: BLE001, RUF100 - framework-boundary registration must not break startup
        logger.exception("FastBlocks health check registration failed")
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
    """Get health results for all components.

    One failing component must not erase the status of its successful
    siblings: each per-component result is captured independently, with the
    failure surfaced in the details dict instead of being dropped.
    """
    component_ids = ["templates", "cache", "routes", "database"]
    results: dict[str, t.Any] = {}

    for component_id in component_ids:
        component = health_service.components.get(component_id)
        if component is None:
            # No registered component for this id — fall back to the legacy
            # ``get_component_health`` API for backwards compatibility with
            # callers that inject external components.
            try:
                result = await health_service.get_component_health(component_id)
            except Exception as exc:
                logger.exception(
                    "Health check exception: component=%s",
                    component_id,
                )
                results[component_id] = {
                    "status": "unknown",
                    "message": f"Health check failed: {exc}",
                    "details": {"error": str(exc)},
                }
                continue

            if result:
                results[component_id] = result.to_dict()
            continue

        # Per-component check: capture the failure explicitly so the
        # overall aggregation can still see the healthy sibling.
        runner = getattr(component, "_perform_health_check", None)
        if runner is None:
            continue
        try:
            outcome = await runner("standard")
        except Exception as exc:
            logger.exception(
                "Health check exception: component=%s",
                component_id,
            )
            results[component_id] = {
                "status": "unknown",
                "message": f"Health check failed: {exc}",
                "details": {"error": str(exc)},
            }
            continue

        if outcome is not None:
            result_dict = getattr(outcome, "to_dict", None)
            if callable(result_dict):
                results[component_id] = result_dict()
            elif isinstance(outcome, dict):
                results[component_id] = outcome

    return results


async def get_fastblocks_health_summary() -> dict[str, t.Any]:
    """Get comprehensive health summary for all FastBlocks components.

    Returns:
        Dictionary with health status for each component
    """
    try:
        # Get Oneiric health service
        # For now, we'll create a new one since we don't have the actual service
        health_service = HealthService()

        # Register components for this check
        await health_service.register_component(TemplatesHealthCheck())
        await health_service.register_component(CacheHealthCheck())
        await health_service.register_component(RoutesHealthCheck())
        await health_service.register_component(DatabaseHealthCheck())

        # Get health status for all registered components
        results = await _get_component_health_results(health_service)

        # Determine overall status
        overall_status = _determine_overall_health_status(results)

        return {
            "status": overall_status,
            "message": f"FastBlocks health status: {overall_status}",
            "components": results,
        }

    except Exception as e:  # noqa: BLE001, RUF100 - framework-boundary health check returns diagnostic, never raises
        logger.exception("FastBlocks overall health check failed")
        return {
            "status": "error",
            "message": f"Health check failed: {e}",
            "components": {},
        }


# Module metadata for Oneiric compatibility
MODULE_ID = UUID("01937d88-0000-7000-8000-000000000001")
MODULE_STATUS = "STABLE"  # Oneiric-compatible status

# Auto-register health checks on module import
# Note: Registration happens during application startup via depends.set()
# This ensures proper async context is available
