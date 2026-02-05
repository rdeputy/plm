"""
Supplier Management Models (AML/AVL)

Approved Manufacturer List and Approved Vendor List per part.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional


class ApprovalStatus(str, Enum):
    """Supplier/manufacturer approval status."""
    PENDING = "pending"
    APPROVED = "approved"
    CONDITIONAL = "conditional"     # Approved with conditions
    SUSPENDED = "suspended"
    DISQUALIFIED = "disqualified"
    EXPIRED = "expired"


class SupplierTier(str, Enum):
    """Supplier classification tier."""
    STRATEGIC = "strategic"         # Key long-term partners
    PREFERRED = "preferred"         # Primary suppliers
    APPROVED = "approved"           # Qualified suppliers
    PROVISIONAL = "provisional"     # Under evaluation
    RESTRICTED = "restricted"       # Limited use only


class QualificationStatus(str, Enum):
    """Part qualification status with supplier."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    QUALIFIED = "qualified"
    FAILED = "failed"
    EXPIRED = "expired"


@dataclass
class Manufacturer:
    """
    A manufacturer who produces parts.

    Used in the Approved Manufacturer List (AML).
    """
    id: str
    manufacturer_code: str          # "MFR-001"
    name: str

    # Contact
    address: str = ""
    country: str = ""
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    website: Optional[str] = None

    # Classification
    status: ApprovalStatus = ApprovalStatus.PENDING

    # Qualifications
    certifications: list[str] = field(default_factory=list)  # ISO 9001, AS9100, etc.
    cage_code: Optional[str] = None  # Commercial and Government Entity code
    duns_number: Optional[str] = None

    # Capabilities
    capabilities: list[str] = field(default_factory=list)
    specialties: list[str] = field(default_factory=list)

    # Audit info
    last_audit_date: Optional[date] = None
    next_audit_date: Optional[date] = None
    audit_score: Optional[int] = None  # 0-100

    # Lifecycle
    created_at: Optional[datetime] = None
    approved_date: Optional[date] = None
    approved_by: Optional[str] = None

    notes: str = ""

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "manufacturer_code": self.manufacturer_code,
            "name": self.name,
            "country": self.country,
            "status": self.status.value,
            "certifications": self.certifications,
            "cage_code": self.cage_code,
            "last_audit_date": self.last_audit_date.isoformat() if self.last_audit_date else None,
            "audit_score": self.audit_score,
        }


@dataclass
class Vendor:
    """
    A vendor/distributor who supplies parts.

    Used in the Approved Vendor List (AVL).
    """
    id: str
    vendor_code: str                # "VND-001"
    name: str

    # Contact
    address: str = ""
    country: str = ""
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    website: Optional[str] = None

    # Classification
    status: ApprovalStatus = ApprovalStatus.PENDING
    tier: SupplierTier = SupplierTier.APPROVED

    # Commercial terms
    payment_terms: str = ""         # "Net 30"
    currency: str = "USD"
    minimum_order: Decimal = Decimal("0")

    # Performance
    on_time_delivery_rate: Optional[float] = None
    quality_rating: Optional[float] = None
    lead_time_days: Optional[int] = None

    # Qualifications
    certifications: list[str] = field(default_factory=list)
    duns_number: Optional[str] = None

    # Lifecycle
    created_at: Optional[datetime] = None
    approved_date: Optional[date] = None
    approved_by: Optional[str] = None

    notes: str = ""

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "vendor_code": self.vendor_code,
            "name": self.name,
            "country": self.country,
            "status": self.status.value,
            "tier": self.tier.value,
            "on_time_delivery_rate": self.on_time_delivery_rate,
            "quality_rating": self.quality_rating,
            "lead_time_days": self.lead_time_days,
        }


@dataclass
class ApprovedManufacturer:
    """
    AML entry - approved manufacturer for a specific part.
    """
    id: str
    part_id: str
    part_number: str
    manufacturer_id: str
    manufacturer_name: str

    # Manufacturer's part number
    manufacturer_part_number: str = ""

    # Status
    status: ApprovalStatus = ApprovalStatus.PENDING
    qualification_status: QualificationStatus = QualificationStatus.NOT_STARTED

    # Preference
    preference_rank: int = 1        # 1 = primary, 2 = secondary, etc.
    is_primary: bool = False

    # Qualification
    qualification_date: Optional[date] = None
    qualification_report: Optional[str] = None
    qualification_expires: Optional[date] = None

    # Lifecycle
    created_at: Optional[datetime] = None
    created_by: Optional[str] = None
    approved_by: Optional[str] = None
    approved_date: Optional[date] = None

    notes: str = ""

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "part_id": self.part_id,
            "part_number": self.part_number,
            "manufacturer_id": self.manufacturer_id,
            "manufacturer_name": self.manufacturer_name,
            "manufacturer_part_number": self.manufacturer_part_number,
            "status": self.status.value,
            "qualification_status": self.qualification_status.value,
            "preference_rank": self.preference_rank,
            "is_primary": self.is_primary,
        }


@dataclass
class ApprovedVendor:
    """
    AVL entry - approved vendor for a specific part.
    """
    id: str
    part_id: str
    part_number: str
    vendor_id: str
    vendor_name: str

    # Vendor's part number (may differ from manufacturer PN)
    vendor_part_number: str = ""

    # Status
    status: ApprovalStatus = ApprovalStatus.PENDING

    # Preference
    preference_rank: int = 1
    is_primary: bool = False

    # Commercial
    unit_price: Decimal = Decimal("0")
    currency: str = "USD"
    minimum_order_qty: Decimal = Decimal("1")
    lead_time_days: int = 0
    price_valid_until: Optional[date] = None

    # Performance for this part
    on_time_delivery_rate: Optional[float] = None
    quality_reject_rate: Optional[float] = None

    # Lifecycle
    created_at: Optional[datetime] = None
    created_by: Optional[str] = None
    approved_by: Optional[str] = None
    approved_date: Optional[date] = None

    notes: str = ""

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "part_id": self.part_id,
            "part_number": self.part_number,
            "vendor_id": self.vendor_id,
            "vendor_name": self.vendor_name,
            "vendor_part_number": self.vendor_part_number,
            "status": self.status.value,
            "preference_rank": self.preference_rank,
            "unit_price": float(self.unit_price),
            "currency": self.currency,
            "lead_time_days": self.lead_time_days,
        }


@dataclass
class PartSourceMatrix:
    """
    Sourcing summary for a part showing all approved sources.
    """
    part_id: str
    part_number: str

    manufacturers: list[dict] = field(default_factory=list)
    vendors: list[dict] = field(default_factory=list)

    has_single_source: bool = False
    total_sources: int = 0
    primary_source: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "part_id": self.part_id,
            "part_number": self.part_number,
            "manufacturers": self.manufacturers,
            "vendors": self.vendors,
            "has_single_source": self.has_single_source,
            "total_sources": self.total_sources,
            "primary_source": self.primary_source,
        }
