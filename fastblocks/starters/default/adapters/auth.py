"""Skeleton auth adapter — does NOT bind any routes by default.

Per Phase 2 contract point 4, this scaffold deliberately exposes no URL
surface. Consumers wire their own provider (OAuth, JWT, session, etc.) and
register routes on top of the registered adapter. Auto-mounting an empty
``/login`` here would be a foot-gun, not a scaffold.

# req: REQ-P2-B1-004
"""
from __future__ import annotations

import fastblocks.adapters.auth as _auth


def build() -> object:
    """Return the auth adapter module — no routes bound by default."""
    return _auth
