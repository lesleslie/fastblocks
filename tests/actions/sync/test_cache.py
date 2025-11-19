"""Tests for cache synchronization functionality."""

from unittest.mock import AsyncMock, patch

import pytest
from fastblocks.actions.sync.cache import CacheSyncResult, sync_cache
from fastblocks.actions.sync.strategies import SyncStrategy


@pytest.fixture
def mock_cache():
    """Create a mock cache adapter."""
    cache = AsyncMock()
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock()
    cache.delete = AsyncMock()
    cache.delete_pattern = AsyncMock(return_value=["key1", "key2"])
    cache.clear = AsyncMock()
    cache.keys = AsyncMock(return_value=[])
    return cache


@pytest.fixture
def mock_strategy():
    """Create a mock sync strategy."""
    strategy = SyncStrategy()
    strategy.dry_run = False
    strategy.parallel = True
    strategy.batch_size = 10
    return strategy


@pytest.fixture
def mock_depends_get(mock_cache):
    """Create a mock for depends.get that returns the cache adapter."""

    async def _get(name):
        if name == "cache":
            return mock_cache
        return None

    return AsyncMock(side_effect=_get)


class TestCacheSyncResult:
    """Test CacheSyncResult functionality."""

    def test_result_initialization_defaults(self):
        """Test CacheSyncResult initializes with default values."""
        result = CacheSyncResult()

        assert result.invalidated_keys == []
        assert result.warmed_keys == []
        assert result.cleared_namespaces == []
        assert result.errors == []

    def test_result_initialization_with_values(self):
        """Test CacheSyncResult initializes with provided values."""
        invalidated = ["key1", "key2"]
        warmed = ["key3", "key4"]
        cleared = ["namespace1"]

        result = CacheSyncResult(
            invalidated_keys=invalidated, warmed_keys=warmed, cleared_namespaces=cleared
        )

        assert result.invalidated_keys == invalidated
        assert result.warmed_keys == warmed
        assert result.cleared_namespaces == cleared


class TestSyncCache:
    """Test sync_cache functionality."""

    @pytest.mark.asyncio
    async def test_sync_cache_no_cache_adapter(self, mock_strategy):
        """Test sync_cache handles missing cache adapter."""

        async def _get_none(name):
            return None

        with patch("acb.depends.depends.get", AsyncMock(side_effect=_get_none)):
            result = await sync_cache(strategy=mock_strategy)

            assert len(result.errors) > 0
            assert any("not available" in str(e) for e in result.errors)

    @pytest.mark.asyncio
    async def test_sync_cache_refresh_operation(self, mock_depends_get, mock_strategy):
        """Test sync_cache with refresh operation."""
        with patch("acb.depends.depends.get", mock_depends_get):
            result = await sync_cache(
                operation="refresh", namespaces=["templates"], strategy=mock_strategy
            )

            assert isinstance(result, CacheSyncResult)

    @pytest.mark.asyncio
    async def test_sync_cache_invalidate_operation(
        self, mock_depends_get, mock_strategy
    ):
        """Test sync_cache with invalidate operation."""
        keys_to_invalidate = ["key1", "key2"]

        with patch("acb.depends.depends.get", mock_depends_get):
            result = await sync_cache(
                operation="invalidate", keys=keys_to_invalidate, strategy=mock_strategy
            )

            assert isinstance(result, CacheSyncResult)
            assert len(result.invalidated_keys) > 0

    @pytest.mark.asyncio
    async def test_sync_cache_warm_operation(self, mock_depends_get, mock_strategy):
        """Test sync_cache with warm operation."""
        with patch("acb.depends.depends.get", mock_depends_get):
            result = await sync_cache(
                operation="warm", namespaces=["templates"], strategy=mock_strategy
            )

            assert isinstance(result, CacheSyncResult)

    @pytest.mark.asyncio
    async def test_sync_cache_clear_operation(self, mock_depends_get, mock_strategy):
        """Test sync_cache with clear operation."""
        with patch("acb.depends.depends.get", mock_depends_get):
            result = await sync_cache(
                operation="clear", namespaces=["templates"], strategy=mock_strategy
            )

            assert isinstance(result, CacheSyncResult)
            assert len(result.cleared_namespaces) > 0

    @pytest.mark.asyncio
    async def test_sync_cache_unknown_operation(self, mock_depends_get, mock_strategy):
        """Test sync_cache with unknown operation."""
        with patch("acb.depends.depends.get", mock_depends_get):
            result = await sync_cache(operation="unknown", strategy=mock_strategy)

            assert len(result.errors) > 0
            assert any("Unknown cache operation" in str(e) for e in result.errors)

    @pytest.mark.asyncio
    async def test_sync_cache_default_namespaces(self, mock_depends_get, mock_strategy):
        """Test sync_cache uses default namespaces when none provided."""
        with patch("acb.depends.depends.get", mock_depends_get):
            result = await sync_cache(operation="refresh", strategy=mock_strategy)

            assert isinstance(result, CacheSyncResult)

    @pytest.mark.asyncio
    async def test_sync_cache_default_strategy(self, mock_depends_get):
        """Test sync_cache uses default strategy when none provided."""
        with patch("acb.depends.depends.get", mock_depends_get):
            result = await sync_cache(operation="refresh", namespaces=["templates"])

            assert isinstance(result, CacheSyncResult)

    @pytest.mark.asyncio
    async def test_sync_cache_with_warm_templates_true(
        self, mock_depends_get, mock_strategy
    ):
        """Test sync_cache with warm_templates enabled."""
        with patch("acb.depends.depends.get", mock_depends_get):
            result = await sync_cache(
                operation="refresh", warm_templates=True, strategy=mock_strategy
            )

            assert isinstance(result, CacheSyncResult)

    @pytest.mark.asyncio
    async def test_sync_cache_with_warm_templates_false(
        self, mock_depends_get, mock_strategy
    ):
        """Test sync_cache with warm_templates disabled."""
        with patch("acb.depends.depends.get", mock_depends_get):
            result = await sync_cache(
                operation="refresh", warm_templates=False, strategy=mock_strategy
            )

            assert isinstance(result, CacheSyncResult)

    @pytest.mark.asyncio
    async def test_sync_cache_handles_exceptions(self, mock_cache, mock_strategy):
        """Test sync_cache handles exceptions gracefully."""
        mock_cache.delete_pattern.side_effect = Exception("Cache error")

        async def _get(name):
            if name == "cache":
                return mock_cache
            return None

        with patch("acb.depends.depends.get", AsyncMock(side_effect=_get)):
            result = await sync_cache(operation="refresh", strategy=mock_strategy)

            assert isinstance(result, CacheSyncResult)
            assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_sync_cache_custom_namespaces(self, mock_depends_get, mock_strategy):
        """Test sync_cache with custom namespaces."""
        custom_namespaces = ["custom1", "custom2"]

        with patch("acb.depends.depends.get", mock_depends_get):
            result = await sync_cache(
                operation="refresh",
                namespaces=custom_namespaces,
                strategy=mock_strategy,
            )

            assert isinstance(result, CacheSyncResult)

    @pytest.mark.asyncio
    async def test_sync_cache_with_specific_keys(self, mock_depends_get, mock_strategy):
        """Test sync_cache with specific keys for invalidation."""
        keys = ["app:cache:key1", "app:cache:key2"]

        with patch("acb.depends.depends.get", mock_depends_get):
            result = await sync_cache(
                operation="invalidate", keys=keys, strategy=mock_strategy
            )

            assert isinstance(result, CacheSyncResult)
            assert len(result.invalidated_keys) > 0

    @pytest.mark.asyncio
    async def test_sync_cache_exception_during_get_depends(self, mock_strategy):
        """Test sync_cache handles exception when getting cache adapter."""
        with patch("acb.depends.depends.get", side_effect=Exception("Depends error")):
            result = await sync_cache(strategy=mock_strategy)

            assert len(result.errors) > 0
