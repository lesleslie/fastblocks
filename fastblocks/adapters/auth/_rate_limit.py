"""In-memory token-bucket rate limiter with account lockout.

The limiter is process-local. It is sufficient for single-instance
deployments and as a local fallback when a shared rate-limit store is
unavailable. State is keyed by an arbitrary subject string (typically a
username, IP address, or API key).

Pattern mirrors splashstand's ``splashstand.security.rate_limit.RateLimiter``
so behavior is consistent across the Bodai ecosystem.
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass

__all__ = ["RateLimiter", "basic_auth_limiter"]


@dataclass
class _SubjectState:
    tokens: float
    last_refill: float
    failures: int


class RateLimiter:
    """Token-bucket rate limiter + consecutive-failure lockout.

    Parameters
    ----------
    max_attempts:
        Maximum number of ``try_acquire`` calls allowed within ``window_seconds``.
    window_seconds:
        Refill window in seconds. Tokens refill linearly at
        ``max_attempts / window_seconds`` per second.
    lockout_threshold:
        Number of consecutive ``record_failure`` calls that triggers a
        lockout. A single ``record_success`` resets the failure count.
    """

    def __init__(
        self,
        max_attempts: int = 10,
        window_seconds: int = 300,
        lockout_threshold: int = 25,
    ) -> None:
        if max_attempts <= 0:
            raise ValueError("max_attempts must be > 0")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be > 0")
        if lockout_threshold <= 0:
            raise ValueError("lockout_threshold must be > 0")
        self._max_attempts = max_attempts
        self._window_seconds = window_seconds
        self._lockout_threshold = lockout_threshold
        self._state: dict[str, _SubjectState] = defaultdict(
            lambda: _SubjectState(
                tokens=float(self._max_attempts),
                last_refill=self._now(),
                failures=0,
            )
        )

    @property
    def max_attempts(self) -> int:
        return self._max_attempts

    @property
    def window_seconds(self) -> int:
        return self._window_seconds

    @property
    def lockout_threshold(self) -> int:
        return self._lockout_threshold

    def _now(self) -> float:
        return time.monotonic()

    def _refill(self, state: _SubjectState) -> None:
        now = self._now()
        elapsed = now - state.last_refill
        state.last_refill = now
        if elapsed <= 0:
            # Clock went backward (or is unchanged). Reset to a full bucket
            # so virtual-clock test overrides behave deterministically.
            state.tokens = float(self._max_attempts)
            return
        rate = self._max_attempts / self._window_seconds
        state.tokens = min(float(self._max_attempts), state.tokens + elapsed * rate)

    def try_acquire(self, subject: str) -> bool:
        """Consume a token. Return ``False`` if locked out or budget empty."""
        if self.is_locked_out(subject):
            return False
        state = self._state[subject]
        self._refill(state)
        if state.tokens >= 1:
            state.tokens -= 1
            return True
        return False

    def record_failure(self, subject: str) -> None:
        """Increment the consecutive-failure count for ``subject``."""
        state = self._state[subject]
        state.failures += 1

    def record_success(self, subject: str) -> None:
        """Reset the consecutive-failure count for ``subject``."""
        state = self._state[subject]
        state.failures = 0

    def is_locked_out(self, subject: str) -> bool:
        """Return ``True`` if ``subject`` has met or exceeded the lockout threshold."""
        state = self._state[subject]
        return state.failures >= self._lockout_threshold

    def reset(self, subject: str) -> None:
        """Clear all state for ``subject`` (tokens, failures, refill time)."""
        self._state.pop(subject, None)


# Process-local singleton used by the basic auth adapter. Defaults match
# the Phase 1.5 spec: 10 attempts / 5 min, lockout after 25 consecutive
# failures.
basic_auth_limiter = RateLimiter(
    max_attempts=10,
    window_seconds=300,
    lockout_threshold=25,
)
