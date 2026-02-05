"""
Requirements Management Module

Requirements traceability and verification tracking.
"""
from .models import (
    RequirementType,
    RequirementStatus,
    RequirementPriority,
    VerificationMethod,
    VerificationStatus,
    Requirement,
    RequirementLink,
    VerificationRecord,
    TraceabilityMatrix,
)
from .service import RequirementsService, get_requirements_service

__all__ = [
    # Enums
    "RequirementType",
    "RequirementStatus",
    "RequirementPriority",
    "VerificationMethod",
    "VerificationStatus",
    # Models
    "Requirement",
    "RequirementLink",
    "VerificationRecord",
    "TraceabilityMatrix",
    # Service
    "RequirementsService",
    "get_requirements_service",
]
