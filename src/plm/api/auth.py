"""
API Authentication

Hybrid authentication supporting both API keys and Supabase JWT tokens.
"""

import logging
import os
import secrets
from typing import Optional, Union

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from .supabase_auth import User, decode_supabase_jwt

logger = logging.getLogger("plm.auth")

# API key read from environment
_PLM_API_KEY = os.getenv("PLM_API_KEY")

# Dev mode must be explicitly enabled (security: prevents accidental unauthenticated access)
_DEV_MODE_ENABLED = os.getenv("PLM_ALLOW_DEV_MODE", "").lower() == "true"

if _DEV_MODE_ENABLED:
    logger.warning(
        "DEV MODE ENABLED - Authentication is disabled. "
        "Never use PLM_ALLOW_DEV_MODE=true in production!"
    )

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


def require_api_key(api_key: Optional[str] = Security(api_key_header)) -> str:
    """
    FastAPI dependency that enforces API key authentication.

    Dev mode only activates when PLM_ALLOW_DEV_MODE=true is explicitly set.
    """
    if _DEV_MODE_ENABLED:
        return "dev"

    if not _PLM_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication not configured. Set PLM_API_KEY or enable dev mode.",
        )

    if not api_key or not secrets.compare_digest(api_key, _PLM_API_KEY):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
    return api_key


async def require_auth(
    api_key: Optional[str] = Security(api_key_header),
    bearer: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Union[str, User]:
    """
    Hybrid authentication dependency that accepts either:
    - API key via X-API-Key header
    - Supabase JWT via Authorization: Bearer header

    Dev mode only activates when PLM_ALLOW_DEV_MODE=true is explicitly set.

    Returns:
        Either the API key string or a User object from JWT
    """
    # Dev mode must be explicitly enabled
    if _DEV_MODE_ENABLED:
        return "dev"

    # Try API key first
    if api_key:
        if _PLM_API_KEY and secrets.compare_digest(api_key, _PLM_API_KEY):
            return api_key

    # Try JWT bearer token
    if bearer:
        try:
            payload = decode_supabase_jwt(bearer.credentials)
            return User.from_jwt_payload(payload)
        except HTTPException:
            pass  # Fall through to error

    # Check if authentication is even configured
    if not _PLM_API_KEY and not os.getenv("SUPABASE_JWT_SECRET"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication not configured. Set PLM_API_KEY, SUPABASE_JWT_SECRET, or enable dev mode.",
        )

    # Neither method worked
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing authentication",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_user_id(auth: Union[str, User] = Depends(require_auth)) -> Optional[str]:
    """
    Extract user ID from authentication result.

    Returns:
        User ID if JWT auth, None if API key auth
    """
    if isinstance(auth, User):
        return auth.id
    return None


def require_user_id(auth: Union[str, User] = Depends(require_auth)) -> str:
    """
    Extract user ID from authentication, requiring JWT auth.

    Use this for endpoints that must know the user identity (uploads, workflows, etc.).
    API key auth is not sufficient for these endpoints.

    Returns:
        User ID from JWT

    Raises:
        HTTPException: If API key auth was used instead of JWT
    """
    if isinstance(auth, User):
        return auth.id

    # Dev mode returns a consistent dev user ID
    if auth == "dev":
        return "dev-user"

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="This endpoint requires user authentication (JWT). API key auth is not sufficient.",
    )
