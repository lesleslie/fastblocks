"""Phase 1.5.x remediation Card 8 — Facade identity check.

F-L3-3 (Phase 1.5 adversarial review): ``FastblocksRegistry.__init__``
accepts any ``Resolver``-shaped object without verifying it is the
canonical singleton from ``get_resolver()``. A caller that constructs
``FastblocksRegistry(Resolver())`` silently creates a parallel registry
that does not share state with the consolidation-invariant singleton,
breaking ADR 0008 Rule 2.

The Card 8 fix is a WARNING (not a raise) at construction time:

  * canonical (``get_resolver()``)        — silent
  * non-canonical (e.g. ``Resolver()``)   — WARNING with caller
    file:line so operators see the leak immediately.

The warning posture was chosen over raising because some legitimate
test isolation patterns construct ephemeral Resolvers to run against
private state (see Card 5's ``_fresh_registry`` helper — that one is
now ironically the canonical example of what the warning is for, and
it suppresses the warning via ``caplog``).

These tests pin:

  1. ``FastblocksRegistry(get_resolver())`` does NOT trigger a
     warning at construction (the canonical path).
  2. ``FastblocksRegistry(Resolver())`` DOES trigger a warning with
     the construction site identified in the log message.
  3. The warning remains stable even when invoked from inside a
     fixture (the ``_construction_site_info`` helper reads two
     frames back, not one — must reach the *caller's* frame, not
     the constructor's own frame).

See ``docs/superpowers/plans/2026-08-21-fastblocks-modern-framework-master-plan.md``
Phase 1.5x remediation, Card 8 (F-L3-3).
"""

from __future__ import annotations

import logging

import pytest
from oneiric.core.resolution import Resolver
from fastblocks.core.resolver import FastblocksRegistry, get_resolver


@pytest.mark.unit
def test_facade_construction_with_canonical_resolver_is_silent(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """``FastblocksRegistry(get_resolver())`` does not emit the leak warning.

    The canonical construction site is the only one the codebase
    uses in production (verified by tests/core/test_migrated_module_spotcheck.py
    Card 7). The warning must NOT fire for this path — otherwise
    every production module load logs a noise line.
    """
    canonical = get_resolver()

    with caplog.at_level(logging.WARNING, logger="fastblocks.core.resolver"):
        registry = FastblocksRegistry(canonical)

    assert isinstance(registry, FastblocksRegistry)
    leak_warnings = [
        record
        for record in caplog.records
        if "non-canonical" in record.getMessage()
    ]
    assert not leak_warnings, (
        f"Canonical construction emitted the leak warning: "
        f"{[r.getMessage() for r in leak_warnings]!r}"
    )


@pytest.mark.unit
def test_facade_construction_with_fresh_resolver_warns(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A fresh ``Resolver()`` triggers a non-canonical warning.

    This is the regression scenario the synthesis agent flagged:
    a caller who wraps a private ``Resolver()`` in
    ``FastblocksRegistry`` gets a parallel registry that never
    shares state with ``get_resolver()``.
    """
    fresh = Resolver()
    assert fresh is not get_resolver(), (
        "Test precondition: get_resolver() must NOT return a fresh Resolver(). "
        "If this fails the singleton is broken — different problem."
    )

    with caplog.at_level(logging.WARNING, logger="fastblocks.core.resolver"):
        FastblocksRegistry(fresh)

    leak_warnings = [
        record
        for record in caplog.records
        if "non-canonical" in record.getMessage()
    ]
    assert leak_warnings, (
        "Constructing FastblocksRegistry(Resolver()) did NOT emit the "
        "non-canonical warning. The Card 8 identity check has regressed."
    )
    assert any(
        "test_facade_identity_check.py" in r.getMessage()
        for r in leak_warnings
    ), (
        "Warning must name the construction site (file:line). "
        f"Got: {[r.getMessage() for r in leak_warnings]!r}"
    )


@pytest.mark.unit
def test_facade_warnings_are_unique_per_construction(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Each non-canonical construction emits exactly one warning.

    A loop or test construction batch must produce one warning
    per registration — not zero (regression), not N>1 (over-emit
    would also be visible to operators at startup).
    """
    fresh_resolvers = [Resolver() for _ in range(3)]

    with caplog.at_level(logging.WARNING, logger="fastblocks.core.resolver"):
        for fresh in fresh_resolvers:
            FastblocksRegistry(fresh)

    leak_warnings = [
        record
        for record in caplog.records
        if "non-canonical" in record.getMessage()
    ]
    assert len(leak_warnings) == len(fresh_resolvers), (
        f"Expected {len(fresh_resolvers)} warnings, got {len(leak_warnings)}. "
        "Each FastblocksRegistry(Resolver()) must emit exactly one warning."
    )


@pytest.mark.unit
def test_facade_warning_names_resolver_class_for_diagnostics(
    caplog: pytest.LogCaptureFixture,
) -> None:
    r"""The warning must include the resolver class so debug logs identify the leak source.

    The message must contain \"Resolver\" (the class name) so an
    operator scanning startup logs can grep for it. The full
    import path is more precise (``oneiric.core.resolution.Resolver``);
    we assert the class name is present as the minimum bar.
    """
    fresh = Resolver()
    with caplog.at_level(logging.WARNING, logger="fastblocks.core.resolver"):
        FastblocksRegistry(fresh)

    messages = [r.getMessage() for r in caplog.records]
    assert any("Resolver" in m for m in messages), (
        f"No warning named the resolver class. Saw: {messages!r}"
    )
