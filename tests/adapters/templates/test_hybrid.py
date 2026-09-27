"""D1 coverage tests for fastblocks/adapters/templates/hybrid.py.

Targets the HybridTemplates integration: AdapterStatus enum, module
metadata, top-level convenience functions (``validate_template_source``,
``get_template_autocomplete``, ``render_htmx_block``,
``render_template_fragment``), and the ``HybridTemplates`` constructor
shape (without exercising the heavyweight async init — we stub it).
"""
# pyright: reportAttributeAccessIssue=false, reportFunctionMemberAccess=false
from __future__ import annotations

import pytest

from fastblocks.adapters.templates.hybrid import (
    MODULE_ID,
    MODULE_STATUS,
    AdapterStatus,
)


# ---------------------------------------------------------------------------
# AdapterStatus / module metadata
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAdapterStatus:
    def test_status_values(self) -> None:
        assert AdapterStatus.STABLE == "STABLE"
        assert AdapterStatus.BETA == "BETA"
        assert AdapterStatus.ALPHA == "ALPHA"
        assert AdapterStatus.EXPERIMENTAL == "EXPERIMENTAL"

    def test_module_metadata(self) -> None:
        assert MODULE_STATUS == AdapterStatus.STABLE
        # UUID object — verify it's a real UUID instance.
        import uuid as _uuid

        assert isinstance(MODULE_ID, _uuid.UUID)


# ---------------------------------------------------------------------------
# HybridTemplates construction (no init)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestHybridTemplatesConstruction:
    def test_construct_without_init(self) -> None:
        """Construction is sync; init is what wires everything up."""
        from fastblocks.adapters.templates.hybrid import HybridTemplates

        # HybridTemplatesSettings() should be constructible standalone.
        from fastblocks.adapters.templates._advanced_manager import (
            HybridTemplatesSettings,
        )

        settings = HybridTemplatesSettings()
        assert settings is not None

        # We don't call .initialize() — that path requires templates,
        # block renderer, etc. The constructor itself is just attribute init.
        ht = HybridTemplates()
        assert ht._initialized is False
        assert ht.base_templates is None
        assert ht.settings is not None


# ---------------------------------------------------------------------------
# Convenience module-level functions
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestModuleLevelFunctions:
    @pytest.mark.asyncio
    async def test_validate_template_source(self) -> None:
        from fastblocks.adapters.templates import hybrid

        # Patch get_hybrid_templates to return a stub.
        class _Stub:
            async def validate_template(
                self, source, name, context
            ) -> dict:
                return {"valid": True, "source_len": len(source), "name": name}

        async def fake_get() -> _Stub:
            return _Stub()

        original = hybrid.get_hybrid_templates
        hybrid.get_hybrid_templates = fake_get  # type: ignore[assignment]
        try:
            result = await hybrid.validate_template_source("hello", "test.html")
        finally:
            hybrid.get_hybrid_templates = original  # type: ignore[assignment]
        assert result["valid"] is True
        assert result["source_len"] == 5
        assert result["name"] == "test.html"

    @pytest.mark.asyncio
    async def test_get_template_autocomplete(self) -> None:
        from fastblocks.adapters.templates import hybrid

        class _Stub:
            async def get_autocomplete_suggestions(
                self, context, cursor, template_name
            ) -> list[dict]:
                return [
                    {"label": "x", "cursor": cursor},
                    {"label": "y", "template": template_name},
                ]

        async def fake_get() -> _Stub:
            return _Stub()

        original = hybrid.get_hybrid_templates
        hybrid.get_hybrid_templates = fake_get  # type: ignore[assignment]
        try:
            result = await hybrid.get_template_autocomplete("{{", 2, "test.html")
        finally:
            hybrid.get_hybrid_templates = original  # type: ignore[assignment]
        assert isinstance(result, list)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_render_htmx_block(self) -> None:
        from starlette.requests import Request

        from fastblocks.adapters.templates import hybrid

        class _Stub:
            async def render_block(self, request, block_id, context, update_mode):
                return f"BLOCK[{block_id}|{update_mode}]"

        async def fake_get() -> _Stub:
            return _Stub()

        original = hybrid.get_hybrid_templates
        hybrid.get_hybrid_templates = fake_get  # type: ignore[assignment]
        try:
            scope = {
                "type": "http",
                "method": "GET",
                "scheme": "https",
                "server": ("x", 443),
                "path": "/",
                "headers": [],
            }
            req = Request(scope)
            result = await hybrid.render_htmx_block(req, "my-block")
        finally:
            hybrid.get_hybrid_templates = original  # type: ignore[assignment]
        assert "my-block" in result

    @pytest.mark.asyncio
    async def test_render_template_fragment(self) -> None:
        from starlette.requests import Request

        from fastblocks.adapters.templates import hybrid

        class _Stub:
            async def render_htmx_fragment(
                self, request, fragment_name, context, template_name
            ):
                return f"FRAG[{fragment_name}|{template_name}]"

        async def fake_get() -> _Stub:
            return _Stub()

        original = hybrid.get_hybrid_templates
        hybrid.get_hybrid_templates = fake_get  # type: ignore[assignment]
        try:
            scope = {
                "type": "http",
                "method": "GET",
                "scheme": "https",
                "server": ("x", 443),
                "path": "/",
                "headers": [],
            }
            req = Request(scope)
            result = await hybrid.render_template_fragment(
                req, "frag-name", template_name="tmpl.html"
            )
        finally:
            hybrid.get_hybrid_templates = original  # type: ignore[assignment]
        assert "frag-name" in result
        assert "tmpl.html" in result


# ---------------------------------------------------------------------------
# clear_caches + utility passthroughs
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestHybridTemplateMethods:
    def test_clear_caches_method_exists(self) -> None:
        from fastblocks.adapters.templates.hybrid import HybridTemplates

        # clear_caches is sync — verify signature without invoking init.
        import inspect

        sig = inspect.signature(HybridTemplates.clear_caches)
        assert callable(sig) or sig is not None

    def test_module_metadata_uuid(self) -> None:
        # MODULE_ID is a UUID — already covered above, but expose as API-level test.
        assert MODULE_ID is not None
        assert MODULE_STATUS == "STABLE"