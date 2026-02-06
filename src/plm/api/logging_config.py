"""
Structured JSON Logging Configuration

Provides JSON-formatted logs for production environments with
configurable log levels and request/response logging middleware.
"""

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from typing import Callable
from uuid import uuid4

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class JSONFormatter(logging.Formatter):
    """Format log records as JSON for log aggregation systems."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "extra_data"):
            log_data.update(record.extra_data)

        return json.dumps(log_data)


def configure_logging() -> logging.Logger:
    """
    Configure structured logging based on environment.

    Returns the root PLM logger.
    """
    log_level = os.getenv("PLM_LOG_LEVEL", "INFO").upper()
    log_format = os.getenv("PLM_LOG_FORMAT", "json")  # json or text

    # Create PLM logger
    logger = logging.getLogger("plm")
    logger.setLevel(getattr(logging, log_level, logging.INFO))

    # Remove existing handlers
    logger.handlers.clear()

    # Create handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)

    if log_format == "json":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )

    logger.addHandler(handler)

    # Also configure uvicorn loggers for JSON
    if log_format == "json":
        for name in ["uvicorn", "uvicorn.access", "uvicorn.error"]:
            uvi_logger = logging.getLogger(name)
            uvi_logger.handlers.clear()
            uvi_logger.addHandler(handler)

    return logger


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all HTTP requests and responses."""

    def __init__(self, app, logger: logging.Logger = None):
        super().__init__(app)
        self.logger = logger or logging.getLogger("plm.http")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid4())[:8]
        start_time = time.perf_counter()

        # Add request ID to request state for access in handlers
        request.state.request_id = request_id

        # Log request
        self.logger.info(
            f"{request.method} {request.url.path}",
            extra={
                "extra_data": {
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "query": str(request.query_params),
                    "client_ip": request.client.host if request.client else None,
                    "user_agent": request.headers.get("user-agent", ""),
                }
            },
        )

        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self.logger.error(
                f"{request.method} {request.url.path} - Error",
                extra={
                    "extra_data": {
                        "request_id": request_id,
                        "duration_ms": round(duration_ms, 2),
                        "error": str(e),
                    }
                },
                exc_info=True,
            )
            raise

        duration_ms = (time.perf_counter() - start_time) * 1000

        # Log response
        self.logger.info(
            f"{request.method} {request.url.path} - {response.status_code}",
            extra={
                "extra_data": {
                    "request_id": request_id,
                    "status_code": response.status_code,
                    "duration_ms": round(duration_ms, 2),
                }
            },
        )

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        return response


# Initialize logger on import
logger = configure_logging()
