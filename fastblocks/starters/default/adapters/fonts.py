"""Fonts adapter — registers the Squirrel font loader.

Squirrel is the framework's preferred font loader (Google Fonts is the
alternative). Replace with the Google Fonts adapter or a custom CDN loader
if your app needs different font sourcing.

# req: REQ-P2-B1-001
"""

from __future__ import annotations

import fastblocks.adapters.fonts.squirrel as _squirrel


def build() -> object:
    """Return the FontSquirrelFonts class."""
    return _squirrel.FontSquirrelFonts
