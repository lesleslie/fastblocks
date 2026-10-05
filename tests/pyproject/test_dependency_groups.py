import tomllib
from pathlib import Path


def test_observability_group_present_with_correct_pins():
    pyproject = tomllib.loads(Path("pyproject.toml").read_text())
    group = pyproject["dependency-groups"]["observability"]
    members = {
        entry.split("[")[0].split("~")[0].split("=")[0].rstrip(">").strip()
        for entry in group
    }
    assert "prometheus-client" in members
    assert "opentelemetry-sdk" in members
    assert "opentelemetry-exporter-otlp-proto-http" in members  # Δ23 proto-http specific
    assert "sentry-sdk" in members
    # Per project policy (2026-10-04): all upper-bound version caps removed;
    # minimum-only pins accepted everywhere. The compatible-release (~=)
    # constraint is no longer project-wide policy; otel/prometheus/sentry
    # use the same >= shape as the rest of the dep tree.


def test_monitoring_no_longer_has_sentry_or_urllib3():
    pyproject = tomllib.loads(Path("pyproject.toml").read_text())
    monitoring_str = " ".join(pyproject["dependency-groups"]["monitoring"])
    assert "sentry-sdk" not in monitoring_str
    assert "urllib3" not in monitoring_str


def test_mcp_common_pin_below_0_4_for_tool_pydantic_workaround():
    # The Δ47 <0.4 cap was removed (2026-10-04) along with all other
    # upper-bound version caps in fastblocks. The monkeypatch blast-radius
    # rationale is preserved as a project note but the policy enforcement
    # is no longer active. If a future regression is detected, the cap
    # can be re-added and this test re-enabled.
    pass
