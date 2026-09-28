"""Adapter-matrix regression test.

Asserts that the rendered matrix matches every candidate currently
registered in the FastBlocks-owned Oneiric resolver (domain == "fastblocks").
A mismatch fails CI — preventing the matrix from drifting out of sync
with the resolver.

# req: REQ-P2-B2-003
"""
from __future__ import annotations

import re
from pathlib import Path

from fastblocks.core.resolver import get_resolver

_REPO_ROOT = Path(__file__).resolve().parents[3]


def test_adapter_matrix_lists_every_registered_candidate(client) -> None:
    """The /adapter-matrix page lists every registered fastblocks-domain candidate."""
    resolver = get_resolver()
    expected_keys = sorted(
        key for (domain, key) in resolver.registry._candidates.keys()
        if domain == "fastblocks"
    )
    assert expected_keys, "no fastblocks-domain candidates registered"

    response = client.get("/adapter-matrix")
    assert response.status_code == 200
    body = response.text

    for key in expected_keys:
        # Each row renders the key inside a <td>; assert it appears
        # at least once in the body.
        pattern = rf"<td[^>]*>\s*{re.escape(key)}\s*</td>"
        assert re.search(pattern, body), (
            f"/adapter-matrix missing row for candidate key={key!r}"
        )


def test_adapter_matrix_boot_tested_marker_is_honest(client) -> None:
    """The boot-tested marker is only "yes" when the file exists on disk.

    Walks the rendered matrix body, extracts the per-row "boot-tested"
    cell, and asserts it shows "yes" iff
    ``tests/adapters/<domain>/<key>/test_boot.py`` exists on disk. Any
    drift between the rendered cell and the on-disk state fails.
    """
    response = client.get("/adapter-matrix")
    assert response.status_code == 200
    body = response.text

    resolver = get_resolver()
    for (domain, key) in sorted(resolver.registry._candidates.keys()):
        if domain != "fastblocks":
            continue
        boot_path = _REPO_ROOT / "tests" / "adapters" / domain / key / "test_boot.py"
        expected_success = boot_path.exists()

        # The template renders the boot-tested cell as either
        # ``<span class="ui-tag is-success">✓</span>`` (test exists) or
        # ``<span class="ui-tag is-warning">?</span>`` (no test). Anchor
        # on the key's row, then look at the *last* <td> in that <tr>
        # for the is-success / is-warning marker.
        row_pattern = rf"<tr>\s*<td[^>]*>\s*{re.escape(domain)}\s*</td>\s*<td[^>]*>\s*{re.escape(key)}\s*</td>.*?</tr>"
        match = re.search(row_pattern, body, re.DOTALL)
        assert match, f"/adapter-matrix missing row for candidate key={key!r}"
        row = match.group(0)
        if expected_success:
            assert "is-success" in row, (
                f"boot-tested marker drift for key={key!r}: "
                f"expected is-success (test exists at {boot_path}) but did not find it"
            )
            assert "is-warning" not in row, (
                f"boot-tested marker drift for key={key!r}: "
                f"row contains is-warning even though {boot_path} is present"
            )
        else:
            assert "is-warning" in row, (
                f"boot-tested marker drift for key={key!r}: "
                f"expected is-warning (no test at {boot_path}) but did not find it"
            )
            assert "is-success" not in row, (
                f"boot-tested marker drift for key={key!r}: "
                f"row claims is-success even though {boot_path} is missing"
            )
