"""
Procurement Models

Vendors, Purchase Orders, and Receiving.
Connects MRP planned orders to actual purchasing.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional


class POStatus(Enum):
    """Purchase order status."""

    DRAFT = "draft"  # Being created
    PENDING_APPROVAL = "pending_approval"  # Awaiting approval
    APPROVED = "approved"  # Approved, not yet sent
    SENT = "sent"  # Sent to vendor
    ACKNOWLEDGED = "acknowledged"  # Vendor confirmed
    PARTIAL = "partial"  # Partially received
    RECEIVED = "received"  # Fully received
    CLOSED = "closed"  # Complete and closed
    CANCELLED = "cancelled"  # Cancelled


@dataclass
class VendorContact:
    """Contact person at a vendor."""

    name: str
    title: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    is_primary: bool = False


@dataclass
class Vendor:
    """
    A supplier/vendor.

    Tracks capabilities, pricing, and performance.
    """

    id: str
    name: str
    vendor_code: str  # Short code for POs

    # Contact info
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: str = "USA"
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None

    contacts: list[VendorContact] = field(default_factory=list)

    # Terms
    payment_terms: str = "Net 30"  # Net 30, Net 15, COD, etc.
    freight_terms: str = "FOB Origin"  # FOB Origin, FOB Dest, Prepaid
    minimum_order: Decimal = Decimal("0")

    # Categories they supply
    categories: list[str] = field(default_factory=list)  # lumber, electrical, plumbing

    # Performance metrics
    on_time_rate: float = 0.0  # 0-100%
    quality_rate: float = 0.0  # 0-100%
    avg_lead_time_days: int = 0

    # Compliance
    is_approved: bool = True
    insurance_expiry: Optional[date] = None
    w9_on_file: bool = False
    certifications: list[str] = field(default_factory=list)

    # Status
    is_active: bool = True
    notes: Optional[str] = None


@dataclass
class PriceAgreement:
    """
    Negotiated pricing with a vendor.

    Can be blanket PO, contract pricing, or volume discounts.
    """

    id: str
    vendor_id: str
    part_id: str
    part_number: str

    # Pricing
    unit_price: Decimal
    currency: str = "USD"

    # Validity
    effective_date: date = field(default_factory=date.today)
    expiration_date: Optional[date] = None

    # Volume breaks
    min_quantity: Decimal = Decimal("1")
    price_breaks: dict[str, Decimal] = field(default_factory=dict)  # qty -> price

    # Reference
    contract_number: Optional[str] = None
    notes: Optional[str] = None

    def get_price(self, quantity: Decimal) -> Decimal:
        """Get unit price for a quantity (applying breaks)."""
        if not self.price_breaks:
            return self.unit_price

        applicable_price = self.unit_price
        for qty_str, price in sorted(self.price_breaks.items(), key=lambda x: Decimal(x[0])):
            if quantity >= Decimal(qty_str):
                applicable_price = price

        return applicable_price


@dataclass
class POItem:
    """Line item on a purchase order."""

    id: str
    po_id: str
    line_number: int

    # Part info
    part_id: str
    part_number: str
    description: str

    # Quantities
    quantity: Decimal
    unit_of_measure: str
    received_quantity: Decimal = Decimal("0")

    @property
    def open_quantity(self) -> Decimal:
        """Quantity not yet received."""
        return self.quantity - self.received_quantity

    # Pricing
    unit_price: Decimal = Decimal("0")
    extended_price: Decimal = Decimal("0")  # qty * unit_price

    # Dates
    required_date: Optional[date] = None  # When needed
    promised_date: Optional[date] = None  # Vendor promised

    # Reference
    project_id: Optional[str] = None
    planned_order_id: Optional[str] = None  # MRP planned order that generated this

    # Status
    is_closed: bool = False


@dataclass
class PurchaseOrder:
    """
    A purchase order to a vendor.

    Created manually or from MRP planned orders.
    """

    id: str
    po_number: str
    vendor_id: str
    vendor_name: str

    status: POStatus = POStatus.DRAFT

    # Items
    items: list[POItem] = field(default_factory=list)

    # Totals
    subtotal: Decimal = Decimal("0")
    tax: Decimal = Decimal("0")
    shipping: Decimal = Decimal("0")
    total: Decimal = Decimal("0")

    # Dates
    order_date: Optional[date] = None
    required_date: Optional[date] = None  # Overall required date
    promised_date: Optional[date] = None  # Vendor promised

    # Shipping
    ship_to_location_id: Optional[str] = None
    ship_to_address: Optional[str] = None
    freight_terms: str = "FOB Origin"

    # Payment
    payment_terms: str = "Net 30"

    # Reference
    project_id: Optional[str] = None  # Primary project
    requisition_id: Optional[str] = None
    notes: Optional[str] = None

    # Approval
    created_by: str = ""
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None

    # Tracking
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def add_item(self, item: POItem) -> None:
        """Add an item and recalculate totals."""
        item.line_number = len(self.items) + 1
        item.extended_price = item.quantity * item.unit_price
        self.items.append(item)
        self._recalc_totals()

    def _recalc_totals(self) -> None:
        """Recalculate order totals."""
        self.subtotal = sum(item.extended_price for item in self.items)
        self.total = self.subtotal + self.tax + self.shipping

    @property
    def is_fully_received(self) -> bool:
        """Check if all items are received."""
        return all(item.open_quantity <= 0 for item in self.items)


@dataclass
class ReceiptItem:
    """Line item on a receipt."""

    id: str
    receipt_id: str
    po_item_id: str
    part_id: str
    part_number: str

    # Quantities
    quantity_received: Decimal
    quantity_accepted: Decimal = Decimal("0")  # After inspection
    quantity_rejected: Decimal = Decimal("0")
    unit_of_measure: str = "EA"

    # Lot/Serial
    lot_number: Optional[str] = None
    serial_numbers: list[str] = field(default_factory=list)

    # Location received into
    location_id: Optional[str] = None

    # Inspection
    inspection_required: bool = False
    inspection_status: Optional[str] = None  # pending, passed, failed
    inspection_notes: Optional[str] = None


@dataclass
class Receipt:
    """
    A goods receipt against a purchase order.

    Records what was received, inspected, and put away.
    """

    id: str
    receipt_number: str
    po_id: str
    po_number: str
    vendor_id: str

    # Items received
    items: list[ReceiptItem] = field(default_factory=list)

    # Dates
    receipt_date: date = field(default_factory=date.today)
    created_at: datetime = field(default_factory=datetime.now)

    # Shipping info
    packing_slip: Optional[str] = None
    carrier: Optional[str] = None
    tracking_number: Optional[str] = None

    # Who
    received_by: str = ""
    location_id: Optional[str] = None  # Default receive location

    # Status
    is_complete: bool = False
    notes: Optional[str] = None
