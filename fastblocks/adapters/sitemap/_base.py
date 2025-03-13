import typing as t

from acb.config import AdapterBase, Settings


class SitemapBaseSettings(Settings):
    change_freq: t.Literal[
        "always", "hourly", "daily", "weekly", "monthly", "yearly", "never"
    ] = "hourly"


class SitemapProtocol(t.Protocol):
    sitemap: t.Any = None


class SitemapBase(AdapterBase): ...
