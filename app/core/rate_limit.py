"""Small process-local fixed-window rate limiter for the prototype."""

from collections import defaultdict, deque
from threading import Lock
from time import monotonic

from fastapi import HTTPException, status


class InMemoryRateLimiter:
    """Bound repeated actions without requiring external infrastructure."""

    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(
        self,
        key: str,
        *,
        limit: int,
        window_seconds: int,
        now: float | None = None,
    ) -> None:
        timestamp = monotonic() if now is None else now
        boundary = timestamp - window_seconds
        with self._lock:
            events = self._events[key]
            while events and events[0] <= boundary:
                events.popleft()
            if len(events) >= limit:
                retry_after = max(
                    1,
                    int(window_seconds - (timestamp - events[0])),
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests. Please try again later.",
                    headers={"Retry-After": str(retry_after)},
                )
            events.append(timestamp)

    def clear(self) -> None:
        """Reset state for deterministic automated tests."""
        with self._lock:
            self._events.clear()


rate_limiter = InMemoryRateLimiter()
