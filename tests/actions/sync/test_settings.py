"""Tests for settings synchronization functionality."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from anyio import Path as AsyncPath
from fastblocks.actions.sync.settings import (
    SettingsSyncResult,
    backup_settings,
    sync_settings,
    validate_all_settings,
)
from fastblocks.actions.sync.strategies import SyncDirection, SyncStrategy


@pytest.fixture
def mock_storage():
    """Create a mock storage adapter."""
    storage = AsyncMock()

    # Mock bucket
    mock_bucket = AsyncMock()
    mock_bucket.exists = AsyncMock(return_value=False)
    mock_bucket.read = AsyncMock(return_value=b"test: value")
    mock_bucket.write = AsyncMock()
    mock_bucket.stat = AsyncMock(return_value={"mtime": 1234567890})

    storage.settings = mock_bucket
    storage._create_bucket = AsyncMock()

    return storage


@pytest.fixture
def mock_strategy():
    """Create a mock sync strategy."""
    strategy = SyncStrategy()
    strategy.direction = SyncDirection.BIDIRECTIONAL
    strategy.dry_run = False
    strategy.backup_on_conflict = True
    return strategy


@pytest.fixture
def mock_async_path():
    """Create mock for AsyncPath operations."""
    async_path = AsyncMock(spec=AsyncPath)
    async_path.exists = AsyncMock(return_value=True)
    async_path.is_file = AsyncMock(return_value=True)
    async_path.read_text = AsyncMock(return_value="module: test\nbucket: settings")
    async_path.read_bytes = AsyncMock(return_value=b"test: value")
    async_path.write_bytes = AsyncMock()
    async_path.parent = AsyncMock()
    async_path.parent.mkdir = AsyncMock()
    async_path.stem = "test_adapter"
    async_path.relative_to = MagicMock(return_value=Path("test_adapter.yml"))
    return async_path


@pytest.fixture
def mock_depends_get(mock_storage):
    """Create a mock for depends.get that returns the storage adapter."""

    async def _get(name):
        if name == "storage":
            return mock_storage
        return None

    return AsyncMock(side_effect=_get)


class TestSettingsSyncResult:
    """Test SettingsSyncResult functionality."""

    def test_result_initialization_defaults(self):
        """Test SettingsSyncResult initializes with default values."""
        result = SettingsSyncResult()

        assert result.config_reloaded == []
        assert result.adapters_affected == []
        assert result.synced_items == []
        assert result.errors == []

    def test_result_initialization_with_values(self):
        """Test SettingsSyncResult initializes with provided values."""
        config = ["adapter1", "adapter2"]
        adapters = ["adapter1"]

        result = SettingsSyncResult(config_reloaded=config, adapters_affected=adapters)

        assert result.config_reloaded == config
        assert result.adapters_affected == adapters


class TestSyncSettings:
    """Test sync_settings functionality."""

    @pytest.mark.asyncio
    async def test_sync_settings_no_storage_adapter(self, mock_strategy):
        """Test sync_settings handles missing storage adapter."""

        async def _get_none(name):
            return None

        with patch("acb.depends.depends.get", AsyncMock(side_effect=_get_none)):
            result = await sync_settings(strategy=mock_strategy)

            assert len(result.errors) > 0
            assert any("not available" in str(e) for e in result.errors)

    @pytest.mark.asyncio
    async def test_sync_settings_no_files_found(self, mock_depends_get, mock_strategy):
        """Test sync_settings with no settings files."""
        with patch("acb.depends.depends.get", mock_depends_get):
            with patch("fastblocks.actions.sync.settings.AsyncPath") as MockAsyncPath:
                mock_path = AsyncMock()
                mock_path.exists = AsyncMock(return_value=False)
                MockAsyncPath.return_value = mock_path

                result = await sync_settings(strategy=mock_strategy)

                assert isinstance(result, SettingsSyncResult)
                assert len(result.synced_items) == 0

    @pytest.mark.asyncio
    async def test_sync_settings_with_adapter_filter(
        self, mock_depends_get, mock_strategy
    ):
        """Test sync_settings with specific adapter names."""
        with patch("acb.depends.depends.get", mock_depends_get):
            with patch("fastblocks.actions.sync.settings.AsyncPath") as MockAsyncPath:
                mock_path = AsyncMock()
                mock_path.exists = AsyncMock(return_value=False)
                MockAsyncPath.return_value = mock_path

                result = await sync_settings(
                    adapter_names=["adapter1", "adapter2"], strategy=mock_strategy
                )

                assert isinstance(result, SettingsSyncResult)

    @pytest.mark.asyncio
    async def test_sync_settings_with_reload_disabled(
        self, mock_depends_get, mock_strategy
    ):
        """Test sync_settings with config reload disabled."""
        with patch("acb.depends.depends.get", mock_depends_get):
            with patch("fastblocks.actions.sync.settings.AsyncPath") as MockAsyncPath:
                mock_path = AsyncMock()
                mock_path.exists = AsyncMock(return_value=False)
                MockAsyncPath.return_value = mock_path

                result = await sync_settings(
                    reload_config=False, strategy=mock_strategy
                )

                assert isinstance(result, SettingsSyncResult)
                assert len(result.config_reloaded) == 0

    @pytest.mark.asyncio
    async def test_sync_settings_custom_storage_bucket(
        self, mock_depends_get, mock_strategy
    ):
        """Test sync_settings with custom storage bucket."""
        with patch("acb.depends.depends.get", mock_depends_get):
            with patch("fastblocks.actions.sync.settings.AsyncPath") as MockAsyncPath:
                mock_path = AsyncMock()
                mock_path.exists = AsyncMock(return_value=False)
                MockAsyncPath.return_value = mock_path

                result = await sync_settings(
                    storage_bucket="custom_bucket", strategy=mock_strategy
                )

                assert isinstance(result, SettingsSyncResult)

    @pytest.mark.asyncio
    async def test_sync_settings_with_custom_path(
        self, mock_depends_get, mock_strategy
    ):
        """Test sync_settings with custom settings path."""
        with patch("acb.depends.depends.get", mock_depends_get):
            custom_path = AsyncPath("custom/settings")

            with patch.object(custom_path, "exists", AsyncMock(return_value=False)):
                result = await sync_settings(
                    settings_path=custom_path, strategy=mock_strategy
                )

                assert isinstance(result, SettingsSyncResult)

    @pytest.mark.asyncio
    async def test_sync_settings_handles_exceptions(self, mock_storage, mock_strategy):
        """Test sync_settings handles exceptions gracefully."""
        mock_storage._create_bucket.side_effect = Exception("Storage error")

        async def _get(name):
            if name == "storage":
                return mock_storage
            return None

        with patch("acb.depends.depends.get", AsyncMock(side_effect=_get)):
            with patch("fastblocks.actions.sync.settings.AsyncPath") as MockAsyncPath:
                mock_path = AsyncMock()
                mock_path.exists = AsyncMock(return_value=False)
                MockAsyncPath.return_value = mock_path

                result = await sync_settings(strategy=mock_strategy)

                assert isinstance(result, SettingsSyncResult)


class TestBackupSettings:
    """Test backup_settings functionality."""

    @pytest.mark.asyncio
    async def test_backup_settings_path_not_exists(self):
        """Test backup_settings when path doesn't exist."""
        with patch("fastblocks.actions.sync.settings.AsyncPath") as MockAsyncPath:
            mock_path = AsyncMock()
            mock_path.exists = AsyncMock(return_value=False)
            MockAsyncPath.return_value = mock_path

            result = await backup_settings()

            assert len(result["errors"]) > 0
            assert any("does not exist" in str(e) for e in result["errors"])

    @pytest.mark.asyncio
    async def test_backup_settings_with_custom_path(self):
        """Test backup_settings with custom path."""
        custom_path = AsyncPath("custom/settings")

        with patch.object(custom_path, "exists", AsyncMock(return_value=False)):
            result = await backup_settings(settings_path=custom_path)

            assert len(result["errors"]) > 0

    @pytest.mark.asyncio
    async def test_backup_settings_with_custom_suffix(self):
        """Test backup_settings with custom backup suffix."""
        with patch("fastblocks.actions.sync.settings.AsyncPath") as MockAsyncPath:
            mock_path = AsyncMock()
            mock_path.exists = AsyncMock(return_value=False)
            MockAsyncPath.return_value = mock_path

            result = await backup_settings(backup_suffix="custom_backup")

            assert "errors" in result

    @pytest.mark.asyncio
    async def test_backup_settings_handles_exceptions(self):
        """Test backup_settings handles exceptions."""
        with patch("fastblocks.actions.sync.settings.AsyncPath") as MockAsyncPath:
            mock_path = AsyncMock()
            mock_path.exists = AsyncMock(return_value=True)
            # Make rglob raise an exception
            mock_path.rglob = AsyncMock(side_effect=Exception("Rglob error"))
            MockAsyncPath.return_value = mock_path

            result = await backup_settings()

            assert len(result["errors"]) > 0


class TestValidateSettings:
    """Test validate_all_settings functionality."""

    @pytest.mark.asyncio
    async def test_validate_all_settings_no_files(self):
        """Test validate_all_settings with no files."""
        with patch("fastblocks.actions.sync.settings.AsyncPath") as MockAsyncPath:
            mock_path = AsyncMock()
            mock_path.exists = AsyncMock(return_value=False)
            MockAsyncPath.return_value = mock_path

            with patch(
                "fastblocks.actions.sync.settings._discover_settings_files",
                AsyncMock(return_value=[]),
            ):
                result = await validate_all_settings()

                assert result["total_checked"] == 0
                assert len(result["valid"]) == 0

    @pytest.mark.asyncio
    async def test_validate_all_settings_with_valid_files(self):
        """Test validate_all_settings with valid YAML files."""
        mock_file = AsyncMock()
        mock_file.exists = AsyncMock(return_value=True)
        mock_file.read_bytes = AsyncMock(return_value=b"test: value")

        settings_files = [{"local_path": mock_file}]

        with patch(
            "fastblocks.actions.sync.settings._discover_settings_files",
            AsyncMock(return_value=settings_files),
        ):
            result = await validate_all_settings()

            assert result["total_checked"] == 1
            assert len(result["valid"]) == 1

    @pytest.mark.asyncio
    async def test_validate_all_settings_with_invalid_yaml(self):
        """Test validate_all_settings with invalid YAML."""
        mock_file = AsyncMock()
        mock_file.exists = AsyncMock(return_value=True)
        mock_file.read_bytes = AsyncMock(return_value=b"invalid: yaml: ::::")

        settings_files = [{"local_path": mock_file}]

        with patch(
            "fastblocks.actions.sync.settings._discover_settings_files",
            AsyncMock(return_value=settings_files),
        ):
            result = await validate_all_settings()

            assert result["total_checked"] == 1
            assert len(result["invalid"]) == 1

    @pytest.mark.asyncio
    async def test_validate_all_settings_with_missing_files(self):
        """Test validate_all_settings with missing files."""
        mock_file = AsyncMock()
        mock_file.exists = AsyncMock(return_value=False)

        settings_files = [{"local_path": mock_file}]

        with patch(
            "fastblocks.actions.sync.settings._discover_settings_files",
            AsyncMock(return_value=settings_files),
        ):
            result = await validate_all_settings()

            assert result["total_checked"] == 1
            assert len(result["missing"]) == 1

    @pytest.mark.asyncio
    async def test_validate_all_settings_custom_path(self):
        """Test validate_all_settings with custom path."""
        custom_path = AsyncPath("custom/settings")

        with patch(
            "fastblocks.actions.sync.settings._discover_settings_files",
            AsyncMock(return_value=[]),
        ):
            result = await validate_all_settings(settings_path=custom_path)

            assert "total_checked" in result

    @pytest.mark.asyncio
    async def test_validate_all_settings_handles_exceptions(self):
        """Test validate_all_settings handles exceptions."""
        with patch(
            "fastblocks.actions.sync.settings._discover_settings_files",
            side_effect=Exception("Discovery error"),
        ):
            result = await validate_all_settings()

            assert "error" in result
