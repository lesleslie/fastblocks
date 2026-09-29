"""Icons adapter — registers a default icon set.

The framework ships with several icon sets (lucide, heroicons, fontawesome,
materialicons, phosphor, remixicon). Pick one and replace the import below;
``Oneiric`` resolves the rest.

# req: REQ-P2-B1-001
"""

from __future__ import annotations

import fastblocks.adapters.icons.lucide as _lucide


def build() -> object:
    """Return the LucideIcons class."""
    return _lucide.LucideIcons
