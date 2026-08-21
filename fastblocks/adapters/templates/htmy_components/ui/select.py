"""Type-safe Select component over ``fastblocks_ui.select``.

Hand-written (WS-16 carve-out): ``options`` is ``list[tuple[object, object]]``
-- codegen mirrors flat scalar/annotation fields, not tuple-shaped list
elements, so this is written by hand rather than generated.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from fastblocks_ui import select as _select
from htmy import Context

from ..base import FastBlocksComponent


@dataclass
class Select(FastBlocksComponent):
    """A native ``<select>``. Thin wrapper over :func:`fastblocks_ui.select`."""

    options: list[tuple[object, object]] = field(default_factory=list)
    value: object | None = None

    class_: object = None
    attrs: dict[str, Any] = field(default_factory=dict)

    def _markup(self, context: Context) -> str:
        return str(_select(self.options, value=self.value))
