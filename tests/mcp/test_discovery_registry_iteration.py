"""Regression test for Card 4 — _discover_from_acb_registry silent no-op.

The pre-fix code called ``getattr(depends, "_registry", {})`` which
always returned ``{}`` because Oneiric's Resolver has no such
attribute. The outer ``with suppress(Exception)`` masked the empty
result, so the function silently discovered zero ACB adapters even
when candidates were registered.

This test pins both:
  1. ``_discover_from_acb_registry`` actually iterates registered
     Candidates and surfaces them as AdapterInfo.
  2. The fix does NOT call ``depends.resolve(...)`` (which returns a
     Candidate record, not an instance) — it must invoke the factory.

See ``docs/superpowers/plans/2026-08-21-fastblocks-modern-framework-master-plan.md``
Phase 1.5x remediation, Card 4 (F-L1-002).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

import pytest
from oneiric.core.resolution import Candidate, Resolver
from fastblocks.core.resolver import FastblocksRegistry
from fastblocks.mcp import discovery as discovery_mod
from fastblocks.mcp.discovery import AdapterDiscoveryServer


def _make_registry() -> FastblocksRegistry:
    """Build a FastblocksRegistry wrapping a fresh Resolver for tests."""
    return FastblocksRegistry(Resolver())

_DOMAIN = "fastblocks"


class _FakeAdapter:
    """Minimal stand-in exposing the two MODULE_* attributes discovery checks for."""


@pytest.fixture
def fake_resolver(monkeypatch):
    """Yield a Resolver with two Candidates registered, then restore monkeypatch state."""
    resolver = _make_registry()
    resolver.register(
        Candidate(
            domain=_DOMAIN,
            key="alpha",
            factory=lambda: _FakeAdapter(),
        ),
    )
    resolver.register(
        Candidate(
            domain=_DOMAIN,
            key="beta",
            factory=lambda: _FakeAdapter(),
        ),
    )

    # The discovery module binds `depends` at import time, so we have
    # to swap the symbol within the module rather than re-register.
    monkeypatch.setattr(discovery_mod, "depends", resolver)
    return resolver


def _faux_adapter(module_name: str = "fastblocks.adapters.tests.fake") -> object:
    """Build a stub adapter carrying MODULE_ID + MODULE_STATUS + a class."""

    @dataclass
    class _Stub:
        MODULE_ID: UUID = field(
            default_factory=lambda: UUID("01937d86-4f2a-7b3c-8d9e-f3b4d3c2b1a0"),
        )
        MODULE_STATUS: str = "stable"

    _Stub.__module__ = module_name  # not part of dataclass fields but needed for AdapterInfo
    return _Stub()


@pytest.mark.asyncio
async def test_discover_from_acb_registry_iterates_registered_candidates(
    monkeypatch,
) -> None:
    """Two Candidates registered → AdapterDiscoveryServer must surface two adapter names.

    Canary: with the pre-fix code, this returned nothing because
    ``getattr(depends, "_registry", {})`` always yielded ``{}``. The
    fix must exercise ``depends.list_active("fastblocks")`` and call
    ``factory()`` per Candidate.
    """
    resolver = _make_registry()

    def factory_alpha() -> object:
        instance = _faux_adapter("fastblocks.adapters.alpha.adapter")
        instance.__class__.__name__ = "AlphaAdapter"
        return instance

    def factory_beta() -> object:
        instance = _faux_adapter("fastblocks.adapters.beta.adapter")
        instance.__class__.__name__ = "BetaAdapter"
        return instance

    resolver.register(
        Candidate(domain=_DOMAIN, key="alpha", factory=factory_alpha),
    )
    resolver.register(
        Candidate(domain=_DOMAIN, key="beta", factory=factory_beta),
    )

    monkeypatch.setattr(discovery_mod, "depends", resolver)

    server = AdapterDiscoveryServer()
    # Prime via the public discover_adapters() entry point, exactly
    # like MCP would.
    await server.discover_adapters()

    # Both registered keys must now be known to the server.
    assert "alpha" in server._discovered_adapters, (
        "alpha Candidate was registered but never surfaced by "
        "_discover_from_acb_registry. Canary failure — code is "
        "still iterating a non-existent _registry attribute."
    )
    assert "beta" in server._discovered_adapters


@pytest.mark.asyncio
async def test_discover_from_acb_registry_skips_candidates_without_module_ids(
    monkeypatch,
) -> None:
    """A factory that returns a plain object (no MODULE_ID) must be skipped, not crash.

    One bad Candidate must not derail discovery of the rest. This
    pins the narrow per-candidate try/except added to replace the
    old blanket ``with suppress(Exception)``.
    """
    resolver = _make_registry()

    def factory_good() -> object:
        instance = _faux_adapter("fastblocks.adapters.gamma.adapter")
        instance.__class__.__name__ = "GammaAdapter"
        return instance

    def factory_bare() -> object:
        # Plain object without MODULE_ID / MODULE_STATUS — must be skipped.
        return object()

    resolver.register(
        Candidate(domain=_DOMAIN, key="gamma", factory=factory_good),
    )
    resolver.register(
        Candidate(domain=_DOMAIN, key="bare", factory=factory_bare),
    )

    monkeypatch.setattr(discovery_mod, "depends", resolver)

    server = AdapterDiscoveryServer()
    await server.discover_adapters()

    assert "gamma" in server._discovered_adapters
    assert "bare" not in server._discovered_adapters  # plain object filtered out


@pytest.mark.asyncio
async def test_discover_from_acb_registry_logs_single_failure(
    monkeypatch,
    caplog,
) -> None:
    """A factory that raises must log a warning, not raise and not silently vanish."""
    import logging

    resolver = _make_registry()

    def factory_raises() -> object:
        raise RuntimeError("intentional test failure")

    def factory_good() -> object:
        instance = _faux_adapter("fastblocks.adapters.delta.adapter")
        instance.__class__.__name__ = "DeltaAdapter"
        return instance

    resolver.register(
        Candidate(domain=_DOMAIN, key="raises", factory=factory_raises),
    )
    resolver.register(
        Candidate(domain=_DOMAIN, key="delta", factory=factory_good),
    )

    monkeypatch.setattr(discovery_mod, "depends", resolver)

    server = AdapterDiscoveryServer()

    with caplog.at_level(logging.WARNING, logger="fastblocks.mcp.discovery"):
        await server.discover_adapters()

    # The broken factory was logged, not swallowed.
    failing_records = [
        record for record in caplog.records if "raises" in record.getMessage()
    ]
    assert failing_records, (
        "Per-candidate failure was not logged. The narrow per-candidate "
        "try/except is missing or the logger was bypassed."
    )

    # The good Candidate still got discovered — one bad apple didn't spoil the bunch.
    assert "delta" in server._discovered_adapters
