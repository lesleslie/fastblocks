"""Tests for the ``/metrics`` HTTP endpoint.

Per Δ42 + P1-3 + Δ9: the ``/metrics`` route lives on ``FastBlocksApp``
(Starlette subclass), serves ``application/openmetrics-text`` or
``text/plain`` per the Accept header, increments a dispatch counter per
request, and wraps the encoder/generate call in a try/except that
increments an error counter on failure.

The 4-case Accept-header matrix verified by this module:

* ``Accept: application/openmetrics-text`` -> OpenMetrics content type
* ``Accept: text/plain`` -> text/plain legacy content type
* ``Accept: */*`` -> OpenMetrics (per Δ42 default)
* (missing Accept header) -> OpenMetrics (per Δ42 default)

Note: ``prometheus_client.exposition.choose_encoder`` defaults ``*/*``
and missing Accept to the legacy text/plain format. The FastBlocks
``/metrics`` handler deliberately overrides that default so the
OpenMetrics content type wins for ``*/*`` and missing headers per Δ42.

Test approach: the FastBlocks app's middleware stack has a pre-existing
shape bug (``fastblocks/applications.py:412`` expects 3-tuples but the
system middleware list holds 2-tuples) that prevents ``TestClient`` from
exercising the full request path. To keep this test file scoped to
Task 9's behavior contract, the handler is invoked directly as a
callable with a Starlette ``Request`` constructed from a synthetic ASGI
scope — the route registration contract is verified separately by
asserting the handler IS bound on a ``FastBlocksApp`` instance.

Process-global counter isolation: the two counters are registered
against the default ``prometheus_client.REGISTRY`` at module-load time
in ``fastblocks.adapters.app.default``. Tests therefore read the
counter via ``prometheus_client.REGISTRY.get_sample_value`` which
returns the cumulative value across the test process — the tests
capture a baseline BEFORE the request and assert the DELTA equals 1.
This avoids relying on absolute counts (which would be fragile if any
other test ran first and incremented the same counter).
"""
from __future__ import annotations

import pytest
from starlette.requests import Request

# Counter names are pinned by ``__init__`` in ``fastblocks.adapters.app.default``.
# These MUST match the names declared in that module exactly.
DISPATCH_COUNTER_NAME = "fastblocks_metrics_endpoint_dispatch_total"
ERROR_COUNTER_NAME = "fastblocks_metrics_endpoint_errors_total"


def _import_default_app_module():
    """Return the cached ``fastblocks.adapters.app.default`` module.

    The module-level Counter declarations register with the process-
    global ``ObservabilityRegistry`` at import time, so re-importing
    via ``importlib.reload`` raises ``MetricNameCollisionError``. The
    Counter is the same instance across all imports in the same
    process — we just use the cached import. The function exists for
    symmetry with the test suites that reload modules; it is a thin
    wrapper so the test bodies stay readable.
    """
    import fastblocks.adapters.app.default as app_mod

    return app_mod


def _make_request(accept_header: str | None) -> Request:
    """Build a Starlette ``Request`` from a synthetic ASGI scope.

    ``accept_header=None`` simulates a request that omits the Accept
    header entirely (some HTTP clients omit it). Other values pass
    through to the ``accept`` header verbatim.
    """
    headers: list[tuple[bytes, bytes]] = []
    if accept_header is not None:
        headers.append((b"accept", accept_header.encode("latin-1")))
    scope: dict[str, object] = {
        "type": "http",
        "method": "GET",
        "path": "/metrics",
        "raw_path": b"/metrics",
        "query_string": b"",
        "headers": headers,
    }

    async def _receive() -> dict[str, object]:
        return {"type": "http.request", "body": b"", "more_body": False}

    return Request(scope, _receive)


def _counter_value(counter_name: str, labels: dict[str, str]) -> float:
    """Return the current cumulative value of a Prometheus counter sample.

    ``prometheus_client.REGISTRY.get_sample_value`` returns ``None`` when
    no sample exists yet (the labelled child has never been observed).
    We coerce ``None`` -> 0.0 so callers can subtract baselines without a
    None-check.

    Note on naming: ``Counter(name=...)`` registers a collector with
    ``name`` verbatim (no automatic ``_total`` suffix). The sample
    value lookup, however, accepts the ``_total`` suffix form per the
    Prometheus exposition convention. ``get_sample_value`` already
    handles that — passing the literal counter name (with the trailing
    ``_total`` from our declarations) returns the cumulative count.
    """
    from prometheus_client import REGISTRY

    sample = REGISTRY.get_sample_value(counter_name, labels=labels)
    return 0.0 if sample is None else float(sample)


# ---------------------------------------------------------------------------
# 0. Route registration contract — /metrics is bound on FastBlocksApp
# ---------------------------------------------------------------------------


def test_metrics_route_is_bound_on_fastblocks_app() -> None:
    """The /metrics route must be registered on FastBlocksApp at __init__.

    Starlette routes live on ``app.router.routes``; each route has a
    ``.path`` attribute. We assert at least one route maps to
    ``/metrics`` so a future regression (e.g. someone removes the
    ``add_route`` from ``FastBlocksApp.__init__``) surfaces here.
    """
    app_mod = _import_default_app_module()
    app = app_mod.FastBlocksApp()
    paths = [getattr(route, "path", None) for route in app.router.routes]
    assert "/metrics" in paths, (
        f"FastBlocksApp must register a /metrics route; current routes: {paths!r}"
    )


# ---------------------------------------------------------------------------
# 1. 4-case Accept-header matrix
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("accept_header", "expected_content_type"),
    [
        (
            "application/openmetrics-text",
            "application/openmetrics-text; version=1.0.0; charset=utf-8",
        ),
        ("text/plain", "text/plain; version=0.0.4; charset=utf-8"),
        ("*/*", "application/openmetrics-text; version=1.0.0; charset=utf-8"),
        (None, "application/openmetrics-text; version=1.0.0; charset=utf-8"),
    ],
    ids=[
        "openmetrics",
        "text_plain_legacy",
        "wildcard_defaults_to_openmetrics",
        "missing_defaults_to_openmetrics",
    ],
)
def test_metrics_endpoint_content_type_matrix(
    accept_header: str | None,
    expected_content_type: str,
) -> None:
    """Per Δ42: 4-case Accept-header matrix produces correct content type."""
    app_mod = _import_default_app_module()
    handler = app_mod.metrics_endpoint

    request = _make_request(accept_header)
    response = handler(request)

    assert response.status_code == 200, (
        f"GET /metrics returned {response.status_code} for Accept={accept_header!r}"
    )
    assert response.headers["content-type"] == expected_content_type, (
        f"Accept={accept_header!r} produced content-type={response.headers['content-type']!r}, "
        f"expected {expected_content_type!r}"
    )


# ---------------------------------------------------------------------------
# 2. Body is non-empty (real metrics returned)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "accept_header",
    [
        "application/openmetrics-text",
        "text/plain",
        "*/*",
        None,
    ],
)
def test_metrics_endpoint_body_non_empty(accept_header: str | None) -> None:
    """Per brief: body must be non-empty bytes for every matrix case."""
    app_mod = _import_default_app_module()
    handler = app_mod.metrics_endpoint

    request = _make_request(accept_header)
    response = handler(request)

    assert response.status_code == 200
    assert len(response.body) > 0, (
        f"GET /metrics returned empty body for Accept={accept_header!r}"
    )


# ---------------------------------------------------------------------------
# 3. Dispatch counter increments per request
# ---------------------------------------------------------------------------


def test_metrics_endpoint_dispatch_counter_increments() -> None:
    """Per Δ39-ε: dispatch counter bumps by 1 per /metrics request."""
    app_mod = _import_default_app_module()
    handler = app_mod.metrics_endpoint

    # Baseline: read current dispatch counter value for the openmetrics
    # label BEFORE the request. The counter is module-level, so it
    # accumulates across tests in the same process.
    label_value = "application/openmetrics-text"
    before = _counter_value(DISPATCH_COUNTER_NAME, {"accept_header": label_value})

    request = _make_request(label_value)
    response = handler(request)
    assert response.status_code == 200

    after = _counter_value(DISPATCH_COUNTER_NAME, {"accept_header": label_value})
    assert after - before == 1.0, (
        f"dispatch counter should bump by 1; before={before}, after={after}"
    )


def test_metrics_endpoint_dispatch_counter_for_wildcard() -> None:
    """Bump dispatch counter for the wildcard Accept-header path.

    Per Δ42 default, ``*/*`` produces OpenMetrics; the counter label
    records the wildcard Accept header verbatim.
    """
    app_mod = _import_default_app_module()
    handler = app_mod.metrics_endpoint

    before = _counter_value(DISPATCH_COUNTER_NAME, {"accept_header": "*/*"})

    request = _make_request("*/*")
    response = handler(request)
    assert response.status_code == 200

    after = _counter_value(DISPATCH_COUNTER_NAME, {"accept_header": "*/*"})
    assert after - before == 1.0, (
        f"dispatch counter for */* should bump by 1; before={before}, after={after}"
    )


def test_metrics_endpoint_dispatch_counter_for_missing_accept() -> None:
    """Bump dispatch counter with the ``missing`` label for omitted Accept.

    Per Δ42 default, a missing Accept header produces OpenMetrics; the
    counter label records the omission via the bounded ``missing`` value.
    """
    app_mod = _import_default_app_module()
    handler = app_mod.metrics_endpoint

    before = _counter_value(DISPATCH_COUNTER_NAME, {"accept_header": "missing"})

    request = _make_request(None)
    response = handler(request)
    assert response.status_code == 200

    after = _counter_value(DISPATCH_COUNTER_NAME, {"accept_header": "missing"})
    assert after - before == 1.0, (
        f"dispatch counter for missing Accept should bump by 1; "
        f"before={before}, after={after}"
    )


# ---------------------------------------------------------------------------
# 4. Error counter increments when encoder raises
# ---------------------------------------------------------------------------


def test_metrics_endpoint_error_counter_on_encoder_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bump the error counter on encoder-selection failure (P1-3).

    Per P1-3, when ``_choose_encoder`` raises, the route increments
    ``fastblocks_metrics_endpoint_errors_total{reason}`` with the
    exception class name and re-raises so Starlette can render a 500.
    """
    app_mod = _import_default_app_module()
    handler = app_mod.metrics_endpoint

    def _raise_encoder(accept_header: str) -> tuple[object, str]:
        raise RuntimeError("simulated encoder failure")

    monkeypatch.setattr(
        app_mod,
        "_choose_encoder",
        _raise_encoder,
    )

    before = _counter_value(ERROR_COUNTER_NAME, {"reason": "RuntimeError"})

    # The handler is expected to re-raise so the caller (Starlette) can
    # render a 500. We use pytest.raises to assert the re-raise while
    # verifying the error counter moved.
    request = _make_request("*/*")
    with pytest.raises(RuntimeError, match="simulated encoder failure"):
        handler(request)

    after = _counter_value(ERROR_COUNTER_NAME, {"reason": "RuntimeError"})
    assert after - before == 1.0, (
        f"error counter should bump by 1 on encoder exception; before={before}, after={after}"
    )


# ---------------------------------------------------------------------------
# 5. Regression: provider.shutdown() still called once per lifespan exit
# ---------------------------------------------------------------------------


def test_metrics_endpoint_does_not_call_provider_shutdown_per_request() -> None:
    """Confirm /metrics handler does NOT trigger provider.shutdown per request.

    Per Δ10, ``provider.shutdown()`` lives in the lifespan (Task 3),
    not in the route handler. A /metrics request must NEVER touch the
    tracer provider so the BatchSpanProcessor shutdown chain stays in
    the lifespan-only path.
    """
    app_mod = _import_default_app_module()
    handler = app_mod.metrics_endpoint

    # Use the global default tracer provider from observability.tracer.
    # Its ``_provider`` cache is module-level; monkey-patch ``shutdown``
    # with a counting spy and verify the handler path doesn't touch it.
    from fastblocks.observability import tracer as tracer_mod

    provider = tracer_mod.get_default_tracer_provider()
    original_shutdown = provider.shutdown

    call_count = {"n": 0}

    def _counting_shutdown() -> None:
        call_count["n"] += 1

    provider.shutdown = _counting_shutdown  # type: ignore[assignment,method-assign]

    try:
        # Three sequential handler invocations must not touch the
        # provider's shutdown.
        for _ in range(3):
            request = _make_request("*/*")
            response = handler(request)
            assert response.status_code == 200

        assert call_count["n"] == 0, (
            f"provider.shutdown() must not be called by /metrics handler; "
            f"observed {call_count['n']} calls"
        )
    finally:
        provider.shutdown = original_shutdown  # type: ignore[assignment,method-assign]
