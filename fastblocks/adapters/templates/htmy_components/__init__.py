"""FastBlocks HTMY typed components (Phase 1B Deliverable C4 — absorbed from standalone).

__absorbed_from__: fastblocks-htmy@0.5.0 (commit 32ec2fabbd64d2bd9968e09156a94a54cd8f568d, fetched 2026-08-21)

Previously distributed as the standalone ``fastblocks-htmy`` PyPI package. The
typed-component layer (32 component classes + ``FastBlocksComponent`` base) is
absorbed into fastblocks proper as of 2026-08-21 (fastblocks 0.31.x); see
CHANGELOG.md for the migration. Users who previously pinned
``fastblocks-htmy>=0.5,<0.6`` should drop that dependency and import from this
module instead. ``fastblocks-htmy 0.6.x`` is a shim-only release that re-exports
from this module — see Deliverable C5 in
``docs/superpowers/plans/2026-08-21-style-renderer-architecture.md``.

Phase 1B Deliverable C4: replaces the standalone's
``_check_fastblocks_ui()`` import-time warning with a soft
``warnings.warn(...)`` so manual
``pip install fastblocks-ui==0.9.0 --force-reinstall`` is still surfaced at
runtime. Declarative pyproject pin (``fastblocks-ui>=0.8,<0.9``) is the
authoritative source; the warning only catches ``--force-reinstall`` edge cases.
"""

from __future__ import annotations

import warnings

from .base import FastBlocksComponent
from .layout import (
    Column,
    Columns,
    Container,
    Footer,
    Hero,
    Level,
    Media,
    NavGroups,
    NavList,
    Section,
    Shell,
    Tile,
    Title,
)
from .ui import (
    Alert,
    Breadcrumb,
    Burger,
    Button,
    Card,
    Checkbox,
    Dialog,
    Drawer,
    Dropdown,
    Field,
    Input,
    Navbar,
    Pagination,
    Progress,
    Select,
    Switch,
    Table,
    Tabs,
    ValidationSummary,
)

# Soft warning replacement for the standalone's ``_check_fastblocks_ui()``.
# Declarative pyproject pin (``fastblocks-ui>=0.8,<0.9``) is authoritative;
# this only catches manual ``--force-reinstall`` edge cases that bypass the
# resolver. Emitted at import time so manual installs outside the tested
# range surface in startup logs before any render attempt.
try:
    import fastblocks_ui as _fbu

    _installed = tuple(int(p) for p in _fbu.__version__.split(".")[:2])
    if not (_installed and _installed[0] == 0 and 8 <= _installed[1] < 9):
        warnings.warn(
            f"fastblocks-ui {_fbu.__version__} outside tested range [0.8, 0.9); "
            "behavior undefined",
            RuntimeWarning,
            stacklevel=1,
        )
except ImportError:
    # fastblocks-ui is a required runtime dep (since 0.30.0); if it's missing
    # entirely, the import error will surface elsewhere. No warning here.
    pass


__version__ = "0.6.0"  # bumped per C5; tracks fastblocks-htmy 0.6.x shim release

__all__ = [
    # Base class
    "FastBlocksComponent",
    # 32 typed component classes
    "Alert",
    "Breadcrumb",
    "Burger",
    "Button",
    "Card",
    "Checkbox",
    "Column",
    "Columns",
    "Container",
    "Dialog",
    "Drawer",
    "Dropdown",
    "Field",
    "Footer",
    "Hero",
    "Input",
    "Level",
    "Media",
    "Navbar",
    "NavGroups",
    "NavList",
    "Pagination",
    "Progress",
    "Section",
    "Select",
    "Shell",
    "Switch",
    "Table",
    "Tabs",
    "Tile",
    "Title",
    "ValidationSummary",
    # Version
    "__version__",
]
