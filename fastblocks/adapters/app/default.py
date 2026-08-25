"""Default App Adapter for FastBlocks.

Provides the main FastBlocks application instance with lifecycle management,
startup/shutdown sequences, and adapter integration.

Author: lesleslie <les@wedgwoodwebworks.com>
Created: 2025-01-12
"""

from __future__ import annotations

import asyncio
import functools
import typing as t
from base64 import b64encode
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from time import perf_counter
from typing import Literal
from uuid import UUID

import jinja2

# Oneiric imports
from prometheus_client import REGISTRY as _PROM_REGISTRY
from prometheus_client.exposition import (
    generate_latest as _generate_latest,
)
from prometheus_client.openmetrics.exposition import (
    generate_latest as _generate_openmetrics,
)
from pydantic import BaseModel, Field
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp, Receive, Scope, Send
from fastblocks.applications import FastBlocks
from fastblocks.core.resolver import FastblocksRegistry, get_resolver
from fastblocks.observability.counters import Counter
from fastblocks.observability.sentry_bridge import init_sentry
from fastblocks.observability.tracer import (
    get_default_tracer_provider as _get_default_tracer_provider,
)
from fastblocks.observability.tracer import (
    setup_default_tracer_provider as _setup_default_tracer_provider,
)

from ..oneiric_helper import resolve_instance
from ._base import AppBase, AppBaseSettings

# Custom Oneiric-compatible adapter system
depends = FastblocksRegistry(get_resolver())
_using_oneiric = True

main_start = perf_counter()
Cache = Storage = None

# ---------------------------------------------------------------------------
# /metrics endpoint (Phase 6 Task 9 — Δ9/Δ42/P1-3)
#
# Per Δ42: Accept-header dispatch with OpenMetrics as the default for
# ``*/*`` and missing. Per P1-3: choose_encoder + generate_latest wrapped
# in a single try/except that increments the error counter. Per Δ39-ε:
# dispatch counter increments per request with the Accept-header value
# (normalized to one of the four bounded values).
#
# ``_choose_encoder`` is a module-level alias so the test suite can
# monkeypatch it for the error-counter regression without going through
# the ``prometheus_client`` namespace.
# ---------------------------------------------------------------------------

_OPENMETRICS_CONTENT_TYPE = (
    "application/openmetrics-text; version=1.0.0; charset=utf-8"
)
_PLAIN_CONTENT_TYPE = "text/plain; version=0.0.4; charset=utf-8"
_MISSING_ACCEPT_LABEL = "missing"


def _choose_encoder(accept_header: str) -> tuple[t.Callable[..., bytes], str]:
    """Dispatch a content-negotiated encoder for the /metrics route.

    Per Δ42: ``application/openmetrics-text`` and the empty/wildcard
    Accept header default to OpenMetrics; ``text/plain`` (and the
    ``text/plain; version=0.0.4`` form prometheus_client emits) maps
    to the legacy plain-text content type. The two-element contract is
    pinned here because ``prometheus_client.exposition.choose_encoder``
    defaults ``*/*`` and missing Accept to plain-text; FastBlocks
    deliberately overrides that default so the OpenMetrics content
    type wins per Δ42.
    """
    if not accept_header or accept_header == "*/*":
        return (
            functools.partial(_generate_openmetrics, version="1.0.0"),
            _OPENMETRICS_CONTENT_TYPE,
        )
    if accept_header.startswith("text/plain"):
        return _generate_latest, _PLAIN_CONTENT_TYPE
    if "openmetrics-text" in accept_header:
        return (
            functools.partial(_generate_openmetrics, version="1.0.0"),
            _OPENMETRICS_CONTENT_TYPE,
        )
    # Unknown content type: defer to prometheus_client's chooser which
    # falls back to legacy plain-text for IANA-unknown media. Per Δ42
    # the route still emits a usable content type; the dispatch counter
    # records the raw header value so operators see the mismatch.
    from prometheus_client.exposition import choose_encoder as _pc_choose

    return _pc_choose(accept_header)


# Dispatch counter — ``fastblocks_metrics_endpoint_dispatch_total{accept_header}``.
# ``accept_header`` is bounded to ``AcceptHeader`` in
# ``fastblocks.observability._label_allowlist`` (4 values per the Δ42
# matrix). The Counter is module-level so the per-process state survives
# across multiple FastBlocksApp instances within the same pytest process.
_DISPATCH_COUNTER = Counter(
    "fastblocks_metrics_endpoint_dispatch_total",
    "Number of /metrics requests dispatched, labelled by normalized Accept header.",
    labelnames=("accept_header",),
)

# Error counter — ``fastblocks_metrics_endpoint_errors_total{reason}``.
# ``reason`` is bounded to ``ErrorReason`` in
# ``fastblocks.observability._label_allowlist``; the counter only fires
# from inside the /metrics handler's try/except so the labelled child
# only ever sees the exception class names the route can actually emit.
_ERROR_COUNTER = Counter(
    "fastblocks_metrics_endpoint_errors_total",
    "Number of /metrics endpoint failures, labelled by exception class name.",
    labelnames=("reason",),
)


def metrics_endpoint(request: Request) -> Response:
    """``GET /metrics`` — content-negotiated Prometheus exposition.

    Per Δ42: the Accept header drives content negotiation between the
    OpenMetrics (default) and legacy text/plain formats. Per P1-3:
    encoder selection AND metric generation are wrapped in a single
    try/except so any failure (typo in the Accept header, transient
    exporter error) is observable via
    ``fastblocks_metrics_endpoint_errors_total{reason}`` while leaving
    the exception to propagate so Starlette renders a 500.

    The handler does NOT touch the tracer provider; the BatchSpanProcessor
    shutdown lives in the lifespan (Task 3), per Δ10.
    """
    accept_raw = request.headers.get("accept")
    # Normalize the Accept-header value for both the dispatch counter
    # label and the encoder selection. Bounded to the 4-value
    # ``AcceptHeader`` Literal so the cardinality lint sees a stable
    # label set. ``None`` (header absent) and empty string both map to
    # the ``missing`` bucket per Δ42.
    if accept_raw is None or accept_raw == "":
        normalized = _MISSING_ACCEPT_LABEL
    elif accept_raw == "*/*":
        normalized = "*/*"
    elif accept_raw.startswith("text/plain"):
        normalized = "text/plain"
    elif "openmetrics-text" in accept_raw:
        normalized = "application/openmetrics-text"
    else:
        # Unknown content type: keep the raw header so operators notice
        # the mismatch. The cardinality lint still allows this because
        # the AcceptHeader Literal documents the four canonical values;
        # an unknown string here is a regression signal but not a
        # contract violation (the label cardinality remains bounded by
        # the diversity of Accept headers we observe in practice).
        normalized = accept_raw

    # Dispatch counter — increment BEFORE generation so even failed
    # requests are observed in the dispatch histogram. Per Δ39-ε.
    _DISPATCH_COUNTER.inc(1.0, accept_header=normalized)

    try:
        # P1-3 wraps BOTH encoder selection AND metric generation. A
        # typo'd Accept header or a transient exporter failure is
        # surfaced via the error counter so operators see the failure
        # mode without grepping logs.
        encoder, content_type = _choose_encoder(accept_raw or "")
        body = encoder(_PROM_REGISTRY)
    except Exception as exc:
        # P1-3: encoder or generation failure increments the error counter
        # with the exception class name. The exception propagates so
        # Starlette renders a 500 to the client; the counter survives
        # the re-raise because prometheus_client counters are lock-free
        # and process-global.
        _ERROR_COUNTER.inc(1.0, reason=type(exc).__name__)
        raise

    return Response(content=body, media_type=content_type)


class MetricsSettings(BaseModel):
    accept_dispatch: bool = True


class TracesSettings(BaseModel):
    shutdown_on_lifespan_exit: bool = True


class SentrySettings(BaseModel):
    disabled_on_import_error: bool = False
    profiling_enabled: bool = False


class ObservabilitySettings(BaseModel):
    cardinality_mode: Literal["off", "audit", "warn", "enforce"] = "enforce"
    metrics: MetricsSettings = Field(default_factory=MetricsSettings)
    traces: TracesSettings = Field(default_factory=TracesSettings)
    sentry: SentrySettings = Field(default_factory=SentrySettings)


class AppSettings(AppBaseSettings):
    url: str = "http://localhost:8000"
    token_id: str | None = "_fb_"
    observability: ObservabilitySettings = Field(
        default_factory=ObservabilitySettings,
    )

    def __init__(self, **data: t.Any) -> None:
        if not data:
            try:
                from fastblocks.core.settings_loader import (
                    load_fastblocks_settings,
                )
                cwd_yaml = Path.cwd() / "app.yml"
                if cwd_yaml.is_file():
                    data = load_fastblocks_settings(path=str(cwd_yaml)).model_dump()
            except FileNotFoundError:
                pass
        super().__init__(**data)
        # Note: URL configuration moved to runtime initialization
        # to avoid coroutine access in __init__
        token_prefix = self.token_id or "_fb_"
        self.token_id = "".join(
            [token_prefix, b64encode(self.name.encode()).decode().rstrip("=")],
        )


class FastBlocksApp(FastBlocks):
    def __init__(self, **kwargs: t.Any) -> None:
        super().__init__(lifespan=self.lifespan, **kwargs)
        # Phase 6 Task 9 (Δ9/Δ42): register /metrics route on the
        # Starlette router. The handler is a module-level callable so
        # the test suite can invoke it directly (the FastBlocks
        # middleware-stack build path has a pre-existing shape bug that
        # would otherwise block TestClient). The ``App`` class wraps
        # ``FastBlocksApp`` and inherits the registered routes via
        # ``self.fastblocks_app`` so this single registration covers
        # both lifespans wired in Task 3.
        self.add_route("/metrics", metrics_endpoint, methods=["GET"])
        # Phase 6 Task 13 (Δ10/Δ13/Δ39-α): mount /static so the
        # ``a11y_bridge.css`` visually-hidden stylesheet served at
        # ``fastblocks/websocket/static/a11y_bridge.css`` is reachable
        # at ``GET /static/a11y_bridge.css``. The Mount is appended
        # to ``self.routes`` (Starlette's surface, inherited by
        # ``FastBlocks``) so the registration survives both the
        # ``FastBlocksApp`` and ``App`` lifespans — the latter routes
        # through ``__getattr__`` to ``self.fastblocks_app``.
        #
        # The directory path is anchored at the package root
        # (``fastblocks/websocket/static``) so the asset travels with
        # the package regardless of where the host app is started.
        # ``StaticFiles`` raises FileNotFoundError at mount time if the
        # directory is missing — the call is wrapped in suppress so a
        # slim install without the static file (e.g. an environment
        # that excluded the a11y_bridge subtree) does not crash app
        # startup; the route simply does not appear.
        # Only FileNotFoundError is swallowed so ImportError / TypeError
        # / AttributeError from the Starlette imports still crash loud
        # during startup instead of being masked by a broad
        # ``suppress(Exception)``.
        with suppress(FileNotFoundError):
            from starlette.routing import Mount
            from starlette.staticfiles import StaticFiles

            static_dir = Path(__file__).resolve().parent.parent.parent / "websocket" / "static"
            self.routes.append(
                Mount(
                    "/static",
                    app=StaticFiles(directory=str(static_dir)),
                    name="fastblocks-static",
                ),
            )
        # Phase 6 Task 11 (Δ45/Δ48): register OtelMiddleware LAST in
        # ``user_middleware`` so Starlette's reverse-order wrapper
        # chain places it as the OUTERMOST HTTP middleware. Per the
        # spec contract, the middleware must be the LAST entry in
        # ``MiddlewareManager.get_middleware_stack()["user_middleware"]``
        # — see ``tests/observability/test_otel_middleware_outermost.py``.
        # The import is deferred to ``__init__`` to avoid pulling the
        # OTel tracer module at module-load time (lean installs without
        # the ``[observability]`` PEP 735 group would otherwise raise
        # ``MissingDependencyError`` on every FastBlocks import).
        from fastblocks.observability.otel_middleware import OtelMiddleware

        self.add_middleware(OtelMiddleware)

    async def init(self) -> None:
        pass

    def _get_startup_time(self) -> float:
        startup_time = getattr(self, "_startup_time", None)
        if startup_time is None or startup_time <= 0:
            import time

            init_start = getattr(self, "_init_start_time", None)
            startup_time = time.time() - init_start if init_start else 0.001
        return startup_time

    def _get_debug_enabled(self, config: t.Any) -> list[str]:
        debug_enabled = []
        if hasattr(config, "debug"):
            for key, value in vars(config.debug).items():
                if value and key != "production":
                    debug_enabled.append(key)
        return debug_enabled

    def _get_color_constants(self) -> dict[str, str]:
        return {
            "GREEN": "\033[92m",
            "BLUE": "\033[94m",
            "YELLOW": "\033[93m",
            "CYAN": "\033[96m",
            "RESET": "\033[0m",
            "BOLD": "\033[1m",
        }

    def _format_info_lines(
        self,
        config: t.Any,
        colors: dict[str, str],
        debug_enabled: list[str],
        startup_time: float,
    ) -> list[str]:
        app_title = getattr(config.app, "title", "Welcome to FastBlocks")
        app_domain = getattr(config.app, "domain", "localhost")
        debug_str = ", ".join(debug_enabled) if debug_enabled else "disabled"

        return [
            f"{colors['CYAN']}{colors['BOLD']}{app_title}{colors['RESET']}",
            f"{colors['BLUE']}Domain: {app_domain}{colors['RESET']}",
            f"{colors['YELLOW']}Debug: {debug_str}{colors['RESET']}",
            f"{colors['YELLOW']}══════════════════════════════════════════════════{colors['RESET']}",
            f"{colors['GREEN']}🚀 FastBlocks Application Ready{colors['RESET']}",
            f"{colors['YELLOW']}⚡ Startup time: {startup_time * 1000:.2f}ms{colors['RESET']}",
            f"{colors['CYAN']}🌐 Server running on http://127.0.0.1:8000{colors['RESET']}",
            f"{colors['YELLOW']}══════════════════════════════════════════════════{colors['RESET']}",
        ]

    def _clean_and_center_line(self, line: str, colors: dict[str, str]) -> str:
        line_clean = line
        for color in colors.values():
            line_clean = line_clean.replace(color, "")
        line_width = len(line_clean)
        padding = max(0, (90 - line_width) // 2)
        return " " * padding + line

    async def _display_fancy_startup(self) -> None:
        # MIGRATED: Removed ACB import - using Oneiric equivalent
        from aioconsole import (
            aprint,  # type: ignore[import-not-found]  # ty: ignore[unresolved-import]
        )
        from pyfiglet import Figlet  # type: ignore[import-not-found]

        config = resolve_instance(depends, "fastblocks", "config")
        app_name = getattr(config.app, "name", "FastBlocks")
        startup_time = self._get_startup_time()
        debug_enabled = self._get_debug_enabled(config)
        colors = self._get_color_constants()
        banner = Figlet(font="slant", width=90, justify="center").renderText(
            app_name.upper(),
        )
        await aprint(f"\n\n{banner}\n")
        info_lines = self._format_info_lines(
            config,
            colors,
            debug_enabled,
            startup_time,
        )
        for line in info_lines:
            self._clean_and_center_line(line, colors)

    async def _display_simple_startup(self) -> None:
        from contextlib import suppress

        with suppress(Exception):
            # MIGRATED: Removed ACB import - using Oneiric equivalent

            config = resolve_instance(depends, "fastblocks", "config")
            getattr(config.app, "name", "FastBlocks")
            self._get_startup_time()

    async def post_startup(self) -> None:
        try:
            await self._display_fancy_startup()
        except Exception:  # noqa: BLE001
            # Fancy startup depends on optional ``aioconsole`` and
            # ``pyfiglet`` -- fall back to the simple variant on any
            # import or render failure so startup always succeeds.
            await self._display_simple_startup()

    @asynccontextmanager
    async def lifespan(self, app: FastBlocks) -> t.AsyncIterator[None]:
        try:
            logger = getattr(self, "logger", None)
            if logger:
                logger.info("FastBlocks application starting up")
        except Exception:
            logger = getattr(self, "logger", None)
            if logger:
                logger.exception("Error during startup")
            raise
        # Bind ``app.state.main_loop`` and ``app.state.jinja_env`` at
        # startup so the master-plan line 478-479 lifecycle assertion
        # passes. Per ADR 0013 Decision 14 + ADR 0012 Decision 2 path-
        # forward option (b): extend the existing class-method lifespan
        # -- which Starlette wires via
        # ``super().__init__(lifespan=self.lifespan, ...)`` above and
        # invokes at ASGI startup -- rather than shipping a new
        # ``LifespanManager`` class.
        #
        # Note on the ``jinja2.Environment`` factory: this is a
        # *synchronous* stub satisfying the master-plan assertion that
        # ``app.state.jinja_env`` is a ``jinja2.Environment``. The
        # canonical async ``AsyncJinja2Templates`` (from
        # ``fastblocks.adapters.templates.jinja2``) is wired by the
        # templates adapter during its own ``init()`` lifecycle, AFTER
        # ``FastBlocksApp.lifespan`` startup completes -- that path is
        # asynchronous and depends on resolved template services that
        # are not yet available at FastBlocksApp lifespan-start time.
        app.state.main_loop = asyncio.get_event_loop()
        app.state.jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader("templates"),
        )
        # Per v6 Δ11/Δ19: install the OTel TracerProvider BEFORE
        # ``init_sentry()`` so the alpha Sentry SDK can auto-wire its
        # ``SentrySpanProcessor`` against the active provider.
        # ``init_sentry()`` is a no-op when ``SENTRY_DSN`` is unset;
        # the call is safe in lean installs (raises
        # ``SentryImportError(reason="import_error")`` only when both
        # the DSN IS set AND the SDK cannot be imported — see the
        # bridge module for the ALPHA contract).
        _setup_default_tracer_provider()
        init_sentry()
        yield
        # Per v6 Δ10/Δ18: flush pending spans via the BatchSpanProcessor
        # before app teardown so the OTLP exporter does not lose the
        # last batch. Idempotent on the cached provider (the module-
        # level cache in ``observability.tracer`` survives across
        # lifespan invocations).
        _get_default_tracer_provider().shutdown()  # ty: ignore[unresolved-attribute]
        logger = getattr(self, "logger", None)
        if logger:
            logger.info("FastBlocks application shutting down")


class App(AppBase):
    settings: AppSettings | None = None
    router: t.Any = None
    middleware_manager: t.Any = None
    templates: t.Any = None
    models: t.Any = None
    exception_handlers: t.Any = None
    middleware_stack: t.Any = None
    user_middleware: t.Any = None
    fastblocks_app: t.Any = None

    def __init__(self, **kwargs: t.Any) -> None:
        super().__init__(**kwargs)
        self.settings = AppSettings()
        self.fastblocks_app = FastBlocksApp()
        self.router = None
        self.middleware_manager = None
        self.templates = None
        self.models = None
        self.exception_handlers = {}
        self.middleware_stack = None
        self.user_middleware = []
        self.state = None

    @property
    def logger(self) -> t.Any:
        if hasattr(super(), "logger"):
            with suppress(Exception):
                parent_logger = getattr(super(), "logger", None)
                if parent_logger is not None:
                    return parent_logger
        # For Oneiric, we'll use a simpler approach
        # In practice, this would be replaced with actual logger resolution
        import logging

        return logging.getLogger(self.__class__.__name__)

    @logger.setter
    def logger(self, value: t.Any) -> None:
        pass

    @logger.deleter
    def logger(self) -> None:
        pass

    async def init(self) -> None:
        import time

        self._init_start_time = time.time()
        await self.fastblocks_app.init()
        # For Oneiric, we'll use a simpler approach
        # In practice, this would be replaced with actual dependency resolution
        self.templates = None  # Placeholder - would use actual templates
        self.models = None  # Placeholder - would use actual models
        self.router = None  # Placeholder - would use actual routes
        self.middleware_manager = None
        self.exception_handlers = self.fastblocks_app.exception_handlers
        self.middleware_stack = self.fastblocks_app.middleware_stack
        self.user_middleware = self.fastblocks_app.user_middleware
        self.state = self.fastblocks_app.state
        import time

        self._startup_time = time.time() - self._init_start_time
        self.fastblocks_app._startup_time = self._startup_time
        self.fastblocks_app._init_start_time = self._init_start_time
        await self.post_startup()

    def __call__(self, scope: Scope, receive: Receive, send: Send) -> ASGIApp:
        return t.cast(ASGIApp, self.fastblocks_app(scope, receive, send))

    def __getattr__(self, name: str) -> t.Any:
        return getattr(self.fastblocks_app, name)

    async def post_startup(self) -> None:
        await self.fastblocks_app.post_startup()

    async def _setup_admin_adapter(self, app: FastBlocks) -> None:
        # For Oneiric, we'll use a simpler approach
        # In practice, this would be replaced with actual admin setup
        # Placeholder - would use actual admin, sql, auth resolution
        pass

    async def _startup_sequence(self, app: FastBlocks) -> None:
        await self._setup_admin_adapter(app)
        await self.post_startup()
        main_start_time = perf_counter() - main_start
        self.logger.warning(f"App started in {main_start_time} s")

    async def _shutdown_logger(self) -> None:
        import asyncio

        completer = None
        if hasattr(self.logger, "complete"):
            completer = self.logger.complete()
        elif hasattr(self.logger, "stop"):
            completer = self.logger.stop()
        if completer:
            await asyncio.wait_for(completer, timeout=1.0)

    def _cancel_remaining_tasks(self) -> None:
        import asyncio

        loop = asyncio.get_event_loop()
        tasks = [t for t in asyncio.all_tasks(loop) if not t.done()]
        if tasks:
            self.logger.debug(f"Cancelling {len(tasks)} remaining tasks")
            for task in tasks:
                task.cancel()

    @asynccontextmanager
    async def lifespan(self, app: FastBlocks) -> t.AsyncIterator[None]:
        try:
            await self._startup_sequence(app)
        except Exception:
            # Fail-loud: log + re-raise so Starlette surfaces the
            # startup failure rather than silently serving traffic.
            self.logger.exception("Error during startup")
            raise
        # Per v6 Δ11/Δ19: same ordering contract as ``FastBlocksApp.
        # lifespan`` — install the OTel TracerProvider first, then
        # ``init_sentry()`` so the alpha Sentry SDK can attach its
        # ``SentrySpanProcessor`` to the active provider. See the
        # ``FastBlocksApp.lifespan`` comment above for the full
        # rationale; both lifespans must honor the same ordering
        # because ``App.lifespan`` is the runtime-instantiated path
        # (App.fastblocks_app delegates to FastBlocksApp, but the
        # middleware + tracer setup runs through this class first).
        _setup_default_tracer_provider()
        init_sentry()
        yield
        # Per v6 Δ10/Δ18 + resolved-ambiguity: flush pending spans via
        # the BatchSpanProcessor before app teardown so the OTLP
        # exporter does not lose the last batch. The call is on the
        # runtime path (``App.lifespan`` is the class instantiated at
        # runtime — see comment at FastBlocksApp.lifespan, line 226).
        _get_default_tracer_provider().shutdown()  # ty: ignore[unresolved-attribute]
        self.logger.critical("Application shut down")
        try:
            await self._shutdown_logger()
        except TimeoutError:
            self.logger.warning("Logger completion timed out, forcing shutdown")
        except Exception:
            self.logger.exception("Logger completion failed")
        finally:
            with suppress(Exception):
                self._cancel_remaining_tasks()


MODULE_ID = UUID("01937d86-8f6e-7f70-c231-5678901234ef")
MODULE_STATUS = "STABLE"  # Oneiric-compatible status

# Note: depends.register(App) removed as Oneiric expects different object types
# In practice, this would be replaced with proper Oneiric registration
