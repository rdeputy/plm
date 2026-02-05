"""
Tests for Requirements Module

Tests Requirement, RequirementLink, and VerificationRecord models.
"""

import pytest
from datetime import datetime
from uuid import uuid4

from plm.requirements.models import (
    Requirement,
    RequirementLink,
    VerificationRecord,
    TraceabilityMatrix,
    RequirementType,
    RequirementStatus,
    RequirementPriority,
    VerificationMethod,
    VerificationStatus,
)


class TestRequirementModel:
    """Tests for Requirement dataclass model."""

    def test_create_requirement(self):
        """Test creating a requirement."""
        req = Requirement(
            id=str(uuid4()),
            requirement_number="REQ-001",
            requirement_type=RequirementType.CUSTOMER,
            title="Load Capacity",
            description="System must support 1000 lb load",
        )
        assert req.requirement_number == "REQ-001"
        assert req.requirement_type == RequirementType.CUSTOMER
        assert req.status == RequirementStatus.DRAFT
        assert req.priority == RequirementPriority.MUST_HAVE
        assert req.created_at is not None

    def test_requirement_to_dict(self):
        """Test converting requirement to dictionary."""
        req = Requirement(
            id="test-id",
            requirement_number="REQ-002",
            requirement_type=RequirementType.SAFETY,
            status=RequirementStatus.APPROVED,
            priority=RequirementPriority.MUST_HAVE,
            title="Safety Interlock",
            description="Must have safety interlock on door",
            source="Customer Spec v1.0",
            verification_method=VerificationMethod.TEST,
        )
        data = req.to_dict()
        assert data["requirement_number"] == "REQ-002"
        assert data["requirement_type"] == "safety"
        assert data["status"] == "approved"
        assert data["priority"] == "must_have"
        assert data["verification_method"] == "test"

    def test_requirement_type_enums(self):
        """Test requirement type enums."""
        assert RequirementType.CUSTOMER.value == "customer"
        assert RequirementType.REGULATORY.value == "regulatory"
        assert RequirementType.SAFETY.value == "safety"
        assert RequirementType.PERFORMANCE.value == "performance"
        assert RequirementType.FUNCTIONAL.value == "functional"

    def test_requirement_status_enums(self):
        """Test requirement status enums."""
        assert RequirementStatus.DRAFT.value == "draft"
        assert RequirementStatus.APPROVED.value == "approved"
        assert RequirementStatus.VERIFIED.value == "verified"
        assert RequirementStatus.OBSOLETE.value == "obsolete"

    def test_requirement_priority_enums(self):
        """Test priority enums (MoSCoW)."""
        assert RequirementPriority.MUST_HAVE.value == "must_have"
        assert RequirementPriority.SHOULD_HAVE.value == "should_have"
        assert RequirementPriority.COULD_HAVE.value == "could_have"
        assert RequirementPriority.WONT_HAVE.value == "wont_have"


class TestRequirementLink:
    """Tests for RequirementLink model."""

    def test_create_requirement_link(self):
        """Test creating a requirement link."""
        link = RequirementLink(
            id=str(uuid4()),
            requirement_id="req-001",
            link_type="part",
            target_id="part-001",
            target_number="PART-12345",
            relationship="implements",
            coverage="full",
        )
        assert link.link_type == "part"
        assert link.relationship == "implements"
        assert link.coverage == "full"

    def test_requirement_link_to_dict(self):
        """Test converting link to dictionary."""
        link = RequirementLink(
            id="link-001",
            requirement_id="req-001",
            link_type="test",
            target_id="test-001",
            relationship="verifies",
            coverage="partial",
            coverage_notes="Only covers nominal case",
        )
        data = link.to_dict()
        assert data["link_type"] == "test"
        assert data["relationship"] == "verifies"
        assert data["coverage"] == "partial"


class TestVerificationRecord:
    """Tests for VerificationRecord model."""

    def test_create_verification_record(self):
        """Test creating a verification record."""
        record = VerificationRecord(
            id=str(uuid4()),
            verification_number="VER-001",
            requirement_id="req-001",
            requirement_number="REQ-001",
            method=VerificationMethod.TEST,
            status=VerificationStatus.PASSED,
            pass_fail=True,
        )
        assert record.verification_number == "VER-001"
        assert record.method == VerificationMethod.TEST
        assert record.status == VerificationStatus.PASSED
        assert record.pass_fail is True

    def test_verification_method_enums(self):
        """Test verification method enums."""
        assert VerificationMethod.TEST.value == "test"
        assert VerificationMethod.INSPECTION.value == "inspection"
        assert VerificationMethod.ANALYSIS.value == "analysis"
        assert VerificationMethod.DEMONSTRATION.value == "demonstration"

    def test_verification_status_enums(self):
        """Test verification status enums."""
        assert VerificationStatus.NOT_STARTED.value == "not_started"
        assert VerificationStatus.IN_PROGRESS.value == "in_progress"
        assert VerificationStatus.PASSED.value == "passed"
        assert VerificationStatus.FAILED.value == "failed"

    def test_verification_record_to_dict(self):
        """Test converting verification record to dict."""
        record = VerificationRecord(
            id="ver-001",
            verification_number="VER-001",
            requirement_id="req-001",
            requirement_number="REQ-001",
            method=VerificationMethod.ANALYSIS,
            status=VerificationStatus.PASSED,
            pass_fail=True,
            verified_by="engineer",
        )
        data = record.to_dict()
        assert data["verification_number"] == "VER-001"
        assert data["method"] == "analysis"
        assert data["status"] == "passed"
        assert data["pass_fail"] is True


class TestTraceabilityMatrix:
    """Tests for TraceabilityMatrix model."""

    def test_create_traceability_matrix(self):
        """Test creating a traceability matrix."""
        matrix = TraceabilityMatrix(
            project_id="proj-001",
            total_requirements=10,
            implemented_count=8,
            verified_count=5,
            failed_count=1,
            not_started_count=4,
        )
        assert matrix.total_requirements == 10
        assert matrix.implemented_count == 8
        assert matrix.verified_count == 5

    def test_traceability_matrix_to_dict(self):
        """Test converting matrix to dict."""
        matrix = TraceabilityMatrix(
            project_id="proj-001",
            total_requirements=10,
            implemented_count=8,
            verified_count=5,
            implementation_coverage=80.0,
            verification_coverage=50.0,
        )
        data = matrix.to_dict()
        assert data["project_id"] == "proj-001"
        assert data["summary"]["total_requirements"] == 10
        assert data["coverage"]["implementation"] == 80.0
        assert data["coverage"]["verification"] == 50.0
