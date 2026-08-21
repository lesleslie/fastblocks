"""Type-safe ValidationSummary component over ``fastblocks_ui.validation_summary``.

Hand-written (WS-16 carve-out): ``errors`` is a real three-way union
(``dict[str, object] | list[object] | tuple[object, ...]``) -- codegen
mirrors a single concrete type per field, not a runtime-dispatched union, so
this is written by hand rather than generated.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from fastblocks_ui import validation_summary as _validation_summary
from htmy import Context

from ..base import FastBlocksComponent


@dataclass
class ValidationSummary(FastBlocksComponent):
    """Aggregated form-error summary. Thin wrapper over
    :func:`fastblocks_ui.validation_summary`.

    ``errors`` accepts a ``dict[field_name, error_message]`` (renders each
    value as a link to ``#field_name``) or a flat ``list``/``tuple`` of
    messages (renders each as plain list items), matching the helper's
    three-way dispatch exactly. Falsy values are skipped either way.
    """

    errors: dict[str, object] | list[object] | tuple[object, ...] = field(
        default_factory=dict
    )
    title: object = "Please correct the errors below."

    class_: object = None
    attrs: dict[str, Any] = field(default_factory=dict)

    def _markup(self, context: Context) -> str:
        return str(_validation_summary(self.errors, title=self.title))
