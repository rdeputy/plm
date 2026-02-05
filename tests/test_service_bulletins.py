"""
Tests for Service Bulletins Module

Tests ServiceBulletin, BulletinCompliance, and related models.
"""

import pytest
from datetime import date, datetime
from uuid import uuid4

from plm.service_bulletins.models import (
    ServiceBulletin,
    BulletinCompliance,
    MaintenanceSchedule,
    UnitConfiguration,
    BulletinType,
    BulletinStatus,
    ComplianceStatus,
)


class TestServiceBulletinModel:
    """Tests for ServiceBulletin dataclass model."""

    def test_create_service_bulletin(self):
        """Test creating a service bulletin."""
        sb = ServiceBulletin(
            id=str(uuid4()),
            bulletin_number="SB-2024-001",
            bulletin_type=BulletinType.MANDATORY,
            title="Replace Widget Assembly",
            summary="Critical widget replacement required",
            safety_issue=True,
        )
        assert sb.bulletin_number == "SB-2024-001"
        assert sb.bulletin_type == BulletinType.MANDATORY
        assert sb.safety_issue is True
        assert sb.status == BulletinStatus.DRAFT

    def test_service_bulletin_to_dict(self):
        """Test converting service bulletin to dictionary."""
        sb = ServiceBulletin(
            id="sb-001",
            bulletin_number="SB-2024-001",
            bulletin_type=BulletinType.SAFETY,
            status=BulletinStatus.ACTIVE,
            title="Safety Recall",
            summary="Safety-critical component recall",
            safety_issue=True,
            affected_part_numbers=["PART-001", "PART-002"],
            compliance_deadline=date(2024, 12, 31),
        )
        data = sb.to_dict()
        assert data["bulletin_number"] == "SB-2024-001"
        assert data["bulletin_type"] == "safety"
        assert data["status"] == "active"
        assert data["safety_issue"] is True
        assert len(data["affected_part_numbers"]) == 2

    def test_bulletin_type_enums(self):
        """Test bulletin type enums."""
        assert BulletinType.SAFETY.value == "safety"
        assert BulletinType.MANDATORY.value == "mandatory"
        assert BulletinType.RECOMMENDED.value == "recommended"
        assert BulletinType.OPTIONAL.value == "optional"
        assert BulletinType.RECALL.value == "recall"

    def test_bulletin_status_enums(self):
        """Test bulletin status enums."""
        assert BulletinStatus.DRAFT.value == "draft"
        assert BulletinStatus.UNDER_REVIEW.value == "under_review"
        assert BulletinStatus.APPROVED.value == "approved"
        assert BulletinStatus.ACTIVE.value == "active"
        assert BulletinStatus.SUPERSEDED.value == "superseded"


class TestBulletinCompliance:
    """Tests for BulletinCompliance model."""

    def test_create_bulletin_compliance(self):
        """Test creating a bulletin compliance record."""
        compliance = BulletinCompliance(
            id=str(uuid4()),
            bulletin_id="sb-001",
            bulletin_number="SB-2024-001",
            serial_number="SN-12345",
            status=ComplianceStatus.COMPLETED,
            completed_date=date(2024, 6, 15),
            completed_by="mechanic",
        )
        assert compliance.status == ComplianceStatus.COMPLETED
        assert compliance.serial_number == "SN-12345"

    def test_bulletin_compliance_waived(self):
        """Test bulletin compliance with waiver."""
        compliance = BulletinCompliance(
            id=str(uuid4()),
            bulletin_id="sb-001",
            bulletin_number="SB-2024-001",
            serial_number="SN-12345",
            status=ComplianceStatus.WAIVED,
            waived=True,
            waiver_reason="Not applicable - different configuration",
            waiver_approved_by="engineering",
        )
        assert compliance.waived is True
        assert compliance.status == ComplianceStatus.WAIVED

    def test_compliance_status_enums(self):
        """Test compliance status enums."""
        assert ComplianceStatus.NOT_APPLICABLE.value == "not_applicable"
        assert ComplianceStatus.PENDING.value == "pending"
        assert ComplianceStatus.IN_PROGRESS.value == "in_progress"
        assert ComplianceStatus.COMPLETED.value == "completed"
        assert ComplianceStatus.WAIVED.value == "waived"

    def test_bulletin_compliance_to_dict(self):
        """Test converting compliance record to dictionary."""
        compliance = BulletinCompliance(
            id="bc-001",
            bulletin_id="sb-001",
            bulletin_number="SB-2024-001",
            serial_number="SN-12345",
            status=ComplianceStatus.COMPLETED,
            completed_date=date(2024, 6, 15),
        )
        data = compliance.to_dict()
        assert data["bulletin_number"] == "SB-2024-001"
        assert data["serial_number"] == "SN-12345"
        assert data["status"] == "completed"


class TestMaintenanceSchedule:
    """Tests for MaintenanceSchedule model."""

    def test_create_maintenance_schedule(self):
        """Test creating a maintenance schedule."""
        schedule = MaintenanceSchedule(
            id=str(uuid4()),
            schedule_code="100HR",
            part_number="ENGINE-001",
            system="Engine",
            interval_type="hours",
            interval_value=100,
            interval_unit="hours",
            task_description="100-hour inspection",
        )
        assert schedule.schedule_code == "100HR"
        assert schedule.interval_value == 100
        assert schedule.is_active is True

    def test_maintenance_schedule_to_dict(self):
        """Test converting maintenance schedule to dictionary."""
        schedule = MaintenanceSchedule(
            id="ms-001",
            schedule_code="ANNUAL",
            system="Airframe",
            interval_type="calendar",
            interval_value=365,
            interval_unit="days",
            task_description="Annual inspection",
        )
        data = schedule.to_dict()
        assert data["schedule_code"] == "ANNUAL"
        assert data["interval_type"] == "calendar"
        assert data["interval_value"] == 365


class TestUnitConfiguration:
    """Tests for UnitConfiguration model."""

    def test_create_unit_configuration(self):
        """Test creating a unit configuration."""
        config = UnitConfiguration(
            id=str(uuid4()),
            serial_number="SN-12345",
            part_id="part-001",
            part_number="PRODUCT-001",
            current_revision="B",
            total_hours=1500.5,
            total_cycles=500,
            owner_name="ABC Company",
        )
        assert config.serial_number == "SN-12345"
        assert config.total_hours == 1500.5
        assert config.total_cycles == 500

    def test_unit_configuration_with_bulletins(self):
        """Test unit configuration with bulletin tracking."""
        config = UnitConfiguration(
            id=str(uuid4()),
            serial_number="SN-12345",
            part_id="part-001",
            part_number="PRODUCT-001",
            applied_bulletins=["SB-001", "SB-002"],
            pending_bulletins=["SB-003"],
        )
        assert len(config.applied_bulletins) == 2
        assert len(config.pending_bulletins) == 1

    def test_unit_configuration_to_dict(self):
        """Test converting unit configuration to dictionary."""
        config = UnitConfiguration(
            id="uc-001",
            serial_number="SN-12345",
            part_id="part-001",
            part_number="PRODUCT-001",
            current_revision="B",
            total_hours=1500.5,
            total_cycles=500,
            owner_name="ABC Company",
            applied_bulletins=["SB-001", "SB-002"],
            pending_bulletins=["SB-003"],
        )
        data = config.to_dict()
        assert data["serial_number"] == "SN-12345"
        assert data["total_hours"] == 1500.5
        assert data["applied_bulletins"] == 2
        assert data["pending_bulletins"] == 1
