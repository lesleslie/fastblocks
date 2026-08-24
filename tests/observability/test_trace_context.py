"""Tests for fastblocks.observability.trace_context public API.

Per Δ36 + Δ33: trace_context exposes ``exemplar()`` that returns
``{"trace_id": str, "span_id": str}`` from a single contextvars read
when a context is bound, or ``None`` when no context is bound. The
returned dict flows into ``Histogram.observe(*, exemplar=...)``.

The module also pins alias identity between the long-form public names
``get_trace_context`` / ``set_trace_context`` / ``reset_trace_context``
(exposed via ``fastblocks.observability.__init__``) and the short-form
module-level ``get`` / ``set`` / ``reset`` — they are the same callable
objects, not just behaviorally equivalent.
"""
from __future__ import annotations

import re

from fastblocks.observability import trace_context as tc


_HEX_RE = re.compile(r"^[0-9a-f]+$")


def test_set_returns_token() -> None:
    """`set` returns the ContextVar Token so callers can pair with `reset`."""
    ctx = tc.TraceContext(trace_id="abc", span_id="def")
    token = tc.set(ctx)
    try:
        # Token is opaque (ContextVar.set return value); the contract is
        # only that it's truthy and accepted by reset().
        assert token is not None
    finally:
        tc.reset(token)
    # After reset, get() returns None (default for unbound ContextVar).
    assert tc.get() is None


def test_reset_token_clears() -> None:
    """`reset(token)` removes the typed ContextVar binding."""
    ctx = tc.TraceContext(trace_id="abc", span_id="def")
    token = tc.set(ctx)
    assert tc.get() is not None
    tc.reset(token)
    assert tc.get() is None


def test_exemplar_returns_dict_when_context_bound() -> None:
    """After `set(...)`, `exemplar()` returns `{trace_id, span_id}`."""
    ctx = tc.TraceContext(trace_id="abc123", span_id="def456")
    token = tc.set(ctx)
    try:
        result = tc.exemplar()
        assert result is not None
        assert result == {"trace_id": "abc123", "span_id": "def456"}
    finally:
        tc.reset(token)


def test_exemplar_returns_none_when_no_context_bound() -> None:
    """`exemplar()` returns None when no set() has occurred."""
    # No prior set: get() default is None → exemplar() short-circuits.
    assert tc.get() is None
    assert tc.exemplar() is None


def test_exemplar_after_reset_returns_none() -> None:
    """`exemplar()` returns None after the binding has been reset."""
    ctx = tc.TraceContext(trace_id="abc", span_id="def")
    token = tc.set(ctx)
    assert tc.exemplar() is not None
    tc.reset(token)
    assert tc.exemplar() is None


def test_alias_identity_get() -> None:
    """`get_trace_context` is the same callable as the module `get`."""
    assert tc.get_trace_context is tc.get


def test_alias_identity_set() -> None:
    """`set_trace_context` is the same callable as the module `set`."""
    assert tc.set_trace_context is tc.set


def test_alias_identity_reset() -> None:
    """`reset_trace_context` is the same callable as the module `reset`."""
    assert tc.reset_trace_context is tc.reset


def test_exemplar_ids_are_hex_strings() -> None:
    """Trace IDs and span IDs returned by `exemplar()` are hex strings.

    Per OTLP convention (and what `Histogram.observe` exemplars expect),
    the values must be hex-encoded strings, not raw integers.
    """
    # Use realistic OTLP-shaped hex values: 32-char trace_id, 16-char span_id.
    trace_id = "0af7651916cd43dd8448eb211c80319c"
    span_id = "b7ad6b7169203331"
    ctx = tc.TraceContext(trace_id=trace_id, span_id=span_id)
    token = tc.set(ctx)
    try:
        result = tc.exemplar()
        assert result is not None
        assert isinstance(result["trace_id"], str)
        assert isinstance(result["span_id"], str)
        assert _HEX_RE.match(result["trace_id"]), (
            f"trace_id is not pure hex: {result['trace_id']!r}"
        )
        assert _HEX_RE.match(result["span_id"]), (
            f"span_id is not pure hex: {result['span_id']!r}"
        )
        # Round-trip the bound values.
        assert result["trace_id"] == trace_id
        assert result["span_id"] == span_id
    finally:
        tc.reset(token)


def test_exemplar_does_not_mutate_context() -> None:
    """Calling `exemplar()` does not consume the token or unbind the context."""
    ctx = tc.TraceContext(trace_id="abc", span_id="def")
    token = tc.set(ctx)
    try:
        first = tc.exemplar()
        second = tc.exemplar()
        third = tc.exemplar()
        # Repeated reads return equal payloads without unbinding.
        assert first == second == third
        # Context remains bound — get() still surfaces the same TraceContext.
        bound = tc.get()
        assert bound is not None
        assert bound.trace_id == "abc"
        assert bound.span_id == "def"
    finally:
        tc.reset(token)


def test_exemplar_dict_has_exactly_two_keys() -> None:
    """`exemplar()` returns a dict with exactly `trace_id` and `span_id`.

    `Histogram.observe(*, exemplar=...)` only consumes those two keys.
    Anything extra would either be ignored or leak internal state.
    """
    ctx = tc.TraceContext(trace_id="abc", span_id="def")
    token = tc.set(ctx)
    try:
        result = tc.exemplar()
        assert result is not None
        assert set(result.keys()) == {"trace_id", "span_id"}
    finally:
        tc.reset(token)


def test_exemplar_does_not_include_parent_span_id() -> None:
    """The exemplar dict excludes `parent_span_id` (Δ33 surface only)."""
    ctx = tc.TraceContext(
        trace_id="abc",
        span_id="def",
        parent_span_id="xyz",
    )
    token = tc.set(ctx)
    try:
        result = tc.exemplar()
        assert result is not None
        assert "parent_span_id" not in result
    finally:
        tc.reset(token)
