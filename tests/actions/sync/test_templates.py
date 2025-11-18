"""Tests for template synchronization functionality."""

from unittest.mock import AsyncMock, patch

import pytest
from anyio import Path as AsyncPath
from fastblocks.actions.sync.strategies import SyncDirection, SyncStrategy
from fastblocks.actions.sync.templates import (
    TemplateSyncResult,
    sync_templates,
)


@pytest.fixture
def mock_storage():
    """Create a mock storage adapter."""
    storage = AsyncMock()

    # Mock bucket
    mock_bucket = AsyncMock()
    mock_bucket.exists = AsyncMock(return_value=False)
    mock_bucket.read = AsyncMock(return_value=b"template content")
    mock_bucket.write = AsyncMock()
    mock_bucket.stat = AsyncMock(return_value={"mtime": 1234567890})

    storage.templates = mock_bucket
    storage._create_bucket = AsyncMock()

    return storage


@pytest.fixture
def mock_cache():
    """Create a mock cache adapter."""
    cache = AsyncMock()
    cache.set = AsyncMock()
    cache.delete = AsyncMock()
    cache.delete_pattern = AsyncMock(return_value=["key1", "key2"])
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


class TestTemplateSyncResult:
    """Test TemplateSyncResult functionality."""

    def test_result_initialization_defaults(self):
        """Test TemplateSyncResult initializes with default values."""
        result = TemplateSyncResult()

        assert result.cache_invalidated == []
        assert result.bytecode_cleared == []
        assert result.synced_items == []
        assert result.errors == []
        assert result.conflicts == []

    def test_result_initialization_with_values(self):
        """Test TemplateSyncResult initializes with provided values."""
        cache_inv = ["template:index.html"]
        bytecode = ["bccache:index.html"]

        result = TemplateSyncResult(
            cache_invalidated=cache_inv, bytecode_cleared=bytecode
        )

        assert result.cache_invalidated == cache_inv
        assert result.bytecode_cleared == bytecode

    def test_synchronized_files_property(self):
        """Test synchronized_files property."""
        result = TemplateSyncResult()
        result.synced_items = ["file1.html", "file2.html"]

        assert result.synchronized_files == ["file1.html", "file2.html"]

    def test_sync_status_success(self):
        """Test sync_status returns success."""
        result = TemplateSyncResult()
        result.synced_items = ["file1.html"]

        assert result.sync_status == "success"

    def test_sync_status_error(self):
        """Test sync_status returns error."""
        result = TemplateSyncResult()
        result.errors = [Exception("Error")]

        assert result.sync_status == "error"

    def test_sync_status_conflict(self):
        """Test sync_status returns conflict."""
        result = TemplateSyncResult()
        result.conflicts = [{"file": "test.html"}]

        assert result.sync_status == "conflict"

    def test_sync_status_no_changes(self):
        """Test sync_status returns no_changes."""
        result = TemplateSyncResult()

        assert result.sync_status == "no_changes"

    def test_dry_run_property(self):
        """Test dry_run property."""
        result = TemplateSyncResult()
        result._dry_run = True

        assert result.dry_run is True

    def test_direction_property(self):
        """Test direction property."""
        result = TemplateSyncResult()
        result._direction = "bidirectional"

        assert result.direction == "bidirectional"

    def test_conflict_strategy_property(self):
        """Test conflict_strategy property."""
        result = TemplateSyncResult()
        result._conflict_strategy = "newest_wins"

        assert result.conflict_strategy == "newest_wins"


class TestSyncTemplates:
    """Test sync_templates functionality."""

    @pytest.mark.asyncio
    async def test_sync_templates_no_storage_adapter(self, mock_strategy):
        """Test sync_templates handles missing storage adapter."""

        async def _get_none(name):
            return None

        with patch("acb.depends.depends.get", AsyncMock(side_effect=_get_none)):
            result = await sync_templates(strategy=mock_strategy)

            assert len(result.errors) > 0
            assert any("not available" in str(e) for e in result.errors)

    @pytest.mark.asyncio
    async def test_sync_templates_with_defaults(self, mock_depends_get):
        """Test sync_templates with default parameters."""
        with patch("acb.depends.depends.get", mock_depends_get):
            with patch(
                "fastblocks.actions.sync.templates._discover_template_files",
                AsyncMock(return_value=[]),
            ):
                result = await sync_templates()

                assert isinstance(result, TemplateSyncResult)

    @pytest.mark.asyncio
    async def test_sync_templates_with_custom_paths(
        self, mock_depends_get, mock_strategy
    ):
        """Test sync_templates with custom template paths."""
        custom_paths = [AsyncPath("custom/templates")]

        with patch("acb.depends.depends.get", mock_depends_get):
            with patch(
                "fastblocks.actions.sync.templates._discover_template_files",
                AsyncMock(return_value=[]),
            ):
                result = await sync_templates(
                    template_paths=custom_paths, strategy=mock_strategy
                )

                assert isinstance(result, TemplateSyncResult)

    @pytest.mark.asyncio
    async def test_sync_templates_with_patterns(self, mock_depends_get, mock_strategy):
        """Test sync_templates with custom patterns."""
        patterns = ["*.html", "*.jinja2"]

        with patch("acb.depends.depends.get", mock_depends_get):
            with patch(
                "fastblocks.actions.sync.templates._discover_template_files",
                AsyncMock(return_value=[]),
            ):
                result = await sync_templates(patterns=patterns, strategy=mock_strategy)

                assert isinstance(result, TemplateSyncResult)

    @pytest.mark.asyncio
    async def test_sync_templates_with_storage_bucket(
        self, mock_depends_get, mock_strategy
    ):
        """Test sync_templates with custom storage bucket."""
        with patch("acb.depends.depends.get", mock_depends_get):
            with patch(
                "fastblocks.actions.sync.templates._discover_template_files",
                AsyncMock(return_value=[]),
            ):
                result = await sync_templates(
                    storage_bucket="custom_bucket", strategy=mock_strategy
                )

                assert isinstance(result, TemplateSyncResult)

    @pytest.mark.asyncio
    async def test_sync_templates_with_direction_cloud_to_local(self, mock_depends_get):
        """Test sync_templates with cloud_to_local direction."""
        with patch("acb.depends.depends.get", mock_depends_get):
            with patch(
                "fastblocks.actions.sync.templates._discover_template_files",
                AsyncMock(return_value=[]),
            ):
                result = await sync_templates(direction="cloud_to_local")

                assert isinstance(result, TemplateSyncResult)
                assert result.direction == "cloud_to_local"

    @pytest.mark.asyncio
    async def test_sync_templates_with_direction_local_to_cloud(self, mock_depends_get):
        """Test sync_templates with local_to_cloud direction."""
        with patch("acb.depends.depends.get", mock_depends_get):
            with patch(
                "fastblocks.actions.sync.templates._discover_template_files",
                AsyncMock(return_value=[]),
            ):
                result = await sync_templates(direction="local_to_cloud")

                assert isinstance(result, TemplateSyncResult)
                assert result.direction == "local_to_cloud"

    @pytest.mark.asyncio
    async def test_sync_templates_with_direction_bidirectional(self, mock_depends_get):
        """Test sync_templates with bidirectional direction."""
        with patch("acb.depends.depends.get", mock_depends_get):
            with patch(
                "fastblocks.actions.sync.templates._discover_template_files",
                AsyncMock(return_value=[]),
            ):
                result = await sync_templates(direction="bidirectional")

                assert isinstance(result, TemplateSyncResult)
                assert result.direction == "bidirectional"

    @pytest.mark.asyncio
    async def test_sync_templates_with_conflict_strategy_local_wins(
        self, mock_depends_get
    ):
        """Test sync_templates with local_wins conflict strategy."""
        with patch("acb.depends.depends.get", mock_depends_get):
            with patch(
                "fastblocks.actions.sync.templates._discover_template_files",
                AsyncMock(return_value=[]),
            ):
                result = await sync_templates(conflict_strategy="local_wins")

                assert isinstance(result, TemplateSyncResult)
                assert result.conflict_strategy == "local_wins"

    @pytest.mark.asyncio
    async def test_sync_templates_with_conflict_strategy_remote_wins(
        self, mock_depends_get
    ):
        """Test sync_templates with remote_wins conflict strategy."""
        with patch("acb.depends.depends.get", mock_depends_get):
            with patch(
                "fastblocks.actions.sync.templates._discover_template_files",
                AsyncMock(return_value=[]),
            ):
                result = await sync_templates(conflict_strategy="remote_wins")

                assert isinstance(result, TemplateSyncResult)
                assert result.conflict_strategy == "remote_wins"

    @pytest.mark.asyncio
    async def test_sync_templates_with_conflict_strategy_newest_wins(
        self, mock_depends_get
    ):
        """Test sync_templates with newest_wins conflict strategy."""
        with patch("acb.depends.depends.get", mock_depends_get):
            with patch(
                "fastblocks.actions.sync.templates._discover_template_files",
                AsyncMock(return_value=[]),
            ):
                result = await sync_templates(conflict_strategy="newest_wins")

                assert isinstance(result, TemplateSyncResult)
                assert result.conflict_strategy == "newest_wins"

    @pytest.mark.asyncio
    async def test_sync_templates_with_dry_run_enabled(self, mock_depends_get):
        """Test sync_templates with dry_run enabled."""
        with patch("acb.depends.depends.get", mock_depends_get):
            with patch(
                "fastblocks.actions.sync.templates._discover_template_files",
                AsyncMock(return_value=[]),
            ):
                result = await sync_templates(dry_run=True)

                assert isinstance(result, TemplateSyncResult)
                assert result.dry_run is True

    @pytest.mark.asyncio
    async def test_sync_templates_with_filters(self, mock_depends_get):
        """Test sync_templates with filters."""
        filters = {"include_patterns": ["*.html"]}

        with patch("acb.depends.depends.get", mock_depends_get):
            with patch(
                "fastblocks.actions.sync.templates._discover_template_files",
                AsyncMock(return_value=[]),
            ):
                result = await sync_templates(filters=filters)

                assert isinstance(result, TemplateSyncResult)

    @pytest.mark.asyncio
    async def test_sync_templates_handles_initialization_exceptions(
        self, mock_strategy
    ):
        """Test sync_templates handles initialization exceptions."""
        with patch("acb.depends.depends.get", side_effect=Exception("Init error")):
            result = await sync_templates(strategy=mock_strategy)

            assert isinstance(result, TemplateSyncResult)
            assert len(result.errors) > 0
