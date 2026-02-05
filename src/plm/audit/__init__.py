"""
Audit Trail Module

Provides comprehensive audit logging for all PLM entities.
Tracks:
- Who made changes
- What changed (old value -> new value)
- When changes occurred
- Why (linked to ECO if applicable)
"""
from .models import AuditAction, AuditEntry
from .service import AuditService, get_audit_service

__all__ = [
    "AuditAction",
    "AuditEntry",
    "AuditService",
    "get_audit_service",
]
