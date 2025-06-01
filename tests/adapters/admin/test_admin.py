import typing as t
from unittest.mock import patch

import pytest
from fastblocks.adapters.admin._base import AdminBaseSettings


@pytest.mark.unit
class TestAdminBaseSettings:
    def test_admin_base_settings_defaults(self) -> None:
        settings = AdminBaseSettings()
        assert settings.title == "FastBlocks Dashboard"
        assert settings.style == "bootstrap"


@pytest.fixture
def mock_adapter_base() -> t.Any:
    with patch("fastblocks.adapters.admin._base.AdapterBase") as mock:
        yield mock


@pytest.mark.unit
class TestAdminBase:
    def test_admin_base_class(self, mock_adapter_base: t.Any) -> None:
        from fastblocks.adapters.admin._base import AdminBase

        assert hasattr(AdminBase, "__name__")
        assert AdminBase.__name__ == "AdminBase"
