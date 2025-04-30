"""Consolidated test fixtures for all tests."""

import tempfile
import typing as t
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, Generator, Iterator, List, Optional, Union
from unittest import mock

import pytest
from acb.config import AdapterBase, Config
from acb.depends import depends
from anyio import Path as AsyncPath
from starlette.requests import Request
from starlette.responses import HTMLResponse, PlainTextResponse, Response
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

_original_methods = {}

#
#


class MockAdapter:
    def __init__(
        self, /, name: str = "mock", category: str = "test", **data: Any
    ) -> None:
        self.name = name
        self.category = category or name
        self.class_name = data.get("class_name", "MockAdapter")
        self.path = data.get("path", Path(__file__).parent.parent)
        self.enabled = True
        self.installed = True
        self.pkg = "test"


class MockTemplatesAdapter(MockAdapter):
    def __init__(self) -> None:
        super().__init__(
            name="templates", category="templates", class_name="MockTemplates"
        )


class MockModelsAdapter(MockAdapter):
    def __init__(self) -> None:
        super().__init__(name="models", category="models", class_name="MockModels")


class MockRoutesAdapter(MockAdapter):
    def __init__(self) -> None:
        super().__init__(name="routes", category="routes", class_name="MockRoutes")


class MockSitemapAdapter(MockAdapter):
    def __init__(self) -> None:
        super().__init__(name="sitemap", category="sitemap", class_name="MockSitemap")


class MockCacheAdapter(MockAdapter):
    def __init__(self) -> None:
        super().__init__(name="cache", category="cache", class_name="MockCache")


class MockStorageAdapter(MockAdapter):
    def __init__(self) -> None:
        super().__init__(name="storage", category="storage", class_name="MockStorage")


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


class MockTemplateRenderer:
    def __init__(self) -> None:
        self._mock_responses = {}

    def set_response(self, template: str, response: Response) -> None:
        self._mock_responses[template] = response

    async def render_template(
        self,
        request: Request,
        template: str,
        context: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Response:
        if template in self._mock_responses:
            return self._mock_responses[template]

        context = context or {}
        headers = headers or {}
        content = f"<html><body>{template}: {', '.join(context.keys())}</body></html>"
        if "home" in template:
            content = "<html><body>home</body></html>"
        elif "about" in template:
            content = "<html><body>about</body></html>"
        elif "cached.html" in template:
            content = "<html><body>Cached content</body></html>"
            if (
                hasattr(request, "app")
                and hasattr(request.app, "state")
                and hasattr(request.app.state, "cache")
            ):
                await request.app.state.cache.set(
                    f"template:{template}", content.encode()
                )
        return HTMLResponse(content, headers=headers)

    async def render_template_block(
        self,
        request: Request,
        template: str,
        block: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Response:
        context = context or {}
        content = f"<div>{template}: {block or 'default'}</div>"
        return HTMLResponse(content)


class MockAdapterBase:
    def __init__(self) -> None:
        self.initialized: bool = False

    async def init(self) -> None:
        self.initialized = True


class MockModels(AdapterBase):
    def __init__(self) -> None:
        self.initialized: bool = False

    async def init(self) -> None:
        self.initialized = True


class MockTemplates(AdapterBase):
    def __init__(self) -> None:
        self.app: MockTemplateRenderer = MockTemplateRenderer()
        self.admin: MockTemplateRenderer = MockTemplateRenderer()
        self.initialized: bool = False
        self.filters = {
            "truncate": lambda text, length: text[: length - 3] + "..."
            if len(text) > length
            else text,
            "filesize": lambda size: f"{size / 1024:.1f} KB"
            if size < 1024 * 1024
            else f"{size / (1024 * 1024):.1f} MB"
            if size < 1024 * 1024 * 1024
            else f"{size / (1024 * 1024 * 1024):.1f} GB",
        }
        self.config: Optional[Config] = None  # type: ignore

    def get_searchpath(self, adapter: Any, path: Any) -> list[Any]:
        style = "test_style"
        if hasattr(self, "config") and self.config and hasattr(self.config, "app"):
            style = getattr(self.config.app, "style", style)

        base_path = path / "base"
        style_path = path / style
        style_adapter_path = path / style / adapter.name
        theme_adapter_path = style_adapter_path / "theme"
        return [
            theme_adapter_path,
            style_adapter_path,
            style_path,
            base_path,
        ]

    async def get_searchpaths(self, adapter: Any) -> list[Any]:
        from anyio import Path as AsyncPath

        path = AsyncPath(adapter.path / "templates" / adapter.category)
        searchpaths = self.get_searchpath(adapter, path)

        if hasattr(adapter, "path") and hasattr(adapter.path, "parent"):
            templates_path = adapter.path.parent / "_templates"
            if templates_path not in searchpaths:
                searchpaths.append(templates_path)

        return searchpaths

    @staticmethod
    def get_storage_path(path: Any) -> Any:
        templates_path_name = "templates"
        if templates_path_name not in path.parts:
            templates_path_name = "_templates"

        try:
            depth = path.parts.index(templates_path_name)
            return type(path)("/".join(path.parts[depth:]))
        except ValueError:
            return path

    @staticmethod
    def get_cache_key(path: Any) -> str:
        return ":".join(path.parts)

    async def init(self) -> None:
        self.initialized = True


class MockSitemap(AdapterBase):
    def __init__(self) -> None:
        class SitemapObj:
            def __init__(self) -> None:
                self.change_freq = "hourly"
                self.urls = []

        self.sitemap = SitemapObj()
        self.initialized: bool = False
        self.urls: list[str] = []

        from acb.config import Config as AcbConfig

        class MockConfig(AcbConfig):
            pass

        self.config = MockConfig()  # type: ignore

    async def init(self) -> None:
        self.initialized = True
        self.config = depends.get(Config)

    async def generate(self) -> str:
        xml = "<?xml version='1.0' encoding='UTF-8'?>"
        xml += "<urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>"

        for url in self.sitemap.urls:
            xml += f"<url><loc>{url.loc}</loc>"
            if hasattr(url, "lastmod") and url.lastmod:
                xml += f"<lastmod>{url.lastmod.isoformat()}</lastmod>"
            change_freq = (
                url.change_freq
                if hasattr(url, "change_freq") and url.change_freq
                else "hourly"
            )
            xml += f"<changefreq>{change_freq}</changefreq>"
            if hasattr(url, "priority") and url.priority is not None:
                xml += f"<priority>{url.priority}</priority>"
            xml += "</url>"

        xml += "</urlset>"
        return xml

    async def add_url(
        self,
        url: str,
        priority: float = 0.5,
        change_freq: Optional[str] = None,
        lastmod: Optional[Any] = None,
    ) -> None:
        if not url.startswith(("http", "/")):
            raise ValueError(f"Invalid URL: {url}")
        if " " in url:
            raise ValueError(f"URL cannot contain spaces: {url}")
        if url.startswith("ftp"):
            raise ValueError(f"Unsupported protocol: {url}")

        if not isinstance(priority, float):
            raise ValueError(
                f"Invalid priority: {priority}. Must be a number between 0 and 1"
            )
        if priority < 0 or priority > 1:
            raise ValueError(
                f"Invalid priority: {priority}. Must be a number between 0 and 1"
            )

        valid_freqs = [
            "always",
            "hourly",
            "daily",
            "weekly",
            "monthly",
            "yearly",
            "never",
        ]
        if change_freq and change_freq not in valid_freqs:
            raise ValueError(
                f"Invalid change frequency: {change_freq}. Must be one of {valid_freqs}"
            )

        url_obj = type(
            "obj",
            (object,),
            {
                "loc": url,
                "priority": priority,
                "change_freq": change_freq,
                "lastmod": lastmod,
            },
        )
        self.sitemap.urls.append(url_obj)
        self.urls.append(url)

    async def write(self, path: Optional[Path] = None) -> None:
        content = await self.generate()
        if path is None:
            if hasattr(self.config, "storage") and hasattr(
                self.config.storage, "local_fs"
            ):
                if not self.config.storage.local_fs:
                    raise ValueError("Local filesystem storage is not enabled")
                path = self.config.storage.local_path / "sitemap.xml"
            else:
                path = Path(tempfile.gettempdir()) / "sitemap.xml"

        assert path is not None
        path.write_text(content)


class MockRoutes(AdapterBase):
    def __init__(self) -> None:
        self.routes = []
        self.initialized: bool = False
        self.middleware = []

    async def init(self) -> None:
        self.initialized = True

    async def gather_routes(
        self, path: Optional[Path] = None
    ) -> List[Union[Route, Mount]]:
        routes = [
            Route("/", self.index, methods=["GET"]),
            Route("/about", self.about, methods=["GET"]),
            Route("/contact", self.contact, methods=["GET"]),
            Route("/favicon.ico", self.favicon, methods=["GET"]),
            Route("/robots.txt", self.robots, methods=["GET"]),
            Mount("/static", StaticFiles(directory="static"), name="static"),  # type: ignore
        ]
        self.routes = routes
        return routes

    async def index(self, request: Request) -> Response:
        if request.scope.get("htmx", {}).get("request", False):
            return HTMLResponse("<div>HTMX Content</div>")
        return HTMLResponse("<html><body>Home Page</body></html>")

    async def about(self, request: Request) -> Response:
        return HTMLResponse("<html><body>About Page</body></html>")

    async def contact(self, request: Request) -> Response:
        return HTMLResponse("<html><body>Contact Page</body></html>")

    async def favicon(self, request: Request) -> Response:
        return PlainTextResponse("favicon")

    async def robots(self, request: Request) -> Response:
        return PlainTextResponse("User-agent: *\nDisallow: /admin/")

    def get_routes(self) -> list[Route | Mount]:
        return self.routes

    def get_static_routes(self) -> list[Mount]:
        return [Mount("/static", app=StaticFiles(directory="static"), name="static")]


class MockCache(AdapterBase):
    def __init__(self) -> None:
        self._storage: dict[str, Any] = {}
        self.initialized: bool = False

    async def get(self, key: str, default: Any = None) -> Any:
        return self._storage.get(key, default)

    async def set(
        self, key: str, value: Any, ttl: Optional[int] = None, **kwargs: Any
    ) -> None:
        self._storage[key] = value

    async def exists(self, key: str) -> bool:
        return key in self._storage

    async def delete(self, key: str) -> None:
        self._storage.pop(key, None)

    async def init(self) -> None:
        self.initialized = True


class MockStorage(AdapterBase):
    def __init__(self) -> None:
        self.initialized: bool = False
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


@pytest.fixture(autouse=True)
def patch_import_adapter():
    with mock.patch("acb.adapters.import_adapter") as mock_import_adapter:

        def mock_adapter_func(category: Optional[str] = None) -> Any:
            if category == "templates" or category is None:
                return MockTemplates()
            elif category == "models":
                return MockModels()
            elif category == "routes":
                return MockRoutes()
            elif category == "sitemap":
                return MockSitemap()
            elif category == "cache":
                return MockCache()
            elif category == "storage":
                return MockStorage()
            return None

        mock_import_adapter.side_effect = mock_adapter_func
        yield


@pytest.fixture(autouse=True)
async def mock_settings(config: Config) -> AsyncGenerator[None, None]:
    yield


@pytest.fixture
def config() -> Generator[Config, None, None]:
    config = Config()
    config.deployed = False

    class StorageConfig:
        def __init__(self) -> None:
            self.local_fs = True
            self.local_path = Path(tempfile.gettempdir())

    config.__dict__["storage"] = StorageConfig()

    class AppConfig:
        def __init__(self) -> None:
            self.style = "test_style"

    config.__dict__["app"] = AppConfig()

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
def routes() -> Generator[MockRoutes, None, None]:
    yield depends.get(MockRoutes)


@pytest.fixture
def cache() -> Generator[MockCache, None, None]:
    yield depends.get(MockCache)


@pytest.fixture
def mock_storage() -> Generator[MockStorage, None, None]:
    yield depends.get(MockStorage)


@pytest.fixture
def http_request() -> Request:
    scope = {"type": "http", "method": "GET", "path": "/"}
    return Request(scope)


@pytest.fixture
def mock_adapter() -> t.Type[MockAdapter]:
    return MockAdapter


@pytest.fixture
def mock_tmp(monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        monkeypatch.setattr(tempfile, "gettempdir", lambda: str(tmp_path))
        yield tmp_path


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
