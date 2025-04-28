"""Consolidated test fixtures for all tests."""

import tempfile
from pathlib import Path
from typing import Any, AsyncGenerator, Generator, Iterator
from unittest import mock

import pytest
from acb.config import Config
from acb.depends import depends
from anyio import Path as AsyncPath
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles
from fastblocks.adapters.templates._base import (
    TemplateContext,
    TemplateRenderer,
    TemplateResponse,
)

_original_methods = {}

#
#


class MockAdapterClass:
    def __init__(self, name: str, category: str | None = None) -> None:
        self.name = name
        self.category = category or name
        self.class_name = f"Mock{name.capitalize()}"
        self.enabled = True
        self.installed = True
        self.pkg = "test"


class MockTemplatesClass(MockAdapterClass):
    def __init__(self) -> None:
        super().__init__("templates")


class MockModelsClass(MockAdapterClass):
    def __init__(self) -> None:
        super().__init__("models")


class MockRoutesClass(MockAdapterClass):
    def __init__(self) -> None:
        super().__init__("routes")


class MockCacheClass(MockAdapterClass):
    def __init__(self) -> None:
        super().__init__("cache")


class MockStorageClass(MockAdapterClass):
    def __init__(self) -> None:
        super().__init__("storage")


class MockSitemapClass(MockAdapterClass):
    def __init__(self) -> None:
        super().__init__("sitemap")


class MockAdapterBase:
    def __init__(self) -> None:
        self.initialized: bool = False

    async def init(self) -> None:
        self.initialized = True


class MockModels(MockAdapterBase):
    pass


class MockTemplateRenderer(TemplateRenderer):
    async def render_template(
        self, request: Request, template: str, context: TemplateContext | None = None
    ) -> TemplateResponse:
        return Response("Mock template response")


class MockTemplates(MockAdapterBase):
    def __init__(self) -> None:
        super().__init__()
        self.app = MockTemplateRenderer()


class MockCache(MockAdapterBase):
    def __init__(self) -> None:
        super().__init__()
        self._storage: dict[str, Any] = {}

    async def get(self, key: str) -> Any:
        return self._storage.get(key)

    async def set(self, key: str, value: Any, **kwargs: Any) -> None:
        self._storage[key] = value

    async def delete(self, key: str) -> None:
        self._storage.pop(key, None)


class MockSitemap(MockAdapterBase):
    def __init__(self) -> None:
        super().__init__()
        self.urls: list[str] = []

    async def init(self) -> None:
        await super().init()
        self.config = depends.get(Config)

    def add_url(self, url: str, priority: float = 0.5) -> None:
        self.urls.append(url)

    async def write(self, path: Path | None = None) -> None:
        pass


class MockStorage(MockAdapterBase):
    def __init__(self) -> None:
        super().__init__()
        self.templates = MockStorageTemplates()
        self.static = MockStorageStatic()
        self.media = MockStorageMedia()


class MockStorageTemplates:
    async def exists(self, path: str) -> bool:
        return True

    async def open(self, path: str) -> bytes:
        return b"test"

    async def stat(self, path: str) -> dict[str, int]:
        return {"mtime": 1, "size": 1}


class MockStorageStatic:
    async def exists(self, path: str) -> bool:
        return True

    async def open(self, path: str) -> bytes:
        return b"test"

    async def stat(self, path: str) -> dict[str, int]:
        return {"mtime": 1, "size": 1}


class MockStorageMedia:
    async def exists(self, path: str) -> bool:
        return True

    async def open(self, path: str) -> bytes:
        return b"test"

    async def stat(self, path: str) -> dict[str, int]:
        return {"mtime": 1, "size": 1}


class MockRoutes(MockAdapterBase):
    def __init__(self) -> None:
        super().__init__()
        self.routes: list[Route] = []
        self.middleware = []

    async def gather_routes(self, path: Path) -> None:
        pass

    def get_routes(self) -> list[Route]:
        return self.routes

    def get_static_routes(self) -> list[Mount]:
        return [Mount("/static", app=StaticFiles(directory="static"), name="static")]


#
#


@pytest.hookimpl(trylast=True)
def pytest_configure(config: pytest.Config) -> None:
    import acb.config

    _original_methods["Config.__init__"] = Config.__init__
    _original_methods["AsyncPath.mkdir"] = AsyncPath.mkdir
    _original_methods["Path.mkdir"] = Path.mkdir
    _original_methods["AsyncPath.exists"] = AsyncPath.exists
    _original_methods["Path.exists"] = Path.exists
    _original_methods["tempfile.gettempdir"] = tempfile.gettempdir
    if "open" in globals():
        _original_methods["open"] = globals()["open"]
    _original_methods["acb.config.Config.__init__"] = acb.config.Config.__init__

    test_dir = Path(__file__).parent

    mock_tmp_dir = Path(test_dir / "mock_tmp")
    mock_tmp_dir.mkdir(parents=True, exist_ok=True)

    mock_pytest_dir = Path(test_dir / "mock_tmp" / "pytest-of-les")
    mock_pytest_dir.mkdir(parents=True, exist_ok=True)

    tempfile.gettempdir = lambda: str(test_dir / "mock_tmp")
    globals()["open"] = mock.mock_open(read_data="test content")

    adapter_classes = {
        "templates": MockTemplatesClass,
        "models": MockModelsClass,
        "routes": MockRoutesClass,
        "cache": MockCacheClass,
        "storage": MockStorageClass,
        "sitemap": MockSitemapClass,
    }

    def patched_import_adapter(category: str | None = None) -> Any:
        if category is None:

            class UnpackableAdapters:
                def __iter__(self) -> Iterator[Any]:
                    return iter(
                        [MockCacheClass(), MockStorageClass(), MockModelsClass()]
                    )

                def __getattr__(self, name: str):
                    if name in adapter_classes:
                        return adapter_classes[name]()
                    return None

            return UnpackableAdapters()

        if category in adapter_classes:
            return adapter_classes[category]

        return None

    acb.adapters.import_adapter = patched_import_adapter

    def patched_acb_config_init(self: Any, *args: Any, **kwargs: Any) -> None:
        with (
            mock.patch.multiple(
                AsyncPath,
                mkdir=mock.AsyncMock(return_value=None),
                exists=mock.AsyncMock(return_value=True),
            ),
            mock.patch.multiple(
                Path,
                mkdir=mock.MagicMock(return_value=None),
                exists=mock.MagicMock(return_value=True),
            ),
        ):
            _original_methods["acb.config.Config.__init__"](self, *args, **kwargs)

        self.root_path = AsyncPath(test_dir)
        self.settings_path = AsyncPath(test_dir / "mock_settings")
        self.secrets_path = AsyncPath(test_dir / "mock_secrets")
        self.tmp_path = AsyncPath(test_dir / "mock_tmp")

    acb.config.Config.__init__ = patched_acb_config_init


@pytest.hookimpl(trylast=True)
def pytest_unconfigure(config: pytest.Config) -> None:
    Config.__init__ = _original_methods["Config.__init__"]
    AsyncPath.mkdir = _original_methods["AsyncPath.mkdir"]
    Path.mkdir = _original_methods["Path.mkdir"]
    AsyncPath.exists = _original_methods["AsyncPath.exists"]
    Path.exists = _original_methods["Path.exists"]
    tempfile.gettempdir = _original_methods["tempfile.gettempdir"]
    if "open" in _original_methods:
        globals()["open"] = _original_methods["open"]

    import acb.adapters
    from acb.adapters import import_adapter as original_import_adapter

    acb.adapters.import_adapter = original_import_adapter


#
#


@pytest.fixture(autouse=True)
async def mock_settings(config: Config) -> AsyncGenerator[None, None]:
    yield


@pytest.fixture
def config() -> Generator[Config, None, None]:
    config = Config()
    config.deployed = False

    config.logger = type(
        "LoggerConfig",
        (object,),
        {"log_level": "INFO", "format": "simple", "level_per_module": {}},
    )()

    yield config


@pytest.fixture
def models() -> Generator[MockModels, None, None]:
    yield depends.get(MockModels)


@pytest.fixture
def templates() -> Generator[MockTemplates, None, None]:
    yield depends.get(MockTemplates)


@pytest.fixture
def sitemap() -> Generator[MockSitemap, None, None]:
    yield depends.get(MockSitemap)


@pytest.fixture
def cache() -> Generator[MockCache, None, None]:
    yield depends.get(MockCache)


@pytest.fixture
def mock_storage() -> Generator[MockStorage, None, None]:
    yield depends.get(MockStorage)


@pytest.fixture
def routes() -> Generator[MockRoutes, None, None]:
    yield depends.get(MockRoutes)


@pytest.fixture
def http_request() -> Request:
    scope = {"type": "http", "method": "GET", "path": "/"}
    return Request(scope)


@pytest.fixture
def mock_tmp(monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        monkeypatch.setattr(tempfile, "gettempdir", lambda: str(tmp_path))
        yield tmp_path


#
#


@pytest.fixture
def adapter_config(tmp_path: Path) -> Config:
    config = Config()

    class StorageConfig:
        def __init__(self) -> None:
            self.local_fs = True
            self.local_path = tmp_path

    config.storage = StorageConfig()
    return config


@pytest.fixture
def adapter_models() -> MockModels:
    return MockModels()


@pytest.fixture
def adapter_templates() -> MockTemplates:
    return MockTemplates()


@pytest.fixture
def adapter_sitemap(adapter_config: Config) -> MockSitemap:
    sitemap = MockSitemap()
    sitemap.config = adapter_config
    return sitemap


@pytest.fixture
def adapter_cache() -> MockCache:
    return MockCache()


@pytest.fixture
def adapter_storage() -> MockStorage:
    return MockStorage()


@pytest.fixture
def adapter_routes() -> MockRoutes:
    return MockRoutes()
