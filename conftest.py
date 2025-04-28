"""Common test fixtures for all adapter tests."""

import tempfile
import typing as t
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from unittest import mock

import pytest
from acb.config import AdapterBase, Config
from starlette.requests import Request
from starlette.responses import HTMLResponse, PlainTextResponse, Response
from starlette.routing import Mount, Route


# Mock Adapter classes
class MockAdapter:
    """Base mock adapter for testing."""

    def __init__(
        self, /, name: str = "mock", category: str = "test", **data: Any
    ) -> None:
        self.name = name
        self.category = category
        self.class_name = data.get("class_name", "MockAdapter")
        self.path = Path(__file__).parent
        self.enabled = True
        self.installed = True
        self.pkg = "test"


class MockTemplatesAdapter(MockAdapter):
    """Mock templates adapter."""

    def __init__(self) -> None:
        super().__init__(
            name="templates", category="templates", class_name="MockTemplates"
        )


class MockModelsAdapter(MockAdapter):
    """Mock models adapter."""

    def __init__(self) -> None:
        super().__init__(name="models", category="models", class_name="MockModels")


class MockRoutesAdapter(MockAdapter):
    """Mock routes adapter."""

    def __init__(self) -> None:
        super().__init__(name="routes", category="routes", class_name="MockRoutes")


class MockSitemapAdapter(MockAdapter):
    """Mock sitemap adapter."""

    def __init__(self) -> None:
        super().__init__(name="sitemap", category="sitemap", class_name="MockSitemap")


# Mock implementations
class MockTemplateRenderer:
    """Mock implementation of template renderer for testing."""

    def __init__(self) -> None:
        self._mock_responses = {}

    def set_response(self, template: str, response: Response) -> None:
        """Set a mock response for a specific template."""
        self._mock_responses[template] = response

    async def render_template(
        self,
        request: Request,
        template: str,
        context: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Response:
        # Check if we have a mock response for this template
        if template in self._mock_responses:
            return self._mock_responses[template]

        # Default behavior
        context = context or {}
        headers = headers or {}
        content = f"<html><body>{template}: {', '.join(context.keys())}</body></html>"
        if "home" in template:
            content = "<html><body>home</body></html>"
        elif "about" in template:
            content = "<html><body>about</body></html>"
        elif "cached.html" in template:
            content = "<html><body>Cached content</body></html>"
            # Store in cache if we have access to it
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
        """Render a template block."""
        context = context or {}
        content = f"<div>{template}: {block or 'default'}</div>"
        return HTMLResponse(content)


class MockModels(AdapterBase):
    """Mock models implementation for testing."""

    def __init__(self) -> None:
        self.initialized: bool = False

    async def init(self) -> None:
        self.initialized = True


class MockTemplates(AdapterBase):
    """Mock templates implementation for testing."""

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
        """Mock implementation of get_searchpath."""
        style = "test_style"  # Default style for tests
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
        """Mock implementation of get_searchpaths."""
        from anyio import Path as AsyncPath

        # Create a basic path for testing
        path = AsyncPath(adapter.path / "templates" / adapter.category)
        searchpaths = self.get_searchpath(adapter, path)

        # Add other adapter paths if needed
        if hasattr(adapter, "path") and hasattr(adapter.path, "parent"):
            templates_path = adapter.path.parent / "_templates"
            if templates_path not in searchpaths:
                searchpaths.append(templates_path)

        return searchpaths

    @staticmethod
    def get_storage_path(path: Any) -> Any:
        """Mock implementation of get_storage_path."""
        templates_path_name = "templates"
        if templates_path_name not in path.parts:
            templates_path_name = "_templates"

        # Find the index of templates in the path
        try:
            depth = path.parts.index(templates_path_name)
            return type(path)("/".join(path.parts[depth:]))
        except ValueError:
            # If templates not in path, return the path as is
            return path

    @staticmethod
    def get_cache_key(path: Any) -> str:
        """Mock implementation of get_cache_key."""
        return ":".join(path.parts)

    async def init(self) -> None:
        self.initialized = True


class MockSitemap(AdapterBase):
    """Mock sitemap implementation for testing."""

    def __init__(self) -> None:
        # Create a class with the required attributes
        class SitemapObj:
            def __init__(self) -> None:
                self.change_freq = "hourly"
                self.urls = []

        self.sitemap = SitemapObj()
        self.initialized: bool = False

        # Create a config object that matches the expected type
        # We're using a dynamic type here, so we need to add a type ignore
        from acb.config import Config as AcbConfig

        # Create a mock config that has the same interface as Config
        class MockConfig(AcbConfig):
            pass

        self.config = MockConfig()  # type: ignore

    async def generate(self) -> str:
        xml = "<?xml version='1.0' encoding='UTF-8'?>"
        xml += "<urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>"

        for url in self.sitemap.urls:
            xml += f"<url><loc>{url.loc}</loc>"
            if hasattr(url, "lastmod") and url.lastmod:
                xml += f"<lastmod>{url.lastmod.isoformat()}</lastmod>"
            # Always include change_freq, using default if not specified
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

    async def init(self) -> None:
        self.initialized = True

    async def add_url(
        self,
        url: str,
        priority: float = 0.5,
        change_freq: Optional[str] = None,
        lastmod: Optional[Any] = None,
    ) -> None:
        # Validate URL
        if not url.startswith(("http", "/")):
            raise ValueError(f"Invalid URL: {url}")
        if " " in url:
            raise ValueError(f"URL cannot contain spaces: {url}")
        if url.startswith("ftp"):
            raise ValueError(f"Unsupported protocol: {url}")

        # Validate priority
        if not isinstance(priority, float):
            raise ValueError(
                f"Invalid priority: {priority}. Must be a number between 0 and 1"
            )
        if priority < 0 or priority > 1:
            raise ValueError(
                f"Invalid priority: {priority}. Must be a number between 0 and 1"
            )

        # Validate change_freq
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
                # Default path for testing
                path = Path(tempfile.gettempdir()) / "sitemap.xml"

        # Write to file
        # We know path is not None at this point
        assert path is not None  # This helps the type checker
        path.write_text(content)


class MockRoutes(AdapterBase):
    """Mock routes implementation for testing."""

    def __init__(self) -> None:
        self.routes = []
        self.initialized: bool = False
        self.middleware = []

    async def init(self) -> None:
        self.initialized = True

    async def gather_routes(
        self, path: Optional[Path] = None
    ) -> List[Union[Route, Mount]]:
        """Mock implementation of gather_routes."""
        # Create some test routes
        routes = [
            Route("/", self.index, methods=["GET"]),
            Route("/about", self.about, methods=["GET"]),
            Route("/contact", self.contact, methods=["GET"]),
            Route("/favicon.ico", self.favicon, methods=["GET"]),
            Route("/robots.txt", self.robots, methods=["GET"]),
            # Type ignore because StaticFiles is not recognized as an ASGIApp
            Mount("/static", StaticFiles(directory="static"), name="static"),  # type: ignore
        ]
        self.routes = routes
        return routes

    async def index(self, request: Request) -> Response:
        """Mock index route."""
        if request.scope.get("htmx", {}).get("request", False):
            return HTMLResponse("<div>HTMX Content</div>")
        return HTMLResponse("<html><body>Home Page</body></html>")

    async def about(self, request: Request) -> Response:
        """Mock about route."""
        return HTMLResponse("<html><body>About Page</body></html>")

    async def contact(self, request: Request) -> Response:
        """Mock contact route."""
        return HTMLResponse("<html><body>Contact Page</body></html>")

    async def favicon(self, request: Request) -> Response:
        """Mock favicon route."""
        return PlainTextResponse("favicon")

    async def robots(self, request: Request) -> Response:
        """Mock robots.txt route."""
        return PlainTextResponse("User-agent: *\nDisallow: /admin/")


class StaticFiles:
    """Mock static files implementation."""

    def __init__(self, directory: str) -> None:
        self.directory = directory


class MockCache:
    """Mock cache implementation for testing."""

    def __init__(self) -> None:
        self._storage: dict[str, Any] = {}
        self.initialized: bool = False

    async def get(self, key: str) -> Any:
        return self._storage.get(key)

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        self._storage[key] = value

    async def exists(self, key: str) -> bool:
        return key in self._storage

    async def delete(self, key: str) -> None:
        self._storage.pop(key, None)

    async def init(self) -> None:
        self.initialized = True


@pytest.fixture(autouse=True)
def patch_import_adapter():
    """Patch the import_adapter function to return our mock adapters."""
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
            return None

        mock_import_adapter.side_effect = mock_adapter_func
        yield


@pytest.fixture
def config(tmp_path: Path) -> Config:
    """Provide a test configuration."""
    config = Config()

    # Add storage attribute to Config
    class StorageConfig:
        def __init__(self) -> None:
            self.local_fs = True
            self.local_path = tmp_path

    # Set storage attribute on config
    config.__dict__["storage"] = StorageConfig()

    # Set app style
    class AppConfig:
        def __init__(self) -> None:
            self.style = "test_style"

    # Set app attribute on config
    config.__dict__["app"] = AppConfig()

    return config


@pytest.fixture
def models() -> MockModels:
    """Provide access to mock models."""
    return MockModels()


@pytest.fixture
def templates() -> MockTemplates:
    """Provide access to mock templates."""
    return MockTemplates()


@pytest.fixture
def sitemap(config: Config) -> MockSitemap:
    """Provide access to mock sitemap."""
    sitemap = MockSitemap()
    sitemap.config = config
    sitemap.sitemap.urls = []
    return sitemap


@pytest.fixture
def routes() -> MockRoutes:
    """Provide access to mock routes."""
    return MockRoutes()


@pytest.fixture
def cache() -> MockCache:
    """Provide access to mock cache."""
    return MockCache()


@pytest.fixture
def http_request() -> Request:
    """Create a mock HTTP request for testing."""
    scope: Dict[str, Any] = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [],
        "query_string": b"",
        "htmx": {"request": False},
    }
    return Request(scope)


@pytest.fixture
def mock_adapter() -> t.Type[MockAdapter]:
    """Provide the MockAdapter class for tests."""
    return MockAdapter


@pytest.fixture
def mock_storage() -> mock.AsyncMock:
    """Provide a mock storage for testing."""
    storage = mock.AsyncMock()
    storage.templates.exists.return_value = False
    storage.templates.open.side_effect = FileNotFoundError
    storage.templates.stat.return_value = {"mtime": 0, "size": 0}
    storage.templates.list.return_value = []
    storage.templates.write.return_value = None
    return storage
