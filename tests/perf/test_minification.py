"""D7: prove the framework's minification actions actually shrink HTML/CSS.

Two assertions lock down the minify contract:

1. HTML minification reduces the size of a redundant HTML input.
2. CSS minification reduces the size of a redundant CSS input.

Brief API adaptation (per constraint F):

- ``from fastblocks.actions import minify`` would FAIL because
  ``fastblocks/actions/__init__.py`` only exports ``gather``. The
  minify module is at ``fastblocks/actions/minify/__init__.py`` and
  the correct import is ``from fastblocks.actions.minify import minify``.
- The instance exposes ``.html()``, ``.css()``, ``.js()`` methods.
"""
from __future__ import annotations

from fastblocks.actions.minify import minify


def test_html_minification_reduces_size():
    raw = "<html>  <head>   <title>Test</title>  </head>  <body>  <p>  hello  </p>  </body></html>"
    minified = minify.html(raw)
    assert isinstance(minified, str), (
        f"D7: minify.html returned {type(minified).__name__}, expected str"
    )
    assert len(minified) < len(raw), (
        f"D7: minified ({len(minified)}) not smaller than raw ({len(raw)})"
    )


def test_css_minification_reduces_size():
    raw = "body  {  color:  red;  }   /* comment */   p {  margin:  0; }"
    minified = minify.css(raw)
    assert len(minified) < len(raw), (
        f"D7: minified ({len(minified)}) not smaller than raw ({len(raw)})"
    )
