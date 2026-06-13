"""Tests for basic auth rate limiter + lockout (Phase 1.5.a).

Mirrors the splashstand RateLimiter pattern: token-bucket (10 / 5 min)
plus consecutive-failure lockout (after 25).
"""

from __future__ import annotations

import pytest
from fastblocks.adapters.auth._rate_limit import RateLimiter, basic_auth_limiter


@pytest.mark.unit
class TestRateLimiterBasics:
    def test_try_acquire_within_budget(self) -> None:
        limiter = RateLimiter(max_attempts=10, window_seconds=300, lockout_threshold=25)
        for _ in range(10):
            assert limiter.try_acquire("alice") is True

    def test_try_acquire_after_budget_exhausted_returns_false(self) -> None:
        limiter = RateLimiter(max_attempts=10, window_seconds=300, lockout_threshold=25)
        for _ in range(10):
            limiter.try_acquire("alice")
        assert limiter.try_acquire("alice") is False

    def test_lockout_after_25_consecutive_failures(self) -> None:
        limiter = RateLimiter(
            max_attempts=100,  # large so budget doesn't interfere
            window_seconds=300,
            lockout_threshold=25,
        )
        for _ in range(25):
            limiter.record_failure("carol")
        assert limiter.is_locked_out("carol") is True
        # Locked-out subjects are denied even if budget remains
        assert limiter.try_acquire("carol") is False

    def test_record_success_resets_failure_count(self) -> None:
        limiter = RateLimiter(
            max_attempts=100, window_seconds=300, lockout_threshold=25
        )
        for _ in range(24):
            limiter.record_failure("dave")
        limiter.record_success("dave")
        # After a success, 24 more failures should NOT lock out
        for _ in range(24):
            limiter.record_failure("dave")
        assert limiter.is_locked_out("dave") is False

    def test_reset_clears_state(self) -> None:
        limiter = RateLimiter(max_attempts=2, window_seconds=300, lockout_threshold=25)
        limiter.record_failure("eve")
        limiter.record_failure("eve")
        limiter.reset("eve")
        assert limiter.is_locked_out("eve") is False
        assert limiter.try_acquire("eve") is True


@pytest.mark.unit
class TestBasicAuthLimiterDefaults:
    def test_default_limiter_uses_10_per_5min_25_lockout(self) -> None:
        """basic_auth_limiter should ship with the spec defaults."""
        assert basic_auth_limiter.max_attempts == 10
        assert basic_auth_limiter.window_seconds == 300
        assert basic_auth_limiter.lockout_threshold == 25
