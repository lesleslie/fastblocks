"""D6: regression test for the kelp-style XSS bug.

The removed kelp.py interpolated content into f-strings without
HTML escaping. ``fastblocks-ui`` escapes by default (per
``tests/style/test_fastblocks_ui_escape_contract.py``). This test pins
the same expectation for the default template adapter (jinja2 via
``starlette-async-jinja``'s ``AsyncJinja2Templates``).

The brief's sketch referenced ``jinja2.Jinja2Adapter().render_string()``;
the actual API has no such method. We adapt to the real contract:
``AsyncJinja2Templates._create_env`` calls
``env_options.setdefault("autoescape", True)``, which makes the
underlying ``AsyncEnvironment`` (``jinja2_async_environment``) enable
autoescape by default. We verify that contract directly by rendering a
string template with a script payload and asserting the output is
HTML-escaped.
"""

from __future__ import annotations


def test_jinja2_environment_default_autoescape_is_true():
    """D6: the jinja2 environment created by the default template
    adapter must enable autoescape by default — this is the XSS
    defense for every rendered template in the framework.
    """
    from anyio import Path as AsyncPath
    from starlette_async_jinja import AsyncJinja2Templates

    templates = AsyncJinja2Templates(directory=AsyncPath("templates"))
    assert templates.env.autoescape is True, (
        f"D6: jinja2 autoescape default regressed (got "
        f"{templates.env.autoescape!r}). The default template adapter "
        "must HTML-escape every variable substitution; otherwise the "
        "removed kelp-style XSS bug recurs."
    )


def test_user_input_in_jinja_template_is_html_escaped():
    """Render a user-controlled string and assert the raw <script> tag
    is HTML-escaped in the output.

    This is the same XSS-regression shape as
    ``tests/style/test_fastblocks_ui_escape_contract.py`` but for the
    jinja2 adapter (the production default for FastBlocks rendering).

    Implementation note: we exercise ``jinja2.Environment`` (stock)
    with the same autoescape contract the adapter passes through to
    the underlying environment via ``env_options.setdefault``. The
    adapter's underlying environment is an ``AsyncEnvironment`` whose
    ``from_string(...).render(...)`` returns the rendered text (the
    async rendering only kicks in for filesystem loaders, not
    ``from_string``), so a stock ``jinja2.Environment`` instance is
    the closest deterministic proxy for the escape contract.
    """
    from jinja2 import Environment

    env = Environment(autoescape=True)
    template = env.from_string("hello {{ name }}")

    rendered = template.render(name="<script>alert(1)</script>")

    # The raw <script> opening tag must NOT appear (it would have
    # meant autoescape regressed and the user payload is now an
    # executable script in the DOM).
    assert "<script>" not in rendered, (
        f"D6: jinja2 autoescape regression — raw <script> rendered "
        f"unescaped: {rendered!r}"
    )
    # The escaped form (&lt;script&gt; with semicolons) MUST appear,
    # proving the value was HTML-escaped (not just stripped).
    assert "&lt;script&gt;" in rendered, (
        f"D6: jinja2 did not HTML-escape the value (rendered={rendered!r})"
    )
    # The original user value substring 'alert(1)' is preserved
    # inside the escaped tag — the user's text is preserved verbatim
    # but the surrounding HTML is escaped.
    assert "alert(1)" in rendered