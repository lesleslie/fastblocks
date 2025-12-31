import typing as t
from dataclasses import dataclass
from datetime import datetime

# Oneiric imports
from oneiric.core.config import OneiricSettings


@dataclass
class SitemapURL:
    loc: str
    lastmod: datetime | None = None
    changefreq: (
        t.Literal["always", "hourly", "daily", "weekly", "monthly", "yearly", "never"]
        | None
    ) = None
    priority: float | None = None


class SitemapBaseSettings(OneiricSettings):
    module: str = "native"
    domain: str = ""
    change_freq: t.Literal[
        "always",
        "hourly",
        "daily",
        "weekly",
        "monthly",
        "yearly",
        "never",
    ] = "weekly"
    cache_ttl: int = 3600

    strategy_options: dict[str, t.Any] = {
        "include_patterns": [],
        "exclude_patterns": ["^/admin/.*", "^/api/.*", ".*/__.*"],
        "static_urls": [],
        "model_configs": [],
        "background_refresh": True,
        "cache_warmup": False,
    }

    def __init__(self, **data: dict) -> None:
        super().__init__(**data)


class SitemapProtocol(t.Protocol):
    sitemap: t.Any = None


class SitemapBase:
    category = "sitemap"
    settings_klass = SitemapBaseSettings
    sitemap: t.Any = None
