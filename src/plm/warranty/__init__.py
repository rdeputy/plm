"""
Warranty Management Module

Warranty registration, claims processing, and RMA management.
"""
from .models import (
    WarrantyType,
    WarrantyStatus,
    ClaimStatus,
    ClaimType,
    RMAStatus,
    DispositionAction,
    FailureCategory,
    WarrantyRegistration,
    WarrantyClaim,
    RMA,
    WarrantyPolicy,
    WarrantyMetrics,
)
from .service import WarrantyService, get_warranty_service

__all__ = [
    # Enums
    "WarrantyType",
    "WarrantyStatus",
    "ClaimStatus",
    "ClaimType",
    "RMAStatus",
    "DispositionAction",
    "FailureCategory",
    # Models
    "WarrantyRegistration",
    "WarrantyClaim",
    "RMA",
    "WarrantyPolicy",
    "WarrantyMetrics",
    # Service
    "WarrantyService",
    "get_warranty_service",
]
