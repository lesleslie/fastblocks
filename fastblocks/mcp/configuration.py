"""Advanced adapter configuration management for FastBlocks MCP system."""

import json
import os
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4

import yaml
from pydantic import BaseModel, Field, ValidationError, field_validator

from .discovery import AdapterInfo
from .registry import AdapterRegistry


class ConfigurationProfile(str, Enum):
    """Configuration deployment profiles."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class ConfigurationStatus(str, Enum):
    """Configuration validation status."""

    VALID = "valid"
    WARNING = "warning"
    ERROR = "error"
    UNKNOWN = "unknown"


@dataclass
class EnvironmentVariable:
    """Environment variable configuration."""

    name: str
    value: str | None = None
    required: bool = True
    description: str = ""
    secret: bool = False
    default: str | None = None
    validator_pattern: str | None = None


@dataclass
class AdapterConfiguration:
    """Individual adapter configuration."""

    name: str
    enabled: bool = True
    settings: dict[str, Any] = field(default_factory=dict)
    environment_variables: list[EnvironmentVariable] = field(default_factory=list)
    dependencies: set[str] = field(default_factory=set)
    profile_overrides: dict[ConfigurationProfile, dict[str, Any]] = field(
        default_factory=dict
    )
    health_check_config: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


class ConfigurationSchema(BaseModel):
    """Pydantic schema for configuration validation."""

    version: str = "1.0"
    profile: ConfigurationProfile = ConfigurationProfile.DEVELOPMENT
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    adapters: dict[str, AdapterConfiguration] = Field(default_factory=dict)
    global_settings: dict[str, Any] = Field(default_factory=dict)
    global_environment: list[EnvironmentVariable] = Field(default_factory=list)

    @field_validator("adapters", mode="before")
    @classmethod
    def validate_adapters(cls, v: Any) -> dict[str, AdapterConfiguration]:
        if isinstance(v, dict):
            # Convert dict values to AdapterConfiguration objects if needed
            result: dict[str, AdapterConfiguration] = {}
            for key, value in v.items():
                if isinstance(value, dict):
                    result[key] = AdapterConfiguration(name=key, **value)
                else:
                    result[key] = value
            return result
        # v should already be dict[str, AdapterConfiguration] if not dict
        return v if isinstance(v, dict) else {}

    class Config:
        arbitrary_types_allowed = True


@dataclass
class ConfigurationValidationResult:
    """Result of configuration validation."""

    status: ConfigurationStatus
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    info: dict[str, Any] = field(default_factory=dict)
    adapter_results: dict[str, dict[str, Any]] = field(default_factory=dict)


@dataclass
class ConfigurationBackup:
    """Configuration backup metadata."""

    id: str
    name: str
    description: str
    created_at: datetime
    profile: ConfigurationProfile
    file_path: Path
    checksum: str


class ConfigurationManager:
    """Advanced configuration management for FastBlocks adapters."""

    def __init__(self, registry: AdapterRegistry, base_path: Path | None = None):
        """Initialize configuration manager."""
        self.registry = registry
        self.base_path = base_path or Path.cwd() / ".fastblocks"
        self.config_dir = self.base_path / "config"
        self.backup_dir = self.base_path / "backups"
        self.templates_dir = self.base_path / "templates"

        # Ensure directories exist
        for directory in (self.config_dir, self.backup_dir, self.templates_dir):
            directory.mkdir(parents=True, exist_ok=True)

    async def initialize(self) -> None:
        """Initialize configuration manager."""
        await self.registry.initialize()
        await self._ensure_default_templates()

    async def get_available_adapters(self) -> dict[str, AdapterInfo]:
        """Get all available adapters for configuration."""
        return await self.registry.list_available_adapters()

    async def get_adapter_configuration_schema(
        self, adapter_name: str
    ) -> dict[str, Any]:
        """Get configuration schema for a specific adapter."""
        adapter_info = await self.registry.get_adapter_info(adapter_name)
        if not adapter_info:
            raise ValueError(f"Adapter '{adapter_name}' not found")

        # Build base schema
        schema = self._build_base_schema(adapter_name, adapter_info)

        # Try to introspect adapter settings
        with suppress(Exception):
            adapter = await self.registry.get_adapter(adapter_name)
            self._introspect_adapter_settings(adapter, schema)

        return schema

    def _build_base_schema(
        self, adapter_name: str, adapter_info: AdapterInfo
    ) -> dict[str, Any]:
        """Build base schema structure."""
        return {
            "name": adapter_name,
            "description": adapter_info.description,
            "category": adapter_info.category,
            "required_settings": [],
            "optional_settings": [],
            "environment_variables": [],
            "dependencies": [],
        }

    def _introspect_adapter_settings(
        self, adapter: Any, schema: dict[str, Any]
    ) -> None:
        """Introspect adapter settings and populate schema."""
        if not adapter or not hasattr(adapter, "settings"):
            return

        settings = adapter.settings
        if not hasattr(settings, "__dict__"):
            return

        # Categorize settings by requirement
        categorized = self._categorize_settings(settings.__dict__)
        schema["required_settings"] = categorized["required"]
        schema["optional_settings"] = categorized["optional"]

    def _categorize_settings(
        self, settings_dict: dict[str, Any]
    ) -> dict[str, list[dict[str, Any]]]:
        """Categorize settings into required and optional."""
        categorized: dict[str, list[dict[str, Any]]] = {
            "required": [],
            "optional": [],
        }

        for key, value in settings_dict.items():
            if key.startswith("_"):
                continue

            setting_info = {
                "name": key,
                "type": type(value).__name__,
                "default": value,
                "required": value is None,
            }

            category = "required" if setting_info["required"] else "optional"
            categorized[category].append(setting_info)

        return categorized

    async def create_configuration(
        self,
        profile: ConfigurationProfile = ConfigurationProfile.DEVELOPMENT,
        adapters: list[str] | None = None,
    ) -> ConfigurationSchema:
        """Create a new configuration."""
        config = ConfigurationSchema(profile=profile)

        if adapters:
            for adapter_name in adapters:
                adapter_config = await self._create_adapter_configuration(adapter_name)
                config.adapters[adapter_name] = adapter_config

        return config

    async def _create_adapter_configuration(
        self, adapter_name: str
    ) -> AdapterConfiguration:
        """Create configuration for a specific adapter."""
        schema = await self.get_adapter_configuration_schema(adapter_name)

        adapter_config = AdapterConfiguration(name=adapter_name)

        # Set up environment variables based on schema
        for setting in schema.get("required_settings", []):
            env_var = EnvironmentVariable(
                name=f"FB_{adapter_name.upper()}_{setting['name'].upper()}",
                required=True,
                description=f"Required setting for {adapter_name}: {setting['name']}",
            )
            adapter_config.environment_variables.append(env_var)

        for setting in schema.get("optional_settings", []):
            env_var = EnvironmentVariable(
                name=f"FB_{adapter_name.upper()}_{setting['name'].upper()}",
                required=False,
                default=str(setting.get("default", "")),
                description=f"Optional setting for {adapter_name}: {setting['name']}",
            )
            adapter_config.environment_variables.append(env_var)

        return adapter_config

    async def validate_configuration(
        self, config: ConfigurationSchema
    ) -> ConfigurationValidationResult:
        """Validate a configuration comprehensively."""
        result = ConfigurationValidationResult(status=ConfigurationStatus.VALID)

        try:
            # Validate configuration schema
            config_dict = (
                config.model_dump()
                if hasattr(config, "model_dump")
                else config.__dict__
            )
            ConfigurationSchema(**config_dict)
        except ValidationError as e:
            result.status = ConfigurationStatus.ERROR
            result.errors.extend([str(error) for error in e.errors()])
        except Exception as e:
            result.status = ConfigurationStatus.ERROR
            result.errors.append(f"Configuration validation error: {e}")

        # Validate individual adapters
        for adapter_name, adapter_config in config.adapters.items():
            adapter_result = await self._validate_adapter_configuration(
                adapter_name, adapter_config
            )
            result.adapter_results[adapter_name] = adapter_result

            if adapter_result.get("errors"):
                result.errors.extend(
                    f"{adapter_name}: {error}" for error in adapter_result["errors"]
                )
                result.status = ConfigurationStatus.ERROR

            if adapter_result.get("warnings"):
                result.warnings.extend(
                    f"{adapter_name}: {warning}"
                    for warning in adapter_result["warnings"]
                )
                if result.status == ConfigurationStatus.VALID:
                    result.status = ConfigurationStatus.WARNING

        # Validate dependencies
        await self._validate_dependencies(config, result)

        # Validate environment variables
        await self._validate_environment_variables(config, result)

        return result

    async def _validate_adapter_configuration(
        self, adapter_name: str, adapter_config: AdapterConfiguration
    ) -> dict[str, Any]:
        """Validate individual adapter configuration."""
        validation_result = await self.registry.validate_adapter(adapter_name)

        result = {
            "valid": validation_result.get("valid", False),
            "errors": validation_result.get("errors", []),
            "warnings": validation_result.get("warnings", []),
            "info": validation_result.get("info", {}),
        }

        # Additional configuration-specific validations
        if adapter_config.enabled:
            # Check required environment variables
            for env_var in adapter_config.environment_variables:
                if env_var.required and not env_var.value and not env_var.default:
                    if env_var.name not in os.environ:
                        result["warnings"].append(
                            f"Required environment variable {env_var.name} is not set"
                        )

        return result

    async def _validate_dependencies(
        self, config: ConfigurationSchema, result: ConfigurationValidationResult
    ) -> None:
        """Validate adapter dependencies."""
        enabled_adapters = {
            name for name, adapter in config.adapters.items() if adapter.enabled
        }

        for adapter_name, adapter_config in config.adapters.items():
            if not adapter_config.enabled:
                continue

            for dependency in adapter_config.dependencies:
                if dependency not in enabled_adapters:
                    result.errors.append(
                        f"Adapter '{adapter_name}' depends on '{dependency}' which is not enabled"
                    )
                    result.status = ConfigurationStatus.ERROR

    def _check_duplicate_env_vars(
        self,
        config: ConfigurationSchema,
        result: ConfigurationValidationResult,
        all_env_vars: set[str],
    ) -> None:
        """Check for duplicate environment variable names."""
        for adapter_config in config.adapters.values():
            for env_var in adapter_config.environment_variables:
                if env_var.name in all_env_vars:
                    result.warnings.append(
                        f"Duplicate environment variable: {env_var.name}"
                    )
                all_env_vars.add(env_var.name)

    def _is_env_var_missing(self, env_var: EnvironmentVariable) -> bool:
        """Check if a required environment variable is missing."""
        return (
            env_var.required
            and not env_var.value
            and not env_var.default
            and env_var.name not in os.environ
        )

    def _check_missing_required_vars(
        self, config: ConfigurationSchema, result: ConfigurationValidationResult
    ) -> None:
        """Check for missing required environment variables."""
        for adapter_name, adapter_config in config.adapters.items():
            if not adapter_config.enabled:
                continue

            for env_var in adapter_config.environment_variables:
                if self._is_env_var_missing(env_var):
                    result.warnings.append(
                        f"Required environment variable {env_var.name} for {adapter_name} is not set"
                    )

    async def _validate_environment_variables(
        self, config: ConfigurationSchema, result: ConfigurationValidationResult
    ) -> None:
        """Validate environment variable configuration."""
        all_env_vars: set[str] = set()

        # Check for duplicate environment variable names
        self._check_duplicate_env_vars(config, result, all_env_vars)

        # Check for missing required variables
        self._check_missing_required_vars(config, result)

    async def save_configuration(
        self, config: ConfigurationSchema, name: str | None = None
    ) -> Path:
        """Save configuration to YAML file."""
        if not name:
            name = f"{config.profile.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        config_file = self.config_dir / f"{name}.yaml"

        # Convert to serializable dict
        config_dict = self._serialize_configuration(config)

        with config_file.open("w") as f:
            yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)

        return config_file

    async def load_configuration(self, name_or_path: str | Path) -> ConfigurationSchema:
        """Load configuration from YAML file."""
        if isinstance(name_or_path, str):
            config_file = self.config_dir / f"{name_or_path}.yaml"
            if not config_file.exists():
                config_file = Path(name_or_path)
        else:
            config_file = name_or_path

        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_file}")

        with config_file.open() as f:
            config_dict = yaml.safe_load(f)

        return self._deserialize_configuration(config_dict)

    def _serialize_configuration(self, config: ConfigurationSchema) -> dict[str, Any]:
        """Convert configuration to serializable dictionary."""
        result = {
            "version": config.version,
            "profile": config.profile.value,
            "created_at": config.created_at.isoformat(),
            "updated_at": config.updated_at.isoformat(),
            "global_settings": config.global_settings,
            "global_environment": [
                {
                    "name": env_var.name,
                    "value": env_var.value,
                    "required": env_var.required,
                    "description": env_var.description,
                    "secret": env_var.secret,
                    "default": env_var.default,
                    "validator_pattern": env_var.validator_pattern,
                }
                for env_var in config.global_environment
            ],
            "adapters": {},
        }

        adapters_dict: dict[str, Any] = {}
        for adapter_name, adapter_config in config.adapters.items():
            adapters_dict[adapter_name] = {
                "enabled": adapter_config.enabled,
                "settings": adapter_config.settings,
                "environment_variables": [
                    {
                        "name": env_var.name,
                        "value": env_var.value,
                        "required": env_var.required,
                        "description": env_var.description,
                        "secret": env_var.secret,
                        "default": env_var.default,
                        "validator_pattern": env_var.validator_pattern,
                    }
                    for env_var in adapter_config.environment_variables
                ],
                "dependencies": list(adapter_config.dependencies),
                "profile_overrides": {
                    profile.value: overrides
                    for profile, overrides in adapter_config.profile_overrides.items()
                },
                "health_check_config": adapter_config.health_check_config,
                "metadata": adapter_config.metadata,
            }

        result["adapters"] = adapters_dict
        return result

    def _deserialize_configuration(
        self, config_dict: dict[str, Any]
    ) -> ConfigurationSchema:
        """Convert dictionary to configuration object."""
        # Convert string dates back to datetime objects
        if "created_at" in config_dict:
            config_dict["created_at"] = datetime.fromisoformat(
                config_dict["created_at"]
            )
        if "updated_at" in config_dict:
            config_dict["updated_at"] = datetime.fromisoformat(
                config_dict["updated_at"]
            )

        # Convert profile string to enum
        if "profile" in config_dict:
            config_dict["profile"] = ConfigurationProfile(config_dict["profile"])

        # Convert global environment variables
        global_env = [
            EnvironmentVariable(**env_data)
            for env_data in config_dict.get("global_environment", [])
        ]
        config_dict["global_environment"] = global_env

        # Convert adapter configurations
        adapters = {}
        for adapter_name, adapter_data in config_dict.get("adapters", {}).items():
            # Convert environment variables
            env_vars = [
                EnvironmentVariable(**env_data)
                for env_data in adapter_data.get("environment_variables", [])
            ]
            adapter_data["environment_variables"] = env_vars

            # Convert profile overrides
            profile_overrides = {}
            for profile_str, overrides in adapter_data.get(
                "profile_overrides", {}
            ).items():
                profile_overrides[ConfigurationProfile(profile_str)] = overrides
            adapter_data["profile_overrides"] = profile_overrides

            # Convert dependencies to set
            adapter_data["dependencies"] = set(adapter_data.get("dependencies", []))

            adapters[adapter_name] = AdapterConfiguration(
                name=adapter_name, **adapter_data
            )

        config_dict["adapters"] = adapters

        return ConfigurationSchema(**config_dict)

    async def generate_environment_file(
        self, config: ConfigurationSchema, output_path: Path | None = None
    ) -> Path:
        """Generate .env file from configuration."""
        if not output_path:
            output_path = self.base_path / f".env.{config.profile.value}"

        # Add global environment variables
        env_vars = [
            self._format_env_var(env_var) for env_var in config.global_environment
        ]

        # Add adapter environment variables
        for adapter_name, adapter_config in config.adapters.items():
            if not adapter_config.enabled:
                continue

            env_vars.append(f"\n# {adapter_name.upper()} ADAPTER")
            for env_var in adapter_config.environment_variables:
                env_vars.append(self._format_env_var(env_var))

        with output_path.open("w") as f:
            f.write("\n".join(env_vars))

        return output_path

    def _format_env_var(self, env_var: EnvironmentVariable) -> str:
        """Format environment variable for .env file."""
        lines = []

        if env_var.description:
            lines.append(f"# {env_var.description}")

        if env_var.required:
            lines.append("# REQUIRED")

        value = env_var.value or env_var.default or ""
        if env_var.secret and value:
            value = "***REDACTED***"

        lines.append(f"{env_var.name}={value}")

        return "\n".join(lines)

    async def backup_configuration(
        self, config: ConfigurationSchema, name: str, description: str = ""
    ) -> ConfigurationBackup:
        """Create a backup of the configuration."""
        backup_id = str(uuid4())
        backup_file = self.backup_dir / f"{backup_id}_{name}.yaml"

        # Save configuration
        config_dict = self._serialize_configuration(config)
        with backup_file.open("w") as f:
            yaml.dump(config_dict, f, default_flow_style=False)

        # Calculate checksum
        import hashlib

        with backup_file.open("rb") as fb:
            checksum = hashlib.sha256(fb.read()).hexdigest()

        backup = ConfigurationBackup(
            id=backup_id,
            name=name,
            description=description,
            created_at=datetime.now(),
            profile=config.profile,
            file_path=backup_file,
            checksum=checksum,
        )

        # Save backup metadata
        metadata_file = self.backup_dir / f"{backup_id}_metadata.json"
        with metadata_file.open("w") as f:
            json.dump(
                {
                    "id": backup.id,
                    "name": backup.name,
                    "description": backup.description,
                    "created_at": backup.created_at.isoformat(),
                    "profile": backup.profile.value,
                    "file_path": str(backup.file_path),
                    "checksum": backup.checksum,
                },
                f,
                indent=2,
            )

        return backup

    async def list_backups(self) -> list[ConfigurationBackup]:
        """List all configuration backups."""
        backups = []

        for metadata_file in self.backup_dir.glob("*_metadata.json"):
            try:
                with metadata_file.open() as f:
                    data = json.load(f)

                backup = ConfigurationBackup(
                    id=data["id"],
                    name=data["name"],
                    description=data["description"],
                    created_at=datetime.fromisoformat(data["created_at"]),
                    profile=ConfigurationProfile(data["profile"]),
                    file_path=Path(data["file_path"]),
                    checksum=data["checksum"],
                )

                # Verify file still exists
                if backup.file_path.exists():
                    backups.append(backup)
            except Exception:
                # Skip corrupted metadata files
                continue

        return sorted(backups, key=lambda b: b.created_at, reverse=True)

    async def restore_backup(self, backup_id: str) -> ConfigurationSchema:
        """Restore configuration from backup."""
        backups = await self.list_backups()
        backup = next((b for b in backups if b.id == backup_id), None)

        if not backup:
            raise ValueError(f"Backup '{backup_id}' not found")

        return await self.load_configuration(backup.file_path)

    async def _ensure_default_templates(self) -> None:
        """Ensure default configuration templates exist."""
        templates = {
            "minimal.yaml": self._create_minimal_template(),
            "development.yaml": self._create_development_template(),
            "production.yaml": self._create_production_template(),
        }

        for template_name, template_config in templates.items():
            template_file = self.templates_dir / template_name
            if not template_file.exists():
                config_dict = self._serialize_configuration(template_config)
                with template_file.open("w") as f:
                    yaml.dump(config_dict, f, default_flow_style=False)

    def _create_minimal_template(self) -> ConfigurationSchema:
        """Create minimal configuration template."""
        return ConfigurationSchema(
            profile=ConfigurationProfile.DEVELOPMENT,
            global_settings={"debug": True, "log_level": "INFO"},
        )

    def _create_development_template(self) -> ConfigurationSchema:
        """Create development configuration template."""
        config = ConfigurationSchema(
            profile=ConfigurationProfile.DEVELOPMENT,
            global_settings={"debug": True, "log_level": "DEBUG", "hot_reload": True},
        )

        # Add common development adapters
        config.adapters["app"] = AdapterConfiguration(
            name="app", enabled=True, settings={"debug": True}
        )

        return config

    def _create_production_template(self) -> ConfigurationSchema:
        """Create production configuration template."""
        config = ConfigurationSchema(
            profile=ConfigurationProfile.PRODUCTION,
            global_settings={
                "debug": False,
                "log_level": "WARNING",
                "hot_reload": False,
            },
        )

        return config
