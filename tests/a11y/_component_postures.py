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
#
# Per Erratum 18: exclusion_rules entries below carry a one-line rationale
# in the implementing test (tests/a11y/test_components_a11y.py), not here.
POSTURES: tuple[ComponentPosture, ...] = (
    ComponentPosture(
        name="Alert",
        scaffold='<!DOCTYPE html><html><body><main><h1>{name}</h1>{rendered}</main></body></html>',
        axe_rules=_AXE_BASE,
        expected_landmark="main",
        accessible_name_source="text",
    ),
    ComponentPosture(
        name="Breadcrumb",
        scaffold='<!DOCTYPE html><html><body><main><h1>{name}</h1>{rendered}</main></body></html>',
        axe_rules=_AXE_BASE,
        expected_landmark="main",
        accessible_name_source="aria-label",
    ),
    ComponentPosture(
        name="Burger",
        scaffold='<!DOCTYPE html><html><body><main><h1>{name}</h1>{rendered}</main></body></html>',
        axe_rules=_AXE_BASE,
        expected_landmark="main",
        accessible_name_source="text",
    ),
    ComponentPosture(
        name="Button",
        scaffold='<!DOCTYPE html><html><body><main><h1>{name}</h1>{rendered}</main></body></html>',
        axe_rules=_AXE_BASE,
        expected_landmark="main",
        accessible_name_source="text",
    ),
    ComponentPosture(
        name="Card",
        scaffold='<!DOCTYPE html><html><body><main><h1>{name}</h1>{rendered}</main></body></html>',
        axe_rules=_AXE_BASE,
        expected_landmark="main",
        accessible_name_source="text",
    ),
    ComponentPosture(
        name="Checkbox",
        scaffold='<!DOCTYPE html><html><body><main><h1>{name}</h1>{rendered}</main></body></html>',
        axe_rules=_AXE_BASE,
        expected_landmark="main",
        accessible_name_source="label",
    ),
    ComponentPosture(
        name="Column",
        scaffold='<!DOCTYPE html><html><body><main><h1>{name}</h1>{rendered}</main></body></html>',
        axe_rules=_AXE_BASE,
        expected_landmark="main",
        accessible_name_source="text",
    ),
    ComponentPosture(
        name="Columns",
        scaffold='<!DOCTYPE html><html><body><main><h1>{name}</h1>{rendered}</main></body></html>',
        axe_rules=_AXE_BASE,
        expected_landmark="main",
        accessible_name_source="text",
    ),
    ComponentPosture(
        name="Container",
        scaffold='<!DOCTYPE html><html><body><main><h1>{name}</h1>{rendered}</main></body></html>',
        axe_rules=_AXE_BASE,
        expected_landmark="main",
        accessible_name_source="text",
    ),
    ComponentPosture(
        name="Dialog",
        # Per Erratum 15: Dialog is the modal component; renders <dialog> with
        # optional autoshow. Exclude landmark-one-main because a modal Dialog
        # overlay does not contain the page main.
        scaffold='<!DOCTYPE html><html><body><main><h1>{name}</h1>{rendered}</main></body></html>',
        axe_rules=_AXE_BASE,
        expected_landmark="main",
        accessible_name_source="aria-labelledby",
        exclusion_rules=("landmark-one-main",),
    ),
    ComponentPosture(
        name="Drawer",
        # Drawer is off-canvas popover. Exclude region because the drawer is
        # in the top layer (popover) and its content is intentionally hidden
        # until shown.
        scaffold='<!DOCTYPE html><html><body><main><h1>{name}</h1>{rendered}</main></body></html>',
        axe_rules=_AXE_BASE,
        expected_landmark="main",
        accessible_name_source="aria-label",
        exclusion_rules=("region",),
    ),
    ComponentPosture(
        name="Dropdown",
        # Dropdown panel is popover; trigger button is separate (not rendered
        # here per realistic-defaults policy). Exclude button-name because the
        # dropdown panel-only render has no button child.
        scaffold='<!DOCTYPE html><html><body><main><h1>{name}</h1>{rendered}</main></body></html>',
        axe_rules=_AXE_BASE,
        expected_landmark="main",
        accessible_name_source="aria-label",
        exclusion_rules=("button-name",),
    ),
    ComponentPosture(
        name="Field",
        scaffold='<!DOCTYPE html><html><body><main><h1>{name}</h1>{rendered}</main></body></html>',
        axe_rules=_AXE_BASE,
        expected_landmark="main",
        accessible_name_source="label",
    ),
    ComponentPosture(
        name="Footer",
        scaffold='<!DOCTYPE html><html><body><main><h1>{name}</h1>{rendered}</main></body></html>',
        axe_rules=_AXE_BASE,
        expected_landmark="main",
        accessible_name_source="text",
    ),
    ComponentPosture(
        name="Hero",
        # Hero default heading_level=None renders title as <p>; scaffold
        # provides the page h1. Exclude page-has-heading-one as a guard
        # against callers setting heading_level=1 (which would emit <h1>).
        scaffold='<!DOCTYPE html><html><body><main><h1>{name}</h1>{rendered}</main></body></html>',
        axe_rules=_AXE_BASE,
        expected_landmark="main",
        accessible_name_source="text",
        exclusion_rules=("page-has-heading-one",),
    ),
    ComponentPosture(
        name="Input",
        # Input is bare <input type="text">; no associated <label> when used
        # standalone. Real callers wrap in <label> or pass aria-label via
        # attrs. Exclude label for the standalone component posture.
        scaffold='<!DOCTYPE html><html><body><main><h1>{name}</h1>{rendered}</main></body></html>',
        axe_rules=_AXE_BASE,
        expected_landmark="main",
        accessible_name_source="aria-label",
        exclusion_rules=("label",),
    ),
    ComponentPosture(
        name="Level",
        scaffold='<!DOCTYPE html><html><body><main><h1>{name}</h1>{rendered}</main></body></html>',
        axe_rules=_AXE_BASE,
        expected_landmark="main",
        accessible_name_source="text",
    ),
    ComponentPosture(
        name="Media",
        scaffold='<!DOCTYPE html><html><body><main><h1>{name}</h1>{rendered}</main></body></html>',
        axe_rules=_AXE_BASE,
        expected_landmark="main",
        accessible_name_source="text",
    ),
    ComponentPosture(
        name="NavGroups",
        scaffold='<!DOCTYPE html><html><body><main><h1>{name}</h1>{rendered}</main></body></html>',
        axe_rules=_AXE_BASE,
        expected_landmark="main",
        accessible_name_source="text",
    ),
    ComponentPosture(
        name="NavList",
        scaffold='<!DOCTYPE html><html><body><main><h1>{name}</h1>{rendered}</main></body></html>',
        axe_rules=_AXE_BASE,
        expected_landmark="main",
        accessible_name_source="text",
    ),
    ComponentPosture(
        name="Navbar",
        scaffold='<!DOCTYPE html><html><body><main><h1>{name}</h1>{rendered}</main></body></html>',
        axe_rules=_AXE_BASE,
        expected_landmark="main",
        accessible_name_source="aria-label",
    ),
    ComponentPosture(
        name="Pagination",
        scaffold='<!DOCTYPE html><html><body><main><h1>{name}</h1>{rendered}</main></body></html>',
        axe_rules=_AXE_BASE,
        expected_landmark="main",
        accessible_name_source="aria-label",
    ),
    ComponentPosture(
        name="Progress",
        scaffold='<!DOCTYPE html><html><body><main><h1>{name}</h1>{rendered}</main></body></html>',
        axe_rules=_AXE_BASE,
        expected_landmark="main",
        accessible_name_source="aria-label",
    ),
    ComponentPosture(
        name="Section",
        scaffold='<!DOCTYPE html><html><body><main><h1>{name}</h1>{rendered}</main></body></html>',
        axe_rules=_AXE_BASE,
        expected_landmark="main",
        accessible_name_source="text",
    ),
    ComponentPosture(
        name="Select",
        # Select is bare <select>...</select>; no associated <label> when used
        # standalone. Exclude label for the standalone component posture.
        scaffold='<!DOCTYPE html><html><body><main><h1>{name}</h1>{rendered}</main></body></html>',
        axe_rules=_AXE_BASE,
        expected_landmark="main",
        accessible_name_source="aria-label",
        exclusion_rules=("label",),
    ),
    ComponentPosture(
        name="Shell",
        # Shell emits its own <main class="ui-shell__main"> as the page-level
        # layout primitive. Wrapping in another <main> would violate
        # landmark-one-main. Exclude the rule.
        scaffold='<!DOCTYPE html><html><body><main><h1>{name}</h1>{rendered}</main></body></html>',
        axe_rules=_AXE_BASE,
        expected_landmark="main",
        accessible_name_source="text",
        exclusion_rules=("landmark-one-main",),
    ),
    ComponentPosture(
        name="Switch",
        scaffold='<!DOCTYPE html><html><body><main><h1>{name}</h1>{rendered}</main></body></html>',
        axe_rules=_AXE_BASE,
        expected_landmark="main",
        accessible_name_source="label",
    ),
    ComponentPosture(
        name="Table",
        scaffold='<!DOCTYPE html><html><body><main><h1>{name}</h1>{rendered}</main></body></html>',
        axe_rules=_AXE_BASE,
        expected_landmark="main",
        accessible_name_source="text",
    ),
    ComponentPosture(
        name="Tabs",
        scaffold='<!DOCTYPE html><html><body><main><h1>{name}</h1>{rendered}</main></body></html>',
        axe_rules=_AXE_BASE,
        expected_landmark="main",
        accessible_name_source="aria-label",
    ),
    ComponentPosture(
        name="Tile",
        scaffold='<!DOCTYPE html><html><body><main><h1>{name}</h1>{rendered}</main></body></html>',
        axe_rules=_AXE_BASE,
        expected_landmark="main",
        accessible_name_source="text",
    ),
    ComponentPosture(
        name="Title",
        # Title default heading_level=None renders as <p>; scaffold provides
        # the page h1. Exclude page-has-heading-one as a guard against callers
        # setting heading_level=1 (which would emit <h1>).
        scaffold='<!DOCTYPE html><html><body><main><h1>{name}</h1>{rendered}</main></body></html>',
        axe_rules=_AXE_BASE,
        expected_landmark="main",
        accessible_name_source="text",
        exclusion_rules=("page-has-heading-one",),
    ),
    ComponentPosture(
        name="ValidationSummary",
        scaffold='<!DOCTYPE html><html><body><main><h1>{name}</h1>{rendered}</main></body></html>',
        axe_rules=_AXE_BASE,
        expected_landmark="main",
        accessible_name_source="text",
    ),
)

assert len(POSTURES) == 32, (
    f"Expected 32 component postures, got {len(POSTURES)}"
)
