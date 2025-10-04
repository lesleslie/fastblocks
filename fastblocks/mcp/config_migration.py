"""Configuration migration tools for FastBlocks."""

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import yaml


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

    def _register_migration_steps(self) -> list[MigrationStep]:
        """Register all migration steps."""
        steps = []

        # 0.1.0 -> 0.2.0: Add adapter metadata
        # 0.2.0 -> 0.3.0: Add environment variable validation
        steps.extend(
            (
                MigrationStep(
                    name="add_adapter_metadata",
                    description="Add MODULE_ID and MODULE_STATUS metadata to adapters",
                    function=self._migrate_add_adapter_metadata,
                    version_from="0.1.0",
                    version_to="0.2.0",
                    direction=MigrationDirection.UPGRADE,
                ),
                MigrationStep(
                    name="add_env_validation",
                    description="Add validation patterns to environment variables",
                    function=self._migrate_add_env_validation,
                    version_from="0.2.0",
                    version_to="0.3.0",
                    direction=MigrationDirection.UPGRADE,
                ),
            )
        )

        # 0.3.0 -> 1.0.0: Production-ready schema
        # Reverse migrations
        steps.extend(
            (
                MigrationStep(
                    name="production_ready_schema",
                    description="Upgrade to production-ready configuration schema",
                    function=self._migrate_production_ready,
                    version_from="0.3.0",
                    version_to="1.0.0",
                    direction=MigrationDirection.UPGRADE,
                ),
                MigrationStep(
                    name="remove_production_features",
                    description="Downgrade from production-ready schema",
                    function=self._migrate_remove_production_features,
                    version_from="1.0.0",
                    version_to="0.3.0",
                    direction=MigrationDirection.DOWNGRADE,
                ),
            )
        )

        return steps

    async def migrate_configuration(
        self, config_data: dict[str, Any], target_version: str
    ) -> MigrationResult:
        """Migrate configuration to target version."""
        current_version = config_data.get("version", "0.1.0")

        if current_version == target_version:
            return MigrationResult(
                success=True,
                version_from=current_version,
                version_to=target_version,
                warnings=["Configuration is already at target version"],
            )

        # Determine migration path
        migration_path = self._get_migration_path(current_version, target_version)
        if not migration_path:
            return MigrationResult(
                success=False,
                version_from=current_version,
                version_to=target_version,
                errors=[
                    f"No migration path found from {current_version} to {target_version}"
                ],
            )

        # Execute migration steps
        result = MigrationResult(
            success=True, version_from=current_version, version_to=target_version
        )

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

        return result

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

        # Determine direction
        if from_idx < to_idx:
            direction = MigrationDirection.UPGRADE
            version_range = self.version_history[from_idx:to_idx]
        else:
            direction = MigrationDirection.DOWNGRADE
            version_range = list(reversed(self.version_history[to_idx:from_idx]))

        # Find applicable migration steps
        migration_path = []
        for i in range(len(version_range) - 1):
            current_version = version_range[i]
            next_version = version_range[i + 1]

            step = self._find_migration_step(current_version, next_version, direction)
            if step:
                migration_path.append(step)

            return []  # No migration path available

        return migration_path

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
    async def _migrate_add_adapter_metadata(
        self, config_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Add adapter metadata to configuration."""
        if "adapters" in config_data:
            for adapter_name, adapter_config in config_data["adapters"].items():
                if isinstance(adapter_config, dict):
                    # Add default metadata if not present
                    if "metadata" not in adapter_config:
                        adapter_config["metadata"] = {}

                    metadata = adapter_config["metadata"]
                    if "module_id" not in metadata:
                        import uuid

                        metadata["module_id"] = str(uuid.uuid4())

                    if "module_status" not in metadata:
                        metadata["module_status"] = "stable"

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

    def _add_production_global_settings(self, global_settings: dict[str, Any]) -> None:
        """Add production-specific global settings."""
        # Define production settings
        production_settings = {
            "security": {
                "force_https": True,
                "secure_cookies": True,
                "csrf_protection": True,
                "content_security_policy": True,
            },
            "monitoring": {
                "health_checks": True,
                "metrics_collection": True,
                "error_reporting": True,
            },
            "performance": {
                "caching_enabled": True,
                "compression_enabled": True,
                "static_file_optimization": True,
            },
        }

        # Add settings if not present
        for key, value in production_settings.items():
            global_settings.setdefault(key, value)

    def _upgrade_adapter_configs(self, adapters: dict[str, Any]) -> None:
        """Upgrade adapter configurations for production."""
        for adapter_config in adapters.values():
            if isinstance(adapter_config, dict):
                self._add_adapter_production_features(adapter_config)

    def _add_adapter_production_features(self, adapter_config: dict[str, Any]) -> None:
        """Add production features to adapter configuration."""
        # Add health check configuration
        adapter_config.setdefault(
            "health_check_config",
            {
                "enabled": True,
                "interval_seconds": 60,
                "timeout_seconds": 30,
            },
        )

        # Add profile-specific overrides
        adapter_config.setdefault(
            "profile_overrides",
            {
                "production": {"debug": False, "log_level": "WARNING"},
                "development": {"debug": True, "log_level": "DEBUG"},
            },
        )

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

    async def migrate_configuration_file(
        self, config_file: Path, target_version: str, output_file: Path | None = None
    ) -> MigrationResult:
        """Migrate configuration file to target version."""
        # Load configuration
        if not config_file.exists():
            return MigrationResult(
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
        except Exception as e:
            return MigrationResult(
                success=False,
                version_from="unknown",
                version_to=target_version,
                errors=[f"Failed to load configuration: {e}"],
            )

        # Perform migration
        result = await self.migrate_configuration(config_data, target_version)

        if result.success:
            # Save migrated configuration
            output_path = output_file or config_file
            try:
                with output_path.open("w") as f:
                    if output_path.suffix.lower() == ".json":
                        json.dump(config_data, f, indent=2)
                    else:
                        yaml.dump(config_data, f, default_flow_style=False)
            except Exception as e:
                result.success = False
                result.errors.append(f"Failed to save migrated configuration: {e}")

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

    async def validate_migration_compatibility(
        self, config_file: Path, target_version: str
    ) -> dict[str, Any]:
        """Validate if migration is possible and safe."""
        current_version = self._detect_configuration_version(config_file)

        result: dict[str, Any] = {
            "compatible": False,
            "current_version": current_version,
            "target_version": target_version,
            "migration_path": [],
            "warnings": [],
            "requirements": [],
        }

        if current_version == "unknown":
            result["warnings"].append("Cannot detect current configuration version")
            return result

        # Get migration path
        migration_path = self._get_migration_path(current_version, target_version)
        if not migration_path:
            result["warnings"].append(
                f"No migration path available from {current_version} to {target_version}"
            )
            return result

        result["compatible"] = True
        result["migration_path"] = [step.name for step in migration_path]

        # Check for potential issues
        for step in migration_path:
            if step.direction == MigrationDirection.DOWNGRADE:
                result["warnings"].append(
                    f"Step '{step.name}' is a downgrade and may result in data loss"
                )

        # Add requirements
        result["requirements"] = [
            "Backup will be created automatically",
            "Configuration file will be updated in place",
            "Verify adapter compatibility after migration",
        ]

        return result
