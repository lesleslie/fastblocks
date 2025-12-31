"""Performance benchmarks for FastBlocks template rendering."""

import asyncio
from unittest.mock import AsyncMock

import pytest
from fastblocks.adapters.templates._async_renderer import (
    AsyncTemplateRenderer,
    CacheStrategy,
    RenderContext,
    RenderMode,
)
from fastblocks.adapters.templates.jinja2 import Templates


class TestTemplateRenderingPerformance:
    """Benchmark template rendering performance."""

    @pytest.fixture
    async def templates(self):
        """Create mock templates adapter with proper structure."""
        from unittest.mock import MagicMock

        # Create mock template with async render method
        async def mock_render_async(context):
            return "<html>Test</html>"

        mock_template = MagicMock()
        mock_template.render_async = mock_render_async

        # Create mock Jinja2 environment
        mock_env = MagicMock()
        mock_env.get_template = MagicMock(return_value=mock_template)

        # Create mock AsyncJinja2Templates
        mock_app = MagicMock()
        mock_app.env = mock_env

        # Create mock Templates adapter
        templates = AsyncMock()
        templates.app = mock_app
        templates.render_template = AsyncMock(return_value="<html>Test</html>")
        templates.render_fragment = AsyncMock(return_value="<div>Fragment</div>")

        return templates

    @pytest.fixture
    async def renderer(self, templates):
        """Create async renderer with memory caching."""
        return AsyncTemplateRenderer(
            base_templates=templates, cache_strategy=CacheStrategy.MEMORY
        )

    @pytest.mark.benchmark(group="template-rendering")
    async def test_basic_template_rendering_performance(self, benchmark, renderer):
        """Benchmark basic template rendering."""
        context = RenderContext(
            template_name="test.html",
            context={"title": "Test Page", "content": "Hello World"},
        )

        result = await benchmark.pedantic(
            renderer.render, args=(context,), iterations=10, rounds=5
        )

        assert result is not None

    @pytest.mark.benchmark(group="template-rendering")
    async def test_cached_template_rendering_performance(self, benchmark, renderer):
        """Benchmark cached template rendering performance."""
        context = RenderContext(
            template_name="test.html",
            context={"title": "Test Page", "content": "Hello World"},
            cache_key="test_cache_key",
            cache_ttl=300,
        )

        # Prime the cache
        await renderer.render(context)

        # Benchmark cached rendering
        result = await benchmark.pedantic(
            renderer.render, args=(context,), iterations=10, rounds=5
        )

        assert result.cache_hit is True

    @pytest.mark.benchmark(group="template-rendering")
    async def test_fragment_rendering_performance(self, benchmark, renderer):
        """Benchmark HTMX fragment rendering performance."""
        from starlette.requests import Request

        # Create a mock request
        scope = {
            "type": "http",
            "method": "GET",
            "headers": [],
            "query_string": b"",
            "path": "/test",
        }
        request = Request(scope)

        async def render_fragment():
            return await renderer.render_htmx_fragment(
                request=request,
                fragment_name="item_list",
                context={"items": [f"item_{i}" for i in range(100)]},
                template_name="test.html",
            )

        result = await benchmark.pedantic(render_fragment, iterations=10, rounds=5)

        assert result.media_type == "text/html"

    @pytest.mark.benchmark(group="template-rendering")
    async def test_streaming_rendering_performance(self, benchmark, renderer):
        """Benchmark streaming template rendering."""
        context = RenderContext(
            template_name="large_page.html",
            context={"data": list(range(1000))},
        )

        async def render_normal():
            result = await renderer.render(context)
            return result.content

        content = await benchmark.pedantic(render_normal, iterations=5, rounds=3)

        assert len(content) > 0

    @pytest.mark.benchmark(group="template-rendering")
    async def test_concurrent_rendering_performance(self, benchmark, renderer):
        """Benchmark concurrent template rendering."""
        contexts = [
            RenderContext(
                template_name=f"template_{i}.html",
                context={"id": i, "data": f"content_{i}"},
                cache_key=f"cache_key_{i}",
            )
            for i in range(20)
        ]

        async def render_concurrent():
            tasks = [renderer.render(context) for context in contexts]
            return await asyncio.gather(*tasks)

        results = await benchmark.pedantic(render_concurrent, iterations=3, rounds=2)

        assert len(results) == 20
        assert all(result.status_code == 200 for result in results)


class TestCachingPerformance:
    """Benchmark caching performance."""

    @pytest.mark.benchmark(group="caching")
    async def test_memory_cache_performance(self, benchmark):
        """Benchmark memory cache operations."""
        from fastblocks.caching import get_cache

        cache = get_cache()
        if not cache:
            pytest.skip("Cache not available")

        test_data = {"key": "value", "data": list(range(100))}

        async def cache_operations():
            await cache.set("test_key", test_data, ttl=300)
            result = await cache.get("test_key")
            await cache.delete("test_key")
            return result

        result = await benchmark.pedantic(cache_operations, iterations=100, rounds=10)

        assert result == test_data

    @pytest.mark.benchmark(group="caching")
    async def test_cache_miss_performance(self, benchmark):
        """Benchmark cache miss handling."""
        from fastblocks.caching import get_cache

        cache = get_cache()
        if not cache:
            pytest.skip("Cache not available")

        async def cache_miss_operation():
            return await cache.get("non_existent_key")

        result = await benchmark.pedantic(cache_miss_operation, iterations=100, rounds=10)

        assert result is None
