"""Type-safe Button component over ``fastblocks_ui.button``."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from fastblocks_ui import Size, Variant
from fastblocks_ui import button as _button
from htmy import Context

from ..base import FastBlocksComponent


@dataclass
class Button(FastBlocksComponent):
    """A button (or link styled as a button).

    Thin wrapper over :func:`fastblocks_ui.button`; emits identical markup.

    The field is ``label``, matching ``manifest.json``'s param name for the
    button component. It was ``text``, which broke the very cross-repo
    contract this hand-written carve-out exists to honour -- the manifest is
    what the codegen reads, so a carve-out deviating from it silently
    desynchronises the typed layer from the design system.
    """

    label: str
    variant: Variant | None = None
    size: Size | None = None
    href: str | None = None
    type: str = "button"

    class_: object = None
    attrs: dict[str, Any] = field(default_factory=dict)

    def _markup(self, context: Context) -> str:
        return str(
            _button(
                self.label,
                variant=self.variant,
                size=self.size,
                href=self.href,
                type=self.type,
                class_=self.class_,
                **self.attrs,
            )
        )
