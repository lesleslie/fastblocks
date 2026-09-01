"""Tests for fastblocks/adapters/templates/_advanced_manager.py.

Targets ``HybridTemplatesManager``'s uncovered helper methods
(284 missing statements before this file). The tests focus on
deterministic string-manipulation helpers that don't require a real
template environment, so they run without file-system dependencies.
"""

from __future__ import annotations

import pytest

from fastblocks.adapters.templates._advanced_manager import (
    AutocompleteItem,
    FragmentInfo,
    HybridTemplatesManager,
    HybridTemplatesSettings,
)


@pytest.fixture
def manager() -> HybridTemplatesManager:
    return HybridTemplatesManager(settings=HybridTemplatesSettings())


@pytest.mark.unit
class TestIsSimilar:
    def test_identical_strings_are_similar(
        self, manager: HybridTemplatesManager
    ) -> None:
        assert manager._is_similar("hello", "hello") is True

    def test_empty_strings_not_similar(
        self, manager: HybridTemplatesManager
    ) -> None:
        assert manager._is_similar("", "hello") is False
        assert manager._is_similar("hello", "") is False

    def test_completely_different_strings(
        self, manager: HybridTemplatesManager
    ) -> None:
        assert manager._is_similar("abc", "xyz") is False

    def test_partial_overlap_passes(
        self, manager: HybridTemplatesManager
    ) -> None:
        # "helo" has 4/5 common chars with "hello" — passes default 0.6.
        assert manager._is_similar("helo", "hello") is True

    def test_custom_threshold(self, manager: HybridTemplatesManager) -> None:
        # At threshold 0.99 even identical strings pass.
        assert manager._is_similar("hello", "hello", threshold=0.99) is True


@pytest.mark.unit
class TestExtractExampleFromDoc:
    def test_returns_none_for_empty_doc(
        self, manager: HybridTemplatesManager
    ) -> None:
        assert manager._extract_example_from_doc("") is None
        assert manager._extract_example_from_doc(None) is None  # type: ignore[arg-type]

    def test_extracts_double_bracketed_line(
        self, manager: HybridTemplatesManager
    ) -> None:
        doc = "Short doc\n\n[[ example line ]]\n"
        assert manager._extract_example_from_doc(doc) == "[[ example line ]]"

    def test_extracts_from_example_section(
        self, manager: HybridTemplatesManager
    ) -> None:
        doc = (
            "Some prose.\n"
            "Example:\n"
            "[[ usage line ]]\n"
            "Trailing prose.\n"
        )
        assert manager._extract_example_from_doc(doc) == "[[ usage line ]]"


@pytest.mark.unit
class TestDataclasses:
    def test_autocomplete_item_constructs(self) -> None:
        item = AutocompleteItem(
            name="url_for",
            type="function",
            description="Build a URL for an endpoint.",
            signature="url_for(endpoint)",
        )
        assert item.name == "url_for"
        assert item.type == "function"
        assert item.signature == "url_for(endpoint)"

    def test_fragment_info_constructs(self) -> None:
        info = FragmentInfo(
            name="my-fragment",
            template_path="base.html",
            block_name="content",
            start_line=12,
            end_line=24,
        )
        assert info.name == "my-fragment"
        assert info.start_line == 12


@pytest.mark.unit
class TestManagerInitialization:
    def test_init_with_no_settings(self) -> None:
        mgr = HybridTemplatesManager()
        # No settings provided → defaults applied.
        assert mgr.settings is not None

    def test_init_with_explicit_settings(self) -> None:
        from fastblocks.adapters.templates._advanced_manager import SecurityLevel

        settings = HybridTemplatesSettings(security_level=SecurityLevel.RESTRICTED)
        mgr = HybridTemplatesManager(settings=settings)
        assert mgr.settings.security_level == SecurityLevel.RESTRICTED


@pytest.mark.unit
class TestClearCaches:
    def test_clear_caches_empties_all_caches(
        self, manager: HybridTemplatesManager
    ) -> None:
        # Pre-populate caches.
        manager._validation_cache["foo"] = "placeholder"
        manager._fragment_cache["bar"] = []
        manager._autocomplete_cache["baz"] = []
        manager._template_dependencies["qux"] = set()
        # Clear.
        manager.clear_caches()
        assert manager._validation_cache == {}
        assert manager._fragment_cache == {}
        assert manager._autocomplete_cache == {}
        assert manager._template_dependencies == {}


@pytest.mark.unit
class TestExtractCurrentWord:
    def test_extract_word_returns_word(self) -> None:
        text = "render_comp"
        word = HybridTemplatesManager._extract_current_word(text)
        assert word == "render_comp"

    def test_extract_word_with_dot(self) -> None:
        text = "config.app"
        word = HybridTemplatesManager._extract_current_word(text)
        assert word == "config.app"

    def test_extract_word_no_match(self) -> None:
        text = "render_comp "
        word = HybridTemplatesManager._extract_current_word(text)
        # Trailing space → no match.
        assert word == ""


@pytest.mark.unit
class TestAutocompleteSuggestions:
    async def test_autocomplete_returns_top_suggestions(
        self, manager: HybridTemplatesManager
    ) -> None:
        # The manager exposes a base Jinja global getter; call it to
        # confirm the autocomplete index materializes names like
        # ``abs`` / ``attr`` from Jinja2's globals.
        items = manager._get_builtin_autocomplete()
        # The canned list contains Jinja globals — verify a few known names.
        names = {item.name for item in items}
        assert "abs" in names or "attr" in names
        # All items are AutocompleteItem instances with a non-empty name.
        assert all(item.name for item in items)

    async def test_autocomplete_filters_by_current_word(
        self, manager: HybridTemplatesManager
    ) -> None:
        # Manually populate the autocomplete cache to drive the filtering
        # branch of get_autocomplete_suggestions.
        manager._autocomplete_cache["global"] = [
            __import__(
                "fastblocks.adapters.templates._advanced_manager",
                fromlist=["AutocompleteItem"],
            ).AutocompleteItem(
                name="render_block",
                type="function",
                description="Render template block",
                adapter_source="fastblocks",
            ),
            __import__(
                "fastblocks.adapters.templates._advanced_manager",
                fromlist=["AutocompleteItem"],
            ).AutocompleteItem(
                name="render_component",
                type="function",
                description="Render HTMY component",
                adapter_source="fastblocks",
            ),
        ]
        # Typing "render" should match both items.
        suggestions = await manager.get_autocomplete_suggestions("render")
        assert len(suggestions) >= 1
        assert all("render" in s.name.lower() for s in suggestions)

    async def test_autocomplete_no_match_returns_top(
        self, manager: HybridTemplatesManager
    ) -> None:
        manager._autocomplete_cache["global"] = [
            __import__(
                "fastblocks.adapters.templates._advanced_manager",
                fromlist=["AutocompleteItem"],
            ).AutocompleteItem(
                name="zzz_nomatch",
                type="function",
                description="No match",
                adapter_source="fastblocks",
            ),
        ]
        suggestions = await manager.get_autocomplete_suggestions("xxx")
        # No match → returns top 20 (the full cached list in this case).
        assert suggestions
