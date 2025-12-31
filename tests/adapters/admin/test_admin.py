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


@pytest.mark.unit
class TestAdminBase:
    def test_admin_base_class(self) -> None:
        from fastblocks.adapters.admin._base import AdminBase

        assert hasattr(AdminBase, "__name__")
        assert AdminBase.__name__ == "AdminBase"
