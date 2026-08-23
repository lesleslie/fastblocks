"""Tests for fastblocks/adapters/templates/_block_renderer.py.

Targets 156 missing statements before this file. Tests cover the
``BlockRegistry`` data structure (``register_block``, ``get_block``,
``list_blocks``, ``clear``) and the dataclass constructors.
"""

from __future__ import annotations

import pytest
from fastblocks.adapters.templates._block_renderer import (
    BlockDefinition,
    BlockRegistry,
    BlockRenderRequest,
    BlockRenderResult,
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