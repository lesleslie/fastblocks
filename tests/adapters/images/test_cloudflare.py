"""D1 coverage tests for fastblocks/adapters/images/cloudflare.py.

Targets the Cloudflare Images adapter: settings, URL builders,
transformation helpers, img-tag generation, and template-filter registration.
"""
# pyright: reportAttributeAccessIssue=false, reportFunctionMemberAccess=false
from __future__ import annotations

from typing import Any

import pytest

from fastblocks.adapters.images.cloudflare import (
    CloudflareImages,
    CloudflareImagesSettings,
    register_cloudflare_filters,
)


@pytest.fixture
def adapter() -> CloudflareImages:
    return CloudflareImages()


@pytest.fixture
def settings() -> CloudflareImagesSettings:
    return CloudflareImagesSettings()


@pytest.fixture
def env(
    adapter: CloudflareImages, monkeypatch: pytest.MonkeyPatch
) -> Any:
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
        "fastblocks.adapters.images.cloudflare.resolve_instance",
        lambda *_a, **_k: adapter,
    )

    return _Env()


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSettings:
    def test_module_metadata(self, settings: CloudflareImagesSettings) -> None:
        assert settings.MODULE_STATUS == "stable"

    def test_defaults(self, settings: CloudflareImagesSettings) -> None:
        assert settings.default_variant == "public"
        assert settings.require_signed_urls is False
        assert settings.timeout == 30


# ---------------------------------------------------------------------------
# URL / transformation builders
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestUrlBuilders:
    def test_build_base_url_without_settings_raises(
        self, adapter: CloudflareImages
    ) -> None:
        adapter.settings = None
        with pytest.raises(RuntimeError, match="not configured"):
            adapter._build_base_url("image-1")

    def test_build_base_url_with_delivery_url(
        self, adapter: CloudflareImages
    ) -> None:
        adapter.settings = CloudflareImagesSettings(
            delivery_url="https://imagedelivery.net/abc"
        )
        url = adapter._build_base_url("image-1")
        assert url == "https://imagedelivery.net/abc/image-1"

    def test_build_base_url_with_account_id(
        self, adapter: CloudflareImages
    ) -> None:
        adapter.settings = CloudflareImagesSettings(account_id="acct-123")
        url = adapter._build_base_url("image-1")
        assert "accounts/acct-123" in url
        assert "image-1" in url

    def test_build_transformation_parts_common(
        self, adapter: CloudflareImages
    ) -> None:
        parts = adapter._build_transformation_parts(
            {"width": 200, "height": 100, "quality": 80, "format": "webp"}
        )
        assert "width=200" in parts
        assert "height=100" in parts
        assert "quality=80" in parts
        assert "format=webp" in parts

    def test_build_transformation_parts_advanced(
        self, adapter: CloudflareImages
    ) -> None:
        parts = adapter._build_transformation_parts(
            {"blur": 5, "brightness": 10, "contrast": 20}
        )
        assert "blur=5" in parts
        assert "brightness=10" in parts
        assert "contrast=20" in parts

    def test_build_transformation_parts_empty(
        self, adapter: CloudflareImages
    ) -> None:
        assert adapter._build_transformation_parts({}) == []

    def test_build_transformed_url(self, adapter: CloudflareImages) -> None:
        adapter.settings = CloudflareImagesSettings(
            delivery_url="https://imagedelivery.net/abc"
        )
        url = adapter._build_transformed_url(
            "https://imagedelivery.net/abc/img",
            {"variant": "thumbnail"},
            ["width=200"],
        )
        assert url == "https://imagedelivery.net/abc/img/thumbnail?width=200"

    def test_build_transformed_url_default_variant(
        self, adapter: CloudflareImages
    ) -> None:
        adapter.settings = CloudflareImagesSettings(
            delivery_url="https://imagedelivery.net/abc",
            default_variant="public",
        )
        url = adapter._build_transformed_url(
            "https://imagedelivery.net/abc/img",
            {},
            [],
        )
        assert url.endswith("/public?")

    def test_build_transformed_url_without_settings_raises(
        self, adapter: CloudflareImages
    ) -> None:
        adapter.settings = None
        with pytest.raises(RuntimeError, match="not configured"):
            adapter._build_transformed_url("base", {}, [])


# ---------------------------------------------------------------------------
# img tag
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestImgTag:
    def test_basic_img_tag(self, adapter: CloudflareImages) -> None:
        adapter.settings = CloudflareImagesSettings(
            delivery_url="https://imagedelivery.net/abc"
        )
        tag = adapter.get_img_tag("img-1", "alt")
        assert "<img" in tag
        assert 'alt="alt"' in tag

    def test_img_tag_with_transformation(self, adapter: CloudflareImages) -> None:
        adapter.settings = CloudflareImagesSettings(
            delivery_url="https://imagedelivery.net/abc"
        )
        tag = adapter.get_img_tag(
            "img-1",
            "alt",
            transformations={"width": 200, "height": 100},
        )
        assert "width=200" in tag
        assert "height=100" in tag

    def test_img_tag_with_dimensions(self, adapter: CloudflareImages) -> None:
        adapter.settings = CloudflareImagesSettings(
            delivery_url="https://imagedelivery.net/abc"
        )
        tag = adapter.get_img_tag(
            "img-1",
            "alt",
            width=300,
            height=150,
        )
        assert 'width="300"' in tag
        assert 'height="150"' in tag


# ---------------------------------------------------------------------------
# Filter registration
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFilterRegistration:
    def test_register_attaches_filters(self, env: Any) -> None:
        register_cloudflare_filters(env)
        assert "cf_image_url" in env.filters
        assert "cf_img_tag" in env.filters
        assert "cloudflare_responsive_img" in env.globals

    def test_cf_image_url_filter_callable(self, env: Any) -> None:
        register_cloudflare_filters(env)
        assert callable(env.filters["cf_image_url"])

    def test_cf_img_tag_filter_callable(self, env: Any) -> None:
        register_cloudflare_filters(env)
        assert callable(env.filters["cf_img_tag"])
