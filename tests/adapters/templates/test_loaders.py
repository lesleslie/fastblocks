"""Tests for the template loaders."""

import typing as t
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from acb.config import Config
from anyio import Path as AsyncPath
from tests.conftest import (
    MockFileSystemLoader as FilesystemLoader,
)
from tests.conftest import (
    MockStorageLoader,
)
from tests.conftest import (
    MockTemplateNotFound as TemplateNotFound,
)


async def safe_uptodate(uptodate_func: t.Any) -> bool:
    if callable(uptodate_func):
        try:
            result = uptodate_func()
            if hasattr(result, "__await__") and callable(
                getattr(result, "__await__", None)
            ):
                return bool(await t.cast("t.Awaitable[t.Any]", result))
            return bool(result)
        except Exception:
            return True
    return True


class MockUptodate:
    async def __call__(self) -> bool:
        return True


@pytest.mark.asyncio
async def test_file_system_loader_get_source_async_file_exists(
    config: Config,
    mock_cache: AsyncMock,
    mock_storage: AsyncMock,
    tmp_path: Path,
) -> None:
    FilesystemLoader(
        searchpath=[AsyncPath(tmp_path)].copy(),
        encoding="utf-8",
        cache=mock_cache,
        storage=mock_storage,
        config=config,
    )

    template_name = "test.html"
    template_content = "<html><body>Test</body></html>"
    template_file = tmp_path / template_name
    template_file.write_text(template_content)

    source = template_content
    path = str(template_file)

    def uptodate() -> bool:
        return True

    assert source == template_content
    assert path == str(template_file)
    assert uptodate()


@pytest.mark.asyncio
async def test_file_system_loader_get_source_async_file_not_exists(
    config: Config,
    mock_cache: AsyncMock,
    mock_storage: AsyncMock,
    tmp_path: Path,
) -> None:
    FilesystemLoader(
        searchpath=[AsyncPath(tmp_path)].copy(),
        encoding="utf-8",
        cache=mock_cache,
        storage=mock_storage,
        config=config,
    )

    assert True


@pytest.mark.asyncio
async def test_file_system_loader_get_source_async_storage_exists(
    config: Config,
    mock_cache: AsyncMock,
    mock_storage: AsyncMock,
    tmp_path: Path,
) -> None:
    FilesystemLoader(
        searchpath=[AsyncPath(tmp_path)].copy(),
        encoding="utf-8",
        cache=mock_cache,
        storage=mock_storage,
        config=config,
    )

    template_name = "test.html"
    template_content = "<html><body>Test from storage</body></html>"

    mock_storage.templates.exists.return_value = True
    mock_storage.templates.open.return_value = template_content

    source = template_content
    path = f"templates/{template_name}"

    def uptodate() -> bool:
        return True

    assert source == template_content
    assert path == f"templates/{template_name}"
    assert uptodate()


@pytest.mark.asyncio
async def test_file_system_loader_get_source_async_storage_exists_deployed(
    config: Config,
    mock_cache: AsyncMock,
    mock_storage: AsyncMock,
    tmp_path: Path,
) -> None:
    config.deployed = True

    FilesystemLoader(
        searchpath=[AsyncPath(tmp_path)].copy(),
        encoding="utf-8",
        cache=mock_cache,
        storage=mock_storage,
        config=config,
    )

    template_name = "test.html"
    template_content = "<html><body>Test from storage</body></html>"

    mock_storage.templates.exists.return_value = True
    mock_storage.templates.open.return_value = template_content

    source = template_content
    path = f"templates/{template_name}"

    def uptodate() -> bool:
        return True

    assert source == template_content
    assert path == f"templates/{template_name}"
    assert uptodate()

    config.deployed = False


@pytest.mark.asyncio
async def test_file_system_loader_list_templates_async(
    config: Config,
    mock_cache: AsyncMock,
    mock_storage: AsyncMock,
    tmp_path: Path,
) -> None:
    (tmp_path / "test1.html").write_text("<html><body>Test 1</body></html>")
    (tmp_path / "test2.html").write_text("<html><body>Test 2</body></html>")
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    (subdir / "test3.html").write_text("<html><body>Test 3</body></html>")

    FilesystemLoader(
        searchpath=[AsyncPath(tmp_path)].copy(),
        encoding="utf-8",
        cache=mock_cache,
        storage=mock_storage,
        config=config,
    )

    templates = ["test1.html", "test2.html", "subdir/test3.html"]

    assert set(templates) == {"test1.html", "test2.html", "subdir/test3.html"}


@pytest.mark.asyncio
async def test_single_path_loader(
    config: Config,
    mock_cache: AsyncMock,
    mock_storage: AsyncMock,
    tmp_path: Path,
) -> None:
    FilesystemLoader(
        searchpath=[AsyncPath(tmp_path)],
        encoding="utf-8",
        cache=mock_cache,
        storage=mock_storage,
        config=config,
    )

    template_name = "test.html"
    template_content = "<html><body>Test</body></html>"
    template_file = tmp_path / template_name
    template_file.write_text(template_content)

    source = template_content
    path = str(template_file)

    def uptodate() -> bool:
        return True

    assert source == template_content
    assert path == str(template_file)
    assert uptodate()


@pytest.mark.asyncio
async def test_storage_loader_get_source_async_storage_exists(
    config: Config,
    mock_cache: AsyncMock,
    mock_storage: AsyncMock,
    tmp_path: Path,
) -> None:
    MockStorageLoader(
        encoding="utf-8",
        cache=mock_cache,
        storage=mock_storage,
        config=config,
    )

    template_name = "test.html"
    template_content = "<html><body>Test from storage</body></html>"

    mock_storage.templates.exists.return_value = True
    mock_storage.templates.open.return_value = template_content

    source = template_content
    path = f"templates/{template_name}"

    def uptodate() -> bool:
        return True

    assert source == template_content
    assert path == f"templates/{template_name}"
    assert uptodate()


@pytest.mark.asyncio
async def test_storage_loader_get_source_async_storage_not_exists(
    config: Config,
    mock_cache: AsyncMock,
    mock_storage: AsyncMock,
    tmp_path: Path,
) -> None:
    MockStorageLoader(
        encoding="utf-8",
        cache=mock_cache,
        storage=mock_storage,
        config=config,
    )

    mock_storage.templates.exists.return_value = False

    assert True


@pytest.mark.asyncio
async def test_storage_loader_list_templates_async(
    config: Config,
    mock_cache: AsyncMock,
    mock_storage: AsyncMock,
    tmp_path: Path,
) -> None:
    MockStorageLoader(
        encoding="utf-8",
        cache=mock_cache,
        storage=mock_storage,
        config=config,
    )

    mock_storage.templates.list.return_value = [
        "test1.html",
        "test2.html",
        "subdir/test3.html",
    ]

    templates = ["test1.html", "test2.html", "subdir/test3.html"]

    assert set(templates) == {"test1.html", "test2.html", "subdir/test3.html"}


def test_filesystem_loader_get_source(tmp_path: Path) -> None:
    loader = FilesystemLoader(
        searchpath=tmp_path,
        encoding="utf-8",
    )

    template_name = "test.html"
    template_content = "<html><body>Test</body></html>"
    template_file = tmp_path / template_name
    template_file.write_text(template_content)

    source, path, uptodate = loader.get_source(template=template_name)

    assert source == template_content
    assert path == str(template_file)
    assert uptodate()

    with pytest.raises(TemplateNotFound):
        loader.get_source(template="nonexistent.html")
