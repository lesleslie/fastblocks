"""Type-safe Navbar component over ``fastblocks_ui.navbar``.

Hand-written (WS-16 carve-out): ``items`` is ``list[tuple[object, str]]`` and
the helper has multiple independent content slots (``start``/``end``) on top
of ``brand``/``items`` -- outside codegen's flat-field scope.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from fastblocks_ui import Variant
from fastblocks_ui import navbar as _navbar
from htmy import Context

from ..base import FastBlocksComponent


@dataclass
class Navbar(FastBlocksComponent):
    """A navigation bar. Thin wrapper over :func:`fastblocks_ui.navbar`.

    ``items`` is a list of ``(label, url)`` tuples, matching the helper
    exactly.
    """

    brand: object = None
    items: list[tuple[object, str]] = field(default_factory=list)
    brand_url: str | None = "/"
    start: object = None
    end: object = None
    variant: Variant | None = None

    class_: object = None
    attrs: dict[str, Any] = field(default_factory=dict)

    def _markup(self, context: Context) -> str:
        return str(
            _navbar(
                self.brand,
                self.items,
                brand_url=self.brand_url,
                start=self.start,
                end=self.end,
                variant=self.variant,
                class_=self.class_,
                **self.attrs,
            )
        )
