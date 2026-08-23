"""Additional tests for fastblocks/actions/sync/cache.py.

Targets 170 missing statements before this file. Tests cover
``get_cache_sync_summary``, ``CacheSyncResult`` dataclass, and the
public ``sync_cache`` entry point with no cache configured.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastblocks.actions.sync.cache import (
    CacheSyncResult,
    get_cache_sync_summary,
    sync_cache,
)


@pytest.mark.unit
class TestCacheSyncResult:
    def test_default_construction(self) -> None:
        result = CacheSyncResult()
        assert result.invalidated_keys == []
        assert result.warmed_keys == []
        assert result.cleared_namespaces == []
        # Inherited from SyncResult.
        assert result.errors == []
        assert result.synced_items == []

    def test_construction_with_data(self) -> None:
        result = CacheSyncResult(
            invalidated_keys=["k1", "k2"],
            warmed_keys=["w1"],
            cleared_namespaces=["templates"],
        )
        assert result.invalidated_keys == ["k1", "k2"]
        assert result.warmed_keys == ["w1"]
        assert result.cleared_namespaces == ["templates"]


@pytest.mark.unit
class TestGetCacheSyncSummary:
    def test_summary_with_empty_result(self) -> None:
        result = CacheSyncResult()
        summary = get_cache_sync_summary(result)
        assert summary["invalidated_count"] == 0
        assert summary["warmed_count"] == 0
        assert summary["cleared_namespaces"] == 0
        assert summary["errors"] == 0
        assert summary["success"] is True

    def test_summary_with_keys(self) -> None:
        result = CacheSyncResult(
            invalidated_keys=["a", "b", "c"],
            warmed_keys=["d"],
        )
        summary = get_cache_sync_summary(result)
        assert summary["invalidated_count"] == 3
        assert summary["warmed_count"] == 1
        assert summary["success"] is True

    def test_summary_with_errors(self) -> None:
        result = CacheSyncResult()
        result.errors.append("disk full")
        summary = get_cache_sync_summary(result)
        assert summary["errors"] == 1
        assert summary["success"] is False


@pytest.mark.unit
class TestSyncCacheWithoutCache:
    async def test_sync_cache_without_cache_adapter(self) -> None:
        # Stub resolve_instance to return None — no cache configured.
        with patch(
            "fastblocks.adapters.oneiric_helper.resolve_instance",
            AsyncMock(return_value=None),
        ):
            result = await sync_cache()
        assert isinstance(result, CacheSyncResult)
        # Primary error recorded because cache is not available.
        assert result.primary_error is not None or len(result.errors) > 0