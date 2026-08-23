"""Phase 5 Hypothesis strategies — shared between 5B and 5C tests.

Custom strategies for property-based testing across the style × renderer
matrix and the XSS regression matrix.
"""

from __future__ import annotations

import dataclasses
import functools

from hypothesis import strategies as st


# Canonical 15-vector SSTI + script payload corpus (inlined as Python literal).
# Per Erratum 17, this stays inline until the corpus grows beyond ~30 vectors,
# at which point we migrate to tests/xss/ssti_payloads.json (created in Task 6).
_UNSAFE_PAYLOADS: tuple[str, ...] = (
    "{{7*7}}", "${7*7}", "#{7*7}}", "<%= 7*7 %>",
    "{{config.__class__.__init__.__globals__['os'].popen('id').read()}}",
    "${T(java.lang.Runtime).getRuntime().exec('id')}",
    "<script>alert(1)</script>",
    "\"><script>alert(1)</script>",
    "javascript:alert(1)",
    "data:text/html,<script>alert(1)</script>",
    "<img src=x onerror=alert(1)>",
    "<svg onload=alert(1)>",
    "'-alert(1)-'",
    "\"; alert(1); //",
    "{{request.application.__globals__.__builtins__.__import__('os').popen('id').read()}}",
)


# Per master plan line 469 + spec §5A.1: safe_user_input alphabet includes
# HTML delimiters `<>"&;(){}[]/=` (all Punctuation-other). Intentionally broader
# than "no-escape-needed" — tests the rendering pipeline's handling of
# HTML-significant characters including the escape path.
_HTML_SAFE_CHARS = st.characters(
    whitelist_categories=("Lu", "Ll", "Nd", "Pc", "Pd", "Po", "Zs"),
    max_codepoint=0xFFFF,
)
_UNSAFE_CHARS = st.characters(
    whitelist_categories=("Lu", "Ll", "Nd", "Pc", "Pd", "Zs", "Po"),
    blacklist_characters=("\n", "\r", "\x00"),
)


safe_user_input: st.SearchStrategy[str] = st.text(
    alphabet=_HTML_SAFE_CHARS, min_size=0, max_size=200,
)

unsafe_input: st.SearchStrategy[str] = st.one_of(
    st.sampled_from(_UNSAFE_PAYLOADS),
    st.text(alphabet=_UNSAFE_CHARS, min_size=1, max_size=200),
)

# 25-name whitelist (master plan §C4 attack vectors). Counted at 25.
attrs_dict: st.SearchStrategy[dict[str, str]] = st.dictionaries(
    keys=st.sampled_from([
        "class", "id", "role", "tabindex",
        "data-test", "data-id", "data-state",
        "aria-label", "aria-hidden", "aria-expanded", "aria-controls",
        "hx-get", "hx-post", "hx-target", "hx-trigger", "hx-swap",
        "hx-vals", "hx-headers", "hx-include", "hx-confirm",
        "name", "value", "type", "placeholder", "title",
    ]),
    values=st.one_of(safe_user_input, unsafe_input),
    max_size=10,
)


# Per Erratum 14: split htmy_component() into three pieces so the assert
# (component count) and the global registry mutation (register_type_strategy)
# happen deterministically at import time. Only the strategy build is cached.
def _build_components() -> tuple[type, ...]:
    """Enumerate absorbed HTMY components at module load.

    Returns a tuple of dataclass types from htmy_components.__all__,
    excluding the FastBlocksComponent base class. Asserts the count
    matches the spec's invariant (32 dataclasses).

    Per spec §5A.1 + Decision 12 erratum: htmy_components.__all__ yields
    34 names total (32 dataclasses + FastBlocksComponent + __version__),
    but only 32 are dataclasses.
    """
    from fastblocks.adapters.templates import htmy_components as _pkg

    components = tuple(
        getattr(_pkg, name)
        for name in _pkg.__all__
        if dataclasses.is_dataclass(getattr(_pkg, name))
        and name != "FastBlocksComponent"
    )
    assert len(components) == 32, (
        f"Expected 32 absorbed HTMY components, got {len(components)}. "
        "Update tests that pin this count or amend "
        "docs/superpowers/specs/2026-08-22-fastblocks-phase-5-design.md."
    )
    return components


def _register_object_strategy() -> None:
    """Register object → safe_user_input at module load.

    Per Erratum 8: this is a process-global mutation. The contamination
    surface is broad (object is the Python type hierarchy root). No other
    test in the suite currently uses st.from_type() for absorbed components,
    so the contamination is acceptable for Phase 5.
    """
    st.register_type_strategy(object, safe_user_input)


# Run at module load — deterministic, before any test imports
_BUILD_COMPONENTS: tuple[type, ...] = _build_components()
_register_object_strategy()


@functools.cache
def htmy_component() -> st.SearchStrategy:
    """Cached strategy that yields an instance of one of the 32 absorbed HTMY components.

    Uses Hypothesis's st.from_type(c) which auto-resolves field types via
    typing.get_type_hints (handles PEP 563 string annotations).

    Cached so the strategy-graph is built once per test session, not per
    Hypothesis example (Decision 8 — was thousands of unnecessary rebuilds
    per CI run with max_examples=100).
    """
    return st.one_of(*[st.from_type(c) for c in _BUILD_COMPONENTS])
