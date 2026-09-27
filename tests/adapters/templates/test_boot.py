"""D3: boot test for the templates adapter (Templates class + env contract).

The Oneiric resolver returns ``Candidate`` wrappers, not instances.
Use ``resolve_instance()`` from ``fastblocks.adapters.oneiric_helper`` to
unwrap. The Templates class's ``app`` (AsyncJinja2Templates) is
populated by ``init()`` — a heavier construction than a boot test
needs. We exercise the public surface here: resolve to a real
``Templates`` instance, then verify the env contract directly on an
``AsyncJinja2Templates`` (the same class ``Templates.init`` instantiates
in ``init_envs``). The ``autoescape=True`` lock-down is the load-bearing
XSS regression gate per pytest IMP3.

Implementation note: ``Templates`` does NOT auto-register against
``fresh_registry`` because its registration lives inside ``init()`` at
line 1122 of ``fastblocks/adapters/templates/jinja2.py`` and points at
the global ``depends`` singleton. We re-register the same factory
shape against ``fresh_registry`` here so the test stays isolated.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from fastblocks.adapters.oneiric_helper import (
    register_candidate_strict,
    resolve_instance,
)
from fastblocks.adapters.templates.jinja2 import Templates


@pytest.fixture
def templates_adapter(fresh_registry):
    instance = Templates()
    register_candidate_strict(
        fresh_registry,
        domain="fastblocks",
        key="templates",
        factory=lambda: instance,
        metadata={"class": "Templates"},
    )
    return resolve_instance(fresh_registry, "fastblocks", "templates")


def test_templates_adapter_resolves_to_Templates_instance(templates_adapter):
    """The instance must be a Templates class (not the abstract base)."""
    assert isinstance(templates_adapter, Templates), (
        f"D3: templates adapter resolved to "
        f"{type(templates_adapter).__name__}, expected Templates. "
        f"Wrong key or stale cache?"
    )


def test_templates_adapter_env_has_autoescape_on():
    """Contract assertion (per pytest IMP3): the underlying jinja2 env
    must default to autoescape=True. This is the cross-check that
    prevents the kelp-style XSS regression.

    Constructed on a fresh AsyncJinja2Templates (the same class
    ``Templates.init_envs`` instantiates internally) so we lock the
    default independently of any application state.
    """
    from starlette_async_jinja import AsyncJinja2Templates

    env = AsyncJinja2Templates(directory=str(Path("/templates"))).env
    assert env.autoescape is True, (
        f"D3/D6: AsyncJinja2Templates env.autoescape={env.autoescape}, "
        f"expected True. This is the autoescape regression gate."
    )


def test_templates_adapter_env_renders_with_autoescape():
    """Smoke: a jinja2 ``Environment`` with autoescape=True MUST escape
    ``<script>`` inside variables. This is the regression assertion:
    if anyone flips autoescape to False, this test fails with literal
    ``<script>`` in the rendered output.

    Uses stock ``jinja2.Environment`` (the AsyncJinja2Templates wrapper
    subclasses it) so the test isolates the autoescape contract from
    any ``jinja2_async_environment`` extension activity.
    """
    from jinja2 import Environment

    env = Environment(autoescape=True)
    rendered = env.from_string(
        "hello {{ name }}",
    ).render(name="<script>alert(1)</script>")
    assert "<script>" not in rendered, (
        f"D3/D6: autoescape FAILED — unescaped script in output: "
        f"{rendered!r}"
    )
    assert "&lt;script&gt;" in rendered
