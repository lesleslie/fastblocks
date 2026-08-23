"""Tests for fastblocks/mcp/cli.py — Click-based MCP admin CLI.

Targets ``fastblocks/mcp/cli.py`` (0% coverage before this file existed).
Each test drives an entire Click subcommand via ``CliRunner`` with the
upstream managers / registry stubbed, so the surface-level control flow,
table formatting, JSON output, and error branches all execute under
coverage. The goal is to lift ``mcp/cli.py`` from 0% to ~80% in one wave.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner
from fastblocks.mcp.cli import cli


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _adapter_info(
    *,
    name: str = "jinja2",
    category: str = "templates",
    module_status: str = "stable",
    description: str = "Jinja2 templates adapter.",
    protocols: list[str] | None = None,
    class_name: str = "Jinja2Templates",
    module_path: str = "fastblocks.adapters.templates.jinja2",
) -> MagicMock:
    """Build a MagicMock that quacks like ``AdapterInfo``."""
    info = MagicMock()
    info.name = name
    info.category = category
    info.module_status = module_status
    info.description = description
    info.protocols = protocols or []
    info.class_name = class_name
    info.module_path = module_path
    info.module_id = "11111111-1111-1111-1111-111111111111"
    info.settings_class = "Jinja2Settings"
    info.to_dict = MagicMock(
        return_value={
            "name": name,
            "category": category,
            "module_status": module_status,
            "description": description,
            "protocols": protocols or [],
            "class_name": class_name,
            "module_path": module_path,
            "module_id": "11111111-1111-1111-1111-111111111111",
            "settings_class": "Jinja2Settings",
        }
    )
    return info


def _registry_with(*, adapters: dict[str, MagicMock] | None = None) -> MagicMock:
    """Build a registry mock whose async methods return ``adapters``."""
    registry = MagicMock()
    registry.initialize = AsyncMock()
    registry.list_available_adapters = AsyncMock(return_value=adapters or {})
    registry.get_adapter_info = AsyncMock(return_value=None)
    registry.get_adapters_by_category = AsyncMock(return_value=[])
    registry.get_categories = AsyncMock(return_value=[])
    registry.get_adapter_statistics = AsyncMock(return_value={})
    return registry


@pytest.mark.unit
class TestListAdapters:
    def test_list_adapters_default_table_format(self, runner: CliRunner) -> None:
        registry = _registry_with(
            adapters={
                "jinja2": _adapter_info(name="jinja2"),
                "htmy": _adapter_info(name="htmy", module_status="beta", category="templates"),
            }
        )
        with patch(
            "fastblocks.mcp.cli.get_registry_and_health",
            AsyncMock(return_value=(registry, MagicMock())),
        ):
            result = runner.invoke(cli, ["list-adapters"])
        assert result.exit_code == 0
        assert "jinja2" in result.output
        assert "htmy" in result.output
        assert "stable" in result.output or "beta" in result.output

    def test_list_adapters_json_format(self, runner: CliRunner) -> None:
        registry = _registry_with(
            adapters={"jinja2": _adapter_info(name="jinja2")},
        )
        with patch(
            "fastblocks.mcp.cli.get_registry_and_health",
            AsyncMock(return_value=(registry, MagicMock())),
        ):
            result = runner.invoke(cli, ["list-adapters", "--format", "json"])
        assert result.exit_code == 0
        # JSON is a parseable dict; verify shape.
        payload = json.loads(result.output)
        assert "jinja2" in payload
        assert payload["jinja2"]["category"] == "templates"

    def test_list_adapters_empty(self, runner: CliRunner) -> None:
        registry = _registry_with()
        with patch(
            "fastblocks.mcp.cli.get_registry_and_health",
            AsyncMock(return_value=(registry, MagicMock())),
        ):
            result = runner.invoke(cli, ["list-adapters"])
        assert result.exit_code == 0
        assert "Available Adapters" in result.output


@pytest.mark.unit
class TestListCategories:
    def test_list_categories_no_filter(self, runner: CliRunner) -> None:
        registry = _registry_with()
        registry.get_categories = AsyncMock(
            return_value=["templates", "storage", "auth"]
        )
        with patch(
            "fastblocks.mcp.cli.get_registry_and_health",
            AsyncMock(return_value=(registry, MagicMock())),
        ):
            result = runner.invoke(cli, ["list-categories"])
        assert result.exit_code == 0
        assert "templates" in result.output
        assert "storage" in result.output
        assert "auth" in result.output

    def test_list_categories_filter_by_category(self, runner: CliRunner) -> None:
        registry = _registry_with()
        registry.get_adapters_by_category = AsyncMock(
            return_value=[_adapter_info(name="jinja2"), _adapter_info(name="htmy")],
        )
        with patch(
            "fastblocks.mcp.cli.get_registry_and_health",
            AsyncMock(return_value=(registry, MagicMock())),
        ):
            result = runner.invoke(cli, ["list-categories", "--category", "templates"])
        assert result.exit_code == 0
        assert "jinja2" in result.output
        assert "htmy" in result.output
        assert "templates" in result.output


@pytest.mark.unit
class TestInspect:
    def test_inspect_adapter_found_text_format(self, runner: CliRunner) -> None:
        registry = _registry_with()
        registry.get_adapter_info = AsyncMock(
            return_value=_adapter_info(name="jinja2"),
        )
        with patch(
            "fastblocks.mcp.cli.get_registry_and_health",
            AsyncMock(return_value=(registry, MagicMock())),
        ):
            result = runner.invoke(cli, ["inspect", "jinja2"])
        assert result.exit_code == 0
        assert "jinja2" in result.output
        assert "Jinja2Templates" in result.output

    def test_inspect_adapter_found_json_format(self, runner: CliRunner) -> None:
        registry = _registry_with()
        registry.get_adapter_info = AsyncMock(
            return_value=_adapter_info(name="jinja2", protocols=["http"]),
        )
        with patch(
            "fastblocks.mcp.cli.get_registry_and_health",
            AsyncMock(return_value=(registry, MagicMock())),
        ):
            result = runner.invoke(cli, ["inspect", "jinja2", "--format", "json"])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["name"] == "jinja2"
        assert payload["protocols"] == ["http"]

    def test_inspect_adapter_not_found(self, runner: CliRunner) -> None:
        registry = _registry_with()
        registry.get_adapter_info = AsyncMock(return_value=None)
        with patch(
            "fastblocks.mcp.cli.get_registry_and_health",
            AsyncMock(return_value=(registry, MagicMock())),
        ):
            result = runner.invoke(cli, ["inspect", "missing"])
        assert result.exit_code == 0
        # Click writes "Adapter 'X' not found" to stderr; CliRunner mixes it
        # into result.output by default, but we accept either form.
        assert "not found" in result.output


@pytest.mark.unit
class TestAudit:
    def test_audit_text_format_runs(self, runner: CliRunner, tmp_path: Path) -> None:
        config_file = tmp_path / "config.yaml"
        config_file.write_text("profile: development\n")
        report = MagicMock()
        report.configuration_name = "configuration"
        report.profile = "development"
        report.score = 92.0
        report.summary = {"total_findings": 1}
        report.findings = []
        report.recommendations = ["Use secret rotation."]
        report.to_dict = MagicMock(
            return_value={"configuration_name": "configuration", "score": 92.0}
        )
        # Stub both the registry/auditor chain and ConfigurationManager.
        with patch(
            "fastblocks.mcp.cli.ConfigurationManager.load_configuration",
            AsyncMock(return_value=MagicMock()),
        ):
            with patch(
                "fastblocks.mcp.cli.ConfigurationAuditor.audit_configuration",
                AsyncMock(return_value=report),
            ):
                result = runner.invoke(cli, ["audit", str(config_file)])
        assert result.exit_code == 0
        assert "Configuration Audit Report" in result.output
        assert "92" in result.output
        assert "Use secret rotation." in result.output

    def test_audit_json_format_writes_to_file(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        config_file = tmp_path / "config.yaml"
        config_file.write_text("profile: development\n")
        output_file = tmp_path / "report.json"
        report = MagicMock()
        report.configuration_name = "configuration"
        report.profile = "development"
        report.score = 80.0
        report.summary = {"total_findings": 0}
        report.findings = []
        report.recommendations = []

        with patch(
            "fastblocks.mcp.cli.ConfigurationManager.load_configuration",
            AsyncMock(return_value=MagicMock()),
        ):
            with patch(
                "fastblocks.mcp.cli.ConfigurationAuditor.audit_configuration",
                AsyncMock(return_value=report),
            ):
                result = runner.invoke(
                    cli,
                    [
                        "audit",
                        str(config_file),
                        "--format",
                        "json",
                        "--output",
                        str(output_file),
                    ],
                )
        assert result.exit_code == 0
        assert output_file.exists()
        payload = json.loads(output_file.read_text())
        assert payload["score"] == 80.0


@pytest.mark.unit
class TestMigrate:
    def test_migrate_compatible_dry_run_no_backup(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        config_file = tmp_path / "config.yaml"
        config_file.write_text("profile: development\nversion: 0.1.0\n")
        compatibility = {
            "compatible": True,
            "warnings": [],
            "current_version": "0.1.0",
            "target_version": "0.2.0",
            "migration_path": [],
        }

        class _StubManager:
            async def validate_migration_compatibility(self, *_args: object, **_kw: object):
                return compatibility

            async def create_migration_backup(self, *_args: object, **_kw: object):
                return tmp_path / "backup.yaml"

            async def migrate_configuration_file(self, *_args: object, **_kw: object):
                return MagicMock(success=True, version_from="0.1.0", version_to="0.2.0")

        # Stub the manager; the CLI auto-confirms via click.confirm so we
        # also stub click.confirm to return True (the default). Patch
        # click.confirm at module level since that's where the CLI looks.
        with patch(
            "fastblocks.mcp.cli.ConfigurationMigrationManager",
            _StubManager,
        ):
            with patch("fastblocks.mcp.cli.click.confirm", MagicMock(return_value=True)):
                result = runner.invoke(
                    cli,
                    [
                        "migrate",
                        str(config_file),
                        "0.2.0",
                        "--no-backup",
                    ],
                )
        # The compatibility gate runs; the result body should reflect that.
        assert result.exit_code == 0
        assert "Compatible" in result.output or "Migration" in result.output

    def test_migrate_incompatible_short_circuits(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        config_file = tmp_path / "config.yaml"
        config_file.write_text("profile: development\nversion: 0.1.0\n")

        class _StubManager:
            async def validate_migration_compatibility(self, *_args: object, **_kw: object):
                return {
                    "compatible": False,
                    "warnings": ["schema drift"],
                    "current_version": "0.1.0",
                    "target_version": "0.5.0",
                }

            async def migrate_configuration_file(self, *_args: object, **_kw: object):
                raise AssertionError("should not be called when incompatible")

        with patch(
            "fastblocks.mcp.cli.ConfigurationMigrationManager",
            _StubManager,
        ):
            result = runner.invoke(
                cli,
                ["migrate", str(config_file), "0.5.0"],
            )
        assert result.exit_code == 0
        # Incompatible path prints "Migration not possible: ...".
        assert "Migration not possible" in result.output
        assert "schema drift" in result.output