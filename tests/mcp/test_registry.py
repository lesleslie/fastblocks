"""Tests for AdapterRegistry.configure (Phase 0a typed API).

The pre-Phase-0a code only has ``configure_adapter(config: dict)``,
which is the unsafe setattr-loop equivalent. After Phase 0a lands,
``configure(adapter_name, **fields)`` is the safe, allowlist-enforced
entry point. The tests in this file are RED until Phase 0a ships.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

import pytest


class _StubSettings:
    """Mirror of the production adapter settings shape (Pydantic-style attrs).

    Fields are set in ``__init__`` so they live in the instance
    ``__dict__`` — matching how real Pydantic models populate
    fields. Class-level-only annotations (without ``__init__``)
    would NOT show up in ``vars(instance)``; do not refactor
    this without checking the production adapter pattern.
    """

    def __init__(self) -> None:
        self.customer_id: str = ""
        self.region: str = "us-central1"
        self.enable_metrics: bool = True


class _StubAdapter:
    """Test double that follows the production adapter pattern."""

    MODULE_ID: UUID = UUID("00000000-0000-0000-0000-000000000001")
    MODULE_STATUS: str = "stable"

    def __init__(self) -> None:
        self.settings: _StubSettings = _StubSettings()


def _registry_with_stub(name: str = "stub") -> tuple[Any, _StubAdapter]:
    """Build a registry with a single stub adapter pre-registered."""
    from fastblocks.mcp.registry import AdapterRegistry

    registry = AdapterRegistry()
    adapter = _StubAdapter()
    registry._active_adapters[name] = adapter
    return registry, adapter


def test_configure_rejects_unknown_field() -> None:
    """The typed configure() must raise ValueError on unknown fields.

    This is the core security guarantee: callers cannot set
    arbitrary attributes on adapter instances.
    """
    registry, _adapter = _registry_with_stub()

    with pytest.raises(ValueError, match=r"unknown field.*'definitely_not_a_field'"):
        registry.configure("stub", definitely_not_a_field=42)


def test_configure_accepts_declared_field() -> None:
    """The typed configure() must accept declared settings fields and write them."""
    registry, adapter = _registry_with_stub()

    registry.configure("stub", customer_id="acme-co")

    assert adapter.settings.customer_id == "acme-co"


def test_configure_accepts_multiple_declared_fields() -> None:
    """The typed configure() must accept and write multiple declared fields."""
    registry, adapter = _registry_with_stub()

    registry.configure("stub", customer_id="acme-co", region="europe-west1")

    assert adapter.settings.customer_id == "acme-co"
    assert adapter.settings.region == "europe-west1"


def test_configure_rejects_known_adapter_with_no_settings() -> None:
    """The typed configure() must raise at call time if the adapter has no settings.

    Note: the v2 review noted that the *better* failure mode is at
    AdapterRegistry init / register time, not at configure() call
    time. That hardening is tracked as a follow-up; this test
    pins the current behavior so a silent acceptance regression
    is caught.
    """
    from fastblocks.mcp.registry import AdapterRegistry

    registry = AdapterRegistry()
    adapter = _StubAdapter()
    # Simulate an adapter that bypassed the standard settings pattern.
    del adapter.settings
    registry._active_adapters["broken"] = adapter

    with pytest.raises((ValueError, AttributeError)):
        registry.configure("broken", customer_id="acme-co")
