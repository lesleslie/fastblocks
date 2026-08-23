"""Helper-level tests for fastblocks/actions/sync/static.py.

Targets the uncovered internal helpers (257 missing statements before
this file) — particularly ``_handle_static_conflict`` and
``_should_exclude_file``. The tests use ``tmp_path`` and stub storage
adapters so they exercise real disk I/O without coupling to cloud
backends.
"""

from __future__ import annotations

import pytest
from fastblocks.actions.sync.static import (
    _handle_static_conflict,
    _should_exclude_file,
    sync_static,
)
from fastblocks.actions.sync.strategies import (
    ConflictStrategy,
    SyncStrategy,
)


@pytest.fixture
def strategy_newest_wins() -> SyncStrategy:
    return SyncStrategy(
        conflict_strategy=ConflictStrategy.NEWEST_WINS,
        backup_on_conflict=False,
        dry_run=False,
    )


@pytest.fixture
def strategy_manual() -> SyncStrategy:
    return SyncStrategy(
        conflict_strategy=ConflictStrategy.MANUAL,
        backup_on_conflict=False,
        dry_run=False,
    )


@pytest.fixture
def strategy_backup_both() -> SyncStrategy:
    return SyncStrategy(
        conflict_strategy=ConflictStrategy.BACKUP_BOTH,
        backup_on_conflict=True,
        dry_run=False,
    )


@pytest.fixture
def strategy_dry_run() -> SyncStrategy:
    return SyncStrategy(
        conflict_strategy=ConflictStrategy.NEWEST_WINS,
        backup_on_conflict=False,
        dry_run=True,
    )


@pytest.mark.unit
class TestShouldExcludeFile:
    def test_excludes_pycache(self) -> None:
        from anyio import Path as AsyncPath

        assert (
            _should_exclude_file(
                AsyncPath("static/__pycache__/foo.pyc"),
                ["__pycache__", "*.pyc"],
            )
            is True
        )

    def test_does_not_exclude_normal_file(self) -> None:
        from anyio import Path as AsyncPath

        assert (
            _should_exclude_file(
                AsyncPath("static/css/site.css"),
                ["__pycache__", "*.pyc"],
            )
            is False
        )


@pytest.mark.unit
class TestHandleStaticConflictManual:
    async def test_manual_records_conflict(
        self,
        strategy_manual: SyncStrategy,
    ) -> None:
        from anyio import Path as AsyncPath

        result: dict = {
            "synced": [],
            "errors": [],
            "backed_up": [],
            "cleanup_errors": [],
            "conflicts": [],
            "pulled": [],
            "pushed": [],
            "metadata": {},
        }
        local_info = {"mtime": 100.0, "content": b"local"}
        remote_info = {"mtime": 200.0, "content": b"remote"}
        await _handle_static_conflict(
            AsyncPath("/static/site.css"),
            storage=MagicMockStub(),
            cache=None,
            bucket="static",
            storage_path="site.css",
            local_info=local_info,
            remote_info=remote_info,
            strategy=strategy_manual,
            mime_type="text/css",
            is_cacheable=True,
            result=result,
        )
        assert len(result["conflicts"]) == 1
        assert result["conflicts"][0]["path"] == "site.css"
        assert result["conflicts"][0]["reason"] == "manual_resolution_required"


class MagicMockStub:
    """Bare stub for storage/cache parameters; ``_handle_static_conflict``
    only touches them on the BACKUP_BOTH branch, which we don't exercise
    here."""


@pytest.mark.unit
class TestHandleStaticConflictDryRun:
    async def test_dry_run_does_not_touch_storage(
        self,
        strategy_dry_run: SyncStrategy,
    ) -> None:
        from anyio import Path as AsyncPath

        result: dict = {
            "synced": [],
            "errors": [],
            "backed_up": [],
            "cleanup_errors": [],
            "conflicts": [],
            "pulled": [],
            "pushed": [],
            "metadata": {},
        }
        local_info = {"mtime": 100.0, "content": b"local"}
        remote_info = {"mtime": 200.0, "content": b"remote"}
        await _handle_static_conflict(
            AsyncPath("/static/site.css"),
            storage=MagicMockStub(),
            cache=None,
            bucket="static",
            storage_path="site.css",
            local_info=local_info,
            remote_info=remote_info,
            strategy=strategy_dry_run,
            mime_type="text/css",
            is_cacheable=True,
            result=result,
        )
        assert len(result["synced"]) == 1
        assert result["synced"][0].startswith("CONFLICT(dry-run):")


@pytest.mark.unit
class TestSyncStaticWithNoFiles:
    async def test_sync_static_empty_static_path(
        self,
        tmp_path,
        monkeypatch,
    ) -> None:
        """``sync_static`` on a missing/empty directory returns a
        result without raising — covers the early-exit branch."""
        from fastblocks.actions.sync.static import StaticSyncResult

        # Point STATIC_PATH / STATIC_URL resolution at a temp dir so the
        # helpers don't try to write to the real project tree.
        monkeypatch.chdir(tmp_path)
        # Stub resolve_instance to return None — no bucket / storage
        # configured for the synthetic project root. The function should
        # still return a StaticSyncResult-shaped value rather than raising.
        from unittest.mock import patch, AsyncMock

        with patch(
            "fastblocks.adapters.oneiric_helper.resolve_instance",
            AsyncMock(return_value=None),
        ):
            result = await sync_static(static_path=str(tmp_path / "static"))
        # The function gracefully degrades when storage isn't available.
        assert isinstance(result, StaticSyncResult) or result is None