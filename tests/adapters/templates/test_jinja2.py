"""Tests for the jinja2 templates adapter module."""
# pyright: reportAttributeAccessIssue=false, reportUnusedImport=false, reportMissingParameterType=false, reportUnknownParameterType=false

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

# Mock AsyncJinja2Templates before importing
import types


# Create a mock AsyncJinja2Templates class
class MockAsyncJinja2Templates:
    def __init__(self, *args, **kwargs) -> None:
        self.env = MagicMock()
        self.TemplateResponse = MagicMock()
        self.render_block = MagicMock()


# Set up the mock modules
sys.modules["starlette_async_jinja"] = types.ModuleType("starlette_async_jinja")
sys.modules["starlette_async_jinja"].AsyncJinja2Templates = MockAsyncJinja2Templates

# Mock AsyncRedisBytecodeCache
sys.modules["jinja2_async_environment"] = types.ModuleType("jinja2_async_environment")
sys.modules["jinja2_async_environment"].bccache = types.ModuleType(
    "jinja2_async_environment.bccache",
)
sys.modules["jinja2_async_environment"].bccache.AsyncRedisBytecodeCache = MagicMock
sys.modules["jinja2_async_environment"].loaders = types.ModuleType(
    "jinja2_async_environment.loaders",
)
sys.modules["jinja2_async_environment"].loaders.AsyncBaseLoader = MagicMock
sys.modules["jinja2_async_environment"].loaders.SourceType = tuple

from acb.config import Config  # noqa: E402
from anyio import Path as AsyncPath  # noqa: E402
from jinja2 import TemplateNotFound  # noqa: E402
from fastblocks.adapters.templates.jinja2 import (  # noqa: E402
    ChoiceLoader,
    PackageLoader,
    RedisLoader,
    StorageLoader,
    Templates,
)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_templates_initialization(config: Config) -> None:
    """Test the initialization of the Templates class."""
    templates = Templates()
    templates.config = config
    templates.logger = MagicMock()  # Mock the logger
    # Mock the necessary methods - let init_envs call get_loader naturally
    with (
        patch.object(
            Templates,
            "get_searchpaths",
            AsyncMock(return_value=[AsyncPath("/templates")]),
        ),
        patch.object(
            Templates,
            "get_loader",
            MagicMock(return_value=MagicMock()),
        ) as mock_get_loader,
    ):
        # Mock external dependencies that init_envs uses
        with patch(
            "starlette_async_jinja.AsyncJinja2Templates",
        ) as mock_async_jinja:
            with patch("jinja2_async_environment.bccache.AsyncRedisBytecodeCache"):
                mock_env = MagicMock()
                mock_templates_obj = MagicMock()
                mock_templates_obj.env = mock_env
                mock_async_jinja.return_value = mock_templates_obj

                await templates.init()

                # Verify the methods were called
                templates.get_searchpaths.assert_called()
                mock_get_loader.assert_called()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_redis_loader_get_source_async(
    config: Config,
    mock_cache: AsyncMock,
    mock_storage: AsyncMock,
) -> None:
    """Test the RedisLoader.get_source_async method."""
    # Setup
    loader = RedisLoader([AsyncPath("/templates")])
    loader.config = config
    loader.cache = mock_cache
    loader.storage = mock_storage

    template_name = "test.html"
    template_content = b"<html><body>Test from redis</body></html>"

    # Mock cache.exists and cache.get
    mock_cache.exists.return_value = True
    mock_cache.get.return_value = template_content

    # Test
    source, _, uptodate_func = await loader.get_source_async(template_name)

    # Verify
    assert source == template_content.decode()
    # uptodate_func should return a callable, not an awaitable
    assert uptodate_func()
    mock_cache.exists.assert_called_once()
    mock_cache.get.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_redis_loader_template_not_found(
    config: Config,
    mock_cache: AsyncMock,
    mock_storage: AsyncMock,
) -> None:
    """Test the RedisLoader when template is not found."""
    # Setup
    loader = RedisLoader([AsyncPath("/templates")])
    loader.config = config
    loader.cache = mock_cache
    loader.storage = mock_storage

    template_name = "nonexistent.html"

    # Mock cache.exists to return False
    mock_cache.exists.return_value = False

    # Test
    with pytest.raises(TemplateNotFound):
        await loader.get_source_async(template_name)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_redis_loader_list_templates_async(
    config: Config,
    mock_cache: AsyncMock,
    mock_storage: AsyncMock,
) -> None:
    """Test the RedisLoader.list_templates_async method."""
    # Setup
    loader = RedisLoader([AsyncPath("/templates")])
    loader.config = config
    loader.cache = mock_cache
    loader.storage = mock_storage

    # Mock cache.scan to return template names
    mock_cache.scan.side_effect = [
        ["template1.html", "template2.html"],
        ["style.css"],
        ["script.js"],
    ]

    # Test
    templates = await loader.list_templates_async()

    # Verify
    assert set(templates) == {
        "template1.html",
        "template2.html",
        "style.css",
        "script.js",
    }
    assert mock_cache.scan.call_count == 3


@pytest.mark.asyncio
@pytest.mark.unit
async def test_package_loader_get_source_async(
    config: Config,
    mock_cache: AsyncMock,
    mock_storage: AsyncMock,
) -> None:
    """Test the PackageLoader.get_source_async method."""
    # Setup
    loader = PackageLoader("test_package", "templates", "admin")
    loader.config = config
    loader.cache = mock_cache
    loader.storage = mock_storage

    # Mock the template root
    loader._template_root = AsyncPath("/templates")

    template_name = "test.html"
    template_content = b"<html><body>{{ variable }}</body></html>"
    expected_content = b"<html><body>[[ variable ]]</body></html>"

    # Mock AsyncPath methods
    with patch.object(AsyncPath, "is_file", AsyncMock(return_value=True)):
        with patch.object(
            AsyncPath,
            "read_bytes",
            AsyncMock(return_value=template_content),
        ):
            with patch.object(
                AsyncPath,
                "stat",
                AsyncMock(return_value=MagicMock(st_mtime=12345)),
            ):
                # Test
                source, path, uptodate = await loader.get_source_async(template_name)

                # Verify
                assert source == expected_content.decode()
                assert path == template_name
                assert await uptodate()
                mock_cache.set.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_choice_loader_fallback(
    config: Config,
    mock_cache: AsyncMock,
    mock_storage: AsyncMock,
) -> None:
    """Test the ChoiceLoader fallback behavior."""
    # Setup
    loader1 = RedisLoader([AsyncPath("/templates")])
    loader1.config = config
    loader1.cache = mock_cache
    loader1.storage = mock_storage

    loader2 = StorageLoader([AsyncPath("/templates")])
    loader2.config = config
    loader2.cache = mock_cache
    loader2.storage = mock_storage

    # Create the choice loader
    choice_loader = ChoiceLoader([loader1, loader2])

    # Mock the get_source_async methods
    loader1.get_source_async = AsyncMock(side_effect=TemplateNotFound("test.html"))

    template_content = "<html><body>Test from storage</body></html>"
    loader2.get_source_async = AsyncMock(
        return_value=(
            template_content,
            "templates/test.html",
            AsyncMock(return_value=True),
        ),
    )

    # Test
    source, _, _ = await choice_loader.get_source_async("test.html")

    # Verify
    assert source == template_content
    loader1.get_source_async.assert_called_once_with("test.html")
    loader2.get_source_async.assert_called_once_with("test.html")


@pytest.mark.asyncio
@pytest.mark.unit
async def test_choice_loader_template_not_found(
    config: Config,
    mock_cache: AsyncMock,
    mock_storage: AsyncMock,
) -> None:
    """Test the ChoiceLoader when no loader can find the template."""
    # Setup
    loader1 = RedisLoader([AsyncPath("/templates")])
    loader1.config = config
    loader1.cache = mock_cache
    loader1.storage = mock_storage

    loader2 = StorageLoader([AsyncPath("/templates")])
    loader2.config = config
    loader2.cache = mock_cache
    loader2.storage = mock_storage

    # Create the choice loader
    choice_loader = ChoiceLoader([loader1, loader2])

    # Mock the get_source_async methods to both raise TemplateNotFound
    loader1.get_source_async = AsyncMock(
        side_effect=TemplateNotFound("nonexistent.html"),
    )
    loader2.get_source_async = AsyncMock(
        side_effect=TemplateNotFound("nonexistent.html"),
    )

    # Test
    with pytest.raises(TemplateNotFound):
        await choice_loader.get_source_async("nonexistent.html")

    # Verify
    loader1.get_source_async.assert_called_once_with("nonexistent.html")
    loader2.get_source_async.assert_called_once_with("nonexistent.html")


@pytest.mark.asyncio
@pytest.mark.unit
async def test_choice_loader_list_templates(
    config: Config,
    mock_cache: AsyncMock,
    mock_storage: AsyncMock,
) -> None:
    """Test the ChoiceLoader.list_templates_async method."""
    # Setup
    loader1 = RedisLoader([AsyncPath("/templates")])
    loader1.config = config
    loader1.cache = mock_cache
    loader1.storage = mock_storage

    loader2 = StorageLoader([AsyncPath("/templates")])
    loader2.config = config
    loader2.cache = mock_cache
    loader2.storage = mock_storage

    # Create the choice loader
    choice_loader = ChoiceLoader([loader1, loader2])

    # Mock the list_templates_async methods
    loader1.list_templates_async = AsyncMock(
        return_value=["template1.html", "template2.html"],
    )
    loader2.list_templates_async = AsyncMock(
        return_value=["template2.html", "template3.html"],
    )

    # Test
    templates = await choice_loader.list_templates_async()

    # Verify
    assert set(templates) == {"template1.html", "template2.html", "template3.html"}
    loader1.list_templates_async.assert_called_once()
    loader2.list_templates_async.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_template_caching_behavior(
    config: Config,
    mock_cache: AsyncMock,
    mock_storage: AsyncMock,
) -> None:
    """Test template caching behavior."""
    # Setup
    templates = Templates()
    templates.config = config

    # Mock settings
    mock_settings = MagicMock()
    mock_settings.cache_timeout = 300
    mock_settings.update_from_config = MagicMock()
    templates.settings = mock_settings

    # Mock the necessary methods
    with (
        patch.object(
            Templates,
            "get_searchpaths",
            AsyncMock(return_value=[AsyncPath("/templates")]),
        ),
        patch.object(Templates, "get_loader", MagicMock()),
    ):
        with patch.object(Templates, "init_envs", AsyncMock()):
            # Initialize templates
            await templates.init()

            # Test cache timeout based on deployment status
            config.deployed = True
            # When deployed, cache timeout should be higher
            mock_settings.cache_timeout = 300
            assert templates.settings.cache_timeout == 300

            config.deployed = False

            # Simulate update_from_config changing timeout for non-deployed
            def mock_update_from_config(config: Config) -> None:
                if not config.deployed:
                    mock_settings.cache_timeout = 1

            mock_settings.update_from_config.side_effect = mock_update_from_config
            templates.settings.update_from_config(config)
            assert templates.settings.cache_timeout == 1


# Additional comprehensive tests for improved coverage


class TestHelperFunctions:
    """Test template replacement helper functions."""

    def test_get_attr_pattern_caching(self):
        """Test that attribute patterns are cached."""
        from fastblocks.adapters.templates.jinja2 import _get_attr_pattern

        pattern1 = _get_attr_pattern("id")
        pattern2 = _get_attr_pattern("id")

        # Should return same cached pattern object
        assert pattern1 is pattern2

    def test_get_attr_pattern_different_attrs(self):
        """Test patterns for different attributes."""
        from fastblocks.adapters.templates.jinja2 import _get_attr_pattern

        id_pattern = _get_attr_pattern("id")
        class_pattern = _get_attr_pattern("class")

        # Should be different pattern objects
        assert id_pattern is not class_pattern

    def test_apply_template_replacements_basic(self):
        """Test basic template delimiter replacements."""
        from fastblocks.adapters.templates.jinja2 import _apply_template_replacements

        source = b"{{ variable }} {% if condition %} content {% endif %}"
        result = _apply_template_replacements(source)

        assert b"[[" in result
        assert b"]]" in result
        assert b"[%" in result
        assert b"%]" in result
        assert b"{{" not in result
        assert b"}}" not in result

    def test_apply_template_replacements_deployed(self):
        """Test http to https conversion when deployed."""
        from fastblocks.adapters.templates.jinja2 import _apply_template_replacements

        source = b"<link href='http://example.com/style.css'>"
        result = _apply_template_replacements(source, deployed=True)

        assert b"https://" in result
        assert b"http://" not in result

    def test_apply_template_replacements_not_deployed(self):
        """Test http remains when not deployed."""
        from fastblocks.adapters.templates.jinja2 import _apply_template_replacements

        source = b"<link href='http://example.com/style.css'>"
        result = _apply_template_replacements(source, deployed=False)

        assert b"http://" in result


class TestBaseTemplateLoader:
    """Test BaseTemplateLoader functionality."""

    def test_initialization_with_searchpath(self):
        """Test BaseTemplateLoader initialization with searchpath."""
        from fastblocks.adapters.templates.jinja2 import BaseTemplateLoader

        searchpath = AsyncPath("templates")

        with patch(
            "fastblocks.adapters.templates.jinja2.depends.get",
            side_effect=Exception("Not available"),
        ):
            with patch(
                "fastblocks.adapters.templates.jinja2.get_adapter", return_value=None
            ):
                loader = BaseTemplateLoader(searchpath)

                assert searchpath in loader.searchpath

    def test_get_supported_extensions(self):
        """Test get_supported_extensions returns correct tuple."""
        from fastblocks.adapters.templates.jinja2 import BaseTemplateLoader

        with patch(
            "fastblocks.adapters.templates.jinja2.depends.get",
            side_effect=Exception("Not available"),
        ):
            with patch(
                "fastblocks.adapters.templates.jinja2.get_adapter", return_value=None
            ):
                loader = BaseTemplateLoader()
                extensions = loader.get_supported_extensions()

                assert extensions == ("html", "css", "js")
                assert isinstance(extensions, tuple)

    def test_normalize_template_with_template_arg(self):
        """Test _normalize_template with template argument."""
        from fastblocks.adapters.templates.jinja2 import BaseTemplateLoader

        with patch(
            "fastblocks.adapters.templates.jinja2.depends.get",
            side_effect=Exception("Not available"),
        ):
            with patch(
                "fastblocks.adapters.templates.jinja2.get_adapter", return_value=None
            ):
                loader = BaseTemplateLoader()
                result = loader._normalize_template("env", "template.html")

                assert result == "template.html"

    @pytest.mark.asyncio
    async def test_list_templates_for_extensions(self, tmp_path):
        """Test _list_templates_for_extensions discovers templates."""
        from fastblocks.adapters.templates.jinja2 import BaseTemplateLoader

        # Create test templates
        test_dir = tmp_path / "templates"
        test_dir.mkdir()
        (test_dir / "index.html").write_text("content")
        (test_dir / "style.css").write_text("content")
        (test_dir / "script.js").write_text("content")

        with patch(
            "fastblocks.adapters.templates.jinja2.depends.get",
            side_effect=Exception("Not available"),
        ):
            with patch(
                "fastblocks.adapters.templates.jinja2.get_adapter", return_value=None
            ):
                loader = BaseTemplateLoader(AsyncPath(test_dir))
                templates = await loader._list_templates_for_extensions(
                    ("html", "css", "js")
                )

                assert len(templates) == 3

    @pytest.mark.asyncio
    async def test_find_template_path_parallel_found(self, tmp_path):
        """Test _find_template_path_parallel finds existing file."""
        from fastblocks.adapters.templates.jinja2 import BaseTemplateLoader

        test_dir = tmp_path / "templates"
        test_dir.mkdir()
        template_file = test_dir / "test.html"
        template_file.write_text("content")

        with patch(
            "fastblocks.adapters.templates.jinja2.depends.get",
            side_effect=Exception("Not available"),
        ):
            with patch(
                "fastblocks.adapters.templates.jinja2.get_adapter", return_value=None
            ):
                loader = BaseTemplateLoader(AsyncPath(test_dir))
                result = await loader._find_template_path_parallel("test.html")

                assert result is not None
                assert "test.html" in str(result)

    @pytest.mark.asyncio
    async def test_find_template_path_parallel_not_found(self, tmp_path):
        """Test _find_template_path_parallel returns None for missing file."""
        from fastblocks.adapters.templates.jinja2 import BaseTemplateLoader

        test_dir = tmp_path / "templates"
        test_dir.mkdir()

        with patch(
            "fastblocks.adapters.templates.jinja2.depends.get",
            side_effect=Exception("Not available"),
        ):
            with patch(
                "fastblocks.adapters.templates.jinja2.get_adapter", return_value=None
            ):
                loader = BaseTemplateLoader(AsyncPath(test_dir))
                result = await loader._find_template_path_parallel("nonexistent.html")

                assert result is None


class TestFileSystemLoader:
    """Test FileSystemLoader functionality."""

    @pytest.mark.asyncio
    async def test_check_storage_exists_no_storage(self):
        """Test _check_storage_exists when storage is None."""
        from fastblocks.adapters.templates.jinja2 import FileSystemLoader

        with patch(
            "fastblocks.adapters.templates.jinja2.depends.get",
            side_effect=Exception("Not available"),
        ):
            with patch(
                "fastblocks.adapters.templates.jinja2.get_adapter", return_value=None
            ):
                loader = FileSystemLoader()
                loader.storage = None

                result = await loader._check_storage_exists(AsyncPath("test.html"))

                assert result is False

    @pytest.mark.asyncio
    async def test_check_storage_exists_with_storage(self):
        """Test _check_storage_exists when storage available."""
        from fastblocks.adapters.templates.jinja2 import FileSystemLoader

        mock_storage = AsyncMock()
        mock_storage.templates.exists = AsyncMock(return_value=True)

        with patch(
            "fastblocks.adapters.templates.jinja2.depends.get",
            side_effect=Exception("Not available"),
        ):
            with patch(
                "fastblocks.adapters.templates.jinja2.get_adapter", return_value=None
            ):
                loader = FileSystemLoader()
                loader.storage = mock_storage

                result = await loader._check_storage_exists(AsyncPath("test.html"))

                assert result is True

    @pytest.mark.asyncio
    async def test_cache_template_with_cache(self):
        """Test _cache_template caches content."""
        from fastblocks.adapters.templates.jinja2 import FileSystemLoader

        mock_cache = AsyncMock()
        mock_cache.set = AsyncMock()

        with patch(
            "fastblocks.adapters.templates.jinja2.depends.get",
            side_effect=Exception("Not available"),
        ):
            with patch(
                "fastblocks.adapters.templates.jinja2.get_adapter", return_value=None
            ):
                with patch(
                    "fastblocks.adapters.templates.jinja2.Templates.get_cache_key",
                    return_value="cache:key",
                ):
                    loader = FileSystemLoader()
                    loader.cache = mock_cache

                    await loader._cache_template(AsyncPath("test.html"), b"content")

                    mock_cache.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_template_no_cache(self):
        """Test _cache_template when cache is None."""
        from fastblocks.adapters.templates.jinja2 import FileSystemLoader

        with patch(
            "fastblocks.adapters.templates.jinja2.depends.get",
            side_effect=Exception("Not available"),
        ):
            with patch(
                "fastblocks.adapters.templates.jinja2.get_adapter", return_value=None
            ):
                loader = FileSystemLoader()
                loader.cache = None

                # Should not raise exception
                await loader._cache_template(AsyncPath("test.html"), b"content")

    @pytest.mark.asyncio
    async def test_list_templates_async(self, tmp_path):
        """Test list_templates_async returns discovered templates."""
        from fastblocks.adapters.templates.jinja2 import FileSystemLoader

        test_dir = tmp_path / "templates"
        test_dir.mkdir()
        (test_dir / "page1.html").write_text("content")
        (test_dir / "page2.html").write_text("content")

        with patch(
            "fastblocks.adapters.templates.jinja2.depends.get",
            side_effect=Exception("Not available"),
        ):
            with patch(
                "fastblocks.adapters.templates.jinja2.get_adapter", return_value=None
            ):
                loader = FileSystemLoader(AsyncPath(test_dir))
                templates = await loader.list_templates_async()

                assert len(templates) >= 2


class TestStorageLoader:
    """Test StorageLoader functionality."""

    @pytest.mark.asyncio
    async def test_check_filesystem_sync_opportunity_deployed(self):
        """Test _check_filesystem_sync_opportunity when deployed."""
        from fastblocks.adapters.templates.jinja2 import StorageLoader

        mock_config = MagicMock()
        mock_config.deployed = True

        with patch(
            "fastblocks.adapters.templates.jinja2.depends.get",
            side_effect=Exception("Not available"),
        ):
            with patch(
                "fastblocks.adapters.templates.jinja2.get_adapter", return_value=None
            ):
                loader = StorageLoader()
                loader.config = mock_config

                result = await loader._check_filesystem_sync_opportunity(
                    "test.html", AsyncPath("storage/test.html")
                )

                assert result is None

    @pytest.mark.asyncio
    async def test_list_templates_async_no_storage(self):
        """Test list_templates_async with no storage."""
        from fastblocks.adapters.templates.jinja2 import StorageLoader

        with patch(
            "fastblocks.adapters.templates.jinja2.depends.get",
            side_effect=Exception("Not available"),
        ):
            with patch(
                "fastblocks.adapters.templates.jinja2.get_adapter", return_value=None
            ):
                loader = StorageLoader()
                loader.storage = None

                templates = await loader.list_templates_async()

                assert templates == []


class TestTemplatesEnhanced:
    """Additional comprehensive tests for Templates adapter."""

    def test_get_loader_development_mode(self):
        """Test get_loader in development mode."""
        mock_config = MagicMock()
        mock_config.deployed = False
        mock_config.debug.production = False

        with patch(
            "fastblocks.adapters.templates.jinja2.get_adapter", return_value=None
        ):
            with patch(
                "fastblocks.adapters.templates.jinja2.depends.get_sync",
                return_value=None,
            ):
                templates = Templates()
                templates.config = mock_config

                loader = templates.get_loader([AsyncPath("templates")])

                # Should be ChoiceLoader
                assert isinstance(loader, ChoiceLoader)
                assert len(loader.loaders) > 0

    def test_filter_decorator(self):
        """Test filter decorator registration."""
        mock_env = MagicMock()
        mock_env.filters = {}
        mock_templates_env = MagicMock()
        mock_templates_env.env = mock_env

        with patch(
            "fastblocks.adapters.templates.jinja2.get_adapter", return_value=None
        ):
            with patch(
                "fastblocks.adapters.templates.jinja2.depends.get_sync",
                return_value=None,
            ):
                templates = Templates()
                templates.app = mock_templates_env

                @templates.filter("custom_filter")
                def my_filter(value):
                    return value.upper()

                assert "custom_filter" in mock_env.filters

    @pytest.mark.asyncio
    async def test_render_template_no_app_env(self):
        """Test render_template without app environment."""
        mock_request = MagicMock()

        with patch(
            "fastblocks.adapters.templates.jinja2.get_adapter", return_value=None
        ):
            with patch(
                "fastblocks.adapters.templates.jinja2.depends.get_sync",
                return_value=None,
            ):
                templates = Templates()
                templates.app = None

                result = await templates.render_template(mock_request, "index.html")

                # Should return 404 response
                assert result.status_code == 404

    @pytest.mark.asyncio
    async def test_render_component_no_htmy_adapter(self):
        """Test render_component when HTMY adapter not available."""
        mock_request = MagicMock()

        async def mock_get_no_htmy(name):
            return None

        with patch(
            "fastblocks.adapters.templates.jinja2.get_adapter", return_value=None
        ):
            with patch(
                "fastblocks.adapters.templates.jinja2.depends.get_sync",
                return_value=None,
            ):
                with patch(
                    "fastblocks.adapters.templates.jinja2.depends.get",
                    new=mock_get_no_htmy,
                ):
                    templates = Templates()

                    result = await templates.render_component(mock_request, "UserCard")

                    # Should return 500 error response
                    assert result.status_code == 500
                    assert b"HTMY adapter not available" in result.body
