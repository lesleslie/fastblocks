"""Type-safe NavList component over ``fastblocks_ui.nav_list``.

Hand-written carve-out: ``items`` is ``list[tuple[object, str]]`` (label, href),
outside codegen's flat-field scope. Added for fastblocks-ui 0.8.0.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from fastblocks_ui import nav_list as _nav_list
from htmy import Context

from ..base import FastBlocksComponent


@dataclass
class NavList(FastBlocksComponent):
    """A vertical in-flow navigation list.

    This is the sidebar list, NOT the dropdown: :class:`Dropdown` renders a
    popover that overlays the page, while this stays in flow.

    ``aria_current`` is a parameter because the list cannot know whether its
    links change pages or only move the viewport -- in-page anchors want
    ``location``, since ``page`` would announce "current page" for a link that
    never leaves it.
    """

    items: list[tuple[object, str]] = field(default_factory=list)
    # `str | None`, not `object`: unlike `class_`/labels (which are rendered,
    # so anything stringifiable works), `active` is *compared* against each
    # item's href to decide which link gets `aria-current`. A non-str here
    # simply never matches, silently marking nothing active.
    active: str | None = None
    aria_current: str = "true"

    class_: object = None
    attrs: dict[str, Any] = field(default_factory=dict)

    def _markup(self, context: Context) -> str:
        return str(
            _nav_list(
                self.items,
                active=self.active,
                aria_current=self.aria_current,
                class_=self.class_,
                **self.attrs,
            )
        )
