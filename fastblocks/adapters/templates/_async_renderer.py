"""Enhanced Async Template Renderer for FastBlocks.

This module provides advanced async template rendering with:
- Enhanced error handling with detailed context
- Performance optimization with caching layers
- HTMX-aware fragment rendering
- Streaming template rendering for large responses
- Template dependency tracking and hot reloading

Requirements:
- jinja2>=3.1.6
- jinja2-async-environment>=0.14.3
- starlette-async-jinja>=1.12.4

Author: lesleslie <les@wedgwoodwebworks.com>
Created: 2025-01-12
"""

import time
import typing as t
from collections.abc import AsyncIterator
from contextlib import suppress
from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID

from acb.adapters import AdapterStatus
from acb.depends import depends
from anyio import Path as AsyncPath
from starlette.requests import Request
from starlette.responses import HTMLResponse, Response, StreamingResponse

from ._advanced_manager import HybridTemplatesManager, TemplateValidationResult
from ._performance_optimizer import (
    PerformanceMetrics,
    PerformanceOptimizer,
    get_performance_optimizer,
)
from .jinja2 import Templates


class RenderMode(Enum):
    """Template rendering modes."""

    STANDARD = "standard"
    FRAGMENT = "fragment"
    BLOCK = "block"
    STREAMING = "streaming"
    HTMX = "htmx"


class CacheStrategy(Enum):
    """Template caching strategies."""

    NONE = "none"
    MEMORY = "memory"
    REDIS = "redis"
    HYBRID = "hybrid"


@dataclass
class RenderContext:
    """Template rendering context with metadata."""

    template_name: str
    context: dict[str, t.Any]
    request: Request | None = None
    mode: RenderMode = RenderMode.STANDARD
    fragment_name: str | None = None
    block_name: str | None = None
    cache_key: str | None = None
    cache_ttl: int = 300
    enable_streaming: bool = False
    chunk_size: int = 8192
    validate_template: bool = False
    secure_render: bool = False


@dataclass
class RenderResult:
    """Result of template rendering operation."""

    content: str | AsyncIterator[str]
    content_type: str = "text/html"
    status_code: int = 200
    headers: dict[str, str] = field(default_factory=dict)
    render_time: float = 0.0
    cache_hit: bool = False
    validation_result: TemplateValidationResult | None = None
    template_path: str | None = None
    fragment_info: dict[str, t.Any] = field(default_factory=dict)


class AsyncTemplateRenderer:
    """Enhanced async template renderer with advanced features."""

    def __init__(
        self,
        base_templates: Templates | None = None,
        hybrid_manager: HybridTemplatesManager | None = None,
        cache_strategy: CacheStrategy = CacheStrategy.MEMORY,
        performance_optimizer: PerformanceOptimizer | None = None,
    ) -> None:
        self.base_templates = base_templates
        self.hybrid_manager = hybrid_manager
        self.cache_strategy = cache_strategy
        self.performance_optimizer = (
            performance_optimizer or get_performance_optimizer()
        )
        self._render_cache: dict[str, tuple[str, float]] = {}
        self._template_watchers: dict[str, float] = {}
        self._performance_metrics: dict[str, list[float]] = {}

    async def initialize(self) -> None:
        """Initialize the async renderer."""
        if not self.base_templates:
            try:
                self.base_templates = await depends.get("templates")
            except Exception:
                self.base_templates = Templates()
                await self.base_templates.init()

        if not self.hybrid_manager:
            try:
                self.hybrid_manager = await depends.get("hybrid_template_manager")
            except Exception:
                self.hybrid_manager = HybridTemplatesManager()
                await self.hybrid_manager.initialize()

    async def render(self, render_context: RenderContext) -> RenderResult:
        """Render template with enhanced error handling and optimization."""
        start_time = time.time()

        try:
            await self._optimize_render_context(render_context)
            context_size = len(str(render_context.context))

            validation_result = await self._validate_if_requested(
                render_context, start_time
            )
            if validation_result and not validation_result.is_valid:
                return self._create_error_result(
                    "Template validation failed",
                    validation_result=validation_result,
                    render_time=time.time() - start_time,
                )

            cached_result = await self._try_get_cached(render_context, start_time)
            if cached_result:
                return cached_result

            content = await self._execute_render_strategy(render_context)
            result = await self._finalize_render_result(
                render_context, content, validation_result, context_size, start_time
            )

            return result

        except Exception as e:
            return self._create_error_result(
                str(e), render_time=time.time() - start_time, status_code=500
            )

    async def _optimize_render_context(self, render_context: RenderContext) -> None:
        """Apply performance optimizations to render context."""
        optimized_context = await self.performance_optimizer.optimize_render_context(
            render_context.template_name, render_context.context
        )
        render_context.context = optimized_context

        context_size = len(str(render_context.context))

        if not render_context.enable_streaming:
            render_context.enable_streaming = (
                self.performance_optimizer.should_enable_streaming(
                    render_context.template_name, context_size
                )
            )
            if render_context.enable_streaming:
                render_context.mode = RenderMode.STREAMING

        if render_context.cache_key and render_context.cache_ttl == 300:
            render_context.cache_ttl = self.performance_optimizer.get_optimal_cache_ttl(
                render_context.template_name
            )

    async def _validate_if_requested(
        self, render_context: RenderContext, start_time: float
    ) -> TemplateValidationResult | None:
        """Validate template if validation is requested."""
        if render_context.validate_template:
            return await self._validate_before_render(render_context)
        return None

    async def _try_get_cached(
        self, render_context: RenderContext, start_time: float
    ) -> RenderResult | None:
        """Try to get cached result if caching is enabled."""
        if render_context.cache_key:
            cached_result = await self._check_cache(render_context)
            if cached_result:
                cached_result.render_time = time.time() - start_time
                cached_result.cache_hit = True
                return cached_result
        return None

    async def _execute_render_strategy(
        self, render_context: RenderContext
    ) -> str | AsyncIterator[str]:
        """Execute the appropriate rendering strategy based on mode."""
        if render_context.mode == RenderMode.STREAMING:
            # _render_streaming returns an AsyncIterator, not awaitable
            result: str | AsyncIterator[str] = self._render_streaming(render_context)
            return result
        elif render_context.mode == RenderMode.FRAGMENT:
            return await self._render_fragment(render_context)
        elif render_context.mode == RenderMode.BLOCK:
            return await self._render_block(render_context)
        elif render_context.mode == RenderMode.HTMX:
            return await self._render_htmx(render_context)

        return await self._render_standard(render_context)

    async def _finalize_render_result(
        self,
        render_context: RenderContext,
        content: str | AsyncIterator[str],
        validation_result: TemplateValidationResult | None,
        context_size: int,
        start_time: float,
    ) -> RenderResult:
        """Finalize render result with caching and metrics."""
        result = RenderResult(
            content=content,
            render_time=time.time() - start_time,
            validation_result=validation_result,
            template_path=render_context.template_name,
        )

        if render_context.cache_key and isinstance(content, str):
            await self._cache_result(render_context, result)

        self._track_performance(render_context.template_name, result.render_time)

        performance_metrics = PerformanceMetrics(
            render_time=result.render_time,
            cache_hit=result.cache_hit,
            template_size=len(render_context.template_name),
            context_size=context_size,
            fragment_count=1 if render_context.fragment_name else 0,
            memory_usage=0,
            concurrent_renders=1,
        )

        self.performance_optimizer.record_render(
            render_context.template_name, performance_metrics
        )

        return result

    async def _validate_before_render(
        self, render_context: RenderContext
    ) -> TemplateValidationResult:
        """Validate template before rendering."""
        if not self.hybrid_manager:
            return TemplateValidationResult(is_valid=True)

        try:
            # Get template source
            env = self.base_templates.app.env  # type: ignore[union-attr]
            source, _ = env.loader.get_source(env, render_context.template_name)

            return await self.hybrid_manager.validate_template(
                source, render_context.template_name, render_context.context
            )
        except Exception:
            return TemplateValidationResult(is_valid=False, errors=[], warnings=[])

    async def _check_cache(self, render_context: RenderContext) -> RenderResult | None:
        """Check if rendered result is cached."""
        if self.cache_strategy == CacheStrategy.NONE or not render_context.cache_key:
            return None

        if self.cache_strategy == CacheStrategy.MEMORY:
            return self._check_memory_cache(render_context)

        elif self.cache_strategy == CacheStrategy.REDIS:
            return await self._check_redis_cache(render_context)

        elif self.cache_strategy == CacheStrategy.HYBRID:
            # Try memory first, then Redis
            result = self._check_memory_cache(render_context)
            if result:
                return result
            return await self._check_redis_cache(render_context)

        return None

    def _check_memory_cache(self, render_context: RenderContext) -> RenderResult | None:
        """Check memory cache for cached result."""
        cache_key = render_context.cache_key
        if cache_key in self._render_cache:
            content, timestamp = self._render_cache[cache_key]
            if time.time() - timestamp < render_context.cache_ttl:
                return RenderResult(content=content, cache_hit=True)
            else:
                del self._render_cache[cache_key]

        return None

    async def _check_redis_cache(
        self, render_context: RenderContext
    ) -> RenderResult | None:
        """Check Redis cache for cached result."""
        with suppress(Exception):
            cache = await depends.get("cache")
            if cache:
                cached_content = await cache.get(render_context.cache_key)
                if cached_content:
                    return RenderResult(content=cached_content, cache_hit=True)

        return None

    async def _render_standard(self, render_context: RenderContext) -> str:
        """Render template using standard mode."""
        if not self.base_templates or not self.base_templates.app:
            raise RuntimeError("Templates not initialized")

        template = self.base_templates.app.env.get_template(
            render_context.template_name
        )

        # Use secure environment if requested
        if render_context.secure_render and self.hybrid_manager:
            env = self.hybrid_manager._get_template_environment(secure=True)
            template = env.get_template(render_context.template_name)

        rendered = await template.render_async(render_context.context)
        return t.cast(str, rendered)

    async def _render_fragment(self, render_context: RenderContext) -> str:
        """Render template fragment for HTMX."""
        if not self.hybrid_manager:
            raise RuntimeError("Advanced manager required for fragment rendering")

        if not render_context.fragment_name:
            raise ValueError("Fragment name required for fragment rendering")

        return await self.hybrid_manager.render_fragment(
            render_context.fragment_name,
            render_context.context,
            render_context.template_name,
            render_context.secure_render,
        )

    async def _render_block(self, render_context: RenderContext) -> str:
        """Render specific template block."""
        if not self.base_templates or not self.base_templates.app:
            raise RuntimeError("Templates not initialized")

        if not render_context.block_name:
            raise ValueError("Block name required for block rendering")

        template = self.base_templates.app.env.get_template(
            render_context.template_name
        )
        # render_block exists in Jinja2 runtime but not in type stubs
        rendered = template.render_block(  # type: ignore[attr-defined]
            render_context.block_name, render_context.context
        )
        return t.cast(str, rendered)

    async def _render_htmx(self, render_context: RenderContext) -> str:
        """Render template optimized for HTMX responses."""
        # Add HTMX-specific context
        htmx_context = render_context.context | {
            "is_htmx": True,
            "htmx_request": getattr(render_context.request, "htmx", None)
            if render_context.request
            else None,
        }

        # Update context and render
        render_context.context = htmx_context

        if render_context.fragment_name:
            return await self._render_fragment(render_context)
        elif render_context.block_name:
            return await self._render_block(render_context)

        return await self._render_standard(render_context)

    def _render_streaming(self, render_context: RenderContext) -> AsyncIterator[str]:
        """Render template with streaming for large responses."""
        if not self.base_templates or not self.base_templates.app:
            raise RuntimeError("Templates not initialized")

        template = self.base_templates.app.env.get_template(
            render_context.template_name
        )

        # Return async generator directly
        return self._stream_template_chunks(template, render_context)

    async def _stream_template_chunks(
        self, template: t.Any, render_context: RenderContext
    ) -> AsyncIterator[str]:
        """Internal async generator for streaming template chunks."""
        # Generate template content in chunks
        async for chunk in template.generate_async(render_context.context):
            # Yield chunks of specified size
            if len(chunk) > render_context.chunk_size:
                for i in range(0, len(chunk), render_context.chunk_size):
                    yield chunk[i : i + render_context.chunk_size]
            else:
                yield chunk

    async def _cache_result(
        self, render_context: RenderContext, result: RenderResult
    ) -> None:
        """Cache the rendered result."""
        if not render_context.cache_key or not isinstance(result.content, str):
            return

        if self.cache_strategy in (CacheStrategy.MEMORY, CacheStrategy.HYBRID):
            self._render_cache[render_context.cache_key] = (result.content, time.time())

        if self.cache_strategy in (CacheStrategy.REDIS, CacheStrategy.HYBRID):
            with suppress(Exception):
                cache = await depends.get("cache")
                if cache:
                    await cache.set(
                        render_context.cache_key,
                        result.content,
                        ttl=render_context.cache_ttl,
                    )

    def _track_performance(self, template_name: str, render_time: float) -> None:
        """Track rendering performance metrics."""
        if template_name not in self._performance_metrics:
            self._performance_metrics[template_name] = []

        metrics = self._performance_metrics[template_name]
        metrics.append(render_time)

        # Keep only last 100 measurements
        if len(metrics) > 100:
            metrics.pop(0)

    def _create_error_result(
        self,
        error_message: str,
        status_code: int = 500,
        render_time: float = 0.0,
        validation_result: TemplateValidationResult | None = None,
    ) -> RenderResult:
        """Create error result with helpful debugging information."""
        error_html = self._generate_error_html(error_message, validation_result)

        return RenderResult(
            content=error_html,
            status_code=status_code,
            render_time=render_time,
            validation_result=validation_result,
        )

    def _generate_error_html(
        self,
        error_message: str,
        validation_result: TemplateValidationResult | None = None,
    ) -> str:
        """Generate helpful error HTML for template issues."""
        error_html = [
            '<div style="background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 4px; padding: 20px; margin: 20px; font-family: monospace;">',
            '<h3 style="color: #dc3545; margin-top: 0;">Template Error</h3>',
            f"<p><strong>Error:</strong> {error_message}</p>",
        ]

        if validation_result and validation_result.errors:
            error_html.extend(
                ('<h4 style="color: #dc3545;">Validation Errors:</h4>', "<ul>")
            )
            for error in validation_result.errors:
                line_info = f" (line {error.line_number})" if error.line_number else ""
                error_html.append(f"<li>{error.message}{line_info}</li>")
                if error.context:
                    error_html.extend(
                        (
                            f'<pre style="background: #f1f3f4; padding: 10px; margin: 5px 0;">{error.context}</pre>',
                            "</ul>",
                        )
                    )

        if validation_result and validation_result.suggestions:
            error_html.extend(('<h4 style="color: #007bff;">Suggestions:</h4>', "<ul>"))
            for suggestion in validation_result.suggestions:
                error_html.extend((f"<li>{suggestion}</li>", "</ul>"))

        error_html.append("</div>")
        return "".join(error_html)

    async def render_response(
        self,
        request: Request,
        template_name: str,
        context: dict[str, t.Any] | None = None,
        **kwargs: t.Any,
    ) -> Response:
        """Render template and return appropriate Response object."""
        render_context = RenderContext(
            template_name=template_name,
            context=context or {},
            request=request,
            **kwargs,
        )

        result = await self.render(render_context)

        # Handle streaming responses
        if isinstance(result.content, AsyncIterator):
            return StreamingResponse(
                result.content,
                status_code=result.status_code,
                headers=result.headers,
                media_type=result.content_type,
            )

        # Standard HTML response
        return HTMLResponse(
            content=result.content,
            status_code=result.status_code,
            headers=result.headers,
        )

    async def render_htmx_fragment(
        self,
        request: Request,
        fragment_name: str,
        context: dict[str, t.Any] | None = None,
        template_name: str | None = None,
        **kwargs: t.Any,
    ) -> Response:
        """Render HTMX fragment with appropriate headers."""
        render_context = RenderContext(
            template_name=template_name or f"_{fragment_name}.html",
            context=context or {},
            request=request,
            mode=RenderMode.HTMX,
            fragment_name=fragment_name,
            **kwargs,
        )

        result = await self.render(render_context)

        # Add HTMX-specific headers
        headers = {"HX-Content-Type": "text/html"} | result.headers

        return HTMLResponse(
            content=result.content, status_code=result.status_code, headers=headers
        )

    async def get_performance_metrics(
        self, template_name: str | None = None
    ) -> dict[str, t.Any]:
        """Get performance metrics for templates."""
        if template_name and template_name in self._performance_metrics:
            metrics = self._performance_metrics[template_name]
            return {
                "template": template_name,
                "avg_render_time": sum(metrics) / len(metrics),
                "min_render_time": min(metrics),
                "max_render_time": max(metrics),
                "render_count": len(metrics),
                "recent_times": metrics[-10:],  # Last 10 renders
            }

        # Return aggregate metrics
        all_metrics = {}
        for tmpl_name, times in self._performance_metrics.items():
            all_metrics[tmpl_name] = {
                "avg_render_time": sum(times) / len(times),
                "min_render_time": min(times),
                "max_render_time": max(times),
                "render_count": len(times),
            }

        return all_metrics

    async def get_performance_stats(self) -> dict[str, t.Any]:
        """Get comprehensive performance statistics from the optimizer."""
        stats = self.performance_optimizer.get_performance_stats()
        return {
            "total_renders": stats.total_renders,
            "avg_render_time": stats.avg_render_time,
            "cache_hit_ratio": stats.cache_hit_ratio,
            "slowest_templates": stats.slowest_templates,
            "fastest_templates": stats.fastest_templates,
            "memory_peak": stats.memory_peak,
            "concurrent_peak": stats.concurrent_peak,
        }

    async def get_optimization_recommendations(self) -> list[str]:
        """Get performance optimization recommendations."""
        return self.performance_optimizer.get_optimization_recommendations()

    async def export_performance_metrics(self) -> dict[str, t.Any]:
        """Export comprehensive performance metrics for monitoring."""
        return self.performance_optimizer.export_metrics()

    def clear_cache(self, template_pattern: str | None = None) -> None:
        """Clear render cache, optionally for specific template pattern."""
        if template_pattern:
            keys_to_remove = [
                key for key in self._render_cache.keys() if template_pattern in key
            ]
            for key in keys_to_remove:
                del self._render_cache[key]
        else:
            self._render_cache.clear()

    async def watch_template_changes(self, template_name: str) -> bool:
        """Check if template has changed since last render."""
        with suppress(Exception):
            env = self.base_templates.app.env  # type: ignore[union-attr]
            _, filename = env.loader.get_source(env, template_name)

            if filename:
                # Check file modification time
                path = AsyncPath(filename)
                if await path.exists():
                    stat = await path.stat()
                    current_mtime = stat.st_mtime

                    if template_name in self._template_watchers:
                        last_mtime = self._template_watchers[template_name]
                        if current_mtime > last_mtime:
                            self._template_watchers[template_name] = current_mtime
                            return True
                    else:
                        self._template_watchers[template_name] = current_mtime

        return False


MODULE_ID = UUID("01937d88-1234-7890-abcd-1234567890ab")
MODULE_STATUS = AdapterStatus.STABLE

# Register the async renderer
with suppress(Exception):
    depends.set("async_template_renderer", AsyncTemplateRenderer)
