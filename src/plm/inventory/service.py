"""
Inventory Service

Business logic for inventory management including:
- Transaction processing (receipt, issue, transfer, adjust)
- Reorder point calculations and suggestions
- Transfer management between locations
- Stock level queries and reports
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import uuid4

from .models import (
    InventoryLocation,
    InventoryItem,
    InventoryTransaction,
    TransactionType,
    StockLevel,
)
from .repository import InventoryRepository


class InventoryError(Exception):
    """Base exception for inventory operations."""

    pass


class InsufficientStockError(InventoryError):
    """Raised when there isn't enough stock for an operation."""

    def __init__(self, part_id: str, requested: Decimal, available: Decimal):
        self.part_id = part_id
        self.requested = requested
        self.available = available
        super().__init__(
            f"Insufficient stock for part {part_id}: "
            f"requested {requested}, available {available}"
        )


class LocationNotFoundError(InventoryError):
    """Raised when a location doesn't exist."""

    pass


class InvalidTransactionError(InventoryError):
    """Raised for invalid transaction parameters."""

    pass


@dataclass
class ReorderSuggestion:
    """Suggestion for reordering inventory."""

    part_id: str
    part_number: str
    location_id: str
    current_available: Decimal
    reorder_point: Decimal
    suggested_qty: Decimal
    priority: str  # urgent, high, normal


@dataclass
class TransferRequest:
    """Request to transfer inventory between locations."""

    id: str
    part_id: str
    part_number: str
    from_location_id: str
    to_location_id: str
    quantity: Decimal
    requested_by: str
    requested_at: datetime
    status: str = "pending"  # pending, approved, in_transit, completed, cancelled
    notes: Optional[str] = None


class InventoryService:
    """
    Service for inventory management operations.

    Handles transaction processing, reorder calculations,
    and stock level management.
    """

    def __init__(self, repository: InventoryRepository):
        self.repo = repository

    # -------------------------------------------------------------------------
    # Transaction Processing
    # -------------------------------------------------------------------------

    def receive(
        self,
        part_id: str,
        part_number: str,
        location_id: str,
        quantity: Decimal,
        unit_cost: Decimal,
        unit_of_measure: str = "EA",
        po_id: Optional[str] = None,
        lot_number: Optional[str] = None,
        serial_number: Optional[str] = None,
        created_by: str = "system",
        notes: Optional[str] = None,
    ) -> InventoryTransaction:
        """
        Receive inventory from a purchase order.

        Increases on-hand quantity and updates costs.
        """
        if quantity <= 0:
            raise InvalidTransactionError("Receive quantity must be positive")

        # Get or create inventory item
        item = self.repo.get_or_create_item(part_id, part_number, location_id)

        # Update quantities using weighted average cost
        old_value = item.on_hand * item.unit_cost
        new_value = quantity * unit_cost
        new_on_hand = item.on_hand + quantity

        if new_on_hand > 0:
            item.unit_cost = (old_value + new_value) / new_on_hand
        item.on_hand = new_on_hand
        item.total_value = item.on_hand * item.unit_cost
        item.last_receipt_date = datetime.now()

        self.repo.update_item(item)

        # Create transaction record
        txn = InventoryTransaction(
            id=str(uuid4()),
            transaction_type=TransactionType.RECEIPT,
            part_id=part_id,
            part_number=part_number,
            quantity=quantity,
            unit_of_measure=unit_of_measure,
            location_id=location_id,
            po_id=po_id,
            unit_cost=unit_cost,
            total_cost=quantity * unit_cost,
            created_by=created_by,
            notes=notes,
            lot_number=lot_number,
            serial_number=serial_number,
        )
        return self.repo.create_transaction(txn)

    def issue(
        self,
        part_id: str,
        part_number: str,
        location_id: str,
        quantity: Decimal,
        unit_of_measure: str = "EA",
        project_id: Optional[str] = None,
        work_order_id: Optional[str] = None,
        created_by: str = "system",
        notes: Optional[str] = None,
        allow_negative: bool = False,
    ) -> InventoryTransaction:
        """
        Issue inventory to a project or work order.

        Decreases on-hand quantity. Checks for sufficient stock
        unless allow_negative is True.
        """
        if quantity <= 0:
            raise InvalidTransactionError("Issue quantity must be positive")

        item = self.repo.get_item_by_part_location(part_id, location_id)
        if not item:
            raise InventoryError(f"No inventory found for part {part_id} at {location_id}")

        available = item.on_hand - item.allocated
        if quantity > available and not allow_negative:
            raise InsufficientStockError(part_id, quantity, available)

        # Update quantities
        item.on_hand -= quantity
        item.total_value = item.on_hand * item.unit_cost
        item.last_issue_date = datetime.now()

        # If there was an allocation, reduce it
        if item.allocated > 0:
            item.allocated = max(Decimal("0"), item.allocated - quantity)

        self.repo.update_item(item)

        # Create transaction record
        txn = InventoryTransaction(
            id=str(uuid4()),
            transaction_type=TransactionType.ISSUE,
            part_id=part_id,
            part_number=part_number,
            quantity=-quantity,  # Negative for issues
            unit_of_measure=unit_of_measure,
            location_id=location_id,
            project_id=project_id,
            work_order_id=work_order_id,
            unit_cost=item.unit_cost,
            total_cost=quantity * item.unit_cost,
            created_by=created_by,
            notes=notes,
        )
        return self.repo.create_transaction(txn)

    def transfer(
        self,
        part_id: str,
        part_number: str,
        from_location_id: str,
        to_location_id: str,
        quantity: Decimal,
        unit_of_measure: str = "EA",
        created_by: str = "system",
        notes: Optional[str] = None,
    ) -> tuple[InventoryTransaction, InventoryTransaction]:
        """
        Transfer inventory between locations.

        Creates two transactions: issue from source, receipt at destination.
        Returns tuple of (from_txn, to_txn).
        """
        if quantity <= 0:
            raise InvalidTransactionError("Transfer quantity must be positive")

        if from_location_id == to_location_id:
            raise InvalidTransactionError("Cannot transfer to same location")

        # Check source inventory
        from_item = self.repo.get_item_by_part_location(part_id, from_location_id)
        if not from_item:
            raise InventoryError(f"No inventory at source location {from_location_id}")

        available = from_item.on_hand - from_item.allocated
        if quantity > available:
            raise InsufficientStockError(part_id, quantity, available)

        # Get or create destination item
        to_item = self.repo.get_or_create_item(part_id, part_number, to_location_id)

        # Update source
        from_item.on_hand -= quantity
        from_item.total_value = from_item.on_hand * from_item.unit_cost
        self.repo.update_item(from_item)

        # Update destination (keep unit cost from source)
        to_item.on_hand += quantity
        to_item.unit_cost = from_item.unit_cost
        to_item.total_value = to_item.on_hand * to_item.unit_cost
        to_item.last_receipt_date = datetime.now()
        self.repo.update_item(to_item)

        # Create transaction records
        from_txn = InventoryTransaction(
            id=str(uuid4()),
            transaction_type=TransactionType.TRANSFER,
            part_id=part_id,
            part_number=part_number,
            quantity=-quantity,
            unit_of_measure=unit_of_measure,
            location_id=from_location_id,
            from_location_id=from_location_id,
            to_location_id=to_location_id,
            unit_cost=from_item.unit_cost,
            total_cost=quantity * from_item.unit_cost,
            created_by=created_by,
            notes=notes,
        )
        from_txn = self.repo.create_transaction(from_txn)

        to_txn = InventoryTransaction(
            id=str(uuid4()),
            transaction_type=TransactionType.TRANSFER,
            part_id=part_id,
            part_number=part_number,
            quantity=quantity,
            unit_of_measure=unit_of_measure,
            location_id=to_location_id,
            from_location_id=from_location_id,
            to_location_id=to_location_id,
            unit_cost=from_item.unit_cost,
            total_cost=quantity * from_item.unit_cost,
            created_by=created_by,
            notes=notes,
        )
        to_txn = self.repo.create_transaction(to_txn)

        return from_txn, to_txn

    def adjust(
        self,
        part_id: str,
        part_number: str,
        location_id: str,
        new_quantity: Decimal,
        unit_of_measure: str = "EA",
        created_by: str = "system",
        notes: Optional[str] = None,
    ) -> InventoryTransaction:
        """
        Adjust inventory quantity (physical count adjustment).

        Sets on-hand to new_quantity, creating adjustment transaction.
        """
        item = self.repo.get_or_create_item(part_id, part_number, location_id)

        adjustment = new_quantity - item.on_hand

        if adjustment == 0:
            raise InvalidTransactionError("No adjustment needed - quantities match")

        # Update quantity
        item.on_hand = new_quantity
        item.total_value = item.on_hand * item.unit_cost
        item.last_count_date = datetime.now()
        self.repo.update_item(item)

        # Create transaction record
        txn = InventoryTransaction(
            id=str(uuid4()),
            transaction_type=TransactionType.ADJUSTMENT,
            part_id=part_id,
            part_number=part_number,
            quantity=adjustment,
            unit_of_measure=unit_of_measure,
            location_id=location_id,
            unit_cost=item.unit_cost,
            total_cost=abs(adjustment) * item.unit_cost,
            created_by=created_by,
            notes=notes or f"Count adjustment from {item.on_hand - adjustment} to {new_quantity}",
        )
        return self.repo.create_transaction(txn)

    def reserve(
        self,
        part_id: str,
        location_id: str,
        quantity: Decimal,
        project_id: Optional[str] = None,
        work_order_id: Optional[str] = None,
        created_by: str = "system",
        notes: Optional[str] = None,
    ) -> InventoryTransaction:
        """
        Reserve inventory for a project/work order (soft allocation).

        Does not change on-hand but increases allocated quantity.
        """
        if quantity <= 0:
            raise InvalidTransactionError("Reserve quantity must be positive")

        item = self.repo.get_item_by_part_location(part_id, location_id)
        if not item:
            raise InventoryError(f"No inventory found for part {part_id} at {location_id}")

        available = item.on_hand - item.allocated
        if quantity > available:
            raise InsufficientStockError(part_id, quantity, available)

        item.allocated += quantity
        self.repo.update_item(item)

        txn = InventoryTransaction(
            id=str(uuid4()),
            transaction_type=TransactionType.RESERVE,
            part_id=part_id,
            part_number=item.part_number,
            quantity=quantity,
            unit_of_measure="EA",
            location_id=location_id,
            project_id=project_id,
            work_order_id=work_order_id,
            unit_cost=item.unit_cost,
            total_cost=quantity * item.unit_cost,
            created_by=created_by,
            notes=notes,
        )
        return self.repo.create_transaction(txn)

    def unreserve(
        self,
        part_id: str,
        location_id: str,
        quantity: Decimal,
        project_id: Optional[str] = None,
        work_order_id: Optional[str] = None,
        created_by: str = "system",
        notes: Optional[str] = None,
    ) -> InventoryTransaction:
        """
        Release a reservation.

        Decreases allocated quantity without changing on-hand.
        """
        if quantity <= 0:
            raise InvalidTransactionError("Unreserve quantity must be positive")

        item = self.repo.get_item_by_part_location(part_id, location_id)
        if not item:
            raise InventoryError(f"No inventory found for part {part_id} at {location_id}")

        if quantity > item.allocated:
            raise InvalidTransactionError(
                f"Cannot unreserve {quantity} - only {item.allocated} allocated"
            )

        item.allocated -= quantity
        self.repo.update_item(item)

        txn = InventoryTransaction(
            id=str(uuid4()),
            transaction_type=TransactionType.UNRESERVE,
            part_id=part_id,
            part_number=item.part_number,
            quantity=-quantity,
            unit_of_measure="EA",
            location_id=location_id,
            project_id=project_id,
            work_order_id=work_order_id,
            unit_cost=item.unit_cost,
            total_cost=quantity * item.unit_cost,
            created_by=created_by,
            notes=notes,
        )
        return self.repo.create_transaction(txn)

    def scrap(
        self,
        part_id: str,
        part_number: str,
        location_id: str,
        quantity: Decimal,
        unit_of_measure: str = "EA",
        created_by: str = "system",
        notes: Optional[str] = None,
    ) -> InventoryTransaction:
        """
        Record scrapped/damaged inventory.

        Decreases on-hand and creates scrap transaction.
        """
        if quantity <= 0:
            raise InvalidTransactionError("Scrap quantity must be positive")

        item = self.repo.get_item_by_part_location(part_id, location_id)
        if not item:
            raise InventoryError(f"No inventory found for part {part_id} at {location_id}")

        if quantity > item.on_hand:
            raise InsufficientStockError(part_id, quantity, item.on_hand)

        item.on_hand -= quantity
        item.total_value = item.on_hand * item.unit_cost
        self.repo.update_item(item)

        txn = InventoryTransaction(
            id=str(uuid4()),
            transaction_type=TransactionType.SCRAP,
            part_id=part_id,
            part_number=part_number,
            quantity=-quantity,
            unit_of_measure=unit_of_measure,
            location_id=location_id,
            unit_cost=item.unit_cost,
            total_cost=quantity * item.unit_cost,
            created_by=created_by,
            notes=notes,
        )
        return self.repo.create_transaction(txn)

    # -------------------------------------------------------------------------
    # Reorder Management
    # -------------------------------------------------------------------------

    def get_reorder_suggestions(self) -> list[ReorderSuggestion]:
        """
        Get list of items that need reordering.

        Returns suggestions sorted by priority.
        """
        items = self.repo.list_items_needing_reorder()
        suggestions = []

        for item in items:
            if item.reorder_point is None:
                continue

            available = item.on_hand - item.allocated

            # Determine priority
            if available <= 0:
                priority = "urgent"
            elif available <= item.reorder_point * Decimal("0.5"):
                priority = "high"
            else:
                priority = "normal"

            # Calculate suggested quantity
            suggested_qty = item.reorder_qty or (item.reorder_point * 2)

            suggestions.append(
                ReorderSuggestion(
                    part_id=item.part_id,
                    part_number=item.part_number,
                    location_id=item.location_id,
                    current_available=available,
                    reorder_point=item.reorder_point,
                    suggested_qty=suggested_qty,
                    priority=priority,
                )
            )

        # Sort by priority
        priority_order = {"urgent": 0, "high": 1, "normal": 2}
        suggestions.sort(key=lambda s: priority_order[s.priority])

        return suggestions

    def set_reorder_point(
        self,
        part_id: str,
        location_id: str,
        reorder_point: Decimal,
        reorder_qty: Optional[Decimal] = None,
    ) -> InventoryItem:
        """Set reorder point and quantity for an item."""
        item = self.repo.get_item_by_part_location(part_id, location_id)
        if not item:
            raise InventoryError(f"No inventory found for part {part_id} at {location_id}")

        item.reorder_point = reorder_point
        if reorder_qty is not None:
            item.reorder_qty = reorder_qty

        return self.repo.update_item(item)

    # -------------------------------------------------------------------------
    # Stock Level Queries
    # -------------------------------------------------------------------------

    def get_stock_level(self, part_id: str, part_name: str = "") -> StockLevel:
        """Get aggregated stock level for a part across all locations."""
        items = self.repo.list_items_by_part(part_id)
        if not items:
            raise InventoryError(f"No inventory found for part {part_id}")
        return StockLevel.from_items(items, part_name)

    def get_stock_at_location(
        self, part_id: str, location_id: str
    ) -> Optional[InventoryItem]:
        """Get stock level for a part at a specific location."""
        return self.repo.get_item_by_part_location(part_id, location_id)

    def get_location_inventory(self, location_id: str) -> list[InventoryItem]:
        """Get all inventory items at a location."""
        return self.repo.list_items_by_location(location_id)

    def get_inventory_value(self, location_id: Optional[str] = None) -> Decimal:
        """Get total inventory value, optionally filtered by location."""
        if location_id:
            items = self.repo.list_items_by_location(location_id)
        else:
            # Get all items - simplified for now
            locations = self.repo.list_locations()
            items = []
            for loc in locations:
                items.extend(self.repo.list_items_by_location(loc.id))

        return sum((item.total_value for item in items), Decimal("0"))

    # -------------------------------------------------------------------------
    # Transaction History
    # -------------------------------------------------------------------------

    def get_transaction_history(
        self,
        part_id: Optional[str] = None,
        location_id: Optional[str] = None,
        transaction_type: Optional[TransactionType] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> list[InventoryTransaction]:
        """Get transaction history with filters."""
        return self.repo.list_transactions(
            part_id=part_id,
            location_id=location_id,
            transaction_type=transaction_type,
            from_date=from_date,
            to_date=to_date,
            limit=limit,
        )

    def get_part_movements(
        self,
        part_id: str,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> dict[str, Decimal]:
        """Get summary of movements for a part by transaction type."""
        return self.repo.get_transaction_summary(part_id, from_date, to_date)

    # -------------------------------------------------------------------------
    # Location Management
    # -------------------------------------------------------------------------

    def create_location(self, location: InventoryLocation) -> InventoryLocation:
        """Create a new inventory location."""
        return self.repo.create_location(location)

    def get_location(self, location_id: str) -> Optional[InventoryLocation]:
        """Get a location by ID."""
        return self.repo.get_location(location_id)

    def list_locations(
        self,
        location_type: Optional[str] = None,
        is_active: bool = True,
    ) -> list[InventoryLocation]:
        """List locations with optional filters."""
        return self.repo.list_locations(location_type=location_type, is_active=is_active)

    def deactivate_location(self, location_id: str) -> InventoryLocation:
        """Deactivate a location (soft delete)."""
        location = self.repo.get_location(location_id)
        if not location:
            raise LocationNotFoundError(f"Location {location_id} not found")

        # Check if location has inventory
        items = self.repo.list_items_by_location(location_id)
        if any(item.on_hand > 0 for item in items):
            raise InventoryError(
                f"Cannot deactivate location {location_id} - has inventory on hand"
            )

        location.is_active = False
        return self.repo.update_location(location)
