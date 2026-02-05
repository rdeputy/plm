"""
Project Management Models

Program and project tracking in PLM context.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional


class ProjectStatus(str, Enum):
    """Project status."""
    PROPOSED = "proposed"
    APPROVED = "approved"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ProjectPhase(str, Enum):
    """Development phases."""
    CONCEPT = "concept"
    DESIGN = "design"
    PROTOTYPE = "prototype"
    TESTING = "testing"
    PILOT = "pilot"
    PRODUCTION = "production"
    MAINTENANCE = "maintenance"


class MilestoneStatus(str, Enum):
    """Milestone status."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DELAYED = "delayed"
    AT_RISK = "at_risk"
    CANCELLED = "cancelled"


class DeliverableType(str, Enum):
    """Types of deliverables."""
    DOCUMENT = "document"
    DRAWING = "drawing"
    PART = "part"
    ASSEMBLY = "assembly"
    PROTOTYPE = "prototype"
    TEST_REPORT = "test_report"
    CERTIFICATION = "certification"
    SOFTWARE = "software"
    TOOLING = "tooling"


@dataclass
class Project:
    """
    A project or program in PLM.

    Organizes parts, BOMs, documents, and changes
    under a common project context.
    """
    id: str
    project_number: str             # "PRJ-2024-001"
    name: str

    # Classification
    status: ProjectStatus = ProjectStatus.PROPOSED
    phase: ProjectPhase = ProjectPhase.CONCEPT
    project_type: str = ""          # "new_product", "redesign", "cost_reduction"

    # Description
    description: str = ""
    objectives: str = ""
    scope: str = ""

    # Hierarchy
    program_id: Optional[str] = None        # Parent program
    parent_project_id: Optional[str] = None # Parent project

    # Customer/contract
    customer_id: Optional[str] = None
    customer_name: str = ""
    contract_number: Optional[str] = None

    # Schedule
    start_date: Optional[date] = None
    target_end_date: Optional[date] = None
    actual_end_date: Optional[date] = None

    # Budget
    budget: Decimal = Decimal("0")
    actual_cost: Decimal = Decimal("0")
    currency: str = "USD"

    # Team
    project_manager_id: Optional[str] = None
    project_manager_name: str = ""
    team_members: list[str] = field(default_factory=list)

    # Linked items
    part_ids: list[str] = field(default_factory=list)
    bom_ids: list[str] = field(default_factory=list)
    document_ids: list[str] = field(default_factory=list)
    eco_ids: list[str] = field(default_factory=list)

    # Lifecycle
    created_at: Optional[datetime] = None
    created_by: Optional[str] = None
    approved_by: Optional[str] = None
    approved_date: Optional[datetime] = None

    notes: str = ""
    tags: list[str] = field(default_factory=list)

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

    @property
    def is_on_schedule(self) -> bool:
        if not self.target_end_date:
            return True
        if self.status == ProjectStatus.COMPLETED:
            return self.actual_end_date <= self.target_end_date if self.actual_end_date else True
        return date.today() <= self.target_end_date

    @property
    def budget_variance(self) -> Decimal:
        return self.actual_cost - self.budget

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_number": self.project_number,
            "name": self.name,
            "status": self.status.value,
            "phase": self.phase.value,
            "customer_name": self.customer_name,
            "project_manager_name": self.project_manager_name,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "target_end_date": self.target_end_date.isoformat() if self.target_end_date else None,
            "budget": float(self.budget),
            "actual_cost": float(self.actual_cost),
            "is_on_schedule": self.is_on_schedule,
            "part_count": len(self.part_ids),
        }


@dataclass
class Milestone:
    """
    Project milestone.
    """
    id: str
    project_id: str
    milestone_number: str           # "M1", "PDR", "CDR"
    name: str

    # Status
    status: MilestoneStatus = MilestoneStatus.NOT_STARTED
    phase: Optional[ProjectPhase] = None

    # Description
    description: str = ""
    success_criteria: str = ""

    # Schedule
    planned_date: Optional[date] = None
    forecast_date: Optional[date] = None
    actual_date: Optional[date] = None

    # Sequence
    sequence: int = 0
    predecessor_ids: list[str] = field(default_factory=list)

    # Review
    review_required: bool = False
    review_type: str = ""           # "gate", "design_review", "customer"
    reviewers: list[str] = field(default_factory=list)
    review_notes: str = ""

    # Deliverables
    deliverable_ids: list[str] = field(default_factory=list)

    # Completion
    completed_by: Optional[str] = None
    completion_notes: str = ""

    created_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

    @property
    def days_until_due(self) -> Optional[int]:
        if self.planned_date:
            return (self.planned_date - date.today()).days
        return None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "milestone_number": self.milestone_number,
            "name": self.name,
            "status": self.status.value,
            "planned_date": self.planned_date.isoformat() if self.planned_date else None,
            "actual_date": self.actual_date.isoformat() if self.actual_date else None,
            "days_until_due": self.days_until_due,
            "review_required": self.review_required,
        }


@dataclass
class Deliverable:
    """
    Project deliverable.
    """
    id: str
    project_id: str
    milestone_id: Optional[str] = None
    deliverable_number: str = ""
    name: str = ""

    # Type
    deliverable_type: DeliverableType = DeliverableType.DOCUMENT

    # Description
    description: str = ""
    acceptance_criteria: str = ""

    # Status
    status: MilestoneStatus = MilestoneStatus.NOT_STARTED
    percent_complete: int = 0

    # Schedule
    due_date: Optional[date] = None
    submitted_date: Optional[date] = None
    accepted_date: Optional[date] = None

    # Assignment
    assigned_to: Optional[str] = None
    assigned_name: str = ""

    # Linked PLM items
    part_id: Optional[str] = None
    document_id: Optional[str] = None
    bom_id: Optional[str] = None

    # Approval
    approved_by: Optional[str] = None
    approval_notes: str = ""

    created_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "milestone_id": self.milestone_id,
            "name": self.name,
            "deliverable_type": self.deliverable_type.value,
            "status": self.status.value,
            "percent_complete": self.percent_complete,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "assigned_name": self.assigned_name,
        }


@dataclass
class ProjectDashboard:
    """
    Project status dashboard.
    """
    project_id: str
    project_number: str
    project_name: str

    # Status summary
    status: str = ""
    phase: str = ""
    health: str = "green"           # green, yellow, red

    # Schedule
    days_to_completion: Optional[int] = None
    schedule_variance_days: int = 0
    on_schedule: bool = True

    # Budget
    budget: float = 0.0
    actual_cost: float = 0.0
    budget_variance: float = 0.0
    on_budget: bool = True

    # Milestones
    total_milestones: int = 0
    completed_milestones: int = 0
    overdue_milestones: int = 0
    upcoming_milestone: Optional[dict] = None

    # Deliverables
    total_deliverables: int = 0
    completed_deliverables: int = 0
    overdue_deliverables: int = 0

    # PLM items
    part_count: int = 0
    document_count: int = 0
    open_ecos: int = 0

    generated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "project_id": self.project_id,
            "project_number": self.project_number,
            "project_name": self.project_name,
            "status": self.status,
            "phase": self.phase,
            "health": self.health,
            "schedule": {
                "days_to_completion": self.days_to_completion,
                "variance_days": self.schedule_variance_days,
                "on_schedule": self.on_schedule,
            },
            "budget": {
                "planned": self.budget,
                "actual": self.actual_cost,
                "variance": self.budget_variance,
                "on_budget": self.on_budget,
            },
            "milestones": {
                "total": self.total_milestones,
                "completed": self.completed_milestones,
                "overdue": self.overdue_milestones,
                "upcoming": self.upcoming_milestone,
            },
            "deliverables": {
                "total": self.total_deliverables,
                "completed": self.completed_deliverables,
                "overdue": self.overdue_deliverables,
            },
            "plm_items": {
                "parts": self.part_count,
                "documents": self.document_count,
                "open_ecos": self.open_ecos,
            },
            "generated_at": self.generated_at.isoformat(),
        }
