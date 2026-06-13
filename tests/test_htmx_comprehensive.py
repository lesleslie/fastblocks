"""Comprehensive tests for HTMX functionality."""

import json
from unittest.mock import MagicMock, Mock

import pytest
from starlette.requests import Request as StarletteRequest

from fastblocks.htmx import (
    HtmxDetails,
    HtmxRequest,
    HtmxResponse,
    htmx_push_url,
    htmx_redirect,
    htmx_refresh,
    htmx_retarget,
    htmx_trigger,
    is_htmx,
)


class TestHtmxDetails:
    """Test HtmxDetails class."""

    def test_htmx_details_init(self) -> None:
        """Test HtmxDetails initialization."""
        scope = {"type": "http", "path": "/test", "headers": []}
        details = HtmxDetails(scope)
        assert details._scope == scope

    def test_is_htmx_request_true(self) -> None:
        """Test detecting HTMX request when header is present."""
        scope = {
            "type": "http",
            "path": "/test",
            "headers": [(b"HX-Request", b"true")],
        }
        details = HtmxDetails(scope)
        assert bool(details) is True

    def test_is_htmx_request_false(self) -> None:
        """Test detecting non-HTMX request."""
        scope = {
            "type": "http",
            "path": "/test",
            "headers": [],
        }
        details = HtmxDetails(scope)
        assert bool(details) is False

    def test_boosted_property(self) -> None:
        """Test boosted property."""
        scope = {
            "type": "http",
            "path": "/test",
            "headers": [(b"HX-Boosted", b"true")],
        }
        details = HtmxDetails(scope)
        assert details.boosted is True

    def test_current_url_property(self) -> None:
        """Test current_url property."""
        url = "http://example.com/test"
        scope = {
            "type": "http",
            "path": "/test",
            "headers": [(b"HX-Current-URL", url.encode())],
        }
        details = HtmxDetails(scope)
        assert details.current_url == url

    def test_history_restore_request(self) -> None:
        """Test history_restore_request property."""
        scope = {
            "type": "http",
            "path": "/test",
            "headers": [(b"HX-History-Restore-Request", b"true")],
        }
        details = HtmxDetails(scope)
        assert details.history_restore_request is True

    def test_prompt_property(self) -> None:
        """Test prompt property."""
        prompt_text = "Enter value:"
        scope = {
            "type": "http",
            "path": "/test",
            "headers": [(b"HX-Prompt", prompt_text.encode())],
        }
        details = HtmxDetails(scope)
        assert details.prompt == prompt_text

    def test_target_property(self) -> None:
        """Test target property."""
        target = "#my-element"
        scope = {
            "type": "http",
            "path": "/test",
            "headers": [(b"HX-Target", target.encode())],
        }
        details = HtmxDetails(scope)
        assert details.target == target

    def test_trigger_property(self) -> None:
        """Test trigger property."""
        trigger = "my-trigger"
        scope = {
            "type": "http",
            "path": "/test",
            "headers": [(b"HX-Trigger", trigger.encode())],
        }
        details = HtmxDetails(scope)
        assert details.trigger == trigger

    def test_trigger_name_property(self) -> None:
        """Test trigger_name property."""
        trigger_name = "myTrigger"
        scope = {
            "type": "http",
            "path": "/test",
            "headers": [(b"HX-Trigger-Name", trigger_name.encode())],
        }
        details = HtmxDetails(scope)
        assert details.trigger_name == trigger_name

    def test_triggering_event_valid_json(self) -> None:
        """Test triggering_event with valid JSON."""
        event_data = {"key": "value", "number": 42}
        scope = {
            "type": "http",
            "path": "/test",
            "headers": [(b"Triggering-Event", json.dumps(event_data).encode())],
        }
        details = HtmxDetails(scope)
        assert details.triggering_event == event_data

    def test_triggering_event_invalid_json(self) -> None:
        """Test triggering_event with invalid JSON."""
        scope = {
            "type": "http",
            "path": "/test",
            "headers": [(b"Triggering-Event", b"invalid json")],
        }
        details = HtmxDetails(scope)
        assert details.triggering_event is None

    def test_triggering_event_none(self) -> None:
        """Test triggering_event when header is missing."""
        scope = {
            "type": "http",
            "path": "/test",
            "headers": [],
        }
        details = HtmxDetails(scope)
        assert details.triggering_event is None

    def test_get_all_headers(self) -> None:
        """Test get_all_headers method."""
        scope = {
            "type": "http",
            "path": "/test",
            "headers": [
                (b"HX-Request", b"true"),
                (b"HX-Boosted", b"true"),
                (b"HX-Current-URL", b"http://example.com"),
                (b"HX-Target", b"#element"),
            ],
        }
        details = HtmxDetails(scope)
        headers = details.get_all_headers()

        assert headers["HX-Request"] == "true"
        assert headers["HX-Boosted"] == "true"
        assert headers["HX-Current-URL"] == "http://example.com"
        assert headers["HX-Target"] == "#element"
        assert "HX-History-Restore-Request" not in headers

    def test_get_header_with_autoencoding(self) -> None:
        """Test _get_header with URI autoencoding."""
        scope = {
            "type": "http",
            "path": "/test",
            "headers": [
                (b"HX-Current-URL", b"http%3A%2F%2Fexample.com%2Ftest%20page"),
                (b"hx-current-url-uri-autoencoded", b"true"),
            ],
        }
        details = HtmxDetails(scope)
        # Should unquote the value
        assert details.current_url == "http://example.com/test page"

    def test_case_insensitive_headers(self) -> None:
        """Test that header matching is case-insensitive."""
        scope = {
            "type": "http",
            "path": "/test",
            "headers": [(b"hx-request", b"true")],  # lowercase
        }
        details = HtmxDetails(scope)
        assert bool(details) is True


class TestHtmxResponse:
    """Test HtmxResponse class."""

    def test_basic_response(self) -> None:
        """Test basic HTMX response."""
        response = HtmxResponse(content="<div>Test</div>")
        assert response.body == b"<div>Test</div>"
        assert response.status_code == 200

    def test_trigger_header(self) -> None:
        """Test HX-Trigger header."""
        response = HtmxResponse(content="test", trigger="myEvent")
        assert "HX-Trigger" in response.headers
        assert response.headers["HX-Trigger"] == "myEvent"

    def test_trigger_after_settle_header(self) -> None:
        """Test HX-Trigger-After-Settle header."""
        response = HtmxResponse(content="test", trigger_after_settle="event1")
        assert "HX-Trigger-After-Settle" in response.headers
        assert response.headers["HX-Trigger-After-Settle"] == "event1"

    def test_trigger_after_swap_header(self) -> None:
        """Test HX-Trigger-After-Swap header."""
        response = HtmxResponse(content="test", trigger_after_swap="event2")
        assert "HX-Trigger-After-Swap" in response.headers
        assert response.headers["HX-Trigger-After-Swap"] == "event2"

    def test_retarget_header(self) -> None:
        """Test HX-Retarget header."""
        response = HtmxResponse(content="test", retarget="#new-target")
        assert "HX-Retarget" in response.headers
        assert response.headers["HX-Retarget"] == "#new-target"

    def test_reselect_header(self) -> None:
        """Test HX-Reselect header."""
        response = HtmxResponse(content="test", reselect=".selected")
        assert "HX-Reselect" in response.headers
        assert response.headers["HX-Reselect"] == ".selected"

    def test_reswap_header(self) -> None:
        """Test HX-Reswap header."""
        response = HtmxResponse(content="test", reswap="innerHTML")
        assert "HX-Reswap" in response.headers
        assert response.headers["HX-Reswap"] == "innerHTML"

    def test_push_url_header_string(self) -> None:
        """Test HX-Push-Url header with string."""
        response = HtmxResponse(content="test", push_url="/new-path")
        assert "HX-Push-Url" in response.headers
        assert response.headers["HX-Push-Url"] == "/new-path"

    def test_push_url_header_false(self) -> None:
        """Test HX-Push-Url header with False."""
        response = HtmxResponse(content="test", push_url=False)
        assert "HX-Push-Url" in response.headers
        assert response.headers["HX-Push-Url"] == "false"

    def test_replace_url_header(self) -> None:
        """Test HX-Replace-Url header."""
        response = HtmxResponse(content="test", replace_url="/replaced")
        assert "HX-Replace-Url" in response.headers
        assert response.headers["HX-Replace-Url"] == "/replaced"

    def test_refresh_header(self) -> None:
        """Test HX-Refresh header."""
        response = HtmxResponse(content="test", refresh=True)
        assert "HX-Refresh" in response.headers
        assert response.headers["HX-Refresh"] == "true"

    def test_redirect_header(self) -> None:
        """Test HX-Redirect header."""
        response = HtmxResponse(content="test", redirect="/redirect-to")
        assert "HX-Redirect" in response.headers
        assert response.headers["HX-Redirect"] == "/redirect-to"

    def test_location_header_dict(self) -> None:
        """Test HX-Location header with dict."""
        location_data = {"path": "/new", "target": "#content"}
        response = HtmxResponse(content="test", location=location_data)
        assert "HX-Location" in response.headers
        assert json.loads(response.headers["HX-Location"]) == location_data

    def test_location_header_string(self) -> None:
        """Test HX-Location header with string."""
        response = HtmxResponse(content="test", location="/location")
        assert "HX-Location" in response.headers
        assert response.headers["HX-Location"] == "/location"

    def test_custom_status_code(self) -> None:
        """Test custom status code."""
        response = HtmxResponse(content="test", status_code=201)
        assert response.status_code == 201

    def test_custom_headers(self) -> None:
        """Test custom headers are preserved."""
        custom_headers = {"X-Custom": "value"}
        response = HtmxResponse(content="test", headers=custom_headers)
        assert "X-Custom" in response.headers
        assert response.headers["X-Custom"] == "value"

    def test_combined_headers(self) -> None:
        """Test multiple HTMX headers combined."""
        response = HtmxResponse(
            content="test",
            trigger="event1",
            retarget="#target",
            reswap="outerHTML",
            refresh=True,
        )
        assert response.headers["HX-Trigger"] == "event1"
        assert response.headers["HX-Retarget"] == "#target"
        assert response.headers["HX-Reswap"] == "outerHTML"
        assert response.headers["HX-Refresh"] == "true"


class TestHtmxHelperFunctions:
    """Test HTMX helper functions."""

    def test_htmx_trigger_with_string(self) -> None:
        """Test htmx_trigger with string event name."""
        response = htmx_trigger("myEvent", content="test")
        assert isinstance(response, HtmxResponse)
        assert response.headers["HX-Trigger"] == "myEvent"

    def test_htmx_trigger_with_dict(self) -> None:
        """Test htmx_trigger with dict event data."""
        events = {"event1": {"data": "value"}, "event2": {"count": 42}}
        response = htmx_trigger(events, content="test")
        assert isinstance(response, HtmxResponse)
        trigger_data = json.loads(response.headers["HX-Trigger"])
        assert trigger_data == events

    def test_htmx_trigger_custom_status(self) -> None:
        """Test htmx_trigger with custom status code."""
        response = htmx_trigger("event", status_code=201)
        assert response.status_code == 201

    def test_htmx_redirect(self) -> None:
        """Test htmx_redirect function."""
        response = htmx_redirect("/new-location")
        assert isinstance(response, HtmxResponse)
        assert response.headers["HX-Redirect"] == "/new-location"

    def test_htmx_redirect_with_kwargs(self) -> None:
        """Test htmx_redirect with additional kwargs."""
        response = htmx_redirect("/location", status_code=302, content="Moved")
        assert response.headers["HX-Redirect"] == "/location"
        assert response.status_code == 302

    def test_htmx_refresh(self) -> None:
        """Test htmx_refresh function."""
        response = htmx_refresh()
        assert isinstance(response, HtmxResponse)
        assert response.headers["HX-Refresh"] == "true"

    def test_htmx_refresh_with_target(self) -> None:
        """Test htmx_refresh with custom target."""
        response = htmx_refresh(target="#custom")
        assert isinstance(response, HtmxResponse)
        assert response.headers["HX-Refresh"] == "true"

    def test_htmx_push_url(self) -> None:
        """Test htmx_push_url function."""
        response = htmx_push_url("/new-url", content="test")
        assert isinstance(response, HtmxResponse)
        assert response.headers["HX-Push-Url"] == "/new-url"

    def test_htmx_retarget(self) -> None:
        """Test htmx_retarget function."""
        response = htmx_retarget("#target", content="test")
        assert isinstance(response, HtmxResponse)
        assert response.headers["HX-Retarget"] == "#target"

    def test_is_htmx_with_request_object(self) -> None:
        """Test is_htmx with Starlette Request object."""
        mock_request = Mock()
        mock_request.headers = {"HX-Request": "true"}
        assert is_htmx(mock_request) is True

    def test_is_htmx_with_request_object_false(self) -> None:
        """Test is_htmx with non-HTMX Request object."""
        mock_request = Mock()
        mock_request.headers = {}
        assert is_htmx(mock_request) is False

    def test_is_htmx_with_scope_dict(self) -> None:
        """Test is_htmx with scope dict."""
        scope = {
            "type": "http",
            "path": "/test",
            "headers": [(b"HX-Request", b"true")],
        }
        assert is_htmx(scope) is True

    def test_is_htmx_with_scope_dict_false(self) -> None:
        """Test is_htmx with scope dict without HTMX headers."""
        scope = {
            "type": "http",
            "path": "/test",
            "headers": [],
        }
        assert is_htmx(scope) is False

    def test_is_htmx_with_invalid_input(self) -> None:
        """Test is_htmx with invalid input."""
        assert is_htmx("invalid") is False
        assert is_htmx(None) is False
        assert is_htmx(123) is False


class TestHtmxRequest:
    """Test HtmxRequest class."""

    def test_htmx_request_extension(self) -> None:
        """Test HtmxRequest extends Starlette Request."""
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/test",
            "headers": [(b"HX-Request", b"true")],
            "query_string": b"",
            "htmx": HtmxDetails(
                {
                    "type": "http",
                    "path": "/test",
                    "headers": [(b"HX-Request", b"true")],
                }
            ),
        }
        request = HtmxRequest(scope)
        assert isinstance(request, StarletteRequest)
        assert request.is_htmx() is True

    def test_htmx_request_is_boosted(self) -> None:
        """Test HtmxRequest.is_boosted method."""
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/test",
            "headers": [(b"HX-Boosted", b"true")],
            "query_string": b"",
            "htmx": HtmxDetails(
                {
                    "type": "http",
                    "path": "/test",
                    "headers": [(b"HX-Boosted", b"true")],
                }
            ),
        }
        request = HtmxRequest(scope)
        assert request.is_boosted() is True

    def test_htmx_request_get_htmx_headers(self) -> None:
        """Test HtmxRequest.get_htmx_headers method."""
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/test",
            "headers": [
                (b"HX-Request", b"true"),
                (b"HX-Trigger", b"click"),
            ],
            "query_string": b"",
            "htmx": HtmxDetails(
                {
                    "type": "http",
                    "path": "/test",
                    "headers": [
                        (b"HX-Request", b"true"),
                        (b"HX-Trigger", b"click"),
                    ],
                }
            ),
        }
        request = HtmxRequest(scope)
        headers = request.get_htmx_headers()
        assert headers["HX-Request"] == "true"
        assert headers["HX-Trigger"] == "click"
