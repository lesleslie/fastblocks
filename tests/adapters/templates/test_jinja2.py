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
    assert await uptodate_func()
    mock_cache.exists.assert_called_once()
    mock_cache.get.assert_called_once()


@pytest.mark.asyncio
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
    loader1.get_source_async.assert_called_once_with("test.html", "test.html")
    loader2.get_source_async.assert_called_once_with("test.html", "test.html")


@pytest.mark.asyncio
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
    loader1.get_source_async.assert_called_once_with(
        "nonexistent.html", "nonexistent.html"
    )
    loader2.get_source_async.assert_called_once_with(
        "nonexistent.html", "nonexistent.html"
    )


@pytest.mark.asyncio
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
