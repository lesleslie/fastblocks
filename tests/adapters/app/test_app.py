import sys
import types
import typing as t

import pytest
from pytest_mock import MockerFixture
from starlette.routing import Router


class MockSettings:
    def __init__(self, **kwargs: t.Any) -> None:
        for key, value in kwargs.items():
            setattr(self, key, value)


class MockAdapterBase:
    pass


@pytest.fixture
def mock_acb(mocker: MockerFixture) -> t.Any:
    mock_acb_module = types.ModuleType("acb")
    mock_config_module = types.ModuleType("acb.config")

    mock_settings_class = MockSettings
    mock_adapter_base_class = MockAdapterBase

    setattr(mock_config_module, "Settings", mock_settings_class)
    setattr(mock_config_module, "AdapterBase", mock_adapter_base_class)
    setattr(mock_config_module, "AppSettings", mock_settings_class)

    setattr(mock_acb_module, "config", mock_config_module)

    sys.modules["acb"] = mock_acb_module
    sys.modules["acb.config"] = mock_config_module

    for mod in list(sys.modules.keys()):
        if mod.startswith("fastblocks"):
            sys.modules.pop(mod, None)

    return mock_acb_module


@pytest.mark.unit
class TestAppBaseSettings:
    def test_app_base_settings_defaults(self, mock_acb: t.Any) -> None:
        sys.modules["fastblocks"] = types.ModuleType("fastblocks")
        sys.modules["fastblocks.adapters"] = types.ModuleType("fastblocks.adapters")
        sys.modules["fastblocks.adapters.app"] = types.ModuleType(
            "fastblocks.adapters.app",
        )

        base_module = types.ModuleType("fastblocks.adapters.app._base")

        class AppBaseSettings(MockSettings):
            debug: bool
            reload: bool
            host: str
            port: int

            def __init__(self) -> None:
                super().__init__(
                    debug=False,
                    reload=False,
                    host="127.0.0.1",
                    port=8000,
                )

        setattr(base_module, "AppBaseSettings", AppBaseSettings)
        sys.modules["fastblocks.adapters.app._base"] = base_module

        AppBaseSettingsType = base_module.AppBaseSettings

        settings = AppBaseSettingsType()

        assert hasattr(settings, "debug")
        assert settings.debug is False
        assert hasattr(settings, "reload")
        assert settings.reload is False
        assert hasattr(settings, "host")
        assert settings.host == "127.0.0.1"
        assert hasattr(settings, "port")
        assert settings.port == 8000


@pytest.mark.unit
class TestAppBase:
    def test_app_base_class(self, mock_acb: t.Any, mocker: MockerFixture) -> None:
        sys.modules["fastblocks"] = types.ModuleType("fastblocks")
        sys.modules["fastblocks.adapters"] = types.ModuleType("fastblocks.adapters")
        sys.modules["fastblocks.adapters.app"] = types.ModuleType(
            "fastblocks.adapters.app",
        )

        base_module = types.ModuleType("fastblocks.adapters.app._base")

        mock_router = mocker.MagicMock(spec=Router)

        class AppBase:
            router = mock_router

        setattr(base_module, "AppBase", AppBase)
        sys.modules["fastblocks.adapters.app._base"] = base_module

        AppBaseType = base_module.AppBase

        assert hasattr(AppBaseType, "router")
        assert AppBaseType.router is mock_router
