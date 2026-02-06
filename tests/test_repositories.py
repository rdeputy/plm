"""
Repository Layer Tests

Tests for the generic repository pattern and domain repositories.
"""

import pytest
from uuid import uuid4
from decimal import Decimal
from datetime import date, datetime

from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker

from plm.db.base import Base
from plm.db.repository import BaseRepository
from plm.db.models import (
    PartModel,
    RequirementModel,
    ManufacturerModel,
    SupplierVendorModel,
    RegulationModel,
    PartCostModel,
    CostElementModel,
    ServiceBulletinModel,
    ProjectModel,
    MilestoneModel,
)
from plm.requirements.repository import RequirementRepository, RequirementLinkRepository
from plm.suppliers.repository import (
    ManufacturerRepository,
    VendorRepository,
    ApprovedManufacturerRepository,
)
from plm.compliance.repository import RegulationRepository, ComplianceDeclarationRepository
from plm.costing.repository import PartCostRepository, CostElementRepository
from plm.service_bulletins.repository import ServiceBulletinRepository, BulletinComplianceRepository
from plm.projects.repository import ProjectRepository, MilestoneRepository, DeliverableRepository


# Test database setup
test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)

# Create all tables
Base.metadata.create_all(bind=test_engine)


@pytest.fixture
def session():
    """Create a fresh session for each test."""
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


# =============================================================================
# Base Repository Tests
# =============================================================================


class TestBaseRepository:
    """Tests for BaseRepository generic operations."""

    def test_create_entity(self, session):
        """Test creating an entity."""
        repo = BaseRepository(session, PartModel)
        part = repo.create(
            part_number="TEST-001",
            revision="A",
            name="Test Part",
            part_type="component",
            status="draft",
        )
        assert part.id is not None
        assert part.part_number == "TEST-001"

    def test_get_entity(self, session):
        """Test getting an entity by ID."""
        repo = BaseRepository(session, PartModel)
        part = repo.create(
            part_number="TEST-002",
            revision="A",
            name="Get Test Part",
            part_type="component",
            status="draft",
        )
        session.flush()

        retrieved = repo.get(part.id)
        assert retrieved is not None
        assert retrieved.part_number == "TEST-002"

    def test_get_nonexistent_entity(self, session):
        """Test getting a nonexistent entity returns None."""
        repo = BaseRepository(session, PartModel)
        result = repo.get(str(uuid4()))
        assert result is None

    def test_get_by_filters(self, session):
        """Test getting entity by filters."""
        repo = BaseRepository(session, PartModel)
        repo.create(
            part_number="FILTER-001",
            revision="A",
            name="Filter Test",
            part_type="assembly",
            status="released",
        )
        session.flush()

        result = repo.get_by(part_number="FILTER-001")
        assert result is not None
        assert result.name == "Filter Test"

    def test_list_entities(self, session):
        """Test listing entities."""
        repo = BaseRepository(session, PartModel)
        for i in range(5):
            repo.create(
                part_number=f"LIST-{i:03d}",
                revision="A",
                name=f"List Part {i}",
                part_type="component",
                status="draft",
            )
        session.flush()

        results = repo.list(limit=10)
        assert len(results) >= 5

    def test_list_with_filters(self, session):
        """Test listing with filters."""
        repo = BaseRepository(session, PartModel)
        repo.create(
            part_number="FILT-001",
            revision="A",
            name="Released Part",
            part_type="component",
            status="released",
        )
        repo.create(
            part_number="FILT-002",
            revision="A",
            name="Draft Part",
            part_type="component",
            status="draft",
        )
        session.flush()

        results = repo.list(status="released")
        assert all(r.status == "released" for r in results)

    def test_update_entity(self, session):
        """Test updating an entity."""
        repo = BaseRepository(session, PartModel)
        part = repo.create(
            part_number="UPDATE-001",
            revision="A",
            name="Original Name",
            part_type="component",
            status="draft",
        )
        session.flush()

        updated = repo.update(part.id, name="Updated Name", status="released")
        assert updated.name == "Updated Name"
        assert updated.status == "released"

    def test_delete_entity(self, session):
        """Test deleting an entity."""
        repo = BaseRepository(session, PartModel)
        part = repo.create(
            part_number="DELETE-001",
            revision="A",
            name="To Delete",
            part_type="component",
            status="draft",
        )
        session.flush()
        part_id = part.id

        result = repo.delete(part_id)
        assert result is True
        assert repo.get(part_id) is None

    def test_search_entities(self, session):
        """Test searching entities."""
        repo = BaseRepository(session, PartModel)
        repo.create(
            part_number="SRCH-001",
            revision="A",
            name="Searchable Widget",
            part_type="component",
            status="draft",
        )
        repo.create(
            part_number="SRCH-002",
            revision="A",
            name="Another Item",
            part_type="component",
            status="draft",
        )
        session.flush()

        results = repo.search("Widget", ["name", "part_number"])
        assert len(results) >= 1
        assert any("Widget" in r.name for r in results)


# =============================================================================
# Requirements Repository Tests
# =============================================================================


class TestRequirementRepository:
    """Tests for RequirementRepository."""

    def test_create_requirement(self, session):
        """Test creating a requirement."""
        repo = RequirementRepository(session)
        req = repo.create(
            requirement_number="REQ-TEST-001",
            requirement_type="functional",
            status="draft",
            priority="must_have",
            title="Test Requirement",
            project_id=str(uuid4()),
        )
        assert req.requirement_number == "REQ-TEST-001"

    def test_find_by_number(self, session):
        """Test finding requirement by number."""
        repo = RequirementRepository(session)
        repo.create(
            requirement_number="REQ-FIND-001",
            requirement_type="performance",
            status="draft",
            priority="should_have",
            title="Find Test",
            project_id=str(uuid4()),
        )
        session.flush()

        result = repo.find_by_number("REQ-FIND-001")
        assert result is not None
        assert result.title == "Find Test"

    def test_list_by_project(self, session):
        """Test listing requirements by project."""
        repo = RequirementRepository(session)
        project_id = str(uuid4())

        for i in range(3):
            repo.create(
                requirement_number=f"REQ-PROJ-{i:03d}",
                requirement_type="functional",
                status="draft",
                priority="must_have",
                title=f"Project Req {i}",
                project_id=project_id,
            )
        session.flush()

        results = repo.list_by_project(project_id)
        assert len(results) == 3


# =============================================================================
# Suppliers Repository Tests
# =============================================================================


class TestManufacturerRepository:
    """Tests for ManufacturerRepository."""

    def test_create_manufacturer(self, session):
        """Test creating a manufacturer."""
        repo = ManufacturerRepository(session)
        mfg = repo.create(
            manufacturer_code="MFG-TEST-001",
            name="Test Manufacturer",
            status="pending",
        )
        assert mfg.manufacturer_code == "MFG-TEST-001"

    def test_find_by_code(self, session):
        """Test finding manufacturer by code."""
        repo = ManufacturerRepository(session)
        repo.create(
            manufacturer_code="MFG-FIND-001",
            name="Find Test Mfg",
            status="approved",
        )
        session.flush()

        result = repo.find_by_code("MFG-FIND-001")
        assert result is not None
        assert result.name == "Find Test Mfg"

    def test_list_approved(self, session):
        """Test listing approved manufacturers."""
        repo = ManufacturerRepository(session)
        repo.create(manufacturer_code="MFG-APP-001", name="Approved 1", status="approved")
        repo.create(manufacturer_code="MFG-PND-001", name="Pending 1", status="pending")
        session.flush()

        results = repo.list_approved()
        assert all(r.status == "approved" for r in results)


class TestVendorRepository:
    """Tests for VendorRepository."""

    def test_create_vendor(self, session):
        """Test creating a vendor."""
        from plm.suppliers.models import SupplierTier, ApprovalStatus
        repo = VendorRepository(session)
        vendor = repo.create(
            vendor_code="VND-TEST-001",
            name="Test Vendor",
            tier=SupplierTier.PREFERRED,
            status=ApprovalStatus.APPROVED,
        )
        assert vendor.vendor_code == "VND-TEST-001"

    def test_list_by_tier(self, session):
        """Test listing vendors by tier."""
        from plm.suppliers.models import SupplierTier, ApprovalStatus
        repo = VendorRepository(session)
        repo.create(vendor_code="VND-T1-001", name="Tier 1", tier=SupplierTier.PREFERRED, status=ApprovalStatus.APPROVED)
        repo.create(vendor_code="VND-T2-001", name="Tier 2", tier=SupplierTier.APPROVED, status=ApprovalStatus.APPROVED)
        session.flush()

        results = repo.list_by_tier(SupplierTier.PREFERRED)
        assert all(r.tier == SupplierTier.PREFERRED for r in results)


# =============================================================================
# Compliance Repository Tests
# =============================================================================


class TestRegulationRepository:
    """Tests for RegulationRepository."""

    def test_create_regulation(self, session):
        """Test creating a regulation."""
        repo = RegulationRepository(session)
        reg = repo.create(
            regulation_code="REG-TEST-001",
            name="Test Regulation",
            regulation_type="ROHS",
            is_active=True,
        )
        assert reg.regulation_code == "REG-TEST-001"

    def test_find_by_code(self, session):
        """Test finding regulation by code."""
        repo = RegulationRepository(session)
        repo.create(
            regulation_code="REG-FIND-001",
            name="Find Test Reg",
            regulation_type="REACH",
            is_active=True,
        )
        session.flush()

        result = repo.find_by_code("REG-FIND-001")
        assert result is not None

    def test_list_active(self, session):
        """Test listing active regulations."""
        repo = RegulationRepository(session)
        repo.create(regulation_code="REG-ACT-001", name="Active", regulation_type="ROHS", is_active=True)
        repo.create(regulation_code="REG-INA-001", name="Inactive", regulation_type="ROHS", is_active=False)
        session.flush()

        results = repo.list_active()
        assert all(r.is_active for r in results)


# =============================================================================
# Costing Repository Tests
# =============================================================================


class TestPartCostRepository:
    """Tests for PartCostRepository."""

    def test_create_part_cost(self, session):
        """Test creating a part cost."""
        repo = PartCostRepository(session)
        cost = repo.create(
            part_id=str(uuid4()),
            part_number="PART-COST-001",
            currency="USD",
            material_cost=Decimal("100.00"),
            labor_cost=Decimal("50.00"),
            overhead_cost=Decimal("25.00"),
            total_cost=Decimal("175.00"),
            status="draft",
        )
        assert cost.total_cost == Decimal("175.00")

    def test_get_for_part(self, session):
        """Test getting cost for a part."""
        from plm.costing.models import CostEstimateStatus
        repo = PartCostRepository(session)
        part_id = str(uuid4())
        repo.create(
            part_id=part_id,
            part_number="PART-COST-002",
            currency="USD",
            total_cost=Decimal("200.00"),
            status=CostEstimateStatus.APPROVED,
        )
        session.flush()

        result = repo.get_for_part(part_id)
        assert result is not None
        assert result.total_cost == Decimal("200.00")


# =============================================================================
# Service Bulletins Repository Tests
# =============================================================================


class TestServiceBulletinRepository:
    """Tests for ServiceBulletinRepository."""

    def test_create_bulletin(self, session):
        """Test creating a service bulletin."""
        repo = ServiceBulletinRepository(session)
        sb = repo.create(
            bulletin_number="SB-TEST-001",
            bulletin_type="mandatory",
            status="draft",
            title="Test Bulletin",
            safety_issue=False,
        )
        assert sb.bulletin_number == "SB-TEST-001"

    def test_find_by_number(self, session):
        """Test finding bulletin by number."""
        repo = ServiceBulletinRepository(session)
        repo.create(
            bulletin_number="SB-FIND-001",
            bulletin_type="optional",
            status="active",
            title="Find Test",
            safety_issue=True,
        )
        session.flush()

        result = repo.find_by_number("SB-FIND-001")
        assert result is not None
        assert result.safety_issue is True

    def test_list_safety_related(self, session):
        """Test listing safety-related bulletins."""
        repo = ServiceBulletinRepository(session)
        repo.create(
            bulletin_number="SB-SAF-001",
            bulletin_type="mandatory",
            status="active",
            title="Safety Bulletin",
            safety_issue=True,
        )
        repo.create(
            bulletin_number="SB-REG-001",
            bulletin_type="optional",
            status="active",
            title="Regular Bulletin",
            safety_issue=False,
        )
        session.flush()

        results = repo.list_safety_related()
        assert all(r.safety_issue for r in results)


# =============================================================================
# Projects Repository Tests
# =============================================================================


class TestProjectRepository:
    """Tests for ProjectRepository."""

    def test_create_project(self, session):
        """Test creating a project."""
        repo = ProjectRepository(session)
        proj = repo.create(
            project_number="PRJ-TEST-001",
            name="Test Project",
            status="proposed",
            phase="concept",
        )
        assert proj.project_number == "PRJ-TEST-001"

    def test_find_by_number(self, session):
        """Test finding project by number."""
        repo = ProjectRepository(session)
        repo.create(
            project_number="PRJ-FIND-001",
            name="Find Test Project",
            status="active",
            phase="design",
        )
        session.flush()

        result = repo.find_by_number("PRJ-FIND-001")
        assert result is not None
        assert result.name == "Find Test Project"

    def test_list_active(self, session):
        """Test listing active projects."""
        repo = ProjectRepository(session)
        repo.create(project_number="PRJ-ACT-001", name="Active", status="active", phase="design")
        repo.create(project_number="PRJ-CMP-001", name="Complete", status="completed", phase="closeout")
        session.flush()

        results = repo.list_active()
        assert all(str(r.status) == "active" or r.status.value == "active" for r in results)


class TestMilestoneRepository:
    """Tests for MilestoneRepository."""

    def test_create_milestone(self, session):
        """Test creating a milestone."""
        # First create a project
        proj_repo = ProjectRepository(session)
        project = proj_repo.create(
            project_number="PRJ-MLST-001",
            name="Milestone Project",
            status="active",
            phase="design",
        )
        session.flush()

        repo = MilestoneRepository(session)
        milestone = repo.create(
            project_id=project.id,
            milestone_number="MS-001",
            name="Test Milestone",
            status="not_started",
            sequence=1,
        )
        assert milestone.name == "Test Milestone"

    def test_list_for_project(self, session):
        """Test listing milestones for a project."""
        proj_repo = ProjectRepository(session)
        project = proj_repo.create(
            project_number="PRJ-MLST-002",
            name="Multi-Milestone Project",
            status="active",
            phase="design",
        )
        session.flush()

        repo = MilestoneRepository(session)
        for i in range(3):
            repo.create(
                project_id=project.id,
                milestone_number=f"MS-{i:03d}",
                name=f"Milestone {i}",
                status="not_started",
                sequence=i,
            )
        session.flush()

        results = repo.list_for_project(project.id)
        assert len(results) == 3
