"""Comprehensive tests for FastBlocks caching."""

from datetime import timedelta
from hypothesis import given, settings
from hypothesis import strategies as st
from starlette.requests import Request
from starlette.responses import Response

from fastblocks.caching import CacheDirectives, CacheUtils, Rule


class TestCacheDirectives:
    """Test CacheDirectives TypedDict."""

    @given(
        max_age=st.integers(min_value=0, max_value=86400),
        public=st.booleans(),
        no_cache=st.booleans(),
        no_store=st.booleans(),
        must_revalidate=st.booleans(),
    )
    @settings(max_examples=50)
    def test_cache_directives_construction(
        self,
        max_age: int,
        public: bool,
        no_cache: bool,
        no_store: bool,
        must_revalidate: bool,
    ) -> None:
        """Test CacheDirectives with various combinations using Hypothesis."""
        directives = CacheDirectives(
            max_age=max_age,
            public=public,
            no_cache=no_cache,
            no_store=no_store,
            must_revalidate=must_revalidate,
        )

        assert directives["max_age"] == max_age
        assert directives["public"] == public
        assert directives["no_cache"] == no_cache
        assert directives["no_store"] == no_store
        assert directives["must_revalidate"] == must_revalidate


class TestRule:
    """Test Rule dataclass."""

    def test_rule_creation_basic(self) -> None:
        """Test basic Rule creation."""
        rule = Rule(
            path_regex="/api/.*",
            methods=["GET", "POST"],
        )
        assert rule.path_regex == "/api/.*"
        assert rule.methods == ["GET", "POST"]

    @given(
        path=st.from_regex(r'[a-zA-Z0-9/_-]*'),
        methods=st.lists(
            st.sampled_from(["GET", "POST", "PUT", "DELETE", "PATCH"]),
            min_size=1,
            max_size=3,
            unique=True,
        ),
    )
    @settings(max_examples=30)
    def test_rule_with_various_inputs(self, path: str, methods: list[str]) -> None:
        """Test Rule with various path and method combinations."""
        if not path:
            path = "/.*"

        rule = Rule(
            path_regex=path,
            methods=methods,
        )
        assert rule.path_regex == path
        assert rule.methods == methods


class TestCacheUtils:
    """Test CacheUtils static methods."""

    @given(value=st.integers(min_value=0, max_value=10**9))
    @settings(max_examples=50)
    def test_to_bytes_from_int(self, value: int) -> None:
        """Test to_bytes conversion from integers."""
        result = CacheUtils.to_bytes(value)
        assert result == value

    @given(seconds=st.integers(min_value=0, max_value=86400))
    @settings(max_examples=50)
    def test_format_timedelta(self, seconds: int) -> None:
        """Test format_timedelta with various seconds values."""
        delta = timedelta(seconds=seconds)
        result = CacheUtils.format_timedelta(delta)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_format_timedelta_specific_values(self) -> None:
        """Test format_timedelta with specific known values."""
        assert CacheUtils.format_timedelta(timedelta(seconds=0)) == "0s"
        assert CacheUtils.format_timedelta(timedelta(seconds=1)) == "1s"
        assert CacheUtils.format_timedelta(timedelta(minutes=1)) == "1m"
        assert CacheUtils.format_timedelta(timedelta(hours=1)) == "1h"
        assert CacheUtils.format_timedelta(timedelta(days=1)) == "1d"

    def test_format_timedelta_combined(self) -> None:
        """Test format_timedelta with combined units."""
        delta = timedelta(days=1, hours=2, minutes=3, seconds=4)
        result = CacheUtils.format_timedelta(delta)
        assert "1d" in result
        assert "2h" in result
        assert "3m" in result
        assert "4s" in result

    @given(text=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=['Lu', 'Ll', 'Nd'])))
    @settings(max_examples=30)
    def test_safe_log(self, text: str) -> None:
        """Test safe_log with various text inputs."""
        # Should not raise exception
        CacheUtils.safe_log(None, "info", text)

    def test_safe_log_with_none_logger(self) -> None:
        """Test safe_log with None logger."""
        CacheUtils.safe_log(None, "info", "Test message")

    def test_safe_log_various_levels(self) -> None:
        """Test safe_log with various log levels."""
        for level in ["debug", "info", "warning", "error", "critical"]:
            CacheUtils.safe_log(None, level, f"Test {level} message")
