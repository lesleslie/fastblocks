"""Templates adapter — registers Jinja2 / hybrid renderer with FastBlocks.

Replace this with a custom adapter if you need HTMY, Mako, or async-renderer
support. The default ``HybridTemplatesManager`` lives at
``fastblocks.adapters.templates.hybrid``.

# req: REQ-P2-B2-001
"""

from __future__ import annotations

import fastblocks.adapters.templates.hybrid as _hybrid


def build() -> object:
    """Return the default HybridTemplatesManager class.

    Callers (e.g. ``register_default_adapters(app)``) are responsible for
    instantiation with the right config.
    """
    return _hybrid.HybridTemplatesManager
