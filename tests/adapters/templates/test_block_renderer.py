"""Tests for fastblocks/adapters/templates/_block_renderer.py.

Wave D coverage backfill for the ``BlockRenderer`` class methods
(lines 178-598) that were uncovered in the prior report. The
``BlockRegistry`` and dataclass tests predate this file and remain
above; the new ``TestBlockRenderer`` class covers the public API
surface (init, ``register_htmx_block``, ``get_htmx_attributes_for_block``,
``get_block_info``, ``_build_htmx_headers``, ``create_*_block`` helpers,
plus the async ``get_block_dependencies`` / ``invalidate_dependent_blocks``
/ ``render_block`` paths with a mocked async_renderer).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastblocks.adapters.templates._block_renderer import (
    BlockDefinition,
    BlockRegistry,
    BlockRenderRequest,
    BlockRenderResult,
    BlockRenderer,
    BlockTrigger,
    BlockUpdateMode,
)


@pytest.mark.unit
class TestBlockRegistry:
    def test_register_and_get_block(self) -> None:
        registry = BlockRegistry()
        block = BlockDefinition(name="content", template_name="base.html")
        registry.register_block(block)
        assert registry.get_block("content") is block

    def test_get_block_returns_none_for_unknown(self) -> None:
        registry = BlockRegistry()
        assert registry.get_block("missing") is None

    def test_register_block_tracks_template(self) -> None:
        registry = BlockRegistry()
        block = BlockDefinition(name="x", template_name="page.html")
        registry.register_block(block)
        blocks = registry.get_blocks_for_template("page.html")
        assert len(blocks) == 1
        assert blocks[0].name == "x"

    def test_register_block_with_parent(self) -> None:
        registry = BlockRegistry()
        block = BlockDefinition(
            name="child",
            template_name="child.html",
            parent_template="parent.html",
        )
        registry.register_block(block)
        children = registry.get_child_blocks("parent.html")
        assert len(children) == 1

    def test_clear_empties_registry(self) -> None:
        registry = BlockRegistry()
        registry.register_block(BlockDefinition(name="a", template_name="x"))
        registry.register_block(BlockDefinition(name="b", template_name="y"))
        registry.clear()
        assert registry.list_blocks() == []


@pytest.mark.unit
class TestBlockDataclasses:
    def test_block_definition_constructs(self) -> None:
        block = BlockDefinition(
            name="content",
            template_name="base.html",
            trigger=BlockTrigger.MANUAL,
            update_mode=BlockUpdateMode.REPLACE,
        )
        assert block.name == "content"
        assert block.trigger == BlockTrigger.MANUAL
        assert block.update_mode == BlockUpdateMode.REPLACE

    def test_block_render_request_constructs(self) -> None:
        request = BlockRenderRequest(
            block_id="content",
            context={"foo": "bar"},
        )
        assert request.block_id == "content"
        assert request.context == {"foo": "bar"}

    def test_block_render_result_constructs(self) -> None:
        result = BlockRenderResult(
            content="<div>hi</div>",
            block_id="content",
            update_mode=BlockUpdateMode.REPLACE,
        )
        assert result.content == "<div>hi</div>"
        assert result.block_id == "content"


@pytest.mark.unit
class TestBlockRendererInit:
    """Cover BlockRenderer.__init__ body (lines 183-186).

    The constructor's default-arg path is the smallest possible entry
    point and exercises every assignment branch.
    """

    def test_init_default_arguments(self) -> None:
        renderer = BlockRenderer()
        assert renderer.async_renderer is None
        assert renderer.hybrid_manager is None
        assert isinstance(renderer.registry, BlockRegistry)
        assert renderer._render_cache == {}

    def test_init_with_async_renderer_only(self) -> None:
        sentinel = object()
        renderer = BlockRenderer(async_renderer=sentinel)
        assert renderer.async_renderer is sentinel
        assert renderer.hybrid_manager is None

    def test_init_with_both_arguments(self) -> None:
        renderer = BlockRenderer(async_renderer="ar", hybrid_manager="hm")
        assert renderer.async_renderer == "ar"
        assert renderer.hybrid_manager == "hm"


@pytest.mark.unit
class TestRegisterHTMXBlock:
    """Cover BlockRenderer.register_htmx_block (lines 480-524).

    Synchronous, returns a BlockDefinition, builds htmx_attrs from the
    trigger_mapping table, and registers the block in self.registry.
    """

    def test_register_htmx_block_minimal(self) -> None:
        renderer = BlockRenderer()
        block = renderer.register_htmx_block("greeting", "pages/home.html")
        assert block.name == "greeting"
        assert block.template_name == "pages/home.html"
        assert block.block_name == "greeting"
        assert block.htmx_attrs == {}
        assert block.css_selector == "#greeting"
        assert block.trigger == BlockTrigger.MANUAL
        assert block.update_mode == BlockUpdateMode.REPLACE
        # round-tripped through registry
        assert renderer.registry.get_block("greeting") is block

    def test_register_htmx_block_with_endpoint(self) -> None:
        renderer = BlockRenderer()
        block = renderer.register_htmx_block(
            "live",
            "tpl.html",
            htmx_endpoint="/api/live",
        )
        assert block.htmx_attrs == {"hx-get": "/api/live"}

    def test_register_htmx_block_with_auto_trigger(self) -> None:
        renderer = BlockRenderer()
        block = renderer.register_htmx_block(
            "auto",
            "tpl.html",
            htmx_endpoint="/x",
            trigger=BlockTrigger.AUTO,
        )
        assert block.htmx_attrs == {"hx-get": "/x", "hx-trigger": "load"}

    def test_register_htmx_block_with_lazy_trigger(self) -> None:
        renderer = BlockRenderer()
        block = renderer.register_htmx_block(
            "lazy",
            "tpl.html",
            htmx_endpoint="/x",
            trigger=BlockTrigger.LAZY,
        )
        assert block.htmx_attrs["hx-trigger"] == "revealed"

    def test_register_htmx_block_polling_default_interval(self) -> None:
        renderer = BlockRenderer()
        block = renderer.register_htmx_block(
            "poll",
            "tpl.html",
            htmx_endpoint="/x",
            trigger=BlockTrigger.POLLING,
        )
        # no auto_refresh -> "every 30s" fallback
        assert block.htmx_attrs["hx-trigger"] == "every 30s"

    def test_register_htmx_block_polling_with_interval(self) -> None:
        renderer = BlockRenderer()
        block = renderer.register_htmx_block(
            "poll",
            "tpl.html",
            htmx_endpoint="/x",
            trigger=BlockTrigger.POLLING,
            auto_refresh=10,
        )
        assert block.htmx_attrs["hx-trigger"] == "every 10s"

    def test_register_htmx_block_websocket_trigger(self) -> None:
        renderer = BlockRenderer()
        block = renderer.register_htmx_block(
            "ws",
            "tpl.html",
            htmx_endpoint="/stream",
            trigger=BlockTrigger.WEBSOCKET,
        )
        assert block.htmx_attrs["hx-trigger"] == "sse"

    def test_register_htmx_block_with_parent_template(self) -> None:
        renderer = BlockRenderer()
        block = renderer.register_htmx_block(
            "child",
            "child.html",
            parent_template="base.html",
        )
        assert block.parent_template == "base.html"


@pytest.mark.unit
class TestCreateHTMXHelpers:
    """Cover create_htmx_polling_block and create_lazy_loading_block."""

    def test_create_htmx_polling_block_sets_trigger_and_interval(self) -> None:
        renderer = BlockRenderer()
        coro = renderer.create_htmx_polling_block(
            "poll",
            "tpl.html",
            endpoint="/api/poll",
            interval=15,
        )
        # The function is ``async def`` (production surfaces it as a
        # coroutine even though the body is sync) — drain the coroutine
        # before inspecting the returned BlockDefinition.
        import asyncio

        block = asyncio.run(coro)
        assert block.trigger == BlockTrigger.POLLING
        assert block.auto_refresh == 15
        assert block.htmx_attrs["hx-get"] == "/api/poll"
        assert block.htmx_attrs["hx-trigger"] == "every 15s"

    def test_create_lazy_loading_block_sets_trigger(self) -> None:
        renderer = BlockRenderer()
        coro = renderer.create_lazy_loading_block(
            "lazy",
            "tpl.html",
            endpoint="/api/lazy",
        )
        import asyncio

        block = asyncio.run(coro)
        assert block.trigger == BlockTrigger.LAZY
        assert block.htmx_attrs["hx-trigger"] == "revealed"
        assert block.htmx_attrs["hx-get"] == "/api/lazy"


@pytest.mark.unit
class TestGetHTMXAttributesForBlock:
    """Cover get_htmx_attributes_for_block (lines 560-576)."""

    def test_returns_empty_string_for_unknown_block(self) -> None:
        renderer = BlockRenderer()
        assert renderer.get_htmx_attributes_for_block("missing") == ""

    def test_returns_attrs_and_id_for_known_block(self) -> None:
        renderer = BlockRenderer()
        renderer.register_htmx_block(
            "my_block",
            "tpl.html",
            htmx_endpoint="/x",
            trigger=BlockTrigger.LAZY,
        )
        rendered = renderer.get_htmx_attributes_for_block("my_block")
        assert 'hx-get="/x"' in rendered
        assert 'hx-trigger="revealed"' in rendered
        assert 'id="my-block"' in rendered

    def test_omits_id_when_css_selector_is_none(self) -> None:
        renderer = BlockRenderer()
        # Build a definition whose css_selector is None to hit the
        # `if block_def.css_selector:` False branch.
        renderer.registry.register_block(
            BlockDefinition(
                name="noid",
                template_name="tpl.html",
                css_selector=None,
            )
        )
        rendered = renderer.get_htmx_attributes_for_block("noid")
        assert "id=" not in rendered


@pytest.mark.unit
class TestBuildHTMXHeaders:
    """Cover BlockRenderer._build_htmx_headers (lines 346-380)."""

    def test_target_header_uses_request_override(self) -> None:
        renderer = BlockRenderer()
        block = BlockDefinition(name="b", template_name="t")
        request = BlockRenderRequest(block_id="b", target_selector="#custom")
        headers = renderer._build_htmx_headers(block, request)
        assert headers["HX-Target"] == "#custom"

    def test_target_header_falls_back_to_block_selector(self) -> None:
        renderer = BlockRenderer()
        block = BlockDefinition(
            name="b",
            template_name="t",
            css_selector="#b",
        )
        request = BlockRenderRequest(block_id="b")
        headers = renderer._build_htmx_headers(block, request)
        assert headers["HX-Target"] == "#b"

    def test_swap_mode_for_replace(self) -> None:
        renderer = BlockRenderer()
        block = BlockDefinition(name="b", template_name="t")
        request = BlockRenderRequest(block_id="b")
        headers = renderer._build_htmx_headers(block, request)
        assert headers["HX-Swap"] == "innerHTML"

    @pytest.mark.parametrize(
        "mode,expected",
        [
            (BlockUpdateMode.APPEND, "beforeend"),
            (BlockUpdateMode.PREPEND, "afterbegin"),
            (BlockUpdateMode.INNER, "innerHTML"),
            (BlockUpdateMode.OUTER, "outerHTML"),
            (BlockUpdateMode.DELETE, "delete"),
            (BlockUpdateMode.NONE, "innerHTML"),
        ],
    )
    def test_swap_mode_mapping(self, mode, expected) -> None:
        renderer = BlockRenderer()
        block = BlockDefinition(name="b", template_name="t")
        request = BlockRenderRequest(block_id="b", update_mode=mode)
        headers = renderer._build_htmx_headers(block, request)
        assert headers["HX-Swap"] == expected

    def test_custom_htmx_attrs_are_promoted_to_headers(self) -> None:
        renderer = BlockRenderer()
        block = BlockDefinition(
            name="b",
            template_name="t",
            htmx_attrs={"hx-confirm": "really?", "hx-get": "/x"},
        )
        request = BlockRenderRequest(block_id="b")
        headers = renderer._build_htmx_headers(block, request)
        assert headers["HX-Confirm"] == "really?"
        assert headers["HX-Get"] == "/x"

    def test_auto_refresh_adds_refresh_headers(self) -> None:
        renderer = BlockRenderer()
        block = BlockDefinition(name="auto_b", template_name="t", auto_refresh=7)
        request = BlockRenderRequest(block_id="auto_b")
        headers = renderer._build_htmx_headers(block, request)
        assert headers["HX-Trigger"] == "refresh-block-auto_b"
        assert headers["HX-Refresh"] == "7"


@pytest.mark.asyncio
@pytest.mark.unit
class TestGetBlockInfo:
    """Cover BlockRenderer.get_block_info (lines 578-598)."""

    async def test_returns_empty_dict_for_missing_block(self) -> None:
        renderer = BlockRenderer()
        assert await renderer.get_block_info("missing") == {}

    async def test_returns_full_info_for_known_block(self) -> None:
        renderer = BlockRenderer()
        renderer.registry.register_block(
            BlockDefinition(
                name="b",
                template_name="t.html",
                block_name="content",
                css_selector="#c",
                htmx_attrs={"hx-get": "/x"},
                cache_ttl=120,
            )
        )
        info = await renderer.get_block_info("b")
        assert info["name"] == "b"
        assert info["template_name"] == "t.html"
        assert info["block_name"] == "content"
        assert info["css_selector"] == "#c"
        assert info["htmx_attrs"] == {"hx-get": "/x"}
        assert info["cache_ttl"] == 120
        # dependencies is an empty list when no hybrid_manager and no parent
        assert info["dependencies"] == []


@pytest.mark.asyncio
@pytest.mark.unit
class TestGetBlockDependencies:
    """Cover BlockRenderer.get_block_dependencies (lines 433-455)."""

    async def test_returns_empty_for_missing_block(self) -> None:
        renderer = BlockRenderer()
        assert await renderer.get_block_dependencies("missing") == []

    async def test_returns_parent_block_names(self) -> None:
        renderer = BlockRenderer()
        renderer.registry.register_block(
            BlockDefinition(
                name="parent_block",
                template_name="base.html",
            )
        )
        renderer.registry.register_block(
            BlockDefinition(
                name="child_block",
                template_name="child.html",
                parent_template="base.html",
            )
        )
        deps = await renderer.get_block_dependencies("child_block")
        assert "parent_block" in deps

    async def test_no_dependencies_when_no_parent(self) -> None:
        renderer = BlockRenderer()
        renderer.registry.register_block(
            BlockDefinition(name="solo", template_name="t.html")
        )
        assert await renderer.get_block_dependencies("solo") == []


@pytest.mark.asyncio
@pytest.mark.unit
class TestInvalidateDependentBlocks:
    """Cover BlockRenderer.invalidate_dependent_blocks (lines 457-478)."""

    async def test_invalidates_block_via_dependency_list(self) -> None:
        renderer = BlockRenderer()
        target = BlockDefinition(name="target", template_name="t.html")
        renderer.registry.register_block(target)
        dependent = BlockDefinition(
            name="dependent",
            template_name="d.html",
            dependencies={"target"},
        )
        renderer.registry.register_block(dependent)
        # Seed the render cache with a key matching dependent's block name.
        renderer._render_cache["block:dependent:abc"] = ("x", 0.0)

        invalidated = await renderer.invalidate_dependent_blocks("target")
        assert invalidated == ["dependent"]
        # dependent's cache entry was purged
        assert "block:dependent:abc" not in renderer._render_cache

    async def test_returns_empty_when_no_dependents(self) -> None:
        renderer = BlockRenderer()
        renderer.registry.register_block(
            BlockDefinition(name="solo", template_name="t.html")
        )
        assert await renderer.invalidate_dependent_blocks("solo") == []


@pytest.mark.asyncio
@pytest.mark.unit
class TestRenderBlock:
    """Cover BlockRenderer.render_block (lines 307-344) via a mocked async_renderer."""

    async def test_render_block_returns_block_render_result(self) -> None:
        renderer = BlockRenderer()
        renderer.async_renderer = MagicMock()
        renderer.async_renderer.render = AsyncMock(
            return_value=MagicMock(content="<p>hi</p>", cache_hit=False)
        )
        renderer.registry.register_block(
            BlockDefinition(name="b", template_name="t.html", block_name="content")
        )
        request = BlockRenderRequest(block_id="b", context={"x": 1})
        result = await renderer.render_block(request)
        assert isinstance(result, BlockRenderResult)
        assert result.content == "<p>hi</p>"
        assert result.block_id == "b"
        assert result.cache_hit is False
        assert result.dependencies == []

    async def test_render_block_raises_for_unknown_block(self) -> None:
        renderer = BlockRenderer()
        renderer.async_renderer = MagicMock()
        with pytest.raises(ValueError, match="not found"):
            await renderer.render_block(BlockRenderRequest(block_id="missing"))

    async def test_render_block_propagates_cache_hit(self) -> None:
        renderer = BlockRenderer()
        renderer.async_renderer = MagicMock()
        renderer.async_renderer.render = AsyncMock(
            return_value=MagicMock(content="<p>cached</p>", cache_hit=True)
        )
        renderer.registry.register_block(
            BlockDefinition(name="b", template_name="t.html")
        )
        result = await renderer.render_block(BlockRenderRequest(block_id="b"))
        assert result.cache_hit is True
        assert result.content == "<p>cached</p>"


@pytest.mark.unit
class TestExtractHTMXAttrs:
    """Cover BlockRenderer._extract_htmx_attrs (lines 269-305).

    Pure synchronous helper — pass a templated source string and a
    block name, get back a dict of HTMX attributes.
    """

    def test_returns_empty_when_block_start_missing(self) -> None:
        renderer = BlockRenderer()
        result = renderer._extract_htmx_attrs("no block here", "content")
        assert result == {}

    def test_returns_empty_when_block_end_missing(self) -> None:
        renderer = BlockRenderer()
        # open block, no closing tag
        source = "[% block content %]\nunclosed"
        assert renderer._extract_htmx_attrs(source, "content") == {}

    def test_extracts_single_hx_get(self) -> None:
        renderer = BlockRenderer()
        source = (
            "[% block content %]\n"
            '<button hx-get="/api/data">click</button>\n'
            "[% endblock %]"
        )
        attrs = renderer._extract_htmx_attrs(source, "content")
        assert attrs == {"hx-get": "/api/data"}

    def test_extracts_multiple_hx_attributes(self) -> None:
        renderer = BlockRenderer()
        source = (
            "[% block content %]\n"
            '<div hx-get="/x" hx-target="#t" hx-swap="outerHTML" '
            'hx-trigger="click" hx-post="/y">body</div>\n'
            "[% endblock %]"
        )
        attrs = renderer._extract_htmx_attrs(source, "content")
        assert attrs["hx-get"] == "/x"
        assert attrs["hx-target"] == "#t"
        assert attrs["hx-swap"] == "outerHTML"
        assert attrs["hx-trigger"] == "click"
        # hx-post is in the pattern dict but uses regex; verify it parses
        assert attrs["hx-post"] == "/y"

    def test_attributes_without_block_not_extracted(self) -> None:
        renderer = BlockRenderer()
        # HTMX attribute exists, but NOT inside the named block
        source = (
            "[% block other %]\n"
            '<button hx-get="/other">x</button>\n'
            "[% endblock %]\n"
            '<button hx-get="/api">y</button>\n'
        )
        attrs = renderer._extract_htmx_attrs(source, "content")
        assert attrs == {}


@pytest.mark.asyncio
@pytest.mark.unit
class TestDiscoverBlocks:
    """Cover BlockRenderer._discover_blocks early-return paths."""

    async def test_returns_when_no_async_renderer(self) -> None:
        renderer = BlockRenderer()
        # async_renderer is None -> early return on line 215
        assert await renderer._discover_blocks() is None

    async def test_returns_when_no_base_templates(self) -> None:
        renderer = BlockRenderer()
        renderer.async_renderer = MagicMock()
        renderer.async_renderer.base_templates = None
        assert await renderer._discover_blocks() is None

    async def test_returns_when_no_env_loader(self) -> None:
        renderer = BlockRenderer()
        renderer.async_renderer = MagicMock()
        renderer.async_renderer.base_templates = MagicMock()
        renderer.async_renderer.base_templates.app.env.loader = None
        assert await renderer._discover_blocks() is None


@pytest.mark.asyncio
@pytest.mark.unit
class TestInitialize:
    """Cover BlockRenderer.initialize paths (lines 188-210)."""

    async def test_initialize_skips_when_async_renderer_provided(self) -> None:
        renderer = BlockRenderer(async_renderer=MagicMock())
        renderer.hybrid_manager = MagicMock()
        # Stub out _discover_blocks so we don't actually walk templates.
        renderer._discover_blocks = AsyncMock()
        await renderer.initialize()
        renderer._discover_blocks.assert_awaited_once()

    async def test_initialize_resolves_hybrid_manager_via_resolver(self) -> None:
        renderer = BlockRenderer(async_renderer=MagicMock())
        sentinel_hybrid = MagicMock()
        renderer.hybrid_manager = sentinel_hybrid
        renderer._discover_blocks = AsyncMock()
        await renderer.initialize()
        # The provided hybrid_manager was kept (no fallback fired).
        assert renderer.hybrid_manager is sentinel_hybrid


@pytest.mark.asyncio
@pytest.mark.unit
class TestRenderFragmentComposition:
    """Cover BlockRenderer.render_fragment_composition (lines 382-431)."""

    async def test_returns_html_response_with_composition_header(self) -> None:
        renderer = BlockRenderer()
        # No fragments registered -> empty body, but header still set.
        response = await renderer.render_fragment_composition(
            composition_name="my_comp",
            fragments=[],
        )
        assert response.headers["HX-Composition"] == "my_comp"
        assert response.body == b""

    async def test_renders_matched_block_content(self) -> None:
        renderer = BlockRenderer()
        renderer.async_renderer = MagicMock()
        renderer.async_renderer.render = AsyncMock(
            return_value=MagicMock(content="<p>hi</p>", cache_hit=False)
        )
        renderer.registry.register_block(
            BlockDefinition(name="tpl.html:greet", template_name="tpl.html")
        )
        response = await renderer.render_fragment_composition(
            composition_name="comp",
            fragments=["greet"],
        )
        assert response.headers["HX-Composition"] == "comp"
        assert b"<p>hi</p>" in response.body

    async def test_unmatched_fragment_produces_no_output(self) -> None:
        renderer = BlockRenderer()
        renderer.async_renderer = MagicMock()
        renderer.async_renderer.render = AsyncMock(
            return_value=MagicMock(content="ignored", cache_hit=False)
        )
        # No matching block; the per-fragment try/except swallows nothing,
        # but matching_blocks is empty so nothing is appended.
        response = await renderer.render_fragment_composition(
            composition_name="c",
            fragments=["nope"],
        )
        assert response.body == b""

    async def test_fragment_render_failure_does_not_collapse(self) -> None:
        renderer = BlockRenderer()
        renderer.async_renderer = MagicMock()
        renderer.async_renderer.render = AsyncMock(
            side_effect=RuntimeError("boom")
        )
        renderer.registry.register_block(
            BlockDefinition(name="tpl:bad", template_name="tpl.html")
        )
        response = await renderer.render_fragment_composition(
            composition_name="c",
            fragments=["bad"],
        )
        # The fragment produced an HTML comment marking failure rather
        # than the whole composition raising.
        assert b"Fragment bad failed to render" in response.body


@pytest.mark.asyncio
@pytest.mark.unit
class TestGetBlockDependenciesHybridManager:
    """Cover the hybrid_manager branch of get_block_dependencies (lines 442-446)."""

    async def test_returns_template_deps_when_hybrid_manager_set(self) -> None:
        renderer = BlockRenderer()
        renderer.hybrid_manager = MagicMock()
        renderer.hybrid_manager.get_template_dependencies = AsyncMock(
            return_value=["base.html", "partials/header.html"]
        )
        renderer.registry.register_block(
            BlockDefinition(name="solo", template_name="t.html")
        )
        deps = await renderer.get_block_dependencies("solo")
        assert "base.html" in deps
        assert "partials/header.html" in deps
