"""Shared mock classes for the FastBlocks test suite.

Extracted from tests/conftest.py to keep conftest under 500 lines.
Import these directly rather than importing from tests.conftest.
"""
from __future__ import annotations

import os
import typing as t
from contextlib import suppress
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

from starlette.requests import Request
from starlette.responses import HTMLResponse, Response

if t.TYPE_CHECKING:
    from collections.abc import Callable


# ---------------------------------------------------------------------------
# Path mock
# ---------------------------------------------------------------------------


class MockAsyncPath:
    def __init__(self, path: str | Path | MockAsyncPath = "") -> None:
        if isinstance(path, MockAsyncPath):
            self._path = path._path
        else:
            self._path = str(path)
        self._hash = hash(self._path)

    def __str__(self) -> str:
        return self._path

    def __repr__(self) -> str:
        return f"MockAsyncPath('{self._path}')"

    def __fspath__(self) -> str:
        return self._path

    def __hash__(self) -> int:
        return self._hash

    def __eq__(self, other: object) -> bool:
        if isinstance(other, MockAsyncPath):
            return self._path == other._path
        if isinstance(other, str | Path):
            return self._path == str(other)
        return False

    def __iter__(self):
        yield self

    def __contains__(self, item: object) -> bool:
        try:
            other_str = str(item)
        except Exception:
            return False
        if other_str == self._path:
            return True
        return self._path.startswith(other_str.rstrip("/") + "/")

    def __truediv__(self, other: str | Path | MockAsyncPath) -> MockAsyncPath:
        other_str = str(other)
        if self._path.endswith("/"):
            return MockAsyncPath(f"{self._path}{other_str}")
        return MockAsyncPath(f"{self._path}/{other_str}")

    @property
    def parent(self) -> MockAsyncPath:
        parent_path = "/".join(self._path.split("/")[:-1])
        if not parent_path:
            parent_path = "/"
        return MockAsyncPath(parent_path)

    @property
    def name(self) -> str:
        return self._path.split("/")[-1]

    @property
    def stem(self) -> str:
        name = self.name
        i = name.rfind(".")
        if i == -1:
            return name
        return name[:i]

    @property
    def parts(self) -> tuple[str, ...]:
        parts = [part for part in self._path.split("/") if part]
        if self._path.startswith("/"):
            return ("/", *tuple(parts))
        return tuple(parts)

    async def exists(self) -> bool:
        return Path(self._path).exists()

    async def is_file(self) -> bool:
        return Path(self._path).is_file()

    async def is_dir(self) -> bool:
        return Path(self._path).is_dir()

    async def mkdir(self, parents: bool = False, exist_ok: bool = False) -> None:
        Path(self._path).mkdir(parents=parents, exist_ok=exist_ok)

    def with_suffix(self, suffix: str) -> MockAsyncPath:
        base = self._path.rsplit(".", 1)[0] if "." in self._path else self._path
        return MockAsyncPath(f"{base}{suffix}")

    def iterdir(self):
        class AsyncIterator:
            def __init__(self, real_iter) -> None:
                self._iter = iter(real_iter)

            def __aiter__(self):
                return self

            async def __anext__(self):
                try:
                    return MockAsyncPath(str(next(self._iter)))
                except StopIteration as exc:
                    raise StopAsyncIteration from exc

        return AsyncIterator(Path(self._path).iterdir())

    async def glob(self, pattern: str) -> list[MockAsyncPath]:
        return [MockAsyncPath(str(p)) for p in Path(self._path).glob(pattern)]

    def rglob(self, pattern: str):
        class AsyncIterator:
            def __init__(self, real_iter) -> None:
                self._iter = iter(real_iter)

            def __aiter__(self):
                return self

            async def __anext__(self):
                try:
                    return MockAsyncPath(str(next(self._iter)))
                except StopIteration as exc:
                    raise StopAsyncIteration from exc

        return AsyncIterator(Path(self._path).rglob(pattern))

    async def read_text(self, encoding: str = "utf-8") -> str:
        return Path(self._path).read_text(encoding=encoding)

    async def read_bytes(self) -> bytes:
        return Path(self._path).read_bytes()

    async def write_text(self, data: str, encoding: str = "utf-8") -> None:
        Path(self._path).write_text(data, encoding=encoding)

    async def stat(self) -> t.Any:
        real = Path(self._path).stat()
        return SimpleNamespace(st_mtime=int(real.st_mtime), st_size=real.st_size)


# ---------------------------------------------------------------------------
# Exception mock (moved here so MockTemplateRenderer can reference it)
# ---------------------------------------------------------------------------


class MockTemplateNotFound(Exception):
    def __init__(self, name: str) -> None:
        self.name = name
        self.message = f"Template '{name}' not found"
        super().__init__(self.message)


# ---------------------------------------------------------------------------
# Adapter / config / template mocks
# ---------------------------------------------------------------------------


class MockAdapter:
    def __init__(
        self,
        name: str = "test",
        category: str = "app",
        path: t.Any = None,
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
        self.templates.extensions = []
        self.templates.context_processors = []
        self.templates.loader = None
        self.templates.delimiters = {}
        self.templates.globals = {}

        self.cache = Mock()
        self.cache.enabled = True
        self.cache.ttl = 3600

        self.storage = Mock()
        self.storage.local_path = "storage"
        self.storage.local_fs = True

        self.sitemap = Mock()
        self.sitemap.change_freq = "hourly"
        self.sitemap.priority = 0.5

        self.debug = Mock()
        self.debug.templates = False

        self.admin = Mock()
        self.admin.style = "bootstrap"
        self.admin.title = "Test Admin"

        self.deployed = False
        self.package_name: str | None = None

    def __getitem__(self, key: str) -> t.Any:
        return getattr(self, key)

    def __setitem__(self, key: str, value: t.Any) -> None:
        setattr(self, key, value)

    def __call__(self, key: str | None = None) -> t.Any:
        if key is None:
            return self
        return self[key]

    def get(self, key: str, default: t.Any = None) -> t.Any:
        return getattr(self, key, default)

    def set(self, key: str, value: t.Any) -> None:
        setattr(self, key, value)


class MockTemplateFilters:
    @staticmethod
    def truncate(text: str, length: int) -> str:
        return text[: length - 3] + "..." if len(text) > length else text

    @staticmethod
    def filesize(size: int) -> str:
        if size < 1024 or size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        if size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB"
        return f"{size / (1024 * 1024 * 1024):.1f} GB"


class MockTemplateRenderer:
    def __init__(
        self,
        storage: MockStorage | None = None,
        cache: MockCache | None = None,
    ) -> None:
        self.templates: dict[str, str] = {
            "page.html": "<html><body>page.html: title, content, items</body></html>",
            "custom.html": "<html><body>Custom template response</body></html>",
            "cached.html": "<html><body>Cached content</body></html>",
            "test.html": "<html><body>test.html: {{ title }}, {{ content }}</body></html>",
        }
        self.storage = storage
        self.cache = cache
        self._mock_responses: dict[str, Response] = {}

    def add_template(self, name: str, content: str) -> None:
        self.templates[name] = content

    def set_response(self, template: str, response: Response) -> None:
        self._mock_responses[template] = response

    async def render_template(
        self,
        request: Request,
        template: str,
        context: dict[str, t.Any] | None = None,
        headers: dict[str, str] | None = None,
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
        block: str | None = None,
        context: dict[str, t.Any] | None = None,
    ) -> str:
        if context is None:
            context = {}

        if template not in self.templates:
            raise MockTemplateNotFound(template)

        return f"Block {block} from {template}"


class MockTemplates:
    def __init__(
        self,
        config: MockConfig | None = None,
        storage: t.Any | None = None,
        cache: t.Any | None = None,
    ) -> None:
        self.storage = storage
        self.cache = cache
        self.config = config or MockConfig()

        if not hasattr(self.config, "app"):
            self.config.app = SimpleNamespace(style="test_style")
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

    def get_searchpath(self, adapter: t.Any, path: t.Any) -> list[t.Any]:
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

    async def get_searchpaths(self, adapter: t.Any) -> list[t.Any]:
        from unittest.mock import patch

        with patch("fastblocks.adapters.templates._base.root_path", adapter.path):
            return self.get_searchpath(
                adapter,
                adapter.path / "templates" / adapter.category,
            )

    def get_storage_path(self, path: str | Path) -> str:
        return f"templates/{path}"

    def get_cache_key(self, path: str | Path) -> str:
        return f"template:{path}"


class MockStorage:
    def __init__(self) -> None:
        self._storage: dict[str, t.Any] = {}

    def __getitem__(self, key: str) -> t.Any:
        return self._storage[key]

    def __setitem__(self, key: str, value: t.Any) -> None:
        self._storage[key] = value

    def __delitem__(self, key: str) -> None:
        del self._storage[key]

    def __contains__(self, key: str) -> bool:
        return key in self._storage

    def get(self, key: str, default: t.Any = None) -> t.Any:
        return self._storage.get(key, default)

    def set(self, key: str, value: t.Any) -> None:
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
        self._cache: dict[str, t.Any] = {}

    def get(self, key: str, default: t.Any = None) -> t.Any:
        return self._cache.get(key, default)

    def set(self, key: str, value: t.Any, expire: int = 0) -> None:
        self._cache[key] = value

    def delete(self, key: str) -> None:
        if key in self._cache:
            del self._cache[key]

    def exists(self, key: str) -> bool:
        return key in self._cache

    def clear(self) -> None:
        self._cache.clear()


class MockModels:
    def __init__(self) -> None:
        self.models: dict[str, t.Any] = {}

    def get_model(self, model_name: str) -> t.Any:
        return self.models.get(model_name)

    def register_model(self, model_name: str, model: t.Any) -> None:
        self.models[model_name] = model


class MockAdapters:
    def __init__(self) -> None:
        self.root_path = MockAsyncPath("/mock/root/path")
        self.Adapter = MagicMock()
        self.pkg_registry = {}
        self._adapters = self._create_adapter_objects()

    def _create_adapter_objects(self) -> dict[str, MockAdapter]:
        adapters = {}
        for name in ("cache", "storage", "templates", "routes"):
            adapter = MockAdapter(name)
            adapter.path = MockAsyncPath(f"/mock/adapters/{name}")
            adapters[name] = adapter
        return adapters

    def import_adapter(self, adapter_name: str = "cache") -> tuple[t.Any, t.Any, t.Any]:
        mock_cache = MockCache()
        mock_storage = MockStorage()
        mock_models = MockModels()
        mock_templates = MockTemplates(MockConfig(), mock_storage, mock_cache)

        if adapter_name == "cache":
            return (mock_cache, mock_storage, mock_models)
        if adapter_name == "storage":
            return (mock_storage, mock_models, None)
        if adapter_name == "templates":
            return (mock_templates, None, None)
        if adapter_name == "routes":
            mock_routes = MagicMock()
            return (mock_routes, None, None)
        return (MagicMock(), MagicMock(), MagicMock())

    def get_adapters(self) -> list[t.Any]:
        return list(self._adapters.values())

    def get_installed_adapter(self, adapter_name: str) -> t.Any:
        return self._adapters.get(adapter_name, MagicMock())

    def get_adapter(self, adapter_name: str) -> t.Any:
        if adapter_name == "cache":
            return MockCache()
        if adapter_name == "storage":
            return MockStorage()
        if adapter_name == "templates":
            return MockTemplates(MockConfig(), MockStorage(), MockCache())
        if adapter_name == "routes":
            return MagicMock()
        return MagicMock()


class MockConfigModule:
    def __init__(self) -> None:
        self._config = MockConfig()
        self.AsyncPath = lambda *args, **kwargs: MockAsyncPath(*args, **kwargs)
        self.Config = self._config
        self.Adapter = MagicMock()
        self.pkg_registry = {}

    class AdapterBase:
        def __init__(self, *args: t.Any, **kwargs: t.Any) -> None:
            self.name = "mock_adapter"
            self.settings = {}

    class Settings:
        def __init__(self, *args: t.Any, **kwargs: t.Any) -> None:
            self.settings = {}
            self.app = SimpleNamespace()
            self.adapters = SimpleNamespace()
            self.debug = SimpleNamespace()

        def load(self) -> None:
            pass

        def __getattr__(self, name: str) -> t.Any:
            return self.settings.get(name, None)

        def __setattr__(self, name: str, value: t.Any) -> None:
            if name in ("settings", "app", "adapters", "debug"):
                super().__setattr__(name, value)
            else:
                self.settings[name] = value


class MockActions:
    def __init__(self) -> None:
        self.hash = self._create_hash_module()

    def _create_hash_module(self) -> t.Any:
        class HashModule:
            def __init__(self) -> None:
                pass

            def hash(self, content: t.Any) -> str:
                if isinstance(content, str | bytes):
                    return f"hash_{len(content)}"
                return "hash_mock"

        return HashModule()


class MockDepends:
    def __init__(self) -> None:
        self.dependencies: dict[str, t.Any] = {}

        def depends_func(*args: t.Any, **kwargs: t.Any) -> t.Any:
            def decorator(func: t.Any) -> t.Any:
                return func

            return decorator

        def inject_func(func: t.Any) -> t.Any:
            return func

        def set_func(cls: t.Any) -> t.Any:
            self.dependencies[cls.__name__] = cls
            return cls

        def get_func(name: str) -> t.Any:
            return self.dependencies.get(name, MagicMock())

        self.depends = depends_func
        self.depends.inject = inject_func
        self.depends.set = set_func
        self.depends.get = get_func


class MockDependsInjector:
    @staticmethod
    def inject(f: t.Any) -> t.Any:
        def wrapper(*args: t.Any, **kwargs: t.Any) -> t.Any:
            if (
                "config" not in kwargs
                and len(args) > 1
                and isinstance(args[1], MockConfig)
            ):
                kwargs["config"] = args[1]
            return f(*args, **kwargs)

        return wrapper


class MockTemplatesBaseSettings:
    def __init__(
        self,
        config: t.Any = None,
        cache_timeout: int = 300,
        **values: t.Any,
    ) -> None:
        self.cache_timeout = cache_timeout
        if config:
            self.update_from_config(config)

    def update_from_config(self, config: t.Any) -> None:
        self.cache_timeout = 300 if getattr(config, "deployed", False) else 1


class MockDebug:
    def __init__(self) -> None:
        self.enabled = True

    def debug(self, *args: t.Any, **kwargs: t.Any) -> None:
        pass

    def trace(self, *args: t.Any, **kwargs: t.Any) -> None:
        pass

    def error(self, *args: t.Any, **kwargs: t.Any) -> None:
        pass


class MockLogger:
    def __init__(self) -> None:
        self.InterceptHandler = MagicMock()
        self.Logger = self._create_logger_class()

    def _create_logger_class(self) -> t.Any:
        class LoggerClass:
            def __init__(self, *args: t.Any, **kwargs: t.Any) -> None:
                self.name = kwargs.get("name", "mock_logger")

            def bind(self, **kwargs: t.Any) -> LoggerClass:
                return self

            def debug(self, message: str, *args: t.Any, **kwargs: t.Any) -> None:
                pass

            def info(self, message: str, *args: t.Any, **kwargs: t.Any) -> None:
                pass

            def warning(self, message: str, *args: t.Any, **kwargs: t.Any) -> None:
                pass

            def error(self, message: str, *args: t.Any, **kwargs: t.Any) -> None:
                pass

            def exception(self, message: str, *args: t.Any, **kwargs: t.Any) -> None:
                pass

        return LoggerClass


class SitemapURL:
    def __init__(
        self,
        loc: str,
        change_freq: str,
        priority: float,
        last_modified: datetime,
    ) -> None:
        self.loc = loc
        self.change_freq = change_freq
        self.priority = priority
        self.last_modified = last_modified


class MockSitemap:
    def __init__(self) -> None:
        class InnerSitemap:
            def __init__(self) -> None:
                self.urls = []
                self.change_freq = "hourly"
                self.priority = 0.5

        self.sitemap = InnerSitemap()
        self.config: t.Any = None

    async def init(self) -> None:
        pass

    async def add_url(self, url: str, **kwargs: t.Any) -> None:
        if not url.startswith(("/", "http")):
            msg = f"Invalid URL format: {url}"
            raise ValueError(msg)

        if " " in url:
            msg = f"URL contains invalid characters: {url}"
            raise ValueError(msg)

        if url.startswith("ftp:"):
            msg = f"Unsupported URL protocol: {url}"
            raise ValueError(msg)

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
            msg = f"Invalid change frequency: {change_freq}"
            raise ValueError(msg)

        priority = kwargs.get("priority", 0.5)
        if not isinstance(priority, int | float) or priority < 0.0 or priority > 1.0:
            msg = f"Invalid priority value: {priority}. Must be between 0.0 and 1.0"
            raise ValueError(msg)

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

    async def write(self, path: t.Any = None) -> None:
        xml = await self.generate()

        if path is None:
            if hasattr(self.config, "storage") and hasattr(
                self.config.storage, "local_path"
            ):
                path = Path(self.config.storage.local_path) / "sitemap.xml"
            else:
                msg = "No path provided and no default path available in config"
                raise ValueError(msg)

        if hasattr(path, "_path"):
            path = Path(path._path)

        Path(path).parent.mkdir(exist_ok=True, parents=True)
        Path(path).write_text(xml)


class MockUptodate:
    def __init__(self) -> None:
        self.updates: dict[str, bool] = {}

    def check(self, package: str) -> bool:
        return self.updates.get(package, True)

    def set_update(self, package: str, is_up_to_date: bool) -> None:
        self.updates[package] = is_up_to_date


# ---------------------------------------------------------------------------
# Loader mock classes (used by tests/adapters/templates/test_loaders*.py)
# ---------------------------------------------------------------------------


class MockAsyncBaseLoader:
    def __init__(self, searchpath: Path | list[t.Any] | None = None) -> None:
        if searchpath is None:
            self.searchpath = [MockAsyncPath("templates")]
        elif isinstance(searchpath, list):
            self.searchpath = searchpath
        else:
            self.searchpath = [searchpath]

        self.encoding = "utf-8"

    async def get_source_async(
        self,
        template: str | t.Any,
    ) -> tuple[str, str, Callable[[], bool]]:
        raise NotImplementedError

    async def list_templates_async(self) -> list[str]:
        raise NotImplementedError


class MockFileSystemLoader(MockAsyncBaseLoader):
    def __init__(
        self,
        searchpath: Path | list[t.Any] | None = None,
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

    def get_source(self, template: str = "") -> tuple[str, str, Callable[[], bool]]:
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
        self,
        template: str | t.Any,
    ) -> tuple[str, str, t.Callable[[], bool]]:
        if not self.searchpath:
            raise MockTemplateNotFound(template)

        storage_result = await self._try_storage_source(template)
        if storage_result:
            return storage_result

        searchpath_result = await self._try_searchpath_source(template)
        if searchpath_result:
            return searchpath_result

        raise MockTemplateNotFound(template)

    async def _try_storage_source(
        self,
        template: str,
    ) -> tuple[str, str, t.Callable[[], bool]] | None:
        if not (self.storage and hasattr(self.storage, "templates")):
            return None

        with suppress(Exception):
            if self.storage.templates.exists(f"templates/{template}"):
                content_bytes = self.storage.templates.open(f"templates/{template}")
                content = self._decode_content(content_bytes)
                self._cache_content(template, content)
                return content, template, lambda: True

        return None

    async def _try_searchpath_source(
        self,
        template: str,
    ) -> tuple[str, str, t.Callable[[], bool]] | None:
        for path in self.searchpath:
            if isinstance(path, str):
                path = Path(path)
            template_path = path / template
            if Path(template_path).exists():
                content = open(template_path).read()
                return content, str(template_path), lambda: True

        return None

    def _decode_content(self, content_bytes: t.Any) -> str:
        if isinstance(content_bytes, bytes):
            return content_bytes.decode(self.encoding)
        return str(content_bytes)

    def _cache_content(self, template: str, content: str) -> None:
        if self.cache:
            cache_key = f"template:{template}"
            self.cache.set(cache_key, content)

    async def list_templates_async(self) -> list[str]:
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
        searchpath: t.Any = None,
        encoding: str | None = None,
        cache: t.Any = None,
        storage: t.Any = None,
        config: t.Any = None,
    ) -> None:
        super().__init__(searchpath)
        self.encoding = encoding or "utf-8"
        self.cache = cache
        self.storage = storage
        self.config = config

    async def get_source_async(
        self,
        template: str | t.Any,
    ) -> tuple[str, str, t.Callable[[], bool]]:
        cache_result = await self._try_cache_source(template)
        if cache_result:
            return cache_result

        storage_result = await self._try_storage_source_redis(template)
        if storage_result:
            return storage_result

        from jinja2 import TemplateNotFound

        raise TemplateNotFound(template)

    async def _try_cache_source(
        self,
        template: str,
    ) -> tuple[str, str, t.Callable[[], bool]] | None:
        if not self.cache:
            return None

        cache_key = f"template:{template}"
        exists = await self.cache.exists(cache_key)
        if not exists:
            return None

        cached = await self.cache.get(cache_key)
        content = cached.decode() if isinstance(cached, bytes) else str(cached)

        def cache_uptodate() -> bool:
            return True

        return content, f"templates/{template}", cache_uptodate

    async def _try_storage_source_redis(
        self,
        template: str,
    ) -> tuple[str, str, t.Callable[[], bool]] | None:
        if not (self.storage and hasattr(self.storage, "templates")):
            return None

        with suppress(Exception):
            template_path = f"templates/{template}"
            exists = await self.storage.templates.exists(template_path)
            if not exists:
                return None

            content_bytes = await self.storage.templates.open(template_path)
            content = self._decode_content_redis(content_bytes)
            await self._cache_content_redis(template, content)

            async def storage_uptodate() -> bool:
                return True

            return content, template_path, storage_uptodate  # type: ignore

        return None

    def _decode_content_redis(self, content_bytes: t.Any) -> str:
        if isinstance(content_bytes, bytes):
            return content_bytes.decode(self.encoding)
        return str(content_bytes)

    async def _cache_content_redis(self, template: str, content: str) -> None:
        if self.cache:
            cache_key = f"template:{template}"
            await self.cache.set(cache_key, content)

    async def list_templates_async(self) -> list[str]:
        found: list[str] = []
        for ext in ("html", "css", "js"):
            scan_result = await self.cache.scan(f"*.{ext}")
            found.extend(scan_result)
        found.sort()
        return found


class MockStorageLoader(MockAsyncBaseLoader):
    def __init__(
        self,
        searchpath: Path | list[t.Any] | None = None,
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

    async def get_source_async(
        self,
        template: str | t.Any,
    ) -> tuple[str, str, t.Callable[[], bool]]:
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

    async def list_templates_async(self) -> list[str]:
        if not self.storage or not hasattr(self.storage, "templates"):
            return []

        try:
            return self.storage.templates.list(Path("templates"))
        except Exception:
            return []


class MockChoiceLoader(MockAsyncBaseLoader):
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
        template: str | t.Any,
    ) -> tuple[str, str, t.Callable[[], bool]]:
        for loader in self.loaders:
            try:
                return await loader.get_source_async(template)
            except (MockTemplateNotFound, Exception):
                continue

        from jinja2 import TemplateNotFound

        raise TemplateNotFound(str(template))

    async def list_templates_async(self) -> list[str]:
        templates = set()
        for loader in self.loaders:
            templates.update(await loader.list_templates_async())
        return sorted(templates)


class MockPackageLoader(MockAsyncBaseLoader):
    def __init__(
        self,
        package_name: str | None = None,
        package_path: str | None = None,
        adapter: str = "admin",
        encoding: str | None = None,
        cache: t.Any = None,
        storage: t.Any = None,
        config: t.Any = None,
    ) -> None:
        super().__init__()
        self.package_name = package_name or "tests"
        self.package_path = package_path or "templates"
        self._adapter = adapter
        from anyio import Path as AsyncPath

        self._template_root = AsyncPath(f"/path/to/package/{package_path}")
        self.encoding = encoding or "utf-8"
        self.cache = cache
        self.storage = storage
        self.config = config

    async def get_source_async(
        self,
        template: str | t.Any,
    ) -> tuple[str, str, t.Callable[[], bool]]:
        path = self._template_root / template
        if not await path.is_file():
            from jinja2 import TemplateNotFound

            raise TemplateNotFound(template)

        source = await path.read_bytes()
        (await path.stat()).st_mtime

        async def uptodate() -> bool:
            return True

        replace = [("{{", "[["), ("}}", "]]"), ("{%", "[%"), ("%}", "%]")]
        if hasattr(self.config, "deployed") and self.config.deployed:
            replace.append(("http://", "https://"))
        for r in replace:
            source = source.replace(
                bytes(r[0], encoding="utf8"),
                bytes(r[1], encoding="utf8"),
            )

        storage_path = f"templates/{template}"
        cache_key = f"template:{storage_path}"
        if self.cache:
            await self.cache.set(cache_key, source)

        return (source.decode(), template, uptodate)  # type: ignore

    async def list_templates_async(self) -> list[str]:
        return ["test1.html", "test2.html", "subdir/test3.html"]


class MockDictLoader(MockAsyncBaseLoader):
    def __init__(
        self,
        templates: dict[str, str] | None = None,
        encoding: str | None = None,
        cache: t.Any = None,
        storage: t.Any = None,
        config: t.Any = None,
    ) -> None:
        super().__init__()
        self.templates = templates or {}
        self.encoding = encoding or "utf-8"
        self.cache = cache
        self.storage = storage
        self.config = config

    async def get_source_async(
        self,
        template: str | t.Any,
    ) -> tuple[str, str, t.Callable[[], bool]]:
        if template not in self.templates:
            raise MockTemplateNotFound(template)

        content = self.templates[template]
        return content, template, lambda: True

    async def list_templates_async(self) -> list[str]:
        return list(self.templates.keys())


class MockFunctionLoader(MockAsyncBaseLoader):
    def __init__(
        self,
        load_func: Callable[[str], str] | None = None,
        encoding: str | None = None,
        cache: t.Any = None,
        storage: t.Any = None,
        config: t.Any = None,
    ) -> None:
        super().__init__()
        self.load_func = load_func or (lambda x: x)
        self.encoding = encoding or "utf-8"
        self.cache = cache
        self.storage = storage
        self.config = config

    async def get_source_async(
        self,
        template: str | t.Any,
    ) -> tuple[str, str, t.Callable[[], bool]]:
        content = self.load_func(template)
        return content, template, lambda: True

    async def list_templates_async(self) -> list[str]:
        return []


class MockPrefixLoader(MockAsyncBaseLoader):
    def __init__(
        self,
        loaders: dict[str, t.Any] | None = None,
        delimiter: str | None = None,
        encoding: str | None = None,
        cache: t.Any = None,
        storage: t.Any = None,
        config: t.Any = None,
    ) -> None:
        super().__init__()
        self.loaders = loaders or {}
        self.delimiter = delimiter or "/"
        self.encoding = encoding or "utf-8"
        self.cache = cache
        self.storage = storage
        self.config = config

    async def get_source_async(
        self,
        template: str | t.Any,
    ) -> tuple[str, str, t.Callable[[], bool]]:
        if self.delimiter not in template:
            raise MockTemplateNotFound(template)

        prefix, name = template.split(self.delimiter, 1)
        if prefix not in self.loaders:
            raise MockTemplateNotFound(template)

        return await self.loaders[prefix].get_source_async(name)

    async def list_templates_async(self) -> list[str]:
        templates = set()
        for prefix, loader in self.loaders.items():
            templates.update(
                prefix + self.delimiter + template
                for template in await loader.list_templates_async()
            )
        return sorted(templates)
