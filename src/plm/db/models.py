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
from ..documents.models import DocumentType, DocumentStatus, CheckoutStatus
from ..ipc.models import EffectivityType
from ..requirements.models import (
    RequirementType, RequirementStatus, RequirementPriority,
    VerificationMethod, VerificationStatus
)
from ..suppliers.models import ApprovalStatus, SupplierTier, QualificationStatus
from ..compliance.models import (
    RegulationType, ComplianceStatus as ComplianceDeclarationStatus,
    CertificateStatus, SubstanceCategory
)
from ..costing.models import CostType, CostVarianceType, CostEstimateStatus
from ..service_bulletins.models import (
    BulletinType, BulletinStatus, ComplianceStatus as BulletinComplianceStatus
)
from ..projects.models import ProjectStatus, ProjectPhase, MilestoneStatus, DeliverableType
from ..integrations.models import SyncStatus, SyncDirection


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


# =============================================================================
# Requirements Models
# =============================================================================


class RequirementModel(Base):
    """Requirement ORM model."""

    __tablename__ = "requirements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    requirement_number: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)

    requirement_type: Mapped[RequirementType] = mapped_column(
        Enum(RequirementType), default=RequirementType.FUNCTIONAL
    )
    status: Mapped[RequirementStatus] = mapped_column(
        Enum(RequirementStatus), default=RequirementStatus.DRAFT, index=True
    )
    priority: Mapped[RequirementPriority] = mapped_column(
        Enum(RequirementPriority), default=RequirementPriority.MUST_HAVE
    )

    title: Mapped[str] = mapped_column(String(255), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    rationale: Mapped[str] = mapped_column(Text, default="")
    acceptance_criteria: Mapped[str] = mapped_column(Text, default="")

    source: Mapped[str] = mapped_column(String(255), default="")
    source_document: Mapped[Optional[str]] = mapped_column(String(255))
    source_section: Mapped[Optional[str]] = mapped_column(String(100))
    customer_id: Mapped[Optional[str]] = mapped_column(String(36))

    verification_method: Mapped[VerificationMethod] = mapped_column(
        Enum(VerificationMethod), default=VerificationMethod.TEST
    )
    verification_procedure: Mapped[Optional[str]] = mapped_column(String(255))

    parent_id: Mapped[Optional[str]] = mapped_column(String(36), index=True)
    derived_from: Mapped[Optional[list]] = mapped_column(JSON, default=list)

    project_id: Mapped[Optional[str]] = mapped_column(String(36), index=True)
    phase: Mapped[Optional[str]] = mapped_column(String(50))

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    created_by: Mapped[Optional[str]] = mapped_column(String(100))
    approved_by: Mapped[Optional[str]] = mapped_column(String(100))
    approved_date: Mapped[Optional[datetime]] = mapped_column(DateTime)

    tags: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    attachments: Mapped[Optional[list]] = mapped_column(JSON, default=list)


class RequirementLinkModel(Base):
    """Requirement traceability link ORM model."""

    __tablename__ = "requirement_links"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    requirement_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("requirements.id"), nullable=False, index=True
    )

    link_type: Mapped[str] = mapped_column(String(50), nullable=False)  # part, document, test
    target_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    target_number: Mapped[Optional[str]] = mapped_column(String(100))
    target_revision: Mapped[Optional[str]] = mapped_column(String(20))

    relationship: Mapped[str] = mapped_column(String(50), default="implements")
    coverage: Mapped[str] = mapped_column(String(20), default="full")
    coverage_notes: Mapped[str] = mapped_column(Text, default="")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    created_by: Mapped[Optional[str]] = mapped_column(String(100))


class VerificationRecordModel(Base):
    """Verification record ORM model."""

    __tablename__ = "verification_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    verification_number: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)

    requirement_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("requirements.id"), nullable=False, index=True
    )
    requirement_number: Mapped[str] = mapped_column(String(50), nullable=False)

    method: Mapped[VerificationMethod] = mapped_column(Enum(VerificationMethod), nullable=False)
    procedure_id: Mapped[Optional[str]] = mapped_column(String(36))
    procedure_number: Mapped[Optional[str]] = mapped_column(String(100))

    status: Mapped[VerificationStatus] = mapped_column(
        Enum(VerificationStatus), default=VerificationStatus.NOT_STARTED, index=True
    )

    result_summary: Mapped[str] = mapped_column(Text, default="")
    pass_fail: Mapped[Optional[bool]] = mapped_column(Boolean)
    actual_value: Mapped[Optional[str]] = mapped_column(String(255))
    expected_value: Mapped[Optional[str]] = mapped_column(String(255))
    deviation: Mapped[Optional[str]] = mapped_column(Text)

    evidence_documents: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    test_report_id: Mapped[Optional[str]] = mapped_column(String(36))

    verified_by: Mapped[Optional[str]] = mapped_column(String(100))
    verified_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    witness: Mapped[Optional[str]] = mapped_column(String(100))

    approved_by: Mapped[Optional[str]] = mapped_column(String(100))
    approved_date: Mapped[Optional[datetime]] = mapped_column(DateTime)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


# =============================================================================
# Supplier Models (AML/AVL)
# =============================================================================


class ManufacturerModel(Base):
    """Manufacturer ORM model."""

    __tablename__ = "manufacturers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    manufacturer_code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    address: Mapped[str] = mapped_column(Text, default="")
    country: Mapped[str] = mapped_column(String(100), default="")
    contact_name: Mapped[Optional[str]] = mapped_column(String(255))
    contact_email: Mapped[Optional[str]] = mapped_column(String(255))
    contact_phone: Mapped[Optional[str]] = mapped_column(String(50))
    website: Mapped[Optional[str]] = mapped_column(String(500))

    status: Mapped[ApprovalStatus] = mapped_column(
        Enum(ApprovalStatus), default=ApprovalStatus.PENDING, index=True
    )

    certifications: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    cage_code: Mapped[Optional[str]] = mapped_column(String(20))
    duns_number: Mapped[Optional[str]] = mapped_column(String(20))

    capabilities: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    specialties: Mapped[Optional[list]] = mapped_column(JSON, default=list)

    last_audit_date: Mapped[Optional[date]] = mapped_column(Date)
    next_audit_date: Mapped[Optional[date]] = mapped_column(Date)
    audit_score: Mapped[Optional[int]] = mapped_column(Integer)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    approved_date: Mapped[Optional[date]] = mapped_column(Date)
    approved_by: Mapped[Optional[str]] = mapped_column(String(100))

    notes: Mapped[str] = mapped_column(Text, default="")


class SupplierVendorModel(Base):
    """Vendor/distributor ORM model for AVL."""

    __tablename__ = "supplier_vendors"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    vendor_code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    address: Mapped[str] = mapped_column(Text, default="")
    country: Mapped[str] = mapped_column(String(100), default="")
    contact_name: Mapped[Optional[str]] = mapped_column(String(255))
    contact_email: Mapped[Optional[str]] = mapped_column(String(255))
    contact_phone: Mapped[Optional[str]] = mapped_column(String(50))
    website: Mapped[Optional[str]] = mapped_column(String(500))

    status: Mapped[ApprovalStatus] = mapped_column(
        Enum(ApprovalStatus), default=ApprovalStatus.PENDING, index=True
    )
    tier: Mapped[SupplierTier] = mapped_column(
        Enum(SupplierTier), default=SupplierTier.APPROVED
    )

    payment_terms: Mapped[str] = mapped_column(String(50), default="")
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    minimum_order: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))

    on_time_delivery_rate: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    quality_rating: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    lead_time_days: Mapped[Optional[int]] = mapped_column(Integer)

    certifications: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    duns_number: Mapped[Optional[str]] = mapped_column(String(20))

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    approved_date: Mapped[Optional[date]] = mapped_column(Date)
    approved_by: Mapped[Optional[str]] = mapped_column(String(100))

    notes: Mapped[str] = mapped_column(Text, default="")


class ApprovedManufacturerModel(Base):
    """AML entry - approved manufacturer for a part."""

    __tablename__ = "approved_manufacturers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    part_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("parts.id"), nullable=False, index=True
    )
    part_number: Mapped[str] = mapped_column(String(100), nullable=False)
    manufacturer_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("manufacturers.id"), nullable=False, index=True
    )
    manufacturer_name: Mapped[str] = mapped_column(String(255), nullable=False)

    manufacturer_part_number: Mapped[str] = mapped_column(String(100), default="")

    status: Mapped[ApprovalStatus] = mapped_column(
        Enum(ApprovalStatus), default=ApprovalStatus.PENDING, index=True
    )
    qualification_status: Mapped[QualificationStatus] = mapped_column(
        Enum(QualificationStatus), default=QualificationStatus.NOT_STARTED
    )

    preference_rank: Mapped[int] = mapped_column(Integer, default=1)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)

    qualification_date: Mapped[Optional[date]] = mapped_column(Date)
    qualification_report: Mapped[Optional[str]] = mapped_column(String(255))
    qualification_expires: Mapped[Optional[date]] = mapped_column(Date)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    created_by: Mapped[Optional[str]] = mapped_column(String(100))
    approved_by: Mapped[Optional[str]] = mapped_column(String(100))
    approved_date: Mapped[Optional[date]] = mapped_column(Date)

    notes: Mapped[str] = mapped_column(Text, default="")


class ApprovedVendorModel(Base):
    """AVL entry - approved vendor for a part."""

    __tablename__ = "approved_vendors"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    part_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("parts.id"), nullable=False, index=True
    )
    part_number: Mapped[str] = mapped_column(String(100), nullable=False)
    vendor_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("supplier_vendors.id"), nullable=False, index=True
    )
    vendor_name: Mapped[str] = mapped_column(String(255), nullable=False)

    vendor_part_number: Mapped[str] = mapped_column(String(100), default="")

    status: Mapped[ApprovalStatus] = mapped_column(
        Enum(ApprovalStatus), default=ApprovalStatus.PENDING, index=True
    )

    preference_rank: Mapped[int] = mapped_column(Integer, default=1)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)

    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("0"))
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    minimum_order_qty: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("1"))
    lead_time_days: Mapped[int] = mapped_column(Integer, default=0)
    price_valid_until: Mapped[Optional[date]] = mapped_column(Date)

    on_time_delivery_rate: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    quality_reject_rate: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    created_by: Mapped[Optional[str]] = mapped_column(String(100))
    approved_by: Mapped[Optional[str]] = mapped_column(String(100))
    approved_date: Mapped[Optional[date]] = mapped_column(Date)

    notes: Mapped[str] = mapped_column(Text, default="")


# =============================================================================
# Compliance Models
# =============================================================================


class RegulationModel(Base):
    """Regulation ORM model."""

    __tablename__ = "regulations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    regulation_code: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    regulation_type: Mapped[RegulationType] = mapped_column(
        Enum(RegulationType), nullable=False, index=True
    )

    description: Mapped[str] = mapped_column(Text, default="")
    authority: Mapped[str] = mapped_column(String(255), default="")
    effective_date: Mapped[Optional[date]] = mapped_column(Date)
    version: Mapped[str] = mapped_column(String(50), default="")

    regions: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    product_categories: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    exemptions: Mapped[Optional[list]] = mapped_column(JSON, default=list)

    reference_url: Mapped[Optional[str]] = mapped_column(String(500))
    reference_document: Mapped[Optional[str]] = mapped_column(String(255))

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class SubstanceDeclarationModel(Base):
    """Substance declaration ORM model."""

    __tablename__ = "substance_declarations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    part_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("parts.id"), nullable=False, index=True
    )
    part_number: Mapped[str] = mapped_column(String(100), nullable=False)

    substance_name: Mapped[str] = mapped_column(String(255), nullable=False)
    cas_number: Mapped[Optional[str]] = mapped_column(String(50))
    category: Mapped[SubstanceCategory] = mapped_column(
        Enum(SubstanceCategory), default=SubstanceCategory.OTHER
    )

    concentration_ppm: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    concentration_percent: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4))
    threshold_ppm: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    above_threshold: Mapped[bool] = mapped_column(Boolean, default=False)

    component: Mapped[str] = mapped_column(String(255), default="")
    homogeneous_material: Mapped[str] = mapped_column(String(255), default="")

    source: Mapped[str] = mapped_column(String(100), default="")
    source_document: Mapped[Optional[str]] = mapped_column(String(255))
    declaration_date: Mapped[Optional[date]] = mapped_column(Date)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class ComplianceDeclarationModel(Base):
    """Compliance declaration ORM model."""

    __tablename__ = "compliance_declarations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    part_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("parts.id"), nullable=False, index=True
    )
    part_number: Mapped[str] = mapped_column(String(100), nullable=False)
    regulation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("regulations.id"), nullable=False, index=True
    )
    regulation_code: Mapped[str] = mapped_column(String(100), nullable=False)

    status: Mapped[ComplianceDeclarationStatus] = mapped_column(
        Enum(ComplianceDeclarationStatus), default=ComplianceDeclarationStatus.UNKNOWN, index=True
    )

    exemption_code: Mapped[Optional[str]] = mapped_column(String(50))
    exemption_expiry: Mapped[Optional[date]] = mapped_column(Date)
    notes: Mapped[str] = mapped_column(Text, default="")

    certificate_id: Mapped[Optional[str]] = mapped_column(String(36))
    test_report_id: Mapped[Optional[str]] = mapped_column(String(36))
    supplier_declaration: Mapped[Optional[str]] = mapped_column(String(255))

    declared_by: Mapped[Optional[str]] = mapped_column(String(100))
    declared_date: Mapped[Optional[date]] = mapped_column(Date)
    verified_by: Mapped[Optional[str]] = mapped_column(String(100))
    verified_date: Mapped[Optional[date]] = mapped_column(Date)
    expires: Mapped[Optional[date]] = mapped_column(Date)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class ComplianceCertificateModel(Base):
    """Compliance certificate ORM model."""

    __tablename__ = "compliance_certificates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    certificate_number: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    regulation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("regulations.id"), nullable=False, index=True
    )
    regulation_code: Mapped[str] = mapped_column(String(100), nullable=False)

    part_ids: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    product_family: Mapped[Optional[str]] = mapped_column(String(255))

    status: Mapped[CertificateStatus] = mapped_column(
        Enum(CertificateStatus), default=CertificateStatus.DRAFT, index=True
    )
    issue_date: Mapped[Optional[date]] = mapped_column(Date)
    expiry_date: Mapped[Optional[date]] = mapped_column(Date)
    issued_by: Mapped[str] = mapped_column(String(255), default="")
    certificate_url: Mapped[Optional[str]] = mapped_column(String(500))

    attachments: Mapped[Optional[list]] = mapped_column(JSON, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class ConflictMineralDeclarationModel(Base):
    """Conflict mineral (3TG) declaration ORM model."""

    __tablename__ = "conflict_mineral_declarations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    part_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("parts.id"), nullable=False, index=True
    )
    part_number: Mapped[str] = mapped_column(String(100), nullable=False)

    contains_tin: Mapped[bool] = mapped_column(Boolean, default=False)
    contains_tantalum: Mapped[bool] = mapped_column(Boolean, default=False)
    contains_tungsten: Mapped[bool] = mapped_column(Boolean, default=False)
    contains_gold: Mapped[bool] = mapped_column(Boolean, default=False)

    conflict_free: Mapped[Optional[bool]] = mapped_column(Boolean)
    smelter_list: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    countries_of_origin: Mapped[Optional[list]] = mapped_column(JSON, default=list)

    cmrt_version: Mapped[Optional[str]] = mapped_column(String(50))
    cmrt_document: Mapped[Optional[str]] = mapped_column(String(255))
    declaration_date: Mapped[Optional[date]] = mapped_column(Date)
    declared_by: Mapped[Optional[str]] = mapped_column(String(100))

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


# =============================================================================
# Costing Models
# =============================================================================


class PartCostModel(Base):
    """Part cost breakdown ORM model."""

    __tablename__ = "part_costs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    part_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("parts.id"), nullable=False, index=True
    )
    part_number: Mapped[str] = mapped_column(String(100), nullable=False)
    part_revision: Mapped[str] = mapped_column(String(20), default="")

    status: Mapped[CostEstimateStatus] = mapped_column(
        Enum(CostEstimateStatus), default=CostEstimateStatus.DRAFT, index=True
    )

    material_cost: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("0"))
    labor_cost: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("0"))
    overhead_cost: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("0"))
    total_cost: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("0"))

    target_cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    should_cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))

    selling_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    margin_percent: Mapped[Optional[float]] = mapped_column(Numeric(8, 4))

    lot_size: Mapped[int] = mapped_column(Integer, default=1)
    annual_volume: Mapped[Optional[int]] = mapped_column(Integer)

    currency: Mapped[str] = mapped_column(String(3), default="USD")
    exchange_rate: Mapped[Decimal] = mapped_column(Numeric(12, 6), default=Decimal("1"))

    effective_date: Mapped[Optional[date]] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    created_by: Mapped[Optional[str]] = mapped_column(String(100))
    approved_by: Mapped[Optional[str]] = mapped_column(String(100))
    approved_date: Mapped[Optional[datetime]] = mapped_column(DateTime)

    notes: Mapped[str] = mapped_column(Text, default="")


class CostElementModel(Base):
    """Cost element (line item) ORM model."""

    __tablename__ = "cost_elements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    part_cost_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("part_costs.id"), nullable=False, index=True
    )

    cost_type: Mapped[CostType] = mapped_column(Enum(CostType), nullable=False)
    description: Mapped[str] = mapped_column(String(255), default="")

    unit_cost: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("0"))
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("1"))
    extended_cost: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("0"))

    rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    unit_of_measure: Mapped[str] = mapped_column(String(10), default="EA")
    basis: Mapped[str] = mapped_column(String(255), default="")

    source: Mapped[str] = mapped_column(String(100), default="")
    vendor_id: Mapped[Optional[str]] = mapped_column(String(36))
    quote_number: Mapped[Optional[str]] = mapped_column(String(50))
    quote_date: Mapped[Optional[date]] = mapped_column(Date)

    target_cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    variance: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    variance_percent: Mapped[Optional[float]] = mapped_column(Numeric(8, 4))


class CostVarianceModel(Base):
    """Cost variance analysis ORM model."""

    __tablename__ = "cost_variances"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    part_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("parts.id"), nullable=False, index=True
    )
    part_number: Mapped[str] = mapped_column(String(100), nullable=False)
    period: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    standard_cost: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    actual_cost: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    variance: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("0"))
    variance_percent: Mapped[float] = mapped_column(Numeric(8, 4), default=0.0)

    variance_type: Mapped[CostVarianceType] = mapped_column(
        Enum(CostVarianceType), default=CostVarianceType.MATERIAL_PRICE
    )
    favorable: Mapped[bool] = mapped_column(Boolean, default=True)

    root_cause: Mapped[str] = mapped_column(Text, default="")
    corrective_action: Mapped[str] = mapped_column(Text, default="")

    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("1"))
    total_variance: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("0"))

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class ShouldCostAnalysisModel(Base):
    """Should-cost analysis ORM model."""

    __tablename__ = "should_cost_analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    part_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("parts.id"), nullable=False, index=True
    )
    part_number: Mapped[str] = mapped_column(String(100), nullable=False)

    analysis_date: Mapped[date] = mapped_column(Date, default=date.today)
    analyst: Mapped[str] = mapped_column(String(100), default="")
    methodology: Mapped[str] = mapped_column(String(50), default="")

    should_cost: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("0"))

    raw_material: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("0"))
    material_processing: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("0"))
    conversion_cost: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("0"))
    profit_margin: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("0"))
    logistics: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("0"))

    current_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    savings_opportunity: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    savings_percent: Mapped[Optional[float]] = mapped_column(Numeric(8, 4))

    assumptions: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    data_sources: Mapped[Optional[list]] = mapped_column(JSON, default=list)

    notes: Mapped[str] = mapped_column(Text, default="")


# =============================================================================
# Service Bulletin Models
# =============================================================================


class ServiceBulletinModel(Base):
    """Service bulletin ORM model."""

    __tablename__ = "service_bulletins"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    bulletin_number: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)

    bulletin_type: Mapped[BulletinType] = mapped_column(Enum(BulletinType), nullable=False)
    status: Mapped[BulletinStatus] = mapped_column(
        Enum(BulletinStatus), default=BulletinStatus.DRAFT, index=True
    )

    title: Mapped[str] = mapped_column(String(255), default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    description: Mapped[str] = mapped_column(Text, default="")
    reason: Mapped[str] = mapped_column(Text, default="")
    safety_issue: Mapped[bool] = mapped_column(Boolean, default=False)

    action_required: Mapped[str] = mapped_column(Text, default="")
    action_procedure: Mapped[str] = mapped_column(Text, default="")
    estimated_time: Mapped[Optional[str]] = mapped_column(String(50))
    special_tools: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    required_parts: Mapped[Optional[list]] = mapped_column(JSON, default=list)

    affected_parts: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    affected_part_numbers: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    serial_range_start: Mapped[Optional[str]] = mapped_column(String(50))
    serial_range_end: Mapped[Optional[str]] = mapped_column(String(50))
    effectivity_start: Mapped[Optional[date]] = mapped_column(Date)
    effectivity_end: Mapped[Optional[date]] = mapped_column(Date)
    affected_configurations: Mapped[Optional[list]] = mapped_column(JSON, default=list)

    compliance_deadline: Mapped[Optional[date]] = mapped_column(Date)
    flight_hours_limit: Mapped[Optional[int]] = mapped_column(Integer)
    cycles_limit: Mapped[Optional[int]] = mapped_column(Integer)

    related_eco_id: Mapped[Optional[str]] = mapped_column(String(36))
    related_ncr_ids: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    supersedes: Mapped[Optional[str]] = mapped_column(String(50))
    superseded_by: Mapped[Optional[str]] = mapped_column(String(50))

    attachments: Mapped[Optional[list]] = mapped_column(JSON, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    created_by: Mapped[Optional[str]] = mapped_column(String(100))
    approved_by: Mapped[Optional[str]] = mapped_column(String(100))
    approved_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    effective_date: Mapped[Optional[date]] = mapped_column(Date)
    expiry_date: Mapped[Optional[date]] = mapped_column(Date)


class BulletinComplianceModel(Base):
    """Bulletin compliance record ORM model."""

    __tablename__ = "bulletin_compliance"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    bulletin_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("service_bulletins.id"), nullable=False, index=True
    )
    bulletin_number: Mapped[str] = mapped_column(String(50), nullable=False)

    serial_number: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    part_id: Mapped[Optional[str]] = mapped_column(String(36))
    part_number: Mapped[Optional[str]] = mapped_column(String(100))

    status: Mapped[BulletinComplianceStatus] = mapped_column(
        Enum(BulletinComplianceStatus), default=BulletinComplianceStatus.PENDING, index=True
    )

    completed_date: Mapped[Optional[date]] = mapped_column(Date)
    completed_by: Mapped[Optional[str]] = mapped_column(String(100))
    work_order_number: Mapped[Optional[str]] = mapped_column(String(50))
    labor_hours: Mapped[Optional[float]] = mapped_column(Numeric(8, 2))

    parts_used: Mapped[Optional[list]] = mapped_column(JSON, default=list)

    waived: Mapped[bool] = mapped_column(Boolean, default=False)
    waiver_reason: Mapped[Optional[str]] = mapped_column(Text)
    waiver_approved_by: Mapped[Optional[str]] = mapped_column(String(100))
    waiver_expiry: Mapped[Optional[date]] = mapped_column(Date)

    notes: Mapped[str] = mapped_column(Text, default="")
    attachments: Mapped[Optional[list]] = mapped_column(JSON, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class MaintenanceScheduleModel(Base):
    """Maintenance schedule ORM model."""

    __tablename__ = "maintenance_schedules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    schedule_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    part_id: Mapped[Optional[str]] = mapped_column(String(36))
    part_number: Mapped[Optional[str]] = mapped_column(String(100))
    system: Mapped[str] = mapped_column(String(100), default="")
    component: Mapped[str] = mapped_column(String(255), default="")

    interval_type: Mapped[str] = mapped_column(String(20), default="calendar")
    interval_value: Mapped[int] = mapped_column(Integer, default=0)
    interval_unit: Mapped[str] = mapped_column(String(20), default="")

    task_description: Mapped[str] = mapped_column(Text, default="")
    procedure_reference: Mapped[Optional[str]] = mapped_column(String(255))
    estimated_time: Mapped[Optional[str]] = mapped_column(String(50))

    required_parts: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    consumables: Mapped[Optional[list]] = mapped_column(JSON, default=list)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class UnitConfigurationModel(Base):
    """Unit (serialized product) configuration ORM model."""

    __tablename__ = "unit_configurations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    serial_number: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    part_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("parts.id"), nullable=False, index=True
    )
    part_number: Mapped[str] = mapped_column(String(100), nullable=False)

    current_revision: Mapped[str] = mapped_column(String(20), default="")
    configuration_id: Mapped[Optional[str]] = mapped_column(String(36))
    build_date: Mapped[Optional[date]] = mapped_column(Date)
    delivery_date: Mapped[Optional[date]] = mapped_column(Date)

    total_hours: Mapped[float] = mapped_column(Numeric(12, 2), default=0.0)
    total_cycles: Mapped[int] = mapped_column(Integer, default=0)
    last_updated: Mapped[Optional[datetime]] = mapped_column(DateTime)

    owner_id: Mapped[Optional[str]] = mapped_column(String(36))
    owner_name: Mapped[str] = mapped_column(String(255), default="")
    location: Mapped[str] = mapped_column(String(255), default="")

    applied_bulletins: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    pending_bulletins: Mapped[Optional[list]] = mapped_column(JSON, default=list)

    last_maintenance_date: Mapped[Optional[date]] = mapped_column(Date)
    next_maintenance_due: Mapped[Optional[date]] = mapped_column(Date)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


# =============================================================================
# Project Models
# =============================================================================


class ProjectModel(Base):
    """Project ORM model."""

    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_number: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus), default=ProjectStatus.PROPOSED, index=True
    )
    phase: Mapped[ProjectPhase] = mapped_column(
        Enum(ProjectPhase), default=ProjectPhase.CONCEPT
    )
    project_type: Mapped[str] = mapped_column(String(50), default="")

    description: Mapped[str] = mapped_column(Text, default="")
    objectives: Mapped[str] = mapped_column(Text, default="")
    scope: Mapped[str] = mapped_column(Text, default="")

    program_id: Mapped[Optional[str]] = mapped_column(String(36))
    parent_project_id: Mapped[Optional[str]] = mapped_column(String(36))

    customer_id: Mapped[Optional[str]] = mapped_column(String(36))
    customer_name: Mapped[str] = mapped_column(String(255), default="")
    contract_number: Mapped[Optional[str]] = mapped_column(String(100))

    start_date: Mapped[Optional[date]] = mapped_column(Date)
    target_end_date: Mapped[Optional[date]] = mapped_column(Date)
    actual_end_date: Mapped[Optional[date]] = mapped_column(Date)

    budget: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    actual_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    currency: Mapped[str] = mapped_column(String(3), default="USD")

    project_manager_id: Mapped[Optional[str]] = mapped_column(String(36))
    project_manager_name: Mapped[str] = mapped_column(String(255), default="")
    team_members: Mapped[Optional[list]] = mapped_column(JSON, default=list)

    part_ids: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    bom_ids: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    document_ids: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    eco_ids: Mapped[Optional[list]] = mapped_column(JSON, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    created_by: Mapped[Optional[str]] = mapped_column(String(100))
    approved_by: Mapped[Optional[str]] = mapped_column(String(100))
    approved_date: Mapped[Optional[datetime]] = mapped_column(DateTime)

    notes: Mapped[str] = mapped_column(Text, default="")
    tags: Mapped[Optional[list]] = mapped_column(JSON, default=list)


class MilestoneModel(Base):
    """Project milestone ORM model."""

    __tablename__ = "milestones"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id"), nullable=False, index=True
    )
    milestone_number: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    status: Mapped[MilestoneStatus] = mapped_column(
        Enum(MilestoneStatus), default=MilestoneStatus.NOT_STARTED, index=True
    )
    phase: Mapped[Optional[ProjectPhase]] = mapped_column(Enum(ProjectPhase))

    description: Mapped[str] = mapped_column(Text, default="")
    success_criteria: Mapped[str] = mapped_column(Text, default="")

    planned_date: Mapped[Optional[date]] = mapped_column(Date)
    forecast_date: Mapped[Optional[date]] = mapped_column(Date)
    actual_date: Mapped[Optional[date]] = mapped_column(Date)

    sequence: Mapped[int] = mapped_column(Integer, default=0)
    predecessor_ids: Mapped[Optional[list]] = mapped_column(JSON, default=list)

    review_required: Mapped[bool] = mapped_column(Boolean, default=False)
    review_type: Mapped[str] = mapped_column(String(50), default="")
    reviewers: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    review_notes: Mapped[str] = mapped_column(Text, default="")

    deliverable_ids: Mapped[Optional[list]] = mapped_column(JSON, default=list)

    completed_by: Mapped[Optional[str]] = mapped_column(String(100))
    completion_notes: Mapped[str] = mapped_column(Text, default="")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class DeliverableModel(Base):
    """Project deliverable ORM model."""

    __tablename__ = "deliverables"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id"), nullable=False, index=True
    )
    milestone_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("milestones.id"), index=True
    )
    deliverable_number: Mapped[str] = mapped_column(String(50), default="")
    name: Mapped[str] = mapped_column(String(255), default="")

    deliverable_type: Mapped[DeliverableType] = mapped_column(
        Enum(DeliverableType), default=DeliverableType.DOCUMENT
    )

    description: Mapped[str] = mapped_column(Text, default="")
    acceptance_criteria: Mapped[str] = mapped_column(Text, default="")

    status: Mapped[MilestoneStatus] = mapped_column(
        Enum(MilestoneStatus), default=MilestoneStatus.NOT_STARTED, index=True
    )
    percent_complete: Mapped[int] = mapped_column(Integer, default=0)

    due_date: Mapped[Optional[date]] = mapped_column(Date)
    submitted_date: Mapped[Optional[date]] = mapped_column(Date)
    accepted_date: Mapped[Optional[date]] = mapped_column(Date)

    assigned_to: Mapped[Optional[str]] = mapped_column(String(36))
    assigned_name: Mapped[str] = mapped_column(String(255), default="")

    part_id: Mapped[Optional[str]] = mapped_column(String(36))
    document_id: Mapped[Optional[str]] = mapped_column(String(36))
    bom_id: Mapped[Optional[str]] = mapped_column(String(36))

    approved_by: Mapped[Optional[str]] = mapped_column(String(100))
    approval_notes: Mapped[str] = mapped_column(Text, default="")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


# =============================================================================
# Integration Models
# =============================================================================


class SyncLogEntryModel(Base):
    """MRP sync log entry ORM model."""

    __tablename__ = "sync_log_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)

    direction: Mapped[SyncDirection] = mapped_column(Enum(SyncDirection), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    entity_number: Mapped[str] = mapped_column(String(100), nullable=False)

    status: Mapped[SyncStatus] = mapped_column(Enum(SyncStatus), nullable=False, index=True)

    action: Mapped[str] = mapped_column(String(50), default="")
    message: Mapped[str] = mapped_column(Text, default="")
    error: Mapped[Optional[str]] = mapped_column(Text)

    request_payload: Mapped[Optional[dict]] = mapped_column(JSON)
    response_payload: Mapped[Optional[dict]] = mapped_column(JSON)

    duration_ms: Mapped[Optional[int]] = mapped_column(Integer)
