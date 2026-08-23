"""Per-component axe-core test posture (Erratum 3 + Erratum 18 schema).

Each component gets one entry mapping it to:
- The HTML scaffold wrapping its render (per v3.1 §5C.2 step 3a)
- The axe-core rule subset to evaluate (10 rules per Erratum 16)
- The expected landmark role and accessible-name source
- Per-component rule exclusions with rationale (Erratum 18)

Loaded by tests/a11y/test_components_a11y.py parameterized loop.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ComponentPosture:
    """One component's axe-core test posture."""

    name: str
    scaffold: str  # HTML wrapping the component (with <main><h1>...</h1>...</main>)
    axe_rules: tuple[str, ...]  # subset of master plan §5C.2 10-rule set (Erratum 16)
    expected_landmark: str  # "navigation", "main", "complementary", etc.
    accessible_name_source: str  # attribute or text-derived
    exclusion_rules: tuple[str, ...] = ()
    # exclusion_rules: axe-core rule IDs to exclude for THIS component only.
    # Each entry must be a single rule ID (e.g., "landmark-one-main") with a
    # one-line rationale in the implementing test (e.g., "Dialog: exclude
    # landmark-one-main because a Dialog does not contain the page main").
    # One-line rationale should be in the implementing test, not in this schema.


# 10-rule axe-core subset (Erratum 16):
# Master-plan baseline (6):
#   - color-contrast: WCAG 1.4.3 contrast ratio
#   - label: form labels associate with controls
#   - button-name: buttons have discernible text
#   - link-name: links have discernible text
#   - image-alt: images have alt text
#   - aria-roles: ARIA roles are valid
# v3.1 extensions (4):
#   - region: all content is inside a landmark region
#   - landmark-one-main: document has exactly one main landmark
#   - page-has-heading-one: document has exactly one h1
#   - duplicate-id: no two elements share the same id
_AXE_BASE: tuple[str, ...] = (
    "color-contrast", "label", "button-name", "link-name", "image-alt",
    "aria-roles", "region", "landmark-one-main", "page-has-heading-one",
    "duplicate-id",
)

# Per Erratum 15: Modal → Dialog (the modal role is performed by Dialog
# in the absorbed components; there is no separate Modal class).
# Realistic-defaults policy (v3.1 §5C.2 + v4 Erratum 25):
#   - Button: standalone with realistic default
#   - Dialog: open (rendered as <dialog open aria-modal="true">)
#   - Dropdown: closed (panel-only — no trigger button)
#   - Tabs: rendered with proper ARIA plumbing (active_id, role="tablist")
#   - Drawer: off-canvas (closed state)
POSTURES: tuple[ComponentPosture, ...] = (
    ComponentPosture(
        name="Button",
        scaffold='<!DOCTYPE html><html><body><main><h1>Button</h1><button>Submit</button></main></body></html>',
        axe_rules=_AXE_BASE,
        expected_landmark="main",
        accessible_name_source="text",
    ),
    # ... 31 more entries — implementer enumerates from htmy_components.__all__ ...
    # For each component, set:
    #   scaffold: <!DOCTYPE html><html><body><main><h1>{name}</h1>{realistic_render}</main></body></html>
    #   axe_rules: _AXE_BASE (or subset if components are restrictive)
    #   expected_landmark: "navigation" / "main" / "complementary" / "region" as appropriate
    #   accessible_name_source: "aria-label" / "text" / etc.
    #   exclusion_rules: tuple of rule IDs to exclude for this component
)
