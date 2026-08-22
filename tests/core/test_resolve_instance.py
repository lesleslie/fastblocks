"""Phase 1.5.x remediation Card 5 — FastblocksRegistry.resolve_instance coverage.

F-L4-01 (Phase 1.5 adversarial review): ``FastblocksRegistry.resolve_instance``
is the user-facing API that swallows a documented exception set and
invokes the factory. Phase 2 typed wrappers will compose on top of
this method, so its four branches need explicit pinning:

  1. happy path — registered factory is invoked and returns the
     instance.
  2. miss path — unknown ``(domain, key)`` returns ``None`` rather
     than raising.
  3. resolver-error path — KeyError / AttributeError / RuntimeError /
     TypeError from the underlying resolver all collapse to ``None``.
  4. factory-error path — the same exception set raised by the
     factory invocation collapses to ``None``.
  5. undocumented-exception path — exceptions OUTSIDE the swallow set
     propagate, so future contributors who broaden the set break
     Phase 2 callers loudly.

These tests use an isolated ``FastblocksRegistry`` wrapping a fresh
``Resolver`` so they cannot pollute the shared ``get_resolver()``
singleton. The resolver is patched via ``monkeypatch.setattr`` rather
than subclassing to avoid LSP-style signature drift when the parent
``Resolver.resolve`` signature evolves across Oneiric versions.

See ``docs/superpowers/plans/2026-08-21-fastblocks-modern-framework-master-plan.md``
Phase 1.5x remediation, Card 5 (F-L4-01).
"""

from __future__ import annotations

import pytest
from oneiric.core.resolution import Candidate
from fastblocks.core.resolver import FastblocksRegistry


def _patch_resolver(
    monkeypatch: pytest.MonkeyPatch,
    registry: FastblocksRegistry,
    side_effect: BaseException,
) -> None:
    """Swap the underlying Resolver's ``resolve`` to raise ``side_effect``."""
    monkeypatch.setattr(
        registry._resolver,
        "resolve",
        lambda *args, **kwargs: (_ for _ in ()).throw(side_effect),
    )


@pytest.mark.unit
def test_resolve_instance_returns_factory_result_on_hit(
    fresh_registry: FastblocksRegistry,
) -> None:
    """Hit path: registered factory invoked exactly once, return value passed through."""
    registry = fresh_registry

    calls: list[int] = []
    sentinel = object()

    def factory() -> object:
        calls.append(1)
        return sentinel

    registry.register(
        Candidate(domain="fastblocks", key="happy", factory=factory),
    )

    result = registry.resolve_instance("fastblocks", "happy")

    assert result is sentinel
    assert calls == [1], (
        "Factory must be invoked exactly once. If this is [] the "
        "implementation changed to not call the factory; if this "
        "is >[1] the implementation is double-invoking."
    )


@pytest.mark.unit
def test_resolve_instance_returns_none_on_unknown_key(
    fresh_registry: FastblocksRegistry,
) -> None:
    """Miss path: unknown (domain, key) yields None, never raises."""
    registry = fresh_registry

    # Empty registry — no candidates registered under this key.
    result = registry.resolve_instance("fastblocks", "never_registered")

    assert result is None


@pytest.mark.unit
@pytest.mark.parametrize(
    "exc",
    [KeyError("k"), AttributeError("a"), RuntimeError("r"), TypeError("t")],
    ids=["KeyError", "AttributeError", "RuntimeError", "TypeError"],
)
def test_resolve_instance_returns_none_on_resolver_exception(
    monkeypatch: pytest.MonkeyPatch,
    fresh_registry: FastblocksRegistry,
    exc: BaseException,
) -> None:
    """Resolver exception path: every swallow-set exception collapses to None."""
    registry = fresh_registry
    _patch_resolver(monkeypatch, registry, exc)

    result = registry.resolve_instance("fastblocks", "any")

    assert result is None


@pytest.mark.unit
@pytest.mark.parametrize(
    "exc",
    [KeyError("k"), AttributeError("a"), RuntimeError("r"), TypeError("t")],
    ids=["KeyError", "AttributeError", "RuntimeError", "TypeError"],
)
def test_resolve_instance_returns_none_when_factory_raises(
    fresh_registry: FastblocksRegistry,
    exc: BaseException,
) -> None:
    """Factory exception path: swallow-set exceptions inside the factory collapse to None."""
    registry = fresh_registry

    def boom() -> object:
        raise exc

    registry.register(
        Candidate(domain="fastblocks", key=f"factory_{type(exc).__name__}", factory=boom),
    )

    result = registry.resolve_instance("fastblocks", f"factory_{type(exc).__name__}")

    assert result is None


@pytest.mark.unit
def test_resolve_instance_propagates_undocumented_factory_exception(
    fresh_registry: FastblocksRegistry,
) -> None:
    """Out-of-set factory exceptions must NOT be swallowed.

    ValueError is NOT in the documented swallow set. A future
    contributor who broadens the swallow set to ``Exception``
    breaks this contract — Phase 2 callers will silently lose
    data on misconfigurations.
    """
    registry = fresh_registry

    def boom() -> object:
        raise ValueError("intentional non-swallowed failure")

    registry.register(
        Candidate(domain="fastblocks", key="value_error_factory", factory=boom),
    )

    with pytest.raises(ValueError, match="intentional non-swallowed failure"):
        registry.resolve_instance("fastblocks", "value_error_factory")


@pytest.mark.unit
def test_resolve_instance_propagates_undocumented_resolver_exception(
    monkeypatch: pytest.MonkeyPatch,
    fresh_registry: FastblocksRegistry,
) -> None:
    """Out-of-set resolver exceptions must NOT be swallowed."""
    registry = fresh_registry
    _patch_resolver(monkeypatch, registry, OSError("network down"))

    with pytest.raises(OSError, match="network down"):
        registry.resolve_instance("fastblocks", "any")


@pytest.mark.unit
def test_resolve_instance_returns_none_for_non_callable_factory(
    fresh_registry: FastblocksRegistry,
) -> None:
    """Defensive test: a string-typed factory returns None (calls fail with TypeError).

    Oneiric allows ``factory`` to be either a callable or an import
    path (``module.path:attribute``). Resolve_instance can only invoke
    callables, so a string factory currently raises ``TypeError`` from
    the call attempt. That ``TypeError`` IS in the swallow set, so the
    documented contract returns ``None`` rather than a half-resolved
    module handle. Phase 2 callers that need the import-path branch
    should compose ``resolver.resolve(...)`` directly.
    """
    registry = fresh_registry
    registry.register(
        Candidate(
            domain="fastblocks",
            key="string_factory",
            factory="fastblocks.adapters.tests.fake:demo",  # type: ignore[arg-type]
        ),
    )

    result = registry.resolve_instance("fastblocks", "string_factory")

    # The try/except in resolve_instance catches the TypeError raised
    # when invoking a string as a callable, collapsing to None.
    assert result is None
