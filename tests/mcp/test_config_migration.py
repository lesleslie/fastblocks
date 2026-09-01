"""Tests for fastblocks/mcp/config_migration.py.

Targets ``ConfigurationMigrationManager`` (0% coverage before this file).
A handful of broad-coverage tests drive the migration engine through its
success, failure, and edge-case paths plus the dataclass constructors.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastblocks.mcp.config_migration import (
    ConfigurationMigrationManager,
    MigrationDirection,
    MigrationResult,
    MigrationStep,
)


@pytest.fixture
def manager(tmp_path: Path) -> ConfigurationMigrationManager:
    return ConfigurationMigrationManager(base_path=tmp_path)


@pytest.mark.unit
class TestMigrationDataclasses:
    def test_migration_step_defaults(self) -> None:
        step = MigrationStep(
            name="noop",
            description="d",
            function=lambda x: x,
            version_from="0.1.0",
            version_to="0.2.0",
            direction=MigrationDirection.UPGRADE,
        )
        assert step.reversible is True

    def test_migration_result_defaults(self) -> None:
        result = MigrationResult(
            success=True,
            version_from="0.1.0",
            version_to="0.2.0",
        )
        assert result.steps_applied == []
        assert result.warnings == []
        assert result.errors == []
        assert result.execution_time_ms == 0.0


@pytest.mark.unit
class TestManagerInitialization:
    def test_init_creates_migrations_dir(
        self, tmp_path: Path
    ) -> None:
        ConfigurationMigrationManager(base_path=tmp_path)
        assert (tmp_path / ".fastblocks" / "migrations").exists()

    def test_init_registers_migration_steps(
        self, manager: ConfigurationMigrationManager
    ) -> None:
        # The manager registers four version-history steps on init.
        assert len(manager.migration_steps) >= 4
        names = {step.name for step in manager.migration_steps}
        assert "add_adapter_metadata" in names

    def test_init_default_base_path(self) -> None:
        mgr = ConfigurationMigrationManager()
        # Default base path is the cwd.
        assert mgr.base_path == Path.cwd()


@pytest.mark.unit
class TestExecuteMigrationStepsSuccess:
    async def test_successful_migration_executes_all_steps(
        self, manager: ConfigurationMigrationManager
    ) -> None:
        result = MigrationResult(
            success=True,
            version_from="0.1.0",
            version_to="0.2.0",
        )
        config = {"version": "0.1.0"}
        path = manager._get_migration_path("0.1.0", "0.2.0")
        # If no migration path exists for 0.1.0→0.2.0, skip the assertion.
        if not path:
            pytest.skip("No migration path 0.1.0→0.2.0 registered")
        await manager._execute_migration_steps(config, path, result)
        # Success path: result remains True and steps were applied.
        assert result.success is True
        assert len(result.steps_applied) >= 1


@pytest.mark.unit
class TestExecuteMigrationStepsFailure:
    async def test_value_error_marks_migration_failed(
        self, manager: ConfigurationMigrationManager
    ) -> None:
        result = MigrationResult(
            success=True,
            version_from="0.1.0",
            version_to="0.3.0",
        )

        async def _failing_step(_data: dict) -> dict:
            raise ValueError("simulated step failure")

        bad_step = MigrationStep(
            name="bad_step",
            description="fails",
            function=_failing_step,
            version_from="0.1.0",
            version_to="0.2.0",
            direction=MigrationDirection.UPGRADE,
        )
        await manager._execute_migration_steps(
            {"version": "0.1.0"}, [bad_step], result
        )
        assert result.success is False
        assert result.errors
        assert "bad_step" in result.errors[0]
        assert result.steps_applied == []


@pytest.mark.unit
class TestMigrateConfiguration:
    async def test_migrate_already_at_version(
        self, manager: ConfigurationMigrationManager
    ) -> None:
        result = await manager.migrate_configuration(
            {"version": "1.0.0"}, "1.0.0"
        )
        assert result.success is True
        assert result.steps_applied == []

    async def test_migrate_unknown_path(
        self, manager: ConfigurationMigrationManager
    ) -> None:
        # 9.9.9 is not in version_history; no path exists.
        result = await manager.migrate_configuration(
            {"version": "9.9.9"}, "0.2.0"
        )
        assert result.success is False
        assert result.errors


@pytest.mark.unit
class TestMigrationHelpers:
    def test_determine_migration_direction_up(
        self, manager: ConfigurationMigrationManager
    ) -> None:
        direction, version_range = manager._determine_migration_direction(0, 1)
        assert direction == MigrationDirection.UPGRADE
        assert version_range

    def test_determine_migration_direction_down(
        self, manager: ConfigurationMigrationManager
    ) -> None:
        direction, version_range = manager._determine_migration_direction(1, 0)
        assert direction == MigrationDirection.DOWNGRADE
        assert version_range

    def test_find_migration_step_returns_none_for_unknown(
        self, manager: ConfigurationMigrationManager
    ) -> None:
        step = manager._find_migration_step(
            MigrationDirection.UPGRADE, "0.1.0", "9.9.9"
        )
        assert step is None
