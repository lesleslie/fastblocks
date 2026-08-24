import pytest
from fastblocks.observability.counters import Counter, Histogram

def test_counter_requires_documentation_arg():
    """Per Δ31: Counter.__init__ requires 'documentation' as 2nd positional."""
    c = Counter("test_demo", "for spec verification", labelnames=("result",))
    assert c is not None

def test_histogram_observe_keyword_only_exemplar():
    """Per P1-2: exemplar is keyword-only; passing positional fails."""
    from fastblocks.observability.counters import Histogram
    h = Histogram("test_demo_h", "histogram for tests", labelnames=(), buckets=(0.01, 1.0))
    h.observe(0.5)
    h.observe(0.5, exemplar={"trace_id": "a"*32, "span_id": "b"*16})
