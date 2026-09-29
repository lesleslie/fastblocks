"""Skeleton admin adapter — does NOT bind any routes by default.

Same contract as ``adapters/auth.py``: consumers register their own admin
routes (model CRUD, dashboard, audit log, etc.) on top of this adapter.

# req: REQ-P2-B1-004
"""

from __future__ import annotations

import fastblocks.adapters.admin as _admin


def build() -> object:
    """Return the admin adapter module — no routes bound by default."""
    return _admin
