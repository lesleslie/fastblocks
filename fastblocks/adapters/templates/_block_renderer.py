"""Block Rendering System for HTMX Partials and Fragments.

This module provides specialized block rendering for HTMX interactions:
- Named template blocks for partial updates
- Fragment composition and inheritance
- Dynamic block swapping and updates
- Progressive enhancement support
- Block-level caching and optimization

Requirements:
- jinja2>=3.1.6
- jinja2-async-environment>=0.14.3
- starlette-async-jinja>=1.12.4

Author: lesleslie <les@wedgwoodwebworks.com>
Created: 2025-01-12
"""

import asyncio
import typing as t
from contextlib import suppress
from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID

from acb.adapters import AdapterStatus
from acb.depends import depends
from jinja2 import Environment, meta
from jinja2.nodes import Block, Extends, Include
from starlette.requests import Request
from starlette.responses import HTMLResponse

from ._advanced_manager import HybridTemplatesManager
from ._async_renderer import AsyncTemplateRenderer, RenderContext, RenderMode


class BlockUpdateMode(Enum):
    """Block update modes for HTMX."""

    REPLACE = "replace"  # Replace entire block
    APPEND = "append"  # Append to block content
    PREPEND = "prepend"  # Prepend to block content
    INNER = "inner"  # Replace inner content only
    OUTER = "outer"  # Replace including block element
    DELETE = "delete"  # Remove the block
    NONE = "none"  # No update


class BlockTrigger(Enum):
    """Block rendering triggers."""

    MANUAL = "manual"  # Manually triggered
    AUTO = "auto"  # Auto-triggered on events
    LAZY = "lazy"  # Lazy-loaded when visible
    POLLING = "polling"  # Periodically updated
    WEBSOCKET = "websocket"  # Updated via WebSocket


@dataclass
class BlockDefinition:
    """Definition of a renderable block."""

    name: str
    template_name: str
    block_name: str | None = None
    parent_template: str | None = None
    dependencies: set[str] = field(default_factory=set)
    variables: set[str] = field(default_factory=set)
    update_mode: BlockUpdateMode = BlockUpdateMode.REPLACE
    trigger: BlockTrigger = BlockTrigger.MANUAL
    cache_key: str | None = None
    cache_ttl: int = 300
    htmx_attrs: dict[str, str] = field(default_factory=dict)
    css_selector: str | None = None
    auto_refresh: int | None = None  # Refresh interval in seconds


@dataclass
class BlockRenderRequest:
    """Request to render a specific block."""

    block_id: str
    context: dict[str, t.Any] = field(default_factory=dict)
    request: Request | None = None
    target_selector: str | None = None
    update_mode: BlockUpdateMode = BlockUpdateMode.REPLACE
    headers: dict[str, str] = field(default_factory=dict)
    validate: bool = False


@dataclass
class BlockRenderResult:
    """Result of block rendering."""

    content: str
    block_id: str
    update_mode: BlockUpdateMode
    target_selector: str | None = None
    htmx_headers: dict[str, str] = field(default_factory=dict)
    cache_hit: bool = False
    render_time: float = 0.0
    dependencies: list[str] = field(default_factory=list)


class BlockRegistry:
    """Registry for managing template blocks."""

    def __init__(self) -> None:
        self._blocks: dict[str, BlockDefinition] = {}
        self._block_hierarchy: dict[str, list[str]] = {}
        self._template_blocks: dict[str, list[str]] = {}

    def register_block(self, block_def: BlockDefinition) -> None:
        """Register a block definition."""
        self._blocks[block_def.name] = block_def

        # Track blocks by template
        if block_def.template_name not in self._template_blocks:
            self._template_blocks[block_def.template_name] = []
        self._template_blocks[block_def.template_name].append(block_def.name)

        # Track hierarchy if parent exists
        if block_def.parent_template:
            if block_def.parent_template not in self._block_hierarchy:
                self._block_hierarchy[block_def.parent_template] = []
            self._block_hierarchy[block_def.parent_template].append(block_def.name)

    def get_block(self, block_id: str) -> BlockDefinition | None:
        """Get block definition by ID."""
        return self._blocks.get(block_id)

    def get_blocks_for_template(self, template_name: str) -> list[BlockDefinition]:
        """Get all blocks for a template."""
        block_ids = self._template_blocks.get(template_name, [])
        return [
            self._blocks[block_id] for block_id in block_ids if block_id in self._blocks
        ]

    def get_child_blocks(self, template_name: str) -> list[BlockDefinition]:
        """Get child blocks that depend on a template."""
        child_ids = self._block_hierarchy.get(template_name, [])
        return [
            self._blocks[block_id] for block_id in child_ids if block_id in self._blocks
        ]

    def list_blocks(self) -> list[BlockDefinition]:
        """List all registered blocks."""
        return list(self._blocks.values())

    def clear(self) -> None:
        """Clear all registered blocks."""
        self._blocks.clear()
        self._block_hierarchy.clear()
        self._template_blocks.clear()


class BlockRenderer:
    """Specialized renderer for template blocks and fragments."""

    def __init__(
        self,
        async_renderer: AsyncTemplateRenderer | None = None,
        hybrid_manager: HybridTemplatesManager | None = None,
    ) -> None:
        self.async_renderer = async_renderer
        self.hybrid_manager = hybrid_manager
        self.registry = BlockRegistry()
        self._render_cache: dict[str, tuple[str, float]] = {}

    async def initialize(self) -> None:
        """Initialize the block renderer."""
        if not self.async_renderer:
            self.async_renderer = AsyncTemplateRenderer()
            await self.async_renderer.initialize()

        if not self.hybrid_manager:
            try:
                self.hybrid_manager = await depends.get("hybrid_template_manager")
            except Exception:
                self.hybrid_manager = HybridTemplatesManager()
                await self.hybrid_manager.initialize()

        # Auto-discover blocks from templates
        await self._discover_blocks()

    async def _discover_blocks(self) -> None:
        """Auto-discover blocks from template files."""
        if not self.async_renderer or not self.async_renderer.base_templates:
            return

        env = self.async_renderer.base_templates.app.env  # type: ignore[union-attr]
        if not env.loader:
            return

        with suppress(Exception):
            template_names = await asyncio.get_event_loop().run_in_executor(
                None, env.loader.list_templates
            )

            for template_name in template_names:
                await self._analyze_template_blocks(template_name, env)

    async def _analyze_template_blocks(
        self, template_name: str, env: Environment
    ) -> None:
        """Analyze template and register its blocks."""
        with suppress(Exception):
            source, _, _ = env.loader.get_source(env, template_name)  # type: ignore[union-attr,misc]
            parsed = env.parse(source, template_name)

            # Find all block nodes
            for node in parsed.find_all(Block):
                block_def = BlockDefinition(
                    name=f"{template_name}:{node.name}",
                    template_name=template_name,
                    block_name=node.name,
                    css_selector=f"#{node.name.replace('_', '-')}",
                )

                # Extract variables used in this block
                # find_undeclared_variables accepts Block nodes at runtime
                block_def.variables = meta.find_undeclared_variables(
                    t.cast(t.Any, node)
                )

                # Check for HTMX attributes in block content
                block_def.htmx_attrs = self._extract_htmx_attrs(source, node.name)

                self.registry.register_block(block_def)

            # Find extends and includes for hierarchy
            for node in t.cast(t.Any, parsed.find_all((Extends, Include))):
                # Template attribute value extraction at runtime
                if hasattr(node, "template") and hasattr(node.template, "value"):
                    parent_template = node.template.value  # type: ignore[attr-defined]
                    # Register dependency relationship
                    for block_def in self.registry.get_blocks_for_template(
                        template_name
                    ):
                        block_def.parent_template = parent_template

    def _extract_htmx_attrs(self, source: str, block_name: str) -> dict[str, str]:
        """Extract HTMX attributes from block content."""
        attrs: dict[str, str] = {}

        # Look for block start
        block_start = f"[% block {block_name} %]"
        block_end = "[% endblock %]"

        start_idx = source.find(block_start)
        if start_idx == -1:
            return attrs

        end_idx = source.find(block_end, start_idx)
        if end_idx == -1:
            return attrs

        block_content = source[start_idx:end_idx]

        # Extract common HTMX patterns
        import re

        htmx_patterns = {
            "hx-get": r'hx-get="([^"]*)"',
            "hx-post": r'hx-post="([^"]*)"',
            "hx-target": r'hx-target="([^"]*)"',
            "hx-swap": r'hx-swap="([^"]*)"',
            "hx-trigger": r'hx-trigger="([^"]*)"',
        }

        for attr_name, pattern in htmx_patterns.items():
            matches = re.findall(
                pattern, block_content
            )  # REGEX OK: extract HTMX attributes from template content
            if matches:
                attrs[attr_name] = matches[0]

        return attrs

    async def render_block(self, request: BlockRenderRequest) -> BlockRenderResult:
        """Render a specific block."""
        import time

        start_time = time.time()

        block_def = self.registry.get_block(request.block_id)
        if not block_def:
            raise ValueError(f"Block '{request.block_id}' not found")

        # Build render context
        render_context = RenderContext(
            template_name=block_def.template_name,
            context=request.context,
            request=request.request,
            mode=RenderMode.BLOCK,
            block_name=block_def.block_name,
            validate_template=request.validate,
            cache_key=f"block:{request.block_id}:{hash(str(request.context))}",
            cache_ttl=block_def.cache_ttl,
        )

        # Render the block
        result = await self.async_renderer.render(render_context)  # type: ignore[union-attr]

        # Build HTMX headers
        htmx_headers = self._build_htmx_headers(block_def, request)

        return BlockRenderResult(
            content=t.cast(str, result.content),
            block_id=request.block_id,
            update_mode=request.update_mode,
            target_selector=request.target_selector or block_def.css_selector,
            htmx_headers=htmx_headers,
            cache_hit=result.cache_hit,
            render_time=time.time() - start_time,
            dependencies=list(block_def.dependencies),
        )

    def _build_htmx_headers(
        self, block_def: BlockDefinition, request: BlockRenderRequest
    ) -> dict[str, str]:
        """Build HTMX response headers for block updates."""
        headers = {}

        # Set target if specified
        target = request.target_selector or block_def.css_selector
        if target:
            headers["HX-Target"] = target

        # Set swap mode
        swap_modes = {
            BlockUpdateMode.REPLACE: "innerHTML",
            BlockUpdateMode.APPEND: "beforeend",
            BlockUpdateMode.PREPEND: "afterbegin",
            BlockUpdateMode.INNER: "innerHTML",
            BlockUpdateMode.OUTER: "outerHTML",
            BlockUpdateMode.DELETE: "delete",
        }

        swap_mode = swap_modes.get(request.update_mode, "innerHTML")
        headers["HX-Swap"] = swap_mode

        # Add any custom HTMX attributes from block definition
        for attr_name, attr_value in block_def.htmx_attrs.items():
            header_name = f"HX-{attr_name.replace('hx-', '').title()}"
            headers[header_name] = attr_value

        # Add refresh headers for auto-updating blocks
        if block_def.auto_refresh:
            headers["HX-Trigger"] = f"refresh-block-{block_def.name}"
            headers["HX-Refresh"] = str(block_def.auto_refresh)

        return headers

    async def render_fragment_composition(
        self,
        composition_name: str,
        fragments: list[str],
        context: dict[str, t.Any] | None = None,
        request: Request | None = None,
    ) -> HTMLResponse:
        """Render a composition of multiple fragments."""
        if not context:
            context = {}

        rendered_fragments = []

        for fragment_name in fragments:
            try:
                # Find block definition for this fragment
                matching_blocks = [
                    block
                    for block in self.registry.list_blocks()
                    if fragment_name in block.name or block.block_name == fragment_name
                ]

                if matching_blocks:
                    block_def = matching_blocks[0]
                    request_obj = BlockRenderRequest(
                        block_id=block_def.name, context=context, request=request
                    )

                    result = await self.render_block(request_obj)
                    rendered_fragments.append(result.content)

            except Exception:
                # Skip failed fragments but continue with others
                rendered_fragments.append(
                    f"<!-- Fragment {fragment_name} failed to render -->"
                )

        # Combine all fragments
        combined_content = "\n".join(rendered_fragments)

        return HTMLResponse(
            content=combined_content, headers={"HX-Composition": composition_name}
        )

    async def get_block_dependencies(self, block_id: str) -> list[str]:
        """Get dependencies for a block (other blocks it depends on)."""
        block_def = self.registry.get_block(block_id)
        if not block_def:
            return []

        dependencies = []

        # Add template dependencies
        if self.hybrid_manager:
            template_deps = await self.hybrid_manager.get_template_dependencies(
                block_def.template_name
            )
            dependencies.extend(template_deps)

        # Add parent template dependencies
        if block_def.parent_template:
            parent_blocks = self.registry.get_blocks_for_template(
                block_def.parent_template
            )
            dependencies.extend([block.name for block in parent_blocks])

        return dependencies

    async def invalidate_dependent_blocks(self, block_id: str) -> list[str]:
        """Invalidate blocks that depend on the given block."""
        invalidated = []

        # Find blocks that depend on this one
        for block_def in self.registry.list_blocks():
            if (
                block_id in block_def.dependencies
                or block_id in await self.get_block_dependencies(block_def.name)
            ):
                # Clear cache for dependent block
                cache_keys_to_remove = [
                    key
                    for key in self._render_cache.keys()
                    if f"block:{block_def.name}" in key
                ]
                for key in cache_keys_to_remove:
                    del self._render_cache[key]

                invalidated.append(block_def.name)

        return invalidated

    def register_htmx_block(
        self,
        name: str,
        template_name: str,
        block_name: str | None = None,
        htmx_endpoint: str | None = None,
        update_mode: BlockUpdateMode = BlockUpdateMode.REPLACE,
        trigger: BlockTrigger = BlockTrigger.MANUAL,
        auto_refresh: int | None = None,
        **kwargs: t.Any,
    ) -> BlockDefinition:
        """Register a block optimized for HTMX interactions."""
        # Build HTMX attributes
        htmx_attrs = {}
        if htmx_endpoint:
            htmx_attrs["hx-get"] = htmx_endpoint

        # Set appropriate triggers
        trigger_mapping = {
            BlockTrigger.AUTO: "load",
            BlockTrigger.LAZY: "revealed",
            BlockTrigger.POLLING: f"every {auto_refresh}s"
            if auto_refresh
            else "every 30s",
            BlockTrigger.WEBSOCKET: "sse",
        }

        if trigger != BlockTrigger.MANUAL and trigger in trigger_mapping:
            htmx_attrs["hx-trigger"] = trigger_mapping[trigger]

        # Create block definition
        block_def = BlockDefinition(
            name=name,
            template_name=template_name,
            block_name=block_name or name,
            update_mode=update_mode,
            trigger=trigger,
            htmx_attrs=htmx_attrs,
            auto_refresh=auto_refresh,
            css_selector=f"#{name.replace('_', '-')}",
            **kwargs,
        )

        self.registry.register_block(block_def)
        return block_def

    async def create_htmx_polling_block(
        self,
        name: str,
        template_name: str,
        endpoint: str,
        interval: int = 30,
        **kwargs: t.Any,
    ) -> BlockDefinition:
        """Create a block that polls for updates via HTMX."""
        return self.register_htmx_block(
            name=name,
            template_name=template_name,
            htmx_endpoint=endpoint,
            trigger=BlockTrigger.POLLING,
            auto_refresh=interval,
            **kwargs,
        )

    async def create_lazy_loading_block(
        self,
        name: str,
        template_name: str,
        endpoint: str,
        **kwargs: t.Any,
    ) -> BlockDefinition:
        """Create a lazy-loading block that loads when visible."""
        return self.register_htmx_block(
            name=name,
            template_name=template_name,
            htmx_endpoint=endpoint,
            trigger=BlockTrigger.LAZY,
            **kwargs,
        )

    def get_htmx_attributes_for_block(self, block_id: str) -> str:
        """Get HTMX attributes string for a block."""
        block_def = self.registry.get_block(block_id)
        if not block_def:
            return ""

        attrs = [
            f'{attr_name}="{attr_value}"'
            for attr_name, attr_value in block_def.htmx_attrs.items()
        ]

        # Add ID for targeting
        if block_def.css_selector:
            selector_id = block_def.css_selector.lstrip("#")
            attrs.append(f'id="{selector_id}"')

        return " ".join(attrs)

    async def get_block_info(self, block_id: str) -> dict[str, t.Any]:
        """Get detailed information about a block."""
        block_def = self.registry.get_block(block_id)
        if not block_def:
            return {}

        dependencies = await self.get_block_dependencies(block_id)

        return {
            "name": block_def.name,
            "template_name": block_def.template_name,
            "block_name": block_def.block_name,
            "update_mode": block_def.update_mode.value,
            "trigger": block_def.trigger.value,
            "css_selector": block_def.css_selector,
            "htmx_attrs": block_def.htmx_attrs,
            "auto_refresh": block_def.auto_refresh,
            "cache_ttl": block_def.cache_ttl,
            "variables": list(block_def.variables),
            "dependencies": dependencies,
        }


MODULE_ID = UUID("01937d89-1234-7890-abcd-1234567890ab")
MODULE_STATUS = AdapterStatus.STABLE

# Register the block renderer
with suppress(Exception):
    depends.set("block_renderer", BlockRenderer)
