"""Verify the autouse fixture in conftest.py swaps the TracerProvider
per test.

Per ADR 0013 Decision 12: OTel's TracerProvider is process-global.
A SpanProcessor installed in test 1 persists into tests 2..N unless
explicitly torn down. The autouse fixture in `conftest.py` swaps
in a fresh `TracerProvider` per test, then restores the previous
one on teardown.

This regression test installs a SpanProcessor in test_a and asserts
in test_b that the active TracerProvider is a *different object* —
i.e. the fixture swapped it. Without the fixture, both tests see the
same proxy/SDK provider.

Note on identity comparison: the previous version stored ``id(provider)``
in ``_PROVIDERS_SEEN`` and compared integers. That is unstable because
CPython may recycle the memory address of the previous test's
``TracerProvider`` (which the autouse teardown drops) into the next
test's ``TracerProvider`` — distinct objects with equal ``id()``.
The fix stores the provider object itself and uses the ``is``
operator (Python's true identity check, which cannot be tricked by
memory-address reuse because it checks the object, not the address).
"""
from __future__ import annotations

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)


# Cross-test state: each invocation of `install_span_processor`
# appends the live provider reference to this list. pytest collects
# test_a before test_b in this file, so list[0] is test_a's provider.
# We keep the OBJECT reference (not ``id(...)``) so identity comparison
# survives CPython's memory-address recycling — see module docstring.
_PROVIDERS_SEEN: list[object] = []


@pytest.fixture
def install_span_processor() -> dict[str, object]:
    """Install a SpanProcessor on the fixture-managed TracerProvider.

    Captures ``trace.get_tracer_provider()`` so test_b can assert that
    the provider was swapped between tests. Without the autouse fixture
    in ``conftest.py``, both tests observe the same provider instance
    (``is`` comparison equal) — regression.
    """
    provider = trace.get_tracer_provider()
    exporter = InMemorySpanExporter()
    span_processor = SimpleSpanProcessor(exporter)
    provider.add_span_processor(span_processor)
    info: dict[str, object] = {
        "exporter": exporter,
        "provider": provider,
    }
    _PROVIDERS_SEEN.append(provider)
    try:
        yield info
    finally:
        with __import__("contextlib").suppress(Exception):
            provider.shutdown()


def test_a_installs_processor(install_span_processor: dict[str, object]) -> None:
    """test_a installs a SpanProcessor on the fixture-managed provider.

    Sanity check: the fixture's captured provider is the same object as
    the currently-active TracerProvider (``is`` comparison), proving
    the test ran inside the autouse-fixture-swapped provider.
    """
    info = install_span_processor
    assert info["exporter"] is not None
    assert info["provider"] is trace.get_tracer_provider()


def test_b_provider_is_fresh_after_test_a(
    install_span_processor: dict[str, object],
) -> None:
    """The autouse fixture must swap the TracerProvider between tests.

    test_a appended ``_PROVIDERS_SEEN[0]`` (the live provider object).
    If the fixture ran, this test observes a *different* provider
    object (``is not``). If the fixture did NOT run, both objects are
    equal — regression signal.
    """
    assert len(_PROVIDERS_SEEN) >= 2, (
        "pytest collection order assumption broken; "
        "test_a must run before test_b"
    )
    provider_a: object = _PROVIDERS_SEEN[0]
    provider_b: object = trace.get_tracer_provider()
    assert provider_b is not provider_a, (
        "TracerProvider swap did NOT happen between tests; "
        "test pollution will follow"
    )
