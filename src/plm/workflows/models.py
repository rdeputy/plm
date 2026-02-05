"""
Workflow Domain Models

Data structures for the approval workflow engine.

Workflow concepts:
- Definition: Template for a workflow (e.g., "ECO Approval", "Document Review")
- Stage: A step in the workflow requiring action
- Instance: An active workflow for a specific entity
- Task: An individual approval task assigned to a user/role
- Transition: Movement between stages
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional


class WorkflowStatus(str, Enum):
    """Status of a workflow instance."""
    DRAFT = "draft"                 # Not yet started
    ACTIVE = "active"               # In progress
    PENDING_APPROVAL = "pending"    # Waiting for approvers
    APPROVED = "approved"           # All approvals complete
    REJECTED = "rejected"           # Workflow rejected
    CANCELLED = "cancelled"         # Workflow cancelled
    ON_HOLD = "on_hold"             # Temporarily paused
    COMPLETED = "completed"         # Workflow finished successfully


class ApprovalDecision(str, Enum):
    """Approval decision options."""
    PENDING = "pending"             # Not yet decided
    APPROVED = "approved"           # Approved without conditions
    APPROVED_WITH_CONDITIONS = "approved_with_conditions"
    REJECTED = "rejected"           # Rejected
    DELEGATE = "delegate"           # Delegated to another user
    ABSTAIN = "abstain"             # Abstained from voting
    RECALLED = "recalled"           # Submitter recalled


class StageType(str, Enum):
    """Types of workflow stages."""
    APPROVAL = "approval"           # Requires approval decision
    REVIEW = "review"               # Review only (no approval)
    NOTIFICATION = "notification"   # Just notify, auto-advance
    TASK = "task"                   # Generic task completion
    PARALLEL = "parallel"           # Parallel approvals
    CONDITIONAL = "conditional"     # Conditional routing


class ApprovalMode(str, Enum):
    """How multiple approvers are handled."""
    ALL = "all"                     # All must approve
    ANY = "any"                     # Any one can approve
    MAJORITY = "majority"           # Majority must approve
    FIRST = "first"                 # First response wins


@dataclass
class WorkflowStage:
    """
    A stage in a workflow definition.

    Represents a step that requires action before
    the workflow can proceed.
    """
    id: str
    name: str                           # "Engineering Review", "Manager Approval"
    stage_type: StageType = StageType.APPROVAL
    sequence: int = 0                   # Order in workflow

    # Who can approve this stage
    approver_roles: list[str] = field(default_factory=list)  # ["engineer", "manager"]
    approver_users: list[str] = field(default_factory=list)  # Specific user IDs
    approval_mode: ApprovalMode = ApprovalMode.ALL

    # Timing
    due_days: int = 5                   # Days to complete
    escalation_days: int = 3            # Days before escalation
    escalate_to: Optional[str] = None   # Role/user to escalate to

    # Conditions
    skip_condition: Optional[str] = None  # Expression to skip this stage
    required: bool = True

    # Next stages (for branching)
    next_stage_on_approve: Optional[str] = None
    next_stage_on_reject: Optional[str] = None

    # Instructions
    instructions: str = ""
    checklist: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "stage_type": self.stage_type.value,
            "sequence": self.sequence,
            "approver_roles": self.approver_roles,
            "approver_users": self.approver_users,
            "approval_mode": self.approval_mode.value,
            "due_days": self.due_days,
            "required": self.required,
            "instructions": self.instructions,
        }


@dataclass
class WorkflowDefinition:
    """
    A workflow template defining approval stages.

    Can be applied to different entity types (ECO, Document, Part, etc.)
    """
    id: str
    name: str                           # "ECO Approval Workflow"
    description: str = ""
    version: str = "1.0"

    # What this workflow applies to
    entity_types: list[str] = field(default_factory=list)  # ["eco", "document", "part"]

    # Stages
    stages: list[WorkflowStage] = field(default_factory=list)

    # Workflow settings
    allow_parallel_stages: bool = False
    require_all_stages: bool = True
    auto_start: bool = False            # Start when entity created

    # Notifications
    notify_on_start: list[str] = field(default_factory=list)
    notify_on_complete: list[str] = field(default_factory=list)
    notify_on_reject: list[str] = field(default_factory=list)

    # Lifecycle
    is_active: bool = True
    created_at: Optional[datetime] = None
    created_by: Optional[str] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

    def get_stage(self, stage_id: str) -> Optional[WorkflowStage]:
        """Get a stage by ID."""
        for stage in self.stages:
            if stage.id == stage_id:
                return stage
        return None

    def get_first_stage(self) -> Optional[WorkflowStage]:
        """Get the first stage in sequence."""
        if not self.stages:
            return None
        return min(self.stages, key=lambda s: s.sequence)

    def get_next_stage(self, current_stage_id: str) -> Optional[WorkflowStage]:
        """Get the next stage after the current one."""
        current = self.get_stage(current_stage_id)
        if not current:
            return None

        next_stages = [s for s in self.stages if s.sequence > current.sequence]
        if not next_stages:
            return None
        return min(next_stages, key=lambda s: s.sequence)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "entity_types": self.entity_types,
            "stages": [s.to_dict() for s in self.stages],
            "is_active": self.is_active,
        }


@dataclass
class WorkflowTask:
    """
    An individual approval task within a workflow instance.

    Assigned to a specific user for a specific stage.
    """
    id: str
    instance_id: str                    # Parent workflow instance
    stage_id: str
    stage_name: str

    # Assignment
    assignee_id: str                    # User or role ID
    assignee_name: str
    assignee_type: str = "user"         # user, role, group

    # Status
    decision: ApprovalDecision = ApprovalDecision.PENDING
    decision_date: Optional[datetime] = None
    comments: str = ""
    conditions: list[str] = field(default_factory=list)

    # Delegation
    delegated_from: Optional[str] = None
    delegated_to: Optional[str] = None

    # Timing
    created_at: Optional[datetime] = None
    due_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Reminder tracking
    reminders_sent: int = 0
    last_reminder: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

    @property
    def is_complete(self) -> bool:
        return self.decision not in [ApprovalDecision.PENDING]

    @property
    def is_overdue(self) -> bool:
        if not self.due_date or self.is_complete:
            return False
        return datetime.now() > self.due_date

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "instance_id": self.instance_id,
            "stage_id": self.stage_id,
            "stage_name": self.stage_name,
            "assignee_id": self.assignee_id,
            "assignee_name": self.assignee_name,
            "assignee_type": self.assignee_type,
            "decision": self.decision.value,
            "decision_date": self.decision_date.isoformat() if self.decision_date else None,
            "comments": self.comments,
            "conditions": self.conditions,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "is_complete": self.is_complete,
            "is_overdue": self.is_overdue,
        }


@dataclass
class WorkflowTransition:
    """
    A transition event in the workflow history.

    Records all state changes for audit trail.
    """
    id: str
    instance_id: str
    timestamp: datetime

    # From/to states
    from_stage_id: Optional[str] = None
    from_stage_name: Optional[str] = None
    to_stage_id: Optional[str] = None
    to_stage_name: Optional[str] = None

    from_status: Optional[WorkflowStatus] = None
    to_status: Optional[WorkflowStatus] = None

    # Who/what triggered
    triggered_by: str = ""              # User ID
    trigger_type: str = "approval"      # approval, rejection, timeout, manual

    # Details
    task_id: Optional[str] = None
    decision: Optional[ApprovalDecision] = None
    comments: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "instance_id": self.instance_id,
            "timestamp": self.timestamp.isoformat(),
            "from_stage": self.from_stage_name,
            "to_stage": self.to_stage_name,
            "from_status": self.from_status.value if self.from_status else None,
            "to_status": self.to_status.value if self.to_status else None,
            "triggered_by": self.triggered_by,
            "trigger_type": self.trigger_type,
            "decision": self.decision.value if self.decision else None,
            "comments": self.comments,
        }


@dataclass
class WorkflowInstance:
    """
    An active workflow for a specific entity.

    Tracks the current state and history of a workflow
    execution.
    """
    id: str
    definition_id: str
    definition_name: str

    # What entity this workflow is for
    entity_type: str                    # "eco", "document", "part"
    entity_id: str
    entity_number: str                  # Display identifier

    # Current state
    status: WorkflowStatus = WorkflowStatus.DRAFT
    current_stage_id: Optional[str] = None
    current_stage_name: Optional[str] = None

    # Tasks
    tasks: list[WorkflowTask] = field(default_factory=list)

    # History
    transitions: list[WorkflowTransition] = field(default_factory=list)

    # Metadata
    initiated_by: Optional[str] = None
    initiated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Comments/notes
    submission_comments: str = ""
    final_comments: str = ""

    # Context data
    context: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.initiated_at is None:
            self.initiated_at = datetime.now()

    @property
    def pending_tasks(self) -> list[WorkflowTask]:
        """Get all pending tasks."""
        return [t for t in self.tasks if not t.is_complete]

    @property
    def completed_tasks(self) -> list[WorkflowTask]:
        """Get all completed tasks."""
        return [t for t in self.tasks if t.is_complete]

    @property
    def current_stage_tasks(self) -> list[WorkflowTask]:
        """Get tasks for the current stage."""
        if not self.current_stage_id:
            return []
        return [t for t in self.tasks if t.stage_id == self.current_stage_id]

    def add_task(self, task: WorkflowTask) -> None:
        """Add a task to this instance."""
        task.instance_id = self.id
        self.tasks.append(task)

    def add_transition(self, transition: WorkflowTransition) -> None:
        """Add a transition to history."""
        transition.instance_id = self.id
        self.transitions.append(transition)

    def get_task(self, task_id: str) -> Optional[WorkflowTask]:
        """Get a task by ID."""
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "definition_id": self.definition_id,
            "definition_name": self.definition_name,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "entity_number": self.entity_number,
            "status": self.status.value,
            "current_stage_id": self.current_stage_id,
            "current_stage_name": self.current_stage_name,
            "initiated_by": self.initiated_by,
            "initiated_at": self.initiated_at.isoformat() if self.initiated_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "pending_tasks": len(self.pending_tasks),
            "completed_tasks": len(self.completed_tasks),
            "tasks": [t.to_dict() for t in self.tasks],
            "transitions": [tr.to_dict() for tr in self.transitions],
        }


# =============================================================================
# Pre-built Workflow Definitions
# =============================================================================


def create_eco_workflow() -> WorkflowDefinition:
    """Create a standard ECO approval workflow."""
    return WorkflowDefinition(
        id="wf-eco-standard",
        name="Standard ECO Approval",
        description="Multi-stage approval for Engineering Change Orders",
        entity_types=["eco", "change_order"],
        stages=[
            WorkflowStage(
                id="stage-submit",
                name="Submission Review",
                stage_type=StageType.REVIEW,
                sequence=10,
                approver_roles=["document_control"],
                approval_mode=ApprovalMode.ANY,
                due_days=2,
                instructions="Verify ECO completeness and proper documentation",
            ),
            WorkflowStage(
                id="stage-engineering",
                name="Engineering Review",
                stage_type=StageType.APPROVAL,
                sequence=20,
                approver_roles=["engineer", "engineering_manager"],
                approval_mode=ApprovalMode.ALL,
                due_days=5,
                instructions="Review technical merit and impact analysis",
                checklist=[
                    "Technical feasibility verified",
                    "Impact analysis complete",
                    "Test plan defined",
                ],
            ),
            WorkflowStage(
                id="stage-quality",
                name="Quality Review",
                stage_type=StageType.APPROVAL,
                sequence=30,
                approver_roles=["quality_engineer"],
                approval_mode=ApprovalMode.ANY,
                due_days=3,
                instructions="Review quality and compliance implications",
            ),
            WorkflowStage(
                id="stage-final",
                name="Final Approval",
                stage_type=StageType.APPROVAL,
                sequence=40,
                approver_roles=["engineering_director", "program_manager"],
                approval_mode=ApprovalMode.ANY,
                due_days=3,
                instructions="Final approval for implementation",
            ),
        ],
    )


def create_document_review_workflow() -> WorkflowDefinition:
    """Create a document review/release workflow."""
    return WorkflowDefinition(
        id="wf-doc-review",
        name="Document Review",
        description="Review and release workflow for controlled documents",
        entity_types=["document"],
        stages=[
            WorkflowStage(
                id="stage-peer-review",
                name="Peer Review",
                stage_type=StageType.REVIEW,
                sequence=10,
                approver_roles=["engineer"],
                approval_mode=ApprovalMode.ANY,
                due_days=3,
                instructions="Review document for accuracy and completeness",
            ),
            WorkflowStage(
                id="stage-approval",
                name="Manager Approval",
                stage_type=StageType.APPROVAL,
                sequence=20,
                approver_roles=["manager"],
                approval_mode=ApprovalMode.ANY,
                due_days=2,
                instructions="Approve document for release",
            ),
        ],
    )


def create_part_release_workflow() -> WorkflowDefinition:
    """Create a part release workflow."""
    return WorkflowDefinition(
        id="wf-part-release",
        name="Part Release",
        description="Workflow for releasing new or revised parts",
        entity_types=["part"],
        stages=[
            WorkflowStage(
                id="stage-design-review",
                name="Design Review",
                stage_type=StageType.APPROVAL,
                sequence=10,
                approver_roles=["design_engineer", "engineering_manager"],
                approval_mode=ApprovalMode.ALL,
                due_days=5,
                instructions="Review part design and specifications",
            ),
            WorkflowStage(
                id="stage-release",
                name="Release Approval",
                stage_type=StageType.APPROVAL,
                sequence=20,
                approver_roles=["document_control"],
                approval_mode=ApprovalMode.ANY,
                due_days=2,
                instructions="Final release to production",
            ),
        ],
    )
