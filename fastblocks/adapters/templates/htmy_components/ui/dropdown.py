"""Type-safe Dropdown component over ``fastblocks_ui.dropdown``.

Hand-written (WS-16 carve-out): ``items`` is ``list[tuple[object, object]]``
(label, href) -- outside codegen's flat-field scope.

Renamed from ``Menu`` in fastblocks-ui 0.8.0, which renamed the underlying
helper and its ``.ui-menu`` classes to ``dropdown`` -- ``ui-nav-list`` was named
to avoid implying kinship with this component, and the rename removed the
ambiguity at its source.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from fastblocks_ui import dropdown as _dropdown
from htmy import Context

from ..base import FastBlocksComponent


@dataclass
class Dropdown(FastBlocksComponent):
    """A disclosure/navigation dropdown. Thin wrapper over
    :func:`fastblocks_ui.dropdown`.

    ``items`` is a list of ``(text, href)`` tuples, matching the helper exactly.

    ``id`` is required, not optional: the panel is a popover opened by a sibling
    ``<button popovertarget="{id}">``, so it needs a stable target. That is the
    htmx stable-ID constraint surfacing in the API, as it does for
    :class:`Drawer` and :class:`Dialog`.

    ``custom_element`` is gone -- ``<ui-dropdown>`` was removed in 0.8.0 once
    the Popover API took over, so the helper raises ``TypeError`` for it.
    """

    items: list[tuple[object, object]] = field(default_factory=list)
    id: str = ""
    label: str = "Menu"

    class_: object = None
    attrs: dict[str, Any] = field(default_factory=dict)

    def _markup(self, context: Context) -> str:
        return str(
            _dropdown(
                self.items,
                id=self.id,
                label=self.label,
                class_=self.class_,
                **self.attrs,
            )
        )
