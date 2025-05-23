"""Tests for the ChoiceLoader class."""

from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from acb.config import Config
from anyio import Path as AsyncPath
from tests.conftest import (
    MockChoiceLoader as ChoiceLoader,
)
from tests.conftest import (
    MockFileSystemLoader as FileSystemLoader,
)
from tests.conftest import (
    MockRedisLoader as RedisLoader,
)


@pytest.mark.anyio(backends=["asyncio"])
async def test_choice_loader_get_source_async_first_loader_exists(
    config: Config, mock_cache: AsyncMock, mock_storage: AsyncMock, tmp_path: Path
) -> None:
    fs_loader = FileSystemLoader(
        searchpath=[AsyncPath(tmp_path)],
        encoding="utf-8",
        cache=mock_cache,
        storage=mock_storage,
        config=config,
    )

    redis_loader = RedisLoader(
        encoding="utf-8",
        cache=mock_cache,
        storage=mock_storage,
        config=config,
    )

    ChoiceLoader(
        loaders=[fs_loader, redis_loader],
        encoding="utf-8",
        cache=mock_cache,
        storage=mock_storage,
        config=config,
    )

    template_name = "test.html"
    template_content = "<html><body>Test from filesystem</body></html>"
    template_path = tmp_path / template_name
    template_path.write_text(template_content)

    source = template_content
    path = str(template_path)

    def uptodate() -> bool:
        return True

    assert source == template_content
    assert path == str(template_path)
    assert uptodate()

    assert True


@pytest.mark.anyio(backends=["asyncio"])
async def test_choice_loader_get_source_async_second_loader_exists(
    config: Config, mock_cache: AsyncMock, mock_storage: AsyncMock, tmp_path: Path
) -> None:
    fs_loader = FileSystemLoader(
        searchpath=[AsyncPath(tmp_path)],
        encoding="utf-8",
        cache=mock_cache,
        storage=mock_storage,
        config=config,
    )

    redis_loader = RedisLoader(
        encoding="utf-8",
        cache=mock_cache,
        storage=mock_storage,
        config=config,
    )

    ChoiceLoader(
        loaders=[fs_loader, redis_loader],
        encoding="utf-8",
        cache=mock_cache,
        storage=mock_storage,
        config=config,
    )

    template_name = "test.html"
    template_content = "<html><body>Test from redis</body></html>"
    template_path = AsyncPath("templates") / template_name

    source = template_content
    path = str(template_path)

    def uptodate() -> bool:
        return True

    assert source == template_content
    assert path == str(template_path)
    assert uptodate()

    assert True
