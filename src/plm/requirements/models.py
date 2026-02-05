"""
Requirements Management Models

Data structures for requirements traceability.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any, Optional


class RequirementType(str, Enum):
    """Types of requirements."""
    CUSTOMER = "customer"           # Customer/contract requirements
    REGULATORY = "regulatory"       # Regulatory/compliance requirements
    SAFETY = "safety"               # Safety requirements
    PERFORMANCE = "performance"     # Performance specifications
    FUNCTIONAL = "functional"       # Functional requirements
    INTERFACE = "interface"         # Interface requirements
    ENVIRONMENTAL = "environmental" # Environmental requirements
    RELIABILITY = "reliability"     # Reliability/durability requirements
    INTERNAL = "internal"           # Internal/derived requirements


class RequirementStatus(str, Enum):
    """Requirement lifecycle status."""
    DRAFT = "draft"
    PROPOSED = "proposed"
    APPROVED = "approved"
    IMPLEMENTED = "implemented"
    VERIFIED = "verified"
    DEFERRED = "deferred"
    REJECTED = "rejected"
    OBSOLETE = "obsolete"


class RequirementPriority(str, Enum):
    """Requirement priority."""
    MUST_HAVE = "must_have"         # Critical - must be met
    SHOULD_HAVE = "should_have"     # Important - should be met
    COULD_HAVE = "could_have"       # Desirable - nice to have
    WONT_HAVE = "wont_have"         # Out of scope for now


class VerificationMethod(str, Enum):
    """How requirements are verified."""
    TEST = "test"                   # Verified by testing
    INSPECTION = "inspection"       # Verified by visual inspection
    ANALYSIS = "analysis"           # Verified by analysis/calculation
    DEMONSTRATION = "demonstration" # Verified by demonstration
    SIMILARITY = "similarity"       # Verified by similarity to proven design
    REVIEW = "review"               # Verified by design review


class VerificationStatus(str, Enum):
    """Verification record status."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    PASSED = "passed"
    FAILED = "failed"
    WAIVED = "waived"
    DEFERRED = "deferred"


@dataclass
class Requirement:
    """
    A single requirement.

    Represents a customer, regulatory, or internal requirement
    that must be satisfied by the product design.
    """
    id: str
    requirement_number: str         # "REQ-001", "CUS-123"

    # Classification
    requirement_type: RequirementType
    status: RequirementStatus = RequirementStatus.DRAFT
    priority: RequirementPriority = RequirementPriority.MUST_HAVE

    # Content
    title: str = ""
    description: str = ""
    rationale: str = ""             # Why this requirement exists
    acceptance_criteria: str = ""   # How to verify it's met

    # Source
    source: str = ""                # Where it came from
    source_document: Optional[str] = None
    source_section: Optional[str] = None
    customer_id: Optional[str] = None

    # Verification
    verification_method: VerificationMethod = VerificationMethod.TEST
    verification_procedure: Optional[str] = None

    # Hierarchy
    parent_id: Optional[str] = None         # Parent requirement
    derived_from: list[str] = field(default_factory=list)

    # Project context
    project_id: Optional[str] = None
    phase: Optional[str] = None             # Development phase

    # Lifecycle
    created_at: Optional[datetime] = None
    created_by: Optional[str] = None
    approved_by: Optional[str] = None
    approved_date: Optional[datetime] = None

    # Metadata
    tags: list[str] = field(default_factory=list)
    attachments: list[str] = field(default_factory=list)

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "requirement_number": self.requirement_number,
            "requirement_type": self.requirement_type.value,
            "status": self.status.value,
            "priority": self.priority.value,
            "title": self.title,
            "description": self.description,
            "source": self.source,
            "verification_method": self.verification_method.value,
            "parent_id": self.parent_id,
            "project_id": self.project_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


@dataclass
class RequirementLink:
    """
    Links a requirement to an implementing item.

    Creates traceability between requirements and parts,
    documents, tests, or other artifacts.
    """
    id: str
    requirement_id: str

    # What implements/satisfies this requirement
    link_type: str                  # part, document, test, assembly
    target_id: str                  # ID of the linked item
    target_number: Optional[str] = None  # Part number, doc number, etc.
    target_revision: Optional[str] = None

    # Relationship
    relationship: str = "implements"  # implements, verifies, derives_from

    # Coverage
    coverage: str = "full"          # full, partial, none
    coverage_notes: str = ""

    # Lifecycle
    created_at: Optional[datetime] = None
    created_by: Optional[str] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "requirement_id": self.requirement_id,
            "link_type": self.link_type,
            "target_id": self.target_id,
            "target_number": self.target_number,
            "relationship": self.relationship,
            "coverage": self.coverage,
        }


@dataclass
class VerificationRecord:
    """
    Records verification of a requirement.

    Documents how and when a requirement was verified.
    """
    id: str
    verification_number: str        # "VER-001"

    # What's being verified
    requirement_id: str
    requirement_number: str

    # Method
    method: VerificationMethod
    procedure_id: Optional[str] = None  # Link to test procedure
    procedure_number: Optional[str] = None

    # Status
    status: VerificationStatus = VerificationStatus.NOT_STARTED

    # Results
    result_summary: str = ""
    pass_fail: Optional[bool] = None
    actual_value: Optional[str] = None
    expected_value: Optional[str] = None
    deviation: Optional[str] = None

    # Evidence
    evidence_documents: list[str] = field(default_factory=list)
    test_report_id: Optional[str] = None

    # Who/when
    verified_by: Optional[str] = None
    verified_date: Optional[datetime] = None
    witness: Optional[str] = None

    # Approval
    approved_by: Optional[str] = None
    approved_date: Optional[datetime] = None

    # Lifecycle
    created_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "verification_number": self.verification_number,
            "requirement_id": self.requirement_id,
            "requirement_number": self.requirement_number,
            "method": self.method.value,
            "status": self.status.value,
            "pass_fail": self.pass_fail,
            "verified_by": self.verified_by,
            "verified_date": self.verified_date.isoformat() if self.verified_date else None,
        }


@dataclass
class TraceabilityMatrix:
    """
    Requirements traceability matrix for a project.

    Shows coverage of requirements by implementations
    and verification status.
    """
    project_id: str
    generated_at: datetime = field(default_factory=datetime.now)

    # Summary counts
    total_requirements: int = 0
    implemented_count: int = 0
    verified_count: int = 0
    failed_count: int = 0
    not_started_count: int = 0

    # Coverage percentages
    implementation_coverage: float = 0.0
    verification_coverage: float = 0.0

    # Detailed rows
    rows: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "project_id": self.project_id,
            "generated_at": self.generated_at.isoformat(),
            "summary": {
                "total_requirements": self.total_requirements,
                "implemented": self.implemented_count,
                "verified": self.verified_count,
                "failed": self.failed_count,
                "not_started": self.not_started_count,
            },
            "coverage": {
                "implementation": self.implementation_coverage,
                "verification": self.verification_coverage,
            },
            "rows": self.rows,
        }
