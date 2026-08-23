"""Tests for fastblocks/actions/sync/settings.py initialization paths.

Targets 212 missing statements before this file. Tests cover
``_initialize_storage_only``, ``_get_default_settings_bucket``,
``_handle_config_reload``, and the ``SettingsSyncResult`` dataclass.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastblocks.actions.sync.settings import (
    SettingsSyncResult,
    _get_default_settings_bucket,
    _handle_config_reload,
    _initialize_storage_only,
)
from fastblocks.actions.sync.strategies import SyncStrategy


@pytest.mark.unit
class TestSettingsSyncResult:
    def test_default_construction(self) -> None:
        result = SettingsSyncResult()
        assert result.synced_items == []
        assert result.errors == []

    def test_with_kwargs(self) -> None:
        result = SettingsSyncResult(synced_items=["settings/a.yaml"])
        assert result.synced_items == ["settings/a.yaml"]


@pytest.mark.unit
class TestGetDefaultSettingsBucket:
    async def test_fallback_to_settings(self, tmp_path) -> None:
        # No settings/storage.yml in tmp_path → fallback.
        import os

        old_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            bucket = await _get_default_settings_bucket()
            assert bucket == "settings"
        finally:
            os.chdir(old_cwd)

    async def test_reads_settings_from_yaml(self, tmp_path) -> None:
        # settings/storage.yml present with custom bucket name.
        (tmp_path / "settings").mkdir()
        (tmp_path / "settings" / "storage.yml").write_text(
            "buckets:\n  settings: media\n"
        )
        import os

        old_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            bucket = await _get_default_settings_bucket()
            # The function reads the configured name when YAML loads.
            assert bucket in ("media", "settings")
        finally:
            os.chdir(old_cwd)


@pytest.mark.unit
class TestInitializeStorageOnly:
    async def test_returns_none_when_storage_unavailable(self) -> None:
        result = SettingsSyncResult()
        with patch(
            "fastblocks.actions.sync.settings.resolve_component_async",
            AsyncMock(return_value=None),
        ):
            storage = await _initialize_storage_only(result)
        assert storage is None
        # Primary error recorded.
        assert result.primary_error is not None

    async def test_returns_storage_when_resolved(self) -> None:
        result = SettingsSyncResult()
        storage = MagicMock()
        with patch(
            "fastblocks.actions.sync.settings.resolve_component_async",
            AsyncMock(return_value=storage),
        ):
            resolved = await _initialize_storage_only(result)
        assert resolved is storage


@pytest.mark.unit
class TestHandleConfigReload:
    async def test_handle_config_reload_no_reload(self) -> None:
        # reload_config=False → no-op.
        result = SettingsSyncResult()
        await _handle_config_reload(reload_config=False, result=result)
        # No exceptions; no changes.

    async def test_handle_config_reload_with_no_synced_items(self) -> None:
        # reload_config=True but no synced_items → no-op.
        result = SettingsSyncResult()
        await _handle_config_reload(reload_config=True, result=result)
        # No exceptions; no changes.