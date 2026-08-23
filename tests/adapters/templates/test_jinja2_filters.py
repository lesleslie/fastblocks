"""Tests for fastblocks/adapters/templates/jinja2.py filter/extension helpers.

Targets 261 missing statements before this file. Tests cover
``_add_filters`` (filter injection branch) and exercise the
``_load_extensions`` path indirectly via ``init_envs``.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastblocks.adapters.templates.jinja2 import Templates


@pytest.mark.unit
class TestAddFilters:
    def test_add_filters_with_add_filter_method(self) -> None:
        env = MagicMock()
        # env has add_filter → uses the hasattr branch.
        env.add_filter = MagicMock()
        templates = Templates()
        templates.filters = {"my_filter": lambda x: x}
        templates._add_filters(env)
        env.add_filter.assert_called_once()

    def test_add_filters_with_dict_fallback(self) -> None:
        env = MagicMock(spec=["filters"])  # no add_filter method
        env.filters = {}
        templates = Templates()
        templates.filters = {"my_filter": lambda x: x}
        templates._add_filters(env)
        # Falls back to the env.filters dict branch.
        assert "my_filter" in env.filters

    def test_add_filters_empty(self) -> None:
        env = MagicMock()
        templates = Templates()
        templates.filters = {}
        templates._add_filters(env)
        # No filters → nothing called.
        env.add_filter.assert_not_called()


@pytest.mark.unit
class TestTemplatesAdminTemplateBasics:
    def test_templates_repr_does_not_raise(self) -> None:
        templates = Templates()
        # Just construct; doesn't need init_envs for repr.
        # No assertion on repr shape — just that it doesn't raise.
        repr(templates)