"""Test the structure of app modules."""

import sys
import types
import typing as t
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def clean_modules() -> t.Generator[None]:
    original_modules = sys.modules.copy()

    for mod in list(sys.modules.keys()):
        if mod.startswith(("fastblocks", "acb")):
            sys.modules.pop(mod, None)

    yield

    sys.modules.clear()
    sys.modules.update(original_modules)


@pytest.mark.unit
class TestAppStructure:
    def test_app_base_structure(self, clean_modules: None) -> None:
        sys.modules["fastblocks"] = types.ModuleType("fastblocks")
        sys.modules["fastblocks.adapters"] = types.ModuleType("fastblocks.adapters")
        sys.modules["fastblocks.adapters.app"] = types.ModuleType(
            "fastblocks.adapters.app",
        )

        base_module = types.ModuleType("fastblocks.adapters.app._base")

        class AppBaseSettings:
            name: str = "fastblocks"
            style: str = "bulma"
            theme: str = "light"

        class AppProtocol(t.Protocol):
            router: t.Any

            async def init(self) -> None: ...

            async def post_startup(self) -> None: ...

        class AppBase:
            router = MagicMock()

        setattr(base_module, "AppBaseSettings", AppBaseSettings)
        setattr(base_module, "AppProtocol", AppProtocol)
        setattr(base_module, "AppBase", AppBase)
        sys.modules["fastblocks.adapters.app._base"] = base_module

        AppBaseType = base_module.AppBase
        AppBaseSettingsType = base_module.AppBaseSettings
        AppProtocolType = base_module.AppProtocol

        assert hasattr(AppBaseSettingsType, "name")
        assert hasattr(AppBaseSettingsType, "style")
        assert hasattr(AppBaseSettingsType, "theme")
        assert AppBaseSettingsType.name == "fastblocks"
        assert AppBaseSettingsType.style == "bulma"
        assert AppBaseSettingsType.theme == "light"

        assert hasattr(AppProtocolType, "init")
        assert hasattr(AppProtocolType, "post_startup")

        assert hasattr(AppBaseType, "router")

    def test_app_default_structure(self, clean_modules: None) -> None:
        sys.modules["fastblocks"] = types.ModuleType("fastblocks")
        sys.modules["fastblocks.adapters"] = types.ModuleType("fastblocks.adapters")
        sys.modules["fastblocks.adapters.app"] = types.ModuleType(
            "fastblocks.adapters.app",
        )

        base_module = types.ModuleType("fastblocks.adapters.app._base")

        class AppBaseSettings:
            name: str = "fastblocks"
            style: str = "bulma"
            theme: str = "light"

        class AppBase:
            router = MagicMock()

        setattr(base_module, "AppBaseSettings", AppBaseSettings)
        setattr(base_module, "AppBase", AppBase)
        sys.modules["fastblocks.adapters.app._base"] = base_module

        depends_module = types.ModuleType("fastblocks.depends")

        def set_dependency(cls: t.Any) -> None:
            pass

        setattr(depends_module, "set", set_dependency)
        sys.modules["fastblocks.depends"] = depends_module

        default_module = types.ModuleType("fastblocks.adapters.app.default")

        class AppSettings(AppBaseSettings):
            pass

        class App(AppBase):
            async def init(self) -> None:
                pass

            async def post_startup(self) -> None:
                pass

            async def lifespan(self, app: t.Any) -> t.AsyncGenerator[None]:
                yield

        setattr(default_module, "AppSettings", AppSettings)
        setattr(default_module, "App", App)
        setattr(default_module, "depends", depends_module)
        sys.modules["fastblocks.adapters.app.default"] = default_module

        depends_spy = MagicMock()
        setattr(depends_module, "set", depends_spy)

        AppType = default_module.App
        AppSettingsType = default_module.AppSettings

        depends_spy(AppType)

        assert issubclass(AppSettingsType, AppBaseSettings)

        assert hasattr(AppType, "init")
        assert hasattr(AppType, "post_startup")
        assert hasattr(AppType, "lifespan")

        depends_spy.assert_called_once_with(AppType)
