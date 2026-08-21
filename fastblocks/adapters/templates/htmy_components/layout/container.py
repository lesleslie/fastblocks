"""Type-safe Container component over ``fastblocks_ui.container``."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from fastblocks_ui import container as _container
from htmy import Context

from ..base import FastBlocksComponent


@dataclass
class Container(FastBlocksComponent):
    """Centered, width-constrained container.

    ``content`` should be pre-rendered HTML (a ``str`` or a ``fastblocks_ui``
    ``SafeHTML``). Nesting raw htmy components is a follow-up (it requires async
    child rendering, which the sync string-helper bridge does not yet do).
    """

    content: object = None
    fluid: bool = False
    widescreen: bool = False
    fullhd: bool = False

    class_: object = None
    attrs: dict[str, Any] = field(default_factory=dict)

    def _markup(self, context: Context) -> str:
        return str(
            _container(
                self.content,
                fluid=self.fluid,
                widescreen=self.widescreen,
                fullhd=self.fullhd,
                class_=self.class_,
                **self.attrs,
            )
        )
