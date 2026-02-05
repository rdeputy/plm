"""
Warranty Management Models

Data structures for warranty registration, claims, and RMAs.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Optional


class WarrantyType(str, Enum):
    """Types of warranty coverage."""
    STANDARD = "standard"           # Basic manufacturer warranty
    EXTENDED = "extended"           # Purchased extended warranty
    LIMITED = "limited"             # Limited coverage (parts only, etc.)
    LIFETIME = "lifetime"           # Lifetime warranty
    PRO_RATA = "pro_rata"          # Prorated based on usage/age


class WarrantyStatus(str, Enum):
    """Warranty registration status."""
    PENDING = "pending"             # Awaiting activation
    ACTIVE = "active"               # Currently valid
    EXPIRED = "expired"             # Past end date
    VOIDED = "voided"               # Cancelled/invalidated
    TRANSFERRED = "transferred"     # Ownership transferred


class ClaimStatus(str, Enum):
    """Warranty claim status."""
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    DENIED = "denied"
    IN_PROGRESS = "in_progress"     # Repair/replacement underway
    COMPLETED = "completed"
    CLOSED = "closed"


class ClaimType(str, Enum):
    """Type of warranty claim."""
    DEFECT = "defect"               # Manufacturing defect
    FAILURE = "failure"             # Component failure
    DAMAGE = "damage"               # Damage (may not be covered)
    MISSING_PARTS = "missing_parts"
    COSMETIC = "cosmetic"
    PERFORMANCE = "performance"     # Not meeting specs


class RMAStatus(str, Enum):
    """Return Merchandise Authorization status."""
    ISSUED = "issued"               # RMA created, awaiting shipment
    SHIPPED = "shipped"             # Customer shipped item
    RECEIVED = "received"           # Item received at facility
    INSPECTING = "inspecting"       # Under inspection
    REPAIRING = "repairing"
    REPAIRED = "repaired"
    REPLACING = "replacing"
    SHIPPING_BACK = "shipping_back"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class DispositionAction(str, Enum):
    """RMA disposition actions."""
    REPAIR = "repair"               # Fix and return
    REPLACE = "replace"             # Send replacement
    REFUND = "refund"               # Issue refund
    CREDIT = "credit"               # Issue credit
    NO_FAULT_FOUND = "no_fault_found"  # Return as-is
    OUT_OF_WARRANTY = "out_of_warranty"
    CUSTOMER_DAMAGE = "customer_damage"
    SCRAP = "scrap"                 # Unrepairable


class FailureCategory(str, Enum):
    """Failure categorization for analysis."""
    DESIGN = "design"               # Design flaw
    MANUFACTURING = "manufacturing" # Production defect
    MATERIAL = "material"           # Material/component issue
    ASSEMBLY = "assembly"           # Assembly error
    SHIPPING = "shipping"           # Shipping damage
    INSTALLATION = "installation"   # Improper installation
    MISUSE = "misuse"              # Customer misuse
    WEAR = "wear"                   # Normal wear
    ENVIRONMENTAL = "environmental" # Environmental factors
    UNKNOWN = "unknown"


@dataclass
class WarrantyRegistration:
    """
    Warranty registration for a serialized product.

    Created when product is sold/delivered to end customer.
    """
    id: str
    registration_number: str        # "WR-2024-0001"

    # Product identification
    part_id: str
    part_number: str
    serial_number: str
    lot_number: Optional[str] = None

    # Customer info
    customer_id: Optional[str] = None
    customer_name: str = ""
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_address: Optional[str] = None

    # Sales info
    purchase_date: Optional[date] = None
    purchase_order: Optional[str] = None
    invoice_number: Optional[str] = None
    sales_channel: Optional[str] = None     # dealer, direct, distributor
    dealer_id: Optional[str] = None

    # Warranty terms
    warranty_type: WarrantyType = WarrantyType.STANDARD
    status: WarrantyStatus = WarrantyStatus.ACTIVE
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    terms: str = ""                         # Coverage description
    exclusions: str = ""                    # What's not covered

    # Extended warranty
    extended_warranty: bool = False
    extended_end_date: Optional[date] = None
    extended_terms: str = ""

    # Transfer history
    transferred_from: Optional[str] = None
    transfer_date: Optional[date] = None

    # Metadata
    created_at: Optional[datetime] = None
    created_by: Optional[str] = None
    notes: str = ""
    attachments: list[str] = field(default_factory=list)

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.start_date is None:
            self.start_date = date.today()

    @property
    def is_active(self) -> bool:
        """Check if warranty is currently valid."""
        if self.status != WarrantyStatus.ACTIVE:
            return False
        today = date.today()
        effective_end = self.extended_end_date if self.extended_warranty else self.end_date
        if effective_end and today > effective_end:
            return False
        return True

    @property
    def days_remaining(self) -> Optional[int]:
        """Days remaining on warranty."""
        if not self.is_active:
            return 0
        effective_end = self.extended_end_date if self.extended_warranty else self.end_date
        if effective_end:
            return (effective_end - date.today()).days
        return None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "registration_number": self.registration_number,
            "part_number": self.part_number,
            "serial_number": self.serial_number,
            "customer_name": self.customer_name,
            "warranty_type": self.warranty_type.value,
            "status": self.status.value,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "is_active": self.is_active,
            "days_remaining": self.days_remaining,
            "extended_warranty": self.extended_warranty,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


@dataclass
class WarrantyClaim:
    """
    Warranty claim filed by customer.

    Documents the issue and tracks resolution.
    """
    id: str
    claim_number: str               # "WC-2024-0001"

    # Link to registration
    warranty_id: str
    registration_number: str

    # Product info (denormalized for quick access)
    part_id: str
    part_number: str
    serial_number: str

    # Claim details
    claim_type: ClaimType = ClaimType.DEFECT
    status: ClaimStatus = ClaimStatus.DRAFT
    priority: str = "medium"        # low, medium, high, critical

    # Problem description
    title: str = ""
    description: str = ""
    failure_date: Optional[date] = None
    reported_date: Optional[date] = None

    # Contact for this claim
    contact_name: str = ""
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None

    # Review
    reviewed_by: Optional[str] = None
    reviewed_date: Optional[datetime] = None
    review_notes: str = ""

    # Decision
    decision: Optional[str] = None          # approved, denied, partial
    decision_reason: str = ""
    decision_by: Optional[str] = None
    decision_date: Optional[datetime] = None

    # Resolution
    resolution: str = ""
    resolution_date: Optional[datetime] = None

    # Linked records
    rma_id: Optional[str] = None
    ncr_id: Optional[str] = None            # Links to quality module

    # Costs
    estimated_cost: Decimal = Decimal("0")
    actual_cost: Decimal = Decimal("0")
    labor_cost: Decimal = Decimal("0")
    parts_cost: Decimal = Decimal("0")
    shipping_cost: Decimal = Decimal("0")

    # Lifecycle
    created_at: Optional[datetime] = None
    created_by: Optional[str] = None
    closed_at: Optional[datetime] = None
    closed_by: Optional[str] = None

    # Attachments (photos, docs)
    attachments: list[str] = field(default_factory=list)

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.reported_date is None:
            self.reported_date = date.today()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "claim_number": self.claim_number,
            "warranty_id": self.warranty_id,
            "part_number": self.part_number,
            "serial_number": self.serial_number,
            "claim_type": self.claim_type.value,
            "status": self.status.value,
            "priority": self.priority,
            "title": self.title,
            "description": self.description,
            "decision": self.decision,
            "rma_id": self.rma_id,
            "ncr_id": self.ncr_id,
            "total_cost": float(self.actual_cost),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


@dataclass
class RMA:
    """
    Return Merchandise Authorization.

    Manages the physical return, inspection, and disposition
    of products under warranty claims.
    """
    id: str
    rma_number: str                 # "RMA-2024-0001"

    # Linked claim
    claim_id: str
    claim_number: str

    # Product info
    part_id: str
    part_number: str
    serial_number: str
    quantity: int = 1

    # Status
    status: RMAStatus = RMAStatus.ISSUED

    # Shipping to facility
    ship_to_address: str = ""
    carrier_to: Optional[str] = None
    tracking_to: Optional[str] = None
    shipped_date: Optional[date] = None
    received_date: Optional[date] = None
    received_by: Optional[str] = None

    # Inspection
    condition_received: str = ""
    inspection_notes: str = ""
    inspected_by: Optional[str] = None
    inspected_date: Optional[datetime] = None

    # Failure analysis
    failure_confirmed: bool = False
    failure_category: Optional[FailureCategory] = None
    failure_description: str = ""
    root_cause: str = ""

    # Disposition
    disposition: Optional[DispositionAction] = None
    disposition_notes: str = ""
    disposition_by: Optional[str] = None
    disposition_date: Optional[datetime] = None

    # Replacement (if applicable)
    replacement_serial: Optional[str] = None
    replacement_part_id: Optional[str] = None

    # Shipping back to customer
    ship_from_address: str = ""
    carrier_from: Optional[str] = None
    tracking_from: Optional[str] = None
    shipped_back_date: Optional[date] = None

    # Refund/credit (if applicable)
    refund_amount: Decimal = Decimal("0")
    credit_amount: Decimal = Decimal("0")
    credit_memo: Optional[str] = None

    # Costs
    repair_labor_cost: Decimal = Decimal("0")
    repair_parts_cost: Decimal = Decimal("0")
    shipping_cost: Decimal = Decimal("0")

    # Lifecycle
    created_at: Optional[datetime] = None
    created_by: Optional[str] = None
    completed_at: Optional[datetime] = None

    # Attachments (inspection photos, etc.)
    attachments: list[str] = field(default_factory=list)

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

    @property
    def total_cost(self) -> Decimal:
        return self.repair_labor_cost + self.repair_parts_cost + self.shipping_cost

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "rma_number": self.rma_number,
            "claim_id": self.claim_id,
            "claim_number": self.claim_number,
            "part_number": self.part_number,
            "serial_number": self.serial_number,
            "status": self.status.value,
            "failure_confirmed": self.failure_confirmed,
            "failure_category": self.failure_category.value if self.failure_category else None,
            "disposition": self.disposition.value if self.disposition else None,
            "replacement_serial": self.replacement_serial,
            "total_cost": float(self.total_cost),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


@dataclass
class WarrantyPolicy:
    """
    Warranty policy template for a part or product family.

    Defines default warranty terms applied at registration.
    """
    id: str
    policy_code: str                # "STD-12M", "EXT-36M"
    name: str

    # Applicability
    part_id: Optional[str] = None           # Specific part
    part_category: Optional[str] = None     # Or category of parts
    product_family: Optional[str] = None    # Or product family

    # Terms
    warranty_type: WarrantyType = WarrantyType.STANDARD
    duration_months: int = 12
    coverage_description: str = ""
    exclusions: str = ""

    # Conditions
    transferable: bool = False
    registration_required: bool = True
    registration_deadline_days: Optional[int] = 30  # Days after purchase

    # Extended warranty options
    extended_available: bool = False
    extended_duration_months: Optional[int] = None
    extended_price: Decimal = Decimal("0")

    # Status
    is_active: bool = True
    effective_date: Optional[date] = None
    expiration_date: Optional[date] = None

    created_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.effective_date is None:
            self.effective_date = date.today()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "policy_code": self.policy_code,
            "name": self.name,
            "warranty_type": self.warranty_type.value,
            "duration_months": self.duration_months,
            "coverage_description": self.coverage_description,
            "transferable": self.transferable,
            "extended_available": self.extended_available,
            "is_active": self.is_active,
        }


@dataclass
class WarrantyMetrics:
    """Aggregated warranty metrics for reporting."""
    # Registration stats
    total_registrations: int = 0
    active_warranties: int = 0
    expiring_30_days: int = 0

    # Claim stats
    total_claims: int = 0
    open_claims: int = 0
    claims_this_month: int = 0
    approval_rate: float = 0.0
    avg_resolution_days: float = 0.0

    # RMA stats
    total_rmas: int = 0
    open_rmas: int = 0
    avg_turnaround_days: float = 0.0

    # Failure analysis
    top_failure_categories: list[dict] = field(default_factory=list)
    top_failing_parts: list[dict] = field(default_factory=list)

    # Costs
    total_warranty_cost: Decimal = Decimal("0")
    avg_claim_cost: Decimal = Decimal("0")
    cost_by_category: dict[str, Decimal] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "registrations": {
                "total": self.total_registrations,
                "active": self.active_warranties,
                "expiring_30_days": self.expiring_30_days,
            },
            "claims": {
                "total": self.total_claims,
                "open": self.open_claims,
                "this_month": self.claims_this_month,
                "approval_rate": self.approval_rate,
                "avg_resolution_days": self.avg_resolution_days,
            },
            "rmas": {
                "total": self.total_rmas,
                "open": self.open_rmas,
                "avg_turnaround_days": self.avg_turnaround_days,
            },
            "failures": {
                "top_categories": self.top_failure_categories,
                "top_parts": self.top_failing_parts,
            },
            "costs": {
                "total": float(self.total_warranty_cost),
                "avg_per_claim": float(self.avg_claim_cost),
            },
        }
