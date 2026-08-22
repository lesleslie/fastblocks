"""Phase 2 source-of-truth module.

Holds the canonical ``StyleName`` Literal, the cross-adapter
``StyleAdapter`` / ``TemplateAdapter`` Protocols (both
``@runtime_checkable``), and the resolver-mismatch error contract.

This module is the **single source of truth** for legal style values.
ADR 0008 Rule3 names this file as the home for Shared Literal sets.
The sync test in ``tests/core/test_validators_sync.py`` enforces that
``AppBaseSettings`` and ``cli.py`` follow this module's Literal set.

Adding a new style value:
1. Edit ``StyleName`` below (add the new member).
2. Re-run ``pytest tests/core/test_validators_sync.py`` — the test
   will FAIL until you update ``AppBaseSettings.style`` and every
   ``cli.py`` ``Literal[...]`` site to reference the new member.

Removing a style value: same as adding, in reverse.

This module must NOT import from ``cli.py`` or
``fastblocks/adapters/app/_base.py`` — those are consumers of this
module's exports, not the other way around.
"""
from __future__ import annotations

import difflib
import typing as t
from typing import Literal, Protocol, runtime_checkable

# ---------------------------------------------------------------------------
# Canonical Literal: legal style values
# ---------------------------------------------------------------------------
StyleName = Literal["vanilla", "fastblocks_ui"]

# Pinned default per master plan §Phase 1A deliverable B.
DEFAULT_STYLE: StyleName = "fastblocks_ui"


# ---------------------------------------------------------------------------
# Protocol contracts — runtime-checkable for isinstance() gates
# ---------------------------------------------------------------------------
@runtime_checkable
class StyleAdapter(t.Protocol):
    """Contract every style adapter module must satisfy.

    A style adapter module at ``fastblocks.adapters.style.<name>``
    implements all four methods. Registration via
    ``register_style_candidate`` verifies
    ``isinstance(module, StyleAdapter)`` — ``@runtime_checkable`` is
    REQUIRED for ``isinstance()`` on method-only Protocols (Python
    3.13).

    Method naming: ``register_style_functions`` (NOT per-style-named
    like ``register_vanilla_functions``). Phase 2 pins the existing
    ``style_registry.py:42`` entry point; the per-style-naming drift
    surface is broken in this commit.
    """

    def register_style_functions(self, env: t.Any) -> None: ...
    def get_css_path(self) -> str: ...
    def get_js_path(self) -> str: ...
    def escape_user_input(self, value: str) -> str: ...


@runtime_checkable
class TemplateAdapter(t.Protocol):
    """Contract every renderer (Jinja2 / HTMY) must satisfy.

    Defined now for Phase 6's Prometheus cardinality lint anchor
    (master plan §Pillar 5). Dispatch refactor lands in a future
    phase; ``register_template_candidate`` is deferred (no consumer
    site today).
    """

    def render(
        self, template: str, context: t.Mapping[str, t.Any]
    ) -> str: ...
    def init_envs(self) -> t.Any: ...


# ---------------------------------------------------------------------------
# Resolver mismatch error contract
# ---------------------------------------------------------------------------
class ResolverMismatchError(ValueError):
    """Raised when a registered value is not in StyleName or vice versa.

    Constructed by :func:`format_resolver_mismatch`; never raised bare.
    Carries the offending value, the legal StyleName set, the nearest-
    neighbor hint (for "Did you mean ...?"), and the single-line
    Oneiric ``explain()`` output for operator debugging.
    """

    def __init__(
        self,
        *,
        value: str,
        legal: tuple[str, ...],
        nearest: str | None,
        resolver_explain: str,
    ) -> None:
        self.value = value
        self.legal = legal
        self.nearest = nearest
        self.resolver_explain = resolver_explain
        msg = (
            f"Style {value!r} is in the registry but not in the legal "
            f"StyleName set {legal}."
        )
        if nearest is not None:
            msg += f" Did you mean {nearest!r}?"
        if resolver_explain and resolver_explain != "<unavailable>":
            msg += f" Resolver explain: {resolver_explain}"
        super().__init__(msg)


# ---------------------------------------------------------------------------
# format_resolution_explanation_one_line
# ---------------------------------------------------------------------------
def format_resolution_explanation_one_line(
    explanation: t.Any,
) -> str:
    """Format a Oneiric ``ResolutionExplanation`` as a single line.

    ``FastblocksRegistry.explain(domain, key)`` returns a
    ``ResolutionExplanation`` dataclass (verified in
    ``oneiric/core/resolution.py:183-197`` and
    ``fastblocks/core/resolver.py:221-223``). It is NOT a string.

    This helper produces an operator-facing single-line string. The
    shape is:

        style=vanila: 3 candidates ranked, 2 shadowed, winner=<module>

    If ``explanation.ordered`` is empty:
        style=vanila: no candidates registered

    If ``explanation`` lacks ``as_dict()`` (different Oneiric version),
    fall back to ``repr(explanation)`` prefixed with ``explain:``.
    """
    if explanation is None:
        return "<unavailable>"
    # Try the common shape first
    ordered = getattr(explanation, "ordered", None)
    if ordered is None:
        # Fallback: repr the whole thing
        return f"explain: {explanation!r}"
    if not ordered:
        key = getattr(explanation, "key", "<unknown>")
        domain = getattr(explanation, "domain", "<unknown>")
        return f"{domain}={key}: no candidates registered"
    n_ranked = len(ordered)
    n_shadowed = sum(1 for r in ordered if not getattr(r, "selected", True))
    winner = next(
        (r for r in ordered if getattr(r, "selected", False)),
        ordered[0],
    )
    domain = getattr(explanation, "domain", "<unknown>")
    key = getattr(explanation, "key", "<unknown>")
    winner_label = getattr(winner, "module", "<unknown>")
    return (
        f"{domain}={key}: {n_ranked} candidates ranked, "
        f"{n_shadowed} shadowed, winner={winner_label}"
    )


# ---------------------------------------------------------------------------
# format_resolver_mismatch
# ---------------------------------------------------------------------------
def format_resolver_mismatch(
    depends: t.Any,
    domain: str,
    value: str,
) -> None:
    """Raise ``ResolverMismatchError`` if ``value`` is registered but
    not in StyleName (or vice versa).

    Returns None on success (the value IS in StyleName — caller should
    proceed). Raises ``ResolverMismatchError`` on mismatch.

    Never raises anything other than ``ResolverMismatchError``;
    ``explain()`` failures are caught and reported as
    ``resolver_explain="<unavailable>"``.
    """
    legal = t.get_args(StyleName)
    # Only check style domain for now; other domains pass through
    if domain != "style":
        # Future phases may add Literal types for other domains
        legal_tuple: tuple[str, ...] = ()
    else:
        legal_tuple = legal  # type: ignore[assignment]

    # Find nearest neighbor for typo hints
    nearest: str | None = None
    if legal_tuple:
        candidates = difflib.get_close_matches(
            value, legal_tuple, n=1, cutoff=0.6
        )
        nearest = candidates[0] if candidates else None

    # Run explain() and format the output
    resolver_explain = "<unavailable>"
    try:
        explanation = depends.explain(domain, value)
        resolver_explain = format_resolution_explanation_one_line(explanation)
    except (RuntimeError, AttributeError, TypeError, ValueError, KeyError):
        # explain() failed; carry on with "<unavailable>"
        pass

    # If the value isn't in StyleName, raise. The "did you mean" hint
    # only fires for typos with lexical similarity; unrelated strings
    # get no hint but still get the legal-set message.
    if value not in legal_tuple:
        raise ResolverMismatchError(
            value=value,
            legal=legal_tuple,
            nearest=nearest,
            resolver_explain=resolver_explain,
        )


# ---------------------------------------------------------------------------
# Protocol introspection helper (used by register_style_candidate)
# ---------------------------------------------------------------------------
def _protocol_missing_methods(
    module: t.Any,
    protocol: type,
) -> list[str]:
    """Return protocol methods absent from ``module``.

    Walks the Protocol's public method names (excludes underscore
    prefix and dunder methods) and returns the subset missing from
    ``module``. Used by ``register_style_candidate`` to build the
    missing-methods error message.

    Type checkers (``ty``, ``mypy``) cannot statically prove
    ``dir(protocol)`` returns the declared methods — runtime
    introspection is intentional. Returns a sorted list for
    deterministic error messages.
    """
    declared = sorted(
        name
        for name in dir(protocol)
        if not name.startswith("_") and callable(getattr(protocol, name, None))
    )
    module_attrs = set(dir(module))
    return [m for m in declared if m not in module_attrs]