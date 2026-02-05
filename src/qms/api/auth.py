"""
QMS API Authentication

Reuses PLM authentication for now - can be customized for QMS-specific auth.
"""

from plm.api.auth import require_api_key

__all__ = ["require_api_key"]
