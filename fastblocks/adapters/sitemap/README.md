# Sitemap Adapter

> **FastBlocks Documentation**: [Main](../../../README.md) | [Core Features](../../README.md) | [Actions](../../actions/README.md) | [Adapters](../README.md)

The Sitemap adapter generates XML sitemaps for FastBlocks applications.

## Overview

The Sitemap adapter allows you to:

- Generate XML sitemaps for search engines
- Define static and dynamic URLs
- Set URL priorities and change frequencies
- Automatically serve sitemaps at `/sitemap.xml`

## Available Implementations

| Implementation | Description |
|----------------|-------------|
| `sitemap` | Default sitemap implementation |

## Configuration

Configure the Sitemap adapter in your settings:

```yaml
# settings/sitemap.yml
sitemap:
  enabled: true
  base_url: "https://example.com"
  cache_timeout: 3600  # 1 hour in seconds
  static_urls:
    - url: "/"
      priority: 1.0
      changefreq: "daily"
    - url: "/about"
      priority: 0.8
      changefreq: "weekly"
    - url: "/contact"
      priority: 0.8
      changefreq: "monthly"
```

## Usage

### Basic Setup

The Sitemap adapter is automatically configured when you install the `sitemap` optional dependency:

```bash
pdm add "fastblocks[sitemap]"
```

The sitemap will be automatically available at `/sitemap.xml`.

### Adding Dynamic URLs

You can add dynamic URLs to the sitemap:

```python
from acb.depends import depends
from acb.adapters import import_adapter
from datetime import datetime

Sitemap = import_adapter("sitemap")
sitemap = depends.get(Sitemap)

# Add blog posts to sitemap
async def add_blog_posts_to_sitemap():
    posts = await get_blog_posts_from_database()
    for post in posts:
        sitemap.add_url(
            url=f"/blog/{post.slug}",
            priority=0.7,
            changefreq="weekly",
            lastmod=post.updated_at or post.created_at
        )

# Call this function during application startup
app.add_event_handler("startup", add_blog_posts_to_sitemap)
```

### Manually Generating Sitemap

You can manually generate the sitemap:

```python
from acb.depends import depends
from acb.adapters import import_adapter
from starlette.responses import Response

Sitemap = import_adapter("sitemap")
sitemap = depends.get(Sitemap)

async def get_sitemap(request):
    sitemap_xml = await sitemap.generate()
    return Response(
        content=sitemap_xml,
        media_type="application/xml"
    )

routes = [
    Route("/custom-sitemap.xml", endpoint=get_sitemap)
]
```

## Settings Reference

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `enabled` | `bool` | `True` | Whether the sitemap is enabled |
| `base_url` | `str` | `""` | The base URL for the sitemap |
| `cache_timeout` | `int` | `3600` | Cache timeout in seconds |
| `static_urls` | `list[dict]` | `[]` | List of static URLs to include |

## Implementation Details

The Sitemap adapter is implemented in the following files:

- `_base.py`: Defines the base class and settings
- `sitemap.py`: Provides the default implementation

### Base Class

```python
from acb.config import AdapterBase, Settings
from datetime import datetime
from typing import Optional, Literal

class SitemapBaseSettings(Settings):
    enabled: bool = True
    base_url: str = ""
    cache_timeout: int = 3600
    static_urls: list[dict] = []

class SitemapBase(AdapterBase):
    def add_url(
        self,
        url: str,
        priority: float = 0.5,
        changefreq: Literal["always", "hourly", "daily", "weekly", "monthly", "yearly", "never"] = "weekly",
        lastmod: Optional[datetime] = None
    ) -> None:
        """Add a URL to the sitemap"""
        raise NotImplementedError()

    async def generate(self) -> str:
        """Generate the sitemap XML"""
        raise NotImplementedError()
```

### Default Implementation

The default implementation uses the [asgi-sitemaps](https://github.com/florimondmanca/asgi-sitemaps) package to generate and serve sitemaps.

## Customization

You can create a custom sitemap adapter for more specialized sitemap needs:

```python
# myapp/adapters/sitemap/custom.py
from fastblocks.adapters.sitemap._base import SitemapBase, SitemapBaseSettings
from datetime import datetime
from typing import Optional, Literal, List, Dict, Any

class CustomSitemapSettings(SitemapBaseSettings):
    image_sitemaps: bool = False

class CustomSitemap(SitemapBase):
    settings: CustomSitemapSettings = None
    urls: List[Dict[str, Any]] = []

    async def init(self) -> None:
        self.urls = []
        for url_data in self.settings.static_urls:
            self.add_url(**url_data)

    def add_url(
        self,
        url: str,
        priority: float = 0.5,
        changefreq: Literal["always", "hourly", "daily", "weekly", "monthly", "yearly", "never"] = "weekly",
        lastmod: Optional[datetime] = None,
        images: Optional[List[Dict[str, str]]] = None
    ) -> None:
        url_data = {
            "url": url,
            "priority": priority,
            "changefreq": changefreq,
        }
        if lastmod:
            url_data["lastmod"] = lastmod.isoformat()
        if images and self.settings.image_sitemaps:
            url_data["images"] = images
        self.urls.append(url_data)

    async def generate(self) -> str:
        # Generate custom XML sitemap
        xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
        xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"'
        if self.settings.image_sitemaps:
            xml += ' xmlns:image="http://www.google.com/schemas/sitemap-image/1.1"'
        xml += '>\n'

        for url_data in self.urls:
            xml += '  <url>\n'
            xml += f'    <loc>{self.settings.base_url}{url_data["url"]}</loc>\n'
            if "lastmod" in url_data:
                xml += f'    <lastmod>{url_data["lastmod"]}</lastmod>\n'
            xml += f'    <changefreq>{url_data["changefreq"]}</changefreq>\n'
            xml += f'    <priority>{url_data["priority"]}</priority>\n'

            if "images" in url_data:
                for image in url_data["images"]:
                    xml += '    <image:image>\n'
                    xml += f'      <image:loc>{image["url"]}</image:loc>\n'
                    if "caption" in image:
                        xml += f'      <image:caption>{image["caption"]}</image:caption>\n'
                    xml += '    </image:image>\n'

            xml += '  </url>\n'

        xml += '</urlset>'
        return xml
```

Then configure your application to use your custom adapter:

```yaml
# settings/adapters.yml
sitemap: custom
```
