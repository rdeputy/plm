"""
Rate Limiting Middleware

Token bucket rate limiting with configurable limits per endpoint.
Uses in-memory storage (Redis recommended for production clusters).

Security: Only trusts X-Forwarded-For from configured trusted proxies.
"""

import logging
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Optional

from fastapi import HTTPException, Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

logger = logging.getLogger("plm.rate_limit")


@dataclass
class RateLimitConfig:
    """Rate limit configuration."""

    requests_per_minute: int = 60
    burst_size: int = 10  # Allow short bursts
    max_buckets: int = 10000  # Prevent memory exhaustion
    trusted_proxies: set[str] = field(default_factory=set)  # IPs allowed to set X-Forwarded-For


class TokenBucket:
    """Thread-safe token bucket rate limiter."""

    def __init__(self, rate: float, capacity: int):
        self.rate = rate  # tokens per second
        self.capacity = capacity
        self.tokens = float(capacity)
        self.last_update = time.monotonic()
        self._lock = threading.Lock()

    def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens. Returns True if allowed. Thread-safe."""
        with self._lock:
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
        with self._lock:
            if self.tokens >= 1:
                return 0
            return int((1 - self.tokens) / self.rate) + 1


class RateLimiter:
    """Thread-safe in-memory rate limiter with per-client buckets."""

    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        self._buckets: dict[str, TokenBucket] = {}
        self._lock = threading.Lock()
        self._cleanup_interval = 300  # 5 minutes
        self._last_cleanup = time.monotonic()

    def _create_bucket(self) -> TokenBucket:
        """Create a new token bucket with configured rate."""
        rate = self.config.requests_per_minute / 60  # tokens per second
        return TokenBucket(rate=rate, capacity=self.config.burst_size)

    def _cleanup_old_buckets(self) -> None:
        """Remove stale buckets to prevent memory growth. Must hold lock."""
        now = time.monotonic()
        if now - self._last_cleanup < self._cleanup_interval:
            return

        self._last_cleanup = now
        stale_keys = [
            key
            for key, bucket in self._buckets.items()
            if now - bucket.last_update > 3600  # 1 hour
        ]
        for key in stale_keys:
            del self._buckets[key]

        if stale_keys:
            logger.debug(f"Cleaned up {len(stale_keys)} stale rate limit buckets")

    def _evict_oldest_bucket(self) -> None:
        """Evict oldest bucket when at capacity. Must hold lock."""
        if not self._buckets:
            return
        oldest_key = min(self._buckets.keys(), key=lambda k: self._buckets[k].last_update)
        del self._buckets[oldest_key]
        logger.warning(f"Rate limit bucket evicted due to capacity: {oldest_key[:20]}...")

    def get_bucket(self, client_id: str) -> TokenBucket:
        """Get or create a bucket for client. Thread-safe."""
        with self._lock:
            self._cleanup_old_buckets()

            if client_id not in self._buckets:
                # Evict oldest if at capacity
                if len(self._buckets) >= self.config.max_buckets:
                    self._evict_oldest_bucket()
                self._buckets[client_id] = self._create_bucket()

            return self._buckets[client_id]

    def check(self, client_id: str) -> tuple[bool, int]:
        """
        Check if request is allowed. Thread-safe.

        Returns (allowed, retry_after_seconds)
        """
        bucket = self.get_bucket(client_id)
        allowed = bucket.consume()
        return allowed, bucket.retry_after

    @property
    def bucket_count(self) -> int:
        """Current number of tracked clients."""
        with self._lock:
            return len(self._buckets)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for rate limiting with trusted proxy support."""

    # Paths exempt from rate limiting
    EXEMPT_PATHS = {"/health", "/", "/docs", "/redoc", "/openapi.json"}

    def __init__(
        self,
        app,
        requests_per_minute: Optional[int] = None,
        burst_size: Optional[int] = None,
        enabled: bool = True,
    ):
        super().__init__(app)
        self.enabled = enabled and os.getenv("PLM_RATE_LIMIT_ENABLED", "true").lower() == "true"

        # Parse trusted proxies from env (comma-separated IPs)
        trusted_proxies_env = os.getenv("PLM_TRUSTED_PROXIES", "")
        trusted_proxies = {ip.strip() for ip in trusted_proxies_env.split(",") if ip.strip()}

        # Parse config with error handling
        try:
            rpm = requests_per_minute or int(os.getenv("PLM_RATE_LIMIT_RPM", "60"))
        except ValueError:
            rpm = 60

        try:
            burst = burst_size or int(os.getenv("PLM_RATE_LIMIT_BURST", "10"))
        except ValueError:
            burst = 10

        config = RateLimitConfig(
            requests_per_minute=rpm,
            burst_size=burst,
            trusted_proxies=trusted_proxies,
        )
        self.limiter = RateLimiter(config)
        self.trusted_proxies = trusted_proxies

        if trusted_proxies:
            logger.info(f"Rate limiter trusting proxies: {trusted_proxies}")

    def _get_client_id(self, request: Request) -> str:
        """
        Get unique client identifier securely.

        Only trusts X-Forwarded-For header when the direct client IP
        is in the trusted_proxies set. This prevents IP spoofing attacks.
        """
        direct_ip = request.client.host if request.client else "unknown"

        # Only trust X-Forwarded-For from trusted proxies
        if direct_ip in self.trusted_proxies:
            forwarded = request.headers.get("x-forwarded-for")
            if forwarded:
                # Take the rightmost untrusted IP (closest to client)
                ips = [ip.strip() for ip in forwarded.split(",")]
                for ip in reversed(ips):
                    if ip not in self.trusted_proxies:
                        return ip
                # All IPs are trusted proxies, use the leftmost (original client)
                return ips[0] if ips else direct_ip

        return direct_ip

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
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
