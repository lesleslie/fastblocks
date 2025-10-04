"""Configuration health checks and testing system for FastBlocks."""

import os
import tempfile
import time
import typing as t
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from .configuration import ConfigurationSchema, ConfigurationStatus
from .env_manager import EnvironmentManager
from .health import HealthCheckSystem
from .registry import AdapterRegistry


class ConfigurationTestType(str, Enum):
    """Types of configuration tests."""

    VALIDATION = "validation"
    ENVIRONMENT = "environment"
    ADAPTER_LOADING = "adapter_loading"
    DEPENDENCIES = "dependencies"
    SECURITY = "security"
    PERFORMANCE = "performance"
    INTEGRATION = "integration"


class TestSeverity(str, Enum):
    """Test result severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class ConfigurationTestResult:
    """Result of a configuration test."""

    test_type: ConfigurationTestType
    test_name: str
    passed: bool
    severity: TestSeverity
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    execution_time_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ConfigurationHealthReport:
    """Comprehensive configuration health report."""

    configuration_name: str
    profile: str
    overall_status: ConfigurationStatus
    test_results: list[ConfigurationTestResult] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)
    execution_time_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


class ConfigurationHealthChecker:
    """Comprehensive health checking for FastBlocks configurations."""

    def __init__(
        self,
        registry: AdapterRegistry,
        env_manager: EnvironmentManager,
        base_path: Path | None = None,
    ):
        """Initialize configuration health checker."""
        self.registry = registry
        self.env_manager = env_manager
        self.health_system = HealthCheckSystem(registry)
        self.base_path = base_path or Path.cwd()

        # Test categories with their severity levels
        self.test_categories = {
            ConfigurationTestType.VALIDATION: TestSeverity.CRITICAL,
            ConfigurationTestType.ENVIRONMENT: TestSeverity.HIGH,
            ConfigurationTestType.ADAPTER_LOADING: TestSeverity.HIGH,
            ConfigurationTestType.DEPENDENCIES: TestSeverity.MEDIUM,
            ConfigurationTestType.SECURITY: TestSeverity.HIGH,
            ConfigurationTestType.PERFORMANCE: TestSeverity.LOW,
            ConfigurationTestType.INTEGRATION: TestSeverity.MEDIUM,
        }

    async def run_comprehensive_health_check(
        self,
        config: ConfigurationSchema,
        test_types: list[ConfigurationTestType] | None = None,
    ) -> ConfigurationHealthReport:
        """Run comprehensive health check on configuration."""
        start_time = time.time()

        if test_types is None:
            test_types = list(ConfigurationTestType)

        report = ConfigurationHealthReport(
            configuration_name="unknown",
            profile=config.profile.value,
            overall_status=ConfigurationStatus.VALID,
        )

        # Run all specified tests
        for test_type in test_types:
            test_results = await self._run_test_category(config, test_type)
            report.test_results.extend(test_results)

        # Analyze results and determine overall status
        report.overall_status = self._determine_overall_status(report.test_results)
        report.summary = self._generate_summary(report.test_results)
        report.recommendations = self._generate_recommendations(
            report.test_results, config
        )
        report.execution_time_ms = (time.time() - start_time) * 1000

        return report

    async def _run_test_category(
        self, config: ConfigurationSchema, test_type: ConfigurationTestType
    ) -> list[ConfigurationTestResult]:
        """Run all tests in a specific category."""
        test_methods = {
            ConfigurationTestType.VALIDATION: self._test_configuration_validation,
            ConfigurationTestType.ENVIRONMENT: self._test_environment_variables,
            ConfigurationTestType.ADAPTER_LOADING: self._test_adapter_loading,
            ConfigurationTestType.DEPENDENCIES: self._test_adapter_dependencies,
            ConfigurationTestType.SECURITY: self._test_security_configuration,
            ConfigurationTestType.PERFORMANCE: self._test_performance_configuration,
            ConfigurationTestType.INTEGRATION: self._test_integration_configuration,
        }

        test_method = test_methods.get(test_type)
        if test_method:
            return await test_method(config)

        return []

    async def _test_configuration_validation(
        self, config: ConfigurationSchema
    ) -> list[ConfigurationTestResult]:
        """Test configuration validation."""
        results = []
        start_time = time.time()

        try:
            # Test schema validation
            from .configuration import ConfigurationManager

            config_manager = ConfigurationManager(self.registry)
            validation_result = await config_manager.validate_configuration(config)

            execution_time = (time.time() - start_time) * 1000

            if validation_result.status == ConfigurationStatus.VALID:
                results.append(
                    ConfigurationTestResult(
                        test_type=ConfigurationTestType.VALIDATION,
                        test_name="Schema Validation",
                        passed=True,
                        severity=TestSeverity.INFO,
                        message="Configuration schema is valid",
                        execution_time_ms=execution_time,
                    )
                )
            else:
                results.append(
                    ConfigurationTestResult(
                        test_type=ConfigurationTestType.VALIDATION,
                        test_name="Schema Validation",
                        passed=False,
                        severity=TestSeverity.CRITICAL,
                        message=f"Configuration validation failed: {validation_result.status.value}",
                        details={
                            "errors": validation_result.errors,
                            "warnings": validation_result.warnings,
                        },
                        execution_time_ms=execution_time,
                    )
                )

        except Exception as e:
            results.append(
                ConfigurationTestResult(
                    test_type=ConfigurationTestType.VALIDATION,
                    test_name="Schema Validation",
                    passed=False,
                    severity=TestSeverity.CRITICAL,
                    message=f"Validation test failed: {e}",
                    execution_time_ms=(time.time() - start_time) * 1000,
                )
            )

        return results

    async def _test_environment_variables(
        self, config: ConfigurationSchema
    ) -> list[ConfigurationTestResult]:
        """Test environment variable configuration."""
        results = []

        # Extract all environment variables
        variables = self.env_manager.extract_variables_from_configuration(config)

        # Validate environment variables
        start_time = time.time()
        validation_result = self.env_manager.validate_environment_variables(variables)
        execution_time = (time.time() - start_time) * 1000

        # Test for missing required variables
        if validation_result.missing_required:
            results.append(
                ConfigurationTestResult(
                    test_type=ConfigurationTestType.ENVIRONMENT,
                    test_name="Required Variables",
                    passed=False,
                    severity=TestSeverity.HIGH,
                    message=f"Missing {len(validation_result.missing_required)} required variables",
                    details={"missing": validation_result.missing_required},
                    execution_time_ms=execution_time,
                )
            )
        else:
            results.append(
                ConfigurationTestResult(
                    test_type=ConfigurationTestType.ENVIRONMENT,
                    test_name="Required Variables",
                    passed=True,
                    severity=TestSeverity.INFO,
                    message="All required environment variables are configured",
                    execution_time_ms=execution_time,
                )
            )

        # Test for format validation
        if validation_result.invalid_format:
            results.append(
                ConfigurationTestResult(
                    test_type=ConfigurationTestType.ENVIRONMENT,
                    test_name="Format Validation",
                    passed=False,
                    severity=TestSeverity.MEDIUM,
                    message=f"{len(validation_result.invalid_format)} variables have format issues",
                    details={"invalid_format": validation_result.invalid_format},
                    execution_time_ms=execution_time,
                )
            )
        else:
            results.append(
                ConfigurationTestResult(
                    test_type=ConfigurationTestType.ENVIRONMENT,
                    test_name="Format Validation",
                    passed=True,
                    severity=TestSeverity.INFO,
                    message="All environment variables have valid formats",
                    execution_time_ms=execution_time,
                )
            )

        return results

    async def _test_adapter_loading(
        self, config: ConfigurationSchema
    ) -> list[ConfigurationTestResult]:
        """Test adapter loading and instantiation."""
        results = []

        for adapter_name, adapter_config in config.adapters.items():
            if not adapter_config.enabled:
                continue

            start_time = time.time()

            try:
                # Try to get adapter info
                adapter_info = await self.registry.get_adapter_info(adapter_name)
                if not adapter_info:
                    results.append(
                        ConfigurationTestResult(
                            test_type=ConfigurationTestType.ADAPTER_LOADING,
                            test_name=f"Adapter Discovery ({adapter_name})",
                            passed=False,
                            severity=TestSeverity.HIGH,
                            message=f"Adapter '{adapter_name}' not found in registry",
                            execution_time_ms=(time.time() - start_time) * 1000,
                        )
                    )
                    continue

                # Try to instantiate adapter
                adapter_instance = await self.registry.get_adapter(adapter_name)
                if adapter_instance:
                    results.append(
                        ConfigurationTestResult(
                            test_type=ConfigurationTestType.ADAPTER_LOADING,
                            test_name=f"Adapter Loading ({adapter_name})",
                            passed=True,
                            severity=TestSeverity.INFO,
                            message=f"Adapter '{adapter_name}' loaded successfully",
                            details={
                                "adapter_class": adapter_instance.__class__.__name__
                            },
                            execution_time_ms=(time.time() - start_time) * 1000,
                        )
                    )
                else:
                    results.append(
                        ConfigurationTestResult(
                            test_type=ConfigurationTestType.ADAPTER_LOADING,
                            test_name=f"Adapter Loading ({adapter_name})",
                            passed=False,
                            severity=TestSeverity.HIGH,
                            message=f"Failed to instantiate adapter '{adapter_name}'",
                            execution_time_ms=(time.time() - start_time) * 1000,
                        )
                    )

            except Exception as e:
                results.append(
                    ConfigurationTestResult(
                        test_type=ConfigurationTestType.ADAPTER_LOADING,
                        test_name=f"Adapter Loading ({adapter_name})",
                        passed=False,
                        severity=TestSeverity.HIGH,
                        message=f"Error loading adapter '{adapter_name}': {e}",
                        execution_time_ms=(time.time() - start_time) * 1000,
                    )
                )

        return results

    async def _test_adapter_dependencies(
        self, config: ConfigurationSchema
    ) -> list[ConfigurationTestResult]:
        """Test adapter dependency resolution."""
        results = []

        enabled_adapters = {
            name for name, adapter in config.adapters.items() if adapter.enabled
        }

        for adapter_name, adapter_config in config.adapters.items():
            if not adapter_config.enabled:
                continue

            start_time = time.time()

            # Check if all dependencies are enabled
            missing_deps = adapter_config.dependencies - enabled_adapters
            if missing_deps:
                results.append(
                    ConfigurationTestResult(
                        test_type=ConfigurationTestType.DEPENDENCIES,
                        test_name=f"Dependencies ({adapter_name})",
                        passed=False,
                        severity=TestSeverity.MEDIUM,
                        message=f"Missing dependencies for '{adapter_name}': {', '.join(missing_deps)}",
                        details={"missing_dependencies": list(missing_deps)},
                        execution_time_ms=(time.time() - start_time) * 1000,
                    )
                )
            else:
                results.append(
                    ConfigurationTestResult(
                        test_type=ConfigurationTestType.DEPENDENCIES,
                        test_name=f"Dependencies ({adapter_name})",
                        passed=True,
                        severity=TestSeverity.INFO,
                        message=f"All dependencies satisfied for '{adapter_name}'",
                        execution_time_ms=(time.time() - start_time) * 1000,
                    )
                )

        return results

    async def _test_security_configuration(
        self, config: ConfigurationSchema
    ) -> list[ConfigurationTestResult]:
        """Test security aspects of configuration."""
        results = []

        # Extract environment variables for security audit
        variables = self.env_manager.extract_variables_from_configuration(config)

        start_time = time.time()
        audit_results = self.env_manager.audit_environment_security(variables)
        execution_time = (time.time() - start_time) * 1000

        # Check for critical security issues
        if audit_results["critical"]:
            results.append(
                ConfigurationTestResult(
                    test_type=ConfigurationTestType.SECURITY,
                    test_name="Critical Security Issues",
                    passed=False,
                    severity=TestSeverity.CRITICAL,
                    message=f"Found {len(audit_results['critical'])} critical security issues",
                    details={"issues": audit_results["critical"]},
                    execution_time_ms=execution_time,
                )
            )

        # Check for high severity issues
        if audit_results["high"]:
            results.append(
                ConfigurationTestResult(
                    test_type=ConfigurationTestType.SECURITY,
                    test_name="High Security Issues",
                    passed=False,
                    severity=TestSeverity.HIGH,
                    message=f"Found {len(audit_results['high'])} high severity security issues",
                    details={"issues": audit_results["high"]},
                    execution_time_ms=execution_time,
                )
            )

        # Production security checks
        if config.profile.value == "production":
            prod_results = self._check_production_security(config)
            results.extend(prod_results)

        # If no critical or high issues found
        if not audit_results["critical"] and not audit_results["high"]:
            results.append(
                ConfigurationTestResult(
                    test_type=ConfigurationTestType.SECURITY,
                    test_name="Security Audit",
                    passed=True,
                    severity=TestSeverity.INFO,
                    message="No critical security issues found",
                    details={
                        "audit_summary": {k: len(v) for k, v in audit_results.items()}
                    },
                    execution_time_ms=execution_time,
                )
            )

        return results

    def _check_production_security(
        self, config: ConfigurationSchema
    ) -> list[ConfigurationTestResult]:
        """Additional security checks for production configuration."""
        results = []
        start_time = time.time()

        # Check debug mode
        debug_enabled = config.global_settings.get("debug", False)
        if debug_enabled:
            results.append(
                ConfigurationTestResult(
                    test_type=ConfigurationTestType.SECURITY,
                    test_name="Production Debug Mode",
                    passed=False,
                    severity=TestSeverity.HIGH,
                    message="Debug mode is enabled in production configuration",
                    details={"recommendation": "Set debug=false for production"},
                    execution_time_ms=(time.time() - start_time) * 1000,
                )
            )

        # Check log level
        log_level = config.global_settings.get("log_level", "INFO").upper()
        if log_level in ("DEBUG"):
            results.append(
                ConfigurationTestResult(
                    test_type=ConfigurationTestType.SECURITY,
                    test_name="Production Log Level",
                    passed=False,
                    severity=TestSeverity.MEDIUM,
                    message="Debug logging enabled in production",
                    details={
                        "current_level": log_level,
                        "recommendation": "Use WARNING or ERROR for production",
                    },
                    execution_time_ms=(time.time() - start_time) * 1000,
                )
            )

        return results

    async def _test_performance_configuration(
        self, config: ConfigurationSchema
    ) -> list[ConfigurationTestResult]:
        """Test performance-related configuration."""
        results = []
        start_time = time.time()

        # Count enabled adapters
        enabled_count = sum(
            1 for adapter in config.adapters.values() if adapter.enabled
        )

        if enabled_count > 20:
            results.append(
                ConfigurationTestResult(
                    test_type=ConfigurationTestType.PERFORMANCE,
                    test_name="Adapter Count",
                    passed=False,
                    severity=TestSeverity.LOW,
                    message=f"High number of enabled adapters ({enabled_count}) may impact performance",
                    details={"enabled_adapters": enabled_count},
                    execution_time_ms=(time.time() - start_time) * 1000,
                )
            )
        else:
            results.append(
                ConfigurationTestResult(
                    test_type=ConfigurationTestType.PERFORMANCE,
                    test_name="Adapter Count",
                    passed=True,
                    severity=TestSeverity.INFO,
                    message=f"Reasonable number of enabled adapters ({enabled_count})",
                    execution_time_ms=(time.time() - start_time) * 1000,
                )
            )

        return results

    async def _test_integration_configuration(
        self, config: ConfigurationSchema
    ) -> list[ConfigurationTestResult]:
        """Test integration aspects of configuration."""
        results = []

        # Test adapter health checks
        for adapter_name, adapter_config in config.adapters.items():
            if not adapter_config.enabled:
                continue

            start_time = time.time()

            try:
                health_result = await self.health_system.check_adapter_health(
                    adapter_name
                )

                if health_result.status == "healthy":
                    results.append(
                        ConfigurationTestResult(
                            test_type=ConfigurationTestType.INTEGRATION,
                            test_name=f"Adapter Health ({adapter_name})",
                            passed=True,
                            severity=TestSeverity.INFO,
                            message=f"Adapter '{adapter_name}' is healthy",
                            details={"health_status": health_result.status},
                            execution_time_ms=(time.time() - start_time) * 1000,
                        )
                    )
                else:
                    results.append(
                        ConfigurationTestResult(
                            test_type=ConfigurationTestType.INTEGRATION,
                            test_name=f"Adapter Health ({adapter_name})",
                            passed=False,
                            severity=TestSeverity.MEDIUM,
                            message=f"Adapter '{adapter_name}' health check failed: {health_result.message}",
                            details={
                                "health_status": health_result.status,
                                "details": health_result.details,
                            },
                            execution_time_ms=(time.time() - start_time) * 1000,
                        )
                    )

            except Exception as e:
                results.append(
                    ConfigurationTestResult(
                        test_type=ConfigurationTestType.INTEGRATION,
                        test_name=f"Adapter Health ({adapter_name})",
                        passed=False,
                        severity=TestSeverity.MEDIUM,
                        message=f"Health check failed for '{adapter_name}': {e}",
                        execution_time_ms=(time.time() - start_time) * 1000,
                    )
                )

        return results

    def _determine_overall_status(
        self, test_results: list[ConfigurationTestResult]
    ) -> ConfigurationStatus:
        """Determine overall configuration status from test results."""
        has_critical = any(
            not result.passed and result.severity == TestSeverity.CRITICAL
            for result in test_results
        )
        if has_critical:
            return ConfigurationStatus.ERROR

        has_high = any(
            not result.passed and result.severity == TestSeverity.HIGH
            for result in test_results
        )
        if has_high:
            return ConfigurationStatus.ERROR

        has_medium = any(
            not result.passed and result.severity == TestSeverity.MEDIUM
            for result in test_results
        )
        if has_medium:
            return ConfigurationStatus.WARNING

        return ConfigurationStatus.VALID

    def _generate_summary(
        self, test_results: list[ConfigurationTestResult]
    ) -> dict[str, Any]:
        """Generate summary statistics from test results."""
        total_tests = len(test_results)
        passed_tests = sum(1 for result in test_results if result.passed)

        severity_counts = {}
        for severity in TestSeverity:
            severity_counts[severity.value] = sum(
                1
                for result in test_results
                if not result.passed and result.severity == severity
            )

        test_type_summary = {}
        for test_type in ConfigurationTestType:
            type_results = [r for r in test_results if r.test_type == test_type]
            test_type_summary[test_type.value] = {
                "total": len(type_results),
                "passed": sum(1 for r in type_results if r.passed),
                "failed": sum(1 for r in type_results if not r.passed),
            }

        return {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": total_tests - passed_tests,
            "pass_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0,
            "severity_breakdown": severity_counts,
            "test_type_summary": test_type_summary,
            "avg_execution_time_ms": sum(r.execution_time_ms for r in test_results)
            / total_tests
            if total_tests > 0
            else 0,
        }

    def _generate_recommendations(
        self, test_results: list[ConfigurationTestResult], config: ConfigurationSchema
    ) -> list[str]:
        """Generate recommendations based on test results."""
        recommendations = []

        # Critical and high severity issues
        critical_issues = [
            r
            for r in test_results
            if not r.passed and r.severity == TestSeverity.CRITICAL
        ]
        if critical_issues:
            recommendations.append(
                f"🔴 Address {len(critical_issues)} critical issues immediately before deploying"
            )

        high_issues = [
            r for r in test_results if not r.passed and r.severity == TestSeverity.HIGH
        ]
        if high_issues:
            recommendations.append(
                f"🟡 Fix {len(high_issues)} high severity issues to improve reliability"
            )

        # Security recommendations
        security_issues = [
            r
            for r in test_results
            if r.test_type == ConfigurationTestType.SECURITY and not r.passed
        ]
        if security_issues:
            recommendations.append("🔒 Review and fix security configuration issues")

        # Performance recommendations
        if config.profile.value == "production":
            enabled_adapters = sum(
                1 for adapter in config.adapters.values() if adapter.enabled
            )
            if enabled_adapters > 15:
                recommendations.append(
                    "⚡ Consider disabling unused adapters to improve performance"
                )

        # Environment recommendations
        env_issues = [
            r
            for r in test_results
            if r.test_type == ConfigurationTestType.ENVIRONMENT and not r.passed
        ]
        if env_issues:
            recommendations.append("🌍 Complete environment variable configuration")

        return recommendations

    async def run_configuration_test_suite(
        self, config_file: Path, output_file: Path | None = None
    ) -> ConfigurationHealthReport:
        """Run complete test suite on a configuration file."""
        from .configuration import ConfigurationManager

        # Load configuration
        config_manager = ConfigurationManager(self.registry, self.base_path)
        await config_manager.initialize()
        config = await config_manager.load_configuration(config_file)

        # Run health check
        report = await self.run_comprehensive_health_check(config)
        report.configuration_name = config_file.stem

        # Save report if requested
        if output_file:
            await self._save_health_report(report, output_file)

        return report

    async def _save_health_report(
        self, report: ConfigurationHealthReport, output_file: Path
    ) -> None:
        """Save health report to file."""
        import json

        # Convert report to serializable dict
        report_dict = {
            "configuration_name": report.configuration_name,
            "profile": report.profile,
            "overall_status": report.overall_status.value,
            "timestamp": report.timestamp.isoformat(),
            "execution_time_ms": report.execution_time_ms,
            "summary": report.summary,
            "recommendations": report.recommendations,
            "test_results": [
                {
                    "test_type": result.test_type.value,
                    "test_name": result.test_name,
                    "passed": result.passed,
                    "severity": result.severity.value,
                    "message": result.message,
                    "details": result.details,
                    "execution_time_ms": result.execution_time_ms,
                    "timestamp": result.timestamp.isoformat(),
                }
                for result in report.test_results
            ],
        }

        with output_file.open("w") as f:
            json.dump(report_dict, f, indent=2)

    @asynccontextmanager
    async def isolated_test_environment(
        self, config: ConfigurationSchema
    ) -> t.AsyncGenerator[Path]:
        """Create isolated environment for testing configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create isolated environment manager
            isolated_env_manager = EnvironmentManager(temp_path)

            # Generate environment file in isolation
            variables = isolated_env_manager.extract_variables_from_configuration(
                config
            )
            env_file = await isolated_env_manager.generate_environment_file(  # type: ignore[misc]
                variables, temp_path / ".env"
            )

            # Backup current environment
            original_env = os.environ.copy()

            try:
                # Load test environment
                test_env = isolated_env_manager.load_environment_from_file(env_file)
                os.environ.update(test_env)

                yield temp_path

            finally:
                # Restore original environment
                os.environ.clear()
                os.environ.update(original_env)
