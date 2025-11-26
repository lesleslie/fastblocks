import pytest


@pytest.mark.unit
class TestImagesBase:
    def test_images_base_settings_defaults(self):
        from fastblocks.adapters.images._base import ImagesBaseSettings

        s = ImagesBaseSettings()
        assert s.media_bucket == "media"
        assert isinstance(s.default_transformations, dict)
        assert s.lazy_loading is True

    @pytest.mark.asyncio
    async def test_images_base_abstract_methods(self, monkeypatch):
        from fastblocks.adapters.images import _base as images_base

        # Allow depends.set(self) call
        monkeypatch.setattr(images_base.depends, "set", lambda *args, **kwargs: None)

        # Base abstract methods raise
        base = images_base.ImagesBase()
        with pytest.raises(NotImplementedError):
            await base.upload_image(b"data", "x.png")
        with pytest.raises(NotImplementedError):
            await base.get_image_url("id")
        with pytest.raises(NotImplementedError):
            base.get_img_tag("id", "alt")
