from fastblocks.observability.errors import (
    ObservabilityError, MissingDependencyError, MetricNameCollisionError, SentryImportError,
)

def test_missing_dependency_carries_structured_fields():
    e = MissingDependencyError(pip_group="observability", package="prometheus-client")
    assert e.pip_group == "observability"
    assert e.package == "prometheus-client"
    assert isinstance(e, ObservabilityError)
    assert isinstance(e, Exception)

def test_metric_name_collision_uses_prometheus_chain():
    """Per Δ35: raise MetricNameCollisionError(...) from prometheus_client.ValueError."""
    try:
        try:
            raise ValueError("Duplicated timeseries in CollectorRegistry")
        except ValueError as inner:
            raise MetricNameCollisionError(metric_name="foo") from inner
    except MetricNameCollisionError as e:
        assert e.metric_name == "foo"
        assert isinstance(e.__cause__, ValueError)
