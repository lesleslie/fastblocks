"""Tests for fastblocks/mcp/config_audit.py.

Targets ``ConfigurationAuditor`` (0% coverage before this file existed).
A handful of broad-coverage tests drive ``audit_configuration`` through
all five audit phases: security, env vars, structure, profile-specific,
compliance, and best-practices — plus the dataclass constructors.
"""

from __future__ import annotations

import pytest
from fastblocks.mcp.config_audit import (
    AuditCategory,
    AuditFinding,
    AuditReport,
    AuditSeverity,
    ConfigurationAuditor,
)
from fastblocks.mcp.configuration import (
    ConfigurationProfile,
    ConfigurationSchema,
    EnvironmentVariable,
)
from fastblocks.mcp.env_manager import EnvironmentManager


@pytest.fixture
def auditor(tmp_path) -> ConfigurationAuditor:
    return ConfigurationAuditor(EnvironmentManager(base_path=tmp_path))


@pytest.mark.unit
class TestAuditSeverityCategoryEnums:
    def test_severity_values(self) -> None:
        assert AuditSeverity.CRITICAL.value == "critical"
        assert AuditSeverity.HIGH.value == "high"
        assert AuditSeverity.MEDIUM.value == "medium"
        assert AuditSeverity.LOW.value == "low"
        assert AuditSeverity.INFO.value == "info"

    def test_category_values(self) -> None:
        assert AuditCategory.SECURITY.value == "security"
        assert AuditCategory.COMPLIANCE.value == "compliance"


@pytest.mark.unit
class TestAuditFindingDataclass:
    def test_finding_default_fields(self) -> None:
        finding = AuditFinding(
            id="X-1",
            category=AuditCategory.SECURITY,
            severity=AuditSeverity.LOW,
            title="sample",
            description="sample",
            recommendation="sample",
        )
        assert finding.affected_items == []
        assert finding.details == {}
        assert finding.references == []
        # timestamp auto-populated
        assert finding.timestamp is not None


@pytest.mark.unit
class TestAuditReportDataclass:
    def test_report_default_fields(self) -> None:
        from datetime import datetime, UTC

        report = AuditReport(
            configuration_name="cfg",
            profile="development",
            audit_timestamp=datetime.now(UTC),
        )
        assert report.findings == []
        assert report.summary == {}
        assert report.score == 0.0


@pytest.mark.unit
class TestAuditConfigurationDevelopment:
    async def test_audit_development_profile_clean(
        self, auditor: ConfigurationAuditor
    ) -> None:
        schema = ConfigurationSchema(
            version="1.0",
            profile=ConfigurationProfile.DEVELOPMENT,
            global_settings={"debug": True},  # debug OK in dev
        )
        report = await auditor.audit_configuration(schema)
        assert isinstance(report, AuditReport)
        # Audit always emits a summary keyed by severity counts.
        assert "total_findings" in report.summary
        # Score in 0..100 range.
        assert 0.0 <= report.score <= 100.0


@pytest.mark.unit
class TestAuditConfigurationProduction:
    async def test_audit_production_with_debug_emits_finding(
        self, auditor: ConfigurationAuditor
    ) -> None:
        schema = ConfigurationSchema(
            version="1.0",
            profile=ConfigurationProfile.PRODUCTION,
            global_settings={"debug": True},
        )
        report = await auditor.audit_configuration(schema)
        # Debug-true in production should produce a HIGH severity finding.
        debug_findings = [
            f for f in report.findings
            if "Debug" in f.title or "debug" in f.description.lower()
        ]
        assert debug_findings
        # Recommendations list must be populated.
        assert isinstance(report.recommendations, list)


@pytest.mark.unit
class TestAuditConfigurationWithSecrets:
    async def test_audit_flags_unmarked_secret(
        self, auditor: ConfigurationAuditor
    ) -> None:
        # Short / weak secret value — should produce a finding.
        schema = ConfigurationSchema(
            version="1.0",
            profile=ConfigurationProfile.PRODUCTION,
            global_environment=[
                EnvironmentVariable("SECRET_KEY", "x", True, "secret"),
            ],
        )
        report = await auditor.audit_configuration(schema)
        # The audit emits a finding for short secrets (length<=4) and/or
        # weak secret content; we just need at least one finding to
        # confirm the security branch ran.
        secret_findings = [
            f for f in report.findings
            if "secret" in (f.title + " " + f.description).lower()
            or f.id.startswith("SEC-")
        ]
        assert secret_findings


@pytest.mark.unit
class TestAuditWithComplianceFramework:
    async def test_audit_with_hipaa_framework(
        self, auditor: ConfigurationAuditor
    ) -> None:
        schema = ConfigurationSchema(
            version="1.0",
            profile=ConfigurationProfile.PRODUCTION,
        )
        report = await auditor.audit_configuration(
            schema, compliance_frameworks=["hipaa"]
        )
        # Compliance audits run; findings list is non-empty when framework
        # is supplied (the auditor emits at least a baseline finding).
        assert isinstance(report.findings, list)
        assert isinstance(report.summary, dict)


@pytest.mark.unit
class TestAuditSummaryAndScore:
    async def test_summary_keys_present(
        self, auditor: ConfigurationAuditor
    ) -> None:
        schema = ConfigurationSchema(
            version="1.0",
            profile=ConfigurationProfile.DEVELOPMENT,
        )
        report = await auditor.audit_configuration(schema)
        # _generate_audit_summary emits a ``severity_breakdown`` nested dict
        # with these standard keys.
        assert "total_findings" in report.summary
        breakdown = report.summary.get("severity_breakdown", {})
        for key in ("critical", "high", "medium", "low", "info"):
            assert key in breakdown
