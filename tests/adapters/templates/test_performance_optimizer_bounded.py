"""Regression tests for PerformanceOptimizer bounded-LRU storage.

Phase 4.D remediation: ``template_stats`` must be bounded by both:
  * ``MAX_SAMPLES_PER_TEMPLATE`` (1024 samples per template)
  * ``MAX_TRACKED_TEMPLATES`` (512 distinct templates, LRU evicted)

and must expose an ``evictions_total`` metric counter.
"""

from __future__ import annotations

from fastblocks.adapters.templates._performance_optimizer import (
    PerformanceMetrics,
    PerformanceOptimizer,
)


def _metrics(render_time: float = 0.01) -> PerformanceMetrics:
    """Build a minimal PerformanceMetrics instance for tests."""
    return PerformanceMetrics(
        render_time=render_time,
        cache_hit=False,
        template_size=1024,
        context_size=64,
    )


class TestTemplateStatsBounding:
    """Verify ``template_stats`` is LRU-bounded on both axes."""

    def test_per_template_samples_capped_at_maxlen(self) -> None:
        """A single template keeps at most ``MAX_SAMPLES_PER_TEMPLATE`` samples."""
        optimizer = PerformanceOptimizer()
        metrics = _metrics()
        for _ in range(optimizer.MAX_SAMPLES_PER_TEMPLATE + 500):
            optimizer.record_render("hot.html", metrics)

        samples = optimizer.template_stats["hot.html"]
        assert len(samples) == optimizer.MAX_SAMPLES_PER_TEMPLATE

    def test_global_template_cap_with_lru_eviction(self) -> None:
        """Pushing more than the cap evicts oldest templates (LRU)."""
        optimizer = PerformanceOptimizer()
        metrics = _metrics()
        total = optimizer.MAX_TRACKED_TEMPLATES + 100
        for i in range(total):
            optimizer.record_render(f"tpl_{i:05d}.html", metrics)

        assert len(optimizer.template_stats) == optimizer.MAX_TRACKED_TEMPLATES

        # The oldest templates should have been evicted; the most recent must remain.
        assert f"tpl_{total - 1:05d}.html" in optimizer.template_stats
        assert "tpl_00000.html" not in optimizer.template_stats

    def test_evictions_total_increments_on_lru_eviction(self) -> None:
        """The ``evictions_total`` counter advances on template eviction."""
        optimizer = PerformanceOptimizer()
        metrics = _metrics()
        assert optimizer.evictions_total == 0

        over = optimizer.MAX_TRACKED_TEMPLATES + 50
        for i in range(over):
            optimizer.record_render(f"tpl_{i:05d}.html", metrics)

        assert optimizer.evictions_total == 50

    def test_touching_existing_template_does_not_evict(self) -> None:
        """Re-recording a known template refreshes LRU order without eviction."""
        optimizer = PerformanceOptimizer()
        metrics = _metrics()
        for i in range(optimizer.MAX_TRACKED_TEMPLATES):
            optimizer.record_render(f"tpl_{i:05d}.html", metrics)

        assert optimizer.evictions_total == 0

        # Touch the oldest template repeatedly; later inserts must not evict it.
        for _ in range(10):
            optimizer.record_render("tpl_00000.html", metrics)
        for i in range(
            optimizer.MAX_TRACKED_TEMPLATES,
            optimizer.MAX_TRACKED_TEMPLATES + 50,
        ):
            optimizer.record_render(f"tpl_{i:05d}.html", metrics)

        assert "tpl_00000.html" in optimizer.template_stats
        assert optimizer.evictions_total == 50
