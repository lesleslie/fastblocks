"""Phase 2 mechanical-four Commit4 — Scenario 3 regression.

Phase 1.5x's ``emit_startup_log`` prints a shadowed-candidate count
at startup. Scenario 3 (registered-but-stale candidate) relies on
this signal. Phase 2 pins the signal so future regressions in the
Phase 1.5x code surface are caught here.
"""
from __future__ import annotations

import typing as t

import pytest


@pytest.mark.unit
def test_emit_startup_log_reports_shadowed_count(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A stale registered candidate produces shadowed count >= 1.

    Mirrors the structured-log capture pattern from
    tests/core/test_resolver_metrics.py:203-235: monkeypatch the
    ``resolver_metrics._log.info`` call (Oneiric structlog does not
    write through stdlib; capsys won't capture it). Use a private
    Resolver for hermetic isolation (canonical singleton is shared
    across the suite; FastblocksRegistry has no clear() method).
    Register a stale candidate — key with a hyphen, not in
    StyleName — via ``registry.register(candidate)`` (the method
    that accepts a pre-built Candidate; ``register_candidate``
    takes a callable factory and would wrap the Candidate).
    """
    from oneiric.core.resolution import (
        Candidate,
        CandidateSource,
        Resolver,
    )
    from fastblocks.core import resolver_metrics
    from fastblocks.core.resolver import FastblocksRegistry

    registry = FastblocksRegistry(Resolver())  # private, hermetic
    candidate = Candidate(
        factory=lambda: object(),
        domain="style",
        key="fastblocks-ui",  # hyphenated, not in StyleName
        source=CandidateSource.LOCAL_PKG,
    )
    registry.register(candidate)  # not register_candidate

    # Spy on resolver_metrics._log.info (structlog BoundLogger)
    info_calls: list[tuple[tuple[t.Any, ...], dict[str, t.Any]]] = []
    real_info = resolver_metrics._log.info

    def spy_info(*args: t.Any, **kwargs: t.Any) -> None:
        info_calls.append((args, kwargs))
        real_info(*args, **kwargs)

    monkeypatch.setattr(resolver_metrics._log, "info", spy_info)
    emit_startup_log = resolver_metrics.emit_startup_log
    emit_startup_log(registry)

    # Find the "M shadowed" call (Phase 1.5x's startup log emits
    # "Oneiric resolver: 1 registry, N candidates, M shadowed")
    shadowed_calls = [
        (args, kwargs)
        for args, kwargs in info_calls
        if args and "shadowed" in (args[0] if args else "")
    ]
    assert shadowed_calls, (
        f"Expected at least one info() call mentioning 'shadowed'; "
        f"saw {len(info_calls)} info() calls total: "
        f"{[args[0] if args else '' for args, _ in info_calls]!r}"
    )
    # The log format string has "%d shadowed" — second positional
    # arg should be an integer >= 1.
    args, _kwargs = shadowed_calls[0]
    # The format-string positional arg for shadowed count
    shadowed_count = None
    for arg in args[1:]:
        if isinstance(arg, int):
            shadowed_count = arg
            break
    assert shadowed_count is not None and shadowed_count >= 1, (
        f"Expected shadowed count >= 1 after registering a stale "
        f"candidate; got {shadowed_count}"
    )
