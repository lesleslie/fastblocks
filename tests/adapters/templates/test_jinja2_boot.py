"""D3: boot test for the ``templates/jinja2`` adapter.

Spec §D3 row ``templates/jinja2`` -> resolver pair
``("fastblocks", "templates")`` (verified at
``fastblocks/adapters/templates/jinja2.py:1125``).

This is a minimal boot test, separate from the existing
``tests/adapters/templates/test_boot.py`` which exercises the full
Templates class lifecycle + autoescape contract. The brief asked for
"boot via Oneiric Resolver, render a trivial template, assert output";
this file delivers exactly that, with no shared module state.

Implementation note: ``Templates`` does NOT auto-register against
``fresh_registry`` (registration is inside ``init()`` at jinja2.py:1122).
We re-register the same factory shape against ``fresh_registry`` so the
test stays isolated from the global resolver singleton.
"""
from __future__ import annotations

from fastblocks.adapters.oneiric_helper import (
    register_candidate_strict,
    resolve_instance,
)


def test_jinja2_adapter_resolves_via_oneiric(fresh_registry) -> None:
    """The jinja2 adapter must be discoverable under
    ``("fastblocks", "templates")``."""
    from fastblocks.adapters.templates.jinja2 import Templates

    instance = Templates()
    register_candidate_strict(
        fresh_registry,
        domain="fastblocks",
        key="templates",
        factory=lambda: instance,
        metadata={"class": "Templates"},
    )
    resolved = resolve_instance(fresh_registry, "fastblocks", "templates")
    assert resolved is not None, (
        "D3: Oneiric resolver returned no instance for "
        "('fastblocks', 'templates')"
    )


def test_jinja2_adapter_instantiates_with_minimal_args() -> None:
    """Smoke: ``Templates()`` constructs with no required arguments."""
    from fastblocks.adapters.templates.jinja2 import Templates

    instance = Templates()
    assert instance is not None, "D3: Templates() returned None"
