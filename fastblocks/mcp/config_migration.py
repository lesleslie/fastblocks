"""Configuration migration tools for FastBlocks."""

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, cast

import yaml

# Module-level constants for migration defaults
_DEFAULT_ADAPTER_METADATA = {
    "module_id_generator": lambda: __import__("uuid").uuid4(),
    "module_status": "stable",
}


class MigrationDirection(str, Enum):
    """Migration direction."""

    UPGRADE = "upgrade"
    DOWNGRADE = "downgrade"


@dataclass
class MigrationStep:
    """A single migration step."""

    name: str
    description: str
    function: Callable[..., Any]
    version_from: str
    version_to: str
    direction: MigrationDirection
    reversible: bool = True


@dataclass
class MigrationResult:
    """Result of a migration operation."""

    success: bool
    version_from: str
    version_to: str
    steps_applied: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    execution_time_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


class ConfigurationMigrationManager:
    """Manages configuration migrations between versions."""

    def __init__(self, base_path: Path | None = None):
        """Initialize migration manager."""
        self.base_path = base_path or Path.cwd()
        self.migrations_dir = self.base_path / ".fastblocks" / "migrations"
        self.migrations_dir.mkdir(parents=True, exist_ok=True)

        # Version history
        self.version_history = [
            "0.1.0",  # Initial version
            "0.2.0",  # Added adapter metadata
            "0.3.0",  # Added environment variable validation
            "1.0.0",  # Production-ready configuration schema
        ]

        # Register migration steps
        self.migration_steps = self._register_migration_steps()

    def _create_metadata_migration_step(self) -> MigrationStep:
        """Create migration step for adding adapter metadata."""
        return MigrationStep(
            name="add_adapter_metadata",
            description="Add MODULE_ID and MODULE_STATUS metadata to adapters",
            function=self._migrate_add_adapter_metadata,
            version_from="0.1.0",
            version_to="0.2.0",
            direction=MigrationDirection.UPGRADE,
        )

    def _create_env_validation_step(self) -> MigrationStep:
        """Create migration step for environment variable validation."""
        return MigrationStep(
            name="add_env_validation",
            description="Add validation patterns to environment variables",
            function=self._migrate_add_env_validation,
            version_from="0.2.0",
            version_to="0.3.0",
            direction=MigrationDirection.UPGRADE,
        )

    def _create_production_upgrade_step(self) -> MigrationStep:
        """Create migration step for production-ready upgrade."""
        return MigrationStep(
            name="production_ready_schema",
            description="Upgrade to production-ready configuration schema",
            function=self._migrate_production_ready,
            version_from="0.3.0",
            version_to="1.0.0",
            direction=MigrationDirection.UPGRADE,
        )

    def _create_production_downgrade_step(self) -> MigrationStep:
        """Create migration step for production downgrade."""
        return MigrationStep(
            name="remove_production_features",
            description="Downgrade from production-ready schema",
            function=self._migrate_remove_production_features,
            version_from="1.0.0",
            version_to="0.3.0",
            direction=MigrationDirection.DOWNGRADE,
        )

    def _register_migration_steps(self) -> list[MigrationStep]:
        """Register all migration steps."""
        return [
            self._create_metadata_migration_step(),
            self._create_env_validation_step(),
            self._create_production_upgrade_step(),
            self._create_production_downgrade_step(),
        ]

    def _create_already_at_version_result(
        self, current_version: str, target_version: str
    ) -> MigrationResult:
        """Create result when already at target version."""
        return MigrationResult(
            success=True,
            version_from=current_version,
            version_to=target_version,
            warnings=["Configuration is already at target version"],
        )

    def _create_no_path_result(
        self, current_version: str, target_version: str
    ) -> MigrationResult:
        """Create result when no migration path exists."""
        return MigrationResult(
            success=False,
            version_from=current_version,
            version_to=target_version,
            errors=[
                f"No migration path found from {current_version} to {target_version}"
            ],
        )

    async def _execute_migration_steps(
        self,
        config_data: dict[str, Any],
        migration_path: list[MigrationStep],
        result: MigrationResult,
    ) -> dict[str, Any]:
        """Execute migration steps and update result."""
        current_data = config_data.copy()

        for step in migration_path:
            try:
                current_data = await step.function(current_data)
                result.steps_applied.append(step.name)
                current_data["version"] = step.version_to
            except Exception as e:
                result.success = False
                result.errors.append(f"Migration step '{step.name}' failed: {e}")
                break

        return current_data

    async def migrate_configuration(
        self, config_data: dict[str, Any], target_version: str
    ) -> MigrationResult:
        """Migrate configuration to target version."""
        current_version = config_data.get("version", "0.1.0")

        if current_version == target_version:
            return self._create_already_at_version_result(
                current_version, target_version
            )

        migration_path = self._get_migration_path(current_version, target_version)
        if not migration_path:
            return self._create_no_path_result(current_version, target_version)

        result = MigrationResult(
            success=True, version_from=current_version, version_to=target_version
        )

        await self._execute_migration_steps(config_data, migration_path, result)

        return result

    def _determine_migration_direction(
        self, from_idx: int, to_idx: int
    ) -> tuple[MigrationDirection, list[str]]:
        """Determine migration direction and version range."""
        if from_idx < to_idx:
            direction = MigrationDirection.UPGRADE
            version_range = self.version_history[from_idx:to_idx]
        else:
            direction = MigrationDirection.DOWNGRADE
            version_range = list(reversed(self.version_history[to_idx:from_idx]))
        return direction, version_range

    def _build_migration_path(
        self, version_range: list[str], direction: MigrationDirection
    ) -> list[MigrationStep]:
        """Build migration path from version range."""
        migration_path = []
        for i in range(len(version_range) - 1):
            current_version = version_range[i]
            next_version = version_range[i + 1]

            step = self._find_migration_step(current_version, next_version, direction)
            if step:
                migration_path.append(step)
            else:
                return []  # No migration path available if any step is missing

        return migration_path

    def _get_migration_path(
        self, from_version: str, to_version: str
    ) -> list[MigrationStep]:
        """Get migration path between versions."""
        if (
            from_version not in self.version_history
            or to_version not in self.version_history
        ):
            return []

        from_idx = self.version_history.index(from_version)
        to_idx = self.version_history.index(to_version)

        if from_idx == to_idx:
            return []

        direction, version_range = self._determine_migration_direction(from_idx, to_idx)
        return self._build_migration_path(version_range, direction)

    def _find_migration_step(
        self, from_version: str, to_version: str, direction: MigrationDirection
    ) -> MigrationStep | None:
        """Find migration step for specific version transition."""
        for step in self.migration_steps:
            if (
                step.version_from == from_version
                and step.version_to == to_version
                and step.direction == direction
            ):
                return step
        return None

    # Migration functions
    def _ensure_adapter_metadata(self, adapter_config: dict[str, Any]) -> None:
        """Ensure adapter has required metadata fields."""
        if "metadata" not in adapter_config:
            adapter_config["metadata"] = {}

        metadata = adapter_config["metadata"]
        if "module_id" not in metadata:
            # Cast to Callable since dict lookup returns Any
            generator = cast(
                Callable[[], Any], _DEFAULT_ADAPTER_METADATA["module_id_generator"]
            )
            metadata["module_id"] = str(generator())

        if "module_status" not in metadata:
            metadata["module_status"] = _DEFAULT_ADAPTER_METADATA["module_status"]

    async def _migrate_add_adapter_metadata(
        self, config_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Add adapter metadata to configuration."""
        if "adapters" not in config_data:
            return config_data

        for adapter_config in config_data["adapters"].values():
            if isinstance(adapter_config, dict):
                self._ensure_adapter_metadata(adapter_config)

        return config_data

    async def _migrate_add_env_validation(
        self, config_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Add environment variable validation patterns."""
        # Add validation patterns to global environment variables
        if "global_environment" in config_data:
            self._add_validation_to_env_vars(config_data["global_environment"])

        # Add validation patterns to adapter environment variables
        if "adapters" in config_data:
            self._add_validation_to_adapter_env_vars(config_data["adapters"])

        return config_data

    def _add_validation_to_env_vars(self, env_vars: list[dict[str, Any]]) -> None:
        """Add validation patterns to environment variables."""
        for env_var in env_vars:
            if isinstance(env_var, dict) and "validator_pattern" not in env_var:
                env_var["validator_pattern"] = self._suggest_validation_pattern(
                    env_var.get("name", "")
                )

    def _add_validation_to_adapter_env_vars(self, adapters: dict[str, Any]) -> None:
        """Add validation patterns to adapter environment variables."""
        for adapter_config in adapters.values():
            if not isinstance(adapter_config, dict):
                continue
            if "environment_variables" not in adapter_config:
                continue

            self._add_validation_to_env_vars(adapter_config["environment_variables"])

    async def _migrate_production_ready(
        self, config_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Upgrade to production-ready configuration schema."""
        # Initialize and configure global settings
        global_settings = config_data.setdefault("global_settings", {})
        self._add_production_global_settings(global_settings)

        # Upgrade adapter configurations
        if "adapters" in config_data:
            self._upgrade_adapter_configs(config_data["adapters"])

        return config_data

    def _get_security_settings(self) -> dict[str, bool]:
        """Get production security settings."""
        return {
            "force_https": True,
            "secure_cookies": True,
            "csrf_protection": True,
            "content_security_policy": True,
        }

    def _get_monitoring_settings(self) -> dict[str, bool]:
        """Get production monitoring settings."""
        return {
            "health_checks": True,
            "metrics_collection": True,
            "error_reporting": True,
        }

    def _get_performance_settings(self) -> dict[str, bool]:
        """Get production performance settings."""
        return {
            "caching_enabled": True,
            "compression_enabled": True,
            "static_file_optimization": True,
        }

    def _add_production_global_settings(self, global_settings: dict[str, Any]) -> None:
        """Add production-specific global settings."""
        production_settings = {
            "security": self._get_security_settings(),
            "monitoring": self._get_monitoring_settings(),
            "performance": self._get_performance_settings(),
        }

        for key, value in production_settings.items():
            global_settings.setdefault(key, value)

    def _upgrade_adapter_configs(self, adapters: dict[str, Any]) -> None:
        """Upgrade adapter configurations for production."""
        for adapter_config in adapters.values():
            if isinstance(adapter_config, dict):
                self._add_adapter_production_features(adapter_config)

    def _get_health_check_config(self) -> dict[str, Any]:
        """Get default health check configuration."""
        return {
            "enabled": True,
            "interval_seconds": 60,
            "timeout_seconds": 30,
        }

    def _get_profile_overrides(self) -> dict[str, dict[str, Any]]:
        """Get default profile overrides."""
        return {
            "production": {"debug": False, "log_level": "WARNING"},
            "development": {"debug": True, "log_level": "DEBUG"},
        }

    def _add_adapter_production_features(self, adapter_config: dict[str, Any]) -> None:
        """Add production features to adapter configuration."""
        adapter_config.setdefault(
            "health_check_config", self._get_health_check_config()
        )
        adapter_config.setdefault("profile_overrides", self._get_profile_overrides())

    async def _migrate_remove_production_features(
        self, config_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Remove production-specific features for downgrade."""
        # Remove production-specific global settings
        if "global_settings" in config_data:
            global_settings = config_data["global_settings"]
            for key in ("security", "monitoring", "performance"):
                global_settings.pop(key, None)

        # Remove adapter production features
        if "adapters" in config_data:
            for adapter_config in config_data["adapters"].values():
                if isinstance(adapter_config, dict):
                    adapter_config.pop("health_check_config", None)
                    adapter_config.pop("profile_overrides", None)

        return config_data

    def _suggest_validation_pattern(self, var_name: str) -> str | None:
        """Suggest validation pattern based on variable name."""
        name_lower = var_name.lower()

        if "url" in name_lower:
            return r"^https?://[^\s/$.?#].[^\s]*$"
        elif "email" in name_lower:
            return r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        elif "port" in name_lower:
            return r"^([1-9][0-9]{0,3}|[1-5][0-9]{4}|6[0-4][0-9]{3}|65[0-4][0-9]{2}|655[0-2][0-9]|6553[0-5])$"
        elif "debug" in name_lower or "enable" in name_lower:
            return r"^(true|false|1|0|yes|no|on|off)$"
        elif "log" in name_lower and "level" in name_lower:
            return r"^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$"

        return None

    def _load_config_file(
        self, config_file: Path, target_version: str
    ) -> tuple[dict[str, Any] | None, MigrationResult | None]:
        """Load configuration file and return data or error result."""
        if not config_file.exists():
            return None, MigrationResult(
                success=False,
                version_from="unknown",
                version_to=target_version,
                errors=[f"Configuration file not found: {config_file}"],
            )

        try:
            with config_file.open() as f:
                if config_file.suffix.lower() == ".json":
                    config_data = json.load(f)
                else:
                    config_data = yaml.safe_load(f)
            return config_data, None
        except Exception as e:
            return None, MigrationResult(
                success=False,
                version_from="unknown",
                version_to=target_version,
                errors=[f"Failed to load configuration: {e}"],
            )

    def _save_config_file(
        self, config_data: dict[str, Any], output_path: Path, result: MigrationResult
    ) -> None:
        """Save migrated configuration to file and update result on error."""
        try:
            with output_path.open("w") as f:
                if output_path.suffix.lower() == ".json":
                    json.dump(config_data, f, indent=2)
                else:
                    yaml.dump(config_data, f, default_flow_style=False)
        except Exception as e:
            result.success = False
            result.errors.append(f"Failed to save migrated configuration: {e}")

    async def migrate_configuration_file(
        self, config_file: Path, target_version: str, output_file: Path | None = None
    ) -> MigrationResult:
        """Migrate configuration file to target version."""
        # Load configuration
        config_data, error_result = self._load_config_file(config_file, target_version)
        if error_result:
            return error_result

        # Perform migration
        result = await self.migrate_configuration(
            cast(dict[str, Any], config_data), target_version
        )

        if result.success:
            # Save migrated configuration
            output_path = output_file or config_file
            self._save_config_file(
                cast(dict[str, Any], config_data), output_path, result
            )

        return result

    def get_current_schema_version(self) -> str:
        """Get the current schema version."""
        return self.version_history[-1]

    def get_supported_versions(self) -> list[str]:
        """Get list of supported configuration versions."""
        return self.version_history.copy()

    async def create_migration_backup(
        self, config_file: Path, target_version: str
    ) -> Path:
        """Create backup before migration."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{config_file.stem}_backup_{timestamp}{config_file.suffix}"
        backup_path = self.migrations_dir / backup_name

        # Copy original file
        import shutil

        shutil.copy2(config_file, backup_path)

        # Create migration metadata
        metadata = {
            "original_file": str(config_file),
            "backup_created": datetime.now().isoformat(),
            "target_version": target_version,
            "original_version": self._detect_configuration_version(config_file),
        }

        metadata_path = backup_path.with_suffix(".metadata.json")
        with metadata_path.open("w") as f:
            json.dump(metadata, f, indent=2)

        return backup_path

    def _detect_configuration_version(self, config_file: Path) -> str:
        """Detect version of configuration file."""
        try:
            with config_file.open() as f:
                if config_file.suffix.lower() == ".json":
                    config_data = json.load(f)
                else:
                    config_data = yaml.safe_load(f)

            version: str = config_data.get("version", "0.1.0")
            return version
        except Exception:
            return "unknown"

    def _create_compatibility_result(
        self, current_version: str, target_version: str
    ) -> dict[str, Any]:
        """Create initial compatibility result structure."""
        return {
            "compatible": False,
            "current_version": current_version,
            "target_version": target_version,
            "migration_path": [],
            "warnings": [],
            "requirements": [],
        }

    def _check_version_unknown(
        self, current_version: str, result: dict[str, Any]
    ) -> bool:
        """Check if version is unknown and update result."""
        if current_version == "unknown":
            result["warnings"].append("Cannot detect current configuration version")
            return True
        return False

    def _check_migration_path_exists(
        self, migration_path: list[MigrationStep], result: dict[str, Any]
    ) -> bool:
        """Check if migration path exists and update result."""
        if not migration_path:
            current_v = result["current_version"]
            target_v = result["target_version"]
            result["warnings"].append(
                f"No migration path available from {current_v} to {target_v}"
            )
            return False
        return True

    def _add_downgrade_warnings(
        self, migration_path: list[MigrationStep], result: dict[str, Any]
    ) -> None:
        """Add warnings for downgrade steps in migration path."""
        for step in migration_path:
            if step.direction == MigrationDirection.DOWNGRADE:
                result["warnings"].append(
                    f"Step '{step.name}' is a downgrade and may result in data loss"
                )

    def _add_migration_requirements(self, result: dict[str, Any]) -> None:
        """Add migration requirements to result."""
        result["requirements"] = [
            "Backup will be created automatically",
            "Configuration file will be updated in place",
            "Verify adapter compatibility after migration",
        ]

    async def validate_migration_compatibility(
        self, config_file: Path, target_version: str
    ) -> dict[str, Any]:
        """Validate if migration is possible and safe."""
        current_version = self._detect_configuration_version(config_file)

        result = self._create_compatibility_result(current_version, target_version)

        if self._check_version_unknown(current_version, result):
            return result

        # Get migration path
        migration_path = self._get_migration_path(current_version, target_version)
        if not self._check_migration_path_exists(migration_path, result):
            return result

        result["compatible"] = True
        result["migration_path"] = [step.name for step in migration_path]

        # Check for potential issues
        self._add_downgrade_warnings(migration_path, result)

        # Add requirements
        self._add_migration_requirements(result)

        return result
