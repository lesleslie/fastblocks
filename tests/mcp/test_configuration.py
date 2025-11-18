"""Tests for MCP configuration management."""

from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastblocks.mcp.configuration import (
    AdapterConfiguration,
    ConfigurationBackup,
    ConfigurationManager,
    ConfigurationProfile,
    ConfigurationSchema,
    ConfigurationStatus,
    ConfigurationValidationResult,
    EnvironmentVariable,
)
from fastblocks.mcp.discovery import AdapterInfo
from fastblocks.mcp.registry import AdapterRegistry


@pytest.fixture
def mock_registry():
    """Create a mock adapter registry."""
    registry = AsyncMock(spec=AdapterRegistry)
    registry.initialize = AsyncMock()
    registry.list_available_adapters = AsyncMock(return_value={})
    registry.get_adapter_info = AsyncMock(return_value=None)
    registry.get_adapter = AsyncMock(return_value=None)
    return registry


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create a temporary configuration directory."""
    return tmp_path / ".fastblocks"


@pytest.fixture
def config_manager(mock_registry, temp_config_dir):
    """Create a configuration manager with mocked registry."""
    return ConfigurationManager(mock_registry, temp_config_dir)


class TestConfigurationProfile:
    """Test ConfigurationProfile enum."""

    def test_development_profile(self):
        """Test DEVELOPMENT profile value."""
        assert ConfigurationProfile.DEVELOPMENT.value == "development"

    def test_staging_profile(self):
        """Test STAGING profile value."""
        assert ConfigurationProfile.STAGING.value == "staging"

    def test_production_profile(self):
        """Test PRODUCTION profile value."""
        assert ConfigurationProfile.PRODUCTION.value == "production"

    def test_profile_is_enum(self):
        """Test ConfigurationProfile is an Enum."""
        assert isinstance(ConfigurationProfile.DEVELOPMENT, ConfigurationProfile)


class TestConfigurationStatus:
    """Test ConfigurationStatus enum."""

    def test_valid_status(self):
        """Test VALID status value."""
        assert ConfigurationStatus.VALID.value == "valid"

    def test_warning_status(self):
        """Test WARNING status value."""
        assert ConfigurationStatus.WARNING.value == "warning"

    def test_error_status(self):
        """Test ERROR status value."""
        assert ConfigurationStatus.ERROR.value == "error"

    def test_unknown_status(self):
        """Test UNKNOWN status value."""
        assert ConfigurationStatus.UNKNOWN.value == "unknown"


class TestEnvironmentVariable:
    """Test EnvironmentVariable dataclass."""

    def test_environment_variable_defaults(self):
        """Test EnvironmentVariable with defaults."""
        env_var = EnvironmentVariable(name="TEST_VAR")

        assert env_var.name == "TEST_VAR"
        assert env_var.value is None
        assert env_var.required is True
        assert env_var.description == ""
        assert env_var.secret is False
        assert env_var.default is None
        assert env_var.validator_pattern is None

    def test_environment_variable_with_values(self):
        """Test EnvironmentVariable with custom values."""
        env_var = EnvironmentVariable(
            name="API_KEY",
            value="secret123",
            required=True,
            description="API authentication key",
            secret=True,
            default="default_key",
            validator_pattern=r"^[A-Za-z0-9]+$",
        )

        assert env_var.name == "API_KEY"
        assert env_var.value == "secret123"
        assert env_var.required is True
        assert env_var.description == "API authentication key"
        assert env_var.secret is True
        assert env_var.default == "default_key"
        assert env_var.validator_pattern == r"^[A-Za-z0-9]+$"


class TestAdapterConfiguration:
    """Test AdapterConfiguration dataclass."""

    def test_adapter_configuration_defaults(self):
        """Test AdapterConfiguration with defaults."""
        config = AdapterConfiguration(name="test_adapter")

        assert config.name == "test_adapter"
        assert config.enabled is True
        assert config.settings == {}
        assert config.environment_variables == []
        assert config.dependencies == set()
        assert config.profile_overrides == {}
        assert config.health_check_config == {}
        assert config.metadata == {}

    def test_adapter_configuration_with_values(self):
        """Test AdapterConfiguration with custom values."""
        env_var = EnvironmentVariable(name="TEST_VAR")
        config = AdapterConfiguration(
            name="auth_adapter",
            enabled=True,
            settings={"timeout": 30},
            environment_variables=[env_var],
            dependencies={"database", "cache"},
            profile_overrides={ConfigurationProfile.PRODUCTION: {"timeout": 60}},
            health_check_config={"interval": 30},
            metadata={"version": "1.0"},
        )

        assert config.name == "auth_adapter"
        assert config.enabled is True
        assert config.settings == {"timeout": 30}
        assert len(config.environment_variables) == 1
        assert config.dependencies == {"database", "cache"}
        assert ConfigurationProfile.PRODUCTION in config.profile_overrides
        assert config.health_check_config == {"interval": 30}
        assert config.metadata == {"version": "1.0"}


class TestConfigurationSchema:
    """Test ConfigurationSchema Pydantic model."""

    def test_configuration_schema_defaults(self):
        """Test ConfigurationSchema with defaults."""
        schema = ConfigurationSchema()

        assert schema.version == "1.0"
        assert schema.profile == ConfigurationProfile.DEVELOPMENT
        assert isinstance(schema.created_at, datetime)
        assert isinstance(schema.updated_at, datetime)
        assert schema.adapters == {}
        assert schema.global_settings == {}
        assert schema.global_environment == []

    def test_configuration_schema_with_values(self):
        """Test ConfigurationSchema with custom values."""
        adapter_config = AdapterConfiguration(name="test")
        schema = ConfigurationSchema(
            version="2.0",
            profile=ConfigurationProfile.PRODUCTION,
            adapters={"test": adapter_config},
            global_settings={"debug": False},
        )

        assert schema.version == "2.0"
        assert schema.profile == ConfigurationProfile.PRODUCTION
        assert "test" in schema.adapters
        assert schema.global_settings == {"debug": False}

    def test_configuration_schema_adapter_validation(self):
        """Test ConfigurationSchema adapters validator."""
        # Test with dict input that should be converted
        schema = ConfigurationSchema(
            adapters={"test": {"enabled": True, "settings": {"foo": "bar"}}}
        )

        assert "test" in schema.adapters
        assert isinstance(schema.adapters["test"], AdapterConfiguration)
        assert schema.adapters["test"].enabled is True


class TestConfigurationValidationResult:
    """Test ConfigurationValidationResult dataclass."""

    def test_validation_result_defaults(self):
        """Test ConfigurationValidationResult with defaults."""
        result = ConfigurationValidationResult(status=ConfigurationStatus.VALID)

        assert result.status == ConfigurationStatus.VALID
        assert result.errors == []
        assert result.warnings == []
        assert result.info == {}
        assert result.adapter_results == {}

    def test_validation_result_with_errors(self):
        """Test ConfigurationValidationResult with errors."""
        result = ConfigurationValidationResult(
            status=ConfigurationStatus.ERROR,
            errors=["Missing required setting", "Invalid value"],
            warnings=["Deprecated option"],
            info={"checked_adapters": 5},
            adapter_results={"auth": {"status": "error"}},
        )

        assert result.status == ConfigurationStatus.ERROR
        assert len(result.errors) == 2
        assert len(result.warnings) == 1
        assert result.info["checked_adapters"] == 5
        assert "auth" in result.adapter_results


class TestConfigurationBackup:
    """Test ConfigurationBackup dataclass."""

    def test_configuration_backup(self):
        """Test ConfigurationBackup creation."""
        now = datetime.now()
        backup = ConfigurationBackup(
            id="backup-123",
            name="Pre-deployment backup",
            description="Backup before production deployment",
            created_at=now,
            profile=ConfigurationProfile.PRODUCTION,
            file_path=Path("/backups/config-123.json"),
            checksum="abc123def456",
        )

        assert backup.id == "backup-123"
        assert backup.name == "Pre-deployment backup"
        assert backup.created_at == now
        assert backup.profile == ConfigurationProfile.PRODUCTION
        assert backup.file_path == Path("/backups/config-123.json")
        assert backup.checksum == "abc123def456"


class TestConfigurationManager:
    """Test ConfigurationManager class."""

    def test_initialization(self, config_manager, temp_config_dir):
        """Test ConfigurationManager initialization."""
        assert config_manager.base_path == temp_config_dir
        assert config_manager.config_dir == temp_config_dir / "config"
        assert config_manager.backup_dir == temp_config_dir / "backups"
        assert config_manager.templates_dir == temp_config_dir / "templates"

    def test_directories_created(self, config_manager):
        """Test that required directories are created."""
        assert config_manager.config_dir.exists()
        assert config_manager.backup_dir.exists()
        assert config_manager.templates_dir.exists()

    @pytest.mark.asyncio
    async def test_initialize(self, config_manager, mock_registry):
        """Test ConfigurationManager initialize method."""
        with patch.object(config_manager, "_ensure_default_templates", AsyncMock()):
            await config_manager.initialize()

            mock_registry.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_available_adapters(self, config_manager, mock_registry):
        """Test getting available adapters."""
        expected_adapters = {
            "auth": MagicMock(spec=AdapterInfo),
            "database": MagicMock(spec=AdapterInfo),
        }
        mock_registry.list_available_adapters.return_value = expected_adapters

        result = await config_manager.get_available_adapters()

        assert result == expected_adapters
        mock_registry.list_available_adapters.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_adapter_configuration_schema_not_found(
        self, config_manager, mock_registry
    ):
        """Test getting schema for non-existent adapter."""
        mock_registry.get_adapter_info.return_value = None

        with pytest.raises(ValueError, match="Adapter 'nonexistent' not found"):
            await config_manager.get_adapter_configuration_schema("nonexistent")

    @pytest.mark.asyncio
    async def test_get_adapter_configuration_schema_success(
        self, config_manager, mock_registry
    ):
        """Test getting schema for existing adapter."""
        adapter_info = MagicMock(spec=AdapterInfo)
        adapter_info.description = "Test adapter"
        adapter_info.category = "auth"
        mock_registry.get_adapter_info.return_value = adapter_info

        schema = await config_manager.get_adapter_configuration_schema("test_adapter")

        assert schema["name"] == "test_adapter"
        assert schema["description"] == "Test adapter"
        assert schema["category"] == "auth"
        assert "required_settings" in schema
        assert "optional_settings" in schema

    @pytest.mark.asyncio
    async def test_create_configuration_default(self, config_manager):
        """Test creating a default configuration."""
        with patch.object(config_manager, "_ensure_default_templates", AsyncMock()):
            config = await config_manager.create_configuration()

            assert config.profile == ConfigurationProfile.DEVELOPMENT
            assert config.version == "1.0"
            assert config.adapters == {}

    @pytest.mark.asyncio
    async def test_create_configuration_with_adapters(
        self, config_manager, mock_registry
    ):
        """Test creating configuration with specific adapters."""
        adapter_info = MagicMock(spec=AdapterInfo)
        adapter_info.description = "Auth adapter"
        adapter_info.category = "auth"
        mock_registry.get_adapter_info.return_value = adapter_info

        config = await config_manager.create_configuration(
            profile=ConfigurationProfile.PRODUCTION, adapters=["auth"]
        )

        assert config.profile == ConfigurationProfile.PRODUCTION
        assert "auth" in config.adapters
        assert isinstance(config.adapters["auth"], AdapterConfiguration)

    def test_build_base_schema(self, config_manager):
        """Test _build_base_schema method."""
        adapter_info = MagicMock(spec=AdapterInfo)
        adapter_info.description = "Test description"
        adapter_info.category = "test_category"

        schema = config_manager._build_base_schema("test_adapter", adapter_info)

        assert schema["name"] == "test_adapter"
        assert schema["description"] == "Test description"
        assert schema["category"] == "test_category"
        assert schema["required_settings"] == []
        assert schema["optional_settings"] == []
        assert schema["environment_variables"] == []
        assert schema["dependencies"] == []

    def test_categorize_settings(self, config_manager):
        """Test _categorize_settings method."""
        settings_dict = {
            "required_setting": None,
            "optional_setting": "default_value",
            "_private_setting": "ignored",
            "another_optional": 42,
        }

        categorized = config_manager._categorize_settings(settings_dict)

        assert len(categorized["required"]) == 1
        assert len(categorized["optional"]) == 2
        assert categorized["required"][0]["name"] == "required_setting"
        assert any(s["name"] == "optional_setting" for s in categorized["optional"])
        assert not any(
            s["name"].startswith("_")
            for s in categorized["required"] + categorized["optional"]
        )
