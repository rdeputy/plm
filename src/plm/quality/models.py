"""
Quality Management Models

Data structures for quality management integration with PLM.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Optional


class NCRStatus(str, Enum):
    """Non-Conformance Report status."""
    DRAFT = "draft"
    OPEN = "open"
    UNDER_INVESTIGATION = "under_investigation"
    PENDING_DISPOSITION = "pending_disposition"
    DISPOSITION_APPROVED = "disposition_approved"
    IN_REWORK = "in_rework"
    PENDING_VERIFICATION = "pending_verification"
    CLOSED = "closed"
    VOIDED = "voided"


class NCRSeverity(str, Enum):
    """NCR severity levels."""
    CRITICAL = "critical"       # Safety/compliance risk
    MAJOR = "major"             # Significant quality issue
    MINOR = "minor"             # Cosmetic or minor deviation
    OBSERVATION = "observation" # Potential concern


class NCRSource(str, Enum):
    """Where the non-conformance was detected."""
    INCOMING_INSPECTION = "incoming_inspection"
    IN_PROCESS = "in_process"
    FINAL_INSPECTION = "final_inspection"
    CUSTOMER_COMPLAINT = "customer_complaint"
    INTERNAL_AUDIT = "internal_audit"
    EXTERNAL_AUDIT = "external_audit"
    FIELD_FAILURE = "field_failure"
    SUPPLIER = "supplier"


class DispositionType(str, Enum):
    """NCR disposition options."""
    USE_AS_IS = "use_as_is"
    REWORK = "rework"
    REPAIR = "repair"
    SCRAP = "scrap"
    RETURN_TO_SUPPLIER = "return_to_supplier"
    DEVIATION = "deviation"


class CAPAType(str, Enum):
    """CAPA type."""
    CORRECTIVE = "corrective"   # Fix existing problem
    PREVENTIVE = "preventive"   # Prevent potential problem


class CAPAStatus(str, Enum):
    """CAPA status."""
    DRAFT = "draft"
    OPEN = "open"
    ROOT_CAUSE_ANALYSIS = "root_cause_analysis"
    ACTION_PLANNING = "action_planning"
    IMPLEMENTATION = "implementation"
    VERIFICATION = "verification"
    EFFECTIVENESS_REVIEW = "effectiveness_review"
    CLOSED = "closed"
    CANCELLED = "cancelled"


@dataclass
class NonConformanceReport:
    """
    Non-Conformance Report (NCR).

    Documents a deviation from requirements, specifications,
    or standards for parts, materials, or processes.
    """
    id: str
    ncr_number: str                     # "NCR-2024-0001"

    # Classification
    status: NCRStatus = NCRStatus.DRAFT
    severity: NCRSeverity = NCRSeverity.MINOR
    source: NCRSource = NCRSource.IN_PROCESS

    # What's non-conforming
    title: str = ""
    description: str = ""
    requirements_violated: list[str] = field(default_factory=list)

    # Related items
    part_id: Optional[str] = None
    part_number: Optional[str] = None
    part_revision: Optional[str] = None
    bom_id: Optional[str] = None
    lot_number: Optional[str] = None
    serial_numbers: list[str] = field(default_factory=list)
    po_id: Optional[str] = None
    supplier_id: Optional[str] = None

    # Quantity
    quantity_affected: Decimal = Decimal("1")
    quantity_rejected: Decimal = Decimal("0")
    unit_of_measure: str = "EA"

    # Project context
    project_id: Optional[str] = None

    # Investigation
    root_cause: Optional[str] = None
    immediate_action: Optional[str] = None
    containment_action: Optional[str] = None

    # Disposition
    disposition: Optional[DispositionType] = None
    disposition_notes: Optional[str] = None
    disposition_by: Optional[str] = None
    disposition_date: Optional[datetime] = None

    # Cost
    estimated_cost: Decimal = Decimal("0")
    actual_cost: Decimal = Decimal("0")

    # Linked CAPA
    capa_id: Optional[str] = None
    capa_required: bool = False

    # Lifecycle
    detected_by: Optional[str] = None
    detected_date: Optional[date] = None
    created_at: Optional[datetime] = None
    created_by: Optional[str] = None
    closed_at: Optional[datetime] = None
    closed_by: Optional[str] = None

    # Attachments
    attachments: list[str] = field(default_factory=list)

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.detected_date is None:
            self.detected_date = date.today()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "ncr_number": self.ncr_number,
            "status": self.status.value,
            "severity": self.severity.value,
            "source": self.source.value,
            "title": self.title,
            "description": self.description,
            "part_number": self.part_number,
            "lot_number": self.lot_number,
            "quantity_affected": float(self.quantity_affected),
            "disposition": self.disposition.value if self.disposition else None,
            "root_cause": self.root_cause,
            "capa_id": self.capa_id,
            "capa_required": self.capa_required,
            "estimated_cost": float(self.estimated_cost),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


@dataclass
class CAPA:
    """
    Corrective and Preventive Action.

    Documents actions taken to eliminate causes of
    non-conformances and prevent recurrence.
    """
    id: str
    capa_number: str                    # "CAPA-2024-0001"
    capa_type: CAPAType

    # Classification
    status: CAPAStatus = CAPAStatus.DRAFT
    priority: str = "medium"            # low, medium, high, critical

    # Problem statement
    title: str = ""
    description: str = ""
    problem_statement: str = ""

    # Source NCRs
    ncr_ids: list[str] = field(default_factory=list)

    # Root cause analysis
    root_cause_method: str = ""         # "5 Why", "Fishbone", etc.
    root_cause_analysis: str = ""
    root_causes: list[str] = field(default_factory=list)
    contributing_factors: list[str] = field(default_factory=list)

    # Actions
    immediate_actions: list[dict] = field(default_factory=list)
    corrective_actions: list[dict] = field(default_factory=list)
    preventive_actions: list[dict] = field(default_factory=list)

    # Verification
    verification_method: str = ""
    verification_results: str = ""
    verified_by: Optional[str] = None
    verified_date: Optional[datetime] = None

    # Effectiveness
    effectiveness_criteria: str = ""
    effectiveness_review_date: Optional[date] = None
    effectiveness_result: Optional[str] = None
    recurrence_count: int = 0

    # Impact
    affected_parts: list[str] = field(default_factory=list)
    affected_processes: list[str] = field(default_factory=list)
    affected_documents: list[str] = field(default_factory=list)

    # Linked ECO (if design change needed)
    eco_id: Optional[str] = None

    # Lifecycle
    initiated_by: Optional[str] = None
    initiated_date: Optional[date] = None
    owner_id: Optional[str] = None
    due_date: Optional[date] = None
    closed_date: Optional[datetime] = None
    closed_by: Optional[str] = None

    created_at: Optional[datetime] = None

    # Attachments
    attachments: list[str] = field(default_factory=list)

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.initiated_date is None:
            self.initiated_date = date.today()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "capa_number": self.capa_number,
            "capa_type": self.capa_type.value,
            "status": self.status.value,
            "priority": self.priority,
            "title": self.title,
            "description": self.description,
            "ncr_count": len(self.ncr_ids),
            "root_causes": self.root_causes,
            "action_count": len(self.corrective_actions) + len(self.preventive_actions),
            "owner_id": self.owner_id,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "eco_id": self.eco_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


@dataclass
class InspectionRecord:
    """
    Inspection record for incoming/in-process/final inspection.
    """
    id: str
    inspection_number: str

    # What was inspected
    inspection_type: str = "receiving"  # receiving, in_process, final
    part_id: Optional[str] = None
    part_number: Optional[str] = None
    lot_number: Optional[str] = None
    po_id: Optional[str] = None

    # Quantities
    quantity_inspected: Decimal = Decimal("0")
    quantity_accepted: Decimal = Decimal("0")
    quantity_rejected: Decimal = Decimal("0")
    sample_size: Optional[int] = None

    # Results
    result: str = "pending"             # pending, pass, fail, conditional
    inspection_criteria: list[dict] = field(default_factory=list)
    measurements: list[dict] = field(default_factory=list)
    defects_found: list[dict] = field(default_factory=list)

    # If failed, link to NCR
    ncr_id: Optional[str] = None

    # Inspector
    inspector_id: Optional[str] = None
    inspector_name: Optional[str] = None
    inspection_date: Optional[date] = None
    completed_at: Optional[datetime] = None

    # Attachments (photos, certificates)
    attachments: list[str] = field(default_factory=list)
    certificates: list[str] = field(default_factory=list)

    created_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "inspection_number": self.inspection_number,
            "inspection_type": self.inspection_type,
            "part_number": self.part_number,
            "lot_number": self.lot_number,
            "quantity_inspected": float(self.quantity_inspected),
            "quantity_accepted": float(self.quantity_accepted),
            "quantity_rejected": float(self.quantity_rejected),
            "result": self.result,
            "defect_count": len(self.defects_found),
            "ncr_id": self.ncr_id,
            "inspector_name": self.inspector_name,
            "inspection_date": self.inspection_date.isoformat() if self.inspection_date else None,
        }


@dataclass
class QualityHold:
    """
    Quality hold on parts/materials.

    Prevents use until quality issue is resolved.
    """
    id: str
    hold_number: str

    # What's on hold
    part_id: Optional[str] = None
    part_number: Optional[str] = None
    lot_number: Optional[str] = None
    serial_numbers: list[str] = field(default_factory=list)
    location_id: Optional[str] = None
    quantity: Decimal = Decimal("0")

    # Hold details
    reason: str = ""
    hold_type: str = "pending_inspection"  # pending_inspection, ncr, suspect, recall
    ncr_id: Optional[str] = None

    # Status
    is_active: bool = True
    placed_by: Optional[str] = None
    placed_at: Optional[datetime] = None
    released_by: Optional[str] = None
    released_at: Optional[datetime] = None
    release_notes: Optional[str] = None

    def __post_init__(self):
        if self.placed_at is None:
            self.placed_at = datetime.now()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "hold_number": self.hold_number,
            "part_number": self.part_number,
            "lot_number": self.lot_number,
            "quantity": float(self.quantity),
            "reason": self.reason,
            "hold_type": self.hold_type,
            "is_active": self.is_active,
            "ncr_id": self.ncr_id,
            "placed_by": self.placed_by,
            "placed_at": self.placed_at.isoformat() if self.placed_at else None,
        }
