"""Additional helper tests for fastblocks/actions/sync/settings.py.

Targets 215 missing statements before this file. Tests cover
``_should_pull_settings``, ``_should_push_settings``,
``_has_bidirectional_conflict``, and ``_validate_yaml_content``.
"""

from __future__ import annotations

import pytest
import yaml
from fastblocks.actions.sync.settings import (
    _has_bidirectional_conflict,
    _should_pull_settings,
    _should_push_settings,
    _validate_yaml_content,
)
from fastblocks.actions.sync.strategies import (
    ConflictStrategy,
    SyncDirection,
    SyncStrategy,
)


@pytest.mark.unit
class TestValidateYAMLContent:
    async def test_valid_yaml_content(self) -> None:
        # Should not raise on valid YAML.
        await _validate_yaml_content(b"key: value\n")

    async def test_invalid_yaml_content_raises(self) -> None:
        with pytest.raises(ValueError):
            await _validate_yaml_content(b"{not valid: [")


@pytest.mark.unit
class TestShouldPullPushSettings:
    def test_should_pull_when_remote_newer(self) -> None:
        strategy = SyncStrategy(
            direction=SyncDirection.BIDIRECTIONAL,
            conflict_strategy=ConflictStrategy.NEWEST_WINS,
        )
        local = {"exists": True, "mtime": 100.0, "content": b"local"}
        remote = {"exists": True, "mtime": 200.0, "content": b"remote"}
        assert _should_pull_settings(strategy, local, remote) is True

    def test_should_not_pull_when_local_newer(self) -> None:
        strategy = SyncStrategy(
            direction=SyncDirection.BIDIRECTIONAL,
            conflict_strategy=ConflictStrategy.NEWEST_WINS,
        )
        local = {"exists": True, "mtime": 200.0, "content": b"local"}
        remote = {"exists": True, "mtime": 100.0, "content": b"remote"}
        assert _should_pull_settings(strategy, local, remote) is False

    def test_should_push_when_local_newer(self) -> None:
        strategy = SyncStrategy(
            direction=SyncDirection.BIDIRECTIONAL,
            conflict_strategy=ConflictStrategy.NEWEST_WINS,
        )
        local = {"exists": True, "mtime": 200.0, "content": b"local"}
        remote = {"exists": True, "mtime": 100.0, "content": b"remote"}
        assert _should_push_settings(strategy, local, remote) is True

    def test_should_not_push_when_remote_newer(self) -> None:
        strategy = SyncStrategy(
            direction=SyncDirection.BIDIRECTIONAL,
            conflict_strategy=ConflictStrategy.NEWEST_WINS,
        )
        local = {"exists": True, "mtime": 100.0, "content": b"local"}
        remote = {"exists": True, "mtime": 200.0, "content": b"remote"}
        assert _should_push_settings(strategy, local, remote) is False


@pytest.mark.unit
class TestHasBidirectionalConflictSettings:
    def test_conflict_when_both_exist(self) -> None:
        strategy = SyncStrategy(
            direction=SyncDirection.BIDIRECTIONAL,
            conflict_strategy=ConflictStrategy.NEWEST_WINS,
        )
        local = {"exists": True, "mtime": 200.0, "content": b"local"}
        remote = {"exists": True, "mtime": 200.0, "content": b"remote"}
        assert _has_bidirectional_conflict(strategy, local, remote) is True

    def test_no_conflict_when_local_missing(self) -> None:
        strategy = SyncStrategy(
            direction=SyncDirection.BIDIRECTIONAL,
            conflict_strategy=ConflictStrategy.NEWEST_WINS,
        )
        local = {"exists": False, "mtime": 0.0, "content": b""}
        remote = {"exists": True, "mtime": 200.0, "content": b"remote"}
        assert _has_bidirectional_conflict(strategy, local, remote) is False

    def test_no_conflict_when_direction_unidirectional(self) -> None:
        strategy = SyncStrategy(
            direction=SyncDirection.PULL,
            conflict_strategy=ConflictStrategy.NEWEST_WINS,
        )
        local = {"exists": True, "mtime": 200.0, "content": b"local"}
        remote = {"exists": True, "mtime": 200.0, "content": b"remote"}
        assert _has_bidirectional_conflict(strategy, local, remote) is False
