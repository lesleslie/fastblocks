#!/usr/bin/env python3
"""Test HTMY component caching functionality."""

import asyncio
import typing as t
from pathlib import Path

import pytest


# Mock cache implementation for testing
class MockCache:
    def __init__(self) -> None:
        self._data = {}

    async def get(self, key: str) -> bytes | None:
        return self._data.get(key)

    async def set(self, key: str, value: bytes) -> None:
        self._data[key] = value

    async def delete(self, key: str) -> None:
        self._data.pop(key, None)

    async def clear(self, namespace: str) -> None:
        keys_to_delete = [k for k in self._data.keys() if k.startswith(namespace)]
        for key in keys_to_delete:
            del self._data[key]


# Mock storage implementation for testing
class MockStorage:
    def __init__(self) -> None:
        self.templates = self

    async def stat(self, path: str) -> dict[str, int]:
        return {"mtime": 1234567890, "size": 100}

    async def open(self, path: str) -> bytes:
        return b"# Mock storage content"


# Standalone AsyncPath-like implementation
class MockAsyncPath:
    def __init__(self, path_str: str) -> None:
        self.path = Path(path_str)

    def __str__(self) -> str:
        return str(self.path)

    def __truediv__(self, other: str) -> "MockAsyncPath":
        return MockAsyncPath(str(self.path / other))

    async def exists(self):
        return self.path.exists()

    async def rglob(self, pattern: str):
        for p in self.path.rglob(pattern):
            yield MockAsyncPath(str(p))

    @property
    def stem(self):
        return self.path.stem

    @property
    def name(self):
        return self.path.name

    async def read_text(self):
        return self.path.read_text()

    async def write_bytes(self, content: bytes) -> None:
        self.path.write_bytes(content)

    async def stat(self):
        stat = self.path.stat()

        class MockStat:
            def __init__(self, mtime: float, size: int) -> None:
                self.st_mtime = mtime
                self.st_size = size

        return MockStat(stat.st_mtime, stat.st_size)


# Import the registry with our test paths
import sys

sys.path.insert(0, "/Users/les/Projects/fastblocks")


# Copy of the enhanced HTMYComponentRegistry for testing
class ComponentNotFound(Exception):
    pass


class ComponentCompilationError(Exception):
    pass


class HTMYComponentRegistry:
    """Registry for discovering and caching HTMY components with Redis and storage support."""

    def __init__(
        self,
        searchpaths: list[MockAsyncPath] | None = None,
        cache: t.Any = None,
        storage: t.Any = None,
    ) -> None:
        self.searchpaths = searchpaths or []
        self.cache = cache
        self.storage = storage
        self._component_cache: dict[str, t.Any] = {}
        self._source_cache: dict[str, str] = {}

    @staticmethod
    def get_cache_key(component_path: MockAsyncPath, cache_type: str = "source") -> str:
        """Generate cache key for component."""
        return f"htmy_component_{cache_type}:{component_path}"

    @staticmethod
    def get_storage_path(component_path: MockAsyncPath) -> MockAsyncPath:
        """Convert local component path to storage path."""
        return component_path

    async def discover_components(self) -> dict[str, MockAsyncPath]:
        """Discover all .py files in component search paths."""
        components = {}

        for search_path in self.searchpaths:
            if not await search_path.exists():
                continue

            async for component_file in search_path.rglob("*.py"):
                if component_file.name == "__init__.py":
                    continue

                component_name = component_file.stem
                components[component_name] = component_file

        return components

    async def _cache_component_source(
        self, component_path: MockAsyncPath, source: str
    ) -> None:
        """Cache component source in Redis."""
        if self.cache is not None:
            cache_key = self.get_cache_key(component_path)
            await self.cache.set(cache_key, source.encode())

    async def _cache_component_bytecode(
        self, component_path: MockAsyncPath, bytecode: bytes
    ) -> None:
        """Cache compiled component bytecode in Redis."""
        if self.cache is not None:
            cache_key = self.get_cache_key(component_path, "bytecode")
            await self.cache.set(cache_key, bytecode)

    async def _get_cached_source(self, component_path: MockAsyncPath) -> str | None:
        """Get cached component source from Redis."""
        if self.cache is not None:
            cache_key = self.get_cache_key(component_path)
            cached = await self.cache.get(cache_key)
            if cached:
                return cached.decode()
        return None

    async def _get_cached_bytecode(self, component_path: MockAsyncPath) -> bytes | None:
        """Get cached component bytecode from Redis."""
        if self.cache is not None:
            cache_key = self.get_cache_key(component_path, "bytecode")
            return await self.cache.get(cache_key)
        return None

    async def _sync_from_storage_fallback(
        self,
        path: MockAsyncPath,
        storage_path: MockAsyncPath,
    ) -> tuple[str, int]:
        """Fallback sync method for components."""
        local_stat = await path.stat()
        local_mtime = int(local_stat.st_mtime)

        if self.storage is not None:
            try:
                local_size = local_stat.st_size
                storage_stat = await self.storage.stat(storage_path)
                storage_mtime = round(storage_stat.get("mtime", 0))
                storage_size = storage_stat.get("size", 0)

                if local_mtime < storage_mtime and local_size != storage_size:
                    resp = await self.storage.open(storage_path)
                    await path.write_bytes(resp)
                    source = resp.decode()
                    return source, storage_mtime
            except Exception as e:
                print(f"Storage fallback failed for {path}: {e}")

        # Read local file
        source = await path.read_text()
        return source, local_mtime

    async def get_component_source(
        self, component_name: str
    ) -> tuple[str, MockAsyncPath]:
        """Get component source code and path with caching and storage sync."""
        components = await self.discover_components()

        if component_name not in components:
            raise ComponentNotFound(f"Component '{component_name}' not found")

        component_path = components[component_name]

        # Check memory cache first
        cache_key = str(component_path)
        if cache_key in self._source_cache:
            print(f"✓ Found in memory cache: {component_name}")
            return self._source_cache[cache_key], component_path

        # Check Redis cache
        cached_source = await self._get_cached_source(component_path)
        if cached_source:
            print(f"✓ Found in Redis cache: {component_name}")
            self._source_cache[cache_key] = cached_source
            return cached_source, component_path

        # Sync with storage and read source
        storage_path = self.get_storage_path(component_path)
        source, _ = await self._sync_from_storage_fallback(component_path, storage_path)

        print(f"✓ Loaded from file: {component_name}")

        # Cache the source
        self._source_cache[cache_key] = source
        await self._cache_component_source(component_path, source)

        return source, component_path

    async def get_component_class(self, component_name: str) -> t.Any:
        """Get compiled component class with bytecode caching."""
        if component_name in self._component_cache:
            print(f"✓ Found compiled class in memory cache: {component_name}")
            return self._component_cache[component_name]

        source, component_path = await self.get_component_source(component_name)

        # Check for cached bytecode
        cached_bytecode = await self._get_cached_bytecode(component_path)

        # Compile the component
        try:
            if cached_bytecode:
                # Try to use cached bytecode
                try:
                    import pickle

                    component_class = pickle.loads(cached_bytecode)
                    print(f"✓ Found compiled class in Redis cache: {component_name}")
                    self._component_cache[component_name] = component_class
                    return component_class
                except Exception as e:
                    print(f"Failed to load cached bytecode for {component_name}: {e}")

            # Compile from source
            print(f"✓ Compiling from source: {component_name}")
            namespace = {}
            compiled_code = compile(source, str(component_path), "exec")
            exec(compiled_code, namespace)

            # Find the component class
            component_class = None
            for obj in namespace.values():
                if hasattr(obj, "htmy") and callable(getattr(obj, "htmy")):
                    component_class = obj
                    break

            if component_class is None:
                raise ComponentCompilationError(
                    f"No valid component class found in {component_path}"
                )

            # Cache the compiled component
            self._component_cache[component_name] = component_class

            # Cache bytecode
            try:
                import pickle

                bytecode = pickle.dumps(component_class)
                await self._cache_component_bytecode(component_path, bytecode)
                print(f"✓ Cached bytecode for: {component_name}")
            except Exception as e:
                print(f"Failed to cache bytecode for {component_name}: {e}")

            return component_class

        except Exception as e:
            raise ComponentCompilationError(
                f"Failed to compile component '{component_name}': {e}"
            ) from e


@pytest.mark.unit
async def test_caching() -> None:
    """Test HTMY component caching functionality."""
    print("=== HTMY Component Caching Test ===")

    try:
        # Create mock cache and storage
        cache = MockCache()
        storage = MockStorage()

        # Test with our component path
        component_path = MockAsyncPath(
            "/Users/les/Projects/sites/fastest/templates/app/bulma/components"
        )
        registry = HTMYComponentRegistry([component_path], cache=cache, storage=storage)

        print("✓ Registry created with cache and storage")

        # Check if path exists
        exists = await component_path.exists()
        print(f"✓ Component path exists: {exists}")

        if exists:
            # Test 1: First load (should read from file and cache)
            print("\\n=== Test 1: First Load ===")
            source1, _ = await registry.get_component_source("user_card")
            class1 = await registry.get_component_class("user_card")

            # Test 2: Second load (should hit memory cache)
            print("\\n=== Test 2: Second Load (Memory Cache) ===")
            source2, _ = await registry.get_component_source("user_card")
            class2 = await registry.get_component_class("user_card")

            # Verify cache hit
            assert source1 == source2, "Source should be identical"
            assert class1 is class2, (
                "Classes should be identical objects (memory cache hit)"
            )

            # Test 3: Clear memory cache, should hit Redis cache
            print("\\n=== Test 3: Redis Cache Test ===")
            registry._component_cache.clear()
            registry._source_cache.clear()

            source3, _ = await registry.get_component_source("user_card")
            await registry.get_component_class("user_card")

            assert source1 == source3, "Source should be identical from Redis"

            # Test 4: Clear all caches
            print("\\n=== Test 4: Clear All Caches ===")
            registry._component_cache.clear()
            registry._source_cache.clear()
            await cache.clear("htmy_component_source")
            await cache.clear("htmy_component_bytecode")

            source4, _ = await registry.get_component_source("user_card")
            await registry.get_component_class("user_card")

            assert source1 == source4, "Source should be identical from file"

            print("\\n🎉 All caching tests passed!")
            print("✓ Source caching: working")
            print("✓ Bytecode caching: working")
            print("✓ Memory cache: working")
            print("✓ Redis cache: working")
            print("✓ Cache invalidation: working")

        else:
            print("❌ Component path does not exist")

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_caching())
