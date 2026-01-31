"""
Change Management Models

Engineering Change Order (ECO) definitions for PLM.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional


class ChangeReason(str, Enum):
    """Reasons for engineering changes."""
    CUSTOMER_REQUEST = "customer_request"
    COST_REDUCTION = "cost_reduction"
    QUALITY_IMPROVEMENT = "quality_improvement"
    REGULATORY_COMPLIANCE = "regulatory_compliance"
    ERROR_CORRECTION = "error_correction"
    SUPPLIER_CHANGE = "supplier_change"
    VALUE_ENGINEERING = "value_engineering"
    FIELD_CONDITION = "field_condition"
    SAFETY = "safety"


class ChangeUrgency(str, Enum):
    """Urgency of a change."""
    EMERGENCY = "emergency"       # Stop work, implement now
    URGENT = "urgent"             # Implement within days
    STANDARD = "standard"         # Normal review cycle
    CONVENIENCE = "convenience"   # When practical


class ECOStatus(str, Enum):
    """Engineering Change Order status."""
    DRAFT = "draft"
    SUBMITTED = "submitted"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    IMPLEMENTED = "implemented"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class ChangeType(str, Enum):
    """Type of change being made."""
    ADD = "add"
    REMOVE = "remove"
    MODIFY = "modify"
    REPLACE = "replace"


@dataclass
class Change:
    """
    A specific change within an ECO.
    """
    id: str
    eco_id: str

    # What's changing
    change_type: ChangeType
    entity_type: str              # "part", "bom_item", "document"
    entity_id: str

    # Before/after
    field_name: Optional[str] = None     # For modifications
    old_value: Optional[str] = None
    new_value: Optional[str] = None

    # For replacements
    replaced_by_id: Optional[str] = None

    # Notes
    justification: str = ""
    notes: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "eco_id": self.eco_id,
            "change_type": self.change_type.value,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "field_name": self.field_name,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "replaced_by_id": self.replaced_by_id,
            "justification": self.justification,
        }


@dataclass
class Approval:
    """
    An approval decision on an ECO.
    """
    id: str
    eco_id: str

    # Approver
    approver_id: str
    approver_name: str
    approver_role: str            # "ARC Committee", "Owner", "PM"

    # Decision
    decision: str                 # "approved", "rejected", "approved_with_conditions"
    conditions: Optional[str] = None
    comments: Optional[str] = None

    # Timestamp
    decided_at: Optional[datetime] = None

    # Signature
    signature_file: Optional[str] = None

    def __post_init__(self):
        if self.decided_at is None:
            self.decided_at = datetime.now()

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "eco_id": self.eco_id,
            "approver_id": self.approver_id,
            "approver_name": self.approver_name,
            "approver_role": self.approver_role,
            "decision": self.decision,
            "conditions": self.conditions,
            "comments": self.comments,
            "decided_at": self.decided_at.isoformat() if self.decided_at else None,
        }


@dataclass
class ImpactAnalysis:
    """
    Analysis of change impact across systems.
    """
    id: str
    eco_id: str
    analyzed_at: Optional[datetime] = None
    analyzed_by: Optional[str] = None

    # Cost impact
    material_cost_delta: Decimal = Decimal("0")
    labor_cost_delta: Decimal = Decimal("0")
    total_cost_delta: Decimal = Decimal("0")

    # Schedule impact
    schedule_delta_days: int = 0
    critical_path_affected: bool = False

    # Compliance impact
    arc_resubmission_required: bool = False
    permit_revision_required: bool = False
    variance_required: bool = False
    compliance_notes: str = ""

    # Downstream impact
    affected_purchase_orders: list[str] = field(default_factory=list)
    affected_work_orders: list[str] = field(default_factory=list)
    affected_inspections: list[str] = field(default_factory=list)

    # Risk assessment
    risk_level: str = "low"       # "low", "medium", "high"
    risk_notes: str = ""

    # Recommendations
    recommendations: list[str] = field(default_factory=list)

    def __post_init__(self):
        if self.analyzed_at is None:
            self.analyzed_at = datetime.now()
        # Calculate total
        self.total_cost_delta = self.material_cost_delta + self.labor_cost_delta

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "eco_id": self.eco_id,
            "analyzed_at": self.analyzed_at.isoformat() if self.analyzed_at else None,
            "analyzed_by": self.analyzed_by,
            "material_cost_delta": float(self.material_cost_delta),
            "labor_cost_delta": float(self.labor_cost_delta),
            "total_cost_delta": float(self.total_cost_delta),
            "schedule_delta_days": self.schedule_delta_days,
            "critical_path_affected": self.critical_path_affected,
            "arc_resubmission_required": self.arc_resubmission_required,
            "permit_revision_required": self.permit_revision_required,
            "variance_required": self.variance_required,
            "risk_level": self.risk_level,
            "recommendations": self.recommendations,
        }


@dataclass
class ChangeOrder:
    """
    Engineering Change Order (ECO).

    Formal request to modify design, tracked through approval workflow.
    """
    id: str
    eco_number: str               # "ECO-2024-0042"
    title: str
    description: str = ""

    # Classification
    reason: ChangeReason = ChangeReason.CUSTOMER_REQUEST
    urgency: ChangeUrgency = ChangeUrgency.STANDARD

    # Scope
    project_id: Optional[str] = None
    submission_id: Optional[str] = None  # ARC submission if applicable

    # What's changing
    affected_parts: list[str] = field(default_factory=list)     # Part IDs
    affected_boms: list[str] = field(default_factory=list)      # BOM IDs
    affected_documents: list[str] = field(default_factory=list) # Document IDs

    # Proposed changes
    changes: list[Change] = field(default_factory=list)

    # Analysis
    impact_analysis: Optional[ImpactAnalysis] = None

    # Workflow
    status: ECOStatus = ECOStatus.DRAFT
    submitted_by: Optional[str] = None
    submitted_at: Optional[datetime] = None

    # Approvals
    required_approvals: list[str] = field(default_factory=list)  # Role or person IDs
    approvals: list[Approval] = field(default_factory=list)

    # Implementation
    implementation_date: Optional[date] = None
    implemented_by: Optional[str] = None
    implementation_notes: Optional[str] = None

    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()

    @property
    def is_approved(self) -> bool:
        """Check if all required approvals received."""
        if not self.required_approvals:
            return False
        approved_by = {a.approver_role for a in self.approvals if a.decision == "approved"}
        return all(role in approved_by for role in self.required_approvals)

    @property
    def can_implement(self) -> bool:
        """Check if ECO can be implemented."""
        return self.status == ECOStatus.APPROVED and self.is_approved

    def add_change(self, change: Change) -> None:
        """Add a change to the ECO."""
        change.eco_id = self.id
        self.changes.append(change)
        self.updated_at = datetime.now()

    def add_approval(self, approval: Approval) -> None:
        """Add an approval decision."""
        approval.eco_id = self.id
        self.approvals.append(approval)
        self.updated_at = datetime.now()

        # Check if all approvals received
        if self.is_approved and self.status == ECOStatus.IN_REVIEW:
            self.status = ECOStatus.APPROVED

    def submit(self, submitter: str) -> None:
        """Submit the ECO for review."""
        if self.status != ECOStatus.DRAFT:
            raise ValueError(f"Cannot submit ECO in status {self.status}")
        self.status = ECOStatus.SUBMITTED
        self.submitted_by = submitter
        self.submitted_at = datetime.now()
        self.updated_at = datetime.now()

    def start_review(self) -> None:
        """Move ECO to in-review status."""
        if self.status != ECOStatus.SUBMITTED:
            raise ValueError(f"Cannot start review for ECO in status {self.status}")
        self.status = ECOStatus.IN_REVIEW
        self.updated_at = datetime.now()

    def implement(self, implementer: str, notes: str = None) -> None:
        """Mark ECO as implemented."""
        if not self.can_implement:
            raise ValueError("ECO cannot be implemented - not approved or missing approvals")
        self.status = ECOStatus.IMPLEMENTED
        self.implemented_by = implementer
        self.implementation_date = date.today()
        self.implementation_notes = notes
        self.updated_at = datetime.now()

    def close(self) -> None:
        """Close the ECO."""
        if self.status != ECOStatus.IMPLEMENTED:
            raise ValueError(f"Cannot close ECO in status {self.status}")
        self.status = ECOStatus.CLOSED
        self.closed_at = datetime.now()
        self.updated_at = datetime.now()

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "eco_number": self.eco_number,
            "title": self.title,
            "description": self.description,
            "reason": self.reason.value,
            "urgency": self.urgency.value,
            "project_id": self.project_id,
            "status": self.status.value,
            "affected_parts": self.affected_parts,
            "affected_boms": self.affected_boms,
            "changes": [c.to_dict() for c in self.changes],
            "approvals": [a.to_dict() for a in self.approvals],
            "impact_analysis": self.impact_analysis.to_dict() if self.impact_analysis else None,
            "is_approved": self.is_approved,
            "can_implement": self.can_implement,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "implementation_date": self.implementation_date.isoformat() if self.implementation_date else None,
        }
