"""Verify the autouse fixture in conftest.py swaps the TracerProvider
per test.

Per ADR 0013 Decision 12: OTel's TracerProvider is process-global.
A SpanProcessor installed in test 1 persists into tests 2..N unless
explicitly torn down. The autouse fixture in `conftest.py` swaps
in a fresh `TracerProvider` per test, then restores the previous
one on teardown.

This regression test installs a SpanProcessor in test_a and asserts
in test_b that the active TracerProvider has a *different* id() — i.e.
the fixture swapped it. Without the fixture, both tests see the
same proxy/SDK provider and id() comparison is equal (regression).
"""
from __future__ import annotations

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)


# Cross-test state: each invocation of `install_span_processor`
# appends the current provider's id() to this list. pytest collects
# test_a before test_b in this file, so list[0] is test_a's id().
_PROVIDERS_SEEN: list[int] = []


@pytest.fixture
def install_span_processor() -> dict[str, object]:
    """Install a SpanProcessor on the fixture-managed TracerProvider.

    Captures ``id(trace.get_tracer_provider())`` so test_b can assert
    that the provider was swapped between tests. Without the autouse
    fixture in ``conftest.py``, both tests observe the same provider
    instance (id() comparison equal) — regression.
    """
    provider = trace.get_tracer_provider()
    exporter = InMemorySpanExporter()
    span_processor = SimpleSpanProcessor(exporter)
    provider.add_span_processor(span_processor)
    info: dict[str, object] = {
        "exporter": exporter,
        "provider_id": id(provider),
    }
    _PROVIDERS_SEEN.append(info["provider_id"])  # type: ignore[arg-type]
    try:
        yield info
    finally:
        with __import__("contextlib").suppress(Exception):
            provider.shutdown()


def test_a_installs_processor(install_span_processor: dict[str, object]) -> None:
    """test_a installs a SpanProcessor on the fixture-managed provider.

    Sanity check: the fixture's captured ``provider_id`` matches the
    currently-active TracerProvider (id() equal), proving the test
    ran inside the autouse-fixture-swapped provider.
    """
    info = install_span_processor
    assert info["exporter"] is not None
    assert info["provider_id"] == id(trace.get_tracer_provider())


def test_b_provider_is_fresh_after_test_a(
    install_span_processor: dict[str, object],
) -> None:
    """The autouse fixture must swap the TracerProvider between tests.

    test_a appended ``_PROVIDERS_SEEN[0]``. If the fixture ran, this
    test observes a *different* provider (id() inequality). If the
    fixture did NOT run, both ids are equal — regression signal.
    """
    assert len(_PROVIDERS_SEEN) >= 2, (
        "pytest collection order assumption broken; "
        "test_a must run before test_b"
    )
    provider_id_a: int = _PROVIDERS_SEEN[0]
    provider_id_b: int = id(trace.get_tracer_provider())
    assert provider_id_b != provider_id_a, (
        "TracerProvider swap did NOT happen between tests; "
        "test pollution will follow"
    )
