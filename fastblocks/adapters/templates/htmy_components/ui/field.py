"""Type-safe Field component over ``fastblocks_ui.field``."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from fastblocks_ui import field as _field
from htmy import Context

from ..base import FastBlocksComponent


@dataclass
class Field(FastBlocksComponent):
    """A form field group (label + control + help/error).

    Thin wrapper over :func:`fastblocks_ui.field`; auto-wires ``aria-describedby``
    and ``aria-invalid`` exactly as the helper does.
    """

    label: object | None = None
    help_text: object | None = None
    error_text: object | None = None
    control_html: object = ""
    control_id: str | None = None

    class_: object = None
    attrs: dict[str, Any] = field(default_factory=dict)

    def _markup(self, context: Context) -> str:
        return str(
            _field(
                label=self.label,
                help_text=self.help_text,
                error_text=self.error_text,
                control_html=self.control_html,
                control_id=self.control_id,
                class_=self.class_,
                **self.attrs,
            )
        )
