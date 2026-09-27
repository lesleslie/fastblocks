"""D1 coverage tests for fastblocks/mcp/configuration.py.

Targets the ConfigurationManager and surrounding dataclasses/enums:
- ``ConfigurationProfile`` / ``ConfigurationStatus`` enum values
- ``EnvironmentVariable`` / ``AdapterConfiguration`` / ``ConfigurationSchema``
  dataclass + pydantic shapes
- ``ConfigurationValidationResult`` / ``ConfigurationBackup`` construction
- ``ConfigurationManager`` constructor, schema builders, settings
  categorisation, validation paths, env-var checks
"""
# pyright: reportAttributeAccessIssue=false, reportFunctionMemberAccess=false
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

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


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestEnums:
    def test_configuration_profile(self) -> None:
        assert ConfigurationProfile.DEVELOPMENT == "development"
        assert ConfigurationProfile.STAGING == "staging"
        assert ConfigurationProfile.PRODUCTION == "production"

    def test_configuration_status(self) -> None:
        assert ConfigurationStatus.VALID == "valid"
        assert ConfigurationStatus.WARNING == "warning"
        assert ConfigurationStatus.ERROR == "error"
        assert ConfigurationStatus.UNKNOWN == "unknown"


# ---------------------------------------------------------------------------
# Dataclasses + pydantic
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDataclasses:
    def test_environment_variable_defaults(self) -> None:
        e = EnvironmentVariable(name="FOO")
        assert e.name == "FOO"
        assert e.required is True
        assert e.value is None
        assert e.secret is False

    def test_adapter_configuration_defaults(self) -> None:
        a = AdapterConfiguration(name="adapter-A")
        assert a.enabled is True
        assert a.settings == {}
        assert a.environment_variables == []
        assert a.dependencies == set()

    def test_configuration_schema_defaults(self) -> None:
        s = ConfigurationSchema()
        assert s.version == "1.0"
        assert s.profile == ConfigurationProfile.DEVELOPMENT
        assert s.adapters == {}

    def test_configuration_schema_adapters_dict_coercion(self) -> None:
        # The validator coerces dict-of-dicts into AdapterConfiguration.
        # The ``name`` field is keyed by the outer dict; the inner dict
        # carries additional attributes — so we omit ``name`` from the
        # inner payload.
        s = ConfigurationSchema(
            adapters={
                "a": {"enabled": False, "settings": {"k": "v"}},
            }
        )
        assert "a" in s.adapters
        assert isinstance(s.adapters["a"], AdapterConfiguration)
        assert s.adapters["a"].enabled is False

    def test_validation_result_defaults(self) -> None:
        v = ConfigurationValidationResult(status=ConfigurationStatus.VALID)
        assert v.errors == []
        assert v.warnings == []
        assert v.info == {}
        assert v.adapter_results == {}

    def test_configuration_backup_constructible(self) -> None:
        b = ConfigurationBackup(
            id="b1",
            name="backup-1",
            description="desc",
            created_at=datetime.now(UTC),
            profile=ConfigurationProfile.DEVELOPMENT,
            file_path=Path("/tmp/x.json"),
            checksum="abc",
        )
        assert b.id == "b1"
        assert b.profile == ConfigurationProfile.DEVELOPMENT


# ---------------------------------------------------------------------------
# ConfigurationManager (without I/O)
# ---------------------------------------------------------------------------


@pytest.fixture
def manager(tmp_path: Path) -> ConfigurationManager:
    # Use a stub registry to avoid Oneiric resolver churn.
    class _StubRegistry:
        async def initialize(self) -> None: ...

        async def list_available_adapters(self) -> dict[str, Any]:
            return {}

        async def get_adapter_info(self, name: str) -> Any:
            return None

        async def get_adapter(self, name: str) -> Any:
            return None

    return ConfigurationManager(_StubRegistry(), base_path=tmp_path)


@pytest.mark.unit
class TestConfigurationManagerInit:
    def test_constructor_creates_directories(
        self, manager: ConfigurationManager
    ) -> None:
        assert manager.config_dir.exists()
        assert manager.backup_dir.exists()
        assert manager.templates_dir.exists()

    def test_default_base_path(self, tmp_path: Path) -> None:
        class _StubRegistry:
            pass

        mgr = ConfigurationManager(_StubRegistry(), base_path=None)
        # Default base_path is .fastblocks under cwd.
        assert mgr.base_path.name == ".fastblocks"


@pytest.mark.unit
class TestSchemaBuilders:
    def test_build_base_schema(self, manager: ConfigurationManager) -> None:
        # AdapterInfo is an object with description/category attributes;
        # provide a minimal stub that exposes them.
        from types import SimpleNamespace

        info = SimpleNamespace(
            description="An adapter",
            category="templates",
        )
        schema = manager._build_base_schema("adapter-A", info)
        assert schema["name"] == "adapter-A"
        assert schema["description"] == "An adapter"
        assert schema["category"] == "templates"

    def test_categorize_settings_required_vs_optional(
        self, manager: ConfigurationManager
    ) -> None:
        result = manager._categorize_settings(
            {"name": "x", "count": 0, "missing": None}
        )
        # "missing" (None) is required; everything else is optional.
        required_names = {r["name"] for r in result["required"]}
        optional_names = {r["name"] for r in result["optional"]}
        assert "missing" in required_names
        assert "name" in optional_names
        assert "count" in optional_names

    def test_categorize_settings_skips_private_keys(
        self, manager: ConfigurationManager
    ) -> None:
        result = manager._categorize_settings(
            {"public": "p", "_private": "x"}
        )
        all_names = (
            {r["name"] for r in result["required"]}
            | {r["name"] for r in result["optional"]}
        )
        assert "public" in all_names
        assert "_private" not in all_names

    def test_introspect_adapter_settings_no_settings_attr(
        self, manager: ConfigurationManager
    ) -> None:
        adapter = object()  # No settings attribute
        schema: dict[str, Any] = {
            "name": "x",
            "required_settings": [],
            "optional_settings": [],
        }
        # Should not raise.
        manager._introspect_adapter_settings(adapter, schema)

    def test_introspect_adapter_settings_with_dict_attr(
        self, manager: ConfigurationManager
    ) -> None:
        # ``_introspect_adapter_settings`` expects ``settings`` to be a
        # Pydantic-style model exposing ``__dict__``. A bare dict does
        # not — verify the function handles that gracefully.
        class _Adapter:
            settings = {"foo": "bar"}

        schema: dict[str, Any] = {
            "name": "x",
            "required_settings": [],
            "optional_settings": [],
        }
        manager._introspect_adapter_settings(_Adapter(), schema)
        # No exception; schema unchanged.
        assert schema["optional_settings"] == []

    @pytest.mark.asyncio
    async def test_get_adapter_configuration_schema_unknown(
        self, manager: ConfigurationManager
    ) -> None:
        # Stub registry returns None for unknown adapter.
        with pytest.raises(ValueError, match="not found"):
            await manager.get_adapter_configuration_schema("never-was")


@pytest.mark.unit
class TestEnvironmentVariableHelpers:
    def test_check_missing_required_vars(self, manager: ConfigurationManager) -> None:
        # ``_check_missing_required_vars`` takes a ConfigurationSchema +
        # result, walks each adapter's environment_variables.
        schema = ConfigurationSchema(
            adapters={
                "a": AdapterConfiguration(
                    name="a",
                    enabled=True,
                    environment_variables=[
                        EnvironmentVariable(name="A", required=True),
                        EnvironmentVariable(name="B", required=True),
                    ],
                )
            }
        )
        result = ConfigurationValidationResult(
            status=ConfigurationStatus.UNKNOWN
        )
        # Provide value for A via env but leave B unset.
        import os

        old = os.environ.copy()
        os.environ["A"] = "x"
        try:
            manager._check_missing_required_vars(schema, result)
        finally:
            os.environ.clear()
            os.environ.update(old)
        # B should be flagged as missing.
        assert any("B" in w for w in result.warnings)

    def test_check_duplicate_env_vars(self, manager: ConfigurationManager) -> None:
        # Build two adapters that both declare the same env var.
        schema = ConfigurationSchema(
            adapters={
                "a": AdapterConfiguration(
                    name="a",
                    environment_variables=[EnvironmentVariable(name="DUP")],
                ),
                "b": AdapterConfiguration(
                    name="b",
                    environment_variables=[EnvironmentVariable(name="DUP")],
                ),
            }
        )
        result = ConfigurationValidationResult(
            status=ConfigurationStatus.UNKNOWN
        )
        manager._check_duplicate_env_vars(schema, result, set())
        # The second occurrence is a duplicate — flagged in warnings.
        assert any("DUP" in w for w in result.warnings)

    def test_is_env_var_missing_no_value(self, manager: ConfigurationManager) -> None:
        e = EnvironmentVariable(name="UNIQUE_TEST_VAR_NOT_SET", required=True)
        # Without setting it in the env, it should be reported missing.
        import os

        os.environ.pop("UNIQUE_TEST_VAR_NOT_SET", None)
        assert manager._is_env_var_missing(e) is True

    def test_is_env_var_missing_with_value(self, manager: ConfigurationManager) -> None:
        import os

        os.environ["PRESENT_VAR"] = "x"
        try:
            e = EnvironmentVariable(name="PRESENT_VAR", required=True)
            assert manager._is_env_var_missing(e) is False
        finally:
            os.environ.pop("PRESENT_VAR", None)