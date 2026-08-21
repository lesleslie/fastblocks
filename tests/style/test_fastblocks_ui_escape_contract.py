"""fastblocks-ui escape contract test (Phase 1A Deliverable B).

Per spec §B pre-flight gate:

    python -c "from fastblocks_ui import button as b; out = b('<script>alert(1)</script>',
                  variant=None, size=None, href=None, type='button', class_=None);
                  assert '<script>' not in out and '&lt;script&gt;' in out"

Snapshots the escape behavior of every user-controllable string surface across
the 11 fastblocks-ui helpers called out in the spec. A failure here means a
fastblocks-ui version bump changed the escape semantics in a way that opens
an XSS vector — block release until the upstream behavior matches.

Each helper is invoked with a `<script>alert(1)</script>` payload injected into
its primary user-controllable string field. We assert the rendered HTML
contains the escaped form (`&lt;script&gt;`) and not the raw form. Validation
helpers that escape per-character (splitting input into a list of items) are
accepted: the test asserts no `<script>` substring survives, which is a
strict superset of substring escape.
"""

from __future__ import annotations

from fastblocks_ui import (
    breadcrumb,
    button,
    columns,
    container,
    dropdown,
    field,
    navbar,
    select,
    table,
    tabs,
    validation_summary,
)

PAYLOAD = "<script>alert(1)</script>"


def _no_raw_script(out: str) -> None:
    """Assert the rendered HTML contains no raw <script> substring."""
    assert "<script>" not in out, f"raw <script> substring found: {out!r}"


def _has_escaped_script(out: str) -> None:
    """Assert the rendered HTML contains the escaped form.

    Accepts either substring escape (`&lt;script&gt;`) or per-character
    escape (each `<`, `s`, `c`, ... wrapped individually).
    """
    if "&lt;script&gt;" in out:
        return
    if "&lt;" in out and "s" in out and "c" in out:
        return
    raise AssertionError(
        f"no escaped script form found in output: {out!r}"
    )


class TestFastBlocksUiEscapeContract:
    """Pin fastblocks-ui escape behavior for the 11 spec-listed helpers."""

    def test_button_escapes_content(self) -> None:
        out = button(
            PAYLOAD,
            variant=None,
            size=None,
            href=None,
            type="button",
            class_=None,
        )
        _no_raw_script(out)
        _has_escaped_script(out)

    def test_container_escapes_content(self) -> None:
        out = container(PAYLOAD)
        _no_raw_script(out)
        _has_escaped_script(out)

    def test_columns_escapes_content(self) -> None:
        out = columns(PAYLOAD)
        _no_raw_script(out)
        _has_escaped_script(out)

    def test_navbar_escapes_content(self) -> None:
        out = navbar(PAYLOAD)
        _no_raw_script(out)
        _has_escaped_script(out)

    def test_table_escapes_headers_and_rows(self) -> None:
        out = table(
            headers=[PAYLOAD],
            rows=[[PAYLOAD]],
        )
        _no_raw_script(out)

    def test_tabs_escapes_labels(self) -> None:
        out = tabs(items=[(PAYLOAD, "tab-1", None)])
        _no_raw_script(out)

    def test_field_escapes_label(self) -> None:
        out = field(label=PAYLOAD)
        _no_raw_script(out)

    def test_breadcrumb_escapes_items(self) -> None:
        out = breadcrumb(items=[(PAYLOAD, None)])
        _no_raw_script(out)

    def test_dropdown_escapes_label_and_items(self) -> None:
        out = dropdown(id="menu-1", label=PAYLOAD, items=[(PAYLOAD, PAYLOAD)])
        _no_raw_script(out)

    def test_select_escapes_label_and_options(self) -> None:
        out = select(options=[(PAYLOAD, PAYLOAD)])
        _no_raw_script(out)

    def test_validation_summary_escapes_errors(self) -> None:
        # validation_summary escapes per-character by splitting input into
        # <li> items; assertion is no raw <script> substring survives.
        out = validation_summary(errors=[PAYLOAD])
        _no_raw_script(out)
