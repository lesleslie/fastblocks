"""Templates adapter — registers the HybridTemplatesManager with Oneiric.

Mirrors the B1 starter's ``adapters/templates.py`` shape but additionally
registers the hybrid renderer under domain ``fastblocks`` key ``hybrid`` so
``oneiric.core.resolution.Resolver.resolve("fastblocks", "hybrid")``
returns a usable HybridTemplatesManager instance.

# req: REQ-P2-B3-001
"""
from __future__ import annotations

import fastblocks.adapters.templates.hybrid as _hybrid
from fastblocks.adapters.oneiric_helper import register_candidate
from fastblocks.core.resolver import get_resolver


def build() -> object:
    """Return the default HybridTemplatesManager class.

    Callers (e.g. route helpers) instantiate it with the right config.
    """
    return _hybrid.HybridTemplatesManager


# Register the hybrid renderer so a Oneiric resolver lookup for
# ``domain="fastblocks", key="hybrid"`` yields a HybridTemplatesManager
# factory. Mirrors the pattern in ``fastblocks/adapters/templates/hybrid.py``
# where ``register_candidate`` is called with ``domain="fastblocks"`` and
# ``key="hybrid_template_manager"``.
register_candidate(
    get_resolver(),
    domain="fastblocks",
    key="hybrid",
    factory=_hybrid.HybridTemplatesManager,
    metadata={"class": "HybridTemplatesManager"},
)