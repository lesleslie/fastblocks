import threading
import pytest
from fastblocks.observability import Counter
from fastblocks.observability.errors import MetricNameCollisionError

def test_counter_collision_raises_via_prometheus_chain():
    """Per Δ35: raise from prometheus_client.ValueError to preserve chain."""
    c1 = Counter("collide_test", "first", labelnames=("a",))
    with pytest.raises(MetricNameCollisionError) as exc_info:
        Counter("collide_test", "second", labelnames=("a",))
    assert exc_info.value.metric_name == "collide_test"
    assert isinstance(exc_info.value.__cause__, ValueError)

def test_concurrent_register_thread_safe():
    """Per P1-8: registration-only lock; concurrent Counter calls race-safely."""
    results = []
    def reg(name):
        try:
            Counter(f"concurrent_test_{name}", "test", labelnames=("r",))
            results.append("ok")
        except MetricNameCollisionError:
            results.append("collide")
    threads = [threading.Thread(target=reg, args=(i,)) for i in range(10)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert sum(1 for r in results if r == "ok") == 10
