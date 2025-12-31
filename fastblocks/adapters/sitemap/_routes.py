import typing as t

from starlette.routing import Route


# Custom implementations for ACB compatibility
class AdapterStatus:
    """Custom AdapterStatus for Oneiric compatibility."""

    STABLE = "STABLE"
    BETA = "BETA"
    ALPHA = "ALPHA"
    EXPERIMENTAL = "EXPERIMENTAL"


def debug(msg: str) -> None:
    """Custom debug function for Oneiric compatibility."""
    print(f"[DEBUG] {msg}")


from oneiric.core.resolution import Resolver

# Oneiric resolver for dependency injection
depends = Resolver()


def import_adapter(adapter_name: str) -> None:
    """Custom implementation for Oneiric compatibility."""
    return None


from fastblocks.adapters.sitemap._base import SitemapProtocol


def get_sitemap_adapter() -> SitemapProtocol:
    return t.cast("SitemapProtocol", import_adapter("sitemap"))


def sitemap_endpoint(request: t.Any) -> t.Any:
    adapter = get_sitemap_adapter()
    return depends.get(adapter.sitemap)(request)


routes = [Route("/sitemap.xml", sitemap_endpoint)]
sitemap_routes: dict[str, t.Any] = {"sitemap_endpoint": sitemap_endpoint}
