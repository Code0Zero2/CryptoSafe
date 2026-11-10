"""Login throttling and rate limiting service to mitigate brute-force attacks."""

import time
from collections import defaultdict
from dataclasses import dataclass, field
from cryptosafe.common.errors import AuthenticationError

@dataclass
class AttemptTracker:
    failure_count: int = 0
    locked_until: float = 0.0

class LoginRateLimiter:
    """In-memory rate limiter enforcing progressive cooldown on consecutive failures."""

    def __init__(self, max_attempts: int = 5, lockout_seconds: int = 30):
        self.max_attempts = max_attempts
        self.lockout_seconds = lockout_seconds
        self._trackers: dict[str, AttemptTracker] = defaultdict(AttemptTracker)

    def check_rate_limit(self, username: str) -> None:
        """Check if username is currently locked out. Raises AuthenticationError if locked."""
        key = username.strip().lower()
        tracker = self._trackers[key]
        now = time.time()

        if tracker.locked_until > now:
            remaining = int(tracker.locked_until - now) + 1
            raise AuthenticationError(
                f"Terlalu banyak percobaan login gagal. Akun dikunci sementara. Silakan coba lagi dalam {remaining} detik."
            )

    def record_failure(self, username: str) -> None:
        """Record a failed login attempt, activating lockout if max attempts exceeded."""
        key = username.strip().lower()
        tracker = self._trackers[key]
        now = time.time()

        # If previous lockout expired, reset count
        if tracker.locked_until > 0 and tracker.locked_until <= now:
            tracker.failure_count = 0
            tracker.locked_until = 0.0

        tracker.failure_count += 1
        if tracker.failure_count >= self.max_attempts:
            tracker.locked_until = now + self.lockout_seconds

    def record_success(self, username: str) -> None:
        """Clear failed attempts on successful authentication."""
        key = username.strip().lower()
        if key in self._trackers:
            del self._trackers[key]

