import typing as t
from dataclasses import dataclass
from datetime import datetime

from acb.config import AdapterBase, Settings


@dataclass
class SitemapURL:
    loc: str
    lastmod: datetime | None = None
    changefreq: (
        t.Literal["always", "hourly", "daily", "weekly", "monthly", "yearly", "never"]
        | None
    ) = None
    priority: float | None = None


class SitemapBaseSettings(Settings):
    change_freq: t.Literal[
        "always",
        "hourly",
        "daily",
        "weekly",
        "monthly",
        "yearly",
        "never",
    ] = "hourly"


class SitemapProtocol(t.Protocol):
    sitemap: t.Any = None


class SitemapBase(AdapterBase):
    sitemap: t.Any = None
