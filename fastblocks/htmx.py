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
- Event-driven HTMX updates via ACB Events system
"""

import asyncio
import json
import typing as t
import warnings
from contextlib import suppress
from typing import Any
from urllib.parse import unquote

try:
    from acb.debug import debug
except ImportError:
    # Fallback debug function if acb.debug is not available
    import logging

    debug = logging.debug
from starlette.responses import HTMLResponse

if t.TYPE_CHECKING:
    from starlette.types import Scope
else:
    Scope = dict

try:
    from starlette.requests import Request as StarletteRequest

    _starlette_available = True
except ImportError:
    _starlette_available = False
    StarletteRequest: t.Any = t.Any  # type: ignore[misc,no-redef]  # Fallback when Starlette unavailable

STARLETTE_AVAILABLE = _starlette_available


class HtmxDetails:
    def __init__(self, scope: "Scope") -> None:
        self._scope = scope
        debug(
            f"HtmxDetails: Processing HTMX headers for {scope.get('path', 'unknown')}"
        )

    def _get_header(self, name: bytes) -> str | None:
        value = _get_header(self._scope, name)
        if value and debug:
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
    key_lower = key.lower()
    value: str | None = None
    should_unquote = False

    # Extract header value and autoencoding flag
    try:
        for k, v in scope["headers"]:
            if k.lower() == key_lower:
                value = v.decode("latin-1")
            if k.lower() == b"%s-uri-autoencoded" % key_lower and v == b"true":
                should_unquote = True
    except (KeyError, UnicodeDecodeError) as e:
        debug(f"HtmxDetails: Error processing header {key}: {e}")
        return None

    # Return None if no value found
    if value is None:
        return None

    # Handle URI autoencoding if needed
    try:
        return unquote(value) if should_unquote else value
    except Exception as e:
        debug(f"HtmxDetails: Error unquoting header value: {e}")
        return value


HtmxScope = dict[str, t.Any]

if STARLETTE_AVAILABLE and StarletteRequest is not t.Any:

    class HtmxRequest(StarletteRequest):  # type: ignore[misc]
        scope: HtmxScope

        @property
        def htmx(self) -> HtmxDetails:
            return t.cast(HtmxDetails, self.scope["htmx"])

        def is_htmx(self) -> bool:
            return bool(self.htmx)

        def is_boosted(self) -> bool:
            return self.htmx.boosted

        def get_htmx_headers(self) -> dict[str, str | None]:
            return self.htmx.get_all_headers()
else:

    class HtmxRequest:  # type: ignore[misc,no-redef]
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

        # Set HTMX-specific headers
        self._set_htmx_headers(
            init_headers,
            trigger=trigger,
            trigger_after_settle=trigger_after_settle,
            trigger_after_swap=trigger_after_swap,
            retarget=retarget,
            reselect=reselect,
            reswap=reswap,
            push_url=push_url,
            replace_url=replace_url,
            refresh=refresh,
            redirect=redirect,
            location=location,
        )

        super().__init__(
            content=content,
            status_code=status_code,
            headers=init_headers,
            media_type=media_type,
            background=background,
        )

    def _set_htmx_headers(
        self,
        headers: dict[str, str],
        *,
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
        """Set HTMX-specific headers in the response."""
        if trigger:
            headers["HX-Trigger"] = trigger
        if trigger_after_settle:
            headers["HX-Trigger-After-Settle"] = trigger_after_settle
        if trigger_after_swap:
            headers["HX-Trigger-After-Swap"] = trigger_after_swap
        if retarget:
            headers["HX-Retarget"] = retarget
        if reselect:
            headers["HX-Reselect"] = reselect
        if reswap:
            headers["HX-Reswap"] = reswap
        if push_url is not None:
            headers["HX-Push-Url"] = str(push_url).lower()
        if replace_url is not None:
            headers["HX-Replace-Url"] = str(replace_url).lower()
        if refresh:
            headers["HX-Refresh"] = "true"
        if redirect:
            headers["HX-Redirect"] = redirect
        if location:
            if isinstance(location, dict):
                headers["HX-Location"] = json.dumps(location)
            else:
                headers["HX-Location"] = str(location)


def htmx_trigger(
    trigger_events: str | dict[str, t.Any],
    content: str = "",
    status_code: int = 200,
    **kwargs: t.Any,
) -> HtmxResponse:
    trigger_data: dict[str, Any]
    if isinstance(trigger_events, dict):
        trigger_value = json.dumps(trigger_events)
        trigger_name = next(iter(trigger_events.keys()), "custom_trigger")
        trigger_data = trigger_events
    else:
        trigger_value = trigger_events
        trigger_name = trigger_events
        trigger_data = {}

    # Schedule event publishing in background
    def _run_publish_event() -> None:
        async def _publish_event(
            trigger_name: str, trigger_data: dict[str, t.Any]
        ) -> None:
            from .adapters.templates._events_wrapper import publish_htmx_trigger

            await publish_htmx_trigger(
                trigger_name=trigger_name,
                trigger_data=trigger_data,
            )

        # Create and schedule the task to run the async function

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            task = _publish_event(trigger_name, trigger_data)
            asyncio.create_task(task)

    with suppress(Exception):
        _run_publish_event()

    return HtmxResponse(
        content=content,
        status_code=status_code,
        trigger=trigger_value,
        **kwargs,
    )


def htmx_redirect(url: str, **kwargs: t.Any) -> HtmxResponse:
    # Schedule event publishing in background
    def _run_publish_event() -> None:
        async def _publish_event(url: str) -> None:
            from ._events_integration import get_event_publisher

            publisher = get_event_publisher()
            if publisher:
                await publisher.publish_htmx_update(
                    update_type="redirect",
                    target=url,
                )

        # Create and schedule the task to run the async function

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            task = _publish_event(url)
            asyncio.create_task(task)

    with suppress(Exception):
        _run_publish_event()

    return HtmxResponse(redirect=url, **kwargs)


def htmx_refresh(**kwargs: t.Any) -> HtmxResponse:
    # Get target from kwargs if provided
    target = kwargs.get("target", "#body")

    # Schedule event publishing in background
    def _run_publish_event() -> None:
        async def _publish_event(target: str) -> None:
            from .adapters.templates._events_wrapper import publish_htmx_refresh

            await publish_htmx_refresh(target=target)

        # Create and schedule the task to run the async function

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            task = _publish_event(target)
            asyncio.create_task(task)

    with suppress(Exception):
        _run_publish_event()

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
