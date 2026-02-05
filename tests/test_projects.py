"""
Tests for Projects Module

Tests Project, Milestone, Deliverable, and related models.
"""

import pytest
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from plm.projects.models import (
    Project,
    Milestone,
    Deliverable,
    ProjectDashboard,
    ProjectStatus,
    ProjectPhase,
    MilestoneStatus,
    DeliverableType,
)


class TestProjectModel:
    """Tests for Project dataclass model."""

    def test_create_project(self):
        """Test creating a project."""
        project = Project(
            id=str(uuid4()),
            project_number="PRJ-2024-001",
            name="New Widget Development",
            status=ProjectStatus.ACTIVE,
            phase=ProjectPhase.DESIGN,
            budget=Decimal("500000.00"),
        )
        assert project.project_number == "PRJ-2024-001"
        assert project.status == ProjectStatus.ACTIVE
        assert project.phase == ProjectPhase.DESIGN
        assert project.created_at is not None

    def test_project_is_on_schedule_no_target(self):
        """Test is_on_schedule when no target date."""
        project = Project(
            id=str(uuid4()),
            project_number="PRJ-001",
            name="Test Project",
        )
        assert project.is_on_schedule is True

    def test_project_is_on_schedule_active(self):
        """Test is_on_schedule for active project."""
        future_date = date.today() + timedelta(days=30)
        project = Project(
            id=str(uuid4()),
            project_number="PRJ-001",
            name="Test Project",
            status=ProjectStatus.ACTIVE,
            target_end_date=future_date,
        )
        assert project.is_on_schedule is True

    def test_project_is_behind_schedule(self):
        """Test is_on_schedule when behind."""
        past_date = date.today() - timedelta(days=30)
        project = Project(
            id=str(uuid4()),
            project_number="PRJ-001",
            name="Test Project",
            status=ProjectStatus.ACTIVE,
            target_end_date=past_date,
        )
        assert project.is_on_schedule is False

    def test_project_budget_variance(self):
        """Test budget variance calculation."""
        project = Project(
            id=str(uuid4()),
            project_number="PRJ-001",
            name="Test Project",
            budget=Decimal("100000.00"),
            actual_cost=Decimal("110000.00"),
        )
        assert project.budget_variance == Decimal("10000.00")

    def test_project_to_dict(self):
        """Test converting project to dictionary."""
        project = Project(
            id="prj-001",
            project_number="PRJ-2024-001",
            name="Widget Project",
            status=ProjectStatus.ACTIVE,
            phase=ProjectPhase.PROTOTYPE,
            customer_name="Acme Corp",
            project_manager_name="John Smith",
            budget=Decimal("500000.00"),
            actual_cost=Decimal("250000.00"),
            part_ids=["p1", "p2", "p3"],
        )
        data = project.to_dict()
        assert data["project_number"] == "PRJ-2024-001"
        assert data["status"] == "active"
        assert data["phase"] == "prototype"
        assert data["budget"] == 500000.00
        assert data["part_count"] == 3

    def test_project_status_enums(self):
        """Test project status enums."""
        assert ProjectStatus.PROPOSED.value == "proposed"
        assert ProjectStatus.APPROVED.value == "approved"
        assert ProjectStatus.ACTIVE.value == "active"
        assert ProjectStatus.ON_HOLD.value == "on_hold"
        assert ProjectStatus.COMPLETED.value == "completed"
        assert ProjectStatus.CANCELLED.value == "cancelled"

    def test_project_phase_enums(self):
        """Test project phase enums."""
        assert ProjectPhase.CONCEPT.value == "concept"
        assert ProjectPhase.DESIGN.value == "design"
        assert ProjectPhase.PROTOTYPE.value == "prototype"
        assert ProjectPhase.TESTING.value == "testing"
        assert ProjectPhase.PRODUCTION.value == "production"


class TestMilestoneModel:
    """Tests for Milestone dataclass model."""

    def test_create_milestone(self):
        """Test creating a milestone."""
        milestone = Milestone(
            id=str(uuid4()),
            project_id="prj-001",
            milestone_number="M1",
            name="Preliminary Design Review",
            status=MilestoneStatus.NOT_STARTED,
            phase=ProjectPhase.DESIGN,
            planned_date=date.today() + timedelta(days=30),
        )
        assert milestone.milestone_number == "M1"
        assert milestone.status == MilestoneStatus.NOT_STARTED

    def test_milestone_days_until_due(self):
        """Test days_until_due calculation."""
        future_date = date.today() + timedelta(days=15)
        milestone = Milestone(
            id=str(uuid4()),
            project_id="prj-001",
            milestone_number="M1",
            name="PDR",
            planned_date=future_date,
        )
        assert milestone.days_until_due == 15

    def test_milestone_days_until_due_none(self):
        """Test days_until_due when no planned date."""
        milestone = Milestone(
            id=str(uuid4()),
            project_id="prj-001",
            milestone_number="M1",
            name="PDR",
        )
        assert milestone.days_until_due is None

    def test_milestone_to_dict(self):
        """Test converting milestone to dictionary."""
        milestone = Milestone(
            id="ms-001",
            project_id="prj-001",
            milestone_number="PDR",
            name="Preliminary Design Review",
            status=MilestoneStatus.COMPLETED,
            planned_date=date(2024, 6, 1),
            actual_date=date(2024, 5, 28),
            review_required=True,
        )
        data = milestone.to_dict()
        assert data["milestone_number"] == "PDR"
        assert data["status"] == "completed"
        assert data["review_required"] is True

    def test_milestone_status_enums(self):
        """Test milestone status enums."""
        assert MilestoneStatus.NOT_STARTED.value == "not_started"
        assert MilestoneStatus.IN_PROGRESS.value == "in_progress"
        assert MilestoneStatus.COMPLETED.value == "completed"
        assert MilestoneStatus.DELAYED.value == "delayed"
        assert MilestoneStatus.AT_RISK.value == "at_risk"


class TestDeliverableModel:
    """Tests for Deliverable dataclass model."""

    def test_create_deliverable(self):
        """Test creating a deliverable."""
        deliverable = Deliverable(
            id=str(uuid4()),
            project_id="prj-001",
            milestone_id="ms-001",
            deliverable_number="D1.1",
            name="Design Specification",
            deliverable_type=DeliverableType.DOCUMENT,
            due_date=date.today() + timedelta(days=14),
        )
        assert deliverable.deliverable_number == "D1.1"
        assert deliverable.deliverable_type == DeliverableType.DOCUMENT

    def test_deliverable_to_dict(self):
        """Test converting deliverable to dictionary."""
        deliverable = Deliverable(
            id="del-001",
            project_id="prj-001",
            name="Prototype Assembly",
            deliverable_type=DeliverableType.PROTOTYPE,
            status=MilestoneStatus.IN_PROGRESS,
            percent_complete=75,
            assigned_name="Engineering Team",
        )
        data = deliverable.to_dict()
        assert data["name"] == "Prototype Assembly"
        assert data["deliverable_type"] == "prototype"
        assert data["percent_complete"] == 75

    def test_deliverable_type_enums(self):
        """Test deliverable type enums."""
        assert DeliverableType.DOCUMENT.value == "document"
        assert DeliverableType.DRAWING.value == "drawing"
        assert DeliverableType.PART.value == "part"
        assert DeliverableType.PROTOTYPE.value == "prototype"
        assert DeliverableType.TEST_REPORT.value == "test_report"


class TestProjectDashboard:
    """Tests for ProjectDashboard model."""

    def test_create_project_dashboard(self):
        """Test creating a project dashboard."""
        dashboard = ProjectDashboard(
            project_id="prj-001",
            project_number="PRJ-2024-001",
            project_name="Widget Project",
            status="active",
            phase="design",
            health="green",
            on_schedule=True,
            on_budget=True,
            total_milestones=5,
            completed_milestones=2,
        )
        assert dashboard.health == "green"
        assert dashboard.total_milestones == 5
        assert dashboard.completed_milestones == 2

    def test_project_dashboard_to_dict(self):
        """Test converting dashboard to dictionary."""
        dashboard = ProjectDashboard(
            project_id="prj-001",
            project_number="PRJ-2024-001",
            project_name="Widget Project",
            status="active",
            phase="design",
            health="yellow",
            days_to_completion=45,
            schedule_variance_days=-5,
            on_schedule=False,
            budget=100000.0,
            actual_cost=75000.0,
            budget_variance=-25000.0,
            on_budget=True,
            total_milestones=5,
            completed_milestones=2,
            overdue_milestones=1,
            part_count=25,
            document_count=15,
            open_ecos=3,
        )
        data = dashboard.to_dict()
        assert data["health"] == "yellow"
        assert data["schedule"]["days_to_completion"] == 45
        assert data["schedule"]["on_schedule"] is False
        assert data["budget"]["actual"] == 75000.0
        assert data["milestones"]["total"] == 5
        assert data["plm_items"]["parts"] == 25
