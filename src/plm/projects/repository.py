"""
Projects Repository

Database operations for projects, milestones, and deliverables.
"""

from typing import Optional
from datetime import date

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from plm.db.repository import BaseRepository
from plm.db.models import (
    ProjectModel,
    MilestoneModel,
    DeliverableModel,
)


class ProjectRepository(BaseRepository[ProjectModel]):
    """Repository for projects."""

    def __init__(self, session: Session):
        super().__init__(session, ProjectModel)

    def find_by_number(self, project_number: str) -> Optional[ProjectModel]:
        """Find project by number."""
        return self.get_by(project_number=project_number)

    def list_by_status(self, status: str) -> list[ProjectModel]:
        """List projects by status."""
        return self.list(status=status, order_by="project_number")

    def list_by_phase(self, phase: str) -> list[ProjectModel]:
        """List projects by phase."""
        return self.list(phase=phase, order_by="project_number")

    def list_for_customer(self, customer_id: str) -> list[ProjectModel]:
        """List projects for a customer."""
        return self.list(customer_id=customer_id, order_by="project_number")

    def list_for_manager(self, manager_id: str) -> list[ProjectModel]:
        """List projects for a project manager."""
        return self.list(project_manager_id=manager_id, order_by="project_number")

    def list_active(self) -> list[ProjectModel]:
        """List active projects."""
        return self.list(status="active", order_by="project_number")

    def list_overdue(self) -> list[ProjectModel]:
        """List projects past target end date."""
        stmt = select(self.model_class).filter(
            ProjectModel.status == "active",
            ProjectModel.target_end_date.isnot(None),
            ProjectModel.target_end_date < date.today(),
        ).order_by(ProjectModel.target_end_date)
        return list(self.session.execute(stmt).scalars().all())

    def search_projects(
        self,
        search: str,
        status: Optional[str] = None,
        phase: Optional[str] = None,
    ) -> list[ProjectModel]:
        """Search projects."""
        return self.search(
            search,
            ["project_number", "name", "description", "customer_name"],
            status=status,
            phase=phase,
        )


class MilestoneRepository(BaseRepository[MilestoneModel]):
    """Repository for project milestones."""

    def __init__(self, session: Session):
        super().__init__(session, MilestoneModel)

    def list_for_project(
        self,
        project_id: str,
        status: Optional[str] = None,
    ) -> list[MilestoneModel]:
        """List milestones for a project."""
        return self.list(
            project_id=project_id,
            status=status,
            order_by="sequence",
        )

    def list_by_status(self, status: str) -> list[MilestoneModel]:
        """List milestones by status."""
        return self.list(status=status)

    def list_upcoming(self, days: int = 30) -> list[MilestoneModel]:
        """List milestones with planned date approaching."""
        from datetime import timedelta

        cutoff = date.today() + timedelta(days=days)
        stmt = select(self.model_class).filter(
            MilestoneModel.status.in_(["not_started", "in_progress"]),
            MilestoneModel.planned_date.isnot(None),
            MilestoneModel.planned_date <= cutoff,
        ).order_by(MilestoneModel.planned_date)
        return list(self.session.execute(stmt).scalars().all())

    def list_overdue(self) -> list[MilestoneModel]:
        """List overdue milestones."""
        stmt = select(self.model_class).filter(
            MilestoneModel.status.in_(["not_started", "in_progress"]),
            MilestoneModel.planned_date.isnot(None),
            MilestoneModel.planned_date < date.today(),
        ).order_by(MilestoneModel.planned_date)
        return list(self.session.execute(stmt).scalars().all())

    def list_requiring_review(self) -> list[MilestoneModel]:
        """List milestones requiring review."""
        return self.list(review_required=True, status="in_progress")

    def complete_milestone(
        self,
        milestone_id: str,
        completed_by: str,
        completion_notes: Optional[str] = None,
    ) -> Optional[MilestoneModel]:
        """Mark milestone as completed."""
        return self.update(
            milestone_id,
            status="completed",
            actual_date=date.today(),
            completed_by=completed_by,
            completion_notes=completion_notes or "",
        )


class DeliverableRepository(BaseRepository[DeliverableModel]):
    """Repository for project deliverables."""

    def __init__(self, session: Session):
        super().__init__(session, DeliverableModel)

    def list_for_project(
        self,
        project_id: str,
        status: Optional[str] = None,
    ) -> list[DeliverableModel]:
        """List deliverables for a project."""
        return self.list(project_id=project_id, status=status)

    def list_for_milestone(self, milestone_id: str) -> list[DeliverableModel]:
        """List deliverables for a milestone."""
        return self.list(milestone_id=milestone_id)

    def list_by_type(
        self,
        project_id: str,
        deliverable_type: str,
    ) -> list[DeliverableModel]:
        """List deliverables by type."""
        return self.list(project_id=project_id, deliverable_type=deliverable_type)

    def list_assigned_to(
        self,
        assigned_to: str,
        status: Optional[str] = None,
    ) -> list[DeliverableModel]:
        """List deliverables assigned to a person."""
        return self.list(assigned_to=assigned_to, status=status)

    def list_due_soon(self, days: int = 14) -> list[DeliverableModel]:
        """List deliverables due soon."""
        from datetime import timedelta

        cutoff = date.today() + timedelta(days=days)
        stmt = select(self.model_class).filter(
            DeliverableModel.status.in_(["not_started", "in_progress"]),
            DeliverableModel.due_date.isnot(None),
            DeliverableModel.due_date <= cutoff,
        ).order_by(DeliverableModel.due_date)
        return list(self.session.execute(stmt).scalars().all())

    def list_overdue(self) -> list[DeliverableModel]:
        """List overdue deliverables."""
        stmt = select(self.model_class).filter(
            DeliverableModel.status.in_(["not_started", "in_progress"]),
            DeliverableModel.due_date.isnot(None),
            DeliverableModel.due_date < date.today(),
        ).order_by(DeliverableModel.due_date)
        return list(self.session.execute(stmt).scalars().all())

    def update_progress(
        self,
        deliverable_id: str,
        percent_complete: int,
    ) -> Optional[DeliverableModel]:
        """Update deliverable progress."""
        status = "completed" if percent_complete >= 100 else "in_progress"
        return self.update(
            deliverable_id,
            percent_complete=min(percent_complete, 100),
            status=status,
        )

    def submit_deliverable(
        self,
        deliverable_id: str,
    ) -> Optional[DeliverableModel]:
        """Submit deliverable for review."""
        return self.update(
            deliverable_id,
            status="in_progress",
            percent_complete=100,
            submitted_date=date.today(),
        )

    def accept_deliverable(
        self,
        deliverable_id: str,
        approved_by: str,
        approval_notes: Optional[str] = None,
    ) -> Optional[DeliverableModel]:
        """Accept deliverable."""
        return self.update(
            deliverable_id,
            status="completed",
            accepted_date=date.today(),
            approved_by=approved_by,
            approval_notes=approval_notes or "",
        )

    def get_project_progress(self, project_id: str) -> dict:
        """Calculate overall project deliverable progress."""
        stmt = select(
            func.count(DeliverableModel.id).label("total"),
            func.sum(DeliverableModel.percent_complete).label("sum_percent"),
        ).filter(DeliverableModel.project_id == project_id)

        result = self.session.execute(stmt).first()
        total = result.total if result else 0
        sum_percent = result.sum_percent if result else 0

        return {
            "total_deliverables": total,
            "average_progress": (sum_percent / total) if total > 0 else 0,
        }
