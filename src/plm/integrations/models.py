"""
PLM-MRP Integration Models

Data transfer objects for synchronizing PLM data with MRP system.
Matches the TypeScript types in @mrp/plm package.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Optional


class SyncStatus(str, Enum):
    """Status of sync operation."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class SyncDirection(str, Enum):
    """Direction of data flow."""
    PLM_TO_MRP = "plm_to_mrp"
    MRP_TO_PLM = "mrp_to_plm"
    BIDIRECTIONAL = "bidirectional"


class ChangeAction(str, Enum):
    """Type of change for sync."""
    ADD = "add"
    REVISE = "revise"
    DELETE = "delete"
    REPLACE = "replace"


# =============================================================================
# Item Master Sync (PLM → MRP)
# =============================================================================

@dataclass
class ItemMasterSync:
    """
    Item master data for MRP sync.

    Sent when parts are released in PLM.
    """
    # Identification
    item_id: str
    item_number: str                # Part number
    revision: str

    # Description
    description: str
    short_description: str = ""

    # Classification
    item_type: str = "purchased"    # purchased, manufactured, phantom
    commodity_code: Optional[str] = None
    product_family: Optional[str] = None

    # Units
    uom: str = "EA"
    uom_conversion: dict[str, Decimal] = field(default_factory=dict)

    # Inventory settings
    lot_controlled: bool = False
    serial_controlled: bool = False
    shelf_life_days: Optional[int] = None

    # Planning
    lead_time_days: int = 0
    safety_stock: Decimal = Decimal("0")
    minimum_order_qty: Decimal = Decimal("1")
    order_multiple: Decimal = Decimal("1")

    # Costing
    standard_cost: Decimal = Decimal("0")
    currency: str = "USD"
    cost_type: str = "standard"     # standard, average, fifo, lifo

    # Status
    status: str = "active"          # active, inactive, obsolete
    effectivity_date: Optional[date] = None
    obsolete_date: Optional[date] = None

    # Sourcing
    make_buy: str = "buy"           # make, buy
    primary_supplier_id: Optional[str] = None
    primary_manufacturer_id: Optional[str] = None

    # PLM metadata
    plm_released_at: Optional[datetime] = None
    plm_released_by: Optional[str] = None
    eco_number: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "itemId": self.item_id,
            "itemNumber": self.item_number,
            "revision": self.revision,
            "description": self.description,
            "itemType": self.item_type,
            "commodityCode": self.commodity_code,
            "uom": self.uom,
            "lotControlled": self.lot_controlled,
            "serialControlled": self.serial_controlled,
            "leadTimeDays": self.lead_time_days,
            "safetyStock": float(self.safety_stock),
            "standardCost": float(self.standard_cost),
            "currency": self.currency,
            "status": self.status,
            "makeBuy": self.make_buy,
            "effectivityDate": self.effectivity_date.isoformat() if self.effectivity_date else None,
            "plmReleasedAt": self.plm_released_at.isoformat() if self.plm_released_at else None,
            "ecoNumber": self.eco_number,
        }


# =============================================================================
# BOM Sync (PLM → MRP)
# =============================================================================

@dataclass
class BOMLineSync:
    """Single BOM line for MRP sync."""
    line_id: str
    line_number: int

    # Component
    component_item_id: str
    component_item_number: str
    component_revision: str

    # Quantity
    quantity: Decimal
    uom: str = "EA"

    # Usage
    find_number: Optional[str] = None
    reference_designator: Optional[str] = None

    # Effectivity
    effectivity_start: Optional[date] = None
    effectivity_end: Optional[date] = None

    # Flags
    is_phantom: bool = False
    is_optional: bool = False
    scrap_percent: Decimal = Decimal("0")

    def to_dict(self) -> dict:
        return {
            "lineId": self.line_id,
            "lineNumber": self.line_number,
            "componentItemId": self.component_item_id,
            "componentItemNumber": self.component_item_number,
            "componentRevision": self.component_revision,
            "quantity": float(self.quantity),
            "uom": self.uom,
            "findNumber": self.find_number,
            "isPhantom": self.is_phantom,
            "scrapPercent": float(self.scrap_percent),
        }


@dataclass
class BOMSync:
    """
    BOM data for MRP sync.

    Sent when BOMs are released in PLM.
    """
    # Identification
    bom_id: str
    bom_number: str
    revision: str

    # Parent item
    parent_item_id: str
    parent_item_number: str
    parent_revision: str

    # Type
    bom_type: str = "manufacturing"  # manufacturing, engineering, planning
    alternate_bom: Optional[str] = None

    # Lines
    lines: list[BOMLineSync] = field(default_factory=list)

    # Effectivity
    effectivity_date: Optional[date] = None
    expiration_date: Optional[date] = None

    # Quantity basis
    base_quantity: Decimal = Decimal("1")

    # Status
    status: str = "released"

    # PLM metadata
    plm_released_at: Optional[datetime] = None
    plm_released_by: Optional[str] = None
    eco_number: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "bomId": self.bom_id,
            "bomNumber": self.bom_number,
            "revision": self.revision,
            "parentItemId": self.parent_item_id,
            "parentItemNumber": self.parent_item_number,
            "parentRevision": self.parent_revision,
            "bomType": self.bom_type,
            "lines": [line.to_dict() for line in self.lines],
            "effectivityDate": self.effectivity_date.isoformat() if self.effectivity_date else None,
            "baseQuantity": float(self.base_quantity),
            "status": self.status,
            "plmReleasedAt": self.plm_released_at.isoformat() if self.plm_released_at else None,
            "ecoNumber": self.eco_number,
        }


# =============================================================================
# ECO Sync (PLM → MRP)
# =============================================================================

@dataclass
class ECOLineSync:
    """ECO line item for MRP notification."""
    line_id: str
    line_number: int

    # What's changing
    change_action: ChangeAction

    # Items affected
    item_id: str
    item_number: str
    old_revision: Optional[str] = None
    new_revision: Optional[str] = None

    # BOM changes
    bom_id: Optional[str] = None
    old_quantity: Optional[Decimal] = None
    new_quantity: Optional[Decimal] = None

    # For replacements
    replacement_item_id: Optional[str] = None
    replacement_item_number: Optional[str] = None

    # Description
    change_description: str = ""

    def to_dict(self) -> dict:
        return {
            "lineId": self.line_id,
            "lineNumber": self.line_number,
            "changeAction": self.change_action.value,
            "itemId": self.item_id,
            "itemNumber": self.item_number,
            "oldRevision": self.old_revision,
            "newRevision": self.new_revision,
            "bomId": self.bom_id,
            "oldQuantity": float(self.old_quantity) if self.old_quantity else None,
            "newQuantity": float(self.new_quantity) if self.new_quantity else None,
            "replacementItemId": self.replacement_item_id,
            "changeDescription": self.change_description,
        }


@dataclass
class ECONotification:
    """
    ECO notification for MRP.

    Sent when ECOs are approved/implemented in PLM.
    """
    # Identification
    eco_id: str
    eco_number: str
    title: str

    # Classification
    change_type: str
    priority: str
    reason: str

    # Effectivity
    effectivity_type: str           # immediate, date, serial_number
    effective_date: Optional[date] = None
    effective_serial: Optional[str] = None

    # Inventory disposition
    old_inventory_disposition: str = "use_as_is"  # use_as_is, rework, scrap

    # Lines
    line_items: list[ECOLineSync] = field(default_factory=list)

    # Affected
    affected_items: list[str] = field(default_factory=list)
    affected_boms: list[str] = field(default_factory=list)

    # Status
    status: str = "approved"

    # Costing impact
    material_cost_change: Optional[Decimal] = None

    # PLM metadata
    approved_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    implemented_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            "ecoId": self.eco_id,
            "ecoNumber": self.eco_number,
            "title": self.title,
            "changeType": self.change_type,
            "priority": self.priority,
            "reason": self.reason,
            "effectivityType": self.effectivity_type,
            "effectiveDate": self.effective_date.isoformat() if self.effective_date else None,
            "oldInventoryDisposition": self.old_inventory_disposition,
            "lineItems": [line.to_dict() for line in self.line_items],
            "affectedItems": self.affected_items,
            "affectedBoms": self.affected_boms,
            "status": self.status,
            "materialCostChange": float(self.material_cost_change) if self.material_cost_change else None,
            "approvedAt": self.approved_at.isoformat() if self.approved_at else None,
            "implementedAt": self.implemented_at.isoformat() if self.implemented_at else None,
        }


# =============================================================================
# Cost Updates (MRP → PLM)
# =============================================================================

@dataclass
class CostUpdate:
    """
    Cost update from MRP to PLM.

    MRP sends actual costs back to PLM for variance tracking.
    """
    item_id: str
    item_number: str

    # Costs
    standard_cost: Decimal
    actual_cost: Optional[Decimal] = None
    average_cost: Optional[Decimal] = None
    last_cost: Optional[Decimal] = None

    # Breakdown
    material_cost: Decimal = Decimal("0")
    labor_cost: Decimal = Decimal("0")
    overhead_cost: Decimal = Decimal("0")
    subcontract_cost: Decimal = Decimal("0")

    # Currency
    currency: str = "USD"

    # Period
    effective_date: date = field(default_factory=date.today)

    # Source
    source_system: str = "mrp"

    def to_dict(self) -> dict:
        return {
            "itemId": self.item_id,
            "itemNumber": self.item_number,
            "standardCost": float(self.standard_cost),
            "actualCost": float(self.actual_cost) if self.actual_cost else None,
            "materialCost": float(self.material_cost),
            "laborCost": float(self.labor_cost),
            "overheadCost": float(self.overhead_cost),
            "currency": self.currency,
            "effectiveDate": self.effective_date.isoformat(),
        }


# =============================================================================
# Inventory Status (MRP → PLM)
# =============================================================================

@dataclass
class InventoryStatus:
    """
    Inventory status from MRP.

    MRP sends stock levels for PLM visibility.
    """
    item_id: str
    item_number: str

    # Quantities
    on_hand: Decimal = Decimal("0")
    allocated: Decimal = Decimal("0")
    available: Decimal = Decimal("0")
    on_order: Decimal = Decimal("0")
    in_transit: Decimal = Decimal("0")

    # By location (optional)
    locations: list[dict] = field(default_factory=list)

    # Dates
    next_receipt_date: Optional[date] = None
    next_receipt_qty: Decimal = Decimal("0")

    # As of
    as_of: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "itemId": self.item_id,
            "itemNumber": self.item_number,
            "onHand": float(self.on_hand),
            "allocated": float(self.allocated),
            "available": float(self.available),
            "onOrder": float(self.on_order),
            "nextReceiptDate": self.next_receipt_date.isoformat() if self.next_receipt_date else None,
            "asOf": self.as_of.isoformat(),
        }


# =============================================================================
# Sync Log
# =============================================================================

@dataclass
class SyncLogEntry:
    """Log entry for sync operations."""
    id: str
    timestamp: datetime

    # Operation
    direction: SyncDirection
    entity_type: str                # item, bom, eco
    entity_id: str
    entity_number: str

    # Status
    status: SyncStatus

    # Details
    action: str = ""                # create, update, delete
    message: str = ""
    error: Optional[str] = None

    # Request/response
    request_payload: Optional[dict] = None
    response_payload: Optional[dict] = None

    # Duration
    duration_ms: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "direction": self.direction.value,
            "entityType": self.entity_type,
            "entityId": self.entity_id,
            "entityNumber": self.entity_number,
            "status": self.status.value,
            "action": self.action,
            "message": self.message,
            "error": self.error,
            "durationMs": self.duration_ms,
        }


# =============================================================================
# Sync Configuration
# =============================================================================

@dataclass
class MRPIntegrationConfig:
    """Configuration for MRP integration."""
    # Connection
    mrp_base_url: str = "http://localhost:3000"
    api_key: Optional[str] = None
    timeout_seconds: int = 30

    # Sync settings
    auto_sync_items: bool = True
    auto_sync_boms: bool = True
    auto_sync_ecos: bool = True

    # Retry settings
    max_retries: int = 3
    retry_delay_seconds: int = 5

    # Webhooks
    webhook_enabled: bool = True
    webhook_secret: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "mrpBaseUrl": self.mrp_base_url,
            "autoSyncItems": self.auto_sync_items,
            "autoSyncBoms": self.auto_sync_boms,
            "autoSyncEcos": self.auto_sync_ecos,
            "webhookEnabled": self.webhook_enabled,
        }
