"""Tests for origin allowlist logic.

Phase 1.1.c: ``FASTBLOCKS_WS_ALLOWED_ORIGINS`` is a comma-separated
default-deny allowlist. Any origin not in the list is rejected at the
WebSocket handshake stage.

The logic lives in a small pure helper so the server can wire it
through to the websockets library's ``process_request`` hook without
exposing a hard dependency on a particular server framework.
"""

from __future__ import annotations

import pytest

from fastblocks.websocket.server import check_origin, parse_allowed_origins


@pytest.mark.unit
class TestCheckOrigin:
    def test_exact_match_allowed(self) -> None:
        assert check_origin("https://app.example.com", ["https://app.example.com"])

    def test_exact_match_rejected(self) -> None:
        assert not check_origin(
            "https://attacker.example.com", ["https://app.example.com"]
        )

    def test_default_deny_when_allowlist_empty(self) -> None:
        """An empty allowlist denies every origin (default-deny)."""
        assert not check_origin("https://anything.example.com", [])

    def test_wildcard_allows_all(self) -> None:
        """``*`` in the allowlist allows every origin (operator opt-in)."""
        assert check_origin("https://attacker.example.com", ["*"])
        assert check_origin("http://localhost:3000", ["*"])

    def test_multiple_allowed_origins(self) -> None:
        allowlist = [
            "https://app.example.com",
            "https://admin.example.com",
        ]
        assert check_origin("https://app.example.com", allowlist)
        assert check_origin("https://admin.example.com", allowlist)
        assert not check_origin("https://other.example.com", allowlist)

    def test_scheme_mismatch_rejected(self) -> None:
        assert not check_origin(
            "http://app.example.com", ["https://app.example.com"]
        )

    def test_port_mismatch_rejected(self) -> None:
        assert not check_origin(
            "https://app.example.com:8443", ["https://app.example.com"]
        )

    @pytest.mark.parametrize(
        "origin",
        [
            None,
            "",
            "not-a-url",
            "javascript:alert(1)",
        ],
    )
    def test_garbage_origin_rejected(self, origin: str | None) -> None:
        assert not check_origin(origin, ["https://app.example.com", "*"])


@pytest.mark.unit
class TestParseAllowedOrigins:
    def test_empty_env_returns_empty_list(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("FASTBLOCKS_WS_ALLOWED_ORIGINS", raising=False)
        assert parse_allowed_origins() == []

    def test_single_origin(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("FASTBLOCKS_WS_ALLOWED_ORIGINS", "https://app.example.com")
        assert parse_allowed_origins() == ["https://app.example.com"]

    def test_comma_separated(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(
            "FASTBLOCKS_WS_ALLOWED_ORIGINS",
            "https://app.example.com, https://admin.example.com ,"
            "https://other.example.com",
        )
        assert parse_allowed_origins() == [
            "https://app.example.com",
            "https://admin.example.com",
            "https://other.example.com",
        ]

    def test_wildcard_passthrough(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("FASTBLOCKS_WS_ALLOWED_ORIGINS", "*")
        assert parse_allowed_origins() == ["*"]
