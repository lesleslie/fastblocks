"""Type-safe Breadcrumb component over ``fastblocks_ui.breadcrumb``.

Hand-written (WS-16 carve-out): ``items`` is
``list[tuple[object, str | None]]`` -- outside codegen's flat-field scope.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from fastblocks_ui import breadcrumb as _breadcrumb
from htmy import Context

from ..base import FastBlocksComponent


@dataclass
class Breadcrumb(FastBlocksComponent):
    """A breadcrumb trail. Thin wrapper over :func:`fastblocks_ui.breadcrumb`.

    ``items`` is a list of ``(label, url)`` tuples; use ``url=None`` for the
    current page, matching the helper exactly.
    """

    items: list[tuple[object, str | None]] = field(default_factory=list)

    class_: object = None
    attrs: dict[str, Any] = field(default_factory=dict)

    def _markup(self, context: Context) -> str:
        return str(_breadcrumb(self.items))
