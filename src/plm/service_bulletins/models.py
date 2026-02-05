"""
Service Bulletin Models

Field service notices and maintenance bulletins.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Optional


class BulletinType(str, Enum):
    """Types of service bulletins."""
    SAFETY = "safety"               # Safety-critical, mandatory
    MANDATORY = "mandatory"         # Required action
    RECOMMENDED = "recommended"     # Recommended action
    OPTIONAL = "optional"           # Optional improvement
    INFORMATIONAL = "informational" # Information only
    RECALL = "recall"               # Product recall


class BulletinStatus(str, Enum):
    """Service bulletin status."""
    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class ComplianceStatus(str, Enum):
    """Compliance status for a specific unit."""
    NOT_APPLICABLE = "not_applicable"
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    WAIVED = "waived"


@dataclass
class ServiceBulletin:
    """
    Service bulletin for field notification.

    Communicates required or recommended actions
    for products in the field.
    """
    id: str
    bulletin_number: str            # "SB-2024-001"

    # Classification
    bulletin_type: BulletinType
    status: BulletinStatus = BulletinStatus.DRAFT

    # Content
    title: str = ""
    summary: str = ""               # Brief description
    description: str = ""           # Full description
    reason: str = ""                # Why this bulletin was issued
    safety_issue: bool = False

    # Instructions
    action_required: str = ""       # What to do
    action_procedure: str = ""      # How to do it
    estimated_time: Optional[str] = None  # "2 hours"
    special_tools: list[str] = field(default_factory=list)
    required_parts: list[str] = field(default_factory=list)

    # Applicability
    affected_parts: list[str] = field(default_factory=list)     # Part IDs
    affected_part_numbers: list[str] = field(default_factory=list)
    serial_range_start: Optional[str] = None
    serial_range_end: Optional[str] = None
    effectivity_start: Optional[date] = None
    effectivity_end: Optional[date] = None
    affected_configurations: list[str] = field(default_factory=list)

    # Compliance
    compliance_deadline: Optional[date] = None
    flight_hours_limit: Optional[int] = None
    cycles_limit: Optional[int] = None

    # Related documents
    related_eco_id: Optional[str] = None
    related_ncr_ids: list[str] = field(default_factory=list)
    supersedes: Optional[str] = None  # Previous bulletin number
    superseded_by: Optional[str] = None

    # Attachments
    attachments: list[str] = field(default_factory=list)

    # Lifecycle
    created_at: Optional[datetime] = None
    created_by: Optional[str] = None
    approved_by: Optional[str] = None
    approved_date: Optional[datetime] = None
    effective_date: Optional[date] = None
    expiry_date: Optional[date] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "bulletin_number": self.bulletin_number,
            "bulletin_type": self.bulletin_type.value,
            "status": self.status.value,
            "title": self.title,
            "summary": self.summary,
            "safety_issue": self.safety_issue,
            "affected_part_numbers": self.affected_part_numbers,
            "compliance_deadline": self.compliance_deadline.isoformat() if self.compliance_deadline else None,
            "effective_date": self.effective_date.isoformat() if self.effective_date else None,
            "supersedes": self.supersedes,
        }


@dataclass
class BulletinCompliance:
    """
    Compliance record for a service bulletin on a specific unit.
    """
    id: str
    bulletin_id: str
    bulletin_number: str

    # Unit identification
    serial_number: str
    part_id: Optional[str] = None
    part_number: Optional[str] = None

    # Compliance status
    status: ComplianceStatus = ComplianceStatus.PENDING

    # Completion details
    completed_date: Optional[date] = None
    completed_by: Optional[str] = None
    work_order_number: Optional[str] = None
    labor_hours: Optional[float] = None

    # Parts used
    parts_used: list[dict] = field(default_factory=list)

    # Waiver (if applicable)
    waived: bool = False
    waiver_reason: Optional[str] = None
    waiver_approved_by: Optional[str] = None
    waiver_expiry: Optional[date] = None

    # Notes
    notes: str = ""
    attachments: list[str] = field(default_factory=list)

    created_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "bulletin_id": self.bulletin_id,
            "bulletin_number": self.bulletin_number,
            "serial_number": self.serial_number,
            "status": self.status.value,
            "completed_date": self.completed_date.isoformat() if self.completed_date else None,
            "waived": self.waived,
        }


@dataclass
class MaintenanceSchedule:
    """
    Scheduled maintenance item for a product.
    """
    id: str
    schedule_code: str              # "100HR", "ANNUAL"

    # What to maintain
    part_id: Optional[str] = None
    part_number: Optional[str] = None
    system: str = ""                # "Engine", "Hydraulics"
    component: str = ""

    # Interval
    interval_type: str = "calendar"  # calendar, hours, cycles
    interval_value: int = 0
    interval_unit: str = ""         # days, hours, cycles

    # Task
    task_description: str = ""
    procedure_reference: Optional[str] = None
    estimated_time: Optional[str] = None

    # Parts needed
    required_parts: list[str] = field(default_factory=list)
    consumables: list[str] = field(default_factory=list)

    is_active: bool = True
    created_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "schedule_code": self.schedule_code,
            "part_number": self.part_number,
            "system": self.system,
            "interval_type": self.interval_type,
            "interval_value": self.interval_value,
            "interval_unit": self.interval_unit,
            "task_description": self.task_description,
            "is_active": self.is_active,
        }


@dataclass
class UnitConfiguration:
    """
    Configuration record for a serialized unit in the field.
    """
    id: str
    serial_number: str
    part_id: str
    part_number: str

    # Current configuration
    current_revision: str = ""
    configuration_id: Optional[str] = None
    build_date: Optional[date] = None
    delivery_date: Optional[date] = None

    # Usage tracking
    total_hours: float = 0.0
    total_cycles: int = 0
    last_updated: Optional[datetime] = None

    # Owner/location
    owner_id: Optional[str] = None
    owner_name: str = ""
    location: str = ""

    # Applied bulletins
    applied_bulletins: list[str] = field(default_factory=list)
    pending_bulletins: list[str] = field(default_factory=list)

    # Maintenance
    last_maintenance_date: Optional[date] = None
    next_maintenance_due: Optional[date] = None

    created_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "serial_number": self.serial_number,
            "part_number": self.part_number,
            "current_revision": self.current_revision,
            "total_hours": self.total_hours,
            "total_cycles": self.total_cycles,
            "owner_name": self.owner_name,
            "applied_bulletins": len(self.applied_bulletins),
            "pending_bulletins": len(self.pending_bulletins),
        }
