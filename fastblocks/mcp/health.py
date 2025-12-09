"""Health check and validation system for FastBlocks adapters."""

import asyncio
import time
from datetime import datetime
from typing import Any

from .registry import AdapterRegistry


class HealthCheckResult:
    """Result of a health check operation."""

    def __init__(
        self,
        adapter_name: str,
        status: str,
        message: str = "",
        details: dict[str, Any] | None = None,
        duration_ms: float = 0.0,
        timestamp: datetime | None = None,
    ):
        self.adapter_name = adapter_name
        self.status = status  # 'healthy', 'warning', 'error', 'unknown'
        self.message = message
        self.details = details or {}
        self.duration_ms = duration_ms
        self.timestamp = timestamp or datetime.now()

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "adapter_name": self.adapter_name,
            "status": self.status,
            "message": self.message,
            "details": self.details,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat(),
        }


class HealthCheckSystem:
    """Health monitoring and validation system for adapters."""

    def __init__(self, registry: AdapterRegistry):
        """Initialize health check system."""
        self.registry = registry
        self._check_history: dict[str, list[HealthCheckResult]] = {}
        self._check_config: dict[str, dict[str, Any]] = {}
        self._running_checks: dict[str, bool] = {}

    async def check_adapter_health(self, adapter_name: str) -> HealthCheckResult:
        """Perform comprehensive health check on an adapter."""
        start_time = time.time()

        try:
            # Prevent concurrent checks on same adapter
            if self._running_checks.get(adapter_name, False):
                return HealthCheckResult(
                    adapter_name, "warning", "Health check already in progress"
                )

            self._running_checks[adapter_name] = True

            # Basic validation check
            validation_result = await self.registry.validate_adapter(adapter_name)

            if not validation_result["valid"]:
                duration_ms = (time.time() - start_time) * 1000
                result = HealthCheckResult(
                    adapter_name,
                    "error",
                    f"Validation failed: {', '.join(validation_result['errors'])}",
                    validation_result,
                    duration_ms,
                )
            else:
                # Get adapter instance for functional tests
                adapter = await self.registry.get_adapter(adapter_name)

                if not adapter:
                    duration_ms = (time.time() - start_time) * 1000
                    result = HealthCheckResult(
                        adapter_name,
                        "error",
                        "Could not instantiate adapter",
                        duration_ms=duration_ms,
                    )
                else:
                    # Perform functional health checks
                    result = await self._perform_functional_checks(
                        adapter_name, adapter, start_time
                    )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            result = HealthCheckResult(
                adapter_name,
                "error",
                f"Health check failed: {e}",
                duration_ms=duration_ms,
            )
        finally:
            self._running_checks[adapter_name] = False

        # Store result in history
        self._store_check_result(result)

        return result

    def _determine_health_status(
        self, checks: list[str], warnings: list[str]
    ) -> tuple[str, str]:
        """Determine health status and message based on checks and warnings."""
        if checks:
            status = "warning" if warnings else "healthy"
            message = f"Passed {len(checks)} checks"
            if warnings:
                message += f", {len(warnings)} warnings"
        else:
            status = "error"
            message = "No functional checks passed"
        return status, message

    async def _perform_category_specific_checks(
        self, adapter_info: Any, adapter: Any
    ) -> list[str]:
        """Perform category-specific health checks."""
        checks = []
        category = adapter_info.category

        # Category-specific health checks
        if category == "images":
            checks.extend(await self._check_image_adapter(adapter))
        elif category == "styles":
            checks.extend(await self._check_style_adapter(adapter))
        elif category == "icons":
            checks.extend(await self._check_icon_adapter(adapter))
        elif category == "fonts":
            checks.extend(await self._check_font_adapter(adapter))
        elif category == "templates":
            checks.extend(await self._check_template_adapter(adapter))

        return checks

    async def _check_acb_registration(
        self, adapter_name: str
    ) -> tuple[list[str], list[str]]:
        """Check ACB registration for the adapter."""
        checks = []
        warnings = []

        try:
            from acb.depends import depends

            registered_adapter = depends.get_sync(adapter_name)
            if registered_adapter:
                checks.append("Registered with ACB")
            else:
                warnings.append("Not registered with ACB")
        except Exception:
            warnings.append("ACB registration check failed")

        return checks, warnings

    async def _perform_functional_checks(
        self, adapter_name: str, adapter: Any, start_time: float
    ) -> HealthCheckResult:
        """Perform functional health checks on an adapter."""
        checks = []
        warnings = []

        # Check if adapter has required methods based on its type
        adapter_info = await self.registry.get_adapter_info(adapter_name)

        if adapter_info:
            checks.extend(
                await self._perform_category_specific_checks(adapter_info, adapter)
            )

        # Check settings availability
        if hasattr(adapter, "settings"):
            checks.append("Settings available")
        else:
            warnings.append("No settings found")

        # Check ACB registration
        acb_checks, acb_warnings = await self._check_acb_registration(adapter_name)
        checks.extend(acb_checks)
        warnings.extend(acb_warnings)

        duration_ms = (time.time() - start_time) * 1000

        # Determine overall status
        status, message = self._determine_health_status(checks, warnings)

        return HealthCheckResult(
            adapter_name,
            status,
            message,
            {
                "checks_passed": checks,
                "warnings": warnings,
                "category": adapter_info.category if adapter_info else "unknown",
            },
            duration_ms,
        )

    async def _check_image_adapter(self, adapter: Any) -> list[str]:
        """Check image adapter functionality."""
        checks = []

        if hasattr(adapter, "get_img_tag"):
            checks.append("get_img_tag method available")

        if hasattr(adapter, "get_image_url"):
            checks.append("get_image_url method available")

        if hasattr(adapter, "upload_image"):
            checks.append("upload_image method available")

        return checks

    async def _check_style_adapter(self, adapter: Any) -> list[str]:
        """Check style adapter functionality."""
        checks = []

        if hasattr(adapter, "get_stylesheet_links"):
            checks.append("get_stylesheet_links method available")

        if hasattr(adapter, "get_component_class"):
            checks.append("get_component_class method available")

        if hasattr(adapter, "get_utility_classes"):
            checks.append("get_utility_classes method available")

        return checks

    async def _check_icon_adapter(self, adapter: Any) -> list[str]:
        """Check icon adapter functionality."""
        checks = []

        if hasattr(adapter, "get_icon_tag"):
            checks.append("get_icon_tag method available")

        if hasattr(adapter, "get_stylesheet_links"):
            checks.append("get_stylesheet_links method available")

        if hasattr(adapter, "get_icon_class"):
            checks.append("get_icon_class method available")

        return checks

    async def _check_font_adapter(self, adapter: Any) -> list[str]:
        """Check font adapter functionality."""
        checks = []

        if hasattr(adapter, "get_font_import"):
            checks.append("get_font_import method available")

        if hasattr(adapter, "get_font_family"):
            checks.append("get_font_family method available")

        return checks

    async def _check_template_adapter(self, adapter: Any) -> list[str]:
        """Check template adapter functionality."""
        checks = []

        if hasattr(adapter, "render_template"):
            checks.append("render_template method available")

        if hasattr(adapter, "get_template"):
            checks.append("get_template method available")

        if hasattr(adapter, "list_templates"):
            checks.append("list_templates method available")

        return checks

    async def check_all_adapters(self) -> dict[str, HealthCheckResult]:
        """Perform health checks on all available adapters."""
        available_adapters = await self.registry.list_available_adapters()
        results = {}

        # Run checks concurrently
        tasks = []
        for adapter_name in available_adapters.keys():
            task = asyncio.create_task(self.check_adapter_health(adapter_name))
            tasks.append((adapter_name, task))

        for adapter_name, task in tasks:
            try:
                result = await task
                results[adapter_name] = result
            except Exception as e:
                results[adapter_name] = HealthCheckResult(
                    adapter_name, "error", f"Check failed: {e}"
                )

        return results

    def _store_check_result(self, result: HealthCheckResult) -> None:
        """Store health check result in history."""
        if result.adapter_name not in self._check_history:
            self._check_history[result.adapter_name] = []

        self._check_history[result.adapter_name].append(result)

        # Keep only last 100 results per adapter
        if len(self._check_history[result.adapter_name]) > 100:
            self._check_history[result.adapter_name] = self._check_history[
                result.adapter_name
            ][-100:]

    def get_check_history(
        self, adapter_name: str, limit: int = 10
    ) -> list[HealthCheckResult]:
        """Get health check history for an adapter."""
        return self._check_history.get(adapter_name, [])[-limit:]

    def get_system_health_summary(self) -> dict[str, Any]:
        """Get overall system health summary."""
        summary: dict[str, Any] = {
            "healthy_adapters": 0,
            "warning_adapters": 0,
            "error_adapters": 0,
            "unknown_adapters": 0,
            "total_adapters": 0,
            "last_check_time": None,
            "adapter_status": {},
        }

        latest_results = {}

        # Get latest result for each adapter
        for adapter_name, history in self._check_history.items():
            if history:
                latest_results[adapter_name] = history[-1]

        # Count statuses
        for adapter_name, result in latest_results.items():
            summary["adapter_status"][adapter_name] = {
                "status": result.status,
                "last_check": result.timestamp.isoformat(),
                "message": result.message,
            }

            if result.status == "healthy":
                summary["healthy_adapters"] += 1
            elif result.status == "warning":
                summary["warning_adapters"] += 1
            elif result.status == "error":
                summary["error_adapters"] += 1
            else:
                summary["unknown_adapters"] += 1

        summary["total_adapters"] = len(latest_results)

        if latest_results:
            latest_time = max(result.timestamp for result in latest_results.values())
            summary["last_check_time"] = latest_time.isoformat()

        return summary

    def configure_health_checks(
        self, adapter_name: str, config: dict[str, Any]
    ) -> None:
        """Configure health check parameters for an adapter."""
        self._check_config[adapter_name] = config

    def get_health_check_config(self, adapter_name: str) -> dict[str, Any]:
        """Get health check configuration for an adapter."""
        return self._check_config.get(adapter_name, {})

    async def schedule_periodic_checks(self, interval_minutes: int = 30) -> None:
        """Schedule periodic health checks for all adapters."""
        while True:
            try:
                await self.check_all_adapters()
                await asyncio.sleep(interval_minutes * 60)
            except Exception:
                # Log error but continue
                await asyncio.sleep(60)  # Wait 1 minute before retrying
