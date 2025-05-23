import os
import sys
from contextlib import suppress
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from starlette.requests import Request
from starlette.responses import HTMLResponse, Response
from starlette.types import Message, Scope


class MockAsyncPath:
    def __init__(self, path: Union[str, Path, "MockAsyncPath"] = "") -> None:
        if isinstance(path, MockAsyncPath):
            self._path = path._path
        else:
            self._path = str(path)

    def __str__(self) -> str:
        return self._path

    def __repr__(self) -> str:
        return f"MockAsyncPath('{self._path}')"

    def __fspath__(self) -> str:
        return self._path

    def __truediv__(self, other: Union[str, Path, "MockAsyncPath"]) -> "MockAsyncPath":
        other_str = str(other)
        if self._path.endswith("/"):
            return MockAsyncPath(f"{self._path}{other_str}")
        return MockAsyncPath(f"{self._path}/{other_str}")

    @property
    def parent(self) -> "MockAsyncPath":
        parent_path = "/".join(self._path.split("/")[:-1])
        if not parent_path:
            parent_path = "/"
        return MockAsyncPath(parent_path)

    @property
    def name(self) -> str:
        return self._path.split("/")[-1]

    @property
    def parts(self) -> Tuple[str, ...]:
        parts = [part for part in self._path.split("/") if part]
        if self._path.startswith("/"):
            return ("/",) + tuple(parts)
        return tuple(parts)

    async def exists(self) -> bool:
        return True

    async def is_file(self) -> bool:
        return "." in self._path.split("/")[-1]

    async def is_dir(self) -> bool:
        return not await self.is_file()

    def with_suffix(self, suffix: str) -> "MockAsyncPath":
        if "." in self._path:
            base = self._path.rsplit(".", 1)[0]
        else:
            base = self._path
        return MockAsyncPath(f"{base}{suffix}")

    async def glob(self, pattern: str) -> List["MockAsyncPath"]:
        return []


class MockAdapter:
    def __init__(
        self, name: str = "test", category: str = "app", path: Any = None
    ) -> None:
        self.name = name
        self.category = category
        self.path = path
        self.style = "test_style"

    def __repr__(self) -> str:
        return f"MockAdapter(name={self.name})"


class MockConfig:
    def __init__(self) -> None:
        self.app = Mock()
        self.app.name = "test_app"
        self.app.debug = True

        self.templates = Mock()
        self.templates.directory = "templates"
        self.templates.extension = ".html"

        self.cache = Mock()
        self.cache.enabled = True
        self.cache.ttl = 3600

        self.storage = Mock()
        self.storage.local_path = "storage"
        self.storage.local_fs = True

        self.sitemap = Mock()
        self.sitemap.change_freq = "hourly"
        self.sitemap.priority = 0.5

        self.package_name: Optional[str] = None

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def __setitem__(self, key: str, value: Any) -> None:
        setattr(self, key, value)

    def __call__(self, key: Optional[str] = None) -> Any:
        if key is None:
            return self
        return self[key]

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def set(self, key: str, value: Any) -> None:
        setattr(self, key, value)


class MockTemplateFilters:
    @staticmethod
    def truncate(text: str, length: int) -> str:
        return text[: length - 3] + "..." if len(text) > length else text

    @staticmethod
    def filesize(size: int) -> str:
        if size < 1024:
            return f"{size / 1024:.1f} KB"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB"
        return f"{size / (1024 * 1024 * 1024):.1f} GB"


class MockTemplateRenderer:
    def __init__(
        self,
        storage: Optional["MockStorage"] = None,
        cache: Optional["MockCache"] = None,
    ) -> None:
        self.templates: Dict[str, str] = {
            "page.html": "<html><body>page.html: title, content, items</body></html>",
            "custom.html": "<html><body>Custom template response</body></html>",
            "cached.html": "<html><body>Cached content</body></html>",
            "test.html": "<html><body>test.html: {{ title }}, {{ content }}</body></html>",
        }
        self.storage = storage
        self.cache = cache
        self._mock_responses: Dict[str, Response] = {}

    def add_template(self, name: str, content: str) -> None:
        self.templates[name] = content

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

        if context is None:
            context = {}

        if headers is None:
            headers = {}

        if template not in self.templates:
            raise MockTemplateNotFound(template)

        if template == "page.html" and "title" in context:
            return HTMLResponse(
                content="<html><body>page.html: title, content, items</body></html>",
                headers=headers,
            )

        if template == "test.html":
            content = "<html><body>test.html: title, content, items</body></html>"
            return HTMLResponse(content=content, headers=headers)

        content = self.templates[template]

        for key, value in context.items():
            if isinstance(value, str):
                content = content.replace("{{ " + key + " }}", value)

        return HTMLResponse(content=content, headers=headers)

    async def render_template_block(
        self,
        request: Request,
        template: str,
        block: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        if context is None:
            context = {}

        if template not in self.templates:
            raise MockTemplateNotFound(template)

        return f"Block {block} from {template}"


class MockTemplates:
    def __init__(
        self,
        config: Optional["MockConfig"] = None,
        storage: Any = None,
        cache: Any = None,
    ) -> None:
        self.storage = storage
        self.cache = cache
        self.config = config or MockConfig()

        if not hasattr(self.config, "app"):
            setattr(self.config, "app", SimpleNamespace(style="test_style"))
        elif not hasattr(self.config.app, "style"):
            self.config.app.style = "test_style"

        self.app = MockTemplateRenderer(storage, cache)
        self.admin = MockTemplateRenderer(storage, cache)

        self.app_searchpaths = None
        self.admin_searchpaths = None

        self.filters = {
            "truncate": MockTemplateFilters.truncate,
            "filesize": MockTemplateFilters.filesize,
        }

    def get_searchpath(self, adapter: Any, path: Any) -> list[Any]:
        style = self.config.app.style
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
        from unittest.mock import patch

        with patch("fastblocks.adapters.templates._base.root_path", adapter.path):
            return self.get_searchpath(
                adapter, adapter.path / "templates" / adapter.category
            )

    def get_storage_path(self, path: Union[str, Path]) -> str:
        return f"templates/{path}"

    def get_cache_key(self, path: Union[str, Path]) -> str:
        return f"template:{path}"


class MockStorage:
    def __init__(self) -> None:
        self._storage: Dict[str, Any] = {}

    def __getitem__(self, key: str) -> Any:
        return self._storage[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self._storage[key] = value

    def __delitem__(self, key: str) -> None:
        del self._storage[key]

    def __contains__(self, key: str) -> bool:
        return key in self._storage

    def get(self, key: str, default: Any = None) -> Any:
        return self._storage.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._storage[key] = value

    def delete(self, key: str) -> None:
        if key in self._storage:
            del self._storage[key]

    def exists(self, key: str) -> bool:
        return key in self._storage

    def clear(self) -> None:
        self._storage.clear()


class MockCache:
    def __init__(self) -> None:
        self._cache: Dict[str, Any] = {}

    def get(self, key: str, default: Any = None) -> Any:
        return self._cache.get(key, default)

    def set(self, key: str, value: Any, expire: int = 0) -> None:
        self._cache[key] = value

    def delete(self, key: str) -> None:
        if key in self._cache:
            del self._cache[key]

    def exists(self, key: str) -> bool:
        return key in self._cache

    def clear(self) -> None:
        self._cache.clear()


class MockAdapters:
    def __init__(self) -> None:
        self.root_path = MockAsyncPath("/mock/root/path")
        self.Adapter = MagicMock()
        self.pkg_registry = {}
        self._adapters = self._create_adapter_objects()

    def _create_adapter_objects(self) -> Dict[str, MockAdapter]:
        adapters = {}

        for name in ("cache", "storage", "templates", "routes"):
            adapter = MockAdapter(name)
            adapter.path = MockAsyncPath(f"/mock/adapters/{name}")
            adapters[name] = adapter

        return adapters

    def import_adapter(self, adapter_name: str = "cache") -> Tuple[Any, Any, Any]:
        mock_cache = MockCache()
        mock_storage = MockStorage()
        mock_models = MockModels()
        mock_templates = MockTemplates(MockConfig(), mock_storage, mock_cache)

        if adapter_name == "cache":
            return (mock_cache, mock_storage, mock_models)
        elif adapter_name == "storage":
            return (mock_storage, mock_models, None)
        elif adapter_name == "templates":
            return (mock_templates, None, None)
        elif adapter_name == "routes":
            mock_routes = MagicMock()
            return (mock_routes, None, None)
        return (MagicMock(), MagicMock(), MagicMock())

    def get_adapters(self) -> List[Any]:
        return list(self._adapters.values())

    def get_installed_adapter(self, adapter_name: str) -> Any:
        return self._adapters.get(adapter_name, MagicMock())

    def get_adapter(self, adapter_name: str) -> Any:
        if adapter_name == "cache":
            return MockCache()
        elif adapter_name == "storage":
            return MockStorage()
        elif adapter_name == "templates":
            return MockTemplates(MockConfig(), MockStorage(), MockCache())
        elif adapter_name == "routes":
            return MagicMock()
        return MagicMock()


class MockConfigModule:
    def __init__(self) -> None:
        self._config = MockConfig()
        self.AsyncPath = MockAsyncPath
        self.Config = self._config
        self.Adapter = MagicMock()
        self.pkg_registry = {}

    class AdapterBase:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.name = "mock_adapter"
            self.settings = {}

    class Settings:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.settings = {}
            self.app = SimpleNamespace()
            self.adapters = SimpleNamespace()
            self.debug = SimpleNamespace()

        def load(self) -> None:
            pass

        def __getattr__(self, name: str) -> Any:
            return self.settings.get(name, None)

        def __setattr__(self, name: str, value: Any) -> None:
            if name in ("settings", "app", "adapters", "debug"):
                super().__setattr__(name, value)
            else:
                self.settings[name] = value


class MockActions:
    def __init__(self) -> None:
        self.hash = self._create_hash_module()

    def _create_hash_module(self) -> Any:
        class HashModule:
            def __init__(self) -> None:
                pass

            def hash(self, content: Any) -> str:
                if isinstance(content, str):
                    return f"hash_{len(content)}"
                elif isinstance(content, bytes):
                    return f"hash_{len(content)}"
                return "hash_mock"

        return HashModule()


class MockDepends:
    def __init__(self) -> None:
        self.dependencies: Dict[str, Any] = {}

        def depends_func(*args: Any, **kwargs: Any) -> Any:
            def decorator(func: Any) -> Any:
                return func

            return decorator

        def inject_func(func: Any) -> Any:
            return func

        def set_func(cls: Any) -> Any:
            self.dependencies[cls.__name__] = cls
            return cls

        def get_func(name: str) -> Any:
            return self.dependencies.get(name, MagicMock())

        self.depends = depends_func
        setattr(self.depends, "inject", inject_func)
        setattr(self.depends, "set", set_func)
        setattr(self.depends, "get", get_func)


class MockDependsInjector:
    @staticmethod
    def inject(f: Any) -> Any:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if (
                "config" not in kwargs
                and len(args) > 1
                and isinstance(args[1], MockConfig)
            ):
                kwargs["config"] = args[1]
            return f(*args, **kwargs)

        return wrapper


class MockTemplatesBaseSettings:
    def __init__(self, cache_timeout: int = 300) -> None:
        self.cache_timeout = cache_timeout

    def update_from_config(self, config: Any) -> None:
        self.cache_timeout = 300 if config.deployed else 1


class MockDebug:
    def __init__(self) -> None:
        self.enabled = True

    def debug(self, *args: Any, **kwargs: Any) -> None:
        pass

    def trace(self, *args: Any, **kwargs: Any) -> None:
        pass

    def error(self, *args: Any, **kwargs: Any) -> None:
        pass


class MockLogger:
    def __init__(self) -> None:
        self.InterceptHandler = MagicMock()
        self.Logger = self._create_logger_class()

    def _create_logger_class(self) -> Any:
        class LoggerClass:
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                self.name = kwargs.get("name", "mock_logger")

            def bind(self, **kwargs: Any) -> "LoggerClass":
                return self

            def debug(self, message: str, *args: Any, **kwargs: Any) -> None:
                pass

            def info(self, message: str, *args: Any, **kwargs: Any) -> None:
                pass

            def warning(self, message: str, *args: Any, **kwargs: Any) -> None:
                pass

            def error(self, message: str, *args: Any, **kwargs: Any) -> None:
                pass

            def exception(self, message: str, *args: Any, **kwargs: Any) -> None:
                pass

        return LoggerClass


class MockSitemap:
    def __init__(self) -> None:
        class InnerSitemap:
            def __init__(self) -> None:
                self.urls = []
                self.change_freq = "hourly"
                self.priority = 0.5

        self.sitemap = InnerSitemap()
        self.config: Any = None

    async def init(self) -> None:
        pass

    async def add_url(self, url: str, **kwargs: Any) -> None:
        if not url.startswith(("/", "http")):
            raise ValueError(f"Invalid URL format: {url}")

        if " " in url:
            raise ValueError(f"URL contains invalid characters: {url}")

        if url.startswith("ftp:"):
            raise ValueError(f"Unsupported URL protocol: {url}")

        change_freq = kwargs.get("change_freq", "hourly")

        valid_freqs = (
            "always",
            "hourly",
            "daily",
            "weekly",
            "monthly",
            "yearly",
            "never",
        )
        if change_freq not in valid_freqs:
            raise ValueError(f"Invalid change frequency: {change_freq}")

        priority = kwargs.get("priority", 0.5)

        if not isinstance(priority, (int, float)) or priority < 0.0 or priority > 1.0:
            raise ValueError(
                f"Invalid priority value: {priority}. Must be between 0.0 and 1.0"
            )

        last_modified = kwargs.get("last_modified", datetime.now())

        url_obj = SitemapURL(
            loc=url,
            change_freq=change_freq,
            priority=priority,
            last_modified=last_modified,
        )
        self.sitemap.urls.append(url_obj)

    async def generate(self) -> str:
        xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
        xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'

        for url in self.sitemap.urls:
            xml += "  <url>\n"
            xml += f"    <loc>{url.loc}</loc>\n"
            if hasattr(url, "last_modified"):
                xml += (
                    f"    <lastmod>{url.last_modified.strftime('%Y-%m-%d')}</lastmod>\n"
                )
            if hasattr(url, "change_freq"):
                xml += f"    <changefreq>{url.change_freq}</changefreq>\n"
            if hasattr(url, "priority"):
                xml += f"    <priority>{url.priority}</priority>\n"
            xml += "  </url>\n"

        xml += "</urlset>"
        return xml

    async def write(self, path: Any = None) -> None:
        xml = await self.generate()

        if path is None:
            if hasattr(self.config, "storage") and hasattr(
                self.config.storage, "local_path"
            ):
                path = Path(self.config.storage.local_path) / "sitemap.xml"
            else:
                raise ValueError(
                    "No path provided and no default path available in config"
                )

        if hasattr(path, "_path"):
            path = Path(path._path)

        Path(path).parent.mkdir(exist_ok=True, parents=True)

        Path(path).write_text(xml)


class MockModels:
    def __init__(self) -> None:
        self.models: Dict[str, Any] = {}

    def get_model(self, model_name: str) -> Any:
        return self.models.get(model_name)

    def register_model(self, model_name: str, model: Any) -> None:
        self.models[model_name] = model


class MockUptodate:
    def __init__(self) -> None:
        self.updates: Dict[str, bool] = {}

    def check(self, package: str) -> bool:
        return self.updates.get(package, True)

    def set_update(self, package: str, is_up_to_date: bool) -> None:
        self.updates[package] = is_up_to_date


@pytest.fixture
def mock_cache() -> AsyncMock:
    mock = AsyncMock()

    mock.exists = AsyncMock(return_value=False)
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=True)
    mock.clear = AsyncMock(return_value=True)

    return mock


@pytest.fixture
def mock_storage() -> AsyncMock:
    mock = AsyncMock()

    mock.exists = AsyncMock(return_value=False)
    mock.open = AsyncMock(return_value=None)
    mock.write = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=True)
    mock.file_exists = AsyncMock(return_value=False)
    mock.directory_exists = AsyncMock(return_value=False)
    mock.create_directory = AsyncMock(return_value=True)

    mock.templates = AsyncMock()
    mock.templates.exists = AsyncMock(return_value=False)
    mock.templates.open = AsyncMock(return_value=None)
    mock.templates.stat = AsyncMock(return_value={"mtime": 123456789, "size": 1024})

    return mock


@pytest.fixture
def mock_models() -> MockModels:
    return MockModels()


@pytest.fixture
def mock_uptodate() -> MockUptodate:
    return MockUptodate()


@pytest.fixture
def config() -> MockConfig:
    return MockConfig()


@pytest.fixture
def mock_path() -> MockAsyncPath:
    return MockAsyncPath()


@pytest.fixture
def mock_import_adapter(monkeypatch: pytest.MonkeyPatch) -> None:
    def mock_import(*args: Any, **kwargs: Any) -> Any:
        adapter_name = args[0] if args else kwargs.get("adapter_name", "")

        if adapter_name == "cache":
            return (MockCache(), None, None)
        elif adapter_name == "storage":
            return (MockStorage(), None, None)
        elif adapter_name == "models":
            return (MockModels(), None, None)
        elif adapter_name == "templates":
            mock_templates = MockTemplates(MockConfig(), MockStorage(), MockCache())
            return (mock_templates, None, None)
        elif adapter_name == "routes":
            mock_routes = MagicMock()
            return (mock_routes, None, None)

        return (MagicMock(), MagicMock(), MagicMock())

    monkeypatch.setattr("acb.adapters.import_adapter", mock_import)

    for module_name in list(sys.modules.keys()):
        if module_name.startswith("fastblocks.adapters"):
            module = sys.modules[module_name]
            if hasattr(module, "import_adapter"):
                monkeypatch.setattr(f"{module_name}.import_adapter", mock_import)


@pytest.fixture
def http_request() -> Request:
    scope: Scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "query_string": b"",
        "headers": [],
    }

    async def receive() -> Message:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: Message) -> None:
        pass

    return Request(scope=scope, receive=receive, send=send)


@pytest.fixture
def mock_jinja2_templates() -> Any:
    class MockJinja2Templates:
        def __init__(self) -> None:
            self.templates: Dict[str, str] = {}

        def get_template(self, template_name: str) -> Any:
            if template_name not in self.templates:
                raise Exception(f"Template not found: {template_name}")

            return template_name

    return MockJinja2Templates


@pytest.fixture
def templates(mock_cache: MockCache, mock_storage: MockStorage) -> MockTemplates:
    config = MockConfig()
    return MockTemplates(config, mock_storage, mock_cache)


@pytest.fixture
def jinja2_templates(templates: MockTemplates) -> Any:
    return templates


@pytest.fixture
def mock_templates(mock_cache: MockCache, mock_storage: MockStorage) -> MockTemplates:
    config = MockConfig()
    return MockTemplates(config, mock_storage, mock_cache)


@pytest.fixture
def mock_adapter() -> type:
    return MockAdapter


class SitemapURL:
    def __init__(
        self, loc: str, change_freq: str, priority: float, last_modified: datetime
    ) -> None:
        self.loc = loc
        self.change_freq = change_freq
        self.priority = priority
        self.last_modified = last_modified


@pytest.fixture(autouse=True)
def patch_template_loaders():
    with (
        patch(
            "fastblocks.adapters.templates.jinja2.FileSystemLoader",
            MockFileSystemLoader,
        ),
        patch("fastblocks.adapters.templates.jinja2.RedisLoader", MockRedisLoader),
        patch("fastblocks.adapters.templates.jinja2.ChoiceLoader", MockChoiceLoader),
        patch("fastblocks.adapters.templates.jinja2.StorageLoader", MockStorageLoader),
        patch("fastblocks.adapters.templates.jinja2.PackageLoader", MockPackageLoader),
    ):
        yield


def patch_acb_module():
    mock_acb = MagicMock()
    mock_acb.adapters = MockAdapters()
    mock_acb.config = MockConfigModule()
    mock_acb.depends = MockDepends()
    mock_acb.debug = MockDebug()
    mock_acb.logger = MockLogger()
    mock_acb.actions = MockActions()

    sys.modules["acb"] = mock_acb
    sys.modules["acb.adapters"] = mock_acb.adapters
    sys.modules["acb.config"] = mock_acb.config
    sys.modules["acb.depends"] = mock_acb.depends
    sys.modules["acb.debug"] = mock_acb.debug
    sys.modules["acb.logger"] = mock_acb.logger
    sys.modules["acb.actions"] = mock_acb.actions
    sys.modules["acb.actions.hash"] = mock_acb.actions.hash

    return mock_acb


mock_acb = patch_acb_module()


@pytest.fixture(autouse=True)
def patch_depends():
    with (
        patch(
            "fastblocks.adapters.templates._base.depends.inject",
            MockDependsInjector.inject,
        ),
        patch(
            "fastblocks.adapters.templates._base.TemplatesBaseSettings",
            MockTemplatesBaseSettings,
        ),
    ):
        yield


class MockTemplateNotFound(Exception):
    def __init__(self, name: str) -> None:
        self.name = name
        self.message = f"Template '{name}' not found"
        super().__init__(self.message)


class MockAsyncBaseLoader:
    def __init__(self, searchpath: Optional[Union[Path, List[Any]]] = None) -> None:
        if searchpath is None:
            self.searchpath = [MockAsyncPath("templates")]
        elif isinstance(searchpath, list):
            self.searchpath = searchpath
        else:
            self.searchpath = [searchpath]

        self.encoding = "utf-8"

    async def get_source_async(
        self, environment: Any = None, template: str = ""
    ) -> Tuple[str, str, Callable[[], bool]]:
        raise NotImplementedError()

    async def list_templates_async(self) -> List[str]:
        raise NotImplementedError()


class MockFileSystemLoader(MockAsyncBaseLoader):
    def __init__(
        self,
        searchpath: Optional[Union[Path, List[Any]]] = None,
        encoding: Optional[str] = None,
        cache: Any = None,
        storage: Any = None,
        config: Any = None,
    ) -> None:
        super().__init__(searchpath=searchpath)
        self.encoding = encoding or "utf-8"
        self.cache = cache
        self.storage = storage
        self.config = config

    def get_source(self, template: str = "") -> Tuple[str, str, Callable[[], bool]]:
        if not self.searchpath:
            raise MockTemplateNotFound(template)

        for i in range(len(self.searchpath)):
            path = self.searchpath[i]

            if isinstance(path, str):
                path = Path(path)

            template_path = path / template
            if Path(template_path).exists():
                content = Path(template_path).read_text(encoding=self.encoding)
                return content, str(template_path), lambda: True

        raise MockTemplateNotFound(template)

    async def get_source_async(
        self, environment: Any = None, template: str = ""
    ) -> Tuple[str, str, Callable[[], bool]]:
        if not self.searchpath:
            raise MockTemplateNotFound(template)

        if self.storage and hasattr(self.storage, "templates"):
            with suppress(Exception):
                if self.storage.templates.exists(f"templates/{template}"):
                    content_bytes = self.storage.templates.open(f"templates/{template}")

                    if isinstance(content_bytes, bytes):
                        content = content_bytes.decode(self.encoding)
                    else:
                        content = str(content_bytes)

                    if self.cache:
                        cache_key = f"template:{template}"
                        self.cache.set(cache_key, content)

                    return content, template, lambda: True

        for i in range(len(self.searchpath)):
            path = self.searchpath[i]

            if isinstance(path, str):
                path = Path(path)

            template_path = path / template
            if Path(template_path).exists():
                content = open(template_path).read()
                return content, str(template_path), lambda: True

        raise MockTemplateNotFound(template)

    async def list_templates_async(self) -> List[str]:
        templates = set()

        for i in range(len(self.searchpath)):
            path = self.searchpath[i]

            path_str = str(path)
            if not Path(path_str).exists():
                continue

            for root, _, files in os.walk(path_str):
                for filename in files:
                    template_path = Path(root, filename)
                    relative_path = str(template_path).replace(str(path) + os.sep, "")

                    if os.sep != "/":
                        relative_path = relative_path.replace(os.sep, "/")

                    templates.add(relative_path)

        return sorted(templates)


class MockRedisLoader(MockAsyncBaseLoader):
    def __init__(
        self,
        encoding: Optional[str] = None,
        cache: Any = None,
        storage: Any = None,
        config: Any = None,
    ) -> None:
        super().__init__()
        self.encoding = encoding or "utf-8"
        self.cache = cache
        self.storage = storage
        self.config = config

    async def get_source_async(
        self, environment: Any = None, template: str = ""
    ) -> Tuple[str, str, Callable[[], bool]]:
        if self.cache:
            cache_key = f"template:{template}"
            exists = self.cache.exists(cache_key)
            if isinstance(exists, AsyncMock):
                exists = exists.return_value

            if exists:
                cached = self.cache.get(cache_key)
                if isinstance(cached, AsyncMock):
                    cached = cached.return_value
                return cached, f"templates/{template}", lambda: True

        if self.storage and hasattr(self.storage, "templates"):
            with suppress(Exception):
                exists = self.storage.templates.exists(f"templates/{template}")
                if isinstance(exists, AsyncMock):
                    exists = exists.return_value

                if exists:
                    content_bytes = self.storage.templates.open(f"templates/{template}")

                    if isinstance(content_bytes, AsyncMock):
                        content_bytes = content_bytes.return_value

                    if isinstance(content_bytes, bytes):
                        content = content_bytes.decode(self.encoding)
                    else:
                        content = str(content_bytes)

                    if self.cache:
                        cache_key = f"template:{template}"
                        self.cache.set(cache_key, content)

                    return content, f"templates/{template}", lambda: True

        raise MockTemplateNotFound(template)

    async def list_templates_async(self) -> List[str]:
        return ["test1.html", "test2.html", "subdir/test3.html"]


class MockStorageLoader(MockAsyncBaseLoader):
    def __init__(
        self,
        searchpath: Optional[Union[Path, List[Any]]] = None,
        encoding: Optional[str] = None,
        cache: Any = None,
        storage: Any = None,
        config: Any = None,
    ) -> None:
        super().__init__()
        self.encoding = encoding or "utf-8"
        self.cache = cache
        self.storage = storage
        self.config = config

    async def get_source_async(
        self, environment: Any = None, template: str = ""
    ) -> Tuple[str, str, Callable[[], bool]]:
        if not self.storage or not hasattr(self.storage, "templates"):
            raise MockTemplateNotFound(template)

        template_path = f"templates/{template}"

        if self.cache:
            cache_key = f"template:{template}"
            cached = self.cache.get(cache_key)
            if cached:
                return cached, template_path, lambda: True

        try:
            if not self.storage.templates.exists(template_path):
                raise MockTemplateNotFound(template)

            content_bytes = self.storage.templates.open(template_path)

            if isinstance(content_bytes, bytes):
                content = content_bytes.decode(self.encoding)
            else:
                content = str(content_bytes)

            if self.cache:
                cache_key = f"template:{template}"
                self.cache.set(cache_key, content)

            return content, template_path, lambda: True
        except Exception as e:
            raise MockTemplateNotFound(template) from e

    async def list_templates_async(self) -> List[str]:
        if not self.storage or not hasattr(self.storage, "templates"):
            return []

        try:
            templates = self.storage.templates.list(Path("templates"))
            return templates
        except Exception:
            return []


class MockChoiceLoader(MockAsyncBaseLoader):
    def __init__(
        self,
        loaders: Optional[List[Any]] = None,
        encoding: Optional[str] = None,
        cache: Any = None,
        storage: Any = None,
        config: Any = None,
    ) -> None:
        super().__init__()
        self.loaders = loaders or []
        self.encoding = encoding or "utf-8"
        self.cache = cache
        self.storage = storage
        self.config = config

    async def get_source_async(
        self, environment: Any = None, template: str = ""
    ) -> Tuple[str, str, Callable[[], bool]]:
        for loader in self.loaders:
            try:
                return await loader.get_source_async(environment, template)
            except MockTemplateNotFound:
                continue

        raise MockTemplateNotFound(template)

    async def list_templates_async(self) -> List[str]:
        templates = set()

        for loader in self.loaders:
            templates.update(await loader.list_templates_async())

        return sorted(templates)


class MockPackageLoader(MockAsyncBaseLoader):
    def __init__(
        self,
        package_name: Optional[str] = None,
        package_path: Optional[str] = None,
        encoding: Optional[str] = None,
        cache: Any = None,
        storage: Any = None,
        config: Any = None,
    ) -> None:
        super().__init__()
        self.package_name = package_name or "tests"
        self.package_path = package_path or "templates"
        self.encoding = encoding or "utf-8"
        self.cache = cache
        self.storage = storage
        self.config = config

    async def get_source_async(
        self, environment: Any = None, template: str = ""
    ) -> Tuple[str, str, Callable[[], bool]]:
        if template == "test.html":
            return (
                "<html><body>Test from package</body></html>",
                f"templates/{template}",
                lambda: True,
            )

        raise MockTemplateNotFound(template)

    async def list_templates_async(self) -> List[str]:
        return ["test1.html", "test2.html", "subdir/test3.html"]


class MockDictLoader(MockAsyncBaseLoader):
    def __init__(
        self,
        templates: Optional[Dict[str, str]] = None,
        encoding: Optional[str] = None,
        cache: Any = None,
        storage: Any = None,
        config: Any = None,
    ) -> None:
        super().__init__()
        self.templates = templates or {}
        self.encoding = encoding or "utf-8"
        self.cache = cache
        self.storage = storage
        self.config = config

    async def get_source_async(
        self, environment: Any = None, template: str = ""
    ) -> Tuple[str, str, Callable[[], bool]]:
        if template not in self.templates:
            raise MockTemplateNotFound(template)

        content = self.templates[template]
        return content, template, lambda: True

    async def list_templates_async(self) -> List[str]:
        return list(self.templates.keys())


class MockFunctionLoader(MockAsyncBaseLoader):
    def __init__(
        self,
        load_func: Optional[Callable[[str], str]] = None,
        encoding: Optional[str] = None,
        cache: Any = None,
        storage: Any = None,
        config: Any = None,
    ) -> None:
        super().__init__()
        self.load_func = load_func or (lambda x: x)
        self.encoding = encoding or "utf-8"
        self.cache = cache
        self.storage = storage
        self.config = config

    async def get_source_async(
        self, environment: Any = None, template: str = ""
    ) -> Tuple[str, str, Callable[[], bool]]:
        content = self.load_func(template)
        return content, template, lambda: True

    async def list_templates_async(self) -> List[str]:
        return []


class MockPrefixLoader(MockAsyncBaseLoader):
    def __init__(
        self,
        loaders: Optional[Dict[str, Any]] = None,
        delimiter: Optional[str] = None,
        encoding: Optional[str] = None,
        cache: Any = None,
        storage: Any = None,
        config: Any = None,
    ) -> None:
        super().__init__()
        self.loaders = loaders or {}
        self.delimiter = delimiter or "/"
        self.encoding = encoding or "utf-8"
        self.cache = cache
        self.storage = storage
        self.config = config

    async def get_source_async(
        self, environment: Any = None, template: str = ""
    ) -> Tuple[str, str, Callable[[], bool]]:
        if self.delimiter not in template:
            raise MockTemplateNotFound(template)

        prefix, name = template.split(self.delimiter, 1)
        if prefix not in self.loaders:
            raise MockTemplateNotFound(template)

        return await self.loaders[prefix].get_source_async(environment, name)

    async def list_templates_async(self) -> List[str]:
        templates = set()

        for prefix, loader in self.loaders.items():
            templates.update(
                prefix + self.delimiter + template
                for template in await loader.list_templates_async()
            )

        return sorted(templates)
