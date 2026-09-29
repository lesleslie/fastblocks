"""D1 coverage tests for fastblocks/observability/registry.py.

Targets the singleton registry: name registration, collision detection,
and singleton identity.
"""
# pyright: reportAttributeAccessIssue=false, reportFunctionMemberAccess=false
from __future__ import annotations

import pytest

from fastblocks.observability.registry import (
    ObservabilityRegistry,
    get_default_registry,
)


@pytest.mark.unit
class TestRegistry:
    def test_singleton_returns_same_instance(self) -> None:
        a = get_default_registry()
        b = get_default_registry()
        assert a is b

    def test_module_level_singleton_is_callable(self) -> None:
        # ObservabilityRegistry is the module-level singleton instance.
        assert ObservabilityRegistry is not None
        assert ObservabilityRegistry is get_default_registry()

    def test_register_new_name(self) -> None:
        reg = ObservabilityRegistry
        # Use a name that's unlikely to clash with the real metrics.
        # (The singleton's _names set is shared across the process; we
        # register-and-unregister to keep test isolation.)
        sentinel = "d1_test_unique_metric_name_for_isolation"
        if sentinel in reg._names:
            reg._names.discard(sentinel)
        reg.register(sentinel)
        try:
            assert sentinel in reg._names
        finally:
            reg._names.discard(sentinel)

    def test_duplicate_register_raises(self) -> None:
        reg = ObservabilityRegistry
        sentinel = "d1_test_collision_metric"
        reg._names.discard(sentinel)
        reg.register(sentinel)
        try:
            with pytest.raises(Exception) as exc_info:
                reg.register(sentinel)
            # MetricNameCollisionError (subclass of Exception) is the wrapper;
            # verify the message references the offending name.
            assert "d1_test_collision_metric" in str(exc_info.value) or hasattr(
                exc_info.value, "metric_name"
            )
        finally:
            reg._names.discard(sentinel)
