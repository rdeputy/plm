"""
Tests for Inventory Module

Tests inventory locations, items, and transactions.
"""

import pytest
from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from plm.inventory.models import (
    InventoryLocation,
    InventoryItem,
    InventoryTransaction,
    TransactionType,
    StockLevel,
)
from plm.db.models import (
    InventoryLocationModel,
    InventoryItemModel,
    InventoryTransactionModel,
)


class TestInventoryModels:
    """Tests for inventory dataclass models."""

    def test_create_location(self):
        """Test creating an inventory location."""
        location = InventoryLocation(
            id=str(uuid4()),
            name="Job Site Trailer",
            location_type="jobsite",
            address="123 Construction Lane",
            is_active=True,
        )
        assert location.name == "Job Site Trailer"
        assert location.location_type == "jobsite"

    def test_create_inventory_item(self):
        """Test creating an inventory item."""
        item = InventoryItem(
            id=str(uuid4()),
            part_id="part-123",
            part_number="LUMBER-2X4",
            location_id="loc-123",
            on_hand=Decimal("100"),
            allocated=Decimal("25"),
            on_order=Decimal("50"),
        )
        assert item.on_hand == Decimal("100")
        assert item.allocated == Decimal("25")
        # Available = on_hand - allocated
        assert item.on_hand - item.allocated == Decimal("75")

    def test_stock_level_calculation(self):
        """Test stock level enum values."""
        assert TransactionType.RECEIPT.value == "receipt"
        assert TransactionType.ISSUE.value == "issue"
        assert TransactionType.TRANSFER.value == "transfer"
        assert TransactionType.ADJUSTMENT.value == "adjustment"


class TestInventoryDatabase:
    """Tests for inventory database operations."""

    def test_persist_location(self, session, sample_location):
        """Test persisting a location."""
        found = (
            session.query(InventoryLocationModel)
            .filter_by(id=sample_location.id)
            .first()
        )
        assert found is not None
        assert found.name == "Main Warehouse"

    def test_persist_inventory_item(self, session, sample_inventory_item):
        """Test persisting an inventory item."""
        found = (
            session.query(InventoryItemModel)
            .filter_by(id=sample_inventory_item.id)
            .first()
        )
        assert found is not None
        assert found.on_hand == Decimal("100")
        assert found.allocated == Decimal("20")

    def test_update_inventory_quantity(self, session, sample_inventory_item):
        """Test updating inventory quantity."""
        sample_inventory_item.on_hand = Decimal("150")
        sample_inventory_item.last_receipt_date = datetime.now()
        session.commit()

        found = (
            session.query(InventoryItemModel)
            .filter_by(id=sample_inventory_item.id)
            .first()
        )
        assert found.on_hand == Decimal("150")

    def test_inventory_by_location(self, session, sample_inventory_item, sample_location):
        """Test querying inventory by location."""
        items = (
            session.query(InventoryItemModel)
            .filter_by(location_id=sample_location.id)
            .all()
        )
        assert len(items) == 1
        assert items[0].part_number == "LUMBER-2X4-8FT"

    def test_low_stock_query(self, session, sample_inventory_item):
        """Test querying items below reorder point."""
        # Set on_hand below reorder point
        sample_inventory_item.on_hand = Decimal("20")
        session.commit()

        # Query items where on_hand < reorder_point
        low_stock = (
            session.query(InventoryItemModel)
            .filter(
                InventoryItemModel.on_hand < InventoryItemModel.reorder_point
            )
            .all()
        )
        assert len(low_stock) == 1


class TestInventoryTransactions:
    """Tests for inventory transactions."""

    def test_create_receipt_transaction(
        self, session, sample_inventory_item, sample_location
    ):
        """Test creating a receipt transaction."""
        txn = InventoryTransactionModel(
            id=str(uuid4()),
            transaction_type=TransactionType.RECEIPT,
            part_id=sample_inventory_item.part_id,
            part_number=sample_inventory_item.part_number,
            quantity=Decimal("50"),
            unit_of_measure="EA",
            location_id=sample_location.id,
            unit_cost=Decimal("8.99"),
            total_cost=Decimal("449.50"),
            created_by="test_user",
            notes="PO-2026-0001 receipt",
        )
        session.add(txn)
        session.commit()

        found = (
            session.query(InventoryTransactionModel)
            .filter_by(id=txn.id)
            .first()
        )
        assert found.transaction_type == TransactionType.RECEIPT
        assert found.quantity == Decimal("50")

    def test_create_issue_transaction(
        self, session, sample_inventory_item, sample_location
    ):
        """Test creating an issue transaction."""
        txn = InventoryTransactionModel(
            id=str(uuid4()),
            transaction_type=TransactionType.ISSUE,
            part_id=sample_inventory_item.part_id,
            part_number=sample_inventory_item.part_number,
            quantity=Decimal("10"),
            unit_of_measure="EA",
            location_id=sample_location.id,
            project_id="project-123",
            work_order_id="wo-456",
            created_by="test_user",
        )
        session.add(txn)
        session.commit()

        found = (
            session.query(InventoryTransactionModel)
            .filter_by(id=txn.id)
            .first()
        )
        assert found.transaction_type == TransactionType.ISSUE
        assert found.project_id == "project-123"

    def test_transfer_transaction(self, session, sample_inventory_item, sample_location):
        """Test creating a transfer transaction."""
        # Create second location
        dest_location = InventoryLocationModel(
            id=str(uuid4()),
            name="Job Site A",
            location_type="jobsite",
            is_active=True,
        )
        session.add(dest_location)
        session.flush()

        txn = InventoryTransactionModel(
            id=str(uuid4()),
            transaction_type=TransactionType.TRANSFER,
            part_id=sample_inventory_item.part_id,
            part_number=sample_inventory_item.part_number,
            quantity=Decimal("25"),
            unit_of_measure="EA",
            location_id=sample_location.id,
            from_location_id=sample_location.id,
            to_location_id=dest_location.id,
            created_by="test_user",
        )
        session.add(txn)
        session.commit()

        found = (
            session.query(InventoryTransactionModel)
            .filter_by(id=txn.id)
            .first()
        )
        assert found.from_location_id == sample_location.id
        assert found.to_location_id == dest_location.id

    def test_transaction_history(
        self, session, sample_inventory_item, sample_location
    ):
        """Test querying transaction history."""
        # Create multiple transactions
        for i in range(5):
            txn = InventoryTransactionModel(
                id=str(uuid4()),
                transaction_type=TransactionType.RECEIPT if i % 2 == 0 else TransactionType.ISSUE,
                part_id=sample_inventory_item.part_id,
                part_number=sample_inventory_item.part_number,
                quantity=Decimal("10"),
                unit_of_measure="EA",
                location_id=sample_location.id,
                created_by="test_user",
            )
            session.add(txn)
        session.commit()

        # Query history
        history = (
            session.query(InventoryTransactionModel)
            .filter_by(part_id=sample_inventory_item.part_id)
            .order_by(InventoryTransactionModel.transaction_date.desc())
            .all()
        )
        assert len(history) == 5

        # Count by type
        receipts = [t for t in history if t.transaction_type == TransactionType.RECEIPT]
        issues = [t for t in history if t.transaction_type == TransactionType.ISSUE]
        assert len(receipts) == 3
        assert len(issues) == 2
