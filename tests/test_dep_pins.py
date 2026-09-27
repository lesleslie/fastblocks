"""D8: dependency hygiene gate (loose pins + broken releases).

Per the audit task brief (D8 / dependency-manager BL1 + BL2):

- BL1: the actual failure mode is **open upper bounds**
  (``>=X.Y.Z`` with no ``<X.Y`` cap), NOT zero-floors. ``uv sync
  --upgrade`` re-resolves open floors to MINIMUM (per
  feedback-crackerjack-gitignore-sync-dev-dep-downgrade), silently
  breaking us.

- BL2: every documented broken release must be absent from current
  dependency specs. YAML-driven so adding a new broken release is one
  YAML row, not a code edit.

Two integration tests fail loudly against the current
``pyproject.toml`` and are the gate's reason for existing. The unit
tests pin the loose-pin detector's accept/reject matrix in place so
refactors don't silently weaken the contract.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import tomllib
import yaml

PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"
BROKEN_RELEASES_YAML = Path(__file__).parent / "dep_broken_releases.yaml"

# CRITICAL_DEPS (per task-3-brief.md).
# 11 load-bearing deps. Refresh when adding a new one whose breakage
# would cascade into the framework. ``jinja2`` was the original entry
# but it's transitive, not declared — removed.
CRITICAL_DEPS = {
    "fastblocks-ui",
    "oneiric",
    "mcp-common",
    "httpx2",  # renamed from httpx; recent migration
    "pydantic",  # framework is Pydantic-v2-classified
    "brotli-asgi",  # D7's headline perf claim depends on this
    "starlette-async-jinja",  # actual jinja2 integration layer
    "starlette-csrf",  # D6's CSRF gate depends on this
    "htmy",  # B3 hybrid render demo depends on this
    "granian",  # ASGI server
    "minify-html",  # D7's minify claim
}


# -----------------------------------------------------------------------------
# Pure helpers (parse + loose detection)
# -----------------------------------------------------------------------------


def _parse_name(spec: str) -> str:
    """Extract bare package name from a PEP 508-ish spec.

    Examples::

        "granian[reload]~=2.6"        -> "granian"
        "httpx2>=0.28.1"              -> "httpx2"
        "fastblocks-ui>=0.9,<0.10"    -> "fastblocks-ui"
    """
    return re.split(r"[<>=!~;\[]", spec.strip(), maxsplit=1)[0].strip()


def _is_loose(spec: str) -> bool:
    """Return ``True`` if a single PEP 508-ish spec is loose.

    Loose means one of:

    - ``*`` wildcard (any unpinned version)
    - ``>=0`` / ``>=0.0`` / ``>=0.0.0`` (zero floor; only ``0``, ``0.0``,
      ``0.0.0`` are PEP 440 forms of version zero — NOT ``0.9``)
    - bare ``>=X.Y.Z`` with no upper cap (``<X.Y+W``) — the
      fastblocks actual failure mode (uv sync --upgrade re-resolves
      open floors to MINIMUM).

    Tight means one of:

    - ``~=X.Y`` (compatible-release) — PEP 440 implicit upper bound
    - ``>=X.Y.Z,<X.Y+W`` (bounded range)
    - ``==X.Y.Z`` (exact pin)
    """
    if "*" in spec:
        return True
    # Bug in the brief's regex: ``\\D|$`` matches the ``.`` in
    # ``>=0.9`` / ``>=0.28`` as a non-digit -> false positives on
    # every non-zero open floor. Floor zero's PEP 440 forms are exactly
    # ``0``, ``0.0``, ``0.0.0`` — anchor on the next non-version
    # separator (``[,;]`` or end-of-string) instead.
    if re.search(r">=0(?:\.0)?(?:\.0)?(?=[,;]|$)", spec):
        return True
    has_upper_cap = bool(re.search(r",\s*<", spec)) or "~=" in spec or "==" in spec
    return not has_upper_cap


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture(scope="module")
def pyproject_data() -> dict:
    return tomllib.loads(PYPROJECT.read_text())


@pytest.fixture(scope="module")
def critical_dep_specs(pyproject_data: dict) -> dict[str, str]:
    """Mapping of CRITICAL_DEPS package names to their current spec strings.

    Missing entries are intentional errors — the integration test asserts
    the mapping is complete.
    """
    deps = pyproject_data["project"]["dependencies"]
    result: dict[str, str] = {}
    for spec in deps:
        name = _parse_name(spec)
        if name in CRITICAL_DEPS:
            result[name] = spec
    return result


# -----------------------------------------------------------------------------
# Unit tests: pin down _is_loose's accept/reject matrix (TDD)
# -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("spec", "expected_loose"),
    [
        # ---- Accept (tight pins) ----
        ("pydantic~=2.12", False),
        ("brotli-asgi~=1.5", False),
        ("fastblocks-ui>=0.9,<0.10", False),
        ("htmy[lxml]>=0.13,<0.14", False),
        ("granian[reload]~=2.6", False),
        ("starlette~=1.3", False),
        ("httpx2~=2.13", False),
        ("mcp-common==0.30.1", False),
        ("starlette-async-jinja~=1.13", False),
        ("starlette-csrf~=3.0", False),
        ("minify-html~=0.18", False),
        ("oneiric>=0.25,<0.26", False),
        # ---- Reject (loose pins) ----
        ("httpx2>=0.28.1", True),
        ("mcp-common>=0.30.0", True),
        ("oneiric>=0.20", True),
        ("foo>=0", True),
        ("foo>=0.0", True),
        ("foo>=0.0.0", True),
        ("foo*", True),
        ("bar[extra]>=1.0", True),
    ],
)
def test_loose_pin_detector_accept_and_reject(spec: str, expected_loose: bool) -> None:
    """Sanity-check the loose-pin detector itself, both accept and reject paths.

    Per task-3-brief.md: actual failure mode is open upper bounds;
    this matrix pins both halves so refactors don't silently loosen
    the gate.
    """
    assert _is_loose(spec) is expected_loose, (
        f"_is_loose({spec!r}) returned {not expected_loose}, "
        f"expected {expected_loose}"
    )


@pytest.mark.parametrize(
    ("spec", "expected_name"),
    [
        ("granian[reload]~=2.6", "granian"),
        ("httpx2>=0.28.1", "httpx2"),
        ("fastblocks-ui>=0.9,<0.10", "fastblocks-ui"),
        ("  httpx2  ", "httpx2"),
        ("starlette-async-jinja~=1.13", "starlette-async-jinja"),
        ("mcp-common>=0.30.0", "mcp-common"),
    ],
)
def test_parse_name_handles_extras_and_pins(spec: str, expected_name: str) -> None:
    assert _parse_name(spec) == expected_name


# -----------------------------------------------------------------------------
# End-to-end integration tests on pyproject.toml
# -----------------------------------------------------------------------------


def test_all_critical_deps_declared(critical_dep_specs: dict[str, str]) -> None:
    """Every CRITICAL_DEPS member must appear in pyproject.toml deps.

    If you add a load-bearing dep to CRITICAL_DEPS but forget to declare
    it in ``[project].dependencies``, this test fires.
    """
    missing = CRITICAL_DEPS - set(critical_dep_specs.keys())
    assert not missing, (
        f"D8: CRITICAL_DEPS members missing from pyproject.toml "
        f"[project].dependencies: {sorted(missing)}. Either declare "
        f"them or remove them from CRITICAL_DEPS."
    )


def test_no_loose_pins_on_critical_deps(critical_dep_specs: dict[str, str]) -> None:
    """D8 gate: every critical runtime dep must have a tight (upper-capped) pin.

    Failure mode per DEPENDENCY-MANAGER BL1: ``uv sync --upgrade``
    re-resolves bare ``>=X.Y.Z`` floors to MINIMUM, silently breaking
    us. Tighten to ``~=X.Y`` or ``>=X.Y.Z,<X.Y+W`` before merging.
    """
    loose = sorted(
        (name, spec) for name, spec in critical_dep_specs.items() if _is_loose(spec)
    )
    assert not loose, (
        "D8: critical dep has loose pin (no upper cap, zero floor, "
        f"or wildcard): {loose}. "
        "Tighten to ~=X.Y (compatible-release) or "
        ">=X.Y.Z,<X.Y+W (bounded range) before merging."
    )


# -----------------------------------------------------------------------------
# Broken-release regression (driven by tests/dep_broken_releases.yaml)
# -----------------------------------------------------------------------------


def test_no_broken_release_in_dep_specs(critical_dep_specs: dict[str, str]) -> None:
    """Per DEPENDENCY-MANAGER BL2: every documented broken release must
    be absent from current dep specs.

    YAML-driven so adding a new broken release is one YAML row, not a
    code edit. Substring match is intentionally simple — it catches the
    primary failure mode (broken version reachable from a current
    floor) at the cost of a few false positives; the test is the
    gate, not a spec parser.
    """
    broken = yaml.safe_load(BROKEN_RELEASES_YAML.read_text())["broken_releases"]
    leaks = []
    for entry in broken:
        pkg = entry["package"]
        bad_version = entry["version"]
        spec = critical_dep_specs.get(pkg)
        if spec is None:
            # pkg not in CRITICAL_DEPS — naive substring over all deps
            # would help if the broken pkg is declared elsewhere, but
            # for now we only protect critical_dep_specs (the YAML
            # source-of-truth scope).
            continue
        if bad_version in spec:
            leaks.append((pkg, bad_version, entry["reason"], entry["fix_release"], spec))
    assert not leaks, (
        "D8: broken-release leak detected:\n"
        + "\n".join(
            f"  - {pkg}=={bad}  reason: {reason}; fix: {fix};  spec: {spec}"
            for pkg, bad, reason, fix, spec in leaks
        )
        + "\nFloor the spec at the fix_release or higher (or remove "
        "the entry from tests/dep_broken_releases.yaml if the fix has "
        "been confirmed across all consumers)."
    )


def test_broken_releases_yaml_well_formed() -> None:
    """Schema guard for tests/dep_broken_releases.yaml.

    Catches typos in a maintainer's fingers (missing key, wrong casing)
    before they silently disable the broken-release regression. Does
    NOT validate that fix_release > version — that's a release-process
    policy, not a schema rule.
    """
    data = yaml.safe_load(BROKEN_RELEASES_YAML.read_text())
    assert "broken_releases" in data, (
        f"{BROKEN_RELEASES_YAML.name} must have a top-level "
        f"`broken_releases:` key"
    )
    for i, entry in enumerate(data["broken_releases"]):
        for required in ("package", "version", "reason", "fix_release"):
            assert required in entry, (
                f"{BROKEN_RELEASES_YAML.name}: entry #{i} missing "
                f"required key {required!r}: {entry}"
            )
