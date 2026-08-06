"""Tests for the Oneiric resolver helpers in `fastblocks.core.resolver`.

Contract surface (Task 0):
- `get_resolver()` returns a process-wide `oneiric.core.resolution.Resolver`.
- `resolve_component()` invokes a registered `Candidate.factory` and returns
  the concrete value, never a `Candidate` wrapper.
- `resolve_component_async()` is the async-aware variant and supports both
  sync and async factories.

These tests intentionally pin the contract so the later tasks that migrate
call sites can rely on `resolve_component[_async]` instead of touching the
raw `Resolver` API (which returns `Candidate | None` rather than the
concrete component).
"""

from __future__ import annotations

import pytest
from oneiric.core.resolution import Candidate
from fastblocks.core.resolver import (
    get_resolver,
    resolve_component,
    resolve_component_async,
)


def test_resolver_is_process_wide() -> None:
    assert get_resolver() is get_resolver()


def test_resolve_component_constructs_candidate_factory() -> None:
    resolver = get_resolver()
    resolver.register(
        Candidate(
            domain="fastblocks", key="test-component", factory=lambda: {"ok": True}
        )
    )

    result = resolve_component(resolver, "fastblocks", "test-component")

    assert result == {"ok": True}


def test_resolve_component_returns_none_for_missing_candidate() -> None:
    assert resolve_component(get_resolver(), "fastblocks", "missing-component") is None


async def test_resolve_component_async_awaits_async_factory() -> None:
    resolver = get_resolver()

    async def factory() -> dict[str, str]:
        return {"async": "ok"}

    resolver.register(
        Candidate(domain="fastblocks", key="async-test-component", factory=factory)
    )

    result = await resolve_component_async(
        resolver, "fastblocks", "async-test-component"
    )

    assert result == {"async": "ok"}


async def test_resolve_component_async_supports_sync_factory() -> None:
    """Async helper must work for plain sync factories too.

    Async callers shouldn't need a parallel sync helper.
    """
    resolver = get_resolver()
    resolver.register(
        Candidate(
            domain="fastblocks", key="async-sync-test-component", factory=lambda: 42
        )
    )

    result = await resolve_component_async(
        resolver, "fastblocks", "async-sync-test-component"
    )

    assert result == 42


def test_resolve_component_rejects_async_factory() -> None:
    """Sync helper must surface a `TypeError` when the factory is async.

    Sync helper has no event loop to await on, so it must surface the
    mistake loudly instead of returning an unawaited coroutine.
    """
    resolver = get_resolver()

    async def factory() -> dict[str, str]:
        return {"async": "ok"}

    resolver.register(
        Candidate(
            domain="fastblocks", key="sync-rejects-async-component", factory=factory
        )
    )

    with pytest.raises(TypeError, match="resolve_component_async"):
        resolve_component(resolver, "fastblocks", "sync-rejects-async-component")
