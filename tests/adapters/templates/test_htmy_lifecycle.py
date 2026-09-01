"""Tests for fastblocks/adapters/templates/htmy.py registry + lifecycle.

Targets the uncovered HTMY surface (217 missing statements before this
file): the ``HTMYComponentRegistry`` cache key / trusted-component
helpers, ``discover_components`` cache invalidation, and the static
helpers on the registry class. Tests avoid the rendering hot path
(which has separate coverage in ``tests/xss``).
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from anyio import Path as AsyncPath
from fastblocks.adapters.templates.htmy import HTMYComponentRegistry


@pytest.fixture
def registry() -> HTMYComponentRegistry:
    storage = MagicMock()
    return HTMYComponentRegistry(storage=storage)


@pytest.mark.unit
class TestRegistryTrustedComponents:
    def test_register_single_component(
        self, registry: HTMYComponentRegistry
    ) -> None:
        sentinel_cls = MagicMock(name="MyComponent")
        registry.register_trusted_component("my-component", sentinel_cls)
        assert registry._trusted_components["my-component"] is sentinel_cls

    def test_register_multiple_components(
        self, registry: HTMYComponentRegistry
    ) -> None:
        components = {
            "comp-a": MagicMock(name="A"),
            "comp-b": MagicMock(name="B"),
        }
        registry.register_trusted_components(components)
        assert "comp-a" in registry._trusted_components
        assert "comp-b" in registry._trusted_components


@pytest.mark.unit
class TestRegistryStaticHelpers:
    def test_get_cache_key_default(
        self, registry: HTMYComponentRegistry
    ) -> None:
        key = registry.get_cache_key(AsyncPath("components/foo.py"))
        assert key.startswith("htmy_component_source:")
        assert "components/foo.py" in key

    def test_get_cache_key_with_custom_type(
        self, registry: HTMYComponentRegistry
    ) -> None:
        key = registry.get_cache_key(
            AsyncPath("components/foo.py"), cache_type="bytecode"
        )
        assert "bytecode" in key

    def test_get_storage_path_passthrough(
        self, registry: HTMYComponentRegistry
    ) -> None:
        path = AsyncPath("components/foo.py")
        assert registry.get_storage_path(path) == path


@pytest.mark.unit
class TestDiscoverComponents:
    async def test_discover_returns_empty_when_no_storage(
        self,
    ) -> None:
        # Storage=None is the documented "no storage" branch; the
        # function should not raise.
        registry = HTMYComponentRegistry(storage=None)
        result = await registry.discover_components()
        assert result == {}
