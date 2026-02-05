"""
Tests for Suppliers Module (AML/AVL)

Tests Manufacturer, Vendor, ApprovedManufacturer, and ApprovedVendor models.
"""

import pytest
from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

from plm.suppliers.models import (
    Manufacturer,
    Vendor,
    ApprovedManufacturer,
    ApprovedVendor,
    PartSourceMatrix,
    ApprovalStatus,
    SupplierTier,
    QualificationStatus,
)


class TestManufacturerModel:
    """Tests for Manufacturer dataclass model."""

    def test_create_manufacturer(self):
        """Test creating a manufacturer."""
        mfr = Manufacturer(
            id=str(uuid4()),
            manufacturer_code="MFR-001",
            name="Acme Industries",
            country="USA",
            status=ApprovalStatus.APPROVED,
        )
        assert mfr.manufacturer_code == "MFR-001"
        assert mfr.name == "Acme Industries"
        assert mfr.status == ApprovalStatus.APPROVED
        assert mfr.created_at is not None

    def test_manufacturer_to_dict(self):
        """Test converting manufacturer to dictionary."""
        mfr = Manufacturer(
            id="mfr-001",
            manufacturer_code="MFR-001",
            name="Acme Industries",
            country="USA",
            status=ApprovalStatus.APPROVED,
            certifications=["ISO 9001", "AS9100"],
            cage_code="12345",
            audit_score=95,
        )
        data = mfr.to_dict()
        assert data["manufacturer_code"] == "MFR-001"
        assert data["status"] == "approved"
        assert data["certifications"] == ["ISO 9001", "AS9100"]
        assert data["cage_code"] == "12345"
        assert data["audit_score"] == 95

    def test_approval_status_enums(self):
        """Test approval status enums."""
        assert ApprovalStatus.PENDING.value == "pending"
        assert ApprovalStatus.APPROVED.value == "approved"
        assert ApprovalStatus.CONDITIONAL.value == "conditional"
        assert ApprovalStatus.SUSPENDED.value == "suspended"
        assert ApprovalStatus.DISQUALIFIED.value == "disqualified"


class TestVendorModel:
    """Tests for Vendor dataclass model."""

    def test_create_vendor(self):
        """Test creating a vendor."""
        vendor = Vendor(
            id=str(uuid4()),
            vendor_code="VND-001",
            name="ABC Distribution",
            country="USA",
            status=ApprovalStatus.APPROVED,
            tier=SupplierTier.PREFERRED,
        )
        assert vendor.vendor_code == "VND-001"
        assert vendor.name == "ABC Distribution"
        assert vendor.tier == SupplierTier.PREFERRED

    def test_vendor_to_dict(self):
        """Test converting vendor to dictionary."""
        vendor = Vendor(
            id="vnd-001",
            vendor_code="VND-001",
            name="ABC Distribution",
            country="USA",
            status=ApprovalStatus.APPROVED,
            tier=SupplierTier.STRATEGIC,
            on_time_delivery_rate=98.5,
            quality_rating=4.8,
            lead_time_days=5,
        )
        data = vendor.to_dict()
        assert data["vendor_code"] == "VND-001"
        assert data["status"] == "approved"
        assert data["tier"] == "strategic"
        assert data["on_time_delivery_rate"] == 98.5
        assert data["quality_rating"] == 4.8

    def test_supplier_tier_enums(self):
        """Test supplier tier enums."""
        assert SupplierTier.STRATEGIC.value == "strategic"
        assert SupplierTier.PREFERRED.value == "preferred"
        assert SupplierTier.APPROVED.value == "approved"
        assert SupplierTier.PROVISIONAL.value == "provisional"
        assert SupplierTier.RESTRICTED.value == "restricted"


class TestApprovedManufacturer:
    """Tests for ApprovedManufacturer (AML entry) model."""

    def test_create_approved_manufacturer(self):
        """Test creating an AML entry."""
        aml = ApprovedManufacturer(
            id=str(uuid4()),
            part_id="part-001",
            part_number="PART-12345",
            manufacturer_id="mfr-001",
            manufacturer_name="Acme Industries",
            manufacturer_part_number="ACM-98765",
            status=ApprovalStatus.APPROVED,
            qualification_status=QualificationStatus.QUALIFIED,
            is_primary=True,
        )
        assert aml.manufacturer_part_number == "ACM-98765"
        assert aml.is_primary is True
        assert aml.qualification_status == QualificationStatus.QUALIFIED

    def test_approved_manufacturer_to_dict(self):
        """Test converting AML entry to dictionary."""
        aml = ApprovedManufacturer(
            id="aml-001",
            part_id="part-001",
            part_number="PART-12345",
            manufacturer_id="mfr-001",
            manufacturer_name="Acme",
            manufacturer_part_number="ACM-001",
            status=ApprovalStatus.APPROVED,
            qualification_status=QualificationStatus.QUALIFIED,
            preference_rank=1,
            is_primary=True,
        )
        data = aml.to_dict()
        assert data["part_number"] == "PART-12345"
        assert data["manufacturer_name"] == "Acme"
        assert data["status"] == "approved"
        assert data["qualification_status"] == "qualified"
        assert data["is_primary"] is True

    def test_qualification_status_enums(self):
        """Test qualification status enums."""
        assert QualificationStatus.NOT_STARTED.value == "not_started"
        assert QualificationStatus.IN_PROGRESS.value == "in_progress"
        assert QualificationStatus.QUALIFIED.value == "qualified"
        assert QualificationStatus.FAILED.value == "failed"


class TestApprovedVendor:
    """Tests for ApprovedVendor (AVL entry) model."""

    def test_create_approved_vendor(self):
        """Test creating an AVL entry."""
        avl = ApprovedVendor(
            id=str(uuid4()),
            part_id="part-001",
            part_number="PART-12345",
            vendor_id="vnd-001",
            vendor_name="ABC Distribution",
            vendor_part_number="ABC-12345",
            status=ApprovalStatus.APPROVED,
            unit_price=Decimal("25.99"),
            lead_time_days=7,
            is_primary=True,
        )
        assert avl.vendor_part_number == "ABC-12345"
        assert avl.unit_price == Decimal("25.99")
        assert avl.lead_time_days == 7

    def test_approved_vendor_to_dict(self):
        """Test converting AVL entry to dictionary."""
        avl = ApprovedVendor(
            id="avl-001",
            part_id="part-001",
            part_number="PART-12345",
            vendor_id="vnd-001",
            vendor_name="ABC",
            unit_price=Decimal("25.99"),
            currency="USD",
            lead_time_days=7,
            status=ApprovalStatus.APPROVED,
        )
        data = avl.to_dict()
        assert data["part_number"] == "PART-12345"
        assert data["unit_price"] == 25.99
        assert data["currency"] == "USD"
        assert data["lead_time_days"] == 7


class TestPartSourceMatrix:
    """Tests for PartSourceMatrix model."""

    def test_create_source_matrix(self):
        """Test creating a part source matrix."""
        matrix = PartSourceMatrix(
            part_id="part-001",
            part_number="PART-12345",
            manufacturers=[{"name": "Acme", "is_primary": True}],
            vendors=[{"name": "ABC", "is_primary": True}],
            has_single_source=False,
            total_sources=2,
            primary_source="Acme via ABC",
        )
        assert matrix.total_sources == 2
        assert matrix.has_single_source is False

    def test_source_matrix_to_dict(self):
        """Test converting source matrix to dictionary."""
        matrix = PartSourceMatrix(
            part_id="part-001",
            part_number="PART-12345",
            total_sources=1,
            has_single_source=True,
        )
        data = matrix.to_dict()
        assert data["part_number"] == "PART-12345"
        assert data["has_single_source"] is True
        assert data["total_sources"] == 1
