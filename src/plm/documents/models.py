"""
Document Models

Document management for PLM - engineering drawings, specifications, reports.
Integrates with orchestrator DMS for storage, versioning, and search.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class DocumentType(str, Enum):
    """Types of documents in PLM."""
    # Engineering
    DRAWING = "drawing"              # CAD drawings (DWG, DXF, PDF)
    MODEL_3D = "model_3d"            # 3D models (DWG, SKP, RVT, IFC)
    SPECIFICATION = "specification"  # Technical specifications
    DATASHEET = "datasheet"          # Product datasheets
    CALCULATION = "calculation"      # Engineering calculations

    # Project
    SUBMITTAL = "submittal"          # Submittal packages
    RFI = "rfi"                      # Requests for Information
    CHANGE_ORDER = "change_order"    # Change order documentation
    FIELD_REPORT = "field_report"    # Site/field reports
    INSPECTION = "inspection"        # Inspection reports

    # Compliance
    PERMIT = "permit"                # Building permits
    CERTIFICATE = "certificate"      # Certifications, approvals
    WARRANTY = "warranty"            # Warranty documents
    MSDS = "msds"                    # Material Safety Data Sheets
    TEST_REPORT = "test_report"      # Test/lab reports

    # Reference
    MANUAL = "manual"                # Installation/operation manuals
    CATALOG = "catalog"              # Product catalogs
    REFERENCE = "reference"          # Reference documents
    PHOTO = "photo"                  # Photos, images

    # General
    OTHER = "other"


class DocumentStatus(str, Enum):
    """Lifecycle status of a document."""
    DRAFT = "draft"                  # Work in progress
    PENDING_REVIEW = "pending_review"  # Submitted for review
    IN_REVIEW = "in_review"          # Under review
    APPROVED = "approved"            # Approved/released
    SUPERSEDED = "superseded"        # Replaced by newer version
    OBSOLETE = "obsolete"            # No longer valid
    VOID = "void"                    # Cancelled/voided


class CheckoutStatus(str, Enum):
    """Check-in/check-out status."""
    AVAILABLE = "available"          # Available for checkout
    CHECKED_OUT = "checked_out"      # Checked out for editing
    LOCKED = "locked"                # Locked by system


@dataclass
class Document:
    """
    A document in the PLM system.

    Documents can be engineering drawings, specifications, reports, etc.
    Storage is delegated to orchestrator DMS; PLM tracks metadata and links.
    """
    id: str
    document_number: str             # "DWG-2024-0001", "SPEC-SIDING-001"
    revision: str                    # "A", "B", "1.0", "1.1"
    title: str                       # "Foundation Plan - Sheet S-1"
    description: Optional[str] = None

    document_type: DocumentType = DocumentType.OTHER
    status: DocumentStatus = DocumentStatus.DRAFT

    # File reference (DMS path)
    storage_path: Optional[str] = None   # Path in orchestrator DMS
    file_name: Optional[str] = None      # Original filename
    file_size: Optional[int] = None      # Bytes
    file_hash: Optional[str] = None      # SHA-256 for integrity
    mime_type: Optional[str] = None      # application/pdf, etc.

    # Classification
    category: Optional[str] = None       # "Structural", "MEP", "Civil"
    discipline: Optional[str] = None     # "Architecture", "Structural", etc.
    project_id: Optional[str] = None     # Associated project

    # Check-in/check-out
    checkout_status: CheckoutStatus = CheckoutStatus.AVAILABLE
    checked_out_by: Optional[str] = None
    checked_out_at: Optional[datetime] = None
    checkout_notes: Optional[str] = None

    # Lifecycle
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    released_by: Optional[str] = None
    released_at: Optional[datetime] = None
    superseded_by: Optional[str] = None  # ID of superseding document

    # Metadata
    attributes: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

    @property
    def full_document_number(self) -> str:
        """Document number with revision."""
        return f"{self.document_number}-{self.revision}"

    def can_checkout(self) -> bool:
        """Check if document can be checked out."""
        return (
            self.checkout_status == CheckoutStatus.AVAILABLE
            and self.status not in [DocumentStatus.OBSOLETE, DocumentStatus.VOID]
        )

    def can_checkin(self, user_id: str) -> bool:
        """Check if user can check in the document."""
        return (
            self.checkout_status == CheckoutStatus.CHECKED_OUT
            and self.checked_out_by == user_id
        )

    def can_release(self) -> bool:
        """Check if document can be released."""
        return self.status in [DocumentStatus.DRAFT, DocumentStatus.PENDING_REVIEW, DocumentStatus.IN_REVIEW]

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "document_number": self.document_number,
            "revision": self.revision,
            "full_document_number": self.full_document_number,
            "title": self.title,
            "description": self.description,
            "document_type": self.document_type.value,
            "status": self.status.value,
            "storage_path": self.storage_path,
            "file_name": self.file_name,
            "file_size": self.file_size,
            "checkout_status": self.checkout_status.value,
            "checked_out_by": self.checked_out_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "released_at": self.released_at.isoformat() if self.released_at else None,
        }


@dataclass
class DocumentVersion:
    """
    A specific version of a document.

    Tracks full history with checksums for integrity verification.
    """
    id: str
    document_id: str
    version_number: int              # Sequential: 1, 2, 3
    revision: str                    # Matches document revision at time of version

    # File snapshot
    storage_path: str                # Path at this version
    file_hash: str                   # SHA-256 at this version
    file_size: int                   # Size at this version

    # Change tracking
    change_summary: Optional[str] = None
    change_order_id: Optional[str] = None  # ECO if change-controlled

    # Timestamps
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None

    # Metadata snapshot
    attributes: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class DocumentLink:
    """
    Links a document to other PLM entities.

    Documents can be linked to parts, BOMs, ECOs, projects.
    """
    id: str
    document_id: str

    # Link target (one of these)
    part_id: Optional[str] = None
    bom_id: Optional[str] = None
    eco_id: Optional[str] = None
    project_id: Optional[str] = None

    # Link metadata
    link_type: str = "reference"     # "reference", "primary", "attachment"
    description: Optional[str] = None

    created_by: Optional[str] = None
    created_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


def increment_document_revision(current: str) -> str:
    """
    Increment a document revision string.

    "A" -> "B", "Z" -> "AA", "1.0" -> "1.1"
    """
    if current.replace(".", "").isdigit():
        # Numeric revision (1.0 -> 1.1)
        parts = current.split(".")
        parts[-1] = str(int(parts[-1]) + 1)
        return ".".join(parts)
    else:
        # Alpha revision (A -> B)
        if current == "Z":
            return "AA"
        elif current.endswith("Z"):
            return current[:-1] + "AA"
        else:
            return current[:-1] + chr(ord(current[-1]) + 1)
