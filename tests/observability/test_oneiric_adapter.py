"""Tests for the oneiric resolver span attribute contract.

Per v6 Δ8/Δ29 + ADR 0013: ``resolver.decision`` spans MUST carry
``domain`` / ``key`` / ``provider`` / ``decision`` attributes (the
"bare attrs" contract). ``scripts/verify_oneiric_otel_attrs.py`` is
the canonical precondition smoke check; this test file exercises
the same contract end-to-end against a real Oneiric resolver round
trip.

This file pairs with ``test_decision_span_processor.py``: the
processor tests use a hand-built ReadableSpan; this file confirms
the Oneiric side actually emits the expected attribute shape.
"""
from __future__ import annotations


def test_oneiric_traced_decision_emits_required_bare_attrs() -> None:
    """Per brief: domain/key/provider/decision MUST be on resolver.decision spans.

    Round-trip a real Oneiric ``traced_decision`` context manager and
    inspect the span it produces. The span must carry the four
    required attributes at the top level (not nested in
    ``attributes.details``).
    """
    from oneiric.core.observability import DecisionEvent, traced_decision
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,
    )

    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    # Swap the global provider so ``trace.get_tracer()`` inside
    # ``traced_decision`` uses our test-managed one.
    try:
        from opentelemetry.trace import _TRACER_PROVIDER_SET_ONCE
        _TRACER_PROVIDER_SET_ONCE._done = False
    except ImportError:  # pragma: no cover - private API renamed
        pass
    trace.set_tracer_provider(provider)

    event = DecisionEvent(
        domain="fastblocks",
        key="templates",
        provider="jinja",
        decision="resolved",
        details={"score": 1.0},
    )
    with traced_decision(event):
        pass

    spans = exporter.get_finished_spans()
    matching = [s for s in spans if s.name == "resolver.decision"]
    assert matching, (
        f"expected one resolver.decision span; got {[s.name for s in spans]!r}"
    )
    span = matching[-1]
    attrs = dict(span.attributes or {})
    for required in ("domain", "key", "provider", "decision"):
        assert required in attrs, (
            f"resolver.decision span MUST carry {required!r} per Δ8/Δ29; "
            f"observed attrs: {attrs!r}"
        )
    assert attrs["domain"] == "fastblocks"
    assert attrs["key"] == "templates"
    assert attrs["decision"] == "resolved"


def test_decisionevent_as_attributes_includes_all_four() -> None:
    """Oneiric's DecisionEvent.as_attributes MUST include the 4 required keys.

    Defense-in-depth: the brief is explicit about the attribute set;
    if Oneiric ever drops one of these from the as_attributes dict,
    this test fails before the integration test does.
    """
    from oneiric.core.observability import DecisionEvent

    event = DecisionEvent(
        domain="fastblocks",
        key="templates",
        provider="jinja",
        decision="resolved",
        details={},
    )
    attrs = event.as_attributes()
    for required in ("domain", "key", "provider", "decision"):
        assert required in attrs, (
            f"DecisionEvent.as_attributes() must include {required!r}; "
            f"got: {attrs!r}"
        )


def test_verify_oneiric_otel_attrs_script_passes_on_live_oneiric() -> None:
    """Per ADR 0013: scripts/verify_oneiric_otel_attrs.py is a precondition.

    The script MUST exit 0 against the current Oneiric install when
    the contract holds (i.e. the Oneiric side actually emits the
    required attrs). If the script ever regresses or Oneiric drops
    an attribute, this test fails before the integration test fails.
    """
    import subprocess
    import sys
    from pathlib import Path

    script = (
        Path(__file__).resolve().parents[2] / "scripts" / "verify_oneiric_otel_attrs.py"
    )
    assert script.exists(), (
        f"scripts/verify_oneiric_otel_attrs.py is missing at {script}"
    )
    result = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"verify_oneiric_otel_attrs.py must pass against current Oneiric; "
        f"exit={result.returncode}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
