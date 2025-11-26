import pytest


@pytest.mark.unit
class TestFontsBase:
    def test_fonts_base_settings_defaults(self):
        from fastblocks.adapters.fonts._base import FontsBaseSettings

        s = FontsBaseSettings()
        assert s.primary_font
        assert s.secondary_font
        assert isinstance(s.font_weights, list)

    @pytest.mark.asyncio
    async def test_fonts_base_abstract_methods(self, monkeypatch):
        from fastblocks.adapters.fonts import _base as fonts_base

        # Allow depends.set(self) call with flexible signature
        monkeypatch.setattr(fonts_base.depends, "set", lambda *args, **kwargs: None)

        class Impl(fonts_base.FontsBase):
            async def get_font_import(self) -> str:  # pragma: no cover - not called
                return ""

            def get_font_family(
                self, font_type: str
            ) -> str:  # pragma: no cover - not called
                return font_type

        Impl()
        # Verify abstract methods on base raise
        with pytest.raises(NotImplementedError):
            _ = await fonts_base.FontsBase().get_font_import()  # type: ignore[misc]

        with pytest.raises(NotImplementedError):
            fonts_base.FontsBase().get_font_family("primary")  # type: ignore[misc]
