"""
Prometheus Metrics

Exposes application metrics for monitoring and alerting.
"""

import time
from typing import Callable

from fastapi import Request, Response
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

# Request metrics
REQUEST_COUNT = Counter(
    "plm_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

REQUEST_LATENCY = Histogram(
    "plm_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

# Active requests gauge
REQUESTS_IN_PROGRESS = Gauge(
    "plm_http_requests_in_progress",
    "Number of HTTP requests currently being processed",
    ["method"],
)

# Business metrics
PARTS_CREATED = Counter(
    "plm_parts_created_total",
    "Total parts created",
)

DOCUMENTS_UPLOADED = Counter(
    "plm_documents_uploaded_total",
    "Total documents uploaded",
    ["document_type"],
)

WORKFLOW_DECISIONS = Counter(
    "plm_workflow_decisions_total",
    "Total workflow decisions made",
    ["decision"],
)

# Database metrics
DB_QUERY_DURATION = Histogram(
    "plm_db_query_duration_seconds",
    "Database query duration in seconds",
    ["operation"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
)

# Rate limiter metrics
RATE_LIMIT_HITS = Counter(
    "plm_rate_limit_hits_total",
    "Total requests that hit rate limits",
)


def normalize_path(path: str) -> str:
    """
    Normalize URL paths by replacing IDs with placeholders.

    This prevents high cardinality in metrics from unique IDs.
    """
    import re
    # Replace UUIDs
    path = re.sub(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "{id}", path)
    # Replace numeric IDs
    path = re.sub(r"/\d+(/|$)", "/{id}\\1", path)
    return path


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to collect request metrics."""

    # Paths to skip for metrics collection
    SKIP_PATHS = {"/metrics", "/health", "/docs", "/redoc", "/openapi.json"}

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Skip metrics for certain paths
        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)

        method = request.method
        path = normalize_path(request.url.path)

        REQUESTS_IN_PROGRESS.labels(method=method).inc()
        start_time = time.perf_counter()

        try:
            response = await call_next(request)
            status = response.status_code
        except Exception:
            status = 500
            raise
        finally:
            duration = time.perf_counter() - start_time
            REQUESTS_IN_PROGRESS.labels(method=method).dec()
            REQUEST_COUNT.labels(method=method, endpoint=path, status=status).inc()
            REQUEST_LATENCY.labels(method=method, endpoint=path).observe(duration)

        return response


def get_metrics() -> bytes:
    """Generate Prometheus metrics output."""
    return generate_latest()


def get_metrics_content_type() -> str:
    """Get the content type for Prometheus metrics."""
    return CONTENT_TYPE_LATEST
