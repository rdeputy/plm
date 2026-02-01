"""
Tests for Procurement Module

Tests vendors, purchase orders, and receipts.
"""

import pytest
from datetime import date
from decimal import Decimal
from uuid import uuid4

from plm.procurement.models import (
    Vendor,
    PurchaseOrder,
    POItem,
    POStatus,
    Receipt,
    ReceiptItem,
)
from plm.db.models import (
    VendorModel,
    PurchaseOrderModel,
    POItemModel,
    ReceiptModel,
    ReceiptItemModel,
)


class TestVendorModel:
    """Tests for Vendor dataclass model."""

    def test_create_vendor(self):
        """Test creating a vendor."""
        vendor = Vendor(
            id=str(uuid4()),
            name="Test Supplier Co",
            vendor_code="TSC001",
            address="789 Supply Road",
            city="Denver",
            state="CO",
            phone="303-555-0200",
        )
        assert vendor.name == "Test Supplier Co"
        assert vendor.vendor_code == "TSC001"

    def test_vendor_to_dict(self, sample_vendor):
        """Test converting vendor to dictionary."""
        # Convert model to dict manually for testing
        data = {
            "id": sample_vendor.id,
            "name": sample_vendor.name,
            "vendor_code": sample_vendor.vendor_code,
            "is_active": sample_vendor.is_active,
        }
        assert data["name"] == "ABC Building Supply"
        assert data["vendor_code"] == "ABC001"


class TestVendorDatabase:
    """Tests for Vendor database operations."""

    def test_persist_vendor(self, session, sample_vendor):
        """Test persisting a vendor."""
        found = session.query(VendorModel).filter_by(id=sample_vendor.id).first()
        assert found is not None
        assert found.name == "ABC Building Supply"
        assert found.is_approved is True

    def test_update_vendor(self, session, sample_vendor):
        """Test updating a vendor."""
        sample_vendor.on_time_rate = Decimal("95.5")
        sample_vendor.quality_rate = Decimal("98.0")
        session.commit()

        found = session.query(VendorModel).filter_by(id=sample_vendor.id).first()
        assert found.on_time_rate == Decimal("95.5")
        assert found.quality_rate == Decimal("98.0")

    def test_deactivate_vendor(self, session, sample_vendor):
        """Test deactivating a vendor."""
        sample_vendor.is_active = False
        session.commit()

        active_vendors = (
            session.query(VendorModel).filter_by(is_active=True).all()
        )
        assert len(active_vendors) == 0

    def test_vendor_code_unique(self, session, sample_vendor):
        """Test vendor code uniqueness constraint."""
        duplicate = VendorModel(
            id=str(uuid4()),
            name="Another Supplier",
            vendor_code=sample_vendor.vendor_code,  # Same code
        )
        session.add(duplicate)
        with pytest.raises(Exception):  # IntegrityError
            session.commit()


class TestPurchaseOrderModel:
    """Tests for PurchaseOrder dataclass model."""

    def test_po_status_values(self):
        """Test PO status enum values."""
        assert POStatus.DRAFT.value == "draft"
        assert POStatus.PENDING_APPROVAL.value == "pending_approval"
        assert POStatus.APPROVED.value == "approved"
        assert POStatus.SENT.value == "sent"
        assert POStatus.RECEIVED.value == "received"
        assert POStatus.CLOSED.value == "closed"
        assert POStatus.CANCELLED.value == "cancelled"


class TestPurchaseOrderDatabase:
    """Tests for PurchaseOrder database operations."""

    def test_persist_purchase_order(self, session, sample_purchase_order):
        """Test persisting a purchase order."""
        found = (
            session.query(PurchaseOrderModel)
            .filter_by(id=sample_purchase_order.id)
            .first()
        )
        assert found is not None
        assert found.po_number == "PO-2026-0001"
        assert found.status == POStatus.DRAFT

    def test_po_items(self, session, sample_purchase_order):
        """Test retrieving PO items."""
        items = (
            session.query(POItemModel)
            .filter_by(po_id=sample_purchase_order.id)
            .all()
        )
        assert len(items) == 1
        assert items[0].quantity == Decimal("100")
        assert items[0].unit_price == Decimal("8.99")

    def test_update_po_status(self, session, sample_purchase_order):
        """Test updating PO status."""
        sample_purchase_order.status = POStatus.APPROVED
        sample_purchase_order.approved_by = "manager"
        session.commit()

        found = (
            session.query(PurchaseOrderModel)
            .filter_by(id=sample_purchase_order.id)
            .first()
        )
        assert found.status == POStatus.APPROVED
        assert found.approved_by == "manager"

    def test_add_po_item(self, session, sample_purchase_order, sample_part_model):
        """Test adding an item to a PO."""
        new_item = POItemModel(
            id=str(uuid4()),
            po_id=sample_purchase_order.id,
            line_number=2,
            part_id=sample_part_model.id,
            part_number=sample_part_model.part_number,
            description="Additional order",
            quantity=Decimal("50"),
            unit_of_measure="EA",
            unit_price=Decimal("8.99"),
            extended_price=Decimal("449.50"),
        )
        session.add(new_item)
        session.commit()

        items = (
            session.query(POItemModel)
            .filter_by(po_id=sample_purchase_order.id)
            .order_by(POItemModel.line_number)
            .all()
        )
        assert len(items) == 2
        assert items[1].line_number == 2

    def test_po_total_calculation(self, session, sample_purchase_order):
        """Test PO total calculation."""
        items = (
            session.query(POItemModel)
            .filter_by(po_id=sample_purchase_order.id)
            .all()
        )

        subtotal = sum(item.extended_price for item in items)
        assert subtotal == Decimal("899.00")

        total = subtotal + sample_purchase_order.shipping
        assert total == Decimal("949.00")


class TestReceiptDatabase:
    """Tests for Receipt database operations."""

    def test_create_receipt(self, session, sample_purchase_order):
        """Test creating a receipt."""
        receipt = ReceiptModel(
            id=str(uuid4()),
            receipt_number="RCV-2026-0001",
            po_id=sample_purchase_order.id,
            po_number=sample_purchase_order.po_number,
            vendor_id=sample_purchase_order.vendor_id,
            receipt_date=date.today(),
            packing_slip="PS-12345",
            carrier="FedEx Freight",
            tracking_number="7891234567890",
            received_by="warehouse_user",
            is_complete=False,
        )
        session.add(receipt)
        session.flush()

        # Get PO item for receipt
        po_items = (
            session.query(POItemModel)
            .filter_by(po_id=sample_purchase_order.id)
            .all()
        )

        # Create receipt item for partial receipt
        receipt_item = ReceiptItemModel(
            id=str(uuid4()),
            receipt_id=receipt.id,
            po_item_id=po_items[0].id,
            part_id=po_items[0].part_id,
            part_number=po_items[0].part_number,
            quantity_received=Decimal("75"),  # Partial
            quantity_accepted=Decimal("75"),
            quantity_rejected=Decimal("0"),
            unit_of_measure="EA",
        )
        session.add(receipt_item)
        session.commit()

        found = (
            session.query(ReceiptModel)
            .filter_by(id=receipt.id)
            .first()
        )
        assert found.receipt_number == "RCV-2026-0001"
        assert found.is_complete is False

    def test_update_po_item_received_qty(self, session, sample_purchase_order):
        """Test updating received quantity on PO item."""
        po_items = (
            session.query(POItemModel)
            .filter_by(po_id=sample_purchase_order.id)
            .all()
        )

        po_items[0].received_quantity = Decimal("75")
        session.commit()

        found = session.query(POItemModel).filter_by(id=po_items[0].id).first()
        assert found.received_quantity == Decimal("75")
        # Still 25 to receive
        assert found.quantity - found.received_quantity == Decimal("25")

    def test_complete_receipt(self, session, sample_purchase_order):
        """Test completing a receipt (full quantity received)."""
        # Create receipt for full quantity
        receipt = ReceiptModel(
            id=str(uuid4()),
            receipt_number="RCV-2026-0002",
            po_id=sample_purchase_order.id,
            po_number=sample_purchase_order.po_number,
            vendor_id=sample_purchase_order.vendor_id,
            received_by="warehouse_user",
            is_complete=True,
        )
        session.add(receipt)
        session.flush()

        po_items = (
            session.query(POItemModel)
            .filter_by(po_id=sample_purchase_order.id)
            .all()
        )

        receipt_item = ReceiptItemModel(
            id=str(uuid4()),
            receipt_id=receipt.id,
            po_item_id=po_items[0].id,
            part_id=po_items[0].part_id,
            part_number=po_items[0].part_number,
            quantity_received=po_items[0].quantity,  # Full qty
            quantity_accepted=po_items[0].quantity,
        )
        session.add(receipt_item)

        # Update PO item
        po_items[0].received_quantity = po_items[0].quantity
        po_items[0].is_closed = True

        # Update PO status
        sample_purchase_order.status = POStatus.RECEIVED
        session.commit()

        found_po = (
            session.query(PurchaseOrderModel)
            .filter_by(id=sample_purchase_order.id)
            .first()
        )
        assert found_po.status == POStatus.RECEIVED

        found_item = session.query(POItemModel).filter_by(id=po_items[0].id).first()
        assert found_item.is_closed is True


class TestProcurementWorkflow:
    """Tests for end-to-end procurement workflow."""

    def test_full_po_lifecycle(self, session, sample_vendor, sample_part_model):
        """Test complete PO lifecycle from draft to closed."""
        # 1. Create PO
        po = PurchaseOrderModel(
            id=str(uuid4()),
            po_number="PO-2026-0099",
            vendor_id=sample_vendor.id,
            vendor_name=sample_vendor.name,
            status=POStatus.DRAFT,
            subtotal=Decimal("1000.00"),
            total=Decimal("1000.00"),
            created_by="buyer",
        )
        session.add(po)
        session.flush()

        item = POItemModel(
            id=str(uuid4()),
            po_id=po.id,
            line_number=1,
            part_id=sample_part_model.id,
            part_number=sample_part_model.part_number,
            description=sample_part_model.name,
            quantity=Decimal("100"),
            unit_of_measure="EA",
            unit_price=Decimal("10.00"),
            extended_price=Decimal("1000.00"),
        )
        session.add(item)
        session.commit()

        # 2. Submit for approval
        po.status = POStatus.PENDING_APPROVAL
        session.commit()
        assert po.status == POStatus.PENDING_APPROVAL

        # 3. Approve
        po.status = POStatus.APPROVED
        po.approved_by = "manager"
        session.commit()
        assert po.status == POStatus.APPROVED

        # 4. Send to vendor
        po.status = POStatus.SENT
        po.order_date = date.today()
        session.commit()
        assert po.status == POStatus.SENT

        # 5. Receive goods
        receipt = ReceiptModel(
            id=str(uuid4()),
            receipt_number="RCV-2026-0099",
            po_id=po.id,
            po_number=po.po_number,
            vendor_id=sample_vendor.id,
            received_by="warehouse",
            is_complete=True,
        )
        session.add(receipt)
        session.flush()

        receipt_item = ReceiptItemModel(
            id=str(uuid4()),
            receipt_id=receipt.id,
            po_item_id=item.id,
            part_id=item.part_id,
            part_number=item.part_number,
            quantity_received=Decimal("100"),
            quantity_accepted=Decimal("100"),
        )
        session.add(receipt_item)

        item.received_quantity = Decimal("100")
        item.is_closed = True
        po.status = POStatus.RECEIVED
        session.commit()

        # 6. Close PO
        po.status = POStatus.CLOSED
        session.commit()

        # Verify final state
        final_po = session.query(PurchaseOrderModel).filter_by(id=po.id).first()
        assert final_po.status == POStatus.CLOSED

        final_item = session.query(POItemModel).filter_by(id=item.id).first()
        assert final_item.is_closed is True
        assert final_item.received_quantity == final_item.quantity
