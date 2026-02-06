"""
Rate Limiting Middleware

Token bucket rate limiting with configurable limits per endpoint.
Uses in-memory storage (Redis recommended for production clusters).
"""

import os
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Callable, Optional

from fastapi import HTTPException, Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware


@dataclass
class RateLimitConfig:
    """Rate limit configuration."""

    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    burst_size: int = 10  # Allow short bursts


class TokenBucket:
    """Token bucket rate limiter."""

    def __init__(self, rate: float, capacity: int):
        self.rate = rate  # tokens per second
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.monotonic()

    def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens. Returns True if allowed."""
        now = time.monotonic()
        elapsed = now - self.last_update
        self.last_update = now

        # Add tokens based on elapsed time
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    @property
    def retry_after(self) -> int:
        """Seconds until a token is available."""
        if self.tokens >= 1:
            return 0
        return int((1 - self.tokens) / self.rate) + 1


class RateLimiter:
    """In-memory rate limiter with per-client buckets."""

    def __init__(self, config: RateLimitConfig = None):
        self.config = config or RateLimitConfig()
        self.buckets: dict[str, TokenBucket] = defaultdict(self._create_bucket)
        self._cleanup_interval = 300  # 5 minutes
        self._last_cleanup = time.monotonic()

    def _create_bucket(self) -> TokenBucket:
        """Create a new token bucket with configured rate."""
        rate = self.config.requests_per_minute / 60  # tokens per second
        return TokenBucket(rate=rate, capacity=self.config.burst_size)

    def _cleanup_old_buckets(self):
        """Remove stale buckets to prevent memory growth."""
        now = time.monotonic()
        if now - self._last_cleanup < self._cleanup_interval:
            return

        self._last_cleanup = now
        stale_keys = [
            key
            for key, bucket in self.buckets.items()
            if now - bucket.last_update > 3600  # 1 hour
        ]
        for key in stale_keys:
            del self.buckets[key]

    def check(self, client_id: str) -> tuple[bool, int]:
        """
        Check if request is allowed.

        Returns (allowed, retry_after_seconds)
        """
        self._cleanup_old_buckets()
        bucket = self.buckets[client_id]
        allowed = bucket.consume()
        return allowed, bucket.retry_after


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for rate limiting."""

    # Paths exempt from rate limiting
    EXEMPT_PATHS = {"/health", "/", "/docs", "/redoc", "/openapi.json"}

    def __init__(
        self,
        app,
        requests_per_minute: int = None,
        burst_size: int = None,
        enabled: bool = True,
    ):
        super().__init__(app)
        self.enabled = enabled and os.getenv("PLM_RATE_LIMIT_ENABLED", "true").lower() == "true"

        config = RateLimitConfig(
            requests_per_minute=requests_per_minute
            or int(os.getenv("PLM_RATE_LIMIT_RPM", "60")),
            burst_size=burst_size or int(os.getenv("PLM_RATE_LIMIT_BURST", "10")),
        )
        self.limiter = RateLimiter(config)

    def _get_client_id(self, request: Request) -> str:
        """Get unique client identifier."""
        # Use X-Forwarded-For if behind proxy, otherwise client IP
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip if disabled or exempt path
        if not self.enabled or request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)

        client_id = self._get_client_id(request)
        allowed, retry_after = self.limiter.check(client_id)

        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers={"Retry-After": str(retry_after)},
            )

        response = await call_next(request)

        # Add rate limit headers
        bucket = self.limiter.buckets[client_id]
        response.headers["X-RateLimit-Limit"] = str(self.limiter.config.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(int(bucket.tokens))

        return response
