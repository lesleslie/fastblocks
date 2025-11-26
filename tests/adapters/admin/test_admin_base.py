import pytest


@pytest.mark.unit
class TestAdminBaseModule:
    def test_admin_base_settings_defaults(self):
        from fastblocks.adapters.admin._base import AdminBaseSettings

        s = AdminBaseSettings()
        assert hasattr(s, "style") and s.style == "bootstrap"
        assert hasattr(s, "title") and isinstance(s.title, str)

    def test_admin_base_instantiation(self):
        from fastblocks.adapters.admin._base import AdminBase

        # Should instantiate without extra requirements
        obj = AdminBase()
        assert isinstance(obj, AdminBase)
