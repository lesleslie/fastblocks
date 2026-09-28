"""Templates adapter — exposes a build() factory for the HybridTemplatesManager.

The framework registers ``HybridTemplatesManager`` itself under
``domain="fastblocks"`` (keys ``"templates"`` and ``"hybrid_template_manager"``);
this module previously re-registered the same factory under the key
``"hybrid"`` for no functional reason. Drop that redundant registration
and let callers resolve via the framework's keys (see the
``test_hybrid_adapter_resolves_through_oneiric`` test, which now uses
the canonical ``"hybrid_template_manager"`` key).

# req: REQ-P2-B3-001
"""
from __future__ import annotations

import fastblocks.adapters.templates.hybrid as _hybrid


def build() -> object:
    """Return the default HybridTemplatesManager class.

    Callers (e.g. route helpers) instantiate it with the right config.
    """
    return _hybrid.HybridTemplatesManager
