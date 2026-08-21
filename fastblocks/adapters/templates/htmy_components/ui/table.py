"""Type-safe Table component over ``fastblocks_ui.table``."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from fastblocks_ui import table as _table
from htmy import Context

from ..base import FastBlocksComponent


@dataclass
class Table(FastBlocksComponent):
    """A styled table. Thin wrapper over :func:`fastblocks_ui.table`."""

    headers: list[str]
    rows: list[list[object]] = field(default_factory=list)
    striped: bool = False
    hoverable: bool = False
    bordered: bool = False
    fullwidth: bool = False

    class_: object = None
    attrs: dict[str, Any] = field(default_factory=dict)

    def _markup(self, context: Context) -> str:
        return str(
            _table(
                self.headers,
                self.rows,
                striped=self.striped,
                hoverable=self.hoverable,
                bordered=self.bordered,
                fullwidth=self.fullwidth,
                class_=self.class_,
                **self.attrs,
            )
        )
