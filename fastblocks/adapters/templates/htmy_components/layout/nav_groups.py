"""Type-safe NavGroups component over ``fastblocks_ui.nav_groups``.

Hand-written carve-out: ``groups`` is
``list[tuple[object, list[tuple[object, str]]]]`` -- a nested shape well outside
codegen's flat-field scope. Added for fastblocks-ui 0.8.0.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from fastblocks_ui import nav_groups as _nav_groups
from htmy import Context

from ..base import FastBlocksComponent


@dataclass
class NavGroups(FastBlocksComponent):
    """Labelled groups of navigation links.

    ``groups`` is a list of ``(label, items)`` pairs, where each ``items`` is
    the same ``(text, href)`` list :class:`NavList` takes. Named plural because
    it takes several groups, not one.
    """

    groups: list[tuple[object, list[tuple[object, str]]]] = field(default_factory=list)
    # See NavList: `active` is compared against hrefs, not rendered, so it is
    # `str | None` rather than the `object` used for renderable fields.
    active: str | None = None
    aria_current: str = "true"

    class_: object = None
    attrs: dict[str, Any] = field(default_factory=dict)

    def _markup(self, context: Context) -> str:
        return str(
            _nav_groups(
                self.groups,
                active=self.active,
                aria_current=self.aria_current,
                class_=self.class_,
                **self.attrs,
            )
        )
