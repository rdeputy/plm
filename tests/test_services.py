"""
Service Layer Tests

Tests for domain service classes.
"""

import pytest
from uuid import uuid4
from decimal import Decimal
from datetime import date

from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker

from plm.db.base import Base
from plm.suppliers.service import ManufacturerService, VendorService, SupplierService
from plm.compliance.service import ComplianceService
from plm.costing.service import CostingService
from plm.service_bulletins.service import ServiceBulletinService, MaintenanceService, UnitConfigurationService
from plm.projects.service import ProjectService


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
# Supplier Service Tests
# =============================================================================


class TestManufacturerService:
    """Tests for ManufacturerService."""

    def test_create_manufacturer(self, session):
        """Test creating a manufacturer."""
        service = ManufacturerService(session)
        mfg = service.create_manufacturer(
            manufacturer_code="MFG-SVC-001",
            name="Service Test Manufacturer",
            country="USA",
        )
        assert mfg.manufacturer_code == "MFG-SVC-001"
        assert mfg.status == "pending"

    def test_get_manufacturer(self, session):
        """Test getting a manufacturer by ID."""
        service = ManufacturerService(session)
        mfg = service.create_manufacturer(
            manufacturer_code="MFG-SVC-002",
            name="Get Test Manufacturer",
        )
        session.flush()

        result = service.get_manufacturer(mfg.id)
        assert result is not None
        assert result.name == "Get Test Manufacturer"

    def test_get_manufacturer_by_code(self, session):
        """Test getting manufacturer by code."""
        service = ManufacturerService(session)
        service.create_manufacturer(
            manufacturer_code="MFG-SVC-003",
            name="Code Test Manufacturer",
        )
        session.flush()

        result = service.get_manufacturer_by_code("MFG-SVC-003")
        assert result is not None

    def test_approve_manufacturer(self, session):
        """Test approving a manufacturer."""
        service = ManufacturerService(session)
        mfg = service.create_manufacturer(
            manufacturer_code="MFG-SVC-004",
            name="Approve Test",
        )
        session.flush()

        approved = service.approve_manufacturer(mfg.id)
        assert approved.status == "approved"


class TestVendorService:
    """Tests for VendorService."""

    def test_create_vendor(self, session):
        """Test creating a vendor."""
        service = VendorService(session)
        vendor = service.create_vendor(
            vendor_code="VND-SVC-001",
            name="Service Test Vendor",
            tier="preferred",
        )
        assert vendor.vendor_code == "VND-SVC-001"
        assert vendor.tier == "preferred"

    def test_get_vendor_by_code(self, session):
        """Test getting vendor by code."""
        service = VendorService(session)
        service.create_vendor(
            vendor_code="VND-SVC-002",
            name="Code Test Vendor",
            tier="approved",
        )
        session.flush()

        result = service.get_vendor_by_code("VND-SVC-002")
        assert result is not None

    def test_approve_vendor(self, session):
        """Test approving a vendor."""
        service = VendorService(session)
        vendor = service.create_vendor(
            vendor_code="VND-SVC-003",
            name="Approve Test Vendor",
        )
        session.flush()

        approved = service.approve_vendor(vendor.id)
        assert approved.status == "approved"


class TestSupplierService:
    """Tests for combined SupplierService."""

    def test_get_stats(self, session):
        """Test getting supplier statistics."""
        # Create some data
        mfg_service = ManufacturerService(session)
        vendor_service = VendorService(session)

        mfg_service.create_manufacturer(
            manufacturer_code="MFG-STAT-001",
            name="Stats Mfg 1",
        )
        mfg_service.approve_manufacturer(
            mfg_service.get_manufacturer_by_code("MFG-STAT-001").id
        )
        vendor_service.create_vendor(
            vendor_code="VND-STAT-001",
            name="Stats Vendor",
            tier="preferred",
        )
        session.flush()

        service = SupplierService(session)
        stats = service.get_stats()

        assert stats.total_manufacturers >= 1
        assert stats.total_vendors >= 1


# =============================================================================
# Compliance Service Tests
# =============================================================================


class TestComplianceService:
    """Tests for ComplianceService."""

    def test_list_active_regulations(self, session):
        """Test listing active regulations."""
        service = ComplianceService(session)

        # Create a regulation
        from plm.compliance.repository import RegulationRepository
        reg_repo = RegulationRepository(session)
        reg_repo.create(
            regulation_code="REG-SVC-001",
            name="Service Test Regulation",
            regulation_type="ROHS",
            is_active=True,
        )
        session.flush()

        results = service.list_active_regulations()
        assert len(results) >= 1

    def test_declare_substance(self, session):
        """Test declaring a substance in a part."""
        service = ComplianceService(session)
        part_id = str(uuid4())

        substance = service.declare_substance(
            part_id=part_id,
            substance_name="Lead",
            cas_number="7439-92-1",
            concentration_ppm=500.0,
            threshold_ppm=1000.0,
        )
        assert substance.substance_name == "Lead"
        assert substance.above_threshold is False

    def test_declare_substance_above_threshold(self, session):
        """Test substance above threshold."""
        service = ComplianceService(session)
        part_id = str(uuid4())

        substance = service.declare_substance(
            part_id=part_id,
            substance_name="Mercury",
            concentration_ppm=1500.0,
            threshold_ppm=1000.0,
        )
        assert substance.above_threshold is True

    def test_get_part_substances(self, session):
        """Test getting substances for a part."""
        service = ComplianceService(session)
        part_id = str(uuid4())

        service.declare_substance(
            part_id=part_id,
            substance_name="Cadmium",
            concentration_ppm=50.0,
        )
        service.declare_substance(
            part_id=part_id,
            substance_name="Lead",
            concentration_ppm=100.0,
        )
        session.flush()

        substances = service.get_part_substances(part_id)
        assert len(substances) == 2


# =============================================================================
# Costing Service Tests
# =============================================================================


class TestCostingService:
    """Tests for CostingService."""

    def test_create_part_cost(self, session):
        """Test creating a part cost record."""
        service = CostingService(session)
        part_id = str(uuid4())

        cost = service.create_part_cost(
            part_id=part_id,
            part_number="PART-SVC-001",
            currency="USD",
        )
        assert cost.part_id == part_id
        assert cost.currency == "USD"

    def test_add_cost_element(self, session):
        """Test adding a cost element."""
        service = CostingService(session)
        part_id = str(uuid4())

        cost = service.create_part_cost(part_id=part_id, part_number="PART-ELM-001")
        session.flush()

        element = service.add_cost_element(
            part_cost_id=cost.id,
            cost_type="material",
            description="Raw Material",
            quantity=Decimal("10"),
            unit_cost=Decimal("5.00"),
        )
        assert element.extended_cost == Decimal("50.00")

    def test_get_cost_breakdown(self, session):
        """Test getting cost breakdown."""
        service = CostingService(session)
        part_id = str(uuid4())

        cost = service.create_part_cost(part_id=part_id, part_number="PART-BRK-001")
        session.flush()

        service.add_cost_element(
            part_cost_id=cost.id,
            cost_type="material",
            description="Material",
            quantity=Decimal("1"),
            unit_cost=Decimal("100.00"),
        )
        service.add_cost_element(
            part_cost_id=cost.id,
            cost_type="labor",
            description="Labor",
            quantity=Decimal("2"),
            unit_cost=Decimal("25.00"),
        )
        session.flush()

        breakdown = service.get_cost_breakdown(part_id)
        assert breakdown is not None
        assert breakdown.element_count == 2

    def test_record_variance(self, session):
        """Test recording a cost variance."""
        service = CostingService(session)
        part_id = str(uuid4())

        variance = service.record_variance(
            part_id=part_id,
            part_number="PART-VAR-001",
            period="2025-01",
            standard_cost=Decimal("100.00"),
            actual_cost=Decimal("110.00"),
            quantity=Decimal("5"),
        )
        assert variance.favorable is False
        assert variance.variance == Decimal("10.00")


# =============================================================================
# Service Bulletins Service Tests
# =============================================================================


class TestServiceBulletinService:
    """Tests for ServiceBulletinService."""

    def test_create_bulletin(self, session):
        """Test creating a service bulletin."""
        service = ServiceBulletinService(session)
        bulletin = service.create_bulletin(
            bulletin_number="SB-SVC-001",
            bulletin_type="mandatory",
            title="Service Test Bulletin",
            summary="Test summary",
            safety_issue=True,
        )
        assert bulletin.bulletin_number == "SB-SVC-001"
        assert bulletin.safety_issue is True

    def test_get_bulletin_by_number(self, session):
        """Test getting bulletin by number."""
        service = ServiceBulletinService(session)
        service.create_bulletin(
            bulletin_number="SB-SVC-002",
            bulletin_type="optional",
            title="Get Test Bulletin",
        )
        session.flush()

        result = service.get_bulletin_by_number("SB-SVC-002")
        assert result is not None

    def test_list_safety_bulletins(self, session):
        """Test listing safety bulletins."""
        service = ServiceBulletinService(session)
        service.create_bulletin(
            bulletin_number="SB-SAF-001",
            bulletin_type="mandatory",
            title="Safety Bulletin",
            safety_issue=True,
        )
        service.create_bulletin(
            bulletin_number="SB-REG-001",
            bulletin_type="optional",
            title="Regular Bulletin",
            safety_issue=False,
        )
        session.flush()

        results = service.list_safety_bulletins()
        assert all(r.safety_issue for r in results)


class TestMaintenanceService:
    """Tests for MaintenanceService."""

    def test_create_schedule(self, session):
        """Test creating a maintenance schedule."""
        service = MaintenanceService(session)
        schedule = service.create_schedule(
            schedule_code="MAINT-001",
            system="Hydraulic",
            component="Pump Assembly",
            interval_type="calendar",
            interval_value=90,
            interval_unit="days",
            task_description="Inspect hydraulic pump",
        )
        assert schedule.schedule_code == "MAINT-001"
        assert schedule.interval_value == 90

    def test_get_schedule_by_code(self, session):
        """Test getting schedule by code."""
        service = MaintenanceService(session)
        service.create_schedule(
            schedule_code="MAINT-002",
            system="Electrical",
            component="Battery",
            interval_type="cycles",
            interval_value=500,
            interval_unit="cycles",
            task_description="Battery check",
        )
        session.flush()

        result = service.get_schedule_by_code("MAINT-002")
        assert result is not None


class TestUnitConfigurationService:
    """Tests for UnitConfigurationService."""

    def test_create_unit(self, session):
        """Test creating a unit configuration."""
        service = UnitConfigurationService(session)
        unit = service.create_unit(
            serial_number="SN-001",
            part_id=str(uuid4()),
            part_number="PART-001",
            owner_name="Test Owner",
        )
        assert unit.serial_number == "SN-001"

    def test_get_unit_by_serial(self, session):
        """Test getting unit by serial number."""
        service = UnitConfigurationService(session)
        service.create_unit(
            serial_number="SN-002",
            part_id=str(uuid4()),
            part_number="PART-002",
        )
        session.flush()

        result = service.get_unit_by_serial("SN-002")
        assert result is not None

    def test_update_usage(self, session):
        """Test updating unit usage."""
        service = UnitConfigurationService(session)
        unit = service.create_unit(
            serial_number="SN-003",
            part_id=str(uuid4()),
            part_number="PART-003",
        )
        session.flush()

        updated = service.update_usage(unit.id, hours=100.5, cycles=50)
        assert float(updated.total_hours) == 100.5
        assert updated.total_cycles == 50


# =============================================================================
# Project Service Tests
# =============================================================================


class TestProjectService:
    """Tests for ProjectService."""

    def test_create_project(self, session):
        """Test creating a project."""
        service = ProjectService(session)
        project = service.create_project(
            project_number="PRJ-SVC-001",
            name="Service Test Project",
            project_type="product",
            description="Test project",
        )
        assert project.project_number == "PRJ-SVC-001"

    def test_get_project_by_number(self, session):
        """Test getting project by number."""
        service = ProjectService(session)
        service.create_project(
            project_number="PRJ-SVC-002",
            name="Get Test Project",
        )
        session.flush()

        result = service.get_project_by_number("PRJ-SVC-002")
        assert result is not None

    def test_activate_project(self, session):
        """Test activating a project."""
        service = ProjectService(session)
        project = service.create_project(
            project_number="PRJ-SVC-003",
            name="Activate Test",
        )
        session.flush()

        activated = service.activate_project(project.id)
        assert str(activated.status) == "active" or activated.status.value == "active"

    def test_create_milestone(self, session):
        """Test creating a milestone."""
        service = ProjectService(session)
        project = service.create_project(
            project_number="PRJ-SVC-004",
            name="Milestone Project",
        )
        session.flush()

        milestone = service.create_milestone(
            project_id=project.id,
            milestone_number="MS-001",
            name="Test Milestone",
            planned_date=date.today(),
        )
        assert milestone.name == "Test Milestone"

    def test_create_deliverable(self, session):
        """Test creating a deliverable."""
        service = ProjectService(session)
        project = service.create_project(
            project_number="PRJ-SVC-005",
            name="Deliverable Project",
        )
        session.flush()

        deliverable = service.create_deliverable(
            project_id=project.id,
            name="Test Deliverable",
            deliverable_type="document",
            due_date=date.today(),
        )
        assert deliverable.name == "Test Deliverable"

    def test_list_project_milestones(self, session):
        """Test listing project milestones."""
        service = ProjectService(session)
        project = service.create_project(
            project_number="PRJ-SVC-006",
            name="Multi-Milestone Project",
        )
        session.flush()

        for i in range(3):
            service.create_milestone(
                project_id=project.id,
                milestone_number=f"MS-{i:03d}",
                name=f"Milestone {i}",
            )
        session.flush()

        milestones = service.list_project_milestones(project.id)
        assert len(milestones) == 3

    def test_get_project_progress(self, session):
        """Test getting project progress."""
        service = ProjectService(session)
        project = service.create_project(
            project_number="PRJ-SVC-007",
            name="Progress Project",
        )
        session.flush()

        service.create_milestone(
            project_id=project.id,
            milestone_number="MS-001",
            name="Milestone 1",
        )
        service.create_deliverable(
            project_id=project.id,
            name="Deliverable 1",
        )
        session.flush()

        progress = service.get_project_progress(project.id)
        assert progress is not None
        assert progress.milestones_total == 1
        assert progress.deliverables_total == 1
