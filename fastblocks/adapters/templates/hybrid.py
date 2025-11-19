"""Hybrid Template Management Integration Module.

This module integrates all Hybrid template management components:
- Hybrid Template Manager with validation and autocomplete
- Async Template Renderer with performance optimization
- Block Renderer for HTMX fragments and partials
- Enhanced filters for secondary adapters
- Template CLI tools and utilities

This provides a unified interface for FastBlocks Week 7-8 template features.

Requirements:
- jinja2>=3.1.6
- jinja2-async-environment>=0.14.3
- starlette-async-jinja>=1.12.4

Author: lesleslie <les@wedgwoodwebworks.com>
Created: 2025-01-12
"""

import typing as t
from contextlib import suppress
from uuid import UUID

from acb.adapters import AdapterStatus
from acb.depends import depends
from starlette.requests import Request
from starlette.responses import Response

from ._advanced_manager import HybridTemplatesManager, HybridTemplatesSettings
from ._async_filters import FASTBLOCKS_ASYNC_FILTERS
from ._async_renderer import AsyncTemplateRenderer, RenderContext, RenderMode
from ._block_renderer import BlockRenderer, BlockRenderRequest, BlockUpdateMode
from ._enhanced_filters import ENHANCED_ASYNC_FILTERS, ENHANCED_FILTERS
from ._filters import FASTBLOCKS_FILTERS
from .jinja2 import Templates


class HybridTemplates:
    """Unified interface for Hybrid template management features."""

    def __init__(self) -> None:
        self.settings = HybridTemplatesSettings()
        self.base_templates: Templates | None = None
        self.hybrid_manager: HybridTemplatesManager | None = None
        self.async_renderer: AsyncTemplateRenderer | None = None
        self.block_renderer: BlockRenderer | None = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize all components."""
        if self._initialized:
            return

        # Get or create base templates
        try:
            self.base_templates = depends.get("templates")
        except Exception:
            self.base_templates = Templates()
            await self.base_templates.init()

        # Initialize Hybrid manager
        self.hybrid_manager = HybridTemplatesManager(self.settings)
        await self.hybrid_manager.initialize()

        # Initialize async renderer
        self.async_renderer = AsyncTemplateRenderer(
            base_templates=self.base_templates, hybrid_manager=self.hybrid_manager
        )
        await self.async_renderer.initialize()

        # Initialize block renderer
        self.block_renderer = BlockRenderer(
            async_renderer=self.async_renderer, hybrid_manager=self.hybrid_manager
        )
        await self.block_renderer.initialize()

        # Register all filters
        await self._register_filters()

        self._initialized = True

    async def _register_filters(self) -> None:
        """Register all template filters with Jinja2 environments."""
        if not self.base_templates:
            return

        all_filters = FASTBLOCKS_FILTERS | ENHANCED_FILTERS

        all_async_filters = FASTBLOCKS_ASYNC_FILTERS | ENHANCED_ASYNC_FILTERS

        # Register with main app environment
        if self.base_templates.app and hasattr(self.base_templates.app.env, "filters"):
            for name, filter_func in all_filters.items():
                self.base_templates.app.env.filters[name] = filter_func

            for name, async_filter_func in all_async_filters.items():
                self.base_templates.app.env.filters[name] = async_filter_func

        # Register with admin environment if available
        if self.base_templates.admin and hasattr(
            self.base_templates.admin.env, "filters"
        ):
            for name, filter_func in all_filters.items():
                self.base_templates.admin.env.filters[name] = filter_func

            for name, async_filter_func in all_async_filters.items():
                self.base_templates.admin.env.filters[name] = async_filter_func

    # Template Validation API
    async def validate_template(
        self,
        template_source: str,
        template_name: str = "unknown",
        context: dict[str, t.Any] | None = None,
    ) -> dict[str, t.Any]:
        """Validate template and return results."""
        if not self.hybrid_manager:
            await self.initialize()
        assert self.hybrid_manager is not None

        result = await self.hybrid_manager.validate_template(
            template_source, template_name, context
        )

        return {
            "is_valid": result.is_valid,
            "errors": [
                {
                    "message": error.message,
                    "line_number": error.line_number,
                    "column_number": error.column_number,
                    "error_type": error.error_type,
                    "severity": error.severity,
                    "context": error.context,
                }
                for error in result.errors
            ],
            "warnings": [
                {
                    "message": warning.message,
                    "line_number": warning.line_number,
                    "severity": warning.severity,
                }
                for warning in result.warnings
            ],
            "suggestions": result.suggestions,
            "used_variables": list(result.used_variables),
            "undefined_variables": list(result.undefined_variables),
            "available_filters": list(result.available_filters),
            "available_functions": list(result.available_functions),
        }

    # Autocomplete API
    async def get_autocomplete_suggestions(
        self, context: str, cursor_position: int = 0, template_name: str = "unknown"
    ) -> list[dict[str, t.Any]]:
        """Get autocomplete suggestions for template editing."""
        if not self.hybrid_manager:
            await self.initialize()
        assert self.hybrid_manager is not None

        suggestions = await self.hybrid_manager.get_autocomplete_suggestions(
            context, cursor_position, template_name
        )

        return [
            {
                "name": item.name,
                "type": item.type,
                "description": item.description,
                "signature": item.signature,
                "adapter_source": item.adapter_source,
                "example": item.example,
            }
            for item in suggestions
        ]

    # Fragment Management API
    async def get_fragments_for_template(
        self, template_name: str
    ) -> list[dict[str, t.Any]]:
        """Get available fragments for a template."""
        if not self.hybrid_manager:
            await self.initialize()
        assert self.hybrid_manager is not None

        fragments = await self.hybrid_manager.get_fragments_for_template(template_name)

        return [
            {
                "name": fragment.name,
                "template_path": fragment.template_path,
                "block_name": fragment.block_name,
                "start_line": fragment.start_line,
                "end_line": fragment.end_line,
                "variables": list(fragment.variables),
                "dependencies": list(fragment.dependencies),
            }
            for fragment in fragments
        ]

    async def render_fragment(
        self,
        fragment_name: str,
        context: dict[str, t.Any] | None = None,
        template_name: str | None = None,
        secure: bool = False,
    ) -> str:
        """Render a template fragment."""
        if not self.hybrid_manager:
            await self.initialize()
        assert self.hybrid_manager is not None

        return await self.hybrid_manager.render_fragment(
            fragment_name, context, template_name, secure
        )

    # Enhanced Rendering API
    async def render_template(
        self,
        request: Request,
        template_name: str,
        context: dict[str, t.Any] | None = None,
        mode: str = "standard",
        fragment_name: str | None = None,
        block_name: str | None = None,
        validate: bool = False,
        secure: bool = False,
        **kwargs: t.Any,
    ) -> Response:
        """Render template with Hybrid features."""
        if not self.async_renderer:
            await self.initialize()
        assert self.async_renderer is not None

        # Map mode string to enum
        mode_mapping = {
            "standard": RenderMode.STANDARD,
            "fragment": RenderMode.FRAGMENT,
            "block": RenderMode.BLOCK,
            "streaming": RenderMode.STREAMING,
            "htmx": RenderMode.HTMX,
        }

        RenderContext(
            template_name=template_name,
            context=context or {},
            request=request,
            mode=mode_mapping.get(mode, RenderMode.STANDARD),
            fragment_name=fragment_name,
            block_name=block_name,
            validate_template=validate,
            secure_render=secure,
            **kwargs,
        )

        return await self.async_renderer.render_response(
            request, template_name, context, **kwargs
        )

    # Block Rendering API
    async def render_block(
        self,
        request: Request,
        block_id: str,
        context: dict[str, t.Any] | None = None,
        update_mode: str = "replace",
        target_selector: str | None = None,
        validate: bool = False,
    ) -> Response:
        """Render a specific template block."""
        if not self.block_renderer:
            await self.initialize()

        # Map update mode string to enum
        update_mode_mapping = {
            "replace": BlockUpdateMode.REPLACE,
            "append": BlockUpdateMode.APPEND,
            "prepend": BlockUpdateMode.PREPEND,
            "inner": BlockUpdateMode.INNER,
            "outer": BlockUpdateMode.OUTER,
            "delete": BlockUpdateMode.DELETE,
        }

        block_request = BlockRenderRequest(
            block_id=block_id,
            context=context or {},
            request=request,
            target_selector=target_selector,
            update_mode=update_mode_mapping.get(update_mode, BlockUpdateMode.REPLACE),
            validate=validate,
        )

        result = await self.block_renderer.render_block(block_request)  # type: ignore[union-attr]

        from starlette.responses import HTMLResponse

        return HTMLResponse(content=result.content, headers=result.htmx_headers)

    async def render_htmx_fragment(
        self,
        request: Request,
        fragment_name: str,
        context: dict[str, t.Any] | None = None,
        template_name: str | None = None,
        **kwargs: t.Any,
    ) -> Response:
        """Render HTMX fragment with appropriate headers."""
        if not self.async_renderer:
            await self.initialize()

        return await self.async_renderer.render_htmx_fragment(  # type: ignore[union-attr]
            request, fragment_name, context, template_name, **kwargs
        )

    # Block Management API
    def register_htmx_block(
        self,
        name: str,
        template_name: str,
        block_name: str | None = None,
        htmx_endpoint: str | None = None,
        update_mode: str = "replace",
        trigger: str = "manual",
        auto_refresh: int | None = None,
        **kwargs: t.Any,
    ) -> dict[str, t.Any]:
        """Register a block optimized for HTMX interactions."""
        if not self.block_renderer:
            raise RuntimeError("Block renderer not initialized")

        from ._block_renderer import BlockTrigger, BlockUpdateMode

        # Map string values to enums
        update_mode_mapping = {
            "replace": BlockUpdateMode.REPLACE,
            "append": BlockUpdateMode.APPEND,
            "prepend": BlockUpdateMode.PREPEND,
            "inner": BlockUpdateMode.INNER,
            "outer": BlockUpdateMode.OUTER,
            "delete": BlockUpdateMode.DELETE,
        }

        trigger_mapping = {
            "manual": BlockTrigger.MANUAL,
            "auto": BlockTrigger.AUTO,
            "lazy": BlockTrigger.LAZY,
            "polling": BlockTrigger.POLLING,
            "websocket": BlockTrigger.WEBSOCKET,
        }

        block_def = self.block_renderer.register_htmx_block(
            name=name,
            template_name=template_name,
            block_name=block_name,
            htmx_endpoint=htmx_endpoint,
            update_mode=update_mode_mapping.get(update_mode, BlockUpdateMode.REPLACE),
            trigger=trigger_mapping.get(trigger, BlockTrigger.MANUAL),
            auto_refresh=auto_refresh,
            **kwargs,
        )

        return {
            "name": block_def.name,
            "template_name": block_def.template_name,
            "block_name": block_def.block_name,
            "css_selector": block_def.css_selector,
            "htmx_attrs": block_def.htmx_attrs,
            "update_mode": block_def.update_mode.value,
            "trigger": block_def.trigger.value,
        }

    async def get_block_info(self, block_id: str) -> dict[str, t.Any]:
        """Get information about a registered block."""
        if not self.block_renderer:
            await self.initialize()

        return await self.block_renderer.get_block_info(block_id)  # type: ignore[union-attr]

    def get_htmx_attributes_for_block(self, block_id: str) -> str:
        """Get HTMX attributes string for a block."""
        if not self.block_renderer:
            return ""

        return self.block_renderer.get_htmx_attributes_for_block(block_id)

    # Performance and Monitoring API
    async def get_performance_metrics(
        self, template_name: str | None = None
    ) -> dict[str, t.Any]:
        """Get template rendering performance metrics."""
        if not self.async_renderer:
            await self.initialize()

        return await self.async_renderer.get_performance_metrics(template_name)  # type: ignore[union-attr]

    def clear_caches(self) -> None:
        """Clear all template caches."""
        if self.hybrid_manager:
            self.hybrid_manager.clear_caches()

        if self.async_renderer:
            self.async_renderer.clear_cache()

    # Utility API
    async def precompile_templates(self) -> dict[str, t.Any]:
        """Precompile templates for performance optimization."""
        if not self.hybrid_manager:
            await self.initialize()

        compiled = await self.hybrid_manager.precompile_templates()  # type: ignore[union-attr]
        return {name: True for name in compiled.keys()}

    async def get_template_dependencies(self, template_name: str) -> list[str]:
        """Get dependencies for a template."""
        if not self.hybrid_manager:
            await self.initialize()

        deps = await self.hybrid_manager.get_template_dependencies(template_name)  # type: ignore[union-attr]
        return list(deps)


# Global integration instance
_integration_instance: HybridTemplates | None = None


async def get_hybrid_templates() -> HybridTemplates:
    """Get or create the global Hybrid templates integration instance."""
    global _integration_instance

    if _integration_instance is None:
        _integration_instance = HybridTemplates()
        await _integration_instance.initialize()

    return _integration_instance


# Convenience functions for common operations
async def validate_template_source(
    template_source: str,
    template_name: str = "unknown",
    context: dict[str, t.Any] | None = None,
) -> dict[str, t.Any]:
    """Validate template source code."""
    integration = await get_hybrid_templates()
    return await integration.validate_template(template_source, template_name, context)


async def get_template_autocomplete(
    context: str, cursor_position: int = 0, template_name: str = "unknown"
) -> list[dict[str, t.Any]]:
    """Get autocomplete suggestions for template editing."""
    integration = await get_hybrid_templates()
    return await integration.get_autocomplete_suggestions(
        context, cursor_position, template_name
    )


async def render_htmx_block(
    request: Request,
    block_id: str,
    context: dict[str, t.Any] | None = None,
    update_mode: str = "replace",
) -> Response:
    """Render HTMX block with appropriate headers."""
    integration = await get_hybrid_templates()
    return await integration.render_block(request, block_id, context, update_mode)


async def render_template_fragment(
    request: Request,
    fragment_name: str,
    context: dict[str, t.Any] | None = None,
    template_name: str | None = None,
) -> Response:
    """Render template fragment for HTMX."""
    integration = await get_hybrid_templates()
    return await integration.render_htmx_fragment(
        request, fragment_name, context, template_name
    )


MODULE_ID = UUID("01937d8b-1234-7890-abcd-1234567890ab")
MODULE_STATUS = AdapterStatus.STABLE

# Register the integration
with suppress(Exception):
    depends.set(Templates, get_hybrid_templates)
