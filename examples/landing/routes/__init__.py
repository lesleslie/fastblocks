"""Routes package — registers all 8 landing-page routes with the app.

# req: REQ-P2-B2-001
"""

from __future__ import annotations

from fastblocks.applications import FastBlocks

from .adapter_matrix import adapter_matrix_route
from .demo import demo_route
from .docs import docs_route
from .features import features_route
from .home import home_route
from .install import install_route
from .performance import performance_route
from .security import security_route


def register_routes(app: FastBlocks) -> None:
    """Register all 8 B2 routes with the FastBlocks app."""
    app.add_route("/", home_route)
    app.add_route("/features", features_route)
    app.add_route("/adapter-matrix", adapter_matrix_route)
    app.add_route("/demo", demo_route)
    app.add_route("/performance", performance_route)
    app.add_route("/security", security_route)
    app.add_route("/docs", docs_route)
    app.add_route("/install", install_route)
