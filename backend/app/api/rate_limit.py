import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

# Very lightweight in-memory rate limiter (per IP).
# For production, replace with Redis or a proper gateway throttle.

WINDOW_SEC = 60
MAX_CALLS = 20

_buckets: dict[str, deque[float]] = defaultdict(deque)


def rate_limit(
    request: Request,
    key: str | None = None,
    max_calls: int | None = None,
    window_sec: int | None = None,
) -> None:
    ip = request.client.host if request and request.client else "unknown"
    path = request.url.path if request else ""
    bucket_key = key or f"{ip}:{path}"
    now = time.time()
    bucket = _buckets[bucket_key]
    limit = max_calls if max_calls is not None else MAX_CALLS
    window = window_sec if window_sec is not None else WINDOW_SEC

    # drop old
    while bucket and now - bucket[0] > window:
        bucket.popleft()

    if len(bucket) >= limit:
        raise HTTPException(status_code=429, detail="Too many requests. Please wait a moment.")

    bucket.append(now)
