"""
Quality Management Module

Quality management for QMS:
- NCRs (Non-Conformance Reports)
- CAPAs (Corrective and Preventive Actions)
- Inspection records
- Quality holds
"""
from .models import (
    NCRStatus,
    NCRSeverity,
    NCRSource,
    DispositionType,
    CAPAType,
    CAPAStatus,
    NonConformanceReport,
    CAPA,
    InspectionRecord,
    QualityHold,
)
from .service import QualityService, get_quality_service

__all__ = [
    # Enums
    "NCRStatus",
    "NCRSeverity",
    "NCRSource",
    "DispositionType",
    "CAPAType",
    "CAPAStatus",
    # Models
    "NonConformanceReport",
    "CAPA",
    "InspectionRecord",
    "QualityHold",
    # Service
    "QualityService",
    "get_quality_service",
]
