"""
Inventory Management Models

Tracks inventory levels, locations, and transactions.
Provides real-time stock visibility for MRP planning.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional


class TransactionType(Enum):
    """Types of inventory transactions."""

    RECEIPT = "receipt"  # Goods received from PO
    ISSUE = "issue"  # Issued to job/project
    TRANSFER = "transfer"  # Between locations
    ADJUSTMENT = "adjustment"  # Physical count adjustment
    RETURN = "return"  # Returned from job
    SCRAP = "scrap"  # Scrapped/damaged
    RESERVE = "reserve"  # Reserved for job (soft allocation)
    UNRESERVE = "unreserve"  # Released reservation


@dataclass
class InventoryLocation:
    """
    A physical or logical inventory location.

    Examples: Warehouse, Job Site, Trailer, Vendor Consignment
    """

    id: str
    name: str
    location_type: str  # warehouse, jobsite, trailer, consignment
    address: Optional[str] = None
    is_active: bool = True

    # For job sites
    project_id: Optional[str] = None

    # For consignment
    vendor_id: Optional[str] = None


@dataclass
class InventoryItem:
    """
    Inventory record for a part at a location.

    Tracks on-hand, allocated, and available quantities.
    """

    id: str
    part_id: str
    part_number: str
    location_id: str

    # Quantities
    on_hand: Decimal = Decimal("0")  # Physical quantity
    allocated: Decimal = Decimal("0")  # Reserved for jobs
    on_order: Decimal = Decimal("0")  # Open PO quantity

    # Computed
    @property
    def available(self) -> Decimal:
        """Quantity available for new allocation."""
        return self.on_hand - self.allocated

    @property
    def projected(self) -> Decimal:
        """Projected quantity (on_hand + on_order - allocated)."""
        return self.on_hand + self.on_order - self.allocated

    # Cost tracking
    unit_cost: Decimal = Decimal("0")  # Average or last cost
    total_value: Decimal = Decimal("0")

    # Tracking
    last_count_date: Optional[datetime] = None
    last_receipt_date: Optional[datetime] = None
    last_issue_date: Optional[datetime] = None

    # Reorder info (can override part defaults)
    reorder_point: Optional[Decimal] = None
    reorder_qty: Optional[Decimal] = None

    def needs_reorder(self) -> bool:
        """Check if item needs reordering."""
        if self.reorder_point is None:
            return False
        return self.available <= self.reorder_point


@dataclass
class InventoryTransaction:
    """
    A single inventory transaction (movement).

    Immutable record of inventory changes for audit trail.
    """

    id: str
    transaction_type: TransactionType
    part_id: str
    part_number: str

    # Quantity (positive for receipts, negative for issues)
    quantity: Decimal
    unit_of_measure: str

    # Location(s)
    location_id: str  # Primary location
    from_location_id: Optional[str] = None  # For transfers
    to_location_id: Optional[str] = None  # For transfers

    # Reference documents
    po_id: Optional[str] = None  # Purchase order
    project_id: Optional[str] = None  # Job/project
    work_order_id: Optional[str] = None  # Work order

    # Cost
    unit_cost: Decimal = Decimal("0")
    total_cost: Decimal = Decimal("0")

    # Tracking
    transaction_date: datetime = field(default_factory=datetime.now)
    created_by: str = ""
    notes: Optional[str] = None

    # Lot/Serial tracking (optional)
    lot_number: Optional[str] = None
    serial_number: Optional[str] = None


@dataclass
class StockLevel:
    """
    Aggregated stock level for reporting.

    Can be per-part, per-location, or per-project.
    """

    part_id: str
    part_number: str
    part_name: str

    # Totals across locations
    total_on_hand: Decimal = Decimal("0")
    total_allocated: Decimal = Decimal("0")
    total_on_order: Decimal = Decimal("0")
    total_available: Decimal = Decimal("0")

    # Value
    total_value: Decimal = Decimal("0")

    # By location breakdown
    by_location: dict[str, Decimal] = field(default_factory=dict)

    # Status
    status: str = "ok"  # ok, low, critical, overstocked

    @classmethod
    def from_items(cls, items: list[InventoryItem], part_name: str = "") -> "StockLevel":
        """Aggregate multiple inventory items into stock level."""
        if not items:
            raise ValueError("No items to aggregate")

        first = items[0]
        level = cls(
            part_id=first.part_id,
            part_number=first.part_number,
            part_name=part_name,
        )

        for item in items:
            level.total_on_hand += item.on_hand
            level.total_allocated += item.allocated
            level.total_on_order += item.on_order
            level.total_value += item.total_value
            level.by_location[item.location_id] = item.on_hand

        level.total_available = level.total_on_hand - level.total_allocated

        # Determine status
        if level.total_available < 0:
            level.status = "critical"
        elif any(item.needs_reorder() for item in items):
            level.status = "low"

        return level
