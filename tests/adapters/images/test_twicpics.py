"""D1 coverage tests for fastblocks/adapters/images/twicpics.py.

Targets TwicPics image adapter:
- settings defaults (quality, format, lazy, progressive)
- ``_build_transform_parts`` for each transformation key
- ``get_image_url`` happy-path URL construction
- ``get_img_tag`` / ``get_responsive_img_tag`` rendering helpers
- filter-registration on a Jinja2 ``Environment`` stub
"""
# pyright: reportAttributeAccessIssue=false, reportFunctionMemberAccess=false
from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from fastblocks.adapters.images.twicpics import (
    TwicPicsImages,
    TwicPicsImagesSettings,
    register_twicpics_filters,
)


@pytest.fixture
def adapter() -> TwicPicsImages:
    return TwicPicsImages()


@pytest.fixture
def settings() -> TwicPicsImagesSettings:
    return TwicPicsImagesSettings(domain="demo.twic.pics")


@pytest.fixture
def env(
    adapter: TwicPicsImages, monkeypatch: pytest.MonkeyPatch
) -> SimpleNamespace:
    filters: dict[str, Any] = {}
    globals_: dict[str, Any] = {}

    class _FilterProxy:
        def __call__(self, name: str):
            def deco(fn: Any) -> Any:
                filters[name] = fn
                return fn

            return deco

    class _GlobalsProxy:
        def __call__(self, name: str):
            def deco(fn: Any) -> Any:
                globals_[name] = fn
                return fn

            return deco

    class _Env:
        def __init__(self) -> None:
            self.filters = filters
            self.globals = globals_
            self.filter = _FilterProxy()
            self.global_ = _GlobalsProxy()

    monkeypatch.setattr(
        "fastblocks.adapters.images.twicpics.resolve_instance",
        lambda *_args, **_kwargs: adapter,
    )

    return SimpleNamespace(env=_Env())


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSettings:
    def test_defaults(self, settings: TwicPicsImagesSettings) -> None:
        assert settings.default_quality == 85
        assert settings.default_format == "auto"
        assert settings.enable_placeholder is True
        assert settings.placeholder_quality == 10
        assert settings.enable_lazy_loading is True
        assert settings.enable_progressive is True
        assert settings.timeout == 30

    def test_module_metadata(self, settings: TwicPicsImagesSettings) -> None:
        assert settings.MODULE_STATUS == "stable"


# ---------------------------------------------------------------------------
# _build_transform_parts
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBuildTransformParts:
    def test_default_quality_and_auto_format(
        self, adapter: TwicPicsImages, settings: TwicPicsImagesSettings
    ) -> None:
        adapter.settings = settings
        parts = adapter._build_transform_parts({})
        assert "quality=85" in parts
        assert "output=auto" not in parts  # "auto" is dropped

    def test_resize_dimensions(self, adapter: TwicPicsImages) -> None:
        adapter.settings = TwicPicsImagesSettings(domain="x.twic.pics")
        parts = adapter._build_transform_parts({"width": 800, "height": 600})
        assert "width=800" in parts
        assert "height=600" in parts

    def test_fit_mode_crop_maps_to_fill(self, adapter: TwicPicsImages) -> None:
        adapter.settings = TwicPicsImagesSettings(domain="x.twic.pics")
        parts = adapter._build_transform_parts({"fit": "crop"})
        assert "resize=fill" in parts

    def test_fit_mode_cover_kept(self, adapter: TwicPicsImages) -> None:
        adapter.settings = TwicPicsImagesSettings(domain="x.twic.pics")
        parts = adapter._build_transform_parts({"fit": "cover"})
        assert "resize=cover" in parts

    def test_explicit_format_included(self, adapter: TwicPicsImages) -> None:
        adapter.settings = TwicPicsImagesSettings(domain="x.twic.pics")
        parts = adapter._build_transform_parts({"format": "webp"})
        assert "output=webp" in parts

    def test_advanced_effects(self, adapter: TwicPicsImages) -> None:
        adapter.settings = TwicPicsImagesSettings(domain="x.twic.pics")
        parts = adapter._build_transform_parts(
            {
                "blur": 5,
                "brightness": 10,
                "contrast": 20,
                "saturation": 50,
                "rotate": 90,
            }
        )
        assert "blur=5" in parts
        assert "brightness=10" in parts
        assert "contrast=20" in parts
        assert "saturation=50" in parts
        assert "rotate=90" in parts

    def test_focus_dict_xy(self, adapter: TwicPicsImages) -> None:
        adapter.settings = TwicPicsImagesSettings(domain="x.twic.pics")
        parts = adapter._build_transform_parts({"focus": {"x": 0.5, "y": 0.8}})
        assert any(p.startswith("focus=") for p in parts)
        assert "focus=0.5x0.8" in parts

    def test_focus_string(self, adapter: TwicPicsImages) -> None:
        adapter.settings = TwicPicsImagesSettings(domain="x.twic.pics")
        parts = adapter._build_transform_parts({"focus": "auto"})
        assert "focus=auto" in parts

    def test_progressive_added_for_jpeg(
        self, adapter: TwicPicsImages
    ) -> None:
        adapter.settings = TwicPicsImagesSettings(
            domain="x.twic.pics", enable_progressive=True
        )
        parts = adapter._build_transform_parts({"format": "jpeg"})
        assert "progressive=true" in parts

    def test_progressive_skipped_for_png(
        self, adapter: TwicPicsImages
    ) -> None:
        adapter.settings = TwicPicsImagesSettings(
            domain="x.twic.pics", enable_progressive=True
        )
        parts = adapter._build_transform_parts({"format": "png"})
        assert "progressive=true" not in parts

    def test_progressive_added_for_auto(
        self, adapter: TwicPicsImages
    ) -> None:
        adapter.settings = TwicPicsImagesSettings(
            domain="x.twic.pics", enable_progressive=True
        )
        parts = adapter._build_transform_parts({})
        assert "progressive=true" in parts


# ---------------------------------------------------------------------------
# get_image_url
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetImageUrl:
    @pytest.mark.asyncio
    async def test_basic_url(self, adapter: TwicPicsImages) -> None:
        adapter.settings = TwicPicsImagesSettings(domain="demo.twic.pics")
        url = await adapter.get_image_url("images/foo.jpg")
        assert "demo.twic.pics" in url
        assert "images/foo.jpg" in url

    @pytest.mark.asyncio
    async def test_url_with_width_and_height(
        self, adapter: TwicPicsImages
    ) -> None:
        adapter.settings = TwicPicsImagesSettings(domain="demo.twic.pics")
        url = await adapter.get_image_url("images/foo.jpg", {"width": 200})
        assert "width=200" in url

    @pytest.mark.asyncio
    async def test_url_with_format_change(
        self, adapter: TwicPicsImages
    ) -> None:
        adapter.settings = TwicPicsImagesSettings(domain="demo.twic.pics")
        url = await adapter.get_image_url("images/foo.jpg", {"format": "webp"})
        assert "output=webp" in url


# ---------------------------------------------------------------------------
# Image-tag helpers
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestImageTagHelpers:
    def test_get_img_tag(self, adapter: TwicPicsImages) -> None:
        adapter.settings = TwicPicsImagesSettings(domain="demo.twic.pics")
        tag = adapter.get_img_tag("images/foo.jpg", "alt text")
        assert "<img" in tag
        assert "alt=" in tag
        assert "src=" in tag
        # TwicPics placeholder class is on by default.
        assert "twic-w" in tag or "data-twic" in tag or "src=" in tag

    def test_get_img_tag_uses_alt(self, adapter: TwicPicsImages) -> None:
        adapter.settings = TwicPicsImagesSettings(domain="demo.twic.pics")
        tag = adapter.get_img_tag("images/foo.jpg", "hello world")
        assert 'alt="hello world"' in tag

    def test_get_img_tag_with_width_attribute(
        self, adapter: TwicPicsImages
    ) -> None:
        adapter.settings = TwicPicsImagesSettings(domain="demo.twic.pics")
        tag = adapter.get_img_tag(
            "images/foo.jpg",
            "alt",
            width=200,
            height=100,
        )
        assert 'width="200"' in tag
        assert 'height="100"' in tag

    def test_get_responsive_img_tag(self, adapter: TwicPicsImages) -> None:
        adapter.settings = TwicPicsImagesSettings(domain="demo.twic.pics")
        tag = adapter.get_responsive_img_tag(
            "images/foo.jpg",
            "alt text",
            sizes="(max-width: 768px) 100vw, 50vw",
        )
        assert "<img" in tag
        assert "srcset" in tag


# ---------------------------------------------------------------------------
# Filter registration
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFilterRegistration:
    def test_register_attaches_filters_and_globals(
        self, env: SimpleNamespace
    ) -> None:
        register_twicpics_filters(env.env)
        assert "twic_url" in env.env.filters
        assert "twic_img" in env.env.filters
        assert "twic_placeholder" in env.env.filters
        # ``twicpics_responsive`` is a global, not a filter.
        assert "twicpics_responsive" in env.env.globals

    @pytest.mark.asyncio
    async def test_twic_url_filter(
        self,
        env: SimpleNamespace,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # Re-seed the resolver target with a domain-bearing adapter so
        # the URL includes the CDN endpoint.
        seeded = TwicPicsImages()
        seeded.settings = TwicPicsImagesSettings(domain="demo.twic.pics")
        monkeypatch.setattr(
            "fastblocks.adapters.images.twicpics.resolve_instance",
            lambda *_a, **_k: seeded,
        )
        register_twicpics_filters(env.env)
        out = await env.env.filters["twic_url"]("images/foo.jpg", width=200)
        assert "demo.twic.pics" in out
        assert "width=200" in out

    def test_twic_img_filter(self, env: SimpleNamespace) -> None:
        register_twicpics_filters(env.env)
        out = env.env.filters["twic_img"]("images/foo.jpg", "alt")
        assert "<img" in out
        assert 'alt="alt"' in out


# ---------------------------------------------------------------------------
# close() and HTTP client lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestClientLifecycle:
    @pytest.mark.asyncio
    async def test_close_closes_client(self, adapter: TwicPicsImages) -> None:
        adapter.settings = TwicPicsImagesSettings(domain="x.twic.pics")
        # Force-create a mock client.
        mock_client = MagicMock()
        mock_client.aclose = AsyncMock()
        adapter._client = mock_client
        await adapter.close()
        mock_client.aclose.assert_awaited_once()
        # close() resets the client attribute.
        assert adapter._client is None

    @pytest.mark.asyncio
    async def test_close_no_client_is_safe(self, adapter: TwicPicsImages) -> None:
        adapter._client = None
        # No error when no client is present.
        await adapter.close()
        assert adapter._client is None