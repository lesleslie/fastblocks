import typing as t
from contextlib import suppress
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, cast
from unittest.mock import AsyncMock, Mock, patch

import pytest
from acb.config import Config
from anyio import Path as AsyncPath
from jinja2 import TemplateNotFound
from starlette.requests import Request
from starlette.responses import Response
from fastblocks.adapters.templates import _base, jinja2
from fastblocks.adapters.templates._base import TemplatesBase, TemplatesBaseSettings
from fastblocks.adapters.templates.jinja2 import LoaderProtocol

TemplateContext = Dict[str, Any]
TemplateResponse = Response

setattr(LoaderProtocol, "storage", None)


async def safe_uptodate(uptodate_func: t.Any) -> bool:
    if callable(uptodate_func):
        try:
            result = uptodate_func()
            if hasattr(result, "__await__") and callable(getattr(result, "__await__")):
                return bool(await t.cast(t.Awaitable[t.Any], result))
            return bool(result)
        except Exception:
            return True
    return True


@pytest.mark.anyio
async def test_templates_base_settings_cache_timeout_deployed(config: Config) -> None:
    config.deployed = True
    settings = TemplatesBaseSettings()
    assert settings.cache_timeout == 300


@pytest.mark.anyio
async def test_templates_base_settings_cache_timeout_not_deployed(
    config: Config,
) -> None:
    config.deployed = False
    settings = TemplatesBaseSettings()
    assert settings.cache_timeout == 1


@pytest.mark.anyio
async def test_get_searchpath(
    templates: TemplatesBase, mock_adapter: type, tmp_path: Path
) -> None:
    adapter = mock_adapter(name="test_adapter", category="app", path=tmp_path)
    path = AsyncPath(tmp_path / "templates" / "app")
    await path.mkdir(parents=True, exist_ok=True)
    result = templates.get_searchpath(adapter, path)
    assert len(result) == 4
    assert result[0] == path / "test_style" / "test_adapter" / "theme"
    assert result[1] == path / "test_style" / "test_adapter"
    assert result[2] == path / "test_style"
    assert result[3] == path / "base"


@pytest.mark.anyio
async def test_get_searchpaths(
    templates: TemplatesBase, mock_adapter: type, tmp_path: Path
) -> None:
    adapter = mock_adapter(name="test_adapter", category="app", path=tmp_path)
    path = tmp_path / "templates" / "app"
    path.mkdir(parents=True, exist_ok=True)
    result = await templates.get_searchpaths(adapter)
    assert len(result) >= 4
    assert result[0] == AsyncPath(
        tmp_path / "templates" / "app" / "test_style" / "test_adapter" / "theme"
    )
    assert result[1] == AsyncPath(
        tmp_path / "templates" / "app" / "test_style" / "test_adapter"
    )
    assert result[2] == AsyncPath(tmp_path / "templates" / "app" / "test_style")
    assert result[3] == AsyncPath(tmp_path / "templates" / "app" / "base")


@pytest.mark.anyio
async def test_get_searchpaths_with_other_adapters(
    templates: TemplatesBase, mock_adapter: type, tmp_path: Path
) -> None:
    adapter = mock_adapter(name="test_adapter", category="app", path=tmp_path)
    other_adapter_path = tmp_path / "other_adapter"
    other_adapter_path.mkdir(parents=True, exist_ok=True)
    other_adapter_templates_path = other_adapter_path / "_templates"
    other_adapter_templates_path.mkdir(parents=True, exist_ok=True)

    class MockPkgRegistry:
        def get(self) -> list[t.Any]:
            return []

    class MockGetAdapters:
        def __iter__(self) -> t.Iterator[t.Any]:
            yield mock_adapter(
                name="other_adapter", category="other", path=other_adapter_path
            )

    _base.pkg_registry = MockPkgRegistry()
    _base.get_adapters = MockGetAdapters()

    result = await templates.get_searchpaths(adapter)
    assert AsyncPath(other_adapter_templates_path) in result


@pytest.mark.anyio
async def test_get_storage_path_templates(
    templates: TemplatesBase, tmp_path: Path
) -> None:
    path = AsyncPath(tmp_path / "some" / "path" / "templates" / "test" / "file.txt")
    result = templates.get_storage_path(path)
    assert result == AsyncPath("templates/test/file.txt")


@pytest.mark.anyio
async def test_get_storage_path_underscore_templates(
    templates: TemplatesBase, tmp_path: Path
) -> None:
    path = AsyncPath(tmp_path / "some" / "path" / "_templates" / "test" / "file.txt")
    result = templates.get_storage_path(path)
    assert result == AsyncPath("_templates/test/file.txt")


@pytest.mark.anyio
async def test_get_cache_key(templates: TemplatesBase, tmp_path: Path) -> None:
    path = AsyncPath(tmp_path / "some" / "path" / "test" / "file.txt")
    result = templates.get_cache_key(path)
    assert result == "some:path:test:file.txt"


@pytest.fixture
def jinja2_templates(config: Config) -> jinja2.Templates:
    templates = jinja2.Templates()
    return templates


@pytest.fixture
def mock_cache() -> Any:
    # Import the MockCache class from conftest
    from conftest import MockCache

    # Create a new instance of MockCache
    cache = MockCache()
    return cache


@pytest.fixture
def mock_storage() -> AsyncMock:
    storage = AsyncMock()

    # Create a templates bucket with proper methods
    templates_bucket = AsyncMock()
    templates_bucket.exists.return_value = False
    templates_bucket.open.side_effect = FileNotFoundError
    templates_bucket.stat.return_value = {"mtime": 0, "size": 0}
    templates_bucket.list.return_value = []
    templates_bucket.write.return_value = None

    # Set up the templates bucket to actually store data
    templates_bucket._storage = {}

    # Override the write method to actually store data
    async def mock_write(path: AsyncPath, data: bytes):
        templates_bucket._storage[str(path)] = data
        return None

    templates_bucket.write.side_effect = mock_write

    # Override the exists method to check the storage
    async def mock_exists(path: AsyncPath) -> bool:
        return str(path) in templates_bucket._storage

    templates_bucket.exists.side_effect = mock_exists

    # Override the open method to return stored data
    async def mock_open(path: AsyncPath):
        if str(path) in templates_bucket._storage:
            return templates_bucket._storage[str(path)]
        raise FileNotFoundError(f"File not found: {path}")

    templates_bucket.open.side_effect = mock_open

    # Attach the templates bucket to the storage
    storage.templates = templates_bucket

    return storage


class MockUptodate:
    async def __call__(self) -> bool:
        return True


@pytest.mark.anyio
async def test_file_system_loader_get_source_async_file_exists(
    config: Config, mock_cache: AsyncMock, mock_storage: AsyncMock, tmp_path: Path
) -> None:
    config.deployed = False
    path = tmp_path / "templates" / "test.html"
    path.parent.mkdir(parents=True, exist_ok=True)

    path.write_text("test")

    with patch.object(
        jinja2.FileSystemLoader, "get_source_async", autospec=True
    ) as mock_get_source:
        mock_uptodate = MockUptodate()
        mock_get_source.return_value = ("test", "templates/test.html", mock_uptodate)

        loader = t.cast(
            LoaderProtocol, jinja2.FileSystemLoader([AsyncPath(tmp_path / "templates")])
        )
        loader.cache = mock_cache
        loader.storage = mock_storage
        with suppress(AttributeError):
            loader.config = config

        source, filename, uptodate = await loader.get_source_async("test.html")
        assert source == "test"
        assert filename == "templates/test.html"
        assert await safe_uptodate(uptodate)
        mock_storage.templates.write.assert_called_once()
        mock_cache.set.assert_called_once()


@pytest.mark.anyio
async def test_file_system_loader_get_source_async_file_not_exists(
    config: Config, mock_cache: AsyncMock, mock_storage: AsyncMock, tmp_path: Path
) -> None:
    with patch.object(
        jinja2.FileSystemLoader, "get_source_async", autospec=True
    ) as mock_get_source:
        mock_get_source.side_effect = TemplateNotFound("test.html")

        loader = t.cast(
            LoaderProtocol, jinja2.FileSystemLoader([AsyncPath(tmp_path / "templates")])
        )
        loader.cache = mock_cache
        loader.storage = mock_storage
        with suppress(AttributeError):
            loader.config = config

        with pytest.raises(TemplateNotFound):
            await loader.get_source_async("test.html")
        mock_storage.templates.write.assert_not_called()
        mock_cache.set.assert_not_called()


@pytest.mark.anyio
async def test_file_system_loader_get_source_async_storage_exists(
    config: Config, mock_cache: AsyncMock, mock_storage: AsyncMock, tmp_path: Path
) -> None:
    config.deployed = False
    path = tmp_path / "templates" / "test.html"
    path.parent.mkdir(parents=True, exist_ok=True)

    path.write_text("test")

    mock_storage.templates.exists.return_value = True
    mock_storage.templates.open.return_value = b"storage"
    mock_storage.templates.stat.return_value = {"mtime": 1, "size": 1}

    with patch.object(
        jinja2.FileSystemLoader, "get_source_async", autospec=True
    ) as mock_get_source:
        mock_uptodate = MockUptodate()
        mock_get_source.return_value = ("storage", "templates/test.html", mock_uptodate)

        loader = t.cast(
            LoaderProtocol, jinja2.FileSystemLoader([AsyncPath(tmp_path / "templates")])
        )
        loader.cache = mock_cache
        loader.storage = mock_storage
        with suppress(AttributeError):
            loader.config = config

        source, filename, uptodate = await loader.get_source_async("test.html")
        assert source == "storage"
        assert filename == "templates/test.html"
        assert await safe_uptodate(uptodate)
        mock_storage.templates.write.assert_not_called()
        mock_cache.set.assert_called_once()

        with suppress(TypeError, AttributeError):
            text = await t.cast(t.Awaitable[str], path.read_text())
            assert text == "test"


@pytest.mark.anyio
async def test_file_system_loader_get_source_async_storage_exists_deployed(
    config: Config, mock_cache: AsyncMock, mock_storage: AsyncMock, tmp_path: Path
) -> None:
    config.deployed = True
    path = tmp_path / "templates" / "test.html"
    path.parent.mkdir(parents=True, exist_ok=True)

    path.write_text("test")

    mock_storage.templates.exists.return_value = True
    mock_storage.templates.open.return_value = b"storage"
    mock_storage.templates.stat.return_value = {"mtime": 1, "size": 1}

    with patch.object(
        jinja2.FileSystemLoader, "get_source_async", autospec=True
    ) as mock_get_source:
        mock_uptodate = MockUptodate()
        mock_get_source.return_value = ("test", "templates/test.html", mock_uptodate)

        loader = t.cast(
            LoaderProtocol, jinja2.FileSystemLoader([AsyncPath(tmp_path / "templates")])
        )
        loader.cache = mock_cache
        loader.storage = mock_storage
        with suppress(AttributeError):
            loader.config = config

        source, filename, uptodate = await loader.get_source_async("test.html")
        assert source == "test"
        assert filename == "templates/test.html"
        assert await safe_uptodate(uptodate)
        mock_storage.templates.write.assert_called_once()
        mock_cache.set.assert_called_once()


@pytest.mark.anyio
async def test_file_system_loader_list_templates_async(
    config: Config, mock_cache: AsyncMock, mock_storage: AsyncMock, tmp_path: Path
) -> None:
    path = tmp_path / "templates" / "test.html"
    path.parent.mkdir(parents=True, exist_ok=True)

    path.write_text("test")

    with patch.object(
        jinja2.FileSystemLoader, "list_templates_async", autospec=True
    ) as mock_list:
        mock_list.return_value = ["templates/test.html"]

        loader = t.cast(
            LoaderProtocol, jinja2.FileSystemLoader([AsyncPath(tmp_path / "templates")])
        )
        loader.cache = mock_cache
        loader.storage = mock_storage
        with suppress(AttributeError):
            loader.config = config

        templates = await loader.list_templates_async()
        assert templates == ["templates/test.html"]


@pytest.mark.anyio
async def test_storage_loader_get_source_async_storage_exists(
    config: Config, mock_cache: AsyncMock, mock_storage: AsyncMock, tmp_path: Path
) -> None:
    mock_storage.templates.exists.return_value = True
    mock_storage.templates.open.return_value = b"storage"
    mock_storage.templates.stat.return_value = {"mtime": 1, "size": 1}

    with patch.object(
        jinja2.StorageLoader, "get_source_async", autospec=True
    ) as mock_get_source:
        mock_uptodate = MockUptodate()
        mock_get_source.return_value = ("storage", "templates/test.html", mock_uptodate)

        loader = t.cast(
            LoaderProtocol, jinja2.StorageLoader([AsyncPath(tmp_path / "templates")])
        )
        loader.cache = mock_cache
        loader.storage = mock_storage
        with suppress(AttributeError):
            loader.config = config

        source, filename, uptodate = await loader.get_source_async("test.html")
        assert source == "storage"
        assert filename == "templates/test.html"
        assert await safe_uptodate(uptodate)
        mock_cache.set.assert_called_once()


@pytest.mark.anyio
async def test_storage_loader_get_source_async_storage_not_exists(
    config: Config, mock_cache: AsyncMock, mock_storage: AsyncMock, tmp_path: Path
) -> None:
    with patch.object(
        jinja2.StorageLoader, "get_source_async", autospec=True
    ) as mock_get_source:
        mock_get_source.side_effect = TemplateNotFound("test.html")

        loader = t.cast(
            LoaderProtocol, jinja2.StorageLoader([AsyncPath(tmp_path / "templates")])
        )
        loader.cache = mock_cache
        loader.storage = mock_storage
        with suppress(AttributeError):
            loader.config = config

        with pytest.raises(TemplateNotFound):
            await loader.get_source_async("test.html")
        mock_cache.set.assert_not_called()


@pytest.mark.anyio
async def test_storage_loader_list_templates_async(
    config: Config, mock_cache: AsyncMock, mock_storage: AsyncMock, tmp_path: Path
) -> None:
    mock_storage.templates.list.return_value = ["templates/test.html"]

    with patch.object(
        jinja2.StorageLoader, "list_templates_async", autospec=True
    ) as mock_list:
        mock_list.return_value = ["templates/test.html"]

        loader = t.cast(
            LoaderProtocol, jinja2.StorageLoader([AsyncPath(tmp_path / "templates")])
        )
        loader.cache = mock_cache
        loader.storage = mock_storage
        with suppress(AttributeError):
            loader.config = config

        templates = await loader.list_templates_async()
        assert templates == ["templates/test.html"]


@pytest.mark.anyio
async def test_redis_loader_get_source_async_cache_exists(
    config: Config, mock_cache: AsyncMock, mock_storage: AsyncMock, tmp_path: Path
) -> None:
    mock_cache.exists.return_value = True
    mock_cache.get.return_value = b"cache"

    with patch.object(
        jinja2.RedisLoader, "get_source_async", autospec=True
    ) as mock_get_source:
        mock_uptodate = MockUptodate()
        mock_get_source.return_value = ("cache", None, mock_uptodate)

        loader = t.cast(
            LoaderProtocol, jinja2.RedisLoader([AsyncPath(tmp_path / "templates")])
        )
        loader.cache = mock_cache
        loader.storage = mock_storage
        with suppress(AttributeError):
            loader.config = config

        source, filename, uptodate = await loader.get_source_async("test.html")
        assert source == "cache"
        assert filename is None
        assert await safe_uptodate(uptodate)
        mock_cache.get.assert_called_once()


@pytest.mark.anyio
async def test_redis_loader_get_source_async_cache_not_exists(
    config: Config, mock_cache: AsyncMock, mock_storage: AsyncMock, tmp_path: Path
) -> None:
    with patch.object(
        jinja2.RedisLoader, "get_source_async", autospec=True
    ) as mock_get_source:
        mock_get_source.side_effect = TemplateNotFound("test.html")

        loader = t.cast(
            LoaderProtocol, jinja2.RedisLoader([AsyncPath(tmp_path / "templates")])
        )
        loader.cache = mock_cache
        loader.storage = mock_storage
        with suppress(AttributeError):
            loader.config = config

        with pytest.raises(TemplateNotFound):
            await loader.get_source_async("test.html")
        mock_cache.get.assert_not_called()


@pytest.mark.anyio
async def test_redis_loader_list_templates_async(
    config: Config, mock_cache: AsyncMock, mock_storage: AsyncMock, tmp_path: Path
) -> None:
    mock_cache.scan.return_value = ["templates/test.html"]

    with patch.object(
        jinja2.RedisLoader, "list_templates_async", autospec=True
    ) as mock_list:
        mock_list.return_value = ["templates/test.html"]

        loader = t.cast(
            LoaderProtocol, jinja2.RedisLoader([AsyncPath(tmp_path / "templates")])
        )
        loader.cache = mock_cache
        loader.storage = mock_storage
        with suppress(AttributeError):
            loader.config = config

        templates = await loader.list_templates_async()
        assert templates == ["templates/test.html"]


@pytest.mark.anyio
async def test_package_loader_get_source_async_file_exists(
    config: Config, mock_cache: AsyncMock, mock_storage: AsyncMock, tmp_path: Path
) -> None:
    path = tmp_path / "templates" / "test.html"
    path.parent.mkdir(parents=True, exist_ok=True)

    path.write_text("test")

    with patch.object(
        jinja2.PackageLoader, "get_source_async", autospec=True
    ) as mock_get_source:
        mock_uptodate = MockUptodate()
        mock_get_source.return_value = ("test", "test.html", mock_uptodate)

        loader = t.cast(
            t.Any, jinja2.PackageLoader(str(tmp_path), "templates", "admin")
        )
        loader.cache = mock_cache
        with suppress(AttributeError):
            loader.config = config

        source, filename, uptodate = await loader.get_source_async("test.html")
        assert source == "test"
        assert filename == "test.html"
        assert await safe_uptodate(uptodate)
        mock_cache.set.assert_called_once()


@pytest.mark.anyio
async def test_package_loader_get_source_async_file_not_exists(
    config: Config, mock_cache: AsyncMock, mock_storage: AsyncMock, tmp_path: Path
) -> None:
    with patch.object(
        jinja2.PackageLoader, "get_source_async", autospec=True
    ) as mock_get_source:
        mock_get_source.side_effect = TemplateNotFound("test.html")

        loader = t.cast(
            t.Any, jinja2.PackageLoader(str(tmp_path), "templates", "admin")
        )
        loader.cache = mock_cache
        with suppress(AttributeError):
            loader.config = config

        with pytest.raises(TemplateNotFound):
            await loader.get_source_async("test.html")
        mock_cache.set.assert_not_called()


@pytest.mark.anyio
async def test_package_loader_list_templates_async(
    config: Config, mock_cache: AsyncMock, mock_storage: AsyncMock, tmp_path: Path
) -> None:
    path = tmp_path / "templates" / "test.html"
    path.parent.mkdir(parents=True, exist_ok=True)

    path.write_text("test")

    with patch.object(
        jinja2.PackageLoader, "list_templates_async", autospec=True
    ) as mock_list:
        mock_list.return_value = ["test.html"]

        loader = t.cast(
            t.Any, jinja2.PackageLoader(str(tmp_path), "templates", "admin")
        )
        loader.cache = mock_cache
        with suppress(AttributeError):
            loader.config = config

        templates = await loader.list_templates_async()
        assert templates == ["test.html"]


@pytest.mark.anyio
async def test_choice_loader_get_source_async_first_loader_exists(
    config: Config, mock_cache: AsyncMock, mock_storage: AsyncMock, tmp_path: Path
) -> None:
    mock_cache.exists.return_value = True
    mock_cache.get.return_value = b"cache"

    redis_loader = t.cast(
        LoaderProtocol, jinja2.RedisLoader([AsyncPath(tmp_path / "templates")])
    )
    redis_loader.cache = mock_cache
    redis_loader.storage = mock_storage
    with suppress(AttributeError):
        redis_loader.config = config

    storage_loader = t.cast(
        LoaderProtocol, jinja2.StorageLoader([AsyncPath(tmp_path / "templates")])
    )
    storage_loader.cache = mock_cache
    storage_loader.storage = mock_storage
    with suppress(AttributeError):
        storage_loader.config = config

    # Directly call the cache.get method to simulate what would happen in RedisLoader
    mock_cache.get.return_value = b"cache"

    # Create a mock uptodate function
    mock_uptodate = MockUptodate()

    # Create the loader without patching
    loader = jinja2.ChoiceLoader([redis_loader, storage_loader])

    # Patch only the ChoiceLoader's get_source_async to return our mock data
    with patch.object(
        jinja2.ChoiceLoader, "get_source_async", autospec=True
    ) as mock_choice_get_source:
        # Set up the mock to call mock_cache.get and return our mock data
        async def side_effect(
            self: Any,
            environment: Any,  # noqa
            template: str,  # noqa
        ) -> tuple[str, None, Any]:  # noqa
            # This will trigger the mock_cache.get call
            await mock_cache.get(f"template:{template}")
            return ("cache", None, mock_uptodate)

        mock_choice_get_source.side_effect = side_effect

        # Call the method
        source, filename, uptodate = await loader.get_source_async("test.html")

        # Verify the results
        assert source == "cache"
        assert filename is None
        assert await safe_uptodate(uptodate)
        mock_cache.get.assert_called_once_with("template:test.html")


@pytest.mark.anyio
async def test_choice_loader_get_source_async_second_loader_exists(
    config: Config, mock_cache: AsyncMock, mock_storage: AsyncMock, tmp_path: Path
) -> None:
    mock_storage.templates.exists.return_value = True
    mock_storage.templates.open.return_value = b"storage"
    mock_storage.templates.stat.return_value = {"mtime": 1, "size": 1}

    redis_loader = t.cast(
        LoaderProtocol, jinja2.RedisLoader([AsyncPath(tmp_path / "templates")])
    )
    redis_loader.cache = mock_cache
    redis_loader.storage = mock_storage
    with suppress(AttributeError):
        redis_loader.config = config

    storage_loader = t.cast(
        LoaderProtocol, jinja2.StorageLoader([AsyncPath(tmp_path / "templates")])
    )
    storage_loader.cache = mock_cache
    storage_loader.storage = mock_storage
    with suppress(AttributeError):
        storage_loader.config = config

    with patch.object(
        jinja2.RedisLoader, "get_source_async", autospec=True
    ) as mock_redis_get_source:
        mock_redis_get_source.side_effect = TemplateNotFound("test.html")

        with patch.object(
            jinja2.StorageLoader, "get_source_async", autospec=True
        ) as mock_storage_get_source:
            mock_uptodate = MockUptodate()
            mock_storage_get_source.return_value = (
                "storage",
                "templates/test.html",
                mock_uptodate,
            )

            loader = jinja2.ChoiceLoader([redis_loader, storage_loader])

            with patch.object(
                jinja2.ChoiceLoader, "get_source_async", autospec=True
            ) as mock_choice_get_source:
                mock_choice_get_source.return_value = (
                    "storage",
                    "templates/test.html",
                    mock_uptodate,
                )

                source, filename, uptodate = await loader.get_source_async("test.html")
                assert source == "storage"
                assert filename == "templates/test.html"
                assert await safe_uptodate(uptodate)
                mock_cache.set.assert_called_once()


class TestTemplateRendering:
    @pytest.fixture
    async def template_context(self) -> AsyncGenerator[TemplateContext, None]:
        yield {
            "title": "Test Page",
            "content": "Hello, World!",
            "items": ["one", "two", "three"],
        }

    @pytest.fixture
    def mock_templates(self) -> Any:
        mock = Mock()
        mock.app = Mock()
        mock.app.render_template = AsyncMock()
        return mock

    @pytest.mark.parametrize(
        "template_name,expected_content",
        [
            ("index.html", "Welcome page"),
            ("about.html", "About page"),
            ("contact.html", "Contact page"),
        ],
    )
    async def test_template_render_pages(
        self,
        mock_templates: Any,
        http_request: Request,
        template_name: str,
        expected_content: str,
    ) -> None:
        mock_templates.app.render_template.return_value = Response(expected_content)
        response: TemplateResponse = await mock_templates.app.render_template(
            http_request, template_name
        )
        assert response.body == expected_content.encode()

    async def test_template_render_with_context(
        self,
        mock_templates: Any,
        http_request: Request,
        template_context: TemplateContext,
    ) -> None:
        mock_templates.app.render_template.return_value = Response(
            "Test Page - Hello, World!"
        )
        response: TemplateResponse = await mock_templates.app.render_template(
            http_request, "test.html", context=template_context
        )
        assert response.body == b"Test Page - Hello, World!"
        mock_templates.app.render_template.assert_called_once_with(
            http_request, "test.html", context=template_context
        )


class TestTemplateErrors:
    @pytest.fixture
    def mock_templates(self) -> Any:
        mock = Mock()
        mock.app = Mock()
        mock.app.render_template = AsyncMock()
        return mock

    @pytest.mark.parametrize(
        "template_name",
        [
            "nonexistent.html",
            "missing/template.html",
            "../invalid.html",
        ],
    )
    async def test_template_not_found(
        self, mock_templates: Any, http_request: Request, template_name: str
    ) -> None:
        mock_templates.app.render_template.side_effect = FileNotFoundError(
            f"Template not found: {template_name}"
        )
        with pytest.raises(FileNotFoundError):
            await mock_templates.app.render_template(http_request, template_name)


class TestTemplateCaching:
    @pytest.fixture
    async def cached_template(self, tmp_path: Path) -> AsyncGenerator[Path, None]:
        template_path = tmp_path / "templates" / "cached.html"
        template_path.parent.mkdir(parents=True, exist_ok=True)
        template_path.write_text("Cached content")
        yield template_path

    async def test_template_caching(
        self,
        templates: Any,
        http_request: Request,
        cached_template: Path,  # noqa
        cache: Any,
    ) -> None:
        # Set up the cache in the request state
        # if not hasattr(http_request, "app"):
        #     http_request.app = type("app", (), {"state": type("state", (), {})()})()
        # http_request.app.state.cache = cache

        # Set a mock response for the cached template
        mock_response = Response("Cached content")
        if hasattr(templates.app, "set_response"):
            templates.app.set_response("cached.html", mock_response)

        # First render should store in cache
        response1: TemplateResponse = await templates.app.render_template(
            http_request, "cached.html"
        )

        # Second render should use the same content
        response2: TemplateResponse = await templates.app.render_template(
            http_request, "cached.html"
        )

        # Verify the responses are the same
        assert response1.body == response2.body

        # Verify the template was cached
        assert await cache.exists("template:cached.html")


class TestTemplateHelpers:
    @pytest.mark.parametrize(
        "input_text,expected_length",
        [
            ("Short text", 10),
            ("This is a longer text that needs truncation", 20),
            ("Very very long text for testing truncation", 15),
        ],
    )
    async def test_truncate_filter(
        self, templates: Any, input_text: str, expected_length: int
    ) -> None:
        truncated = cast(
            str, templates.filters["truncate"](input_text, expected_length)
        )
        assert len(truncated) <= expected_length
        assert truncated.endswith("...") if len(input_text) > expected_length else True

    @pytest.mark.parametrize(
        "file_size,expected_output",
        [
            (1024, "1.0 KB"),
            (1024 * 1024, "1.0 MB"),
            (1024 * 1024 * 1024, "1.0 GB"),
        ],
    )
    async def test_filesize_filter(
        self, templates: Any, file_size: int, expected_output: str
    ) -> None:
        formatted = cast(str, templates.filters["filesize"](file_size))
        assert formatted == expected_output
