"""Phase 2 mechanical-four Commit4 — TemplateAdapter Protocol tests.

The Protocol surface ships in Phase 2 (for Phase 6's Prometheus
cardinality lint anchor); ``register_template_candidate`` is
deferred. Three tests cover the Protocol surface.
"""
from __future__ import annotations

import typing as t
from types import SimpleNamespace

import pytest
from fastblocks.core.validators import (
    TemplateAdapter,
    _protocol_missing_methods,
)


def _make_template_module(methods: set[str]) -> t.Any:
    ns = SimpleNamespace()
    if "render" in methods:
        ns.render = lambda template, context: "<rendered>"
    if "init_envs" in methods:
        ns.init_envs = lambda: object()
    return t.cast("TemplateAdapter", ns)


@pytest.mark.unit
@pytest.mark.parametrize("missing_method", ["render", "init_envs"])
def test_template_protocol_missing_methods(missing_method: str) -> None:
    """Each missing method is reported by _protocol_missing_methods."""
    module = _make_template_module({"render", "init_envs"} - {missing_method})
    missing = _protocol_missing_methods(module, TemplateAdapter)
    assert missing_method in missing


@pytest.mark.unit
def test_template_protocol_is_runtime_checkable() -> None:
    """TemplateAdapter carries @runtime_checkable."""
    assert hasattr(TemplateAdapter, "_is_runtime_protocol")


@pytest.mark.unit
def test_full_template_module_satisfies_protocol() -> None:
    """A module with both methods satisfies TemplateAdapter."""
    module = _make_template_module({"render", "init_envs"})
    assert isinstance(module, TemplateAdapter)
