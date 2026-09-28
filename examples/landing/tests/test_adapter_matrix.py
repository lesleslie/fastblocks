"""Adapter-matrix regression test.

Asserts that the rendered matrix matches every adapter the spec §D3
marks as in-scope for the dogfood-readiness D3 dimension. The
in-scope set is the single source of truth exported by the route
module (``examples/landing/routes/adapter_matrix.py``'s
``_IN_SCOPE_ADAPTERS``) — re-imported here so the test cannot drift
out of sync with the spec silently.

Adapter rows are uniquely identified by their (domain, resolver_key)
pair. Middleware rows all share ``domain="—"``, ``key="—"``,
``provider="module-resident"`` — those are verified in aggregate by
total marker count, not per-row.

# req: REQ-P2-B2-003
"""
from __future__ import annotations

import re
from pathlib import Path

from routes import adapter_matrix as _adapter_matrix_route

_REPO_ROOT = Path(__file__).resolve().parents[3]
_IN_SCOPE_ADAPTERS = _adapter_matrix_route._IN_SCOPE_ADAPTERS
_DOMAIN = "fastblocks"

_ADAPTER_ROW = (
    rf"<tr>\s*<td[^>]*>\s*{_DOMAIN}\s*</td>\s*"
    rf"<td[^>]*>\s*{{key}}\s*</td>.*?</tr>"
)
_MIDDLEWARE_ROW = (
    r"<tr>\s*<td[^>]*>\s*—\s*</td>\s*<td[^>]*>\s*—\s*</td>\s*"
    r"<td[^>]*>\s*module-resident\s*</td>.*?</tr>"
)


def _adapter_rows() -> list[tuple[str, str, str]]:
    """Return the resolver-backed (spec_label, resolver_key, boot_relpath) entries."""
    return [
        (spec_label, resolver_key, boot_relpath)
        for (spec_label, resolver_key, boot_relpath) in _IN_SCOPE_ADAPTERS
        if resolver_key is not None
    ]


def _middleware_rows() -> list[tuple[str, str]]:
    """Return the middleware (spec_label, boot_relpath) entries."""
    return [
        (spec_label, boot_relpath)
        for (spec_label, resolver_key, boot_relpath) in _IN_SCOPE_ADAPTERS
        if resolver_key is None
    ]


def test_adapter_matrix_lists_every_registered_candidate(client) -> None:
    """Spec §D3 coverage: every in-scope adapter has a row in /adapter-matrix.

    Walks the route module's ``_IN_SCOPE_ADAPTERS`` constant and asserts
    the rendered HTML contains a row for each entry. Adapter rows are
    matched by ``(domain, resolver_key)``; middleware rows are counted
    in aggregate because their ``(domain, key, provider)`` cells are
    identical.
    """
    response = client.get("/adapter-matrix")
    assert response.status_code == 200
    body = response.text

    for spec_label, resolver_key, _boot_relpath in _adapter_rows():
        pattern = _ADAPTER_ROW.format(key=re.escape(resolver_key))
        assert re.search(pattern, body, re.DOTALL), (
            f"/adapter-matrix missing row for spec §D3 entry {spec_label!r} "
            f"(resolver pair ({_DOMAIN!r}, {resolver_key!r}))"
        )

    middleware = _middleware_rows()
    actual_middleware = len(re.findall(_MIDDLEWARE_ROW, body, re.DOTALL))
    assert actual_middleware == len(middleware), (
        f"/adapter-matrix expected {len(middleware)} middleware rows "
        f"({[label for label, _ in middleware]!r}), "
        f"found {actual_middleware}"
    )


def test_adapter_matrix_boot_tested_marker_is_honest(client) -> None:
    """Spec §D3 honesty: the ``is-success`` / ``is-warning`` marker matches on-disk state.

    For each spec §D3 entry, asserts the rendered row's boot-tested
    marker reflects whether the documented ``tests/.../test_<name>_boot.py``
    path exists on disk. Adapter rows are checked individually by
    ``(domain, resolver_key)``; middleware rows are checked by aggregate
    marker count because their rendered cells are identical.
    """
    response = client.get("/adapter-matrix")
    assert response.status_code == 200
    body = response.text

    for spec_label, resolver_key, boot_relpath in _adapter_rows():
        expected_success = (_REPO_ROOT / boot_relpath).exists()
        pattern = _ADAPTER_ROW.format(key=re.escape(resolver_key))
        match = re.search(pattern, body, re.DOTALL)
        assert match, f"/adapter-matrix missing row for spec §D3 entry {spec_label!r}"
        row = match.group(0)
        if expected_success:
            assert "is-success" in row, (
                f"boot_tested drift for spec §D3 entry {spec_label!r}: "
                f"expected is-success (test exists at {boot_relpath}) "
                f"but did not find it"
            )
            assert "is-warning" not in row, (
                f"boot_tested drift for spec §D3 entry {spec_label!r}: "
                f"row contains is-warning even though {boot_relpath} is present"
            )
        else:
            assert "is-warning" in row, (
                f"boot_tested drift for spec §D3 entry {spec_label!r}: "
                f"expected is-warning (no test at {boot_relpath}) "
                f"but did not find it"
            )
            assert "is-success" not in row, (
                f"boot_tested drift for spec §D3 entry {spec_label!r}: "
                f"row claims is-success even though {boot_relpath} is missing"
            )

    middleware = _middleware_rows()
    middleware_section = re.findall(_MIDDLEWARE_ROW, body, re.DOTALL)
    expected_success = sum(
        1 for _, boot_relpath in middleware
        if (_REPO_ROOT / boot_relpath).exists()
    )
    expected_warning = len(middleware) - expected_success
    actual_success = sum(1 for row in middleware_section if "is-success" in row)
    actual_warning = sum(1 for row in middleware_section if "is-warning" in row)
    assert actual_success == expected_success, (
        f"middleware boot_tested drift: expected {expected_success} "
        f"is-success rows, found {actual_success} "
        f"(middleware entries: {[label for label, _ in middleware]!r})"
    )
    assert actual_warning == expected_warning, (
        f"middleware boot_tested drift: expected {expected_warning} "
        f"is-warning rows, found {actual_warning} "
        f"(middleware entries: {[label for label, _ in middleware]!r})"
    )
