import tomllib
from pathlib import Path


def test_observability_group_present_with_correct_pins():
    pyproject = tomllib.loads(Path("pyproject.toml").read_text())
    group = pyproject["dependency-groups"]["observability"]
    members = {
        entry.split("[")[0].split("~")[0].split("=")[0].strip()
        for entry in group
    }
    assert "prometheus-client" in members
    assert "opentelemetry-sdk" in members
    assert "opentelemetry-exporter-otlp-proto-http" in members  # Δ23 proto-http specific
    assert "sentry-sdk" in members
    # No alpha meta-pkg; pin shape ~=X.Y (Δ22)
    for entry in group:
        if entry.startswith("opentelemetry-exporter-otlp-proto-http"):
            assert "~=" in entry, f"missing version pin: {entry}"


def test_monitoring_no_longer_has_sentry_or_urllib3():
    pyproject = tomllib.loads(Path("pyproject.toml").read_text())
    monitoring_str = " ".join(pyproject["dependency-groups"]["monitoring"])
    assert "sentry-sdk" not in monitoring_str
    assert "urllib3" not in monitoring_str


def test_mcp_common_pin_below_0_4_for_tool_pydantic_workaround():
    pyproject = tomllib.loads(Path("pyproject.toml").read_text())
    found = any(
        "mcp-common" in entry and "<0.4" in entry
        for entry in pyproject["dependency-groups"].get("observability", [])
    )
    assert found, "mcp-common<0.4 pin required (Δ47 lifted monkeypatch blast radius)"
