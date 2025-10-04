"""Performance optimizer for FastBlocks template rendering."""

import operator
import time
from collections import defaultdict, deque
from contextlib import suppress
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from acb.depends import depends


@dataclass
class PerformanceMetrics:
    """Performance metrics for template rendering."""

    render_time: float
    cache_hit: bool
    template_size: int
    context_size: int
    fragment_count: int = 0
    memory_usage: int = 0
    concurrent_renders: int = 1


@dataclass
class PerformanceStats:
    """Aggregated performance statistics."""

    total_renders: int = 0
    avg_render_time: float = 0.0
    cache_hit_ratio: float = 0.0
    slowest_templates: dict[str, float] = field(default_factory=dict)
    fastest_templates: dict[str, float] = field(default_factory=dict)
    memory_peak: int = 0
    concurrent_peak: int = 0


class PerformanceOptimizer:
    """Template rendering performance optimizer."""

    # Required ACB 0.19.0+ metadata
    MODULE_ID: UUID = UUID("01937d87-b123-4567-89ab-123456789def")
    MODULE_STATUS: str = "stable"

    def __init__(self) -> None:
        """Initialize performance optimizer."""
        self.metrics_history: deque[dict[str, Any]] = deque(maxlen=1000)
        self.template_stats: dict[str, list[float]] = defaultdict(list)
        self.cache_stats: dict[str, int] = defaultdict(int)
        self.concurrent_renders: int = 0
        self.optimization_enabled: bool = True

        # Register with ACB
        with suppress(Exception):
            depends.set(self)

    def record_render(self, template_name: str, metrics: PerformanceMetrics) -> None:
        """Record template rendering metrics."""
        if not self.optimization_enabled:
            return

        # Store metrics
        self.metrics_history.append(
            {"template": template_name, "timestamp": time.time(), "metrics": metrics}
        )

        # Update template-specific stats
        self.template_stats[template_name].append(metrics.render_time)

        # Update cache stats
        cache_key = f"{template_name}_cache"
        if metrics.cache_hit:
            self.cache_stats[f"{cache_key}_hits"] += 1
        else:
            self.cache_stats[f"{cache_key}_misses"] += 1

        # Track concurrent renders
        self.concurrent_renders = max(
            self.concurrent_renders, metrics.concurrent_renders
        )

    def get_performance_stats(self) -> PerformanceStats:
        """Get aggregated performance statistics."""
        if not self.metrics_history:
            return PerformanceStats()

        total_renders = len(self.metrics_history)
        total_render_time = sum(
            entry["metrics"].render_time for entry in self.metrics_history
        )
        avg_render_time = total_render_time / total_renders

        # Cache hit ratio
        total_hits = sum(
            count for key, count in self.cache_stats.items() if key.endswith("_hits")
        )
        total_requests = sum(self.cache_stats.values())
        cache_hit_ratio = total_hits / total_requests if total_requests > 0 else 0.0

        # Template performance analysis
        slowest_templates: dict[str, Any] = {}
        fastest_templates: dict[str, Any] = {}

        for template, times in self.template_stats.items():
            if times:
                avg_time = sum(times) / len(times)
                if len(slowest_templates) < 5:
                    slowest_templates[template] = avg_time
                elif avg_time > min(slowest_templates.values()):
                    # Replace slowest if this is slower
                    min_key = min(
                        slowest_templates.items(), key=operator.itemgetter(1)
                    )[0]
                    del slowest_templates[min_key]
                    slowest_templates[template] = avg_time

                if len(fastest_templates) < 5:
                    fastest_templates[template] = avg_time
                elif avg_time < max(fastest_templates.values()):
                    # Replace fastest if this is faster
                    max_key = max(
                        fastest_templates.items(), key=operator.itemgetter(1)
                    )[0]
                    del fastest_templates[max_key]
                    fastest_templates[template] = avg_time

        return PerformanceStats(
            total_renders=total_renders,
            avg_render_time=avg_render_time,
            cache_hit_ratio=cache_hit_ratio,
            slowest_templates=slowest_templates,
            fastest_templates=fastest_templates,
            concurrent_peak=self.concurrent_renders,
        )

    def get_optimization_recommendations(self) -> list[str]:
        """Get performance optimization recommendations."""
        recommendations = []
        stats = self.get_performance_stats()

        # Cache optimization
        if stats.cache_hit_ratio < 0.7:
            recommendations.append(
                f"Cache hit ratio is {stats.cache_hit_ratio:.1%}. "
                "Consider increasing cache TTL or improving cache keys."
            )

        # Slow template analysis
        if stats.avg_render_time > 0.1:  # 100ms
            recommendations.append(
                f"Average render time is {stats.avg_render_time:.3f}s. "
                "Consider template optimization or caching strategies."
            )

        # Identify problematic templates
        for template, avg_time in stats.slowest_templates.items():
            if avg_time > 0.2:  # 200ms
                recommendations.append(
                    f"Template '{template}' averages {avg_time:.3f}s. "
                    "Consider breaking into fragments or optimizing logic."
                )

        # Concurrent rendering
        if stats.concurrent_peak > 50:
            recommendations.append(
                f"Peak concurrent renders: {stats.concurrent_peak}. "
                "Consider implementing render queuing or rate limiting."
            )

        return recommendations

    async def optimize_render_context(
        self, template_name: str, context: dict[str, Any]
    ) -> dict[str, Any]:
        """Optimize render context for better performance."""
        if not self.optimization_enabled:
            return context

        optimized_context = context.copy()

        # Historical performance analysis
        if template_name in self.template_stats:
            avg_time = sum(self.template_stats[template_name]) / len(
                self.template_stats[template_name]
            )

            # For slow templates, optimize context
            if avg_time > 0.1:
                # Limit large collections (iterate over copy to avoid RuntimeError)
                items_to_process = list(optimized_context.items())
                for key, value in items_to_process:
                    if isinstance(value, list | tuple) and len(value) > 100:
                        optimized_context[f"{key}_paginated"] = True
                        optimized_context[f"{key}_total"] = len(value)
                        optimized_context[key] = value[:50]  # Paginate large lists

                    # Convert complex objects to simpler representations
                    elif hasattr(value, "__dict__") and len(value.__dict__) > 20:
                        optimized_context[f"{key}_summary"] = True

        return optimized_context

    def should_enable_streaming(self, template_name: str, context_size: int) -> bool:
        """Determine if streaming should be enabled for this render."""
        if not self.optimization_enabled:
            return False

        # Enable streaming for large contexts
        if context_size > 50000:  # 50KB
            return True

        # Historical analysis
        if template_name in self.template_stats:
            times = self.template_stats[template_name]
            if times and max(times) > 0.5:  # 500ms
                return True

        return False

    def get_optimal_cache_ttl(self, template_name: str) -> int:
        """Get optimal cache TTL for a template."""
        if not self.optimization_enabled:
            return 300  # Default 5 minutes

        # Analysis based on template usage patterns
        if template_name in self.template_stats:
            times = self.template_stats[template_name]
            if times:
                avg_time = sum(times) / len(times)

                # Slower templates get longer cache TTL
                if avg_time > 0.2:
                    return 1800  # 30 minutes
                elif avg_time > 0.1:
                    return 900  # 15 minutes

                return 300  # 5 minutes

        return 300

    def clear_stats(self) -> None:
        """Clear all performance statistics."""
        self.metrics_history.clear()
        self.template_stats.clear()
        self.cache_stats.clear()
        self.concurrent_renders = 0

    def export_metrics(self) -> dict[str, Any]:
        """Export metrics for external monitoring."""
        stats = self.get_performance_stats()

        return {
            "performance_stats": {
                "total_renders": stats.total_renders,
                "avg_render_time": stats.avg_render_time,
                "cache_hit_ratio": stats.cache_hit_ratio,
                "concurrent_peak": stats.concurrent_peak,
            },
            "template_performance": {
                "slowest": stats.slowest_templates,
                "fastest": stats.fastest_templates,
            },
            "recommendations": self.get_optimization_recommendations(),
            "timestamp": time.time(),
        }


# Global performance optimizer instance
_performance_optimizer = None


def get_performance_optimizer() -> PerformanceOptimizer:
    """Get global performance optimizer instance."""
    global _performance_optimizer
    if _performance_optimizer is None:
        _performance_optimizer = PerformanceOptimizer()
    return _performance_optimizer
