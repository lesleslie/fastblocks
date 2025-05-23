"""Tests for the sitemap adapter module."""

import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
from acb.adapters import import_adapter
from acb.config import Config
from fastblocks.adapters.sitemap._base import SitemapURL

sys.path.append(str(Path(__file__).parent.parent.parent.parent))
from tests.conftest import MockSitemap  # noqa

Sitemap = import_adapter("sitemap")


@pytest.fixture
def config(tmp_path: Path) -> Config:
    config = Config()

    class StorageConfig:
        def __init__(self) -> None:
            self.local_fs = True
            self.local_path = tmp_path

    config.__dict__["storage"] = StorageConfig()

    return config


@pytest.fixture
def sitemap(config: Config) -> MockSitemap:
    sitemap = MockSitemap()
    sitemap.config = config
    sitemap.sitemap.urls = []
    return sitemap


@pytest.mark.anyio(backends=["asyncio"])
async def test_sitemap_init(sitemap: MockSitemap, config: Config) -> None:
    await sitemap.init()
    assert sitemap.sitemap is not None
    assert sitemap.sitemap.change_freq == "hourly"


@pytest.mark.anyio(backends=["asyncio"])
async def test_sitemap_add_url(sitemap: MockSitemap, config: Config) -> None:
    await sitemap.init()
    await sitemap.add_url("/test")
    assert len(sitemap.sitemap.urls) == 1
    assert sitemap.sitemap.urls[0].loc == "/test"
    await sitemap.add_url("/test2", change_freq="daily")
    assert len(sitemap.sitemap.urls) == 2
    assert sitemap.sitemap.urls[1].loc == "/test2"
    assert sitemap.sitemap.urls[1].change_freq == "daily"


@pytest.mark.anyio(backends=["asyncio"])
async def test_sitemap_add_url_invalid_change_freq(
    sitemap: MockSitemap, config: Config
) -> None:
    await sitemap.init()
    with pytest.raises(ValueError):
        await sitemap.add_url("/test", change_freq="invalid")


@pytest.mark.anyio(backends=["asyncio"])
async def test_sitemap_generate(sitemap: MockSitemap, config: Config) -> None:
    await sitemap.init()
    await sitemap.add_url("/test")
    await sitemap.add_url("/test2", change_freq="daily")
    result = await sitemap.generate()
    assert result.startswith("<?xml")


@pytest.mark.anyio(backends=["asyncio"])
async def test_sitemap_write(
    sitemap: MockSitemap, config: Config, tmp_path: Path
) -> None:
    await sitemap.init()
    await sitemap.add_url("/test")
    await sitemap.add_url("/test2", change_freq="daily")
    sitemap_path = tmp_path / "sitemap.xml"
    await sitemap.write(sitemap_path)
    assert sitemap_path.exists()
    sitemap_content = sitemap_path.read_text()
    assert "<urlset" in sitemap_content
    assert "<loc>/test</loc>" in sitemap_content
    assert "<loc>/test2</loc>" in sitemap_content
    assert "<changefreq>daily</changefreq>" in sitemap_content
    assert "<changefreq>hourly</changefreq>" in sitemap_content


@pytest.mark.anyio(backends=["asyncio"])
async def test_sitemap_write_default_path(
    sitemap: MockSitemap, config: Config, tmp_path: Path
) -> None:
    config.storage.local_path = tmp_path
    config.storage.local_fs = True
    await sitemap.init()
    await sitemap.add_url("/test")
    await sitemap.add_url("/test2", change_freq="daily")
    await sitemap.write()
    sitemap_path = tmp_path / "sitemap.xml"
    assert sitemap_path.exists()
    sitemap_content = sitemap_path.read_text()
    assert "<urlset" in sitemap_content
    assert "<loc>/test</loc>" in sitemap_content
    assert "<loc>/test2</loc>" in sitemap_content
    assert "<changefreq>daily</changefreq>" in sitemap_content
    assert "<changefreq>hourly</changefreq>" in sitemap_content


class TestSitemapGeneration:
    @pytest.fixture
    def sample_urls(self) -> list[SitemapURL]:
        return [
            SitemapURL(
                loc="https://example.com/",
                lastmod=datetime.now(),
                changefreq="daily",
                priority=1.0,
            ),
            SitemapURL(
                loc="https://example.com/about",
                lastmod=datetime.now(),
                changefreq="weekly",
                priority=0.8,
            ),
            SitemapURL(
                loc="https://example.com/blog",
                lastmod=datetime.now(),
                changefreq="daily",
                priority=0.9,
            ),
        ]

    @pytest.mark.asyncio
    async def test_empty_sitemap_generation(self, sitemap: Any) -> None:
        result: str = await sitemap.generate()
        assert result.startswith("<?xml")
        assert "urlset" in result
        assert "xmlns" in result

    @pytest.mark.asyncio
    async def test_sitemap_with_urls(
        self, sitemap: Any, sample_urls: list[SitemapURL]
    ) -> None:
        for url in sample_urls:
            await sitemap.add_url(
                url=url.loc,
                priority=url.priority,
                change_freq=url.changefreq,
                lastmod=url.lastmod,
            )

        result: str = await sitemap.generate()
        assert all(url.loc in result for url in sample_urls)
        assert "<priority>" in result
        assert "<changefreq>" in result
        assert "<lastmod>" in result

    @pytest.mark.parametrize(
        "url,priority",
        [
            ("https://example.com/", 1.0),
            ("https://example.com/about", 0.8),
            ("https://example.com/contact", 0.5),
        ],
    )
    @pytest.mark.asyncio
    async def test_url_priority(self, sitemap: Any, url: str, priority: float) -> None:
        await sitemap.add_url(url=url, priority=priority)
        result: str = await sitemap.generate()
        assert f"<priority>{priority}</priority>" in result

    @pytest.mark.parametrize(
        "change_freq",
        ["always", "hourly", "daily", "weekly", "monthly", "yearly", "never"],
    )
    @pytest.mark.asyncio
    async def test_change_frequency(self, sitemap: Any, change_freq: str) -> None:
        await sitemap.add_url(url="https://example.com/", change_freq=change_freq)
        result: str = await sitemap.generate()
        assert f"<changefreq>{change_freq}</changefreq>" in result


class TestSitemapValidation:
    @pytest.mark.parametrize(
        "invalid_url",
        [
            "not_a_url",
            "ftp://example.com",
            "http://invalid space.com",
        ],
    )
    @pytest.mark.asyncio
    async def test_invalid_urls(self, sitemap: Any, invalid_url: str) -> None:
        with pytest.raises(ValueError):
            await sitemap.add_url(url=invalid_url)

    @pytest.mark.parametrize(
        "invalid_priority",
        [
            -0.1,
            1.1,
            "high",
            None,
        ],
    )
    @pytest.mark.asyncio
    async def test_invalid_priority(self, sitemap: Any, invalid_priority: Any) -> None:
        with pytest.raises(ValueError):
            await sitemap.add_url(url="https://example.com", priority=invalid_priority)

    @pytest.mark.parametrize(
        "invalid_change_freq",
        [
            "sometimes",
            "bi-weekly",
            "annually",
            123,
        ],
    )
    @pytest.mark.asyncio
    async def test_invalid_change_frequency(
        self, sitemap: Any, invalid_change_freq: Any
    ) -> None:
        with pytest.raises(ValueError):
            await sitemap.add_url(
                url="https://example.com", change_freq=invalid_change_freq
            )
