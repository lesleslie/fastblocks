"""Configuration audit and security checks for FastBlocks."""

import re
import typing as t
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from .configuration import ConfigurationSchema
from .env_manager import EnvironmentManager


class AuditSeverity(str, Enum):
    """Audit finding severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AuditCategory(str, Enum):
    """Audit categories."""

    SECURITY = "security"
    COMPLIANCE = "compliance"
    PERFORMANCE = "performance"
    CONFIGURATION = "configuration"
    BEST_PRACTICES = "best_practices"


@dataclass
class AuditFinding:
    """Individual audit finding."""

    id: str
    category: AuditCategory
    severity: AuditSeverity
    title: str
    description: str
    recommendation: str
    affected_items: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)
    references: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class AuditReport:
    """Comprehensive audit report."""

    configuration_name: str
    profile: str
    audit_timestamp: datetime
    findings: list[AuditFinding] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)
    score: float = 0.0
    recommendations: list[str] = field(default_factory=list)


class ConfigurationAuditor:
    """Comprehensive configuration auditor with security focus."""

    def __init__(self, env_manager: EnvironmentManager):
        """Initialize configuration auditor."""
        self.env_manager = env_manager

        # Security patterns and rules
        self.secret_patterns = [
            re.compile(
                r".*secret.*", re.IGNORECASE
            ),  # REGEX OK: detect secret config vars
            re.compile(
                r".*password.*", re.IGNORECASE
            ),  # REGEX OK: detect password config vars
            re.compile(r".*key$", re.IGNORECASE),  # REGEX OK: detect key config vars
            re.compile(
                r".*token.*", re.IGNORECASE
            ),  # REGEX OK: detect token config vars
            re.compile(
                r".*credential.*", re.IGNORECASE
            ),  # REGEX OK: detect credential config vars
        ]

        self.weak_secret_patterns = [
            re.compile(
                r"^(password|secret|admin|test|dev|123|abc)", re.IGNORECASE
            ),  # REGEX OK: detect weak secret values
            re.compile(
                r"^(.)\1+$"
            ),  # REGEX OK: detect repeated characters  # REGEX OK: detect weak secrets - repeated chars
            re.compile(
                r"^[a-z]+$"
            ),  # REGEX OK: detect weak secrets - only lowercase  # REGEX OK: detect weak secrets - lowercase only
            re.compile(
                r"^[0-9]+$"
            ),  # REGEX OK: detect weak secrets - numbers only  # REGEX OK: detect weak secrets - numeric only
        ]

        # Compliance frameworks
        self.compliance_rules = {
            "OWASP": self._get_owasp_rules(),
            "NIST": self._get_nist_rules(),
            "SOC2": self._get_soc2_rules(),
        }

    async def audit_configuration(
        self,
        config: ConfigurationSchema,
        compliance_frameworks: list[str] | None = None,
    ) -> AuditReport:
        """Perform comprehensive audit of configuration."""
        report = AuditReport(
            configuration_name="configuration",
            profile=config.profile.value,
            audit_timestamp=datetime.now(),
        )

        # Run all audit checks
        findings = []

        # Security audits
        findings.extend(await self._audit_security(config))

        # Environment variable audits
        findings.extend(await self._audit_environment_variables(config))

        # Configuration structure audits
        findings.extend(await self._audit_configuration_structure(config))

        # Profile-specific audits
        findings.extend(await self._audit_profile_specific(config))

        # Compliance audits
        if compliance_frameworks:
            for framework in compliance_frameworks:
                findings.extend(await self._audit_compliance(config, framework))

        # Best practices audits
        findings.extend(await self._audit_best_practices(config))

        report.findings = findings
        report.summary = self._generate_audit_summary(findings)
        report.score = self._calculate_audit_score(findings)
        report.recommendations = self._generate_audit_recommendations(findings, config)

        return report

    async def _audit_security(self, config: ConfigurationSchema) -> list[AuditFinding]:
        """Audit security-related configuration."""
        findings = []

        # Check debug mode in production
        if config.profile.value == "production":
            debug_enabled = config.global_settings.get("debug", False)
            if debug_enabled:
                findings.append(
                    AuditFinding(
                        id="SEC-001",
                        category=AuditCategory.SECURITY,
                        severity=AuditSeverity.HIGH,
                        title="Debug Mode Enabled in Production",
                        description="Debug mode is enabled in production configuration, which can expose sensitive information.",
                        recommendation="Set debug=false in production configurations.",
                        affected_items=["global_settings.debug"],
                        references=["OWASP Top 10 - A3 Sensitive Data Exposure"],
                    )
                )

        # Check log level in production
        if config.profile.value == "production":
            log_level = config.global_settings.get("log_level", "INFO").upper()
            if log_level in ("DEBUG", "TRACE"):
                findings.append(
                    AuditFinding(
                        id="SEC-002",
                        category=AuditCategory.SECURITY,
                        severity=AuditSeverity.MEDIUM,
                        title="Verbose Logging in Production",
                        description="Debug-level logging is enabled in production, which may log sensitive data.",
                        recommendation="Use WARNING or ERROR log level in production.",
                        affected_items=["global_settings.log_level"],
                        details={"current_level": log_level},
                    )
                )

        # Check for hardcoded secrets in configuration
        hardcoded_secrets = self._find_hardcoded_secrets(config)
        if hardcoded_secrets:
            findings.append(
                AuditFinding(
                    id="SEC-003",
                    category=AuditCategory.SECURITY,
                    severity=AuditSeverity.CRITICAL,
                    title="Hardcoded Secrets Detected",
                    description="Hardcoded secrets found in configuration. These should be moved to environment variables.",
                    recommendation="Move all secrets to environment variables and mark them as secret.",
                    affected_items=hardcoded_secrets,
                    references=["OWASP Top 10 - A2 Broken Authentication"],
                )
            )

        # Check for missing security headers
        security_settings = config.global_settings.get("security", {})
        missing_headers = []
        required_headers = ["force_https", "secure_cookies", "csrf_protection"]

        for header in required_headers:
            if not security_settings.get(header, False):
                missing_headers.append(header)

        if missing_headers:
            findings.append(
                AuditFinding(
                    id="SEC-004",
                    category=AuditCategory.SECURITY,
                    severity=AuditSeverity.MEDIUM,
                    title="Missing Security Headers",
                    description="Important security headers are not configured.",
                    recommendation="Enable all security headers for production deployment.",
                    affected_items=missing_headers,
                    details={"missing_headers": missing_headers},
                )
            )

        return findings

    def _check_weak_secrets(self, variables: list[t.Any]) -> AuditFinding | None:
        """Check for weak secret values in environment variables."""
        weak_secrets = []
        for var in variables:
            if var.secret and var.value:
                if self._is_weak_secret(var.value):
                    weak_secrets.append(var.name)

        if weak_secrets:
            return AuditFinding(
                id="ENV-001",
                category=AuditCategory.SECURITY,
                severity=AuditSeverity.HIGH,
                title="Weak Secret Values",
                description="Environment variables contain weak or predictable secret values.",
                recommendation="Generate strong, random secret values using cryptographically secure methods.",
                affected_items=weak_secrets,
                details={"count": len(weak_secrets)},
            )
        return None

    def _check_unmarked_secrets(self, variables: list[t.Any]) -> AuditFinding | None:
        """Check for unmarked secret variables."""
        unmarked_secrets = []
        for var in variables:
            if not var.secret and any(
                pattern.match(var.name) for pattern in self.secret_patterns
            ):
                if var.value and len(var.value) > 10:  # Likely a secret
                    unmarked_secrets.append(var.name)

        if unmarked_secrets:
            return AuditFinding(
                id="ENV-002",
                category=AuditCategory.SECURITY,
                severity=AuditSeverity.MEDIUM,
                title="Unmarked Secret Variables",
                description="Environment variables appear to contain secrets but are not marked as secret.",
                recommendation="Mark sensitive environment variables as secret to ensure proper handling.",
                affected_items=unmarked_secrets,
            )
        return None

    def _check_missing_required(self, variables: list[t.Any]) -> AuditFinding | None:
        """Check for missing required environment variables."""
        missing_required = [
            var.name
            for var in variables
            if var.required and not var.value and not var.default
        ]

        if missing_required:
            return AuditFinding(
                id="ENV-003",
                category=AuditCategory.CONFIGURATION,
                severity=AuditSeverity.HIGH,
                title="Missing Required Variables",
                description="Required environment variables are not configured.",
                recommendation="Provide values for all required environment variables.",
                affected_items=missing_required,
            )
        return None

    async def _audit_environment_variables(
        self, config: ConfigurationSchema
    ) -> list[AuditFinding]:
        """Audit environment variable configuration."""
        findings = []

        # Extract all environment variables
        variables = self.env_manager.extract_variables_from_configuration(config)

        # Run all checks and collect findings
        for check in (
            self._check_weak_secrets,
            self._check_unmarked_secrets,
            self._check_missing_required,
        ):
            finding = check(variables)
            if finding:
                findings.append(finding)

        return findings

    async def _audit_configuration_structure(
        self, config: ConfigurationSchema
    ) -> list[AuditFinding]:
        """Audit configuration structure and completeness."""
        findings = []

        # Check for empty adapter configurations
        empty_adapters = [
            name
            for name, adapter_config in config.adapters.items()
            if (
                adapter_config.enabled
                and not adapter_config.settings
                and not adapter_config.environment_variables
            )
        ]

        if empty_adapters:
            findings.append(
                AuditFinding(
                    id="CFG-001",
                    category=AuditCategory.CONFIGURATION,
                    severity=AuditSeverity.LOW,
                    title="Empty Adapter Configurations",
                    description="Some enabled adapters have no configuration settings.",
                    recommendation="Review adapter configurations and provide necessary settings.",
                    affected_items=empty_adapters,
                )
            )

        # Check for unused dependencies
        enabled_adapters = {
            name for name, adapter in config.adapters.items() if adapter.enabled
        }
        unused_deps = []

        for name, adapter_config in config.adapters.items():
            if adapter_config.enabled:
                for dep in adapter_config.dependencies:
                    if dep not in enabled_adapters:
                        unused_deps.append(f"{name} -> {dep}")

        if unused_deps:
            findings.append(
                AuditFinding(
                    id="CFG-002",
                    category=AuditCategory.CONFIGURATION,
                    severity=AuditSeverity.MEDIUM,
                    title="Unused Dependencies",
                    description="Some adapters depend on disabled adapters.",
                    recommendation="Either enable the dependent adapters or remove the dependencies.",
                    affected_items=unused_deps,
                )
            )

        # Check for configuration version currency
        if hasattr(config, "version"):
            if config.version != "1.0":
                findings.append(
                    AuditFinding(
                        id="CFG-003",
                        category=AuditCategory.CONFIGURATION,
                        severity=AuditSeverity.LOW,
                        title="Outdated Configuration Version",
                        description="Configuration uses an older schema version.",
                        recommendation="Migrate to the latest configuration schema version.",
                        details={
                            "current_version": config.version,
                            "latest_version": "1.0",
                        },
                    )
                )

        return findings

    async def _audit_profile_specific(
        self, config: ConfigurationSchema
    ) -> list[AuditFinding]:
        """Audit profile-specific requirements."""
        findings = []

        if config.profile.value == "production":
            # Production-specific checks

            # Check for development-only settings
            dev_settings = ["hot_reload", "auto_reload", "development_mode"]
            enabled_dev_settings = [
                setting
                for setting in dev_settings
                if config.global_settings.get(setting, False)
            ]

            if enabled_dev_settings:
                findings.append(
                    AuditFinding(
                        id="PROD-001",
                        category=AuditCategory.CONFIGURATION,
                        severity=AuditSeverity.HIGH,
                        title="Development Settings in Production",
                        description="Development-only settings are enabled in production configuration.",
                        recommendation="Disable development settings in production.",
                        affected_items=enabled_dev_settings,
                    )
                )

            # Check for monitoring configuration
            monitoring = config.global_settings.get("monitoring", {})
            if not monitoring.get("health_checks", False):
                findings.append(
                    AuditFinding(
                        id="PROD-002",
                        category=AuditCategory.CONFIGURATION,
                        severity=AuditSeverity.MEDIUM,
                        title="Health Checks Disabled",
                        description="Health checks are not enabled in production configuration.",
                        recommendation="Enable health checks for production monitoring.",
                    )
                )

        elif config.profile.value == "development":
            # Development-specific checks

            # Warn about production settings in development
            if config.global_settings.get("debug", True) is False:
                findings.append(
                    AuditFinding(
                        id="DEV-001",
                        category=AuditCategory.CONFIGURATION,
                        severity=AuditSeverity.INFO,
                        title="Debug Disabled in Development",
                        description="Debug mode is disabled in development configuration.",
                        recommendation="Consider enabling debug mode for better development experience.",
                    )
                )

        return findings

    async def _audit_compliance(
        self, config: ConfigurationSchema, framework: str
    ) -> list[AuditFinding]:
        """Audit compliance with specific framework."""
        findings = []

        rules = self.compliance_rules.get(framework, [])

        for rule in rules:
            if not rule["check_function"](config):
                findings.append(
                    AuditFinding(
                        id=rule["id"],
                        category=AuditCategory.COMPLIANCE,
                        severity=AuditSeverity(rule["severity"]),
                        title=f"{framework} - {rule['title']}",
                        description=rule["description"],
                        recommendation=rule["recommendation"],
                        references=[f"{framework} {rule['reference']}"],
                    )
                )

        return findings

    async def _audit_best_practices(
        self, config: ConfigurationSchema
    ) -> list[AuditFinding]:
        """Audit against best practices."""
        findings = []

        # Check for documentation/comments
        if not config.global_settings.get("description"):
            findings.append(
                AuditFinding(
                    id="BP-001",
                    category=AuditCategory.BEST_PRACTICES,
                    severity=AuditSeverity.LOW,
                    title="Missing Configuration Description",
                    description="Configuration lacks a description field.",
                    recommendation="Add a description to document the configuration purpose.",
                )
            )

        # Check adapter count
        enabled_count = sum(
            1 for adapter in config.adapters.values() if adapter.enabled
        )
        if enabled_count > 20:
            findings.append(
                AuditFinding(
                    id="BP-002",
                    category=AuditCategory.BEST_PRACTICES,
                    severity=AuditSeverity.LOW,
                    title="High Adapter Count",
                    description=f"Configuration enables {enabled_count} adapters, which may impact performance.",
                    recommendation="Review if all adapters are necessary and consider disabling unused ones.",
                    details={"enabled_adapters": enabled_count},
                )
            )

        # Check environment variable naming consistency
        variables = self.env_manager.extract_variables_from_configuration(config)
        prefixes = set()
        for var in variables:
            if "_" in var.name:
                prefix = var.name.split("_")[0]
                prefixes.add(prefix)

        if len(prefixes) > 5:
            findings.append(
                AuditFinding(
                    id="BP-003",
                    category=AuditCategory.BEST_PRACTICES,
                    severity=AuditSeverity.LOW,
                    title="Inconsistent Variable Naming",
                    description="Environment variables use many different prefixes.",
                    recommendation="Consider using consistent prefixes for related variables.",
                    details={"prefix_count": len(prefixes), "prefixes": list(prefixes)},
                )
            )

        return findings

    def _is_secret_key(self, key: str) -> bool:
        """Check if a key name matches secret patterns."""
        return any(pattern.match(key) for pattern in self.secret_patterns)

    def _is_hardcoded_value(self, value: str) -> bool:
        """Check if a value appears to be hardcoded (not an env var reference)."""
        return len(value) > 8 and not value.startswith("${")

    def _check_global_settings_for_secrets(
        self, config: ConfigurationSchema
    ) -> list[str]:
        """Check global settings for hardcoded secrets."""
        hardcoded = []

        for key, value in config.global_settings.items():
            if isinstance(value, str) and self._is_secret_key(key):
                if self._is_hardcoded_value(value):
                    hardcoded.append(f"global_settings.{key}")

        return hardcoded

    def _check_adapter_settings_for_secrets(
        self, config: ConfigurationSchema
    ) -> list[str]:
        """Check adapter settings for hardcoded secrets."""
        hardcoded = []

        for adapter_name, adapter_config in config.adapters.items():
            for key, value in adapter_config.settings.items():
                if isinstance(value, str) and self._is_secret_key(key):
                    if self._is_hardcoded_value(value):
                        hardcoded.append(f"adapters.{adapter_name}.settings.{key}")

        return hardcoded

    def _find_hardcoded_secrets(self, config: ConfigurationSchema) -> list[str]:
        """Find potential hardcoded secrets in configuration."""
        hardcoded = []

        # Check global settings
        hardcoded.extend(self._check_global_settings_for_secrets(config))

        # Check adapter settings
        hardcoded.extend(self._check_adapter_settings_for_secrets(config))

        return hardcoded

    def _is_weak_secret(self, secret: str) -> bool:
        """Check if a secret value is weak."""
        if len(secret) < 16:
            return True

        return any(pattern.match(secret) for pattern in self.weak_secret_patterns)

    def _get_owasp_rules(self) -> list[dict[str, Any]]:
        """Get OWASP compliance rules."""
        return [
            {
                "id": "OWASP-001",
                "title": "Secure Authentication Configuration",
                "description": "Authentication adapter must be properly configured",
                "recommendation": "Configure authentication with secure settings",
                "severity": "high",
                "reference": "A2 - Broken Authentication",
                "check_function": lambda config: any(
                    name.startswith("auth") for name in config.adapters.keys()
                ),
            },
            {
                "id": "OWASP-002",
                "title": "Sensitive Data Protection",
                "description": "Sensitive data must not be exposed in configuration",
                "recommendation": "Use environment variables for sensitive data",
                "severity": "critical",
                "reference": "A3 - Sensitive Data Exposure",
                "check_function": lambda config: len(
                    self._find_hardcoded_secrets(config)
                )
                == 0,
            },
        ]

    def _get_nist_rules(self) -> list[dict[str, Any]]:
        """Get NIST compliance rules."""
        return [
            {
                "id": "NIST-001",
                "title": "Access Control Configuration",
                "description": "Access controls must be properly configured",
                "recommendation": "Enable and configure access control mechanisms",
                "severity": "high",
                "reference": "AC-2 Account Management",
                "check_function": lambda config: "auth" in config.adapters,
            }
        ]

    def _get_soc2_rules(self) -> list[dict[str, Any]]:
        """Get SOC2 compliance rules."""
        return [
            {
                "id": "SOC2-001",
                "title": "Monitoring and Logging",
                "description": "System monitoring must be enabled",
                "recommendation": "Enable monitoring and logging for security events",
                "severity": "medium",
                "reference": "CC7.2 System Monitoring",
                "check_function": lambda config: config.global_settings.get(
                    "monitoring", {}
                ).get("enabled", False),
            }
        ]

    def _generate_audit_summary(self, findings: list[AuditFinding]) -> dict[str, Any]:
        """Generate audit summary statistics."""
        total_findings = len(findings)

        severity_counts = {}
        category_counts = {}

        for severity in AuditSeverity:
            severity_counts[severity.value] = sum(
                1 for f in findings if f.severity == severity
            )

        for category in AuditCategory:
            category_counts[category.value] = sum(
                1 for f in findings if f.category == category
            )

        return {
            "total_findings": total_findings,
            "severity_breakdown": severity_counts,
            "category_breakdown": category_counts,
            "critical_count": severity_counts.get("critical", 0),
            "high_count": severity_counts.get("high", 0),
        }

    def _calculate_audit_score(self, findings: list[AuditFinding]) -> float:
        """Calculate audit score (0-100)."""
        if not findings:
            return 100.0

        # Weight findings by severity
        severity_weights = {
            AuditSeverity.CRITICAL: 25,
            AuditSeverity.HIGH: 10,
            AuditSeverity.MEDIUM: 5,
            AuditSeverity.LOW: 2,
            AuditSeverity.INFO: 1,
        }

        total_deductions = sum(
            severity_weights.get(finding.severity, 1) for finding in findings
        )

        # Calculate score (max deduction caps at 100)
        score = max(0, 100 - min(total_deductions, 100))
        return round(score, 1)

    def _generate_audit_recommendations(
        self, findings: list[AuditFinding], config: ConfigurationSchema
    ) -> list[str]:
        """Generate high-level recommendations."""
        recommendations = []

        critical_count = sum(
            1 for f in findings if f.severity == AuditSeverity.CRITICAL
        )
        high_count = sum(1 for f in findings if f.severity == AuditSeverity.HIGH)

        if critical_count > 0:
            recommendations.append(
                f"🔴 URGENT: Address {critical_count} critical security issues before deployment"
            )

        if high_count > 0:
            recommendations.append(
                f"🟡 HIGH PRIORITY: Fix {high_count} high-severity issues to improve security posture"
            )

        # Profile-specific recommendations
        if config.profile.value == "production":
            prod_issues = [f for f in findings if f.id.startswith("PROD")]
            if prod_issues:
                recommendations.append(
                    "🏭 Review production-specific configuration requirements"
                )

        # Security-specific recommendations
        security_issues = [f for f in findings if f.category == AuditCategory.SECURITY]
        if len(security_issues) > 3:
            recommendations.append(
                "🔒 Consider security review and penetration testing"
            )

        return recommendations

    async def generate_security_checklist(
        self, config: ConfigurationSchema
    ) -> dict[str, Any]:
        """Generate security checklist for configuration."""
        checklist: dict[str, list[dict[str, Any]]] = {
            "authentication": [],
            "authorization": [],
            "data_protection": [],
            "logging_monitoring": [],
            "network_security": [],
            "configuration_security": [],
        }

        # Authentication checks
        auth_adapters = [name for name in config.adapters.keys() if "auth" in name]
        checklist["authentication"].append(
            {
                "item": "Authentication adapter configured",
                "status": "pass" if auth_adapters else "fail",
                "details": f"Found: {', '.join(auth_adapters)}"
                if auth_adapters
                else "No authentication adapters found",
            }
        )

        # Data protection checks
        variables = self.env_manager.extract_variables_from_configuration(config)
        secret_vars = [v for v in variables if v.secret]
        checklist["data_protection"].append(
            {
                "item": "Secrets properly marked",
                "status": "pass" if secret_vars else "warning",
                "details": f"{len(secret_vars)} secret variables configured",
            }
        )

        # Configuration security checks
        hardcoded_secrets = self._find_hardcoded_secrets(config)
        checklist["configuration_security"].append(
            {
                "item": "No hardcoded secrets",
                "status": "pass" if not hardcoded_secrets else "fail",
                "details": f"Found {len(hardcoded_secrets)} hardcoded secrets"
                if hardcoded_secrets
                else "No hardcoded secrets found",
            }
        )

        return checklist
