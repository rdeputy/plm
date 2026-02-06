"""
Projects Service

Business logic for project management.
"""

from typing import Optional
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy.orm import Session

from plm.projects.repository import (
    ProjectRepository,
    MilestoneRepository,
    DeliverableRepository,
)
from plm.db.models import (
    ProjectModel,
    MilestoneModel,
    DeliverableModel,
)


@dataclass
class ProjectStats:
    """Statistics for projects."""

    total: int
    by_status: dict[str, int]
    by_phase: dict[str, int]
    active: int
    overdue: int
    total_budget: float
    total_actual: float


@dataclass
class ProjectProgress:
    """Progress summary for a project."""

    project_id: str
    project_number: str
    name: str
    phase: str
    milestones_total: int
    milestones_completed: int
    deliverables_total: int
    deliverables_completed: int
    overall_percent: float
    days_remaining: Optional[int]
    is_overdue: bool


class ProjectService:
    """Service for project management."""

    def __init__(self, session: Session):
        self.session = session
        self.projects = ProjectRepository(session)
        self.milestones = MilestoneRepository(session)
        self.deliverables = DeliverableRepository(session)

    def create_project(
        self,
        project_number: str,
        name: str,
        project_type: str = "",
        description: str = "",
        customer_id: Optional[str] = None,
        customer_name: str = "",
        start_date: Optional[date] = None,
        target_end_date: Optional[date] = None,
        budget: float = 0,
        currency: str = "USD",
        project_manager_id: Optional[str] = None,
        project_manager_name: str = "",
        created_by: Optional[str] = None,
    ) -> ProjectModel:
        """Create a new project."""
        return self.projects.create(
            project_number=project_number,
            name=name,
            project_type=project_type,
            description=description,
            customer_id=customer_id,
            customer_name=customer_name,
            start_date=start_date,
            target_end_date=target_end_date,
            budget=budget,
            currency=currency,
            project_manager_id=project_manager_id,
            project_manager_name=project_manager_name,
            status="proposed",
            phase="concept",
            created_by=created_by,
        )

    def get_project(self, project_id: str) -> Optional[ProjectModel]:
        """Get project by ID."""
        return self.projects.get(project_id)

    def get_project_by_number(self, project_number: str) -> Optional[ProjectModel]:
        """Get project by number."""
        return self.projects.find_by_number(project_number)

    def activate_project(self, project_id: str) -> Optional[ProjectModel]:
        """Activate a project."""
        return self.projects.update(
            project_id,
            status="active",
            start_date=date.today(),
        )

    def advance_phase(
        self,
        project_id: str,
        new_phase: str,
    ) -> Optional[ProjectModel]:
        """Advance project to next phase."""
        return self.projects.update(project_id, phase=new_phase)

    def complete_project(
        self,
        project_id: str,
        actual_cost: Optional[float] = None,
    ) -> Optional[ProjectModel]:
        """Mark project as completed."""
        data = {
            "status": "completed",
            "actual_end_date": date.today(),
        }
        if actual_cost is not None:
            data["actual_cost"] = actual_cost
        return self.projects.update(project_id, **data)

    def list_active_projects(self) -> list[ProjectModel]:
        """List active projects."""
        return self.projects.list_active()

    def list_overdue_projects(self) -> list[ProjectModel]:
        """List overdue projects."""
        return self.projects.list_overdue()

    def create_milestone(
        self,
        project_id: str,
        milestone_number: str,
        name: str,
        phase: Optional[str] = None,
        description: str = "",
        planned_date: Optional[date] = None,
        sequence: int = 0,
        review_required: bool = False,
        review_type: str = "",
    ) -> MilestoneModel:
        """Create a project milestone."""
        return self.milestones.create(
            project_id=project_id,
            milestone_number=milestone_number,
            name=name,
            phase=phase,
            description=description,
            planned_date=planned_date,
            sequence=sequence,
            review_required=review_required,
            review_type=review_type,
            status="not_started",
        )

    def get_milestone(self, milestone_id: str) -> Optional[MilestoneModel]:
        """Get milestone by ID."""
        return self.milestones.get(milestone_id)

    def start_milestone(self, milestone_id: str) -> Optional[MilestoneModel]:
        """Start a milestone."""
        return self.milestones.update(milestone_id, status="in_progress")

    def complete_milestone(
        self,
        milestone_id: str,
        completed_by: str,
        completion_notes: Optional[str] = None,
    ) -> Optional[MilestoneModel]:
        """Complete a milestone."""
        return self.milestones.complete_milestone(
            milestone_id, completed_by, completion_notes
        )

    def list_project_milestones(
        self,
        project_id: str,
        status: Optional[str] = None,
    ) -> list[MilestoneModel]:
        """List milestones for a project."""
        return self.milestones.list_for_project(project_id, status)

    def list_upcoming_milestones(self, days: int = 30) -> list[MilestoneModel]:
        """List upcoming milestones."""
        return self.milestones.list_upcoming(days)

    def list_overdue_milestones(self) -> list[MilestoneModel]:
        """List overdue milestones."""
        return self.milestones.list_overdue()

    def create_deliverable(
        self,
        project_id: str,
        name: str,
        deliverable_type: str = "document",
        description: str = "",
        due_date: Optional[date] = None,
        milestone_id: Optional[str] = None,
        assigned_to: Optional[str] = None,
        assigned_name: str = "",
    ) -> DeliverableModel:
        """Create a project deliverable."""
        return self.deliverables.create(
            project_id=project_id,
            milestone_id=milestone_id,
            name=name,
            deliverable_type=deliverable_type,
            description=description,
            due_date=due_date,
            assigned_to=assigned_to,
            assigned_name=assigned_name,
            status="not_started",
            percent_complete=0,
        )

    def get_deliverable(self, deliverable_id: str) -> Optional[DeliverableModel]:
        """Get deliverable by ID."""
        return self.deliverables.get(deliverable_id)

    def update_deliverable_progress(
        self,
        deliverable_id: str,
        percent_complete: int,
    ) -> Optional[DeliverableModel]:
        """Update deliverable progress."""
        return self.deliverables.update_progress(deliverable_id, percent_complete)

    def submit_deliverable(
        self,
        deliverable_id: str,
    ) -> Optional[DeliverableModel]:
        """Submit deliverable for approval."""
        return self.deliverables.submit_deliverable(deliverable_id)

    def accept_deliverable(
        self,
        deliverable_id: str,
        approved_by: str,
        approval_notes: Optional[str] = None,
    ) -> Optional[DeliverableModel]:
        """Accept a submitted deliverable."""
        return self.deliverables.accept_deliverable(
            deliverable_id, approved_by, approval_notes
        )

    def list_project_deliverables(
        self,
        project_id: str,
        status: Optional[str] = None,
    ) -> list[DeliverableModel]:
        """List deliverables for a project."""
        return self.deliverables.list_for_project(project_id, status)

    def list_my_deliverables(
        self,
        assigned_to: str,
        status: Optional[str] = None,
    ) -> list[DeliverableModel]:
        """List deliverables assigned to someone."""
        return self.deliverables.list_assigned_to(assigned_to, status)

    def list_overdue_deliverables(self) -> list[DeliverableModel]:
        """List overdue deliverables."""
        return self.deliverables.list_overdue()

    def get_project_progress(self, project_id: str) -> Optional[ProjectProgress]:
        """Get progress summary for a project."""
        project = self.projects.get(project_id)
        if not project:
            return None

        milestones = self.milestones.list_for_project(project_id)
        deliverables = self.deliverables.list_for_project(project_id)

        milestones_completed = sum(
            1 for m in milestones
            if str(m.status.value if hasattr(m.status, "value") else m.status) == "completed"
        )

        deliverables_completed = sum(
            1 for d in deliverables
            if str(d.status.value if hasattr(d.status, "value") else d.status) == "completed"
        )

        total_items = len(milestones) + len(deliverables)
        completed_items = milestones_completed + deliverables_completed
        overall_percent = (completed_items / total_items * 100) if total_items > 0 else 0

        days_remaining = None
        is_overdue = False
        if project.target_end_date:
            delta = project.target_end_date - date.today()
            days_remaining = delta.days
            is_overdue = days_remaining < 0 and str(project.status.value if hasattr(project.status, "value") else project.status) == "active"

        return ProjectProgress(
            project_id=project_id,
            project_number=project.project_number,
            name=project.name,
            phase=str(project.phase.value if hasattr(project.phase, "value") else project.phase),
            milestones_total=len(milestones),
            milestones_completed=milestones_completed,
            deliverables_total=len(deliverables),
            deliverables_completed=deliverables_completed,
            overall_percent=overall_percent,
            days_remaining=days_remaining,
            is_overdue=is_overdue,
        )

    def get_stats(self) -> ProjectStats:
        """Get overall project statistics."""
        all_projects = self.projects.list(limit=10000)
        active = self.projects.list_active()
        overdue = self.projects.list_overdue()

        by_status: dict[str, int] = {}
        by_phase: dict[str, int] = {}
        total_budget = 0.0
        total_actual = 0.0

        for p in all_projects:
            status = str(p.status.value if hasattr(p.status, "value") else p.status)
            phase = str(p.phase.value if hasattr(p.phase, "value") else p.phase)

            by_status[status] = by_status.get(status, 0) + 1
            by_phase[phase] = by_phase.get(phase, 0) + 1

            total_budget += float(p.budget or 0)
            total_actual += float(p.actual_cost or 0)

        return ProjectStats(
            total=len(all_projects),
            by_status=by_status,
            by_phase=by_phase,
            active=len(active),
            overdue=len(overdue),
            total_budget=total_budget,
            total_actual=total_actual,
        )

    def commit(self):
        """Commit transaction."""
        self.session.commit()
