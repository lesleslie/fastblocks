"""Tests for the ChoiceLoader class."""

import typing as t
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from anyio import Path as AsyncPath


class MockAsyncPath:
    def __init__(self, path: t.Union[str, Path, "MockAsyncPath"] = "") -> None:
        if isinstance(path, MockAsyncPath):
            self._path = path._path
        else:
            self._path = str(path)

    def __str__(self) -> str:
        return self._path

    def __truediv__(
        self,
        other: t.Union[str, Path, "MockAsyncPath"],
    ) -> "MockAsyncPath":
        other_str = str(other)
        if self._path.endswith("/"):
            return MockAsyncPath(f"{self._path}{other_str}")
        return MockAsyncPath(f"{self._path}/{other_str}")

    async def exists(self) -> bool:
        return True

    async def is_file(self) -> bool:
        return "." in self._path.split("/")[-1]


class MockConfig:
    def __init__(self) -> None:
        self.app = MagicMock()
        self.app.name = "test_app"
        self.app.debug = True

        self.templates = MagicMock()
        self.templates.directory = "templates"
        self.templates.extension = ".html"

        self.cache = MagicMock()
        self.cache.enabled = True
        self.cache.ttl = 3600


class MockBaseLoader:
    def __init__(self, searchpath: list[MockAsyncPath] | None = None) -> None:
        self.searchpath = searchpath or [MockAsyncPath("templates")]
        self.encoding = "utf-8"

    async def get_source_async(
        self,
        environment: t.Any = None,
        template: str = "",
    ) -> tuple[str, str, t.Callable[[], bool]]:
        msg = "Subclasses must implement get_source_async"
        raise NotImplementedError(msg)

    async def list_templates_async(self) -> list[str]:
        return []


class MockFileSystemLoader(MockBaseLoader):
    def __init__(
        self,
        searchpath: list[MockAsyncPath] | None = None,
        encoding: str | None = None,
        cache: t.Any = None,
        storage: t.Any = None,
        config: t.Any = None,
    ) -> None:
        super().__init__(searchpath=searchpath)
        self.encoding = encoding or "utf-8"
        self.cache = cache
        self.storage = storage
        self.config = config
        self._templates = {}

    async def get_source_async(
        self,
        environment: t.Any = None,
        template: str = "",
    ) -> tuple[str, str, t.Callable[[], bool]]:
        if template in self._templates:
            return (
                self._templates[template],
                str(self.searchpath[0] / template),
                lambda: True,
            )

        msg = f"Template {template} not found"
        raise FileNotFoundError(msg)


class MockRedisLoader(MockBaseLoader):
    def __init__(
        self,
        encoding: str | None = None,
        cache: t.Any = None,
        storage: t.Any = None,
        config: t.Any = None,
    ) -> None:
        super().__init__()
        self.encoding = encoding or "utf-8"
        self.cache = cache
        self.storage = storage
        self.config = config
        self._templates = {
            "test.html": "<html><body>Test from redis</body></html>",
        }

    async def get_source_async(
        self,
        environment: t.Any = None,
        template: str = "",
    ) -> tuple[str, str, t.Callable[[], bool]]:
        if template in self._templates:
            template_path = AsyncPath("templates") / template
            return self._templates[template], str(template_path), lambda: True

        msg = f"Template {template} not found"
        raise FileNotFoundError(msg)


class MockChoiceLoader(MockBaseLoader):
    def __init__(
        self,
        loaders: list[t.Any] | None = None,
        encoding: str | None = None,
        cache: t.Any = None,
        storage: t.Any = None,
        config: t.Any = None,
    ) -> None:
        super().__init__()
        self.loaders = loaders or []
        self.encoding = encoding or "utf-8"
        self.cache = cache
        self.storage = storage
        self.config = config

    async def get_source_async(
        self,
        environment: t.Any = None,
        template: str = "",
    ) -> tuple[str, str, t.Callable[[], bool]]:
        for loader in self.loaders:
            try:
                return await loader.get_source_async(environment, template)
            except FileNotFoundError:
                continue

        msg = f"Template {template} not found in any loader"
        raise FileNotFoundError(msg)


@pytest.fixture
def config() -> MockConfig:
    return MockConfig()


@pytest.fixture
def mock_cache() -> AsyncMock:
    cache = AsyncMock()
    cache.get.return_value = None
    return cache


@pytest.fixture
def mock_storage() -> AsyncMock:
    storage = AsyncMock()
    storage.get.return_value = None
    return storage


@pytest.mark.asyncio
async def test_choice_loader_get_source_async_first_loader_exists(
    config: MockConfig,
    mock_cache: AsyncMock,
    mock_storage: AsyncMock,
    tmp_path: Path,
) -> None:
    fs_loader = MockFileSystemLoader(
        searchpath=[MockAsyncPath(tmp_path)],
        encoding="utf-8",
        cache=mock_cache,
        storage=mock_storage,
        config=config,
    )

    redis_loader = MockRedisLoader(
        encoding="utf-8",
        cache=mock_cache,
        storage=mock_storage,
        config=config,
    )

    choice_loader = MockChoiceLoader(
        loaders=[fs_loader, redis_loader],
        encoding="utf-8",
        cache=mock_cache,
        storage=mock_storage,
        config=config,
    )

    template_name = "test.html"
    template_content = "<html><body>Test from filesystem</body></html>"

    fs_loader._templates[template_name] = template_content
    template_path = str(tmp_path / template_name)

    source, path, uptodate = await choice_loader.get_source_async(None, template_name)

    assert source == template_content
    assert path == template_path
    assert uptodate()


@pytest.mark.asyncio
async def test_choice_loader_get_source_async_second_loader_exists(
    config: MockConfig,
    mock_cache: AsyncMock,
    mock_storage: AsyncMock,
    tmp_path: Path,
) -> None:
    fs_loader = MockFileSystemLoader(
        searchpath=[MockAsyncPath(tmp_path)],
        encoding="utf-8",
        cache=mock_cache,
        storage=mock_storage,
        config=config,
    )

    redis_loader = MockRedisLoader(
        encoding="utf-8",
        cache=mock_cache,
        storage=mock_storage,
        config=config,
    )

    choice_loader = MockChoiceLoader(
        loaders=[fs_loader, redis_loader],
        encoding="utf-8",
        cache=mock_cache,
        storage=mock_storage,
        config=config,
    )

    template_name = "test.html"
    template_content = "<html><body>Test from redis</body></html>"
    template_path = str(AsyncPath("templates") / template_name)

    source, path, uptodate = await choice_loader.get_source_async(None, template_name)

    assert source == template_content
    assert path == template_path
    assert uptodate()
