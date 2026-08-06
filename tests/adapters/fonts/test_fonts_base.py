import pytest


@pytest.mark.unit
class TestFontsBase:
    def test_fonts_base_settings_defaults(self):
        from fastblocks.adapters.fonts._base import FontsBaseSettings

        s = FontsBaseSettings()
        assert s.primary_font
        assert s.secondary_font
        assert isinstance(s.font_weights, list)

    def test_fonts_base_settings_lists_are_isolated(self) -> None:
        """RUF012: each instance gets its own mutable default.

        Pre-fix this test fails because ``FontsBaseSettings`` exposed
        ``font_weights: list[str] = ["400", "700"]`` as a shared list,
        so appending to ``first.font_weights`` would leak into
        ``second.font_weights``. The default_factory ensures the
        instance-level isolation that callers rely on.
        """
        from fastblocks.adapters.fonts._base import FontsBaseSettings

        first = FontsBaseSettings()
        second = FontsBaseSettings()

        first.font_weights.append("900")

        assert "900" not in second.font_weights
        # Defense-in-depth: also confirm the literal default remains.
        assert second.font_weights == ["400", "700"]

    def test_google_fonts_settings_lists_are_isolated(self) -> None:
        """Google-fonts specific mutable defaults are isolated too."""
        from fastblocks.adapters.fonts.google import GoogleFontsSettings

        first = GoogleFontsSettings()
        second = GoogleFontsSettings()

        first.weights.append("900")
        first.families.append("Inter")
        first.subsets.append("latin-ext")

        assert second.weights == ["400", "700"]
        assert second.families == ["Roboto", "Open Sans"]
        assert second.subsets == ["latin"]

    @pytest.mark.asyncio
    async def test_fonts_base_abstract_methods(self, monkeypatch):
        from fastblocks.adapters.fonts import _base as fonts_base

        # Allow depends.register(self) call with flexible signature
        monkeypatch.setattr(fonts_base.depends, "register", lambda *args, **kwargs: None)

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
