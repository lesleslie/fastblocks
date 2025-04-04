import pytest
from acb.adapters import import_adapter
from acb.config import Config
from acb.depends import depends
from anyio import Path

Sitemap = import_adapter()


@pytest.fixture
def config() -> Config:
    config = Config()
    return config


@pytest.fixture
def sitemap(config: Config) -> Sitemap:
    sitemap = depends.get()
    return sitemap


@pytest.mark.anyio
async def test_sitemap_init(sitemap: Sitemap, config: Config) -> None:
    await sitemap.init()
    assert sitemap.sitemap is not None
    assert sitemap.sitemap.change_freq == "hourly"


@pytest.mark.anyio
async def test_sitemap_add_url(sitemap: Sitemap, config: Config) -> None:
    await sitemap.init()
    await sitemap.add_url("/test")
    assert len(sitemap.sitemap.urls) == 1
    assert sitemap.sitemap.urls[0].loc == "/test"
    await sitemap.add_url("/test2", change_freq="daily")
    assert len(sitemap.sitemap.urls) == 2
    assert sitemap.sitemap.urls[1].loc == "/test2"
    assert sitemap.sitemap.urls[1].change_freq == "daily"


@pytest.mark.anyio
async def test_sitemap_add_url_invalid_change_freq(
    sitemap: Sitemap, config: Config
) -> None:
    await sitemap.init()
    with pytest.raises(ValueError):
        await sitemap.add_url("/test", change_freq="invalid")


@pytest.mark.anyio
async def test_sitemap_generate(sitemap: Sitemap, config: Config) -> None:
    await sitemap.init()
    await sitemap.add_url("/test")
    await sitemap.add_url("/test2", change_freq="daily")
    sitemap_xml = await sitemap.generate()
    assert isinstance(sitemap_xml, str)
    assert "<urlset" in sitemap_xml
    assert "<loc>/test</loc>" in sitemap_xml
    assert "<loc>/test2</loc>" in sitemap_xml
    assert "<changefreq>daily</changefreq>" in sitemap_xml
    assert "<changefreq>hourly</changefreq>" in sitemap_xml


@pytest.mark.anyio
async def test_sitemap_write(sitemap: Sitemap, config: Config, tmp_path: Path) -> None:
    await sitemap.init()
    await sitemap.add_url("/test")
    await sitemap.add_url("/test2", change_freq="daily")
    sitemap_path = tmp_path / "sitemap.xml"
    await sitemap.write(sitemap_path)
    assert await sitemap_path.exists()
    sitemap_content = await sitemap_path.read_text()
    assert "<urlset" in sitemap_content
    assert "<loc>/test</loc>" in sitemap_content
    assert "<loc>/test2</loc>" in sitemap_content
    assert "<changefreq>daily</changefreq>" in sitemap_content
    assert "<changefreq>hourly</changefreq>" in sitemap_content


@pytest.mark.anyio
async def test_sitemap_write_default_path(
    sitemap: Sitemap, config: Config, tmp_path: Path
) -> None:
    config.storage.local_path = tmp_path
    config.storage.local_fs = True
    await sitemap.init()
    await sitemap.add_url("/test")
    await sitemap.add_url("/test2", change_freq="daily")
    await sitemap.write()
    sitemap_path = tmp_path / "sitemap.xml"
    assert await sitemap_path.exists()
    sitemap_content = await sitemap_path.read_text()
    assert "<urlset" in sitemap_content
    assert "<loc>/test</loc>" in sitemap_content
    assert "<loc>/test2</loc>" in sitemap_content
    assert "<changefreq>daily</changefreq>" in sitemap_content
    assert "<changefreq>hourly</changefreq>" in sitemap_content
