"""D1 coverage tests for fastblocks/htmx.py.

Targets HtmxDetails: header getters, JSON parsing for triggering-event,
and the HtmxRequest scope reader.
"""
# pyright: reportAttributeAccessIssue=false, reportFunctionMemberAccess=false
from __future__ import annotations

from typing import Any

import pytest

from fastblocks.htmx import HtmxDetails, _get_header


def _scope_with_headers(headers: list[tuple[bytes, bytes]]) -> dict[str, Any]:
    return {
        "type": "http",
        "method": "GET",
        "scheme": "https",
        "server": ("x", 443),
        "path": "/",
        "headers": headers,
    }


@pytest.mark.unit
class TestGetHeader:
    def test_present_header(self) -> None:
        scope = _scope_with_headers([(b"hx-request", b"true")])
        assert _get_header(scope, b"hx-request") == "true"

    def test_missing_header(self) -> None:
        scope = _scope_with_headers([])
        assert _get_header(scope, b"hx-request") is None


@pytest.mark.unit
class TestHtmxDetails:
    def test_bool_true_when_request_header_present(self) -> None:
        scope = _scope_with_headers([(b"hx-request", b"true")])
        d = HtmxDetails(scope)
        assert bool(d) is True

    def test_bool_false_when_no_request_header(self) -> None:
        d = HtmxDetails(_scope_with_headers([]))
        assert bool(d) is False

    def test_boosted(self) -> None:
        scope = _scope_with_headers([(b"hx-boosted", b"true")])
        assert HtmxDetails(scope).boosted is True

    def test_boosted_false_when_absent(self) -> None:
        assert HtmxDetails(_scope_with_headers([])).boosted is False

    def test_current_url(self) -> None:
        scope = _scope_with_headers([(b"hx-current-url", b"https://x.test/path")])
        assert HtmxDetails(scope).current_url == "https://x.test/path"

    def test_history_restore_request(self) -> None:
        scope = _scope_with_headers([(b"hx-history-restore-request", b"true")])
        assert HtmxDetails(scope).history_restore_request is True

    def test_prompt(self) -> None:
        scope = _scope_with_headers([(b"hx-prompt", b"my prompt")])
        assert HtmxDetails(scope).prompt == "my prompt"

    def test_target(self) -> None:
        scope = _scope_with_headers([(b"hx-target", b"#main")])
        assert HtmxDetails(scope).target == "#main"

    def test_trigger(self) -> None:
        scope = _scope_with_headers([(b"hx-trigger", b"event-name")])
        assert HtmxDetails(scope).trigger == "event-name"

    def test_trigger_name(self) -> None:
        scope = _scope_with_headers([(b"hx-trigger-name", b"my-event")])
        assert HtmxDetails(scope).trigger_name == "my-event"

    def test_triggering_event_parses_json(self) -> None:
        import json

        event = {"event": "click", "target": "#btn"}
        scope = _scope_with_headers(
            [(b"triggering-event", json.dumps(event).encode())]
        )
        result = HtmxDetails(scope).triggering_event
        assert result == event

    def test_triggering_event_invalid_json_returns_none(self) -> None:
        scope = _scope_with_headers([(b"triggering-event", b"not-json{")])
        assert HtmxDetails(scope).triggering_event is None

    def test_triggering_event_non_dict_returns_none(self) -> None:
        scope = _scope_with_headers([(b"triggering-event", b'"a-string"')])
        assert HtmxDetails(scope).triggering_event is None

    def test_triggering_event_missing_returns_none(self) -> None:
        assert HtmxDetails(_scope_with_headers([])).triggering_event is None

    def test_get_all_headers_shape(self) -> None:
        scope = _scope_with_headers(
            [
                (b"hx-request", b"true"),
                (b"hx-target", b"#main"),
                (b"hx-prompt", b"hi"),
            ]
        )
        all_headers = HtmxDetails(scope).get_all_headers()
        assert isinstance(all_headers, dict)
        assert all_headers["HX-Request"] == "true"
        assert all_headers["HX-Target"] == "#main"
        assert all_headers["HX-Prompt"] == "hi"

    def test_get_all_headers_missing_values(self) -> None:
        # The implementation filters out None values, so an empty scope
        # yields an empty dict.
        all_headers = HtmxDetails(_scope_with_headers([])).get_all_headers()
        assert all_headers == {}

    def test_get_all_headers_partial(self) -> None:
        # Mix of present and absent headers — absent keys are dropped.
        scope = _scope_with_headers([(b"hx-target", b"#main")])
        all_headers = HtmxDetails(scope).get_all_headers()
        assert all_headers.get("HX-Target") == "#main"
        assert "HX-Boosted" not in all_headers