"""Tests for fastblocks/mcp/env_manager.py.

Targets ``EnvironmentManager`` (0% coverage before this file existed).
Each test drives a distinct surface: ``generate_environment_templates``,
``generate_environment_file``, ``generate_environment_example``,
``load_environment_from_file``, ``sync_environment_variables``,
``extract_variables_from_configuration``, ``audit_environment_security``,
plus the dataclass constructors.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastblocks.mcp.configuration import (
    ConfigurationProfile,
    ConfigurationSchema,
    EnvironmentVariable,
)
from fastblocks.mcp.env_manager import (
    EnvironmentManager,
    EnvironmentTemplate,
    EnvironmentValidationResult,
)


@pytest.fixture
def manager(tmp_path: Path) -> EnvironmentManager:
    return EnvironmentManager(base_path=tmp_path)


@pytest.mark.unit
class TestEnvironmentValidationResult:
    def test_validation_result_defaults(self) -> None:
        result = EnvironmentValidationResult(valid=True)
        assert result.valid is True
        assert result.missing_required == []
        assert result.invalid_format == []
        assert result.security_warnings == []
        assert result.recommendations == []


@pytest.mark.unit
class TestGenerateEnvironmentTemplates:
    def test_generate_three_standard_templates(
        self, manager: EnvironmentManager
    ) -> None:
        templates = manager.generate_environment_templates()
        assert set(templates.keys()) == {"development", "production", "testing"}
        for key in ("development", "production", "testing"):
            assert isinstance(templates[key], EnvironmentTemplate)
            assert templates[key].name == key
            assert all(
                isinstance(v, EnvironmentVariable) for v in templates[key].variables
            )

    def test_generated_variables_have_expected_names(
        self, manager: EnvironmentManager
    ) -> None:
        templates = manager.generate_environment_templates()
        names = {v.name for v in templates["development"].variables}
        assert "DEBUG" in names
        assert "SECRET_KEY" in names
        assert "DATABASE_URL" in names


@pytest.mark.unit
class TestGenerateEnvironmentFile:
    def test_generates_env_file_for_dev_variables(
        self, manager: EnvironmentManager, tmp_path: Path
    ) -> None:
        templates = manager.generate_environment_templates()
        output = tmp_path / ".env"
        result = manager.generate_environment_file(
            templates["development"].variables, output
        )
        text = result.read_text()
        assert "DEBUG=true" in text
        assert "LOG_LEVEL=DEBUG" in text
        assert "SECRET_KEY" in text

    def test_generated_env_example_for_production(
        self, manager: EnvironmentManager, tmp_path: Path
    ) -> None:
        templates = manager.generate_environment_templates()
        output = tmp_path / ".env.example"
        result = manager.generate_environment_example(
            templates["production"].variables, output
        )
        text = result.read_text()
        # Production example must include HTTPS_ONLY (production-specific).
        assert "HTTPS_ONLY" in text
        # Debug should be "false" in production template.
        assert "DEBUG=false" in text


@pytest.mark.unit
class TestLoadEnvironmentFromFile:
    def test_load_simple_env_file(
        self, manager: EnvironmentManager, tmp_path: Path
    ) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text(
            "DEBUG=true\n"
            "DATABASE_URL=sqlite:///./dev.db\n"
            "# comment line\n"
            "\n"
            "LOG_LEVEL=INFO\n"
        )
        loaded = manager.load_environment_from_file(env_file)
        assert loaded["DEBUG"] == "true"
        assert loaded["DATABASE_URL"] == "sqlite:///./dev.db"
        assert loaded["LOG_LEVEL"] == "INFO"

    def test_load_missing_file_returns_empty(
        self, manager: EnvironmentManager, tmp_path: Path
    ) -> None:
        loaded = manager.load_environment_from_file(tmp_path / "absent.env")
        assert loaded == {}


@pytest.mark.unit
class TestSyncEnvironmentVariables:
    def test_sync_returns_summary_dict(
        self, manager: EnvironmentManager, tmp_path: Path
    ) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("FOO=existing_value\n")
        variables = [
            EnvironmentVariable("FOO", "new_value", False, "foo"),
            EnvironmentVariable("BAR", "bar_value", False, "bar"),
        ]
        result = manager.sync_environment_variables(variables, env_file)
        assert isinstance(result, dict)
        assert result["file_exists"] is True
        assert result["total"] == 2
        # FOO existed so it should be updated.
        assert result["updated"] >= 1


@pytest.mark.unit
class TestExtractVariablesFromConfiguration:
    def test_extracts_global_environment_variables(
        self, manager: EnvironmentManager
    ) -> None:
        schema = ConfigurationSchema(
            version="1.0",
            profile=ConfigurationProfile.DEVELOPMENT,
            global_environment=[
                EnvironmentVariable("DEBUG", "true", False, "debug"),
                EnvironmentVariable("LOG_LEVEL", "DEBUG", False, "log level"),
            ],
        )
        variables = manager.extract_variables_from_configuration(schema)
        names = {v.name for v in variables}
        assert "DEBUG" in names
        assert "LOG_LEVEL" in names


@pytest.mark.unit
class TestAuditEnvironmentSecurity:
    def test_audit_returns_severity_buckets(
        self, manager: EnvironmentManager
    ) -> None:
        variables = [
            EnvironmentVariable("SECRET_KEY", "abc", True, "secret", True),
        ]
        audit = manager.audit_environment_security(variables)
        assert "critical" in audit
        assert "high" in audit
        assert "medium" in audit
        assert "low" in audit
        assert "info" in audit
        # A short / dictionary secret should produce at least one finding.
        total_findings = sum(len(v) for v in audit.values())
        assert total_findings >= 1

    def test_audit_strong_secret_has_fewer_findings(
        self, manager: EnvironmentManager
    ) -> None:
        weak = EnvironmentVariable("SECRET_KEY", "abc", True, "secret", True)
        strong = EnvironmentVariable(
            "API_TOKEN",
            "A" * 48,
            True,
            "token",
            True,
        )
        weak_audit = manager.audit_environment_security([weak])
        strong_audit = manager.audit_environment_security([strong])
        weak_total = sum(len(v) for v in weak_audit.values())
        strong_total = sum(len(v) for v in strong_audit.values())
        # Weak short secrets should produce at least as many findings as
        # strong long secrets (covers _check_secret_strength branch).
        assert weak_total >= strong_total