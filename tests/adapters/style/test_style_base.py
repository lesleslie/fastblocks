import pytest


@pytest.mark.unit
class TestStyleBase:
    def test_style_base_settings_defaults(self):
        from fastblocks.adapters.style._base import StyleBaseSettings

        s = StyleBaseSettings()
        assert s.version == "latest"
        assert isinstance(s.additional_stylesheets, list)

    def test_style_base_abstract_methods(self, monkeypatch):
        from fastblocks.adapters.style import _base as style_base

        # Allow depends.register(self) call
        monkeypatch.setattr(style_base.depends, "register", lambda *args, **kwargs: None)

        base = style_base.StyleBase()
        with pytest.raises(NotImplementedError):
            base.get_stylesheet_links()
        with pytest.raises(NotImplementedError):
            base.get_component_class("button")
