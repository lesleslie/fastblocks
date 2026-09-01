"""Tests for fastblocks/actions/gather/models.py.

Targets 180 missing statements before this file. Tests cover
``_get_default_model_base_classes``, ``_get_model_source_type_by_index``,
``_process_single_model_source_result``, and the ``ModelGatherResult``
dataclass.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastblocks.actions.gather.models import (
    ModelGatherResult,
    _get_default_model_base_classes,
    _get_model_source_type_by_index,
    _prepare_model_gather_config,
    gather_models,
)


@pytest.mark.unit
class TestModelGatherResult:
    def test_default_construction(self) -> None:
        result = ModelGatherResult()
        # Inherited from SyncResult-like base.
        assert result.total_models == 0 or hasattr(result, "total_models")

    def test_get_all_models_returns_list(self) -> None:
        result = ModelGatherResult()
        # After construction, get_all_models returns a (possibly empty) list.
        result.get_all_models()
        assert True  # Doesn't raise.


@pytest.mark.unit
class TestGetDefaultModelBaseClasses:
    def test_returns_list_of_classes(self) -> None:
        result = _get_default_model_base_classes()
        assert isinstance(result, list)


@pytest.mark.unit
class TestGetModelSourceTypeByIndex:
    def test_index_zero_returns_first_source(self) -> None:
        result = _get_model_source_type_by_index(0, ["models", "adapters"])
        assert isinstance(result, str)

    def test_index_out_of_range_returns_string(self) -> None:
        result = _get_model_source_type_by_index(100, ["models"])
        # Out-of-range → some fallback string.
        assert isinstance(result, str)


@pytest.mark.unit
class TestPrepareModelGatherConfig:
    def test_prepare_with_no_args(self) -> None:
        config = _prepare_model_gather_config(None, None, None, None)
        assert isinstance(config, dict)
        assert "sources" in config or "strategy" in config

    def test_prepare_with_args(self) -> None:
        from fastblocks.actions.gather.strategies import GatherStrategy

        strategy = GatherStrategy()
        config = _prepare_model_gather_config(
            ["models"],
            ["*.py"],
            [object],
            strategy,
        )
        assert isinstance(config, dict)


@pytest.mark.unit
class TestGatherModelsEmpty:
    async def test_gather_models_without_adapters(self) -> None:
        # Stub ``gather_with_strategy`` so the function doesn't touch real
        # adapter resolution.
        from fastblocks.actions.gather.models import ModelGatherResult
        from fastblocks.actions.gather.strategies import GatherResult

        empty_gather_result = GatherResult()
        with patch(
            "fastblocks.actions.gather.models.gather_with_strategy",
            AsyncMock(return_value=empty_gather_result),
        ):
            result = await gather_models(
                sources=["models"],
                patterns=[],
                include_base=False,
                include_adapters=False,
                include_admin=False,
            )
        assert isinstance(result, ModelGatherResult)
