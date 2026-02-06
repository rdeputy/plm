"""
Security Headers Middleware

Adds security-related HTTP headers to all responses.
"""

import os
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.

    Headers added:
    - Content-Security-Policy: Restricts resource loading
    - X-Content-Type-Options: Prevents MIME sniffing
    - X-Frame-Options: Prevents clickjacking
    - X-XSS-Protection: Legacy XSS protection
    - Referrer-Policy: Controls referrer information
    - Permissions-Policy: Restricts browser features
    """

    def __init__(self, app, csp_policy: str | None = None):
        super().__init__(app)

        # Default CSP - restrictive but allows API functionality
        default_csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "  # Allow inline for Swagger UI
            "style-src 'self' 'unsafe-inline'; "   # Allow inline for Swagger UI
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "form-action 'self'; "
            "base-uri 'self'"
        )

        self.csp_policy = csp_policy or os.getenv("PLM_CSP_POLICY", default_csp)
        self.enabled = os.getenv("PLM_SECURITY_HEADERS", "true").lower() == "true"

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)

        if not self.enabled:
            return response

        # Content Security Policy
        response.headers["Content-Security-Policy"] = self.csp_policy

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Clickjacking protection
        response.headers["X-Frame-Options"] = "DENY"

        # Legacy XSS protection (for older browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Control referrer information
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Restrict browser features
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), "
            "camera=(), "
            "geolocation=(), "
            "gyroscope=(), "
            "magnetometer=(), "
            "microphone=(), "
            "payment=(), "
            "usb=()"
        )

        # HSTS - only if explicitly enabled (should be set by reverse proxy in production)
        if os.getenv("PLM_ENABLE_HSTS", "").lower() == "true":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

        return response
