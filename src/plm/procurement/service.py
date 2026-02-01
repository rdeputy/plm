"""
Procurement Service

Business logic for procurement management including:
- Vendor management and performance tracking
- Purchase order lifecycle (create, approve, send, receive, close)
- Price agreement management
- Goods receipt processing
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import uuid4

from .models import (
    Vendor,
    VendorContact,
    PurchaseOrder,
    POItem,
    POStatus,
    PriceAgreement,
    Receipt,
    ReceiptItem,
)
from .repository import ProcurementRepository


class ProcurementError(Exception):
    """Base exception for procurement operations."""

    pass


class VendorNotFoundError(ProcurementError):
    """Raised when a vendor doesn't exist."""

    pass


class PONotFoundError(ProcurementError):
    """Raised when a PO doesn't exist."""

    pass


class InvalidPOStateError(ProcurementError):
    """Raised for invalid PO state transitions."""

    pass


class ReceiptError(ProcurementError):
    """Raised for receipt processing errors."""

    pass


@dataclass
class VendorPerformance:
    """Vendor performance metrics."""

    vendor_id: str
    vendor_name: str
    total_orders: int
    total_value: Decimal
    on_time_deliveries: int
    late_deliveries: int
    on_time_rate: float
    quality_accepts: Decimal
    quality_rejects: Decimal
    quality_rate: float
    avg_lead_time_days: float


@dataclass
class POSummary:
    """Summary of purchase order status."""

    total_orders: int
    total_value: Decimal
    by_status: dict[str, int]
    open_value: Decimal
    received_value: Decimal


class ProcurementService:
    """
    Service for procurement management operations.

    Handles vendor management, purchase orders, and receiving.
    """

    def __init__(self, repository: ProcurementRepository):
        self.repo = repository

    # -------------------------------------------------------------------------
    # Vendor Management
    # -------------------------------------------------------------------------

    def create_vendor(self, vendor: Vendor) -> Vendor:
        """Create a new vendor."""
        if not vendor.id:
            vendor.id = str(uuid4())
        return self.repo.create_vendor(vendor)

    def get_vendor(self, vendor_id: str) -> Optional[Vendor]:
        """Get a vendor by ID."""
        return self.repo.get_vendor(vendor_id)

    def get_vendor_by_code(self, vendor_code: str) -> Optional[Vendor]:
        """Get a vendor by code."""
        return self.repo.get_vendor_by_code(vendor_code)

    def list_vendors(
        self,
        is_active: bool = True,
        is_approved: Optional[bool] = None,
        category: Optional[str] = None,
    ) -> list[Vendor]:
        """List vendors with optional filters."""
        return self.repo.list_vendors(
            is_active=is_active, is_approved=is_approved, category=category
        )

    def update_vendor(self, vendor: Vendor) -> Vendor:
        """Update vendor information."""
        return self.repo.update_vendor(vendor)

    def deactivate_vendor(self, vendor_id: str) -> Vendor:
        """Deactivate a vendor."""
        vendor = self.repo.get_vendor(vendor_id)
        if not vendor:
            raise VendorNotFoundError(f"Vendor {vendor_id} not found")
        vendor.is_active = False
        return self.repo.update_vendor(vendor)

    def add_vendor_contact(
        self, vendor_id: str, contact: VendorContact
    ) -> Vendor:
        """Add a contact to a vendor."""
        vendor = self.repo.get_vendor(vendor_id)
        if not vendor:
            raise VendorNotFoundError(f"Vendor {vendor_id} not found")
        vendor.contacts.append(contact)
        return self.repo.update_vendor(vendor)

    def get_vendor_performance(self, vendor_id: str) -> VendorPerformance:
        """Get vendor performance metrics."""
        vendor = self.repo.get_vendor(vendor_id)
        if not vendor:
            raise VendorNotFoundError(f"Vendor {vendor_id} not found")

        # Get all POs for this vendor
        pos = self.repo.list_purchase_orders(vendor_id=vendor_id)

        total_orders = len(pos)
        total_value = sum(po.total for po in pos)

        # Calculate on-time rate from closed POs
        closed_pos = [po for po in pos if po.status == POStatus.CLOSED]
        on_time = 0
        late = 0
        for po in closed_pos:
            if po.promised_date and po.order_date:
                # Get receipts for this PO
                receipts = self.repo.list_receipts(po_id=po.id)
                if receipts:
                    last_receipt = max(receipts, key=lambda r: r.receipt_date)
                    if last_receipt.receipt_date <= po.promised_date:
                        on_time += 1
                    else:
                        late += 1

        on_time_rate = (on_time / (on_time + late) * 100) if (on_time + late) > 0 else 0

        # Get receipt quality data
        quality_accepts = Decimal("0")
        quality_rejects = Decimal("0")
        for po in closed_pos:
            receipts = self.repo.list_receipts(po_id=po.id)
            for receipt in receipts:
                for item in receipt.items:
                    quality_accepts += item.quantity_accepted
                    quality_rejects += item.quantity_rejected

        quality_rate = (
            float(quality_accepts / (quality_accepts + quality_rejects) * 100)
            if (quality_accepts + quality_rejects) > 0
            else 0
        )

        return VendorPerformance(
            vendor_id=vendor_id,
            vendor_name=vendor.name,
            total_orders=total_orders,
            total_value=total_value,
            on_time_deliveries=on_time,
            late_deliveries=late,
            on_time_rate=on_time_rate,
            quality_accepts=quality_accepts,
            quality_rejects=quality_rejects,
            quality_rate=quality_rate,
            avg_lead_time_days=vendor.avg_lead_time_days,
        )

    # -------------------------------------------------------------------------
    # Price Agreement Management
    # -------------------------------------------------------------------------

    def create_price_agreement(self, agreement: PriceAgreement) -> PriceAgreement:
        """Create a new price agreement."""
        if not agreement.id:
            agreement.id = str(uuid4())
        return self.repo.create_price_agreement(agreement)

    def get_price_for_part(
        self,
        vendor_id: str,
        part_id: str,
        quantity: Decimal = Decimal("1"),
        as_of: Optional[date] = None,
    ) -> Optional[Decimal]:
        """Get the current price for a part from a vendor."""
        agreement = self.repo.get_current_price(vendor_id, part_id, as_of)
        if not agreement:
            return None
        return agreement.get_price(quantity)

    def list_price_agreements(
        self,
        vendor_id: Optional[str] = None,
        part_id: Optional[str] = None,
        active_only: bool = True,
    ) -> list[PriceAgreement]:
        """List price agreements."""
        return self.repo.list_price_agreements(
            vendor_id=vendor_id, part_id=part_id, active_only=active_only
        )

    def find_best_price(
        self, part_id: str, quantity: Decimal = Decimal("1")
    ) -> list[tuple[Vendor, Decimal]]:
        """Find vendors with pricing for a part, sorted by price."""
        agreements = self.repo.list_price_agreements(part_id=part_id, active_only=True)
        results = []
        for agreement in agreements:
            vendor = self.repo.get_vendor(agreement.vendor_id)
            if vendor and vendor.is_active:
                price = agreement.get_price(quantity)
                results.append((vendor, price))
        results.sort(key=lambda x: x[1])
        return results

    # -------------------------------------------------------------------------
    # Purchase Order Lifecycle
    # -------------------------------------------------------------------------

    def create_purchase_order(
        self,
        vendor_id: str,
        items: list[dict],
        ship_to_location_id: Optional[str] = None,
        ship_to_address: Optional[str] = None,
        required_date: Optional[date] = None,
        project_id: Optional[str] = None,
        created_by: str = "system",
        notes: Optional[str] = None,
    ) -> PurchaseOrder:
        """
        Create a new purchase order.

        items should be a list of dicts with keys:
        - part_id, part_number, description, quantity, unit_of_measure
        - optionally: unit_price, required_date, project_id
        """
        vendor = self.repo.get_vendor(vendor_id)
        if not vendor:
            raise VendorNotFoundError(f"Vendor {vendor_id} not found")

        if not vendor.is_active:
            raise ProcurementError(f"Vendor {vendor.name} is not active")

        po = PurchaseOrder(
            id=str(uuid4()),
            po_number=self.repo.get_next_po_number(),
            vendor_id=vendor_id,
            vendor_name=vendor.name,
            status=POStatus.DRAFT,
            ship_to_location_id=ship_to_location_id,
            ship_to_address=ship_to_address,
            required_date=required_date,
            freight_terms=vendor.freight_terms,
            payment_terms=vendor.payment_terms,
            project_id=project_id,
            created_by=created_by,
            notes=notes,
        )

        # Add items
        for i, item_data in enumerate(items):
            # Try to get price from agreement
            unit_price = item_data.get("unit_price")
            if unit_price is None:
                unit_price = self.get_price_for_part(
                    vendor_id,
                    item_data["part_id"],
                    item_data["quantity"],
                ) or Decimal("0")

            po_item = POItem(
                id=str(uuid4()),
                po_id=po.id,
                line_number=i + 1,
                part_id=item_data["part_id"],
                part_number=item_data["part_number"],
                description=item_data.get("description", item_data["part_number"]),
                quantity=Decimal(str(item_data["quantity"])),
                unit_of_measure=item_data.get("unit_of_measure", "EA"),
                unit_price=Decimal(str(unit_price)),
                required_date=item_data.get("required_date", required_date),
                project_id=item_data.get("project_id", project_id),
                planned_order_id=item_data.get("planned_order_id"),
            )
            po_item.extended_price = po_item.quantity * po_item.unit_price
            po.items.append(po_item)

        # Calculate totals
        po._recalc_totals()

        return self.repo.create_purchase_order(po)

    def get_purchase_order(self, po_id: str) -> Optional[PurchaseOrder]:
        """Get a purchase order by ID."""
        return self.repo.get_purchase_order(po_id)

    def get_purchase_order_by_number(self, po_number: str) -> Optional[PurchaseOrder]:
        """Get a purchase order by PO number."""
        return self.repo.get_purchase_order_by_number(po_number)

    def list_purchase_orders(
        self,
        vendor_id: Optional[str] = None,
        status: Optional[POStatus] = None,
        project_id: Optional[str] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> list[PurchaseOrder]:
        """List purchase orders with filters."""
        return self.repo.list_purchase_orders(
            vendor_id=vendor_id,
            status=status,
            project_id=project_id,
            from_date=from_date,
            to_date=to_date,
        )

    def submit_for_approval(self, po_id: str) -> PurchaseOrder:
        """Submit a draft PO for approval."""
        po = self.repo.get_purchase_order(po_id)
        if not po:
            raise PONotFoundError(f"PO {po_id} not found")

        if po.status != POStatus.DRAFT:
            raise InvalidPOStateError(
                f"Cannot submit PO in status {po.status.value} for approval"
            )

        if not po.items:
            raise ProcurementError("Cannot submit PO with no items")

        po.status = POStatus.PENDING_APPROVAL
        return self.repo.update_purchase_order(po)

    def approve_purchase_order(
        self, po_id: str, approved_by: str, notes: Optional[str] = None
    ) -> PurchaseOrder:
        """Approve a purchase order."""
        po = self.repo.get_purchase_order(po_id)
        if not po:
            raise PONotFoundError(f"PO {po_id} not found")

        if po.status != POStatus.PENDING_APPROVAL:
            raise InvalidPOStateError(
                f"Cannot approve PO in status {po.status.value}"
            )

        po.status = POStatus.APPROVED
        po.approved_by = approved_by
        po.approved_at = datetime.now()
        if notes:
            po.notes = (po.notes or "") + f"\nApproval: {notes}"

        return self.repo.update_purchase_order(po)

    def reject_purchase_order(
        self, po_id: str, rejected_by: str, reason: str
    ) -> PurchaseOrder:
        """Reject a purchase order, returning to draft."""
        po = self.repo.get_purchase_order(po_id)
        if not po:
            raise PONotFoundError(f"PO {po_id} not found")

        if po.status != POStatus.PENDING_APPROVAL:
            raise InvalidPOStateError(
                f"Cannot reject PO in status {po.status.value}"
            )

        po.status = POStatus.DRAFT
        po.notes = (po.notes or "") + f"\nRejected by {rejected_by}: {reason}"

        return self.repo.update_purchase_order(po)

    def send_purchase_order(self, po_id: str) -> PurchaseOrder:
        """Mark PO as sent to vendor."""
        po = self.repo.get_purchase_order(po_id)
        if not po:
            raise PONotFoundError(f"PO {po_id} not found")

        if po.status != POStatus.APPROVED:
            raise InvalidPOStateError(
                f"Cannot send PO in status {po.status.value}"
            )

        po.status = POStatus.SENT
        po.order_date = date.today()

        return self.repo.update_purchase_order(po)

    def acknowledge_purchase_order(
        self, po_id: str, promised_date: Optional[date] = None
    ) -> PurchaseOrder:
        """Vendor acknowledges PO."""
        po = self.repo.get_purchase_order(po_id)
        if not po:
            raise PONotFoundError(f"PO {po_id} not found")

        if po.status != POStatus.SENT:
            raise InvalidPOStateError(
                f"Cannot acknowledge PO in status {po.status.value}"
            )

        po.status = POStatus.ACKNOWLEDGED
        if promised_date:
            po.promised_date = promised_date

        return self.repo.update_purchase_order(po)

    def cancel_purchase_order(self, po_id: str, reason: str) -> PurchaseOrder:
        """Cancel a purchase order."""
        po = self.repo.get_purchase_order(po_id)
        if not po:
            raise PONotFoundError(f"PO {po_id} not found")

        if po.status in [POStatus.RECEIVED, POStatus.CLOSED]:
            raise InvalidPOStateError(
                f"Cannot cancel PO in status {po.status.value}"
            )

        po.status = POStatus.CANCELLED
        po.notes = (po.notes or "") + f"\nCancelled: {reason}"

        return self.repo.update_purchase_order(po)

    def close_purchase_order(self, po_id: str) -> PurchaseOrder:
        """Close a fully received PO."""
        po = self.repo.get_purchase_order(po_id)
        if not po:
            raise PONotFoundError(f"PO {po_id} not found")

        if po.status != POStatus.RECEIVED:
            raise InvalidPOStateError(
                f"Cannot close PO in status {po.status.value}"
            )

        po.status = POStatus.CLOSED
        for item in po.items:
            item.is_closed = True
            self.repo.update_po_item(item)

        return self.repo.update_purchase_order(po)

    def add_po_item(self, po_id: str, item_data: dict) -> PurchaseOrder:
        """Add an item to a draft PO."""
        po = self.repo.get_purchase_order(po_id)
        if not po:
            raise PONotFoundError(f"PO {po_id} not found")

        if po.status != POStatus.DRAFT:
            raise InvalidPOStateError(
                f"Cannot add items to PO in status {po.status.value}"
            )

        # Get price
        unit_price = item_data.get("unit_price")
        if unit_price is None:
            unit_price = self.get_price_for_part(
                po.vendor_id,
                item_data["part_id"],
                item_data["quantity"],
            ) or Decimal("0")

        po_item = POItem(
            id=str(uuid4()),
            po_id=po.id,
            line_number=len(po.items) + 1,
            part_id=item_data["part_id"],
            part_number=item_data["part_number"],
            description=item_data.get("description", item_data["part_number"]),
            quantity=Decimal(str(item_data["quantity"])),
            unit_of_measure=item_data.get("unit_of_measure", "EA"),
            unit_price=Decimal(str(unit_price)),
            required_date=item_data.get("required_date"),
            project_id=item_data.get("project_id"),
        )
        po_item.extended_price = po_item.quantity * po_item.unit_price
        po.add_item(po_item)

        # Save - need to update PO and create item
        return self.repo.update_purchase_order(po)

    def get_po_summary(
        self,
        vendor_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> POSummary:
        """Get summary of PO status."""
        pos = self.repo.list_purchase_orders(
            vendor_id=vendor_id, project_id=project_id
        )

        by_status: dict[str, int] = {}
        total_value = Decimal("0")
        open_value = Decimal("0")
        received_value = Decimal("0")

        for po in pos:
            status = po.status.value
            by_status[status] = by_status.get(status, 0) + 1
            total_value += po.total

            if po.status in [
                POStatus.APPROVED,
                POStatus.SENT,
                POStatus.ACKNOWLEDGED,
                POStatus.PARTIAL,
            ]:
                open_value += po.total
            elif po.status in [POStatus.RECEIVED, POStatus.CLOSED]:
                received_value += po.total

        return POSummary(
            total_orders=len(pos),
            total_value=total_value,
            by_status=by_status,
            open_value=open_value,
            received_value=received_value,
        )

    # -------------------------------------------------------------------------
    # Receiving
    # -------------------------------------------------------------------------

    def receive_goods(
        self,
        po_id: str,
        items: list[dict],
        received_by: str,
        location_id: Optional[str] = None,
        packing_slip: Optional[str] = None,
        carrier: Optional[str] = None,
        tracking_number: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Receipt:
        """
        Receive goods against a purchase order.

        items should be a list of dicts with keys:
        - po_item_id, quantity_received
        - optionally: quantity_accepted, quantity_rejected, lot_number,
          serial_numbers, location_id, inspection_required
        """
        po = self.repo.get_purchase_order(po_id)
        if not po:
            raise PONotFoundError(f"PO {po_id} not found")

        if po.status not in [
            POStatus.SENT,
            POStatus.ACKNOWLEDGED,
            POStatus.PARTIAL,
        ]:
            raise InvalidPOStateError(
                f"Cannot receive against PO in status {po.status.value}"
            )

        # Create receipt
        receipt = Receipt(
            id=str(uuid4()),
            receipt_number=self.repo.get_next_receipt_number(),
            po_id=po_id,
            po_number=po.po_number,
            vendor_id=po.vendor_id,
            receipt_date=date.today(),
            received_by=received_by,
            location_id=location_id,
            packing_slip=packing_slip,
            carrier=carrier,
            tracking_number=tracking_number,
            notes=notes,
        )

        # Process items
        for item_data in items:
            po_item = next(
                (i for i in po.items if i.id == item_data["po_item_id"]), None
            )
            if not po_item:
                raise ReceiptError(
                    f"PO item {item_data['po_item_id']} not found on PO {po.po_number}"
                )

            qty_received = Decimal(str(item_data["quantity_received"]))
            qty_accepted = Decimal(
                str(item_data.get("quantity_accepted", qty_received))
            )
            qty_rejected = Decimal(str(item_data.get("quantity_rejected", 0)))

            # Validate quantities
            if qty_accepted + qty_rejected > qty_received:
                raise ReceiptError(
                    f"Accepted ({qty_accepted}) + Rejected ({qty_rejected}) "
                    f"exceeds received ({qty_received})"
                )

            receipt_item = ReceiptItem(
                id=str(uuid4()),
                receipt_id=receipt.id,
                po_item_id=po_item.id,
                part_id=po_item.part_id,
                part_number=po_item.part_number,
                quantity_received=qty_received,
                quantity_accepted=qty_accepted,
                quantity_rejected=qty_rejected,
                unit_of_measure=po_item.unit_of_measure,
                lot_number=item_data.get("lot_number"),
                serial_numbers=item_data.get("serial_numbers", []),
                location_id=item_data.get("location_id", location_id),
                inspection_required=item_data.get("inspection_required", False),
                inspection_status="pending" if item_data.get("inspection_required") else None,
            )
            receipt.items.append(receipt_item)

            # Update PO item received quantity
            po_item.received_quantity += qty_accepted

        # Save receipt
        receipt = self.repo.create_receipt(receipt)

        # Update PO status
        all_received = all(item.open_quantity <= 0 for item in po.items)
        any_received = any(item.received_quantity > 0 for item in po.items)

        if all_received:
            po.status = POStatus.RECEIVED
        elif any_received:
            po.status = POStatus.PARTIAL

        self.repo.update_purchase_order(po)

        return receipt

    def get_receipt(self, receipt_id: str) -> Optional[Receipt]:
        """Get a receipt by ID."""
        return self.repo.get_receipt(receipt_id)

    def list_receipts(
        self,
        po_id: Optional[str] = None,
        vendor_id: Optional[str] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> list[Receipt]:
        """List receipts with filters."""
        return self.repo.list_receipts(
            po_id=po_id,
            vendor_id=vendor_id,
            from_date=from_date,
            to_date=to_date,
        )

    def complete_inspection(
        self,
        receipt_id: str,
        receipt_item_id: str,
        passed: bool,
        quantity_accepted: Decimal,
        quantity_rejected: Decimal = Decimal("0"),
        notes: Optional[str] = None,
    ) -> Receipt:
        """Complete inspection for a receipt item."""
        receipt = self.repo.get_receipt(receipt_id)
        if not receipt:
            raise ReceiptError(f"Receipt {receipt_id} not found")

        item = next((i for i in receipt.items if i.id == receipt_item_id), None)
        if not item:
            raise ReceiptError(f"Receipt item {receipt_item_id} not found")

        if not item.inspection_required:
            raise ReceiptError("Item does not require inspection")

        item.inspection_status = "passed" if passed else "failed"
        item.quantity_accepted = quantity_accepted
        item.quantity_rejected = quantity_rejected
        item.inspection_notes = notes

        # Update PO item if quantities changed
        po = self.repo.get_purchase_order(receipt.po_id)
        if po:
            po_item = next((i for i in po.items if i.id == item.po_item_id), None)
            if po_item:
                # Recalculate received from all receipts
                all_receipts = self.repo.list_receipts(po_id=receipt.po_id)
                total_accepted = sum(
                    ri.quantity_accepted
                    for r in all_receipts
                    for ri in r.items
                    if ri.po_item_id == po_item.id
                )
                po_item.received_quantity = total_accepted
                self.repo.update_po_item(po_item)

        return receipt
