"""Tests for the FastBlocks HTMX module."""

import asyncio
import json
import warnings
from unittest.mock import AsyncMock, patch

import pytest
from starlette.responses import HTMLResponse

# Mock the debug module to avoid AttributeError
with patch("fastblocks.htmx.debug") as mock_debug:
    mock_debug.enabled = False
    from fastblocks.htmx import (
        HtmxDetails,
        HtmxResponse,
        _get_header,
        _run_async_safely,
        htmx_push_url,
        htmx_redirect,
        htmx_refresh,
        htmx_retarget,
        htmx_trigger,
        is_htmx,
    )


@pytest.mark.unit
class TestHtmxDetails:
    """Test HtmxDetails class."""

    def test_htmx_details_bool_true(self) -> None:
        """Test HtmxDetails.__bool__ returns True when HX-Request is 'true'."""
        scope = {
            "headers": [
                (b"hx-request", b"true"),
            ],
            "path": "/test",
        }
        # Mock debug.enabled to avoid AttributeError
        with patch("fastblocks.htmx.debug") as mock_debug:
            mock_debug.enabled = False
            details = HtmxDetails(scope)
            assert bool(details) is True

    def test_htmx_details_bool_false(self) -> None:
        """Test HtmxDetails.__bool__ returns False when HX-Request is not 'true'."""
        scope = {
            "headers": [
                (b"hx-request", b"false"),
            ],
            "path": "/test",
        }
        # Mock debug.enabled to avoid AttributeError
        with patch("fastblocks.htmx.debug") as mock_debug:
            mock_debug.enabled = False
            details = HtmxDetails(scope)
            assert bool(details) is False

    def test_htmx_details_bool_missing_header(self) -> None:
        """Test HtmxDetails.__bool__ returns False when HX-Request header is missing."""
        scope = {
            "headers": [
                (b"content-type", b"text/html"),
            ],
            "path": "/test",
        }
        # Mock debug.enabled to avoid AttributeError
        with patch("fastblocks.htmx.debug") as mock_debug:
            mock_debug.enabled = False
            details = HtmxDetails(scope)
            assert bool(details) is False

    def test_htmx_details_boosted_true(self) -> None:
        """Test HtmxDetails.boosted property returns True."""
        scope = {
            "headers": [
                (b"hx-request", b"true"),
                (b"hx-boosted", b"true"),
            ],
            "path": "/test",
        }
        # Mock debug.enabled to avoid AttributeError
        with patch("fastblocks.htmx.debug") as mock_debug:
            mock_debug.enabled = False
            details = HtmxDetails(scope)
            assert details.boosted is True

    def test_htmx_details_boosted_false(self) -> None:
        """Test HtmxDetails.boosted property returns False."""
        scope = {
            "headers": [
                (b"hx-request", b"true"),
                (b"hx-boosted", b"false"),
            ],
            "path": "/test",
        }
        # Mock debug.enabled to avoid AttributeError
        with patch("fastblocks.htmx.debug") as mock_debug:
            mock_debug.enabled = False
            details = HtmxDetails(scope)
            assert details.boosted is False

    def test_htmx_details_boosted_missing(self) -> None:
        """Test HtmxDetails.boosted property returns False when header is missing."""
        scope = {
            "headers": [
                (b"hx-request", b"true"),
            ],
            "path": "/test",
        }
        # Mock debug.enabled to avoid AttributeError
        with patch("fastblocks.htmx.debug") as mock_debug:
            mock_debug.enabled = False
            details = HtmxDetails(scope)
            assert details.boosted is False

    def test_htmx_details_current_url(self) -> None:
        """Test HtmxDetails.current_url property."""
        scope = {
            "headers": [
                (b"hx-request", b"true"),
                (b"hx-current-url", b"https://example.com/page"),
            ],
            "path": "/test",
        }
        # Mock debug.enabled to avoid AttributeError
        with patch("fastblocks.htmx.debug") as mock_debug:
            mock_debug.enabled = False
            details = HtmxDetails(scope)
            assert details.current_url == "https://example.com/page"

    def test_htmx_details_current_url_missing(self) -> None:
        """Test HtmxDetails.current_url property when header is missing."""
        scope = {
            "headers": [
                (b"hx-request", b"true"),
            ],
            "path": "/test",
        }
        # Mock debug.enabled to avoid AttributeError
        with patch("fastblocks.htmx.debug") as mock_debug:
            mock_debug.enabled = False
            details = HtmxDetails(scope)
            assert details.current_url is None

    def test_htmx_details_history_restore_request_true(self) -> None:
        """Test HtmxDetails.history_restore_request property returns True."""
        scope = {
            "headers": [
                (b"hx-request", b"true"),
                (b"hx-history-restore-request", b"true"),
            ],
            "path": "/test",
        }
        # Mock debug.enabled to avoid AttributeError
        with patch("fastblocks.htmx.debug") as mock_debug:
            mock_debug.enabled = False
            details = HtmxDetails(scope)
            assert details.history_restore_request is True

    def test_htmx_details_history_restore_request_false(self) -> None:
        """Test HtmxDetails.history_restore_request property returns False."""
        scope = {
            "headers": [
                (b"hx-request", b"true"),
                (b"hx-history-restore-request", b"false"),
            ],
            "path": "/test",
        }
        # Mock debug.enabled to avoid AttributeError
        with patch("fastblocks.htmx.debug") as mock_debug:
            mock_debug.enabled = False
            details = HtmxDetails(scope)
            assert details.history_restore_request is False

    def test_htmx_details_prompt(self) -> None:
        """Test HtmxDetails.prompt property."""
        scope = {
            "headers": [
                (b"hx-request", b"true"),
                (b"hx-prompt", b"Are you sure?"),
            ],
            "path": "/test",
        }
        # Mock debug.enabled to avoid AttributeError
        with patch("fastblocks.htmx.debug") as mock_debug:
            mock_debug.enabled = False
            details = HtmxDetails(scope)
            assert details.prompt == "Are you sure?"

    def test_htmx_details_target(self) -> None:
        """Test HtmxDetails.target property."""
        scope = {
            "headers": [
                (b"hx-request", b"true"),
                (b"hx-target", b"#content"),
            ],
            "path": "/test",
        }
        # Mock debug.enabled to avoid AttributeError
        with patch("fastblocks.htmx.debug") as mock_debug:
            mock_debug.enabled = False
            details = HtmxDetails(scope)
            assert details.target == "#content"

    def test_htmx_details_trigger(self) -> None:
        """Test HtmxDetails.trigger property."""
        scope = {
            "headers": [
                (b"hx-request", b"true"),
                (b"hx-trigger", b"submit-button"),
            ],
            "path": "/test",
        }
        # Mock debug.enabled to avoid AttributeError
        with patch("fastblocks.htmx.debug") as mock_debug:
            mock_debug.enabled = False
            details = HtmxDetails(scope)
            assert details.trigger == "submit-button"

    def test_htmx_details_trigger_name(self) -> None:
        """Test HtmxDetails.trigger_name property."""
        scope = {
            "headers": [
                (b"hx-request", b"true"),
                (b"hx-trigger-name", b"action"),
            ],
            "path": "/test",
        }
        # Mock debug.enabled to avoid AttributeError
        with patch("fastblocks.htmx.debug") as mock_debug:
            mock_debug.enabled = False
            details = HtmxDetails(scope)
            assert details.trigger_name == "action"

    def test_htmx_details_triggering_event_valid_json(self) -> None:
        """Test HtmxDetails.triggering_event property with valid JSON."""
        event_data = {"type": "click", "target": "button"}
        scope = {
            "headers": [
                (b"hx-request", b"true"),
                (b"triggering-event", json.dumps(event_data).encode()),
            ],
            "path": "/test",
        }
        # Mock debug.enabled to avoid AttributeError
        with patch("fastblocks.htmx.debug") as mock_debug:
            mock_debug.enabled = False
            details = HtmxDetails(scope)
            assert details.triggering_event == event_data

    def test_htmx_details_triggering_event_invalid_json(self) -> None:
        """Test HtmxDetails.triggering_event property with invalid JSON."""
        scope = {
            "headers": [
                (b"hx-request", b"true"),
                (b"triggering-event", b"invalid json"),
            ],
            "path": "/test",
        }
        # Mock debug.enabled to avoid AttributeError
        with patch("fastblocks.htmx.debug") as mock_debug:
            mock_debug.enabled = False
            details = HtmxDetails(scope)
            assert details.triggering_event is None

    def test_htmx_details_triggering_event_missing(self) -> None:
        """Test HtmxDetails.triggering_event property when header is missing."""
        scope = {
            "headers": [
                (b"hx-request", b"true"),
            ],
            "path": "/test",
        }
        # Mock debug.enabled to avoid AttributeError
        with patch("fastblocks.htmx.debug") as mock_debug:
            mock_debug.enabled = False
            details = HtmxDetails(scope)
            assert details.triggering_event is None

    def test_htmx_details_get_all_headers(self) -> None:
        """Test HtmxDetails.get_all_headers method."""
        scope = {
            "headers": [
                (b"hx-request", b"true"),
                (b"hx-boosted", b"true"),
                (b"hx-current-url", b"https://example.com/page"),
                (b"hx-target", b"#content"),
            ],
            "path": "/test",
        }
        # Mock debug.enabled to avoid AttributeError
        with patch("fastblocks.htmx.debug") as mock_debug:
            mock_debug.enabled = False
            details = HtmxDetails(scope)
            headers = details.get_all_headers()
            assert headers == {
                "HX-Request": "true",
                "HX-Boosted": "true",
                "HX-Current-URL": "https://example.com/page",
                "HX-Target": "#content",
            }

    def test_get_header_with_uri_autoencoded(self) -> None:
        """Test _get_header with URI autoencoded header."""
        scope = {
            "headers": [
                (b"hx-current-url", b"https%3A%2F%2Fexample.com%2Fpage"),
                (b"hx-current-url-uri-autoencoded", b"true"),
            ]
        }
        # Mock debug.enabled to avoid AttributeError
        with patch("fastblocks.htmx.debug") as mock_debug:
            mock_debug.enabled = False
            value = _get_header(scope, b"hx-current-url")
            assert value == "https://example.com/page"

    def test_get_header_unicode_decode_error(self) -> None:
        """Test _get_header handles UnicodeDecodeError."""
        scope = {
            "headers": [
                (b"hx-current-url", b"\xff\xfe"),  # Invalid UTF-8
            ]
        }
        # Mock debug.enabled to avoid AttributeError
        with patch("fastblocks.htmx.debug") as mock_debug:
            mock_debug.enabled = False
            value = _get_header(scope, b"hx-current-url")
            # With the current implementation, invalid UTF-8 bytes are decoded as latin-1
            # and returned as-is when unquote fails
            assert value == "ÿþ"

    def test_get_header_key_error(self) -> None:
        """Test _get_header handles KeyError."""
        scope = {}  # Missing 'headers' key
        # Mock debug.enabled to avoid AttributeError
        with patch("fastblocks.htmx.debug") as mock_debug:
            mock_debug.enabled = False
            value = _get_header(scope, b"hx-current-url")
            assert value is None


@pytest.mark.unit
class TestHtmxResponse:
    """Test HtmxResponse class."""

    def test_htmx_response_basic(self) -> None:
        """Test basic HtmxResponse creation."""
        response = HtmxResponse(content="<div>Hello</div>", status_code=200)
        assert isinstance(response, HTMLResponse)
        assert response.body == b"<div>Hello</div>"
        assert response.status_code == 200

    def test_htmx_response_with_trigger(self) -> None:
        """Test HtmxResponse with trigger header."""
        response = HtmxResponse(content="", trigger="showMessage")
        assert response.headers["HX-Trigger"] == "showMessage"

    def test_htmx_response_with_trigger_after_settle(self) -> None:
        """Test HtmxResponse with trigger-after-settle header."""
        response = HtmxResponse(content="", trigger_after_settle="showMessage")
        assert response.headers["HX-Trigger-After-Settle"] == "showMessage"

    def test_htmx_response_with_trigger_after_swap(self) -> None:
        """Test HtmxResponse with trigger-after-swap header."""
        response = HtmxResponse(content="", trigger_after_swap="showMessage")
        assert response.headers["HX-Trigger-After-Swap"] == "showMessage"

    def test_htmx_response_with_retarget(self) -> None:
        """Test HtmxResponse with retarget header."""
        response = HtmxResponse(content="", retarget="#new-target")
        assert response.headers["HX-Retarget"] == "#new-target"

    def test_htmx_response_with_reselect(self) -> None:
        """Test HtmxResponse with reselect header."""
        response = HtmxResponse(content="", reselect=".new-content")
        assert response.headers["HX-Reselect"] == ".new-content"

    def test_htmx_response_with_reswap(self) -> None:
        """Test HtmxResponse with reswap header."""
        response = HtmxResponse(content="", reswap="outerHTML")
        assert response.headers["HX-Reswap"] == "outerHTML"

    def test_htmx_response_with_push_url(self) -> None:
        """Test HtmxResponse with push-url header."""
        response = HtmxResponse(content="", push_url="/new-page")
        # The actual implementation doesn't add the domain, it just converts to string
        assert response.headers["HX-Push-Url"] == "/new-page"

    def test_htmx_response_with_push_url_false(self) -> None:
        """Test HtmxResponse with push-url header set to False."""
        response = HtmxResponse(content="", push_url=False)
        assert response.headers["HX-Push-Url"] == "false"

    def test_htmx_response_with_replace_url(self) -> None:
        """Test HtmxResponse with replace-url header."""
        response = HtmxResponse(content="", replace_url="/new-page")
        # The actual implementation doesn't add the domain, it just converts to string
        assert response.headers["HX-Replace-Url"] == "/new-page"

    def test_htmx_response_with_refresh(self) -> None:
        """Test HtmxResponse with refresh header."""
        response = HtmxResponse(content="", refresh=True)
        assert response.headers["HX-Refresh"] == "true"

    def test_htmx_response_with_redirect(self) -> None:
        """Test HtmxResponse with redirect header."""
        response = HtmxResponse(content="", redirect="/login")
        assert response.headers["HX-Redirect"] == "/login"

    def test_htmx_response_with_location_dict(self) -> None:
        """Test HtmxResponse with location header as dict."""
        location = {"path": "/new-page", "target": "#content"}
        response = HtmxResponse(content="", location=location)
        assert response.headers["HX-Location"] == json.dumps(location)

    def test_htmx_response_with_location_string(self) -> None:
        """Test HtmxResponse with location header as string."""
        response = HtmxResponse(content="", location="/new-page")
        assert response.headers["HX-Location"] == "/new-page"


@pytest.mark.unit
class TestHtmxHelpers:
    """Test HTMX helper functions."""

    def test_htmx_trigger_string(self) -> None:
        """Test htmx_trigger with string argument."""
        response = htmx_trigger("showMessage")
        assert isinstance(response, HtmxResponse)
        assert response.headers["HX-Trigger"] == "showMessage"

    def test_htmx_trigger_dict(self) -> None:
        """Test htmx_trigger with dict argument."""
        events = {"showMessage": "Hello World"}
        response = htmx_trigger(events)
        assert isinstance(response, HtmxResponse)
        assert response.headers["HX-Trigger"] == json.dumps(events)

    def test_htmx_redirect(self) -> None:
        """Test htmx_redirect function."""
        response = htmx_redirect("/login")
        assert isinstance(response, HtmxResponse)
        assert response.headers["HX-Redirect"] == "/login"

    def test_htmx_refresh(self) -> None:
        """Test htmx_refresh function."""
        response = htmx_refresh()
        assert isinstance(response, HtmxResponse)
        assert response.headers["HX-Refresh"] == "true"

    def test_htmx_push_url(self) -> None:
        """Test htmx_push_url function."""
        response = htmx_push_url("/new-page", "<div>New content</div>")
        assert isinstance(response, HtmxResponse)
        assert response.headers["HX-Push-Url"] == "/new-page"
        assert response.body == b"<div>New content</div>"

    def test_htmx_retarget(self) -> None:
        """Test htmx_retarget function."""
        response = htmx_retarget("#new-target", "<div>New content</div>")
        assert isinstance(response, HtmxResponse)
        assert response.headers["HX-Retarget"] == "#new-target"
        assert response.body == b"<div>New content</div>"


@pytest.mark.unit
class TestIsHtmx:
    """Test is_htmx function."""

    def test_is_htmx_with_request_object(self) -> None:
        """Test is_htmx with request-like object."""

        class MockRequest:
            def __init__(self, is_htmx: bool) -> None:
                self.headers = {"HX-Request": "true" if is_htmx else "false"}

        assert is_htmx(MockRequest(True)) is True
        assert is_htmx(MockRequest(False)) is False

    def test_is_htmx_with_scope_dict(self) -> None:
        """Test is_htmx with scope dict."""
        scope = {
            "headers": [
                (b"hx-request", b"true"),
            ]
        }
        # Mock debug.enabled to avoid AttributeError
        with patch("fastblocks.htmx.debug") as mock_debug:
            mock_debug.enabled = False
            assert is_htmx(scope) is True

    def test_is_htmx_with_scope_dict_no_htmx(self) -> None:
        """Test is_htmx with scope dict without HTMX header."""
        scope = {
            "headers": [
                (b"content-type", b"text/html"),
            ]
        }
        assert is_htmx(scope) is False

    def test_is_htmx_with_invalid_object(self) -> None:
        """Test is_htmx with invalid object."""
        assert is_htmx("invalid") is False


# Skip HtmxRequest tests as they require Starlette.Request which is complex to mock
# In a real test environment, we would test this with integration tests


@pytest.mark.unit
class TestHtmxAsyncFallback:
    """Regression coverage for the safe async boundary used by HTMX decorators.

    Pins two contracts documented in ``fastblocks/CLAUDE.md``::

      * The sync fallback must execute the publish coroutine to completion
        and close its event loop — no coroutine is silently dropped.
      * An async caller must not run a blocking loop from inside an
        active event loop — ``_run_async_safely`` must refuse and surface
        a clear ``RuntimeError`` so the caller can await natively.
    """

    def test_htmx_trigger_publishes_and_completes(self) -> None:
        """htmx_trigger must await publish_htmx_trigger to completion."""
        publisher = AsyncMock(return_value=True)
        # Track whether the coroutine was awaited
        awaited = {"value": False}

        async def fake_publish(trigger_name, trigger_data=None, target=None):
            awaited["value"] = True
            return await publisher(trigger_name=trigger_name, trigger_data=trigger_data)

        with patch(
            "fastblocks.adapters.templates._events_wrapper.publish_htmx_trigger",
            side_effect=fake_publish,
        ):
            with warnings.catch_warnings():
                warnings.simplefilter("error", RuntimeWarning)
                response = htmx_trigger({"showMessage": "Hello"})

        assert isinstance(response, HtmxResponse)
        assert response.headers["HX-Trigger"] == json.dumps({"showMessage": "Hello"})
        assert awaited["value"] is True

    def test_htmx_redirect_publishes_and_completes(self) -> None:
        """htmx_redirect must await publish_htmx_update to completion."""
        publisher = AsyncMock(return_value=True)
        awaited = {"value": False}

        class _Stub:
            async def publish_htmx_update(
                self, update_type, target=None, **_kwargs
            ):
                awaited["value"] = True
                return await publisher(update_type=update_type, target=target)

        # Note: htmx.py calls ``get_event_publisher()`` without ``await``,
        # so the stub factory must be synchronous.
        with patch(
            "fastblocks._events_integration.get_event_publisher",
            return_value=_Stub(),
        ):
            with warnings.catch_warnings():
                warnings.simplefilter("error", RuntimeWarning)
                response = htmx_redirect("/login")

        assert isinstance(response, HtmxResponse)
        assert response.headers["HX-Redirect"] == "/login"
        assert awaited["value"] is True

    def test_htmx_refresh_publishes_and_completes(self) -> None:
        """htmx_refresh must await publish_htmx_refresh to completion."""
        publisher = AsyncMock(return_value=True)
        awaited = {"value": False}

        async def fake_publish(target, swap_method=None):
            awaited["value"] = True
            return await publisher(target=target, swap_method=swap_method)

        with patch(
            "fastblocks.adapters.templates._events_wrapper.publish_htmx_refresh",
            side_effect=fake_publish,
        ):
            with warnings.catch_warnings():
                warnings.simplefilter("error", RuntimeWarning)
                response = htmx_refresh()

        assert isinstance(response, HtmxResponse)
        assert response.headers["HX-Refresh"] == "true"
        assert awaited["value"] is True

    def test_htmx_decorators_do_not_warn_on_no_publisher(self) -> None:
        """No RuntimeWarning must leak when the event publisher is unavailable.

        Regression for the four ``RuntimeWarning: coroutine ... was never
        awaited`` warnings previously emitted by every HTMX decorator path
        in pytest-asyncio's auto-managed event loop.
        """
        # Force the publisher lookup to fail/return None so we exercise the
        # real short-circuit inside the publish helpers.
        with patch(
            "fastblocks._events_integration.get_event_publisher",
            return_value=None,
        ):
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                htmx_trigger("showMessage")
                htmx_redirect("/login")
                htmx_refresh()

        coroutine_warnings = [
            w
            for w in caught
            if issubclass(w.category, RuntimeWarning)
            and "was never awaited" in str(w.message)
        ]
        assert coroutine_warnings == []


@pytest.mark.unit
class TestRunAsyncSafely:
    """Direct coverage for the ``_run_async_safely`` helper."""

    def test_runs_coroutine_to_completion_when_no_loop(self) -> None:
        """Sync callers get the coroutine result with no leaked loop."""
        result = _run_async_safely(asyncio.sleep(0, result="ok"))
        assert result == "ok"

    def test_propagates_coroutine_exceptions(self) -> None:
        """Exceptions from the coroutine surface to the caller."""

        async def _boom() -> None:
            raise RuntimeError("kaboom")

        with pytest.raises(RuntimeError, match="kaboom"):
            _run_async_safely(_boom())

    def test_refuses_inside_running_loop(self) -> None:
        """Already inside a loop -> RuntimeError points at native async path."""
        ran = {"value": False}

        async def _outer() -> None:
            nonlocal ran
            ran["value"] = True
            # Build the inner coroutine here so the test's RuntimeError
            # path can ``close()`` it before it would be GC'd.
            inner = asyncio.sleep(0, result="should-not-run")
            try:
                with pytest.raises(
                    RuntimeError,
                    match="use the native async path inside an active event loop",
                ):
                    _run_async_safely(inner)
            finally:
                # Prevent RuntimeWarning leak from the never-awaited inner.
                inner.close()

        asyncio.run(_outer())
        assert ran["value"] is True
