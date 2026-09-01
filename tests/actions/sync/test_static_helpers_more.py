"""Additional helper tests for fastblocks/actions/sync/static.py.

Targets 219 missing statements before this file. Tests cover
``_detect_mime_type``, ``_is_cacheable_file``, and the
``_should_pull_static`` / ``_should_push_static`` branches.
"""

from __future__ import annotations

import pytest
from anyio import Path as AsyncPath
from fastblocks.actions.sync.static import (
    _detect_mime_type,
    _has_bidirectional_conflict,
    _is_cacheable_file,
    _should_pull_static,
    _should_push_static,
)
from fastblocks.actions.sync.strategies import (
    ConflictStrategy,
    SyncDirection,
    SyncStrategy,
)


@pytest.mark.unit
class TestDetectMimeType:
    def test_detects_html_mime(self) -> None:
        result = _detect_mime_type(AsyncPath("index.html"))
        assert "html" in result

    def test_detects_css_mime(self) -> None:
        result = _detect_mime_type(AsyncPath("styles.css"))
        assert "css" in result

    def test_detects_javascript_mime(self) -> None:
        result = _detect_mime_type(AsyncPath("app.js"))
        assert "javascript" in result or "ecmascript" in result

    def test_unknown_extension_returns_octet_stream(self) -> None:
        result = _detect_mime_type(AsyncPath("weird.xyz123"))
        # Unknown extension → fallback.
        assert result == "application/octet-stream"


@pytest.mark.unit
class TestIsCacheableFile:
    def test_css_is_cacheable(self) -> None:
        from unittest.mock import MagicMock

        path = MagicMock()
        path.suffix = ".css"
        assert _is_cacheable_file(path) is True

    def test_js_is_cacheable(self) -> None:
        from unittest.mock import MagicMock

        path = MagicMock()
        path.suffix = ".js"
        assert _is_cacheable_file(path) is True

    def test_html_is_not_cacheable(self) -> None:
        from unittest.mock import MagicMock

        path = MagicMock()
        path.suffix = ".html"
        # .html is not in CACHEABLE_EXTENSIONS (only .css/.js/.md/.txt).
        assert _is_cacheable_file(path) is False

    def test_tmp_file_not_cacheable(self) -> None:
        from unittest.mock import MagicMock

        path = MagicMock()
        path.suffix = ".tmp"
        assert _is_cacheable_file(path) is False

    def test_log_file_not_cacheable(self) -> None:
        from unittest.mock import MagicMock

        path = MagicMock()
        path.suffix = ".log"
        assert _is_cacheable_file(path) is False


@pytest.mark.unit
class TestShouldPullPushStatic:
    def test_should_pull_when_remote_newer(self) -> None:
        strategy = SyncStrategy(
            direction=SyncDirection.BIDIRECTIONAL,
            conflict_strategy=ConflictStrategy.NEWEST_WINS,
        )
        local = {"exists": True, "mtime": 100.0, "content": b"local"}
        remote = {"exists": True, "mtime": 200.0, "content": b"remote"}
        assert _should_pull_static(strategy, local, remote) is True

    def test_should_not_pull_when_local_newer(self) -> None:
        strategy = SyncStrategy(
            direction=SyncDirection.BIDIRECTIONAL,
            conflict_strategy=ConflictStrategy.NEWEST_WINS,
        )
        local = {"exists": True, "mtime": 200.0, "content": b"local"}
        remote = {"exists": True, "mtime": 100.0, "content": b"remote"}
        assert _should_pull_static(strategy, local, remote) is False

    def test_should_push_when_local_newer(self) -> None:
        strategy = SyncStrategy(
            direction=SyncDirection.BIDIRECTIONAL,
            conflict_strategy=ConflictStrategy.NEWEST_WINS,
        )
        local = {"exists": True, "mtime": 200.0, "content": b"local"}
        remote = {"exists": True, "mtime": 100.0, "content": b"remote"}
        assert _should_push_static(strategy, local, remote) is True

    def test_should_not_push_when_local_missing(self) -> None:
        strategy = SyncStrategy(
            direction=SyncDirection.BIDIRECTIONAL,
            conflict_strategy=ConflictStrategy.NEWEST_WINS,
        )
        local = {"exists": False, "mtime": 0.0, "content": b""}
        remote = {"exists": True, "mtime": 200.0, "content": b"remote"}
        assert _should_push_static(strategy, local, remote) is False


@pytest.mark.unit
class TestHasBidirectionalConflictStatic:
    def test_conflict_when_bidirectional_and_both_exist(self) -> None:
        strategy = SyncStrategy(
            direction=SyncDirection.BIDIRECTIONAL,
            conflict_strategy=ConflictStrategy.NEWEST_WINS,
        )
        local = {"exists": True, "mtime": 200.0, "content": b"local"}
        remote = {"exists": True, "mtime": 200.0, "content": b"remote"}
        assert _has_bidirectional_conflict(strategy, local, remote) is True

    def test_no_conflict_when_unidirectional(self) -> None:
        strategy = SyncStrategy(
            direction=SyncDirection.PUSH,
            conflict_strategy=ConflictStrategy.NEWEST_WINS,
        )
        local = {"exists": True, "mtime": 200.0, "content": b"local"}
        remote = {"exists": True, "mtime": 200.0, "content": b"remote"}
        assert _has_bidirectional_conflict(strategy, local, remote) is False
