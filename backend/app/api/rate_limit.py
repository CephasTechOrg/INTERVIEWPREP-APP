import time
from collections import deque, defaultdict

from fastapi import HTTPException, Request

# Very lightweight in-memory rate limiter (per IP).
# For production, replace with Redis or a proper gateway throttle.

WINDOW_SEC = 60
MAX_CALLS = 20

_buckets: dict[str, deque[float]] = defaultdict(deque)


def rate_limit(request: Request) -> None:
    ip = request.client.host if request and request.client else "unknown"
    now = time.time()
    bucket = _buckets[ip]

    # drop old
    while bucket and now - bucket[0] > WINDOW_SEC:
        bucket.popleft()

    if len(bucket) >= MAX_CALLS:
        raise HTTPException(status_code=429, detail="Too many requests. Please wait a moment.")

    bucket.append(now)
