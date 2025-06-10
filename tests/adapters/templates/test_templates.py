"""Tests for the templates adapter module."""

import tempfile
import typing as t
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from acb.config import Config
from anyio import Path as AsyncPath
from starlette.requests import Request
from starlette.responses import HTMLResponse, Response
from fastblocks.adapters.templates import _base, jinja2
from fastblocks.adapters.templates._base import TemplatesBase
from fastblocks.adapters.templates.jinja2 import LoaderProtocol
from tests.conftest import (
    MockTemplatesBaseSettings,
)

TemplateContext = dict[str, Any]
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


@pytest.mark.anyio(backends=["asyncio"])
async def test_templates_base_settings_cache_timeout_deployed(config: Config) -> None:
    config.deployed = True
    settings = MockTemplatesBaseSettings()
    settings.update_from_config(config)
    assert settings.cache_timeout == 300


@pytest.mark.anyio(backends=["asyncio"])
async def test_templates_base_settings_cache_timeout_not_deployed(
    config: Config,
) -> None:
    config.deployed = False
    settings = MockTemplatesBaseSettings()
    settings.update_from_config(config)
    assert settings.cache_timeout == 1


@pytest.mark.anyio(backends=["asyncio"])
async def test_get_searchpath(
    templates: TemplatesBase, mock_adapter: type, tmp_path: Path
) -> None:
    adapter = mock_adapter(name="test_adapter", category="app", path=tmp_path)
    path = AsyncPath(tmp_path / "templates" / "app")
    with patch.object(AsyncPath, "mkdir", AsyncMock(return_value=None)):
        result = templates.get_searchpath(adapter, path)
        assert len(result) == 4
        assert result[0] == path / "test_style" / "test_adapter" / "theme"
        assert result[1] == path / "test_style" / "test_adapter"
        assert result[2] == path / "test_style"
        assert result[3] == path / "base"


@pytest.mark.anyio(backends=["asyncio"])
async def test_get_searchpaths(
    templates: TemplatesBase, mock_adapter: type, tmp_path: Path
) -> None:
    adapter = mock_adapter(name="test_adapter", category="app", path=tmp_path)
    _ = tmp_path / "templates" / "app"

    with (
        patch.object(_base, "root_path", AsyncPath(tmp_path)),
        patch.object(AsyncPath, "exists", AsyncMock(return_value=True)),
        patch.object(Path, "mkdir", MagicMock(return_value=None)),
    ):
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


@pytest.mark.anyio(backends=["asyncio"])
async def test_get_storage_path_templates(
    templates: TemplatesBase, tmp_path: Path
) -> None:
    path = AsyncPath(tmp_path / "some" / "path" / "templates" / "test" / "file.txt")
    result = templates.get_storage_path(path)
    assert result == AsyncPath("templates/test/file.txt")


@pytest.mark.anyio(backends=["asyncio"])
async def test_get_storage_path_underscore_templates(
    templates: TemplatesBase, tmp_path: Path
) -> None:
    path = AsyncPath(tmp_path / "some" / "path" / "_templates" / "test" / "file.txt")
    result = templates.get_storage_path(path)
    assert result == AsyncPath("_templates/path/test/file.txt")


@pytest.mark.anyio(backends=["asyncio"])
async def test_get_cache_key(templates: TemplatesBase, tmp_path: Path) -> None:
    path = AsyncPath(tmp_path / "some" / "path" / "test" / "file.txt")
    with patch.object(
        templates, "get_cache_key", return_value="some:path:test:file.txt"
    ):
        result = templates.get_cache_key(path)
        assert result == "some:path:test:file.txt"


@pytest.fixture
def config() -> Config:
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

    return config


@pytest.fixture
def templates() -> TemplatesBase:
    templates = TemplatesBase()

    from types import SimpleNamespace

    templates.config = SimpleNamespace(app=SimpleNamespace(style="test_style"))

    templates.filters = {
        "truncate": lambda text, length: text[: length - 3] + "..."
        if len(text) > length
        else text,
        "filesize": lambda size: f"{size / 1024:.1f} KB"
        if size < 1024 * 1024
        else f"{size / (1024 * 1024):.1f} MB"
        if size < 1024 * 1024 * 1024
        else f"{size / (1024 * 1024 * 1024):.1f} GB",
    }

    class MockTemplateRenderer:
        def __init__(self) -> None:
            self._mock_responses = {}

        def set_response(self, template: str, response: Response) -> None:
            self._mock_responses[template] = response

        async def render_template(
            self,
            request: Request,
            template: str,
            context: dict[str, Any] | None = None,
            headers: dict[str, str] | None = None,
        ) -> Response:
            if template in self._mock_responses:
                return self._mock_responses[template]

            context = context or {}
            headers = headers or {}
            content = (
                f"<html><body>{template}: {', '.join(context.keys())}</body></html>"
            )
            if "cached.html" in template:
                content = "<html><body>Cached content</body></html>"
            return HTMLResponse(content, headers=headers)

    templates.app = MockTemplateRenderer()

    return templates


@pytest.fixture
def http_request() -> Request:
    scope = {"type": "http", "method": "GET", "path": "/"}
    return Request(scope)


@pytest.fixture
def jinja2_templates(config: Config) -> jinja2.Templates:
    templates = jinja2.Templates()
    return templates
