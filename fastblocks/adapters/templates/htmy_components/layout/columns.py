"""Type-safe Columns component over ``fastblocks_ui.columns``.

Hand-written (WS-16 carve-out): the helper's ``*children`` is variadic
positional, which a flat, keyword-mirroring codegen template can't express as
a single dataclass field the way it does for every other layout component
(see ``fastblocks_htmy/layout/_generated.py``). ``children`` is a
``list[object]`` here instead and unpacked at call time.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from fastblocks_ui import columns as _columns
from htmy import Context

from ..base import FastBlocksComponent


@dataclass
class Columns(FastBlocksComponent):
    """A columns grid container. Thin wrapper over :func:`fastblocks_ui.columns`.

    ``children`` should already be rendered markup (e.g. a list of
    :class:`~fastblocks_htmy.layout.Column` instances rendered to ``str``, or
    ``fastblocks_ui`` ``SafeHTML``/``column()`` output) — matching
    :class:`~fastblocks_htmy.layout.Container`'s pre-rendered-content
    convention.
    """

    children: list[object] = field(default_factory=list)
    centered: bool = False
    vcentered: bool = False
    gapless: bool = False
    multiline: bool = True

    class_: object = None
    attrs: dict[str, Any] = field(default_factory=dict)

    def _markup(self, context: Context) -> str:
        return str(
            _columns(
                *self.children,
                centered=self.centered,
                vcentered=self.vcentered,
                gapless=self.gapless,
                multiline=self.multiline,
                class_=self.class_,
                **self.attrs,
            )
        )
