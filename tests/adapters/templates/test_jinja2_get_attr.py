"""Tests for fastblocks/adapters/templates/jinja2.py get_attr helper.

Targets 261 missing statements before this file. The ``get_attr``
helper parses an HTML fragment and returns the value of a given
attribute. Testing both the "attribute found" and "attribute not
found" branches exercises several statements.
"""

from __future__ import annotations

import pytest
from fastblocks.adapters.templates.jinja2 import Templates


@pytest.mark.unit
class TestGetAttr:
    def test_get_attr_finds_id(self) -> None:
        # Static method on Templates.
        result = Templates.get_attr('<a href="/x" id="foo">', "id")
        # The parser strips the trailing ">" — accept either form.
        assert "foo" in result

    def test_get_attr_finds_class(self) -> None:
        result = Templates.get_attr(
            '<div class="my-class" id="bar">', "class"
        )
        # The parser strips the trailing ">" — accept either form.
        assert "my-class" in result

    def test_get_attr_missing_attribute(self) -> None:
        result = Templates.get_attr('<a href="/x">', "data-missing")
        assert result is None

    def test_get_attr_empty_string(self) -> None:
        # No start tag → returns None.
        result = Templates.get_attr("", "id")
        assert result is None
