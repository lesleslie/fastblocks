"""Regression test for B023 closure-binding bug in ``fastblocks.caching``.

Pin the B023 ``function-uses-loop-variable`` rule observed at
``fastblocks/caching.py:523`` (``_delete_cache_entries``), where the inner
``_publish_event`` coroutine bound the loop's ``cache_key`` by reference and
therefore could only ever observe the final iteration's value when it was
eventually awaited.

This test ensures each scheduled publish task receives the cache key
captured at the moment of scheduling — not the final key from the loop.
"""

from __future__ import annotations

import asyncio
from typing import Any

from starlette.datastructures import URL, Headers


class _FakeCache:
    async def delete(self, _key: str) -> None:
        return None


class _FakeLogger:
    def debug(self, _message: str) -> None:
        return None


async def test_cache_helpers_bind_each_cache_key(monkeypatch: Any) -> None:
    from fastblocks.caching import _delete_cache_entries

    published: list[str] = []

    async def publish_cache_invalidation(**kwargs: Any) -> None:
        published.append(kwargs["cache_key"])

    async def generate_key(_url: Any, *, method: str, headers: Any, varying_headers: Any) -> str:
        return f"{method}-key"

    monkeypatch.setattr("fastblocks.caching.generate_cache_key", generate_key)
    monkeypatch.setattr(
        "fastblocks.adapters.templates._events_wrapper.publish_cache_invalidation",
        publish_cache_invalidation,
    )

    await _delete_cache_entries(
        URL("https://example.test"),
        Headers(),
        _FakeCache(),
        _FakeLogger(),
        {},
    )

    # Yield control so the scheduled publish tasks can run.
    for _ in range(5):
        await asyncio.sleep(0)
        if len(published) >= 2:
            break

    assert published == ["GET-key", "HEAD-key"]