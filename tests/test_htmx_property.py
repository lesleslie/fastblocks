"""Property-based tests for FastBlocks HTMX module using Hypothesis."""

import json
from typing import Any

import pytest
from hypothesis import assume, given, settings, strategies as st
from hypothesis.strategies import (
    dictionaries,
    just,
    lists,
    nothing,
    one_of,
    sampled_from,
    text,
)
from starlette.datastructures import Headers
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from fastblocks.htmx import (
    HtmxDetails,
    HtmxResponse,
    _get_header,
    htmx_push_url,
    htmx_redirect,
    htmx_refresh,
    htmx_retarget,
    htmx_trigger,
    is_htmx,
)


# Helper strategies
@st.composite
def htmx_scope_strategy(draw) -> dict[str, Any]:
    """Generate a valid HTMX scope."""
    # Generate safe text that can be encoded as latin-1
    safe_text = st.text(
        alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/:-_?=&",
        min_size=0,
        max_size=100
    )

    headers = draw(
        st.lists(
            st.tuples(
                st.sampled_from(
                    [
                        b"hx-request",
                        b"HX-Request",
                        b"hx-boosted",
                        b"HX-Boosted",
                        b"hx-current-url",
                        b"HX-Current-URL",
                        b"hx-history-restore-request",
                        b"HX-History-Restore-Request",
                        b"hx-prompt",
                        b"HX-Prompt",
                        b"hx-target",
                        b"HX-Target",
                        b"hx-trigger",
                        b"HX-Trigger",
                        b"hx-trigger-name",
                        b"HX-Trigger-Name",
                        b"triggering-event",
                        b"Triggering-Event",
                    ]
                ),
                safe_text.map(lambda x: x.encode("latin-1")),
            ),
            min_size=0,
            max_size=10,
        )
    )

    scope = {
        "type": "http",
        "method": draw(sampled_from(["GET", "POST", "PUT", "DELETE", "PATCH"])),
        "path": draw(text(min_size=1, max_size=50, alphabet="abcdefghijklmnopqrstuvwxyz/")),
        "headers": headers,
    }

    return scope


@st.composite
def htmx_trigger_strategy(draw) -> dict[str, Any]:
    """Generate valid HTMX trigger data."""
    event_name = draw(text(min_size=1, max_size=30, alphabet="abcdefghijklmnopqrstuvwxyz_"))
    event_data = draw(
        dictionaries(
            keys=text(min_size=1, max_size=20),
            values=one_of(text(), st.integers(), st.booleans(), st.none()),
            min_size=0,
            max_size=5,
        )
    )
    return {event_name: event_data}


@st.composite
def url_strategy(draw) -> str:
    """Generate valid URLs."""
    path = draw(text(min_size=1, max_size=50, alphabet="abcdefghijklmnopqrstuvwxyz/-"))
    return f"/{path}"


@pytest.mark.unit
@pytest.mark.property
class TestHtmxDetailsProperties:
    """Property-based tests for HtmxDetails."""

    @given(htmx_scope_strategy())
    @settings(max_examples=100)
    def test_htmx_details_alters_scope(self, scope: dict[str, Any]) -> None:
        """Test that HtmxDetails can be created from any valid scope."""
        details = HtmxDetails(scope)
        assert details._scope == scope

    @given(
        htmx_scope_strategy(),
        st.sampled_from([b"hx-request", b"HX-Request"]),
    )
    @settings(max_examples=50)
    def test_htmx_request_detection(
        self, scope: dict[str, Any], header_key: bytes
    ) -> None:
        """Test that HtmxRequest detection works correctly."""
        details = HtmxDetails(scope)

        # If header is set to "true" (any casing), is_htmx should be True
        if any(h[0].lower() == b"hx-request" and h[1].lower() == b"true" for h in scope["headers"]):
            assert details.__bool__() is True
        else:
            # If no "true" header, should be False
            assert details.__bool__() is False

    @given(htmx_scope_strategy())
    @settings(max_examples=50)
    def test_htmx_properties_return_none_or_string(
        self, scope: dict[str, Any]
    ) -> None:
        """Test that all HtmxDetails properties return None or str."""
        details = HtmxDetails(scope)

        properties = [
            "boosted",
            "current_url",
            "history_restore_request",
            "prompt",
            "target",
            "trigger",
            "trigger_name",
        ]

        for prop in properties:
            value = getattr(details, prop)
            if value is not None:
                assert isinstance(value, (str, bool))
                # boosted and history_restore_request return bool
                if prop in ("boosted", "history_restore_request"):
                    assert isinstance(value, bool)
                else:
                    assert isinstance(value, str)

    @given(htmx_scope_strategy())
    @settings(max_examples=50)
    def test_get_all_headers_returns_dict(self, scope: dict[str, Any]) -> None:
        """Test that get_all_headers returns a dict with string keys."""
        details = HtmxDetails(scope)
        headers = details.get_all_headers()

        assert isinstance(headers, dict)
        for key, value in headers.items():
            assert isinstance(key, str)
            if value is not None:
                assert isinstance(value, str)

    @given(htmx_scope_strategy())
    @settings(max_examples=30)
    def test_triggering_event_parsing(self, scope: dict[str, Any]) -> None:
        """Test that triggering_event property handles JSON correctly."""
        details = HtmxDetails(scope)
        event = details.triggering_event

        # If event is not None, it should be a dict or None
        if event is not None:
            assert isinstance(event, dict)


@pytest.mark.unit
@pytest.mark.property
class TestHtmxResponseProperties:
    """Property-based tests for HtmxResponse."""

    @given(
        st.text(min_size=0, max_size=100),
        st.integers(min_value=100, max_value=599),
        st.dictionaries(
            keys=text(min_size=1, max_size=20, alphabet=st.characters(min_codepoint=0x21, max_codepoint=0x7E)),
            values=text(min_size=0, max_size=100, alphabet=st.characters(max_codepoint=0xFF)),
            min_size=0,
            max_size=5,
        ),
    )
    @settings(max_examples=50)
    def test_htmx_response_basic_creation(
        self, content: str, status_code: int, headers: dict[str, str]
    ) -> None:
        """Test that HtmxResponse can be created with various inputs."""
        response = HtmxResponse(content=content, status_code=status_code, headers=headers)

        assert response.body == content.encode()
        assert response.status_code == status_code

    @given(
        st.text(min_size=1, max_size=50, alphabet="abcdefghijklmnopqrstuvwxyz_"),
        st.text(min_size=0, max_size=100),
        st.integers(min_value=200, max_value=299),
    )
    @settings(max_examples=30)
    def test_htmx_response_with_trigger(
        self, trigger: str, content: str, status_code: int
    ) -> None:
        """Test HtmxResponse with trigger parameter."""
        response = HtmxResponse(
            content=content, status_code=status_code, trigger=trigger
        )

        assert "HX-Trigger" in response.headers
        assert response.headers["HX-Trigger"] == trigger

    @given(
        url_strategy(),
        st.text(min_size=0, max_size=100),
    )
    @settings(max_examples=30)
    def test_htmx_response_with_redirect(self, url: str, content: str) -> None:
        """Test HtmxResponse with redirect parameter."""
        response = HtmxResponse(content=content, redirect=url)

        assert "HX-Redirect" in response.headers
        assert response.headers["HX-Redirect"] == url

    @given(
        url_strategy(),
        st.text(min_size=0, max_size=100),
    )
    @settings(max_examples=30)
    def test_htmx_response_with_push_url(self, url: str, content: str) -> None:
        """Test HtmxResponse with push_url parameter."""
        response = HtmxResponse(content=content, push_url=url)

        assert "HX-Push-Url" in response.headers
        assert response.headers["HX-Push-Url"] == url

    @given(
        st.text(min_size=1, max_size=50, alphabet=st.characters(max_codepoint=0xFF)),
        st.text(min_size=0, max_size=100),
    )
    @settings(max_examples=30)
    def test_htmx_response_with_retarget(self, target: str, content: str) -> None:
        """Test HtmxResponse with retarget parameter."""
        response = HtmxResponse(content=content, retarget=target)

        assert "HX-Retarget" in response.headers
        assert response.headers["HX-Retarget"] == target

    @given(
        st.dictionaries(
            keys=text(min_size=1, max_size=20),
            values=one_of(text(), st.integers(), st.booleans()),
            min_size=1,
            max_size=5,
        ),
        st.text(min_size=0, max_size=100),
    )
    @settings(max_examples=30)
    def test_htmx_response_with_location_dict(
        self, location: dict[str, Any], content: str
    ) -> None:
        """Test HtmxResponse with location as dict."""
        response = HtmxResponse(content=content, location=location)

        assert "HX-Location" in response.headers
        # Should be JSON string
        assert json.loads(response.headers["HX-Location"]) == location


@pytest.mark.unit
@pytest.mark.property
class TestHtmxHelperFunctions:
    """Property-based tests for HTMX helper functions."""

    @given(
        one_of(
            text(min_size=1, max_size=50, alphabet="abcdefghijklmnopqrstuvwxyz_"),
            htmx_trigger_strategy(),
        ),
        st.text(min_size=0, max_size=100),
        st.integers(min_value=200, max_value=299),
    )
    @settings(max_examples=50)
    def test_htmx_trigger_always_returns_response(
        self, trigger: Any, content: str, status_code: int
    ) -> None:
        """Test that htmx_trigger always returns HtmxResponse."""
        response = htmx_trigger(trigger, content=content, status_code=status_code)

        assert isinstance(response, HtmxResponse)
        assert response.body == content.encode()
        assert response.status_code == status_code

    @given(url_strategy())
    @settings(max_examples=30)
    def test_htmx_redirect_always_returns_response(self, url: str) -> None:
        """Test that htmx_redirect always returns HtmxResponse."""
        response = htmx_redirect(url)

        assert isinstance(response, HtmxResponse)
        assert "HX-Redirect" in response.headers
        assert response.headers["HX-Redirect"] == url

    @given(st.text(min_size=0, max_size=100))
    @settings(max_examples=20)
    def test_htmx_refresh_always_returns_response(self, content: str) -> None:
        """Test that htmx_refresh always returns HtmxResponse."""
        response = htmx_refresh(content=content)

        assert isinstance(response, HtmxResponse)
        assert "HX-Refresh" in response.headers
        assert response.headers["HX-Refresh"] == "true"

    @given(
        url_strategy(),
        st.text(min_size=0, max_size=100),
    )
    @settings(max_examples=30)
    def test_htmx_push_url_always_returns_response(
        self, url: str, content: str
    ) -> None:
        """Test that htmx_push_url always returns HtmxResponse."""
        response = htmx_push_url(url, content=content)

        assert isinstance(response, HtmxResponse)
        assert response.body == content.encode()
        assert "HX-Push-Url" in response.headers

    @given(
        st.text(min_size=1, max_size=50, alphabet=st.characters(max_codepoint=0xFF)),
        st.text(min_size=0, max_size=100),
    )
    @settings(max_examples=30)
    def test_htmx_retarget_always_returns_response(
        self, target: str, content: str
    ) -> None:
        """Test that htmx_retarget always returns HtmxResponse."""
        response = htmx_retarget(target, content=content)

        assert isinstance(response, HtmxResponse)
        assert response.body == content.encode()
        assert "HX-Retarget" in response.headers


@pytest.mark.unit
@pytest.mark.property
class TestIsHtmx:
    """Property-based tests for is_htmx function."""

    @given(htmx_scope_strategy())
    @settings(max_examples=50)
    def test_is_htmx_with_scope(self, scope: dict[str, Any]) -> None:
        """Test is_htmx with scope dict."""
        result = is_htmx(scope)

        # First occurrence of hx-request header wins (HTTP single-value header)
        first_value = next(
            (h[1] for h in scope.get("headers", []) if h[0].lower() == b"hx-request"),
            None,
        )
        has_htmx_header = first_value is not None and first_value.lower() == b"true"
        assert result == has_htmx_header

    @given(
        st.dictionaries(
            keys=text(min_size=1, max_size=20),
            values=one_of(text(), st.none()),
            min_size=0,
            max_size=10,
        )
    )
    @settings(max_examples=30)
    def test_is_htmx_with_dict_headers(self, headers: dict[str, Any]) -> None:
        """Test is_htmx with dict that has headers attribute."""
        mock_obj = type("MockObj", (), {"headers": headers})()
        result = is_htmx(mock_obj)

        expected = headers.get("HX-Request") == "true"
        assert result == expected


@pytest.mark.unit
@pytest.mark.property
class TestGetHeader:
    """Property-based tests for _get_header function."""

    @given(
        st.lists(
            st.tuples(
                st.text(min_size=1, max_size=20).map(lambda x: x.encode()),
                st.text(min_size=0, max_size=100, alphabet=st.characters(max_codepoint=0xFF)).map(lambda x: x.encode("latin-1")),
            ),
            min_size=0,
            max_size=20,
        ),
        st.text(min_size=1, max_size=20).map(lambda x: x.encode()),
    )
    @settings(max_examples=50)
    def test_get_header_handles_various_inputs(
        self, headers: list[tuple[bytes, bytes]], key: bytes
    ) -> None:
        """Test _get_header with various inputs."""
        scope = {"headers": headers}
        result = _get_header(scope, key)

        # Result should be None or str
        if result is not None:
            assert isinstance(result, str)

    @given(
        st.lists(
            st.tuples(
                st.just(b"test-header"),
                st.text(min_size=0, max_size=50, alphabet=st.characters(max_codepoint=0xFF)).map(lambda x: x.encode("latin-1")),
            ),
            min_size=0,
            max_size=10,
        )
    )
    @settings(max_examples=30)
    def test_get_header_case_insensitive(self, headers: list[tuple[bytes, bytes]]) -> None:
        """Test that _get_header is case-insensitive."""
        scope = {"headers": headers}

        # Try different case variations
        result1 = _get_header(scope, b"test-header")
        result2 = _get_header(scope, b"TEST-HEADER")
        result3 = _get_header(scope, b"Test-Header")

        # All should return the same value
        assert result1 == result2 == result3


@pytest.mark.unit
@pytest.mark.property
class TestHtmxResponseHeaders:
    """Property-based tests for HtmxResponse header setting."""

    @given(
        st.text(min_size=0, max_size=100, alphabet=""),
        st.integers(min_value=200, max_value=599),
        st.none() | st.text(min_size=0, max_size=50, alphabet=st.characters(max_codepoint=0xFF)),
        st.none() | st.text(min_size=0, max_size=50, alphabet=st.characters(max_codepoint=0xFF)),
        st.none() | st.text(min_size=0, max_size=50, alphabet=st.characters(max_codepoint=0xFF)),
    )
    @settings(max_examples=30)
    def test_multiple_trigger_headers(
        self,
        content: str,
        status: int,
        trigger: str | None,
        trigger_after_settle: str | None,
        trigger_after_swap: str | None,
    ) -> None:
        """Test HtmxResponse with multiple trigger headers."""
        response = HtmxResponse(
            content=content,
            status_code=status,
            trigger=trigger,
            trigger_after_settle=trigger_after_settle,
            trigger_after_swap=trigger_after_swap,
        )

        # Check headers are set correctly
        if trigger:
            assert response.headers.get("HX-Trigger") == trigger
        if trigger_after_settle:
            assert response.headers.get("HX-Trigger-After-Settle") == trigger_after_settle
        if trigger_after_swap:
            assert response.headers.get("HX-Trigger-After-Swap") == trigger_after_swap

    @given(
        st.none() | st.just(True) | st.just(False),
        st.none() | st.text(min_size=1, max_size=100, alphabet=st.characters(max_codepoint=0xFF)),
        st.none() | st.text(min_size=1, max_size=100, alphabet=st.characters(max_codepoint=0xFF)),
    )
    @settings(max_examples=30)
    def test_url_and_refresh_headers(
        self,
        refresh: bool | None,
        push_url: str | bool | None,
        replace_url: str | bool | None,
    ) -> None:
        """Test HtmxResponse with URL and refresh headers."""
        response = HtmxResponse(
            refresh=refresh if refresh is None else bool(refresh),
            push_url=push_url,
            replace_url=replace_url,
        )

        # Check refresh header
        if refresh is True:
            assert response.headers.get("HX-Refresh") == "true"

        # Check push_url header
        if push_url is not None:
            assert "HX-Push-Url" in response.headers

        # Check replace_url header
        if replace_url is not None:
            assert "HX-Replace-Url" in response.headers


@pytest.mark.unit
@pytest.mark.property
class TestHtmxEdgeCases:
    """Property-based tests for HTMX edge cases."""

    @given(
        st.text(min_size=0, max_size=1000, alphabet="\\x00\\x01\\x02\\x03\\x04\\x05\\x06\\x07\\x08\\x0b\\x0c\\x0e\\x0f\\x10\\x11\\x12\\x13\\x14\\x15\\x16\\x17\\x18\\x19\\x1a\\x1b\\x1c\\x1d\\x1e\\x1f\\x7f\\x80\\x81\\x82\\x83\\x84\\x85\\x86\\x87\\x88\\x89\\x8a\\x8b\\x8c\\x8d\\x8e\\x8f\\x90\\x91\\x92\\x93\\x94\\x95\\x96\\x97\\x98\\x99\\x9a\\x9b\\x9c\\x9d\\x9e\\x9f\\xa0\\xa1\\xa2\\xa3\\xa4\\xa5\\xa6\\xa7\\xa8\\xa9\\xaa\\xab\\xac\\xad\\xae\\xaf\\xb0\\xb1\\xb2\\xb3\\xb4\\xb5\\xb6\\xb7\\xb8\\xb9\\xba\\xbb\\xbc\\xbd\\xbe\\xbf\\xc0\\xc1\\xc2\\xc3\\xc4\\xc5\\xc6\\xc7\\xc8\\xc9\\xca\\xcb\\xcc\\xcd\\xce\\xcf\\xd0\\xd1\\xd2\\xd3\\xd4\\xd5\\xd6\\xd7\\xd8\\xd9\\xda\\xdb\\xdc\\xdd\\xde\\xdf\\xe0\\xe1\\xe2\\xe3\\xe4\\xe5\\xe6\\xe7\\xe8\\xe9\\xea\\xeb\\xec\\xed\\xee\\xef\\xf0\\xf1\\xf2\\xf3\\xf4\\xf5\\xf6\\xf7\\xf8\\xf9\\xfa\\xfb\\xfc\\xfd\\xfe\\xff")
    )
    @settings(max_examples=20)
    def test_htmx_response_with_special_chars(self, content: str) -> None:
        """Test HtmxResponse with special characters."""
        # This should not raise an exception
        response = HtmxResponse(content=content)
        assert isinstance(response, HtmxResponse)

    @given(
        st.dictionaries(
            keys=text(min_size=1, max_size=20).map(lambda x: x.encode()),
            values=text(min_size=0, max_size=100).map(lambda x: x.encode("latin-1", errors="replace")),
            min_size=0,
            max_size=10,
        )
    )
    @settings(max_examples=30)
    def test_htmx_details_with_various_headers(self, headers: dict[bytes, bytes]) -> None:
        """Test HtmxDetails with various header encodings."""
        headers_list = list(headers.items())
        scope = {"type": "http", "headers": headers_list}

        # Should not raise an exception
        details = HtmxDetails(scope)
        assert details is not None

    @given(
        st.lists(
            st.tuples(
                st.text(min_size=1, max_size=30).map(lambda x: x.encode()),
                st.text(min_size=0, max_size=100).map(lambda x: x.encode("latin-1", errors="replace")),
            ),
            min_size=0,
            max_size=50,
        )
    )
    @settings(max_examples=20)
    def test_htmx_details_with_many_headers(self, headers: list[tuple[bytes, bytes]]) -> None:
        """Test HtmxDetails with many headers."""
        scope = {"type": "http", "headers": headers}

        # Should handle many headers gracefully
        details = HtmxDetails(scope)
        result_headers = details.get_all_headers()
        assert isinstance(result_headers, dict)
