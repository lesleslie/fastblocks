"""Tests for fastblocks/actions/sync/strategies.py uncovered helpers.

Targets 105 missing statements before this file. Tests cover the
helper surface: ``compare_content``, ``get_file_info``,
``_check_missing_files``, ``_check_content_differences``,
``should_sync``, ``resolve_conflict``, ``create_backup``, and
``get_sync_summary``.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastblocks.actions.sync.strategies import (
    ConflictStrategy,
    SyncDirection,
    SyncResult,
    SyncStrategy,
    _check_content_differences,
    _check_missing_files,
    compare_content,
    create_backup,
    get_file_info,
    get_sync_summary,
    resolve_conflict,
    should_sync,
)


@pytest.mark.unit
class TestCompareContent:
    def test_identical_content_returns_true(self) -> None:
        assert compare_content(b"abc", b"abc") is True

    def test_different_content_returns_false(self) -> None:
        assert compare_content(b"abc", b"xyz") is False

    def test_different_length_returns_false(self) -> None:
        assert compare_content(b"abc", b"abcd") is False

    def test_no_hash_comparison_for_small_content(self) -> None:
        # use_hash=False forces byte-by-byte comparison.
        assert compare_content(b"abc", b"abc", use_hash=False) is True
        assert compare_content(b"abc", b"abd", use_hash=False) is False


@pytest.mark.unit
class TestGetFileInfo:
    async def test_get_file_info_returns_metadata(self, tmp_path: Path) -> None:
        f = tmp_path / "info.txt"
        f.write_bytes(b"hello world")
        info = await get_file_info(f)
        assert info["exists"] is True
        assert info["content"] == b"hello world"
        assert info["size"] == len(b"hello world")
        assert info["mtime"] > 0
        assert info["content_hash"]

    async def test_get_file_info_missing_file(self, tmp_path: Path) -> None:
        info = await get_file_info(tmp_path / "missing.txt")
        assert info["exists"] is False
        assert info["size"] == 0


@pytest.mark.unit
class TestCheckMissingFiles:
    def test_local_missing_with_pull(self) -> None:
        result = _check_missing_files(
            local_exists=False,
            remote_exists=True,
            direction=SyncDirection.PULL,
        )
        assert result == (True, "local_missing")

    def test_remote_missing_with_push(self) -> None:
        result = _check_missing_files(
            local_exists=True,
            remote_exists=False,
            direction=SyncDirection.PUSH,
        )
        assert result == (True, "remote_missing")

    def test_both_present_returns_none(self) -> None:
        result = _check_missing_files(
            local_exists=True,
            remote_exists=True,
            direction=SyncDirection.BIDIRECTIONAL,
        )
        assert result is None


@pytest.mark.unit
class TestCheckContentDifferences:
    def test_no_difference(self) -> None:
        info = {"exists": True, "content": b"abc", "mtime": 100.0, "content_hash": "abc"}
        other = {"exists": True, "content": b"abc", "mtime": 100.0, "content_hash": "abc"}
        result = _check_content_differences(
            info, other, SyncDirection.BIDIRECTIONAL
        )
        assert result[0] is False

    def test_content_differs(self) -> None:
        info = {"exists": True, "content": b"abc", "mtime": 100.0, "content_hash": "abc"}
        other = {"exists": True, "content": b"xyz", "mtime": 100.0, "content_hash": "xyz"}
        result = _check_content_differences(
            info, other, SyncDirection.BIDIRECTIONAL
        )
        assert result[0] is True


@pytest.mark.unit
class TestShouldSync:
    def test_should_sync_returns_true_for_differences(self) -> None:
        local = {"exists": True, "content": b"abc", "mtime": 100.0, "content_hash": "abc"}
        remote = {"exists": True, "content": b"xyz", "mtime": 200.0, "content_hash": "xyz"}
        should, reason = should_sync(
            local, remote, SyncDirection.BIDIRECTIONAL
        )
        assert should is True

    def test_should_sync_returns_false_when_identical(self) -> None:
        local = {"exists": True, "content": b"abc", "mtime": 100.0, "content_hash": "abc"}
        remote = {"exists": True, "content": b"abc", "mtime": 100.0, "content_hash": "abc"}
        should, reason = should_sync(
            local, remote, SyncDirection.BIDIRECTIONAL
        )
        assert should is False


@pytest.mark.unit
class TestResolveConflict:
    async def test_resolve_conflict_newest_wins(self) -> None:
        local_path = Path("/tmp/local")
        content, reason = await resolve_conflict(
            local_path,
            remote_content=b"remote",
            local_content=b"local",
            strategy=ConflictStrategy.NEWEST_WINS,
            local_mtime=200.0,
            remote_mtime=100.0,
        )
        # Local is newer → wins.
        assert content == b"local"

    async def test_resolve_conflict_remote_wins(self) -> None:
        local_path = Path("/tmp/local")
        content, reason = await resolve_conflict(
            local_path,
            remote_content=b"remote",
            local_content=b"local",
            strategy=ConflictStrategy.REMOTE_WINS,
            local_mtime=100.0,
            remote_mtime=200.0,
        )
        assert content == b"remote"

    async def test_resolve_conflict_local_wins(self) -> None:
        local_path = Path("/tmp/local")
        content, reason = await resolve_conflict(
            local_path,
            remote_content=b"remote",
            local_content=b"local",
            strategy=ConflictStrategy.LOCAL_WINS,
            local_mtime=100.0,
            remote_mtime=200.0,
        )
        assert content == b"local"

    async def test_resolve_conflict_manual_raises(self) -> None:
        local_path = Path("/tmp/local")
        with pytest.raises(ValueError):
            await resolve_conflict(
                local_path,
                remote_content=b"remote",
                local_content=b"local",
                strategy=ConflictStrategy.MANUAL,
                local_mtime=100.0,
                remote_mtime=200.0,
            )

    async def test_resolve_conflict_backup_both(self, tmp_path: Path) -> None:
        local_path = tmp_path / "local.txt"
        local_path.write_bytes(b"local content")
        content, reason = await resolve_conflict(
            local_path,
            remote_content=b"remote",
            local_content=b"local content",
            strategy=ConflictStrategy.BACKUP_BOTH,
            local_mtime=100.0,
            remote_mtime=200.0,
        )
        # BACKUP_BOTH → backup is created; either side wins.
        assert content is not None


@pytest.mark.unit
class TestCreateBackup:
    async def test_create_backup_creates_file(self, tmp_path: Path) -> None:
        f = tmp_path / "original.txt"
        f.write_bytes(b"hello")
        backup = await create_backup(f, suffix="test")
        assert backup.exists()
        assert backup.read_bytes() == b"hello"

    async def test_create_backup_default_suffix(self, tmp_path: Path) -> None:
        f = tmp_path / "original.txt"
        f.write_bytes(b"hello")
        backup = await create_backup(f)
        assert backup.exists()
        assert backup.read_bytes() == b"hello"


@pytest.mark.unit
class TestGetSyncSummary:
    def test_get_sync_summary_returns_dict(self) -> None:
        result = SyncResult()
        summary = get_sync_summary(result)
        assert isinstance(summary, dict)
        # Summary contains the basic result fields.
        assert "total_processed" in summary or "success" in summary

    def test_get_sync_summary_with_synced_items(self) -> None:
        result = SyncResult(synced_items=["a", "b", "c"])
        summary = get_sync_summary(result)
        assert isinstance(summary, dict)
        assert summary.get("synced") == 3 or summary.get("total_processed") == 3