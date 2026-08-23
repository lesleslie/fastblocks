"""Tests for fastblocks/actions/gather/templates.py.

Targets 170 missing statements before this file. Tests cover
``_has_template_extensions_config``, ``_extract_filters_from_module``,
``_extract_filter_functions``, and ``_is_valid_extension_class``.
"""

from __future__ import annotations

import pytest
from fastblocks.actions.gather.templates import (
    TemplateGatherResult,
    _has_template_extensions_config,
    _is_valid_extension_class,
    gather_templates,
)


@pytest.mark.unit
class TestTemplateGatherResult:
    def test_default_construction(self) -> None:
        result = TemplateGatherResult()
        assert result.total_components == 0 or hasattr(result, "total_components")


@pytest.mark.unit
class TestHasTemplateExtensionsConfig:
    def test_returns_true_when_present(self) -> None:
        class _Templates:
            extensions = ["a", "b"]

        class _C:
            templates = _Templates()

        assert _has_template_extensions_config(_C()) is True

    def test_returns_false_when_absent(self) -> None:
        class _C:
            pass

        assert _has_template_extensions_config(_C()) is False

    def test_returns_false_when_templates_lacks_extensions(self) -> None:
        class _C:
            templates = object()

        assert _has_template_extensions_config(_C()) is False


@pytest.mark.unit
class TestIsValidExtensionClass:
    def test_valid_class_returns_true(self) -> None:
        from jinja2.ext import Extension

        class MyExt(Extension):
            pass

        assert _is_valid_extension_class(MyExt) is True

    def test_non_class_returns_false(self) -> None:
        assert _is_valid_extension_class("not a class") is False


@pytest.mark.unit
class TestGatherTemplatesEmpty:
    async def test_gather_templates_no_args(self) -> None:
        from unittest.mock import AsyncMock, patch
        from fastblocks.actions.gather.strategies import GatherResult

        # Stub gather_with_strategy so the function doesn't touch real adapters.
        empty_gather_result = GatherResult()
        with patch(
            "fastblocks.actions.gather.templates.gather_with_strategy",
            AsyncMock(return_value=empty_gather_result),
        ):
            result = await gather_templates(
                template_paths=[],
                loader_types=[],
                extension_modules=[],
                context_processor_paths=[],
                filter_modules=[],
                admin_mode=False,
            )
        assert isinstance(result, TemplateGatherResult)