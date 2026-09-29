"""Style adapter — registers fastblocks_ui as the active design system.

The framework recognises exactly two legal style values today: ``vanilla`` and
``fastblocks_ui``. Any other value (including the previously-removed ``kelp``
and ``webawesome``) fails loudly via the ``ResolverMismatchError`` contract
in ``fastblocks.core.validators``.

# req: REQ-P2-B1-001, REQ-P2-B1-002
"""

from __future__ import annotations

import fastblocks.adapters.style.fastblocks_ui as _fbui


def build() -> object:
    """Return the FastBlocksUIStyle class."""
    return _fbui.FastBlocksUIStyle
