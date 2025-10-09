"""Enhanced caching strategies for FastBlocks template rendering.

This module provides advanced caching capabilities including:
- Intelligent cache warming based on usage patterns
- Hierarchical cache invalidation with dependencies
- Performance monitoring and analytics
- Multi-tier caching with automatic promotion/demotion
- Predictive cache preloading

Requirements:
- acb[cache]>=0.19.0
- redis>=4.0.0 (for Redis backend)
- asyncio

Author: lesleslie <les@wedgwoodwebworks.com>
Created: 2025-01-12
"""

import asyncio
import builtins
import time
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable
from contextlib import suppress
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import UUID

from acb.depends import depends


class CacheTier(Enum):
    """Cache tier levels for multi-tier caching."""

    HOT = "hot"  # Frequently accessed, in-memory
    WARM = "warm"  # Moderately accessed, memory/redis hybrid
    COLD = "cold"  # Rarely accessed, redis only
    FROZEN = "frozen"  # Archive tier, slow but persistent


@dataclass
class CacheMetrics:
    """Cache performance metrics."""

    hits: int = 0
    misses: int = 0
    evictions: int = 0
    warming_operations: int = 0
    invalidations: int = 0
    tier_promotions: int = 0
    tier_demotions: int = 0
    memory_usage: int = 0

    @property
    def hit_ratio(self) -> float:
        """Calculate cache hit ratio."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    @property
    def efficiency(self) -> float:
        """Calculate cache efficiency (hits vs operations)."""
        operations = self.hits + self.misses + self.warming_operations
        return self.hits / operations if operations > 0 else 0.0


@dataclass
class CacheEntry:
    """Enhanced cache entry with metadata."""

    key: str
    value: Any
    tier: CacheTier = CacheTier.COLD
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0
    dependencies: set[str] = field(default_factory=set)
    tags: set[str] = field(default_factory=set)
    size: int = 0
    ttl: int | None = None

    @property
    def age(self) -> float:
        """Age of the cache entry in seconds."""
        return time.time() - self.created_at

    @property
    def idle_time(self) -> float:
        """Time since last access in seconds."""
        return time.time() - self.last_accessed

    def touch(self) -> None:
        """Update access statistics."""
        self.last_accessed = time.time()
        self.access_count += 1


@dataclass
class CacheStats:
    """Comprehensive cache statistics."""

    total_entries: int = 0
    tier_distribution: dict[CacheTier, int] = field(
        default_factory=lambda: {tier: 0 for tier in CacheTier}
    )
    memory_usage_by_tier: dict[CacheTier, int] = field(
        default_factory=lambda: {tier: 0 for tier in CacheTier}
    )
    metrics: CacheMetrics = field(default_factory=CacheMetrics)
    hot_entries: list[str] = field(default_factory=list)
    cold_entries: list[str] = field(default_factory=list)


class EnhancedCacheManager:
    """Enhanced cache manager with intelligent strategies."""

    # Required ACB 0.19.0+ metadata
    MODULE_ID: UUID = UUID("01937d89-b123-4567-89ab-123456789def")
    MODULE_STATUS: str = "stable"

    def __init__(
        self,
        max_memory_entries: int = 1000,
        hot_tier_size: int = 100,
        warm_tier_size: int = 300,
        promotion_threshold: int = 5,
        demotion_idle_time: int = 3600,
    ) -> None:
        """Initialize enhanced cache manager.

        Args:
            max_memory_entries: Maximum entries to keep in memory
            hot_tier_size: Maximum entries in hot tier
            warm_tier_size: Maximum entries in warm tier
            promotion_threshold: Access count threshold for promotion
            demotion_idle_time: Seconds of idle time before demotion
        """
        self.max_memory_entries = max_memory_entries
        self.hot_tier_size = hot_tier_size
        self.warm_tier_size = warm_tier_size
        self.promotion_threshold = promotion_threshold
        self.demotion_idle_time = demotion_idle_time

        # Internal data structures
        self.entries: dict[str, CacheEntry] = {}
        self.access_history: deque[tuple[str, float]] = deque(maxlen=10000)
        self.dependency_graph: dict[str, set[str]] = defaultdict(set)
        self.tag_index: dict[str, set[str]] = defaultdict(set)
        self.warming_queue: asyncio.Queue[
            tuple[str, Callable[[str], Awaitable[Any]]]
        ] = asyncio.Queue()

        # Performance tracking
        self.metrics = CacheMetrics()
        self.performance_history: deque[dict[str, Any]] = deque(maxlen=1000)

        # Background tasks
        self._maintenance_task: asyncio.Task[None] | None = None
        self._warming_task: asyncio.Task[None] | None = None

        # Register with ACB
        with suppress(Exception):
            depends.set(self)

    async def initialize(self) -> None:
        """Initialize cache manager and start background tasks."""
        # Start maintenance task
        self._maintenance_task = asyncio.create_task(self._maintenance_loop())

        # Start cache warming task
        self._warming_task = asyncio.create_task(self._warming_loop())

    async def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache with tier management."""
        start_time = time.time()

        try:
            if key in self.entries:
                entry = self.entries[key]

                # Check TTL expiration
                if self._is_expired(entry):
                    await self._remove_entry(key)
                    self.metrics.misses += 1
                    return default

                # Update access statistics
                entry.touch()
                self.access_history.append((key, time.time()))

                # Consider promotion
                await self._consider_promotion(entry)

                self.metrics.hits += 1
                return entry.value
            else:
                self.metrics.misses += 1
                return default

        finally:
            # Track performance
            operation_time = time.time() - start_time
            self.performance_history.append(
                {
                    "operation": "get",
                    "key": key,
                    "time": operation_time,
                    "hit": key in self.entries,
                    "timestamp": time.time(),
                }
            )

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
        dependencies: set[str] | None = None,
        tags: set[str] | None = None,
        tier: CacheTier | None = None,
    ) -> None:
        """Set value in cache with metadata."""
        # Calculate entry size (approximate)
        size = self._calculate_size(value)

        # Create cache entry
        entry = CacheEntry(
            key=key,
            value=value,
            tier=tier or CacheTier.COLD,
            dependencies=dependencies or set(),
            tags=tags or set(),
            size=size,
            ttl=ttl,
        )

        # Store entry
        self.entries[key] = entry

        # Update indexes
        self._update_dependency_graph(key, dependencies or set())
        self._update_tag_index(key, tags or set())

        # Manage memory usage
        await self._manage_memory()

        # Update metrics
        self.metrics.memory_usage += size

    async def delete(self, key: str) -> bool:
        """Delete entry from cache."""
        if key in self.entries:
            await self._remove_entry(key)
            return True
        return False

    async def invalidate_by_dependency(self, dependency: str) -> list[str]:
        """Invalidate all entries that depend on the given dependency."""
        invalidated = []

        if dependency in self.dependency_graph:
            dependent_keys = self.dependency_graph[dependency].copy()

            for key in dependent_keys:
                if await self.delete(key):
                    invalidated.append(key)

            # Clean up dependency graph
            del self.dependency_graph[dependency]

        self.metrics.invalidations += len(invalidated)
        return invalidated

    async def invalidate_by_tags(self, tags: builtins.set[str]) -> list[str]:
        """Invalidate all entries with any of the given tags."""
        invalidated = []

        for tag in tags:
            if tag in self.tag_index:
                tagged_keys = self.tag_index[tag].copy()

                for key in tagged_keys:
                    if key not in invalidated and await self.delete(key):
                        invalidated.append(key)

        self.metrics.invalidations += len(invalidated)
        return invalidated

    async def warm_cache(
        self, keys: list[str], loader_func: Callable[[str], Awaitable[Any]]
    ) -> None:
        """Warm cache with specified keys using loader function."""
        for key in keys:
            if key not in self.entries:
                await self.warming_queue.put((key, loader_func))

        self.metrics.warming_operations += len(keys)

    async def get_stats(self) -> CacheStats:
        """Get comprehensive cache statistics."""
        tier_distribution = {tier: 0 for tier in CacheTier}
        memory_usage_by_tier = {tier: 0 for tier in CacheTier}
        hot_entries = []
        cold_entries = []

        for entry in self.entries.values():
            tier_distribution[entry.tier] += 1
            memory_usage_by_tier[entry.tier] += entry.size

            if entry.tier == CacheTier.HOT:
                hot_entries.append(entry.key)
            elif entry.tier == CacheTier.COLD:
                cold_entries.append(entry.key)

        return CacheStats(
            total_entries=len(self.entries),
            tier_distribution=tier_distribution,
            memory_usage_by_tier=memory_usage_by_tier,
            metrics=self.metrics,
            hot_entries=hot_entries[:10],  # Top 10 hot entries
            cold_entries=cold_entries[:10],  # Top 10 cold entries
        )

    async def get_performance_report(self) -> dict[str, Any]:
        """Get detailed performance report."""
        if not self.performance_history:
            return {"message": "No performance data available"}

        # Calculate averages
        recent_operations = list(self.performance_history)[-100:]  # Last 100 operations
        avg_get_time = sum(
            op["time"] for op in recent_operations if op["operation"] == "get"
        ) / max(1, sum(1 for op in recent_operations if op["operation"] == "get"))

        # Hit ratio trend
        hits = sum(1 for op in recent_operations if op.get("hit"))
        hit_ratio = hits / len(recent_operations) if recent_operations else 0

        return {
            "avg_get_time": avg_get_time,
            "hit_ratio": hit_ratio,
            "total_operations": len(self.performance_history),
            "recent_operations": len(recent_operations),
            "cache_efficiency": self.metrics.efficiency,
            "memory_usage": self.metrics.memory_usage,
            "tier_promotions": self.metrics.tier_promotions,
            "tier_demotions": self.metrics.tier_demotions,
        }

    async def optimize_tiers(self) -> dict[str, int]:
        """Optimize cache tiers based on access patterns."""
        promotions = 0
        demotions = 0

        for entry in list(self.entries.values()):
            # Promotion logic
            if (
                entry.tier != CacheTier.HOT
                and entry.access_count >= self.promotion_threshold
            ):
                await self._promote_entry(entry)
                promotions += 1

            # Demotion logic
            elif (
                entry.tier != CacheTier.COLD
                and entry.idle_time > self.demotion_idle_time
            ):
                await self._demote_entry(entry)
                demotions += 1

        self.metrics.tier_promotions += promotions
        self.metrics.tier_demotions += demotions

        return {
            "promotions": promotions,
            "demotions": demotions,
            "hot_tier_count": sum(
                1 for e in self.entries.values() if e.tier == CacheTier.HOT
            ),
            "warm_tier_count": sum(
                1 for e in self.entries.values() if e.tier == CacheTier.WARM
            ),
            "cold_tier_count": sum(
                1 for e in self.entries.values() if e.tier == CacheTier.COLD
            ),
        }

    async def clear(self, pattern: str | None = None) -> int:
        """Clear cache entries, optionally matching a pattern."""
        cleared = 0

        if pattern:
            import re

            regex = re.compile(pattern)  # REGEX OK: pattern-based cache invalidation
            keys_to_remove = [
                key for key in self.entries.keys() if regex.search(key)
            ]  # REGEX OK: pattern-based cache invalidation
        else:
            keys_to_remove = list(self.entries.keys())

        for key in keys_to_remove:
            if await self.delete(key):
                cleared += 1

        return cleared

    def _calculate_size(self, value: Any) -> int:
        """Calculate approximate size of cached value."""
        try:
            import sys

            return sys.getsizeof(value)
        except Exception:
            # Fallback estimation
            if isinstance(value, str):
                return len(value.encode("utf-8"))
            elif isinstance(value, list | tuple):
                return sum(self._calculate_size(item) for item in value)
            elif isinstance(value, dict):
                return sum(
                    self._calculate_size(k) + self._calculate_size(v)
                    for k, v in value.items()
                )

            return 64  # Default estimate

    def _is_expired(self, entry: CacheEntry) -> bool:
        """Check if cache entry is expired."""
        if entry.ttl is None:
            return False
        return entry.age > entry.ttl

    async def _remove_entry(self, key: str) -> None:
        """Remove entry and clean up indexes."""
        if key not in self.entries:
            return

        entry = self.entries[key]

        # Update metrics
        self.metrics.memory_usage -= entry.size
        self.metrics.evictions += 1

        # Clean up indexes
        for dep in entry.dependencies:
            self.dependency_graph[dep].discard(key)
            if not self.dependency_graph[dep]:
                del self.dependency_graph[dep]

        for tag in entry.tags:
            self.tag_index[tag].discard(key)
            if not self.tag_index[tag]:
                del self.tag_index[tag]

        # Remove entry
        del self.entries[key]

    def _update_dependency_graph(
        self, key: str, dependencies: builtins.set[str]
    ) -> None:
        """Update dependency graph."""
        for dep in dependencies:
            self.dependency_graph[dep].add(key)

    def _update_tag_index(self, key: str, tags: builtins.set[str]) -> None:
        """Update tag index."""
        for tag in tags:
            self.tag_index[tag].add(key)

    async def _consider_promotion(self, entry: CacheEntry) -> None:
        """Consider promoting entry to higher tier."""
        if entry.access_count >= self.promotion_threshold:
            await self._promote_entry(entry)

    async def _promote_entry(self, entry: CacheEntry) -> None:
        """Promote entry to higher tier."""
        if entry.tier == CacheTier.COLD:
            entry.tier = CacheTier.WARM
        elif entry.tier == CacheTier.WARM:
            entry.tier = CacheTier.HOT
        # HOT is the highest tier

    async def _demote_entry(self, entry: CacheEntry) -> None:
        """Demote entry to lower tier."""
        if entry.tier == CacheTier.HOT:
            entry.tier = CacheTier.WARM
        elif entry.tier == CacheTier.WARM:
            entry.tier = CacheTier.COLD
        # COLD is the lowest active tier

    async def _manage_memory(self) -> None:
        """Manage memory usage by evicting entries."""
        if len(self.entries) <= self.max_memory_entries:
            return

        # Sort entries by tier and access patterns for eviction
        entries_by_priority = sorted(
            self.entries.values(),
            key=lambda e: (e.tier.value, e.access_count, -e.idle_time),
        )

        # Evict least important entries
        to_evict = len(self.entries) - self.max_memory_entries
        for entry in entries_by_priority[:to_evict]:
            await self._remove_entry(entry.key)

    async def _maintenance_loop(self) -> None:
        """Background maintenance loop."""
        while True:
            try:
                # Remove expired entries
                expired_keys = [
                    key
                    for key, entry in self.entries.items()
                    if self._is_expired(entry)
                ]

                for key in expired_keys:
                    await self._remove_entry(key)

                # Optimize tiers
                await self.optimize_tiers()

                # Memory cleanup
                await self._manage_memory()

                # Sleep for 60 seconds
                await asyncio.sleep(60)

            except asyncio.CancelledError:
                break
            except Exception:
                # Continue on errors
                await asyncio.sleep(60)

    async def _warming_loop(self) -> None:
        """Background cache warming loop."""
        while True:
            try:
                # Wait for warming request
                key, loader_func = await self.warming_queue.get()

                # Check if still needed
                if key not in self.entries:
                    with suppress(Exception):
                        value = await loader_func(key)
                        await self.set(
                            key,
                            value,
                            tier=CacheTier.WARM,  # Warmed entries start in WARM tier
                        )

                # Mark task as done
                self.warming_queue.task_done()

            except asyncio.CancelledError:
                break
            except Exception:
                # Continue on errors
                await asyncio.sleep(1)

    async def shutdown(self) -> None:
        """Shutdown cache manager and cleanup resources."""
        if self._maintenance_task:
            self._maintenance_task.cancel()
            try:
                await self._maintenance_task
            except asyncio.CancelledError:
                pass

        if self._warming_task:
            self._warming_task.cancel()
            try:
                await self._warming_task
            except asyncio.CancelledError:
                pass

        self.entries.clear()
        self.dependency_graph.clear()
        self.tag_index.clear()


# Global enhanced cache manager instance
_enhanced_cache = None


def get_enhanced_cache() -> EnhancedCacheManager:
    """Get global enhanced cache manager instance."""
    global _enhanced_cache
    if _enhanced_cache is None:
        _enhanced_cache = EnhancedCacheManager()
    return _enhanced_cache


# ACB 0.19.0+ compatibility
__all__ = [
    "EnhancedCacheManager",
    "CacheTier",
    "CacheEntry",
    "CacheStats",
    "get_enhanced_cache",
]
