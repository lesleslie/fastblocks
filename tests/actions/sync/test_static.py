"""Tests for static files synchronization functionality."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from anyio import Path as AsyncPath
from fastblocks.actions.sync.static import (
    CACHEABLE_EXTENSIONS,
    NON_CACHEABLE_EXTENSIONS,
    StaticSyncResult,
    _is_cacheable_file,
    backup_static_files,
    sync_static,
    warm_static_cache,
)
from fastblocks.actions.sync.strategies import SyncDirection, SyncStrategy


@pytest.fixture
def mock_storage():
    """Create a mock storage adapter."""
    storage = AsyncMock()

    # Mock bucket
    mock_bucket = AsyncMock()
    mock_bucket.exists = AsyncMock(return_value=False)
    mock_bucket.read = AsyncMock(return_value=b"file content")
    mock_bucket.write = AsyncMock()
    mock_bucket.stat = AsyncMock(return_value={"mtime": 1234567890})

    storage.static = mock_bucket
    storage._create_bucket = AsyncMock()

    return storage


@pytest.fixture
def mock_cache():
    """Create a mock cache adapter."""
    cache = AsyncMock()
    cache.set = AsyncMock()
    cache.exists = AsyncMock(return_value=False)
    return cache


@pytest.fixture
def mock_strategy():
    """Create a mock sync strategy."""
    strategy = SyncStrategy()
    strategy.direction = SyncDirection.BIDIRECTIONAL
    strategy.dry_run = False
    strategy.backup_on_conflict = True
    return strategy


@pytest.fixture
def mock_depends_get(mock_storage, mock_cache):
    """Create a mock for depends.get that returns adapters."""

    async def _get(name):
        if name == "storage":
            return mock_storage
        elif name == "cache":
            return mock_cache
        return None

    return AsyncMock(side_effect=_get)


class TestStaticSyncResult:
    """Test StaticSyncResult functionality."""

    def test_result_initialization_defaults(self):
        """Test StaticSyncResult initializes with default values."""
        result = StaticSyncResult()

        assert result.assets_processed == []
        assert result.mime_types_detected == {}
        assert result.cache_invalidated == []
        assert result.cache_cleared == []
        assert result.cacheable_assets == []
        assert result.non_cacheable_assets == []

    def test_result_initialization_with_values(self):
        """Test StaticSyncResult initializes with provided values."""
        assets = ["file1.css", "file2.js"]
        mime_types = {"file1.css": "text/css"}
        cache_inv = ["static:file1.css"]

        result = StaticSyncResult(
            assets_processed=assets,
            mime_types_detected=mime_types,
            cache_invalidated=cache_inv,
        )

        assert result.assets_processed == assets
        assert result.mime_types_detected == mime_types
        assert result.cache_invalidated == cache_inv


class TestCacheableFileDetection:
    """Test _is_cacheable_file functionality."""

    def test_is_cacheable_css(self):
        """Test CSS files are cacheable."""
        mock_path = MagicMock(spec=AsyncPath)
        mock_path.suffix = ".css"
        assert _is_cacheable_file(mock_path) is True

    def test_is_cacheable_js(self):
        """Test JavaScript files are cacheable."""
        mock_path = MagicMock(spec=AsyncPath)
        mock_path.suffix = ".js"
        assert _is_cacheable_file(mock_path) is True

    def test_is_cacheable_md(self):
        """Test Markdown files are cacheable."""
        mock_path = MagicMock(spec=AsyncPath)
        mock_path.suffix = ".md"
        assert _is_cacheable_file(mock_path) is True

    def test_is_not_cacheable_png(self):
        """Test PNG images are not cacheable."""
        mock_path = MagicMock(spec=AsyncPath)
        mock_path.suffix = ".png"
        assert _is_cacheable_file(mock_path) is False

    def test_is_not_cacheable_jpg(self):
        """Test JPG images are not cacheable."""
        mock_path = MagicMock(spec=AsyncPath)
        mock_path.suffix = ".jpg"
        assert _is_cacheable_file(mock_path) is False

    def test_is_not_cacheable_woff(self):
        """Test font files are not cacheable."""
        mock_path = MagicMock(spec=AsyncPath)
        mock_path.suffix = ".woff2"
        assert _is_cacheable_file(mock_path) is False

    def test_cacheable_extensions_constant(self):
        """Test CACHEABLE_EXTENSIONS constant."""
        assert ".css" in CACHEABLE_EXTENSIONS
        assert ".js" in CACHEABLE_EXTENSIONS
        assert ".md" in CACHEABLE_EXTENSIONS
        assert ".txt" in CACHEABLE_EXTENSIONS

    def test_non_cacheable_extensions_constant(self):
        """Test NON_CACHEABLE_EXTENSIONS constant."""
        assert ".png" in NON_CACHEABLE_EXTENSIONS
        assert ".jpg" in NON_CACHEABLE_EXTENSIONS
        assert ".woff2" in NON_CACHEABLE_EXTENSIONS


class TestSyncStatic:
    """Test sync_static functionality."""

    @pytest.mark.asyncio
    async def test_sync_static_no_storage_adapter(self, mock_strategy):
        """Test sync_static handles missing storage adapter."""

        async def _get_none(name):
            return None

        with patch("acb.depends.depends.get", AsyncMock(side_effect=_get_none)):
            result = await sync_static(strategy=mock_strategy)

            assert len(result.errors) > 0
            assert any("not available" in str(e) for e in result.errors)

    @pytest.mark.asyncio
    async def test_sync_static_no_files_found(self, mock_depends_get, mock_strategy):
        """Test sync_static with no static files."""
        with patch("acb.depends.depends.get", mock_depends_get):
            with patch("fastblocks.actions.sync.static.AsyncPath") as MockAsyncPath:
                mock_path = AsyncMock()
                mock_path.exists = AsyncMock(return_value=False)
                MockAsyncPath.return_value = mock_path

                result = await sync_static(strategy=mock_strategy)

                assert isinstance(result, StaticSyncResult)
                assert len(result.synced_items) == 0

    @pytest.mark.asyncio
    async def test_sync_static_with_file_patterns(
        self, mock_depends_get, mock_strategy
    ):
        """Test sync_static with custom file patterns."""
        with patch("acb.depends.depends.get", mock_depends_get):
            with patch("fastblocks.actions.sync.static.AsyncPath") as MockAsyncPath:
                mock_path = AsyncMock()
                mock_path.exists = AsyncMock(return_value=False)
                MockAsyncPath.return_value = mock_path

                result = await sync_static(
                    file_patterns=["*.css", "*.js"], strategy=mock_strategy
                )

                assert isinstance(result, StaticSyncResult)

    @pytest.mark.asyncio
    async def test_sync_static_with_exclude_patterns(
        self, mock_depends_get, mock_strategy
    ):
        """Test sync_static with exclude patterns."""
        with patch("acb.depends.depends.get", mock_depends_get):
            with patch("fastblocks.actions.sync.static.AsyncPath") as MockAsyncPath:
                mock_path = AsyncMock()
                mock_path.exists = AsyncMock(return_value=False)
                MockAsyncPath.return_value = mock_path

                result = await sync_static(
                    exclude_patterns=["*.tmp", "*.log"], strategy=mock_strategy
                )

                assert isinstance(result, StaticSyncResult)

    @pytest.mark.asyncio
    async def test_sync_static_custom_storage_bucket(
        self, mock_depends_get, mock_strategy
    ):
        """Test sync_static with custom storage bucket."""
        with patch("acb.depends.depends.get", mock_depends_get):
            with patch("fastblocks.actions.sync.static.AsyncPath") as MockAsyncPath:
                mock_path = AsyncMock()
                mock_path.exists = AsyncMock(return_value=False)
                MockAsyncPath.return_value = mock_path

                result = await sync_static(
                    storage_bucket="custom_bucket", strategy=mock_strategy
                )

                assert isinstance(result, StaticSyncResult)

    @pytest.mark.asyncio
    async def test_sync_static_with_custom_path(self, mock_depends_get, mock_strategy):
        """Test sync_static with custom static path."""
        with patch("acb.depends.depends.get", mock_depends_get):
            custom_path = AsyncPath("custom/static")

            with patch.object(custom_path, "exists", AsyncMock(return_value=False)):
                result = await sync_static(
                    static_path=custom_path, strategy=mock_strategy
                )

                assert isinstance(result, StaticSyncResult)

    @pytest.mark.asyncio
    async def test_sync_static_handles_exceptions(
        self, mock_storage, mock_cache, mock_strategy
    ):
        """Test sync_static handles exceptions gracefully."""
        mock_storage._create_bucket.side_effect = Exception("Storage error")

        async def _get(name):
            if name == "storage":
                return mock_storage
            elif name == "cache":
                return mock_cache
            return None

        with patch("acb.depends.depends.get", AsyncMock(side_effect=_get)):
            with patch("fastblocks.actions.sync.static.AsyncPath") as MockAsyncPath:
                mock_path = AsyncMock()
                mock_path.exists = AsyncMock(return_value=False)
                MockAsyncPath.return_value = mock_path

                result = await sync_static(strategy=mock_strategy)

                assert isinstance(result, StaticSyncResult)


class TestWarmStaticCache:
    """Test warm_static_cache functionality."""

    @pytest.mark.asyncio
    async def test_warm_cache_no_cache_adapter(self):
        """Test warm_static_cache when cache adapter not available."""

        async def _get_none(name):
            return None

        with patch("acb.depends.depends.get", AsyncMock(side_effect=_get_none)):
            result = await warm_static_cache()

            assert len(result["errors"]) > 0

    @pytest.mark.asyncio
    async def test_warm_cache_with_default_paths(self, mock_depends_get):
        """Test warm_static_cache with default static paths."""
        with patch("acb.depends.depends.get", mock_depends_get):
            result = await warm_static_cache()

            assert "warmed" in result
            assert "errors" in result
            assert "skipped" in result

    @pytest.mark.asyncio
    async def test_warm_cache_with_custom_paths(self, mock_depends_get):
        """Test warm_static_cache with custom paths."""
        custom_paths = ["custom/style.css", "custom/script.js"]

        with patch("acb.depends.depends.get", mock_depends_get):
            result = await warm_static_cache(static_paths=custom_paths)

            assert "warmed" in result

    @pytest.mark.asyncio
    async def test_warm_cache_with_custom_namespace(self, mock_depends_get):
        """Test warm_static_cache with custom cache namespace."""
        with patch("acb.depends.depends.get", mock_depends_get):
            result = await warm_static_cache(cache_namespace="custom_static")

            assert "warmed" in result

    @pytest.mark.asyncio
    async def test_warm_cache_handles_exceptions(self, mock_storage, mock_cache):
        """Test warm_static_cache handles exceptions."""
        mock_cache.set.side_effect = Exception("Cache error")

        async def _get(name):
            if name == "storage":
                return mock_storage
            elif name == "cache":
                return mock_cache
            return None

        with patch("acb.depends.depends.get", AsyncMock(side_effect=_get)):
            result = await warm_static_cache(static_paths=["test.css"])

            assert "errors" in result


class TestBackupStaticFiles:
    """Test backup_static_files functionality."""

    @pytest.mark.asyncio
    async def test_backup_static_path_not_exists(self):
        """Test backup_static_files when path doesn't exist."""
        with patch("fastblocks.actions.sync.static.AsyncPath") as MockAsyncPath:
            mock_path = AsyncMock()
            mock_path.exists = AsyncMock(return_value=False)
            MockAsyncPath.return_value = mock_path

            result = await backup_static_files()

            assert len(result["errors"]) > 0
            assert any("does not exist" in str(e) for e in result["errors"])

    @pytest.mark.asyncio
    async def test_backup_static_with_custom_path(self):
        """Test backup_static_files with custom path."""
        custom_path = AsyncPath("custom/static")

        with patch.object(custom_path, "exists", AsyncMock(return_value=False)):
            result = await backup_static_files(static_path=custom_path)

            assert len(result["errors"]) > 0

    @pytest.mark.asyncio
    async def test_backup_static_with_custom_suffix(self):
        """Test backup_static_files with custom backup suffix."""
        with patch("fastblocks.actions.sync.static.AsyncPath") as MockAsyncPath:
            mock_path = AsyncMock()
            mock_path.exists = AsyncMock(return_value=False)
            MockAsyncPath.return_value = mock_path

            result = await backup_static_files(backup_suffix="custom_backup")

            assert "errors" in result

    @pytest.mark.asyncio
    async def test_backup_static_handles_exceptions(self):
        """Test backup_static_files handles exceptions."""
        with patch("fastblocks.actions.sync.static.AsyncPath") as MockAsyncPath:
            mock_path = AsyncMock()
            mock_path.exists = AsyncMock(return_value=True)
            # Make rglob raise an exception
            mock_path.rglob = AsyncMock(side_effect=Exception("Rglob error"))
            MockAsyncPath.return_value = mock_path

            result = await backup_static_files()

            assert len(result["errors"]) > 0
