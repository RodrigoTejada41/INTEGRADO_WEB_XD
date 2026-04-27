from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from threading import Lock


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    retry_after_seconds: int = 0


class InMemoryRateLimiter:
    def __init__(self, limit_per_minute: int):
        self.limit_per_minute = max(1, int(limit_per_minute))
        self.window = timedelta(minutes=1)
        self._lock = Lock()
        self._requests: dict[str, deque[datetime]] = defaultdict(deque)

    def allow(self, key: str) -> RateLimitDecision:
        now = datetime.now(UTC)
        cutoff = now - self.window
        with self._lock:
            bucket = self._requests[key]
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            if len(bucket) >= self.limit_per_minute:
                retry_after = max(1, int((bucket[0] + self.window - now).total_seconds()))
                return RateLimitDecision(allowed=False, retry_after_seconds=retry_after)
            bucket.append(now)
            return RateLimitDecision(allowed=True, retry_after_seconds=0)


def rate_limit_key(method: str, path: str, client_host: str) -> str:
    return f"{client_host}:{method}:{path}"
