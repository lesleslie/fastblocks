"""FastBlocks adapter bridge for Oneiric.

Hosts the FastBlocks-side observability bindings for Oneiric
resolver events (Phase 6 Task 4). The bridge is intentionally
scoped to the DecisionSpanProcessor — heavier Oneiric integration
(e.g. adapter registration) lives in
``fastblocks.core.resolver`` which is the canonical Phase 1.5
singleton owner.
"""

from __future__ import annotations

from .observability import DecisionSpanProcessor

__all__ = [
    "DecisionSpanProcessor",
]
