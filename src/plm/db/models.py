"""
SQLAlchemy ORM Models

Database models for all PLM entities.
Maps to the dataclass models in each module.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

# Import enums from domain models
from ..parts.models import PartStatus, PartType, UnitOfMeasure
from ..boms.models import BOMType, Effectivity
from ..changes.models import ChangeReason, ChangeType, ChangeUrgency, ECOStatus
from ..inventory.models import TransactionType
from ..procurement.models import POStatus
from ..documents.models import DocumentType, DocumentStatus, CheckoutStatus
from ..ipc.models import EffectivityType


# =============================================================================
# Part Models
# =============================================================================


class PartModel(Base):
    """Part/component ORM model."""

    __tablename__ = "parts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    part_number: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    revision: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)

    part_type: Mapped[PartType] = mapped_column(
        Enum(PartType), default=PartType.COMPONENT
    )
    status: Mapped[PartStatus] = mapped_column(
        Enum(PartStatus), default=PartStatus.DRAFT, index=True
    )

    # Classification
    category: Mapped[Optional[str]] = mapped_column(String(100))
    csi_code: Mapped[Optional[str]] = mapped_column(String(20), index=True)
    uniformat_code: Mapped[Optional[str]] = mapped_column(String(20))

    # Physical properties
    unit_of_measure: Mapped[UnitOfMeasure] = mapped_column(
        Enum(UnitOfMeasure), default=UnitOfMeasure.EACH
    )
    unit_weight: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    unit_volume: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))

    # Cost
    unit_cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    cost_currency: Mapped[str] = mapped_column(String(3), default="USD")
    cost_effective_date: Mapped[Optional[date]] = mapped_column(Date)

    # Procurement
    manufacturer: Mapped[Optional[str]] = mapped_column(String(255))
    manufacturer_pn: Mapped[Optional[str]] = mapped_column(String(100))
    vendor: Mapped[Optional[str]] = mapped_column(String(255))
    lead_time_days: Mapped[Optional[int]] = mapped_column(Integer)
    min_order_qty: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    order_multiple: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))

    # Design files
    model_file: Mapped[Optional[str]] = mapped_column(String(500))
    drawing_file: Mapped[Optional[str]] = mapped_column(String(500))
    spec_file: Mapped[Optional[str]] = mapped_column(String(500))

    # Lifecycle
    created_by: Mapped[Optional[str]] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    released_by: Mapped[Optional[str]] = mapped_column(String(100))
    released_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    obsoleted_by: Mapped[Optional[str]] = mapped_column(String(100))
    obsoleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Metadata (JSON)
    attributes: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    tags: Mapped[Optional[list]] = mapped_column(JSON, default=list)

    # Relationships
    revisions: Mapped[list["PartRevisionModel"]] = relationship(
        back_populates="part", cascade="all, delete-orphan"
    )
    bom_items: Mapped[list["BOMItemModel"]] = relationship(back_populates="part")
    inventory_items: Mapped[list["InventoryItemModel"]] = relationship(
        back_populates="part"
    )

    @property
    def full_part_number(self) -> str:
        return f"{self.part_number}-{self.revision}"


class PartRevisionModel(Base):
    """Part revision history."""

    __tablename__ = "part_revisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    part_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("parts.id"), nullable=False, index=True
    )
    revision: Mapped[str] = mapped_column(String(20), nullable=False)
    previous_revision: Mapped[Optional[str]] = mapped_column(String(20))
    change_order_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("change_orders.id")
    )

    change_summary: Mapped[str] = mapped_column(Text, default="")
    change_details: Mapped[Optional[str]] = mapped_column(Text)

    status: Mapped[PartStatus] = mapped_column(
        Enum(PartStatus), default=PartStatus.DRAFT
    )
    approved_by: Mapped[Optional[str]] = mapped_column(String(100))
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    approval_notes: Mapped[Optional[str]] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    released_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Relationships
    part: Mapped["PartModel"] = relationship(back_populates="revisions")
    change_order: Mapped[Optional["ChangeOrderModel"]] = relationship()


# =============================================================================
# BOM Models
# =============================================================================


class BOMModel(Base):
    """Bill of Materials ORM model."""

    __tablename__ = "boms"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    bom_number: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    revision: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)

    parent_part_id: Mapped[str] = mapped_column(String(36), index=True)
    parent_part_revision: Mapped[str] = mapped_column(String(20))

    bom_type: Mapped[BOMType] = mapped_column(
        Enum(BOMType), default=BOMType.ENGINEERING
    )
    effectivity: Mapped[Effectivity] = mapped_column(
        Enum(Effectivity), default=Effectivity.AS_DESIGNED
    )

    effective_from: Mapped[Optional[date]] = mapped_column(Date)
    effective_to: Mapped[Optional[date]] = mapped_column(Date)

    status: Mapped[PartStatus] = mapped_column(
        Enum(PartStatus), default=PartStatus.DRAFT, index=True
    )

    created_by: Mapped[Optional[str]] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    released_by: Mapped[Optional[str]] = mapped_column(String(100))
    released_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    project_id: Mapped[Optional[str]] = mapped_column(String(36), index=True)

    # Relationships
    items: Mapped[list["BOMItemModel"]] = relationship(
        back_populates="bom", cascade="all, delete-orphan"
    )

    @property
    def full_bom_number(self) -> str:
        return f"{self.bom_number}-{self.revision}"


class BOMItemModel(Base):
    """BOM line item ORM model."""

    __tablename__ = "bom_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    bom_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("boms.id"), nullable=False, index=True
    )
    part_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("parts.id"), nullable=False, index=True
    )
    part_number: Mapped[str] = mapped_column(String(100), nullable=False)
    part_revision: Mapped[str] = mapped_column(String(20), nullable=False)

    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    unit_of_measure: Mapped[UnitOfMeasure] = mapped_column(
        Enum(UnitOfMeasure), default=UnitOfMeasure.EACH
    )

    find_number: Mapped[int] = mapped_column(Integer, default=0)
    reference_designator: Mapped[str] = mapped_column(String(100), default="")
    location: Mapped[Optional[str]] = mapped_column(String(255))
    notes: Mapped[Optional[str]] = mapped_column(Text)

    is_optional: Mapped[bool] = mapped_column(Boolean, default=False)
    option_code: Mapped[Optional[str]] = mapped_column(String(50))
    alternate_parts: Mapped[Optional[list]] = mapped_column(JSON, default=list)

    has_sub_bom: Mapped[bool] = mapped_column(Boolean, default=False)
    low_level_code: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    bom: Mapped["BOMModel"] = relationship(back_populates="items")
    part: Mapped["PartModel"] = relationship(back_populates="bom_items")


# =============================================================================
# Change Management Models
# =============================================================================


class ChangeOrderModel(Base):
    """Engineering Change Order ORM model."""

    __tablename__ = "change_orders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    eco_number: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")

    reason: Mapped[ChangeReason] = mapped_column(
        Enum(ChangeReason), default=ChangeReason.CUSTOMER_REQUEST
    )
    urgency: Mapped[ChangeUrgency] = mapped_column(
        Enum(ChangeUrgency), default=ChangeUrgency.STANDARD
    )

    project_id: Mapped[Optional[str]] = mapped_column(String(36), index=True)
    submission_id: Mapped[Optional[str]] = mapped_column(String(36))

    affected_parts: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    affected_boms: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    affected_documents: Mapped[Optional[list]] = mapped_column(JSON, default=list)

    status: Mapped[ECOStatus] = mapped_column(
        Enum(ECOStatus), default=ECOStatus.DRAFT, index=True
    )
    submitted_by: Mapped[Optional[str]] = mapped_column(String(100))
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    required_approvals: Mapped[Optional[list]] = mapped_column(JSON, default=list)

    implementation_date: Mapped[Optional[date]] = mapped_column(Date)
    implemented_by: Mapped[Optional[str]] = mapped_column(String(100))
    implementation_notes: Mapped[Optional[str]] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Relationships
    changes: Mapped[list["ChangeModel"]] = relationship(
        back_populates="change_order", cascade="all, delete-orphan"
    )
    approvals: Mapped[list["ApprovalModel"]] = relationship(
        back_populates="change_order", cascade="all, delete-orphan"
    )
    impact_analysis: Mapped[Optional["ImpactAnalysisModel"]] = relationship(
        back_populates="change_order", uselist=False, cascade="all, delete-orphan"
    )


class ChangeModel(Base):
    """Individual change within an ECO."""

    __tablename__ = "changes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    eco_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("change_orders.id"), nullable=False, index=True
    )

    change_type: Mapped[ChangeType] = mapped_column(Enum(ChangeType), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False)

    field_name: Mapped[Optional[str]] = mapped_column(String(100))
    old_value: Mapped[Optional[str]] = mapped_column(Text)
    new_value: Mapped[Optional[str]] = mapped_column(Text)
    replaced_by_id: Mapped[Optional[str]] = mapped_column(String(36))

    justification: Mapped[str] = mapped_column(Text, default="")
    notes: Mapped[Optional[str]] = mapped_column(Text)

    # Relationships
    change_order: Mapped["ChangeOrderModel"] = relationship(back_populates="changes")


class ApprovalModel(Base):
    """Approval decision on an ECO."""

    __tablename__ = "approvals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    eco_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("change_orders.id"), nullable=False, index=True
    )

    approver_id: Mapped[str] = mapped_column(String(36), nullable=False)
    approver_name: Mapped[str] = mapped_column(String(255), nullable=False)
    approver_role: Mapped[str] = mapped_column(String(100), nullable=False)

    decision: Mapped[str] = mapped_column(String(50), nullable=False)
    conditions: Mapped[Optional[str]] = mapped_column(Text)
    comments: Mapped[Optional[str]] = mapped_column(Text)

    decided_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    signature_file: Mapped[Optional[str]] = mapped_column(String(500))

    # Relationships
    change_order: Mapped["ChangeOrderModel"] = relationship(back_populates="approvals")


class ImpactAnalysisModel(Base):
    """Impact analysis for an ECO."""

    __tablename__ = "impact_analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    eco_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("change_orders.id"), nullable=False, unique=True
    )

    analyzed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    analyzed_by: Mapped[Optional[str]] = mapped_column(String(100))

    material_cost_delta: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0")
    )
    labor_cost_delta: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0")
    )
    total_cost_delta: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0")
    )

    schedule_delta_days: Mapped[int] = mapped_column(Integer, default=0)
    critical_path_affected: Mapped[bool] = mapped_column(Boolean, default=False)

    arc_resubmission_required: Mapped[bool] = mapped_column(Boolean, default=False)
    permit_revision_required: Mapped[bool] = mapped_column(Boolean, default=False)
    variance_required: Mapped[bool] = mapped_column(Boolean, default=False)
    compliance_notes: Mapped[str] = mapped_column(Text, default="")

    affected_purchase_orders: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    affected_work_orders: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    affected_inspections: Mapped[Optional[list]] = mapped_column(JSON, default=list)

    risk_level: Mapped[str] = mapped_column(String(20), default="low")
    risk_notes: Mapped[str] = mapped_column(Text, default="")
    recommendations: Mapped[Optional[list]] = mapped_column(JSON, default=list)

    # Relationships
    change_order: Mapped["ChangeOrderModel"] = relationship(
        back_populates="impact_analysis"
    )


# =============================================================================
# Inventory Models
# =============================================================================


class InventoryLocationModel(Base):
    """Inventory location ORM model."""

    __tablename__ = "inventory_locations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    location_type: Mapped[str] = mapped_column(String(50), nullable=False)
    address: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    project_id: Mapped[Optional[str]] = mapped_column(String(36), index=True)
    vendor_id: Mapped[Optional[str]] = mapped_column(String(36), index=True)

    # Relationships
    inventory_items: Mapped[list["InventoryItemModel"]] = relationship(
        back_populates="location"
    )


class InventoryItemModel(Base):
    """Inventory record per part/location."""

    __tablename__ = "inventory_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    part_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("parts.id"), nullable=False, index=True
    )
    part_number: Mapped[str] = mapped_column(String(100), nullable=False)
    location_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("inventory_locations.id"), nullable=False, index=True
    )

    on_hand: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("0"))
    allocated: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("0"))
    on_order: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("0"))

    unit_cost: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("0"))
    total_value: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("0"))

    last_count_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    last_receipt_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    last_issue_date: Mapped[Optional[datetime]] = mapped_column(DateTime)

    reorder_point: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    reorder_qty: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))

    # Relationships
    part: Mapped["PartModel"] = relationship(back_populates="inventory_items")
    location: Mapped["InventoryLocationModel"] = relationship(
        back_populates="inventory_items"
    )

    @property
    def available(self) -> Decimal:
        return self.on_hand - self.allocated

    @property
    def projected(self) -> Decimal:
        return self.on_hand + self.on_order - self.allocated


class InventoryTransactionModel(Base):
    """Inventory transaction (immutable audit trail)."""

    __tablename__ = "inventory_transactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    transaction_type: Mapped[TransactionType] = mapped_column(
        Enum(TransactionType), nullable=False
    )
    part_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    part_number: Mapped[str] = mapped_column(String(100), nullable=False)

    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    unit_of_measure: Mapped[str] = mapped_column(String(10), nullable=False)

    location_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    from_location_id: Mapped[Optional[str]] = mapped_column(String(36))
    to_location_id: Mapped[Optional[str]] = mapped_column(String(36))

    po_id: Mapped[Optional[str]] = mapped_column(String(36), index=True)
    project_id: Mapped[Optional[str]] = mapped_column(String(36), index=True)
    work_order_id: Mapped[Optional[str]] = mapped_column(String(36))

    unit_cost: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("0"))
    total_cost: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("0"))

    transaction_date: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, index=True
    )
    created_by: Mapped[str] = mapped_column(String(100), default="")
    notes: Mapped[Optional[str]] = mapped_column(Text)

    lot_number: Mapped[Optional[str]] = mapped_column(String(100))
    serial_number: Mapped[Optional[str]] = mapped_column(String(100))


# =============================================================================
# Procurement Models
# =============================================================================


class VendorModel(Base):
    """Vendor/supplier ORM model."""

    __tablename__ = "vendors"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    vendor_code: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)

    address: Mapped[Optional[str]] = mapped_column(Text)
    city: Mapped[Optional[str]] = mapped_column(String(100))
    state: Mapped[Optional[str]] = mapped_column(String(50))
    postal_code: Mapped[Optional[str]] = mapped_column(String(20))
    country: Mapped[str] = mapped_column(String(50), default="USA")
    phone: Mapped[Optional[str]] = mapped_column(String(50))
    email: Mapped[Optional[str]] = mapped_column(String(255))
    website: Mapped[Optional[str]] = mapped_column(String(500))

    contacts: Mapped[Optional[list]] = mapped_column(JSON, default=list)

    payment_terms: Mapped[str] = mapped_column(String(50), default="Net 30")
    freight_terms: Mapped[str] = mapped_column(String(50), default="FOB Origin")
    minimum_order: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))

    categories: Mapped[Optional[list]] = mapped_column(JSON, default=list)

    on_time_rate: Mapped[float] = mapped_column(Numeric(5, 2), default=0.0)
    quality_rate: Mapped[float] = mapped_column(Numeric(5, 2), default=0.0)
    avg_lead_time_days: Mapped[int] = mapped_column(Integer, default=0)

    is_approved: Mapped[bool] = mapped_column(Boolean, default=True)
    insurance_expiry: Mapped[Optional[date]] = mapped_column(Date)
    w9_on_file: Mapped[bool] = mapped_column(Boolean, default=False)
    certifications: Mapped[Optional[list]] = mapped_column(JSON, default=list)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    # Relationships
    purchase_orders: Mapped[list["PurchaseOrderModel"]] = relationship(
        back_populates="vendor"
    )
    price_agreements: Mapped[list["PriceAgreementModel"]] = relationship(
        back_populates="vendor"
    )


class PriceAgreementModel(Base):
    """Vendor price agreement ORM model."""

    __tablename__ = "price_agreements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    vendor_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("vendors.id"), nullable=False, index=True
    )
    part_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    part_number: Mapped[str] = mapped_column(String(100), nullable=False)

    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD")

    effective_date: Mapped[date] = mapped_column(Date, default=date.today)
    expiration_date: Mapped[Optional[date]] = mapped_column(Date)

    min_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("1"))
    price_breaks: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)

    contract_number: Mapped[Optional[str]] = mapped_column(String(50))
    notes: Mapped[Optional[str]] = mapped_column(Text)

    # Relationships
    vendor: Mapped["VendorModel"] = relationship(back_populates="price_agreements")


class PurchaseOrderModel(Base):
    """Purchase order ORM model."""

    __tablename__ = "purchase_orders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    po_number: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    vendor_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("vendors.id"), nullable=False, index=True
    )
    vendor_name: Mapped[str] = mapped_column(String(255), nullable=False)

    status: Mapped[POStatus] = mapped_column(
        Enum(POStatus), default=POStatus.DRAFT, index=True
    )

    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    tax: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    shipping: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))

    order_date: Mapped[Optional[date]] = mapped_column(Date)
    required_date: Mapped[Optional[date]] = mapped_column(Date)
    promised_date: Mapped[Optional[date]] = mapped_column(Date)

    ship_to_location_id: Mapped[Optional[str]] = mapped_column(String(36))
    ship_to_address: Mapped[Optional[str]] = mapped_column(Text)
    freight_terms: Mapped[str] = mapped_column(String(50), default="FOB Origin")
    payment_terms: Mapped[str] = mapped_column(String(50), default="Net 30")

    project_id: Mapped[Optional[str]] = mapped_column(String(36), index=True)
    requisition_id: Mapped[Optional[str]] = mapped_column(String(36))
    notes: Mapped[Optional[str]] = mapped_column(Text)

    created_by: Mapped[str] = mapped_column(String(100), default="")
    approved_by: Mapped[Optional[str]] = mapped_column(String(100))
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )

    # Relationships
    vendor: Mapped["VendorModel"] = relationship(back_populates="purchase_orders")
    items: Mapped[list["POItemModel"]] = relationship(
        back_populates="purchase_order", cascade="all, delete-orphan"
    )
    receipts: Mapped[list["ReceiptModel"]] = relationship(
        back_populates="purchase_order"
    )


class POItemModel(Base):
    """Purchase order line item."""

    __tablename__ = "po_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    po_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("purchase_orders.id"), nullable=False, index=True
    )
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)

    part_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    part_number: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    unit_of_measure: Mapped[str] = mapped_column(String(10), nullable=False)
    received_quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), default=Decimal("0")
    )

    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("0"))
    extended_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0")
    )

    required_date: Mapped[Optional[date]] = mapped_column(Date)
    promised_date: Mapped[Optional[date]] = mapped_column(Date)

    project_id: Mapped[Optional[str]] = mapped_column(String(36))
    planned_order_id: Mapped[Optional[str]] = mapped_column(String(36))

    is_closed: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    purchase_order: Mapped["PurchaseOrderModel"] = relationship(back_populates="items")

    @property
    def open_quantity(self) -> Decimal:
        return self.quantity - self.received_quantity


class ReceiptModel(Base):
    """Goods receipt ORM model."""

    __tablename__ = "receipts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    receipt_number: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    po_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("purchase_orders.id"), nullable=False, index=True
    )
    po_number: Mapped[str] = mapped_column(String(50), nullable=False)
    vendor_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    receipt_date: Mapped[date] = mapped_column(Date, default=date.today)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    packing_slip: Mapped[Optional[str]] = mapped_column(String(100))
    carrier: Mapped[Optional[str]] = mapped_column(String(100))
    tracking_number: Mapped[Optional[str]] = mapped_column(String(100))

    received_by: Mapped[str] = mapped_column(String(100), default="")
    location_id: Mapped[Optional[str]] = mapped_column(String(36))

    is_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    # Relationships
    purchase_order: Mapped["PurchaseOrderModel"] = relationship(
        back_populates="receipts"
    )
    items: Mapped[list["ReceiptItemModel"]] = relationship(
        back_populates="receipt", cascade="all, delete-orphan"
    )


class ReceiptItemModel(Base):
    """Receipt line item."""

    __tablename__ = "receipt_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    receipt_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("receipts.id"), nullable=False, index=True
    )
    po_item_id: Mapped[str] = mapped_column(String(36), nullable=False)
    part_id: Mapped[str] = mapped_column(String(36), nullable=False)
    part_number: Mapped[str] = mapped_column(String(100), nullable=False)

    quantity_received: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    quantity_accepted: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), default=Decimal("0")
    )
    quantity_rejected: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), default=Decimal("0")
    )
    unit_of_measure: Mapped[str] = mapped_column(String(10), default="EA")

    lot_number: Mapped[Optional[str]] = mapped_column(String(100))
    serial_numbers: Mapped[Optional[list]] = mapped_column(JSON, default=list)

    location_id: Mapped[Optional[str]] = mapped_column(String(36))

    inspection_required: Mapped[bool] = mapped_column(Boolean, default=False)
    inspection_status: Mapped[Optional[str]] = mapped_column(String(50))
    inspection_notes: Mapped[Optional[str]] = mapped_column(Text)

    # Relationships
    receipt: Mapped["ReceiptModel"] = relationship(back_populates="items")


# =============================================================================
# Document Models
# =============================================================================


class DocumentModel(Base):
    """Document ORM model."""

    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    document_number: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    revision: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)

    document_type: Mapped[DocumentType] = mapped_column(
        Enum(DocumentType), default=DocumentType.OTHER
    )
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus), default=DocumentStatus.DRAFT, index=True
    )

    # File reference (DMS path)
    storage_path: Mapped[Optional[str]] = mapped_column(String(1000))
    file_name: Mapped[Optional[str]] = mapped_column(String(255))
    file_size: Mapped[Optional[int]] = mapped_column(Integer)
    file_hash: Mapped[Optional[str]] = mapped_column(String(64))  # SHA-256
    mime_type: Mapped[Optional[str]] = mapped_column(String(100))

    # Classification
    category: Mapped[Optional[str]] = mapped_column(String(100))
    discipline: Mapped[Optional[str]] = mapped_column(String(100))
    project_id: Mapped[Optional[str]] = mapped_column(String(36), index=True)

    # Check-in/check-out
    checkout_status: Mapped[CheckoutStatus] = mapped_column(
        Enum(CheckoutStatus), default=CheckoutStatus.AVAILABLE
    )
    checked_out_by: Mapped[Optional[str]] = mapped_column(String(100))
    checked_out_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    checkout_notes: Mapped[Optional[str]] = mapped_column(Text)

    # Lifecycle
    created_by: Mapped[Optional[str]] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    released_by: Mapped[Optional[str]] = mapped_column(String(100))
    released_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    superseded_by: Mapped[Optional[str]] = mapped_column(String(36))

    # Metadata (JSON)
    attributes: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    tags: Mapped[Optional[list]] = mapped_column(JSON, default=list)

    # Relationships
    versions: Mapped[list["DocumentVersionModel"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    links: Mapped[list["DocumentLinkModel"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )

    @property
    def full_document_number(self) -> str:
        return f"{self.document_number}-{self.revision}"


class DocumentVersionModel(Base):
    """Document version history."""

    __tablename__ = "document_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    revision: Mapped[str] = mapped_column(String(20), nullable=False)

    # File snapshot
    storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)

    # Change tracking
    change_summary: Mapped[Optional[str]] = mapped_column(Text)
    change_order_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("change_orders.id")
    )

    # Timestamps
    created_by: Mapped[Optional[str]] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    # Metadata snapshot
    attributes: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)

    # Relationships
    document: Mapped["DocumentModel"] = relationship(back_populates="versions")
    change_order: Mapped[Optional["ChangeOrderModel"]] = relationship()


class DocumentLinkModel(Base):
    """Document links to PLM entities."""

    __tablename__ = "document_links"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id"), nullable=False, index=True
    )

    # Link targets (one of these)
    part_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("parts.id"), index=True)
    bom_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("boms.id"), index=True)
    eco_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("change_orders.id"), index=True)
    project_id: Mapped[Optional[str]] = mapped_column(String(36), index=True)

    # Link metadata
    link_type: Mapped[str] = mapped_column(String(50), default="reference")
    description: Mapped[Optional[str]] = mapped_column(Text)

    created_by: Mapped[Optional[str]] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    # Relationships
    document: Mapped["DocumentModel"] = relationship(back_populates="links")
    part: Mapped[Optional["PartModel"]] = relationship()
    bom: Mapped[Optional["BOMModel"]] = relationship()
    change_order: Mapped[Optional["ChangeOrderModel"]] = relationship()


# =============================================================================
# IPC Models (Illustrated Parts Catalog)
# =============================================================================


class SupersessionModel(Base):
    """Part supersession/replacement history."""

    __tablename__ = "supersessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # Old part being replaced
    superseded_part_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("parts.id"), nullable=False, index=True
    )
    superseded_part_number: Mapped[str] = mapped_column(String(100), nullable=False)

    # New replacement part
    superseding_part_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("parts.id"), nullable=False, index=True
    )
    superseding_part_number: Mapped[str] = mapped_column(String(100), nullable=False)

    # Supersession details
    supersession_type: Mapped[str] = mapped_column(
        String(50), default="replacement"
    )  # replacement, alternate, upgrade
    is_interchangeable: Mapped[bool] = mapped_column(Boolean, default=True)
    quantity_ratio: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=Decimal("1"))

    # Effectivity
    effective_date: Mapped[Optional[date]] = mapped_column(Date)
    effective_serial: Mapped[Optional[str]] = mapped_column(String(50))

    # Reason
    reason: Mapped[str] = mapped_column(Text, default="")
    change_order_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("change_orders.id")
    )
    notes: Mapped[Optional[str]] = mapped_column(Text)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    created_by: Mapped[Optional[str]] = mapped_column(String(100))

    # Relationships
    superseded_part: Mapped["PartModel"] = relationship(
        foreign_keys=[superseded_part_id],
        backref="superseded_by_records"
    )
    superseding_part: Mapped["PartModel"] = relationship(
        foreign_keys=[superseding_part_id],
        backref="supersedes_records"
    )
    change_order: Mapped[Optional["ChangeOrderModel"]] = relationship()


class EffectivityRangeModel(Base):
    """Effectivity range for parts/BOM items."""

    __tablename__ = "effectivity_ranges"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    effectivity_type: Mapped[EffectivityType] = mapped_column(
        Enum(EffectivityType), nullable=False
    )

    # Serial/lot ranges
    serial_from: Mapped[Optional[str]] = mapped_column(String(50))
    serial_to: Mapped[Optional[str]] = mapped_column(String(50))

    # Date ranges
    date_from: Mapped[Optional[date]] = mapped_column(Date)
    date_to: Mapped[Optional[date]] = mapped_column(Date)

    # Model/config codes (JSON arrays)
    model_codes: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    config_codes: Mapped[Optional[list]] = mapped_column(JSON, default=list)

    # What this applies to
    part_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("parts.id"), index=True
    )
    bom_item_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("bom_items.id"), index=True
    )

    # Display
    display_text: Mapped[str] = mapped_column(String(255), default="All")
    notes: Mapped[Optional[str]] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    # Relationships
    part: Mapped[Optional["PartModel"]] = relationship(
        backref="effectivity_ranges"
    )
    bom_item: Mapped[Optional["BOMItemModel"]] = relationship(
        backref="effectivity_ranges"
    )


class IPCFigureModel(Base):
    """IPC figure (exploded view) linking document to BOM."""

    __tablename__ = "ipc_figures"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id"), nullable=False, index=True
    )
    bom_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("boms.id"), nullable=False, index=True
    )

    figure_number: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)

    # Sheet info
    sheet_number: Mapped[int] = mapped_column(Integer, default=1)
    total_sheets: Mapped[int] = mapped_column(Integer, default=1)

    # View type
    view_type: Mapped[str] = mapped_column(String(50), default="exploded")
    scale: Mapped[Optional[str]] = mapped_column(String(20))

    # Status
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)
    superseded_by: Mapped[Optional[str]] = mapped_column(String(36))

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )

    # Relationships
    document: Mapped["DocumentModel"] = relationship()
    bom: Mapped["BOMModel"] = relationship()
    hotspots: Mapped[list["FigureHotspotModel"]] = relationship(
        back_populates="figure", cascade="all, delete-orphan"
    )


class FigureHotspotModel(Base):
    """Clickable hotspot on an IPC figure."""

    __tablename__ = "figure_hotspots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    figure_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("ipc_figures.id"), nullable=False, index=True
    )
    bom_item_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("bom_items.id"), nullable=False, index=True
    )

    # Callout numbers
    index_number: Mapped[int] = mapped_column(Integer, nullable=False)
    find_number: Mapped[int] = mapped_column(Integer, nullable=False)

    # Position (normalized 0-1)
    x: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False)
    y: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False)

    # Leader line target (optional)
    target_x: Mapped[Optional[float]] = mapped_column(Numeric(6, 4))
    target_y: Mapped[Optional[float]] = mapped_column(Numeric(6, 4))

    # Display
    shape: Mapped[str] = mapped_column(String(20), default="circle")
    size: Mapped[float] = mapped_column(Numeric(4, 3), default=0.02)

    # Denormalized part info
    part_number: Mapped[Optional[str]] = mapped_column(String(100))
    part_name: Mapped[Optional[str]] = mapped_column(String(255))
    quantity: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))

    # Page for multi-page figures
    page_number: Mapped[int] = mapped_column(Integer, default=1)

    notes: Mapped[Optional[str]] = mapped_column(Text)

    # Relationships
    figure: Mapped["IPCFigureModel"] = relationship(back_populates="hotspots")
    bom_item: Mapped["BOMItemModel"] = relationship()
