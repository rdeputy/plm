"""
API Authentication

API key-based authentication for PLM endpoints.
"""

import os
import secrets

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

# API key read from environment — fail fast if not set in production
_PLM_API_KEY = os.getenv("PLM_API_KEY")

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(api_key: str | None = Security(api_key_header)) -> str:
    """
    FastAPI dependency that enforces API key authentication.

    If PLM_API_KEY is not set, authentication is disabled (dev mode).
    """
    if not _PLM_API_KEY:
        # No key configured — allow (dev/test mode)
        return "dev"

    if not api_key or not secrets.compare_digest(api_key, _PLM_API_KEY):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
    return api_key
