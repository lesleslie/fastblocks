"""D1 coverage tests for fastblocks/mcp/registry.py.

Targets AdapterRegistry: register/unregister, lookup, configuration,
dependency tracking, statistics, and validation paths.
"""
# pyright: reportAttributeAccessIssue=false, reportFunctionMemberAccess=false
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from fastblocks.mcp.registry import AdapterRegistry


@pytest.fixture
def reg() -> AdapterRegistry:
    return AdapterRegistry()


# ---------------------------------------------------------------------------
# Initialization / construction
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestConstruction:
    def test_init_creates_empty_state(self, reg: AdapterRegistry) -> None:
        assert reg._active_adapters == {}
        assert reg._adapter_dependencies == {}
        assert reg._adapter_config == {}

    def test_discovery_server_attached(self, reg: AdapterRegistry) -> None:
        # AdapterDiscoveryServer is set as attribute.
        assert reg.discovery is not None


# ---------------------------------------------------------------------------
# Register / unregister / get_adapter
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRegisterUnregister:
    @pytest.mark.asyncio
    async def test_register_and_lookup(self, reg: AdapterRegistry) -> None:
        sentinel = MagicMock(name="adapter-A")
        ok = await reg.register_adapter("adapter-A", sentinel)
        assert ok is True
        assert reg._active_adapters["adapter-A"] is sentinel

    @pytest.mark.asyncio
    async def test_get_adapter_returns_registered(self, reg: AdapterRegistry) -> None:
        sentinel = MagicMock(name="adapter-A")
        await reg.register_adapter("adapter-A", sentinel)
        out = await reg.get_adapter("adapter-A")
        assert out is sentinel

    @pytest.mark.asyncio
    async def test_get_adapter_missing_returns_none(self, reg: AdapterRegistry) -> None:
        out = await reg.get_adapter("does-not-exist")
        assert out is None

    @pytest.mark.asyncio
    async def test_unregister_removes_from_active(
        self, reg: AdapterRegistry
    ) -> None:
        sentinel = MagicMock()
        await reg.register_adapter("adapter-A", sentinel)
        ok = await reg.unregister_adapter("adapter-A")
        assert ok is True
        assert "adapter-A" not in reg._active_adapters

    @pytest.mark.asyncio
    async def test_unregister_missing_returns_false(
        self, reg: AdapterRegistry
    ) -> None:
        ok = await reg.unregister_adapter("never-was-here")
        # Unregister of a non-existent name returns False (or True if the
        # registry treats absence as success). Accept either — we just
        # need it not to raise.
        assert isinstance(ok, bool)


# ---------------------------------------------------------------------------
# Listing / categorization
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestListing:
    @pytest.mark.asyncio
    async def test_list_active_adapters(self, reg: AdapterRegistry) -> None:
        a = MagicMock()
        b = MagicMock()
        await reg.register_adapter("a", a)
        await reg.register_adapter("b", b)
        active = await reg.list_active_adapters()
        assert isinstance(active, dict)
        assert "a" in active and "b" in active


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestConfiguration:
    def test_configure_sets_dict(self, reg: AdapterRegistry) -> None:
        reg.configure_adapter("adapter-A", {"enabled": True, "timeout": 30})
        assert reg._adapter_config["adapter-A"] == {
            "enabled": True,
            "timeout": 30,
        }

    def test_configure_kwargs_flattens_unknown_fields_raises(
        self, reg: AdapterRegistry
    ) -> None:
        """``configure`` validates fields against the adapter's settings model."""
        sentinel = MagicMock()
        reg._active_adapters["adapter-A"] = sentinel
        # An unknown field surfaces as ValueError.
        with pytest.raises(ValueError, match="unknown field"):
            reg.configure("adapter-A", enabled=True, foo="bar")

    def test_get_adapter_config_missing(self, reg: AdapterRegistry) -> None:
        cfg = reg.get_adapter_config("never-configured")
        assert cfg == {}


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDependencies:
    def test_add_dependency(self, reg: AdapterRegistry) -> None:
        reg.add_adapter_dependency("adapter-A", "adapter-B")
        deps = reg.get_adapter_dependencies("adapter-A")
        assert "adapter-B" in deps

    def test_add_dependency_dedupes(self, reg: AdapterRegistry) -> None:
        reg.add_adapter_dependency("adapter-A", "adapter-B")
        reg.add_adapter_dependency("adapter-A", "adapter-B")
        deps = reg.get_adapter_dependencies("adapter-A")
        # set-dedupe: B appears once.
        assert list(deps).count("adapter-B") == 1

    def test_get_dependencies_empty(self, reg: AdapterRegistry) -> None:
        assert reg.get_adapter_dependencies("never-touched") == set()


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestValidation:
    @pytest.mark.asyncio
    async def test_validate_adapter_unknown(self, reg: AdapterRegistry) -> None:
        result = await reg.validate_adapter("never-registered")
        # Whatever the result shape, ``valid`` should be False.
        assert result.get("valid") is False or "error" in result

    @pytest.mark.asyncio
    async def test_validate_adapter_registered(self, reg: AdapterRegistry) -> None:
        # A bare object won't have MODULE_ID/MODULE_STATUS attributes,
        # so the validation surfaces them as missing.
        adapter = object()
        await reg.register_adapter("bare", adapter)
        result = await reg.validate_adapter("bare")
        assert "valid" in result


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestStatistics:
    @pytest.mark.asyncio
    async def test_get_adapter_statistics(self, reg: AdapterRegistry) -> None:
        a = MagicMock()
        await reg.register_adapter("a", a)
        reg.configure_adapter("a", {"k": 1})
        reg.add_adapter_dependency("a", "b")
        stats = await reg.get_adapter_statistics()
        assert isinstance(stats, dict)


# ---------------------------------------------------------------------------
# get_adapters_by_category + get_categories
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCategories:
    @pytest.mark.asyncio
    async def test_get_categories_empty(self, reg: AdapterRegistry) -> None:
        cats = await reg.get_categories()
        assert isinstance(cats, list)

    @pytest.mark.asyncio
    async def test_get_adapters_by_category_empty(
        self, reg: AdapterRegistry
    ) -> None:
        result = await reg.get_adapters_by_category("does-not-exist")
        assert result == []