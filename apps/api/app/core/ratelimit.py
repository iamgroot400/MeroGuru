"""Per-client request ceilings and a request body cap.

The API has no authentication by design (single-user, self-hosted), so nothing
otherwise bounds how often an endpoint can be called. That matters most for
plan generation, where one request drives a roadmap call plus a per-lesson
generation against the operator's paid provider key.

Deliberately dependency-free and in-process: a fixed-window counter in a dict,
which is proportionate for a single-user deployment. Two consequences worth
knowing: counters are per-worker (a multi-worker deployment multiplies the
effective limit by the worker count), and they reset on restart. An instance
exposed to a real network wants a reverse proxy doing this properly.
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings

# Endpoints whose cost is dominated by outbound AI calls rather than local work.
_EXPENSIVE_SUFFIX = "/generate-plan"


class _FixedWindowCounter:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._windows: dict[tuple[str, str], tuple[int, int]] = defaultdict(lambda: (0, 0))

    def hit(self, key: str, bucket: str, limit: int, window_seconds: int) -> bool:
        """Record a request. Returns True if it is within the limit."""
        if limit <= 0:
            return True
        now = int(time.time())
        window_start = now - (now % window_seconds)
        with self._lock:
            recorded_start, count = self._windows[(key, bucket)]
            if recorded_start != window_start:
                recorded_start, count = window_start, 0
            count += 1
            self._windows[(key, bucket)] = (recorded_start, count)
            return count <= limit


_counter = _FixedWindowCounter()


def _client_key(request: Request) -> str:
    return request.client.host if request.client else "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/health"):
            return await call_next(request)

        declared = request.headers.get("content-length")
        if declared is not None:
            try:
                if int(declared) > settings.max_request_bytes:
                    return JSONResponse({"detail": "request body too large"}, status_code=413)
            except ValueError:
                return JSONResponse({"detail": "invalid content-length"}, status_code=400)

        key = _client_key(request)

        if not _counter.hit(key, "global", settings.rate_limit_per_minute, 60):
            return JSONResponse({"detail": "too many requests"}, status_code=429)

        if request.method == "POST" and request.url.path.endswith(_EXPENSIVE_SUFFIX):
            if not _counter.hit(
                key, "generate_plan", settings.plan_generation_rate_limit_per_hour, 3600
            ):
                return JSONResponse(
                    {"detail": "plan generation rate limit exceeded"}, status_code=429
                )

        return await call_next(request)
