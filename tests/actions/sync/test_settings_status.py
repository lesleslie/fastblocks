"""Additional tests for fastblocks/actions/sync/settings.py status helpers."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from anyio import Path as AsyncPath
from fastblocks.actions.sync.settings import (
    get_settings_sync_status,
)


@pytest.mark.unit
class TestGetSettingsSyncStatusWithoutStorage:
    async def test_status_without_storage(self) -> None:
        # Stub _get_storage_adapter to return None — function reports
        # "Storage adapter not available" gracefully.
        with patch(
            "fastblocks.actions.sync.settings._get_storage_adapter",
            AsyncMock(return_value=None),
        ):
            status = await get_settings_sync_status()
        assert isinstance(status, dict)
        assert status["error"] == "Storage adapter not available"
        assert status["total_settings"] == 0

    async def test_status_with_empty_storage(self, tmp_path) -> None:
        # Stub storage with an empty list — function reports a clean sync.
        storage = MagicMock()
        storage.list_objects = AsyncMock(return_value=[])
        with patch(
            "fastblocks.actions.sync.settings._get_storage_adapter",
            AsyncMock(return_value=storage),
        ):
            status = await get_settings_sync_status(
                settings_path=AsyncPath(str(tmp_path))
            )
        assert isinstance(status, dict)
        assert status["total_settings"] == 0
