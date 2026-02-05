"""
Quality Management Module

Integrated quality management for PLM:
- NCRs (Non-Conformance Reports)
- CAPAs (Corrective and Preventive Actions)
- Inspection records
- Quality holds
"""
from .models import (
    NCRStatus,
    NCRSeverity,
    NCRSource,
    CAPAType,
    CAPAStatus,
    NonConformanceReport,
    CAPA,
    InspectionRecord,
    QualityHold,
)
from .service import QualityService, get_quality_service

__all__ = [
    # Models
    "NCRStatus",
    "NCRSeverity",
    "NCRSource",
    "CAPAType",
    "CAPAStatus",
    "NonConformanceReport",
    "CAPA",
    "InspectionRecord",
    "QualityHold",
    # Service
    "QualityService",
    "get_quality_service",
]
