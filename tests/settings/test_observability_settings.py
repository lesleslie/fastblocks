from fastblocks.adapters.app.default import AppSettings


def test_default_settings_match_v6_spec():
    s = AppSettings()
    assert s.observability.cardinality_mode == "enforce"  # Δ41 ordering
    assert s.observability.metrics.accept_dispatch is True  # Δ9
    assert s.observability.traces.shutdown_on_lifespan_exit is True  # Δ18 / Δ10
    assert s.observability.sentry.disabled_on_import_error is False  # Δ11 loud-fail default
    assert s.observability.sentry.profiling_enabled is False  # Δ20 only safe value when bridging
