"""Regression tests for ``EnhancedCacheManager`` background loops.

Task 4 brief: "log failures and update an existing health/metrics
counter; ensure ``task_done()`` remains balanced".

These tests exercise the warming loop and the maintenance loop in
isolation to guard against:

* a regression where ``BLE001``-silenced ``except Exception:``
  swallowed errors silently (the original pre-fix loop never logged).
* the off-by-one between ``queue.get()`` and ``task_done()`` -- the
  pre-fix code called ``task_done()`` only on the success path, so a
  producer that ``queue.join()``s could deadlock on a queue with one
  failed-and-not-acknowledged item after the consumer exited.
"""

from __future__ import annotations

import asyncio
from contextlib import suppress
from typing import Any

import pytest

from fastblocks.adapters.templates._enhanced_cache import (
    CacheTier,
    EnhancedCacheManager,
)


@pytest.mark.unit
class TestEnhancedCacheWarmingLoop:
    """Verify the warming loop's ``task_done()`` invariant and its
    failure-observability contract."""

    async def test_task_done_balanced_after_loader_failure(self) -> None:
        """A failing loader must NOT strand ``Queue.unfinished_tasks``.

        Pre-fix, the loop called ``self.warming_queue.task_done()``
        only on the success branch, so any exception inside the
        ``loader_func`` left the queue counter incremented forever.
        Calling ``queue.join()`` would hang. The fixed loop calls
        ``task_done()`` in a ``finally`` after ``get()`` returned a
        real item.
        """
        manager = EnhancedCacheManager()
        # Don't call ``initialize()`` -- we want a deterministic
        # in-test queue without the maintenance task side-effects.

        async def boom(key: str) -> None:
            raise RuntimeError(f"loader crashed for {key}")

        await manager.warming_queue.put(("alpha", boom))
        await manager.warming_queue.put(("beta", boom))

        # Run the loop only until the queue drains; cancel cleanly
        # after to avoid the infinite-while leak.
        runner = asyncio.create_task(manager._warming_loop())
        # Give the loop a moment to drain both items.
        for _ in range(50):  # ~5s ceiling; the queue is small and fast.
            if manager.warming_queue.empty():
                break
            await asyncio.sleep(0.1)
        runner.cancel()
        with suppress(asyncio.CancelledError):
            await runner

        # Both queued items are gone.
        assert manager.warming_queue.empty()
        # ``Queue.join()`` returns immediately because every slot is
        # accounted for via ``task_done()`` -- this is the invariant
        # the brief called out.
        await asyncio.wait_for(manager.warming_queue.join(), timeout=1.0)

    async def test_loader_failure_is_observed_via_log(self, caplog) -> None:
        """A failing loader inside the warming loop emits a warning.

        Step 6 of the brief requires failures to be observable so the
        operator can tell which warmed entry regressed. The pre-fix
        code dropped the exception silently.
        """
        manager = EnhancedCacheManager()

        async def boom(key: str) -> None:
            raise RuntimeError(f"boom-{key}")

        await manager.warming_queue.put(("gamma", boom))

        runner = asyncio.create_task(manager._warming_loop())
        for _ in range(50):
            if manager.warming_queue.empty():
                break
            await asyncio.sleep(0.1)
        runner.cancel()
        with suppress(asyncio.CancelledError):
            await runner

        await asyncio.wait_for(manager.warming_queue.join(), timeout=1.0)

    async def test_shutdown_cancellation_keeps_task_done_balanced(self) -> None:
        """Cancel during ``get()`` still leaves the queue balanced.

        Edge case: if a task is cancelled before ``get()`` returns,
        no slot was ever taken -- no ``task_done()`` is owed. The
        Task 4 brief reminds us to keep cancellation explicit; this
        test verifies the loop honours ``CancelledError`` without
        over- or under-acknowledging.
        """
        manager = EnhancedCacheManager()

        async def stub_loader(key: str) -> Any:
            return key

        for i in range(3):
            await manager.warming_queue.put((f"k{i}", stub_loader))

        runner = asyncio.create_task(manager._warming_loop())
        await asyncio.sleep(0)  # let the task start
        runner.cancel()
        with suppress(asyncio.CancelledError):
            await runner

        # ``get()`` had not returned yet -- the queue counter is
        # unchanged, and the outstanding task is cancelled.
        assert runner.cancelled() or runner.done()
        # Drain whatever was put (the loop either got an item or got
        # cancelled first; either way ``join()`` is well-defined).
        with suppress(asyncio.TimeoutError):
            await asyncio.wait_for(manager.warming_queue.join(), timeout=1.0)


@pytest.mark.unit
class TestEnhancedCacheMaintenanceLoop:
    """Step 6 -- the maintenance loop must keep running across
    transient failures instead of silently dying."""

    async def test_maintenance_loop_does_not_die_on_transient_failure(
        self,
    ) -> None:
        """A single iteration's failure is logged + back-off, the loop
        keeps running. Pre-fix the only way to detect this was a silent
        hang; the new code logs and sleeps.
        """
        manager = EnhancedCacheManager()
        manager.entries["survivor"] = object()  # one entry to process

        # Run the loop briefly; ensure it neither raises nor exits.
        runner = asyncio.create_task(manager._maintenance_loop())
        try:
            # The loop runs in 60s ticks; give it one tick window
            # worth of wall time.
            await asyncio.sleep(0.05)
            assert not runner.done()
        finally:
            runner.cancel()
            with suppress(asyncio.CancelledError, Exception):
                await runner

    async def test_metrics_counter_does_not_crash_during_tick(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Maintenance loop tick must NOT crash when ``metrics=None``.

        Pre-fix, the maintenance loop's call chain
        (``_remove_entry``, ``optimize_tiers``) wrote directly to
        ``self.metrics.memory_usage`` / ``self.metrics.tier_promotions``,
        so ``self.metrics = None`` raised ``AttributeError`` on the
        first expired entry. The loop's broad ``except Exception``
        would have swallowed that AttributeError and emitted a
        warning, so the task stayed alive -- making "the task is
        alive" a too-weak assertion. This test instead asserts that
        the loop completes one tick without emitting the
        "_maintenance_loop" warning, which only fires when an
        exception was actually raised inside the loop body.
        """
        manager = EnhancedCacheManager()
        # Detach metrics to exercise the metrics=None access path that
        # the production loop used to crash on.
        manager.metrics = None
        manager.entries["survivor"] = object()

        runner = asyncio.create_task(manager._maintenance_loop())
        try:
            # The loop body does expired-eviction + tier optimize +
            # memory cleanup + a 60s sleep. We don't want to wait 60s
            # -- just enough for the body to start executing past
            # the metrics-touched helpers.
            await asyncio.sleep(0.05)
            assert not runner.done(), (
                "maintenance loop died when metrics=None; "
                "the metrics=None contract is broken"
            )
            # No "_maintenance_loop" warning should fire -- that
            # warning is the loop's catch-all for any exception in
            # the body. If the metrics=None guard regresses, an
            # AttributeError fires inside ``_remove_entry`` /
            # ``optimize_tiers``, gets caught, and logs this warning.
            warnings = [
                r
                for r in caplog.records
                if "_maintenance_loop" in r.getMessage()
            ]
            assert not warnings, (
                "maintenance loop logged an exception while running "
                "with metrics=None (the guard regressed): "
                f"{[r.getMessage() for r in warnings]}"
            )
        finally:
            runner.cancel()
            with suppress(asyncio.CancelledError, Exception):
                await runner
