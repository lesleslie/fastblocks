"""FastBlocks Native HTMX Support.

This module consolidates and enhances HTMX functionality for FastBlocks,
originally based on the asgi-htmx library.

Original asgi-htmx library:
- Author: Marcelo Trylesinski
- Repository: https://github.com/marcelotrylesisnki/asgi-htmx
- License: MIT

The FastBlocks implementation extends the original with:
- ACB (Asynchronous Component Base) integration
- FastBlocks-specific debugging and logging
- Enhanced template integration
- Response helpers optimized for FastBlocks
"""

import json
import typing as t
from urllib.parse import unquote

from acb.debug import debug
from starlette.responses import HTMLResponse

if t.TYPE_CHECKING:
    from starlette.types import Scope
else:
    Scope = dict

try:
    from starlette.requests import Request

    _starlette_available = True
except ImportError:
    _starlette_available = False
    Request = t.Any  # type: ignore

STARLETTE_AVAILABLE = _starlette_available


class HtmxDetails:
    def __init__(self, scope: "Scope") -> None:
        self._scope = scope
        debug(
            f"HtmxDetails: Processing HTMX headers for {scope.get('path', 'unknown')}"
        )

    def _get_header(self, name: bytes) -> str | None:
        value = _get_header(self._scope, name)
        if value and debug.enabled:
            debug(f"HtmxDetails: {name.decode()}: {value}")
        return value

    def __bool__(self) -> bool:
        is_htmx = self._get_header(b"HX-Request") == "true"
        debug(f"HtmxDetails: Is HTMX request: {is_htmx}")
        return is_htmx

    @property
    def boosted(self) -> bool:
        return self._get_header(b"HX-Boosted") == "true"

    @property
    def current_url(self) -> str | None:
        return self._get_header(b"HX-Current-URL")

    @property
    def history_restore_request(self) -> bool:
        return self._get_header(b"HX-History-Restore-Request") == "true"

    @property
    def prompt(self) -> str | None:
        return self._get_header(b"HX-Prompt")

    @property
    def target(self) -> str | None:
        return self._get_header(b"HX-Target")

    @property
    def trigger(self) -> str | None:
        return self._get_header(b"HX-Trigger")

    @property
    def trigger_name(self) -> str | None:
        return self._get_header(b"HX-Trigger-Name")

    @property
    def triggering_event(self) -> t.Any:
        value = self._get_header(b"Triggering-Event")
        if value is None:
            return None
        try:
            event_data = json.loads(value)
            debug(f"HtmxDetails: Parsed triggering event: {event_data}")
            return event_data
        except json.JSONDecodeError as e:
            debug(f"HtmxDetails: Failed to parse triggering event JSON: {e}")
            return None

    def get_all_headers(self) -> dict[str, str | None]:
        headers = {
            "HX-Request": self._get_header(b"HX-Request"),
            "HX-Boosted": self._get_header(b"HX-Boosted"),
            "HX-Current-URL": self.current_url,
            "HX-History-Restore-Request": self._get_header(
                b"HX-History-Restore-Request"
            ),
            "HX-Prompt": self.prompt,
            "HX-Target": self.target,
            "HX-Trigger": self.trigger,
            "HX-Trigger-Name": self.trigger_name,
            "Triggering-Event": self._get_header(b"Triggering-Event"),
        }

        return {k: v for k, v in headers.items() if v is not None}


def _get_header(scope: "Scope", key: bytes) -> str | None:
    key = key.lower()
    value: str | None = None
    should_unquote = False
    try:
        for k, v in scope["headers"]:
            if k.lower() == key:
                value = v.decode("latin-1")
            if k.lower() == b"%s-uri-autoencoded" % key and v == b"true":
                should_unquote = True
    except (KeyError, UnicodeDecodeError) as e:
        debug(f"HtmxDetails: Error processing header {key}: {e}")
        return None
    if value is None:
        return None
    try:
        return unquote(value) if should_unquote else value
    except Exception as e:
        debug(f"HtmxDetails: Error unquoting header value: {e}")
        return value


HtmxScope = dict[str, t.Any]

if STARLETTE_AVAILABLE and Request is not t.Any:

    class HtmxRequest(Request):  # type: ignore
        scope: HtmxScope

        @property
        def htmx(self) -> HtmxDetails:
            return self.scope["htmx"]

        def is_htmx(self) -> bool:
            return bool(self.htmx)

        def is_boosted(self) -> bool:
            return self.htmx.boosted

        def get_htmx_headers(self) -> dict[str, str | None]:
            return self.htmx.get_all_headers()
else:

    class HtmxRequest:  # type: ignore
        """Placeholder HtmxRequest when Starlette is not available."""

        def __init__(self, *args: t.Any, **kwargs: t.Any) -> None:
            raise ImportError(
                "Starlette is required for HtmxRequest. Install with: uv add starlette"
            )


class HtmxResponse(HTMLResponse):
    def __init__(
        self,
        content: str = "",
        status_code: int = 200,
        headers: t.Mapping[str, str] | None = None,
        media_type: str | None = None,
        background: t.Any = None,
        trigger: str | None = None,
        trigger_after_settle: str | None = None,
        trigger_after_swap: str | None = None,
        retarget: str | None = None,
        reselect: str | None = None,
        reswap: str | None = None,
        push_url: str | bool | None = None,
        replace_url: str | bool | None = None,
        refresh: bool = False,
        redirect: str | None = None,
        location: dict[str, t.Any] | str | None = None,
    ) -> None:
        init_headers = dict(headers or {})

        if trigger:
            init_headers["HX-Trigger"] = trigger
        if trigger_after_settle:
            init_headers["HX-Trigger-After-Settle"] = trigger_after_settle
        if trigger_after_swap:
            init_headers["HX-Trigger-After-Swap"] = trigger_after_swap
        if retarget:
            init_headers["HX-Retarget"] = retarget
        if reselect:
            init_headers["HX-Reselect"] = reselect
        if reswap:
            init_headers["HX-Reswap"] = reswap
        if push_url is not None:
            init_headers["HX-Push-Url"] = str(push_url).lower()
        if replace_url is not None:
            init_headers["HX-Replace-Url"] = str(replace_url).lower()
        if refresh:
            init_headers["HX-Refresh"] = "true"
        if redirect:
            init_headers["HX-Redirect"] = redirect
        if location:
            if isinstance(location, dict):
                init_headers["HX-Location"] = json.dumps(location)
            else:
                init_headers["HX-Location"] = str(location)

        super().__init__(
            content=content,
            status_code=status_code,
            headers=init_headers,
            media_type=media_type,
            background=background,
        )


def htmx_trigger(
    trigger_events: str | dict[str, t.Any],
    content: str = "",
    status_code: int = 200,
    **kwargs: t.Any,
) -> HtmxResponse:
    if isinstance(trigger_events, dict):
        trigger_value = json.dumps(trigger_events)
    else:
        trigger_value = trigger_events

    return HtmxResponse(
        content=content,
        status_code=status_code,
        trigger=trigger_value,
        **kwargs,
    )


def htmx_redirect(url: str, **kwargs: t.Any) -> HtmxResponse:
    return HtmxResponse(redirect=url, **kwargs)


def htmx_refresh(**kwargs: t.Any) -> HtmxResponse:
    return HtmxResponse(refresh=True, **kwargs)


def htmx_push_url(url: str, content: str = "", **kwargs: t.Any) -> HtmxResponse:
    return HtmxResponse(content=content, push_url=url, **kwargs)


def htmx_retarget(target: str, content: str = "", **kwargs: t.Any) -> HtmxResponse:
    return HtmxResponse(content=content, retarget=target, **kwargs)


def is_htmx(scope_or_request: dict[str, t.Any] | t.Any) -> bool:
    if hasattr(scope_or_request, "headers"):
        headers = getattr(scope_or_request, "headers", {})
        return headers.get("HX-Request") == "true"
    else:
        if isinstance(scope_or_request, dict):
            details = HtmxDetails(scope_or_request)
            return getattr(details, "is_htmx", False)
        return False


__all__ = [
    "HtmxDetails",
    "HtmxRequest",
    "HtmxResponse",
    "htmx_trigger",
    "htmx_redirect",
    "htmx_refresh",
    "htmx_push_url",
    "htmx_retarget",
    "is_htmx",
]
