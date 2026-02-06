"""
Supabase JWT Authentication

Validates JWT tokens issued by Supabase for user authentication.
"""

import os
from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# Optional import — gracefully degrade if jose not installed
try:
    from jose import jwt, JWTError
    JOSE_AVAILABLE = True
except ImportError:
    JOSE_AVAILABLE = False
    jwt = None
    JWTError = Exception

# Supabase configuration from environment
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")

# JWT algorithm used by Supabase
JWT_ALGORITHM = "HS256"

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class User:
    """Authenticated user from Supabase JWT."""

    id: str
    email: Optional[str] = None
    role: str = "authenticated"

    @classmethod
    def from_jwt_payload(cls, payload: dict) -> "User":
        """Create User from decoded JWT payload."""
        return cls(
            id=payload.get("sub", ""),
            email=payload.get("email"),
            role=payload.get("role", "authenticated"),
        )


def decode_supabase_jwt(token: str) -> dict:
    """
    Decode and validate a Supabase JWT token.

    Args:
        token: The JWT token string

    Returns:
        The decoded payload dict

    Raises:
        HTTPException: If token is invalid or expired
    """
    if not JOSE_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="JWT validation not available (python-jose not installed)",
        )

    if not SUPABASE_JWT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SUPABASE_JWT_SECRET not configured",
        )

    try:
        payload = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            options={"verify_aud": False},  # Supabase doesn't set aud by default
        )
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Optional[User]:
    """
    FastAPI dependency to get the current authenticated user from JWT.

    Returns None if no token provided (for optional auth).
    Raises HTTPException if token is invalid.
    """
    if credentials is None:
        return None

    payload = decode_supabase_jwt(credentials.credentials)
    return User.from_jwt_payload(payload)


async def require_user(
    user: Optional[User] = Depends(get_current_user),
) -> User:
    """
    FastAPI dependency that requires an authenticated user.

    Raises HTTPException if no valid token provided.
    """
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
