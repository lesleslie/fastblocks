"""Tests for fastblocks.observability.loggers.

Per v6 Δ40 + log_correlation mapping: structlog Logger bound to Oneiric
settings, pre-configured with ``merge_contextvars`` + ``JSONRenderer``,
with TraceContext's contextvars auto-flowing into every log event.

Uses ``structlog.testing.capture_logs()`` to capture event dicts BEFORE
rendering. With ``JSONRenderer`` configured at runtime, those event
dicts serialize to JSON; the test demonstrates the configuration is in
place without coupling to a JSON library.
"""
from __future__ import annotations

import structlog
from fastblocks.observability.loggers import (
    configure_logging,
    get_logger,
)


def test_get_logger_returns_bound_logger() -> None:
    """Per brief: get_logger(name) -> structlog.stdlib.BoundLogger."""
    log = get_logger("mymod")
    # BoundLogger has .info / .warning / .exception etc.
    assert hasattr(log, "info")
    assert hasattr(log, "warning")
    assert hasattr(log, "exception")


def test_logger_emits_event_with_kwargs() -> None:
    """Per brief: get_logger("mymod").info("event", request_id="abc") emits JSON.

    Uses structlog.testing.capture_logs() to capture event dicts before
    rendering. The captured dict carries ``event == "event"`` and the
    kwargs (``request_id == "abc"``). With ``JSONRenderer`` configured
    at runtime, those dicts serialize to JSON — the test demonstrates
    the configuration is in place without coupling to a JSON lib.
    """
    configure_logging()
    with structlog.testing.capture_logs() as captured:
        get_logger("mymod").info("event", request_id="abc")

    assert captured, "capture_logs() should record at least one event"
    assert any(
        record.get("event") == "event" and record.get("request_id") == "abc"
        for record in captured
    ), f"expected event dict with request_id='abc'; got: {captured!r}"


def test_configure_logging_includes_merge_contextvars_and_json_renderer() -> None:
    """Per 'log_correlation mapping': merge_contextvars + JSONRenderer wired.

    Inspects the live processor chain to verify both processors are in
    place. This is the wiring test for the brief's contract: TraceContext
    fields auto-flow into every log emission via merge_contextvars, and
    Oneiric's log aggregator receives structured JSON via JSONRenderer.
    """
    configure_logging()
    config = structlog.get_config()
    processors = list(config["processors"])

    assert any(p is structlog.contextvars.merge_contextvars for p in processors), (
        "configure_logging() must include structlog.contextvars.merge_contextvars "
        "so TraceContext fields auto-flow into log lines; got processors: "
        f"{[getattr(p, '__name__', repr(p)) for p in processors]}"
    )
    # JSONRenderer is a class; structlog.configure instantiates it, so the
    # processor list holds INSTANCES. Use isinstance for the membership check.
    assert any(isinstance(p, structlog.processors.JSONRenderer) for p in processors), (
        "configure_logging() must include structlog.processors.JSONRenderer "
        "so Oneiric's log aggregator receives structured JSON; got: "
        f"{[getattr(p, '__name__', repr(p)) for p in processors]}"
    )


def test_configure_logging_is_idempotent() -> None:
    """Per brief: 'lazy config so app-startup configures once'.

    Calling configure_logging() twice must not crash or replace the
    first configuration with a no-op duplicate processor chain.
    """
    configure_logging()
    first_config = structlog.get_config()
    configure_logging()
    second_config = structlog.get_config()
    assert first_config == second_config, (
        "configure_logging() must be idempotent; config changed across calls"
    )


def test_logger_does_not_use_error_with_exc_info() -> None:
    """Per Δ40: prefer logger.exception(...) over logger.error(..., exc_info=True).

    Source-level check via AST ensures the production module does not
    regress to the discouraged pattern. Both forms serialize to the same
    on-the-wire shape, but ``logger.exception`` is the idiomatic stdlib
    contract that structlog honors identically.
    """
    import ast
    from pathlib import Path

    # Resolve via __file__ so the path follows the test, not the cwd.
    # Test file lives at <repo>/tests/observability/test_loggers.py
    #   parents[0] = observability
    #   parents[1] = tests
    #   parents[2] = <repo>  (works in both worktree and main checkout)
    target = Path(__file__).resolve().parents[2] / "fastblocks" / "observability" / "loggers.py"
    source = target.read_text()
    tree = ast.parse(source)
    offenders: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        # Detect <anything>.error(..., exc_info=True) — anything that
        # ends in .error() and passes exc_info=True as a kwarg.
        if not isinstance(func, ast.Attribute) or func.attr != "error":
            continue
        for kw in node.keywords:
            if kw.arg == "exc_info" and (
                kw.value is None or (
                    isinstance(kw.value, ast.Constant) and kw.value.value is True
                )
            ):
                offenders.append(
                    f"line {node.lineno}: logger.error(..., exc_info=True)"
                )
    assert not offenders, (
        "production code must use logger.exception(...) instead of "
        f"logger.error(..., exc_info=True); offenders: {offenders}"
    )


def test_module_declares_all() -> None:
    """Per module pattern: every public module declares __all__."""
    import fastblocks.observability.loggers as loggers_mod

    assert hasattr(loggers_mod, "__all__"), "loggers.py must declare __all__"
    assert "get_logger" in loggers_mod.__all__
    assert "configure_logging" in loggers_mod.__all__


def test_structlog_pinned_in_observability_dep_group() -> None:
    """Pin Δ40 contract: lean installs can resolve structlog via the observability group.

    Without this dep entry, ``uv sync --no-group dev`` cannot import
    ``fastblocks.observability.loggers`` (the ``MissingDependencyError``
    guard correctly fires) and the wire-up is unreachable. The pin
    shape ``~=X.Y`` follows Global Constraint line 25.
    """
    import tomllib
    from pathlib import Path

    pyproject = tomllib.loads(Path("pyproject.toml").read_text())
    group = pyproject["dependency-groups"]["observability"]
    matches = [
        entry for entry in group
        if entry.split("[")[0].split("~")[0].split("=")[0].strip() == "structlog"
    ]
    assert matches, (
        "structlog must be pinned in the [dependency-groups].observability "
        "table so lean installs can wire up fastblocks.observability.loggers; "
        f"observed group: {group!r}"
    )
    # Single pin, ~=X.Y shape per Global Constraint line 25.
    assert len(matches) == 1, f"expected exactly one structlog pin; got {matches!r}"
    assert "~=" in matches[0], (
        f"structlog pin must use compatible-release clause '~=' per "
        f"Global Constraint line 25; got {matches[0]!r}"
    )
