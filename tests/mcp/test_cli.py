"""D1 coverage tests for fastblocks/mcp/cli.py.

Targets the MCP CLI helper display functions (health, migration, audit)
which are pure formatting over data and can be tested without any I/O.
"""
# pyright: reportAttributeAccessIssue=false, reportFunctionMemberAccess=false
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from fastblocks.mcp.cli import (
    _display_audit_finding,
    _display_health_result_detail,
    _display_health_result_summary,
    _display_migration_compatibility,
    _display_migration_failure,
    _display_migration_incompatibility,
    _display_migration_success,
    _display_system_health_summary,
    _display_text_audit_report,
    _format_finding_for_json,
    _write_json_audit_report,
    _write_text_audit_report,
)


# ---------------------------------------------------------------------------
# Test fixtures: simple dataclass-like objects
# ---------------------------------------------------------------------------


@dataclass
class _Result:
    status: str = "healthy"
    message: str = "ok"
    duration_ms: float = 1.0
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class _Finding:
    id: str = "f-1"
    category: Any = None
    severity: Any = None
    title: str = "Title"
    description: str = "Description"
    recommendation: str = "Fix this"
    affected_items: list[str] = field(default_factory=list)


@pytest.fixture
def finding() -> _Finding:
    # Provide category / severity that expose ``.value``.
    return _Finding(
        affected_items=["item1", "item2"],
        category=type("E", (), {"value": "security"})(),
        severity=type("E", (), {"value": "warning"})(),
    )


# ---------------------------------------------------------------------------
# Health display
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestHealthDisplay:
    def test_health_result_summary(self, capsys: pytest.CaptureFixture[str]) -> None:
        _display_health_result_summary("alpha", _Result(status="healthy"))
        out = capsys.readouterr().out
        assert "alpha" in out
        assert "HEALTHY" in out

    def test_health_result_summary_warning(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _display_health_result_summary("beta", _Result(status="warning"))
        out = capsys.readouterr().out
        assert "beta" in out
        assert "WARNING" in out

    def test_health_result_detail(self, capsys: pytest.CaptureFixture[str]) -> None:
        r = _Result(details={"items": ["a", "b"], "count": 2})
        _display_health_result_detail("gamma", r)
        out = capsys.readouterr().out
        assert "gamma" in out
        assert "items: a, b" in out
        assert "count: 2" in out

    def test_health_result_detail_no_details(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _display_health_result_detail("delta", _Result())
        out = capsys.readouterr().out
        assert "delta" in out

    def test_system_health_summary(self, capsys: pytest.CaptureFixture[str]) -> None:
        summary = {
            "total_adapters": 4,
            "healthy_adapters": 2,
            "warning_adapters": 1,
            "error_adapters": 1,
            "unknown_adapters": 0,
        }
        _display_system_health_summary(summary)
        out = capsys.readouterr().out
        assert "Total Adapters: 4" in out
        assert "Healthy: 2" in out

    def test_system_health_summary_no_adapters(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        summary = {
            "total_adapters": 0,
            "healthy_adapters": 0,
            "warning_adapters": 0,
            "error_adapters": 0,
            "unknown_adapters": 0,
        }
        _display_system_health_summary(summary)
        out = capsys.readouterr().out
        assert "Total Adapters: 0" in out


# ---------------------------------------------------------------------------
# Migration display
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMigrationDisplay:
    def test_migration_compatibility(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        compat = {
            "current_version": "1.0",
            "migration_path": ["1.0", "1.5", "2.0"],
            "warnings": ["step a", "step b"],
        }
        _display_migration_compatibility(compat, "2.0")
        out = capsys.readouterr().out
        assert "1.0" in out
        assert "2.0" in out
        assert "step a" in out

    def test_migration_compatibility_no_warnings(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        compat = {
            "current_version": "1.0",
            "migration_path": ["1.0", "2.0"],
            "warnings": [],
        }
        _display_migration_compatibility(compat, "2.0")
        out = capsys.readouterr().out
        assert "1.0 -> 2.0" in out

    def test_migration_incompatibility(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        compat = {"warnings": ["incompat-a", "incompat-b"]}
        _display_migration_incompatibility(compat)
        err = capsys.readouterr().err
        assert "Migration not possible" in err
        assert "incompat-a" in err

    def test_migration_success(self, capsys: pytest.CaptureFixture[str]) -> None:
        result = type("R", (), {"steps_applied": ["a", "b"], "warnings": ["w"]})()
        _display_migration_success(result)
        out = capsys.readouterr().out
        assert "Migration completed" in out
        assert "a, b" in out
        assert "w" in out

    def test_migration_failure(self, capsys: pytest.CaptureFixture[str]) -> None:
        result = type("R", (), {"errors": ["e1", "e2"]})()
        _display_migration_failure(result)
        out = capsys.readouterr().out
        assert "Migration failed" in out
        assert "e1" in out


# ---------------------------------------------------------------------------
# Audit display
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAuditDisplay:
    def test_format_finding_for_json(self, finding: _Finding) -> None:
        d = _format_finding_for_json(finding)
        assert d["id"] == "f-1"
        assert d["title"] == "Title"
        assert d["affected_items"] == ["item1", "item2"]

    def test_display_audit_finding(self, finding: _Finding) -> None:
        # The function uses finding.severity.value as a dict key — give
        # it a stub with .value = "warning".
        from types import SimpleNamespace

        wrapped = SimpleNamespace(
            id=finding.id,
            category=SimpleNamespace(value="security"),
            severity=SimpleNamespace(value="warning"),
            title=finding.title,
            description=finding.description,
            recommendation=finding.recommendation,
            affected_items=finding.affected_items,
        )
        # The function should not raise.
        _display_audit_finding(wrapped)

    def test_write_json_audit_report_stdout(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        report = type(
            "R",
            (),
            {
                "configuration_name": "test",
                "profile": "dev",
                "score": 90,
                "summary": {"total_findings": 1},
                "findings": [],
            },
        )()
        _write_json_audit_report(report, None)
        out = capsys.readouterr().out
        assert "test" in out
        assert "dev" in out
        assert "90" in out

    def test_write_json_audit_report_to_file(
        self, tmp_path, finding: _Finding
    ) -> None:
        from types import SimpleNamespace

        wrapped = SimpleNamespace(
            id=finding.id,
            category=SimpleNamespace(value="security"),
            severity=SimpleNamespace(value="warning"),
            title=finding.title,
            description=finding.description,
            recommendation=finding.recommendation,
            affected_items=finding.affected_items,
        )
        report = type(
            "R",
            (),
            {
                "configuration_name": "test",
                "profile": "dev",
                "score": 90,
                "summary": {"total_findings": 1},
                "findings": [wrapped],
            },
        )()
        out_file = tmp_path / "report.json"
        _write_json_audit_report(report, str(out_file))
        assert out_file.exists()
        content = out_file.read_text()
        assert "test" in content
        assert "Title" in content

    def test_display_text_audit_report_no_findings(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        report = type(
            "R",
            (),
            {
                "configuration_name": "test",
                "profile": "prod",
                "score": 100,
                "summary": {"total_findings": 0},
                "findings": [],
                "recommendations": [],
            },
        )()
        _display_text_audit_report(report)
        out = capsys.readouterr().out
        assert "Configuration Audit Report: test" in out
        assert "100/100" in out

    def test_display_text_audit_report_with_findings(
        self, capsys: pytest.CaptureFixture[str], finding: _Finding
    ) -> None:
        from types import SimpleNamespace

        wrapped = SimpleNamespace(
            id=finding.id,
            category=SimpleNamespace(value="security"),
            severity=SimpleNamespace(value="error"),
            title=finding.title,
            description=finding.description,
            recommendation=finding.recommendation,
            affected_items=finding.affected_items,
        )
        report = type(
            "R",
            (),
            {
                "configuration_name": "test",
                "profile": "prod",
                "score": 75,
                "summary": {"total_findings": 1},
                "findings": [wrapped],
                "recommendations": ["rec-1"],
            },
        )()
        _display_text_audit_report(report)
        out = capsys.readouterr().out
        assert "75/100" in out
        assert "ERROR" in out
        assert "rec-1" in out

    def test_write_text_audit_report(self, tmp_path) -> None:
        report = type(
            "R",
            (),
            {
                "configuration_name": "test",
                "profile": "prod",
                "score": 88,
                "summary": {"total_findings": 0},
            },
        )()
        out_file = tmp_path / "audit.txt"
        _write_text_audit_report(report, str(out_file))
        assert out_file.exists()
        content = out_file.read_text()
        assert "Configuration Audit Report" in content
        assert "test" in content
        assert "88" in content