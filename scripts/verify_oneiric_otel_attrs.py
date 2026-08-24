#!/usr/bin/env -S uv run --quiet --project ../python python
r"""Precondition smoke check for the Oneiric resolver-decision OTel attribute contract.

Per v6 Delta-8/Delta-29 + ADR 0013: ``resolver.decision`` spans emitted by the
Oneiric resolver MUST carry the four bare attrs ``domain``,
``key``, ``provider``, and ``decision`` (where ``decision`` is
``Literal["resolved","error"]``). FastBlocks'
``DecisionSpanProcessor`` reads exactly those attrs on
``on_end``; if Oneiric ever drops or renames one, every
decision-spans metric silently goes to zero.

This script is the canonical precondition check (ADR 0013 says:
"precondition smoke checks must be runnable stand-alone and exit
non-zero on failure"). It does NOT depend on pytest, the
ObservabilityRegistry, or the test conftest fixtures. It can be
run from the repo root with::

    /Users/les/Projects/fastblocks/.venv/bin/python \\
        /Users/les/Projects/fastblocks/scripts/verify_oneiric_otel_attrs.py

Exit codes:
  * ``0`` — contract holds (all four attrs present).
  * ``1`` — contract violation (missing or renamed attr).
  * ``2`` — environment failure (no OTel SDK, no Oneiric, etc.).

The script deliberately reads Oneiric's own
``DecisionEvent.as_attributes()`` rather than introspecting the
emitted span at runtime; the static-method check is fast,
deterministic, and does not require a configured TracerProvider.
"""
from __future__ import annotations

import sys
from typing import NoReturn

REQUIRED_ATTRS: tuple[str, ...] = ("domain", "key", "provider", "decision")


def _fail(message: str, *, code: int = 1) -> NoReturn:
    """Print the failure, the actual attrs, and exit non-zero."""
    print(f"FAIL: {message}", file=sys.stderr)
    sys.exit(code)


def main() -> int:
    try:
        from oneiric.core.observability import DecisionEvent
    except ImportError as exc:  # pragma: no cover - environment failure
        _fail(
            "could not import oneiric.core.observability.DecisionEvent; "
            f"is Oneiric installed in the active environment? error={exc!r}",
            code=2,
        )

    event = DecisionEvent(
        domain="fastblocks",
        key="templates",
        provider="jinja",
        decision="resolved",
        details={},
    )
    # If Oneiric's DecisionEvent.as_attributes() regresses, an
    # unhandled exception is exactly what the operator should see —
    # so we deliberately do NOT wrap this call in try/except. The
    # script's exit code on uncaught exception is 1 (Python default),
    # which is the contract-violation code; the traceback prints
    # to stderr via Python's default behavior.
    attrs = event.as_attributes()

    print("DecisionEvent.as_attributes() returned:", attrs)
    missing = [a for a in REQUIRED_ATTRS if a not in attrs]
    if missing:
        _fail(
            "resolver.decision span contract is violated: missing required "
            f"attribute(s) {missing!r} in DecisionEvent.as_attributes(); "
            f"observed: {attrs!r}"
        )

    decision = attrs.get("decision")
    if decision not in ("resolved", "error"):
        _fail(
            f"DecisionEvent.decision must be Literal['resolved','error']; "
            f"got {decision!r}"
        )

    print("PASS: resolver.decision span contract holds.")
    print(
        f"  - required attrs present: {REQUIRED_ATTRS!r}",
    )
    print(f"  - decision value: {decision!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
