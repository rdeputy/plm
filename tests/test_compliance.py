"""
Tests for Compliance Module

Tests Regulation, ComplianceDeclaration, and related models.
"""

import pytest
from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

from plm.compliance.models import (
    Regulation,
    SubstanceDeclaration,
    ComplianceDeclaration,
    ComplianceCertificate,
    ConflictMineralDeclaration,
    PartComplianceStatus,
    RegulationType,
    ComplianceStatus,
    CertificateStatus,
    SubstanceCategory,
)


class TestRegulationModel:
    """Tests for Regulation dataclass model."""

    def test_create_regulation(self):
        """Test creating a regulation."""
        reg = Regulation(
            id=str(uuid4()),
            regulation_code="ROHS-2011/65/EU",
            name="RoHS Directive",
            regulation_type=RegulationType.ROHS,
            authority="European Union",
            regions=["EU"],
        )
        assert reg.regulation_code == "ROHS-2011/65/EU"
        assert reg.regulation_type == RegulationType.ROHS
        assert reg.is_active is True

    def test_regulation_to_dict(self):
        """Test converting regulation to dictionary."""
        reg = Regulation(
            id="reg-001",
            regulation_code="REACH-1907/2006",
            name="REACH Regulation",
            regulation_type=RegulationType.REACH,
            authority="ECHA",
            regions=["EU"],
            effective_date=date(2007, 6, 1),
        )
        data = reg.to_dict()
        assert data["regulation_code"] == "REACH-1907/2006"
        assert data["regulation_type"] == "reach"
        assert data["authority"] == "ECHA"
        assert data["regions"] == ["EU"]

    def test_regulation_type_enums(self):
        """Test regulation type enums."""
        assert RegulationType.ROHS.value == "rohs"
        assert RegulationType.REACH.value == "reach"
        assert RegulationType.CONFLICT_MINERALS.value == "conflict_minerals"
        assert RegulationType.WEEE.value == "weee"
        assert RegulationType.EXPORT_CONTROL.value == "export_control"


class TestSubstanceDeclaration:
    """Tests for SubstanceDeclaration model."""

    def test_create_substance_declaration(self):
        """Test creating a substance declaration."""
        decl = SubstanceDeclaration(
            id=str(uuid4()),
            part_id="part-001",
            part_number="PART-12345",
            substance_name="Lead",
            cas_number="7439-92-1",
            category=SubstanceCategory.LEAD,
            concentration_ppm=Decimal("50"),
            threshold_ppm=Decimal("1000"),
            above_threshold=False,
        )
        assert decl.substance_name == "Lead"
        assert decl.category == SubstanceCategory.LEAD
        assert decl.above_threshold is False

    def test_substance_declaration_to_dict(self):
        """Test converting substance declaration to dict."""
        decl = SubstanceDeclaration(
            id="sub-001",
            part_id="part-001",
            part_number="PART-12345",
            substance_name="Cadmium",
            cas_number="7440-43-9",
            category=SubstanceCategory.CADMIUM,
            concentration_ppm=Decimal("150"),
            above_threshold=True,
        )
        data = decl.to_dict()
        assert data["substance_name"] == "Cadmium"
        assert data["category"] == "cadmium"
        assert data["concentration_ppm"] == 150.0
        assert data["above_threshold"] is True

    def test_substance_category_enums(self):
        """Test substance category enums."""
        assert SubstanceCategory.LEAD.value == "lead"
        assert SubstanceCategory.MERCURY.value == "mercury"
        assert SubstanceCategory.CADMIUM.value == "cadmium"
        assert SubstanceCategory.CHROMIUM_VI.value == "chromium_vi"
        assert SubstanceCategory.SVHC.value == "svhc"


class TestComplianceDeclaration:
    """Tests for ComplianceDeclaration model."""

    def test_create_compliance_declaration(self):
        """Test creating a compliance declaration."""
        decl = ComplianceDeclaration(
            id=str(uuid4()),
            part_id="part-001",
            part_number="PART-12345",
            regulation_id="reg-001",
            regulation_code="ROHS-2011/65/EU",
            status=ComplianceStatus.COMPLIANT,
        )
        assert decl.status == ComplianceStatus.COMPLIANT
        assert decl.regulation_code == "ROHS-2011/65/EU"

    def test_compliance_declaration_with_exemption(self):
        """Test compliance declaration with exemption."""
        decl = ComplianceDeclaration(
            id=str(uuid4()),
            part_id="part-001",
            part_number="PART-12345",
            regulation_id="reg-001",
            regulation_code="ROHS-2011/65/EU",
            status=ComplianceStatus.EXEMPT,
            exemption_code="6(c)",
            exemption_expiry=date(2026, 7, 21),
        )
        assert decl.status == ComplianceStatus.EXEMPT
        assert decl.exemption_code == "6(c)"

    def test_compliance_status_enums(self):
        """Test compliance status enums."""
        assert ComplianceStatus.UNKNOWN.value == "unknown"
        assert ComplianceStatus.COMPLIANT.value == "compliant"
        assert ComplianceStatus.NON_COMPLIANT.value == "non_compliant"
        assert ComplianceStatus.EXEMPT.value == "exempt"
        assert ComplianceStatus.PENDING_DATA.value == "pending_data"


class TestComplianceCertificate:
    """Tests for ComplianceCertificate model."""

    def test_create_certificate(self):
        """Test creating a compliance certificate."""
        cert = ComplianceCertificate(
            id=str(uuid4()),
            certificate_number="CERT-2024-001",
            regulation_id="reg-001",
            regulation_code="ROHS-2011/65/EU",
            status=CertificateStatus.ACTIVE,
            issue_date=date(2024, 1, 1),
            expiry_date=date(2027, 12, 31),  # Future date
            issued_by="TUV",
        )
        assert cert.certificate_number == "CERT-2024-001"
        assert cert.status == CertificateStatus.ACTIVE
        assert cert.is_valid is True

    def test_certificate_expired(self):
        """Test expired certificate is_valid property."""
        cert = ComplianceCertificate(
            id=str(uuid4()),
            certificate_number="CERT-2020-001",
            regulation_id="reg-001",
            regulation_code="ROHS",
            status=CertificateStatus.ACTIVE,
            issue_date=date(2020, 1, 1),
            expiry_date=date(2021, 12, 31),  # Expired
        )
        assert cert.is_valid is False

    def test_certificate_status_enums(self):
        """Test certificate status enums."""
        assert CertificateStatus.DRAFT.value == "draft"
        assert CertificateStatus.ACTIVE.value == "active"
        assert CertificateStatus.EXPIRED.value == "expired"
        assert CertificateStatus.REVOKED.value == "revoked"


class TestConflictMineralDeclaration:
    """Tests for ConflictMineralDeclaration model."""

    def test_create_conflict_mineral_declaration(self):
        """Test creating a 3TG declaration."""
        decl = ConflictMineralDeclaration(
            id=str(uuid4()),
            part_id="part-001",
            part_number="PART-12345",
            contains_tin=True,
            contains_tantalum=False,
            contains_tungsten=False,
            contains_gold=True,
            conflict_free=True,
        )
        assert decl.contains_3tg is True
        assert decl.conflict_free is True

    def test_no_3tg_content(self):
        """Test declaration with no 3TG content."""
        decl = ConflictMineralDeclaration(
            id=str(uuid4()),
            part_id="part-001",
            part_number="PART-12345",
            contains_tin=False,
            contains_tantalum=False,
            contains_tungsten=False,
            contains_gold=False,
        )
        assert decl.contains_3tg is False

    def test_conflict_mineral_to_dict(self):
        """Test converting 3TG declaration to dict."""
        decl = ConflictMineralDeclaration(
            id="cm-001",
            part_id="part-001",
            part_number="PART-12345",
            contains_tin=True,
            contains_gold=True,
            conflict_free=True,
        )
        data = decl.to_dict()
        assert data["contains_3tg"] is True
        assert data["conflict_free"] is True
        assert data["contains"]["tin"] is True
        assert data["contains"]["gold"] is True
        assert data["contains"]["tantalum"] is False


class TestPartComplianceStatus:
    """Tests for PartComplianceStatus model."""

    def test_create_part_compliance_status(self):
        """Test creating part compliance status."""
        status = PartComplianceStatus(
            part_id="part-001",
            part_number="PART-12345",
            overall_compliant=True,
            has_issues=False,
            pending_review=2,
        )
        assert status.overall_compliant is True
        assert status.pending_review == 2

    def test_part_compliance_status_to_dict(self):
        """Test converting status to dict."""
        status = PartComplianceStatus(
            part_id="part-001",
            part_number="PART-12345",
            overall_compliant=False,
            has_issues=True,
            expiring_30_days=["ROHS", "REACH"],
        )
        data = status.to_dict()
        assert data["overall_compliant"] is False
        assert data["has_issues"] is True
        assert len(data["expiring_30_days"]) == 2
