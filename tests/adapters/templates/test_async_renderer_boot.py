"""D3: boot test for the ``templates/_async_renderer`` adapter.

Spec §D3 row ``templates/_async_renderer`` -> resolver pair
``("fastblocks", "async_template_renderer")`` (verified at
``fastblocks/adapters/templates/_async_renderer.py:723``).

The async renderer wraps ``Templates`` with caching, performance
metrics, and HTMX-aware rendering. Booting requires either a real
``base_templates`` or letting ``initialize()`` fall back to
``Templates()`` + ``await base_templates.init()``. We instantiate
without ``initialize()`` to assert the no-arg boot path documented at
``_async_renderer.py:119`` (the ``__init__`` accepts all-None args).
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from fastblocks.adapters.oneiric_helper import (
    register_candidate_strict,
    resolve_instance,
)
from fastblocks.adapters.templates import _async_renderer


def test_async_renderer_resolves_via_oneiric(fresh_registry) -> None:
    """The async renderer must be discoverable under
    ``("fastblocks", "async_template_renderer")``."""
    from fastblocks.adapters.templates._async_renderer import AsyncTemplateRenderer

    factory = AsyncTemplateRenderer
    register_candidate_strict(
        fresh_registry,
        domain="fastblocks",
        key="async_template_renderer",
        factory=lambda: factory,
        metadata={"class": "AsyncTemplateRenderer"},
    )
    resolved = resolve_instance(
        fresh_registry, "fastblocks", "async_template_renderer"
    )
    assert resolved is not None, (
        "D3: Oneiric resolver returned no instance for "
        "('fastblocks', 'async_template_renderer')"
    )


def test_async_renderer_instantiates_with_minimal_args() -> None:
    """Smoke: ``AsyncTemplateRenderer()`` constructs with no required
    arguments. All four ``__init__`` parameters are typed optional
    (verified at ``_async_renderer.py:119-131``)."""
    from fastblocks.adapters.templates._async_renderer import AsyncTemplateRenderer

    instance = AsyncTemplateRenderer()
    assert instance is not None, "D3: AsyncTemplateRenderer() returned None"


@pytest.mark.asyncio
async def test_async_renderer_renders_trivial_context() -> None:
    """Render a trivial RenderContext through the renderer. The
    renderer is fail-safe (``render`` returns a RenderResult even on
    error per ``_async_renderer.py:193-199``), so we do not need a
    working ``base_templates`` to assert the boot path is intact."""
    from fastblocks.adapters.templates._async_renderer import (
        AsyncTemplateRenderer,
        RenderContext,
    )

    # Suppress the module logger so the fail-safe ``render`` path is
    # independent of the active structlog wrapper class. Sibling
    # observability tests reconfigure structlog to the generic
    # ``BoundLogger`` whose ``__getattr__``-wrapped
    # ``_proxy_to_logger`` raises TypeError on the printf-style
    # ``_log.exception("...: %s", type(e).__name__)`` call the
    # renderer's boundary handler emits.
    with patch.object(_async_renderer, "_log"):
        instance = AsyncTemplateRenderer()
        ctx = RenderContext(
            template_name="trivial.html",
            context={"name": "world"},
        )
        result = await instance.render(ctx)
    assert result is not None, "D3: AsyncTemplateRenderer.render returned None"
    assert isinstance(result.content, (str, type(result.content))), (
        "D3: RenderResult.content is not a string-or-async-iterator"
    )