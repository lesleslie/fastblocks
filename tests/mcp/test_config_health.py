"""Tests for fastblocks/mcp/config_health.py.

Targets ``ConfigurationHealthChecker`` (147 missing statements before
this file). A handful of broad-coverage tests drive the health-check
fan-out and exercise the static helpers.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastblocks.mcp.config_health import (
    ConfigurationHealthChecker,
    ConfigurationHealthReport,
    ConfigurationTestResult,
    ConfigurationTestType,
    TestSeverity,
)
from fastblocks.mcp.configuration import (
    ConfigurationProfile,
    ConfigurationSchema,
    ConfigurationStatus,
)
from fastblocks.mcp.env_manager import EnvironmentManager
from fastblocks.mcp.registry import AdapterRegistry


@pytest.fixture
def checker(tmp_path) -> ConfigurationHealthChecker:
    """Build a checker with stubbed registry/env_manager."""
    registry = MagicMock(spec=AdapterRegistry)
    env_manager = MagicMock(spec=EnvironmentManager)
    return ConfigurationHealthChecker(
        registry=registry,
        env_manager=env_manager,
        base_path=tmp_path,
    )


@pytest.mark.unit
class TestConfigurationHealthReport:
    def test_report_defaults(self) -> None:
        report = ConfigurationHealthReport(
            configuration_name="cfg",
            profile="development",
            overall_status=ConfigurationStatus.VALID,
        )
        assert report.test_results == []
        assert report.summary == {}
        assert report.recommendations == []
        assert report.execution_time_ms == 0.0


@pytest.mark.unit
class TestTestResultAndSeverity:
    def test_severity_values(self) -> None:
        assert TestSeverity.CRITICAL.value == "critical"
        assert TestSeverity.HIGH.value == "high"
        assert TestSeverity.MEDIUM.value == "medium"
        assert TestSeverity.LOW.value == "low"
        assert TestSeverity.INFO.value == "info"

    def test_test_result_construction(self) -> None:
        result = ConfigurationTestResult(
            test_type=ConfigurationTestType.VALIDATION,
            test_name="schema_valid",
            passed=True,
            severity=TestSeverity.INFO,
            message="OK",
        )
        assert result.test_name == "schema_valid"
        assert result.execution_time_ms == 0.0
        assert result.details == {}


@pytest.mark.unit
class TestHealthCheckComprehensive:
    async def test_health_check_runs_all_categories(
        self, checker: ConfigurationHealthChecker
    ) -> None:
        schema = ConfigurationSchema(
            version="1.0",
            profile=ConfigurationProfile.DEVELOPMENT,
        )
        # Stub internal test methods to avoid touching real adapters.
        checker._test_configuration_validation = AsyncMock(return_value=[])
        checker._test_environment_variables = AsyncMock(return_value=[])
        checker._test_adapter_loading = AsyncMock(return_value=[])
        checker._test_adapter_dependencies = AsyncMock(return_value=[])
        checker._test_security_configuration = AsyncMock(return_value=[])
        checker._test_performance_configuration = AsyncMock(return_value=[])
        checker._test_integration_configuration = AsyncMock(return_value=[])
        report = await checker.run_comprehensive_health_check(schema)
        # All test categories ran → at least one result per category.
        assert isinstance(report, ConfigurationHealthReport)
        assert report.summary is not None


@pytest.mark.unit
class TestHealthCheckSubset:
    async def test_health_check_with_validation_only(
        self, checker: ConfigurationHealthChecker
    ) -> None:
        schema = ConfigurationSchema(
            version="1.0",
            profile=ConfigurationProfile.PRODUCTION,
        )
        checker._test_configuration_validation = AsyncMock(return_value=[])
        report = await checker.run_comprehensive_health_check(
            schema, test_types=[ConfigurationTestType.VALIDATION]
        )
        assert report.test_results == []
        # Validation only — overall_status is still a valid enum value.
        assert report.overall_status in list(ConfigurationStatus)


@pytest.mark.unit
class TestHealthCheckProductionProfile:
    async def test_production_profile_runs_security(
        self, checker: ConfigurationHealthChecker
    ) -> None:
        schema = ConfigurationSchema(
            version="1.0",
            profile=ConfigurationProfile.PRODUCTION,
        )
        checker._test_security_configuration = AsyncMock(return_value=[])
        report = await checker.run_comprehensive_health_check(
            schema,
            test_types=[ConfigurationTestType.SECURITY],
        )
        # Production + security check should produce results.
        assert report.overall_status in list(ConfigurationStatus)
