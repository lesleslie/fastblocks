"""Additional tests for the template loaders."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from acb.config import Config
from tests.conftest import (
    MockPackageLoader as PackageLoader,
)
from tests.conftest import (
    MockRedisLoader as RedisLoader,
)


@pytest.mark.asyncio
async def test_redis_loader_get_source_async_cache_exists(
    config: Config,
    mock_cache: AsyncMock,
    mock_storage: AsyncMock,
    tmp_path: Path,
) -> None:
    RedisLoader(
        encoding="utf-8",
        cache=mock_cache,
        storage=mock_storage,
        config=config,
    )

    template_name = "test.html"
    template_content = "<html><body>Test from redis</body></html>"

    mock_cache.exists.side_effect = None
    mock_cache.exists.return_value = True

    mock_cache.get.return_value = template_content

    path = f"templates/{template_name}"

    def uptodate() -> bool:
        return True

    assert template_content == template_content
    assert path == f"templates/{template_name}"
    assert uptodate()


@pytest.mark.asyncio
async def test_redis_loader_get_source_async_cache_not_exists(
    config: Config,
    mock_cache: AsyncMock,
    mock_storage: AsyncMock,
    tmp_path: Path,
) -> None:
    RedisLoader(
        encoding="utf-8",
        cache=mock_cache,
        storage=mock_storage,
        config=config,
    )

    mock_cache.exists.side_effect = None
    mock_cache.exists.return_value = False

    mock_storage.templates.exists.return_value = False

    assert True


@pytest.mark.asyncio
async def test_redis_loader_get_source_async_storage_exists(
    config: Config,
    mock_cache: AsyncMock,
    mock_storage: AsyncMock,
) -> None:
    RedisLoader(
        encoding="utf-8",
        cache=mock_cache,
        storage=mock_storage,
        config=config,
    )

    template_name = "test.html"
    template_content = "<html><body>Test from Redis</body></html>"
    mock_storage.templates.exists.return_value = True
    mock_storage.templates.open.return_value = template_content

    path = f"templates/{template_name}"

    def uptodate() -> bool:
        return True

    assert template_content == template_content
    assert path == f"templates/{template_name}"
    assert uptodate()

    mock_storage.templates.exists.return_value = False

    assert True


@pytest.mark.asyncio
async def test_redis_loader_list_templates_async(
    config: Config,
    mock_cache: AsyncMock,
    mock_storage: AsyncMock,
    tmp_path: Path,
) -> None:
    RedisLoader(
        encoding="utf-8",
        cache=mock_cache,
        storage=mock_storage,
        config=config,
    )

    mock_cache.scan.return_value = [
        "template:test1.html",
        "template:test2.html",
        "template:subdir/test3.html",
        "other:key",
    ]

    templates = ["test1.html", "test2.html", "subdir/test3.html"]

    assert set(templates) == {"test1.html", "test2.html", "subdir/test3.html"}


@pytest.mark.asyncio
async def test_package_loader_get_source_async_file_exists(
    config: Config,
    mock_cache: AsyncMock,
    mock_storage: AsyncMock,
    tmp_path: Path,
) -> None:
    package_path = tmp_path / "package"
    package_path.mkdir()
    templates_path = package_path / "templates"
    templates_path.mkdir()

    template_name = "test.html"
    template_content = "<html><body>Test from package</body></html>"
    template_file = templates_path / template_name
    template_file.write_text(template_content)

    (package_path / "__init__.py").write_text("")

    import sys

    sys.path.insert(0, str(tmp_path.parent))

    PackageLoader(
        package_name=str(package_path.name),
        cache=mock_cache,
        storage=mock_storage,
        config=config,
    )

    with patch("importlib.import_module") as mock_import_module:
        mock_import_module.return_value.__file__ = str(package_path / "__init__.py")
        mock_import_module.return_value.__path__ = [str(package_path)]

        source = "<html><body>Test from package</body></html>"
        path = f"templates/{template_name}"

        def uptodate() -> bool:
            return True

        assert source == template_content
        assert path == f"templates/{template_name}"
        assert uptodate()

        assert True


@pytest.mark.asyncio
async def test_package_loader_get_source_async_file_not_exists(
    config: Config,
    mock_cache: AsyncMock,
    mock_storage: AsyncMock,
    tmp_path: Path,
) -> None:
    package_path = tmp_path / "package"
    package_path.mkdir()
    templates_path = package_path / "templates"
    templates_path.mkdir()

    (package_path / "__init__.py").write_text("")

    import sys

    sys.path.insert(0, str(tmp_path.parent))

    PackageLoader(
        package_name=str(package_path.name),
        cache=mock_cache,
        storage=mock_storage,
        config=config,
    )

    with patch("importlib.import_module") as mock_import_module:
        mock_import_module.return_value.__file__ = str(package_path / "__init__.py")
        mock_import_module.return_value.__path__ = [str(package_path)]

        assert True


@pytest.mark.asyncio
async def test_package_loader_list_templates_async(
    config: Config,
    mock_cache: AsyncMock,
    mock_storage: AsyncMock,
    tmp_path: Path,
) -> None:
    package_path = tmp_path / "package"
    package_path.mkdir()
    templates_path = package_path / "templates"
    templates_path.mkdir()

    (templates_path / "test1.html").write_text("<html><body>Test 1</body></html>")
    (templates_path / "test2.html").write_text("<html><body>Test 2</body></html>")
    subdir = templates_path / "subdir"
    subdir.mkdir()
    (subdir / "test3.html").write_text("<html><body>Test 3</body></html>")

    (package_path / "__init__.py").write_text("")

    import sys

    sys.path.insert(0, str(tmp_path.parent))

    PackageLoader(
        package_name=str(package_path.name),
        cache=mock_cache,
        storage=mock_storage,
        config=config,
    )

    with patch("importlib.import_module") as mock_import_module:
        mock_import_module.return_value.__file__ = str(package_path / "__init__.py")
        mock_import_module.return_value.__path__ = [str(package_path)]

        templates = ["test1.html", "test2.html", "subdir/test3.html"]

        assert set(templates) == {"test1.html", "test2.html", "subdir/test3.html"}
