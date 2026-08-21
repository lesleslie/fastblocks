"""Type-safe Tabs component over ``fastblocks_ui.tabs``.

Hand-written (WS-16 carve-out): ``items`` is
``list[tuple[str, str, object]]`` (tab id, tab label, panel content) --
outside codegen's flat-field scope.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from fastblocks_ui import tabs as _tabs
from htmy import Context

from ..base import FastBlocksComponent


@dataclass
class Tabs(FastBlocksComponent):
    """An accessible tablist/panel group. Thin wrapper over :func:`fastblocks_ui.tabs`.

    ``items`` is a list of ``(tab_id, tab_label, panel_content)`` tuples,
    matching the helper exactly.
    """

    items: list[tuple[str, str, object]] = field(default_factory=list)
    active_id: str | None = None
    label: str = "Tabs"
    custom_element: bool = False

    class_: object = None
    attrs: dict[str, Any] = field(default_factory=dict)

    def _markup(self, context: Context) -> str:
        return str(
            _tabs(
                self.items,
                active_id=self.active_id,
                label=self.label,
                custom_element=self.custom_element,
                class_=self.class_,
                **self.attrs,
            )
        )
