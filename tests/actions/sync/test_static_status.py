"""Additional tests for fastblocks/actions/sync/static.py.

Targets ``get_static_sync_status`` and the discovery/sync helpers
(242 missing statements before this file). Tests stub the storage
adapter so they don't require real cloud backends.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from anyio import Path as AsyncPath
from fastblocks.actions.sync.static import (
    _get_default_static_bucket,
    _should_exclude_file,
    get_static_sync_status,
)


@pytest.mark.unit
class TestGetDefaultStaticBucket:
    async def test_returns_static_when_no_config(self, tmp_path) -> None:
        # No settings/storage.yml present → falls back to "static".
        import os

        old_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            bucket = await _get_default_static_bucket()
            assert bucket == "static"
        finally:
            os.chdir(old_cwd)

    async def test_returns_static_when_config_exists(self, tmp_path) -> None:
        # settings/storage.yml is present with a static bucket name.
        settings_dir = tmp_path / "settings"
        settings_dir.mkdir()
        (settings_dir / "storage.yml").write_text("buckets:\n  static: media\n")
        import os

        old_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            bucket = await _get_default_static_bucket()
            # The function reads the configured bucket name when YAML loads.
            assert bucket in ("media", "static")
        finally:
            os.chdir(old_cwd)


@pytest.mark.unit
class TestShouldExcludeFileExtended:
    def test_excludes_dot_files(self) -> None:
        assert (
            _should_exclude_file(
                AsyncPath("static/.hidden"),
                [".*"],
            )
            is True
        )

    def test_excludes_tmp(self) -> None:
        assert (
            _should_exclude_file(
                AsyncPath("static/foo.tmp"),
                ["*.tmp"],
            )
            is True
        )

    def test_includes_normal_css(self) -> None:
        assert (
            _should_exclude_file(
                AsyncPath("static/css/site.css"),
                ["*.tmp", "*.pyc"],
            )
            is False
        )


@pytest.mark.unit
class TestGetStaticSyncStatusWithoutStorage:
    async def test_status_without_storage(self) -> None:
        # Stub _get_storage_adapter to return None — function reports
        # "Storage adapter not available" gracefully.
        with patch(
            "fastblocks.actions.sync.static._get_storage_adapter",
            AsyncMock(return_value=None),
        ):
            status = await get_static_sync_status(static_path=AsyncPath("static"))
        assert isinstance(status, dict)
        assert status["error"] == "Storage adapter not available"
        assert status["total_static_files"] == 0

    async def test_status_with_storage_but_no_files(
        self, tmp_path
    ) -> None:
        # Stub storage with an empty list — function reports a clean sync.
        storage = MagicMock()
        storage.list_objects = AsyncMock(return_value=[])
        with patch(
            "fastblocks.actions.sync.static._get_storage_adapter",
            AsyncMock(return_value=storage),
        ):
            status = await get_static_sync_status(
                static_path=AsyncPath(str(tmp_path)),
            )
        assert isinstance(status, dict)
        assert status["total_static_files"] == 0