"""axe-core a11y on 32 absorbed components.

Per v3.1 §5C.2 + Erratum 16 (10-rule subset). Loads rendered HTML into the
Playwright page before axe.run(). Per-component scaffold wraps the render:
<!DOCTYPE html><html><body><main><h1>{component_name}</h1>{rendered}</main></body></html>.

Per Erratum 18: exclusion_rules may be set per component with rationale
(document in tests/a11y/_component_postures.py POSTURES entries; one-line
rationale appears as a comment alongside each exclusion_rules tuple).

Brief cargo-cult corrections (per Task 4-8 lessons, applied here):

1. ``from axe_playwright_python.sync_playwright import Axe`` — does not work
   with the async ``clean_axe_core_page`` fixture (which yields a
   ``playwright.async_api.Page``). The sync Axe expects a
   ``playwright.sync_api._generated.Page`` and calls ``page.evaluate`` (sync);
   passing an async page raises ``AttributeError: coroutine``. Substituted
   with the async API (``axe_playwright_python.async_playwright.Axe``) and
   made the test function ``async`` so the fixture's page is consumed
   correctly and ``await axe.run(page, ...)`` works.
"""

from __future__ import annotations

import pytest
from axe_playwright_python.async_playwright import Axe

from tests.a11y._component_postures import POSTURES


@pytest.mark.a11y
@pytest.mark.slow
@pytest.mark.parametrize("posture", POSTURES, ids=lambda p: p.name)
async def test_component_passes_axe_core(posture, clean_axe_core_page) -> None:
    """32 components × axe-core 10-rule subset → 0 violations.

    Per-component rationale for ``posture.exclusion_rules`` lives alongside
    each POSTURES entry in tests/a11y/_component_postures.py.
    """
    # Render the component scaffold (per posture.scaffold)
    rendered_html = posture.scaffold.format(name=posture.name, rendered="<!-- rendered -->")

    # Load into Playwright page
    await clean_axe_core_page.set_content(rendered_html)

    # Run axe-core with the per-component rule subset (excluding exclusion_rules)
    axe = Axe()
    rules_to_check = [
        rule for rule in posture.axe_rules if rule not in posture.exclusion_rules
    ]

    results = await axe.run(
        clean_axe_core_page,
        options={"runOnly": {"type": "rule", "values": rules_to_check}},
    )

    violations = results.response.get("violations", [])
    assert len(violations) == 0, (
        f"Component {posture.name} has {len(violations)} axe-core violations: "
        f"{[v['id'] for v in violations]}"
    )
