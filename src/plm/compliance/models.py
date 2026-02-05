"""
Compliance Management Models

Regulatory compliance tracking (RoHS, REACH, conflict minerals, etc.)
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Optional


class RegulationType(str, Enum):
    """Types of regulations."""
    ROHS = "rohs"                   # Restriction of Hazardous Substances
    REACH = "reach"                 # EU chemical regulation
    CONFLICT_MINERALS = "conflict_minerals"  # Dodd-Frank Section 1502
    WEEE = "weee"                   # Waste Electrical and Electronic Equipment
    TSCA = "tsca"                   # Toxic Substances Control Act
    PROP65 = "prop65"               # California Proposition 65
    CPSIA = "cpsia"                 # Consumer Product Safety Improvement Act
    EXPORT_CONTROL = "export_control"  # ITAR, EAR
    COUNTRY_OF_ORIGIN = "country_of_origin"
    CUSTOM = "custom"               # Custom/internal regulation


class ComplianceStatus(str, Enum):
    """Compliance declaration status."""
    UNKNOWN = "unknown"
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    EXEMPT = "exempt"
    PENDING_REVIEW = "pending_review"
    PENDING_DATA = "pending_data"   # Awaiting supplier data
    NOT_APPLICABLE = "not_applicable"


class CertificateStatus(str, Enum):
    """Certificate validity status."""
    DRAFT = "draft"
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"


class SubstanceCategory(str, Enum):
    """Categories of restricted substances."""
    LEAD = "lead"
    MERCURY = "mercury"
    CADMIUM = "cadmium"
    CHROMIUM_VI = "chromium_vi"
    PBB = "pbb"                     # Polybrominated biphenyls
    PBDE = "pbde"                   # Polybrominated diphenyl ethers
    PHTHALATES = "phthalates"
    SVHC = "svhc"                   # Substances of Very High Concern
    OTHER = "other"


@dataclass
class Regulation:
    """
    A regulation that products must comply with.
    """
    id: str
    regulation_code: str            # "ROHS-2011/65/EU"
    name: str
    regulation_type: RegulationType

    description: str = ""
    authority: str = ""             # Regulating body
    effective_date: Optional[date] = None
    version: str = ""

    # Applicability
    regions: list[str] = field(default_factory=list)  # "EU", "US", "CA"
    product_categories: list[str] = field(default_factory=list)
    exemptions: list[str] = field(default_factory=list)

    # Reference
    reference_url: Optional[str] = None
    reference_document: Optional[str] = None

    is_active: bool = True
    created_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "regulation_code": self.regulation_code,
            "name": self.name,
            "regulation_type": self.regulation_type.value,
            "authority": self.authority,
            "regions": self.regions,
            "effective_date": self.effective_date.isoformat() if self.effective_date else None,
            "is_active": self.is_active,
        }


@dataclass
class SubstanceDeclaration:
    """
    Declaration of a substance in a part.
    """
    id: str
    part_id: str
    part_number: str

    # Substance info
    substance_name: str
    cas_number: Optional[str] = None  # Chemical Abstracts Service number
    category: SubstanceCategory = SubstanceCategory.OTHER

    # Concentration
    concentration_ppm: Optional[Decimal] = None
    concentration_percent: Optional[Decimal] = None
    threshold_ppm: Optional[Decimal] = None
    above_threshold: bool = False

    # Location
    component: str = ""             # Where in the part
    homogeneous_material: str = ""  # Specific material

    # Source
    source: str = ""                # "supplier declaration", "testing"
    source_document: Optional[str] = None
    declaration_date: Optional[date] = None

    created_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "part_id": self.part_id,
            "part_number": self.part_number,
            "substance_name": self.substance_name,
            "cas_number": self.cas_number,
            "category": self.category.value,
            "concentration_ppm": float(self.concentration_ppm) if self.concentration_ppm else None,
            "above_threshold": self.above_threshold,
        }


@dataclass
class ComplianceDeclaration:
    """
    Compliance status of a part for a specific regulation.
    """
    id: str
    part_id: str
    part_number: str
    regulation_id: str
    regulation_code: str

    # Status
    status: ComplianceStatus = ComplianceStatus.UNKNOWN

    # Details
    exemption_code: Optional[str] = None  # If exempt
    exemption_expiry: Optional[date] = None
    notes: str = ""

    # Evidence
    certificate_id: Optional[str] = None
    test_report_id: Optional[str] = None
    supplier_declaration: Optional[str] = None

    # Lifecycle
    declared_by: Optional[str] = None
    declared_date: Optional[date] = None
    verified_by: Optional[str] = None
    verified_date: Optional[date] = None
    expires: Optional[date] = None

    created_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "part_id": self.part_id,
            "part_number": self.part_number,
            "regulation_code": self.regulation_code,
            "status": self.status.value,
            "exemption_code": self.exemption_code,
            "declared_date": self.declared_date.isoformat() if self.declared_date else None,
            "expires": self.expires.isoformat() if self.expires else None,
        }


@dataclass
class ComplianceCertificate:
    """
    Certificate documenting compliance.
    """
    id: str
    certificate_number: str
    regulation_id: str
    regulation_code: str

    # Scope
    part_ids: list[str] = field(default_factory=list)
    product_family: Optional[str] = None

    # Certificate details
    status: CertificateStatus = CertificateStatus.DRAFT
    issue_date: Optional[date] = None
    expiry_date: Optional[date] = None
    issued_by: str = ""             # Certifying body or internal
    certificate_url: Optional[str] = None

    # Attachments
    attachments: list[str] = field(default_factory=list)

    created_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

    @property
    def is_valid(self) -> bool:
        if self.status != CertificateStatus.ACTIVE:
            return False
        if self.expiry_date and self.expiry_date < date.today():
            return False
        return True

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "certificate_number": self.certificate_number,
            "regulation_code": self.regulation_code,
            "status": self.status.value,
            "issue_date": self.issue_date.isoformat() if self.issue_date else None,
            "expiry_date": self.expiry_date.isoformat() if self.expiry_date else None,
            "issued_by": self.issued_by,
            "is_valid": self.is_valid,
            "part_count": len(self.part_ids),
        }


@dataclass
class ConflictMineralDeclaration:
    """
    Conflict mineral (3TG) declaration for a part.

    3TG = Tin, Tantalum, Tungsten, Gold
    """
    id: str
    part_id: str
    part_number: str

    # 3TG content
    contains_tin: bool = False
    contains_tantalum: bool = False
    contains_tungsten: bool = False
    contains_gold: bool = False

    # Sourcing
    conflict_free: Optional[bool] = None
    smelter_list: list[str] = field(default_factory=list)
    countries_of_origin: list[str] = field(default_factory=list)

    # Declaration
    cmrt_version: Optional[str] = None  # Conflict Minerals Reporting Template
    cmrt_document: Optional[str] = None
    declaration_date: Optional[date] = None
    declared_by: Optional[str] = None

    created_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

    @property
    def contains_3tg(self) -> bool:
        return any([self.contains_tin, self.contains_tantalum,
                   self.contains_tungsten, self.contains_gold])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "part_id": self.part_id,
            "part_number": self.part_number,
            "contains_3tg": self.contains_3tg,
            "conflict_free": self.conflict_free,
            "contains": {
                "tin": self.contains_tin,
                "tantalum": self.contains_tantalum,
                "tungsten": self.contains_tungsten,
                "gold": self.contains_gold,
            },
            "declaration_date": self.declaration_date.isoformat() if self.declaration_date else None,
        }


@dataclass
class PartComplianceStatus:
    """
    Overall compliance status for a part across all regulations.
    """
    part_id: str
    part_number: str

    # Overall status
    overall_compliant: bool = True
    has_issues: bool = False
    pending_review: int = 0

    # By regulation
    declarations: list[dict] = field(default_factory=list)
    substances: list[dict] = field(default_factory=list)
    conflict_minerals: Optional[dict] = None

    # Expiring soon
    expiring_30_days: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "part_id": self.part_id,
            "part_number": self.part_number,
            "overall_compliant": self.overall_compliant,
            "has_issues": self.has_issues,
            "pending_review": self.pending_review,
            "declarations": self.declarations,
            "conflict_minerals": self.conflict_minerals,
            "expiring_30_days": self.expiring_30_days,
        }
