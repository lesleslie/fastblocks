"""Tests for fastblocks/adapters/templates/_advanced_manager.py init paths.

Targets 242 missing statements in ``_advanced_manager.py``. The
``_initialize_base_templates`` and ``_initialize_advanced_features``
methods are core initialization paths; testing them with stubs exercises
~25 statements per test.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastblocks.adapters.templates._advanced_manager import (
    HybridTemplatesManager,
    HybridTemplatesSettings,
)


@pytest.fixture
def manager() -> HybridTemplatesManager:
    return HybridTemplatesManager(settings=HybridTemplatesSettings())


@pytest.mark.unit
class TestInitializeBaseTemplates:
    async def test_initialize_base_templates_with_resolved(
        self, manager: HybridTemplatesManager
    ) -> None:
        # Stub resolve_instance to return a fake templates object.
        # The function imports ``resolve_instance`` lazily inside the
        # try block, so we patch it at the source module path.
        fake_templates = MagicMock()
        with patch(
            "fastblocks.adapters.oneiric_helper.resolve_instance",
            MagicMock(return_value=fake_templates),
        ):
            # The function calls ``resolve_instance`` indirectly via the
            # depends global; we patch that to ensure the right branch
            # is exercised.
            with patch(
                "fastblocks.adapters.templates._advanced_manager.resolve_instance",
                MagicMock(return_value=fake_templates),
            ):
                await manager._initialize_base_templates()
        # No assertion: the contract is that _initialize_base_templates
        # does not raise when resolve_instance returns the fake adapter.
        # (Originally a tautological `is None or is not None` was here,
        # removed by multi-agent review F-L3-008.)

    async def test_initialize_base_templates_fallback(
        self, manager: HybridTemplatesManager
    ) -> None:
        # Stub resolve_instance to raise → fallback creates a Templates().
        with patch(
            "fastblocks.adapters.oneiric_helper.resolve_instance",
            MagicMock(side_effect=RuntimeError("no adapter")),
        ):
            # The fallback path creates a Templates(); mock the Templates
            # class so we don't touch real Jinja init.
            with patch(
                "fastblocks.adapters.templates._advanced_manager.Templates",
                MagicMock(),
            ):
                await manager._initialize_base_templates()
        # No assertion: the contract is that the fallback path doesn't
        # raise. The original tautology `is not None or is None` was
        # removed by multi-agent review F-L3-008; a tighter assertion
        # requires investigating the production fallback contract
        # (TODO: follow-up commit).


@pytest.mark.unit
class TestInitializeAdvancedFeatures:
    async def test_initialize_advanced_features_runs_fragments_and_autocomplete(
        self, manager: HybridTemplatesManager
    ) -> None:
        # Stub the discover/build helpers — they have their own coverage.
        manager._discover_fragments = AsyncMock()
        manager._build_autocomplete_index = AsyncMock()
        manager.settings.enable_fragments = True
        manager.settings.enable_autocomplete = True
        await manager._initialize_advanced_features()
        manager._discover_fragments.assert_called_once()
        manager._build_autocomplete_index.assert_called_once()

    async def test_initialize_advanced_features_disabled(
        self, manager: HybridTemplatesManager
    ) -> None:
        manager._discover_fragments = AsyncMock()
        manager._build_autocomplete_index = AsyncMock()
        manager.settings.enable_fragments = False
        manager.settings.enable_autocomplete = False
        await manager._initialize_advanced_features()
        manager._discover_fragments.assert_not_called()
        manager._build_autocomplete_index.assert_not_called()


@pytest.mark.unit
class TestGetTemplateDependencies:
    async def test_get_template_dependencies_empty(
        self, manager: HybridTemplatesManager
    ) -> None:
        # Pre-populate the dependency cache for the trivial case.
        manager._template_dependencies["simple.html"] = set()
        deps = await manager.get_template_dependencies("simple.html")
        assert deps == set()

    async def test_get_template_dependencies_populated(
        self, manager: HybridTemplatesManager
    ) -> None:
        manager._template_dependencies["parent.html"] = {
            "child1.html",
            "child2.html",
        }
        deps = await manager.get_template_dependencies("parent.html")
        assert "child1.html" in deps
        assert "child2.html" in deps
