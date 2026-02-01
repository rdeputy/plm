"""
Inventory Repository

Data access layer for inventory operations.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import uuid4

from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from plm.db.models import (
    InventoryLocationModel,
    InventoryItemModel,
    InventoryTransactionModel,
)
from .models import (
    InventoryLocation,
    InventoryItem,
    InventoryTransaction,
    TransactionType,
)


class InventoryRepository:
    """Repository for inventory data access."""

    def __init__(self, session: Session):
        self.session = session

    # -------------------------------------------------------------------------
    # Location Operations
    # -------------------------------------------------------------------------

    def create_location(self, location: InventoryLocation) -> InventoryLocation:
        """Create a new inventory location."""
        model = InventoryLocationModel(
            id=location.id or str(uuid4()),
            name=location.name,
            location_type=location.location_type,
            address=location.address,
            is_active=location.is_active,
            project_id=location.project_id,
            vendor_id=location.vendor_id,
        )
        self.session.add(model)
        self.session.flush()
        location.id = model.id
        return location

    def get_location(self, location_id: str) -> Optional[InventoryLocation]:
        """Get a location by ID."""
        model = self.session.query(InventoryLocationModel).filter_by(id=location_id).first()
        if not model:
            return None
        return self._model_to_location(model)

    def get_location_by_name(self, name: str) -> Optional[InventoryLocation]:
        """Get a location by name."""
        model = self.session.query(InventoryLocationModel).filter_by(name=name).first()
        if not model:
            return None
        return self._model_to_location(model)

    def list_locations(
        self,
        location_type: Optional[str] = None,
        is_active: Optional[bool] = None,
        project_id: Optional[str] = None,
    ) -> list[InventoryLocation]:
        """List locations with optional filters."""
        query = self.session.query(InventoryLocationModel)
        if location_type:
            query = query.filter_by(location_type=location_type)
        if is_active is not None:
            query = query.filter_by(is_active=is_active)
        if project_id:
            query = query.filter_by(project_id=project_id)
        return [self._model_to_location(m) for m in query.all()]

    def update_location(self, location: InventoryLocation) -> InventoryLocation:
        """Update a location."""
        model = self.session.query(InventoryLocationModel).filter_by(id=location.id).first()
        if model:
            model.name = location.name
            model.location_type = location.location_type
            model.address = location.address
            model.is_active = location.is_active
            model.project_id = location.project_id
            model.vendor_id = location.vendor_id
            self.session.flush()
        return location

    def _model_to_location(self, model: InventoryLocationModel) -> InventoryLocation:
        """Convert DB model to domain model."""
        return InventoryLocation(
            id=model.id,
            name=model.name,
            location_type=model.location_type,
            address=model.address,
            is_active=model.is_active,
            project_id=model.project_id,
            vendor_id=model.vendor_id,
        )

    # -------------------------------------------------------------------------
    # Inventory Item Operations
    # -------------------------------------------------------------------------

    def get_item(self, item_id: str) -> Optional[InventoryItem]:
        """Get an inventory item by ID."""
        model = self.session.query(InventoryItemModel).filter_by(id=item_id).first()
        if not model:
            return None
        return self._model_to_item(model)

    def get_item_by_part_location(
        self, part_id: str, location_id: str
    ) -> Optional[InventoryItem]:
        """Get inventory item for a part at a specific location."""
        model = (
            self.session.query(InventoryItemModel)
            .filter_by(part_id=part_id, location_id=location_id)
            .first()
        )
        if not model:
            return None
        return self._model_to_item(model)

    def get_or_create_item(
        self, part_id: str, part_number: str, location_id: str
    ) -> InventoryItem:
        """Get existing inventory item or create new one."""
        item = self.get_item_by_part_location(part_id, location_id)
        if item:
            return item

        model = InventoryItemModel(
            id=str(uuid4()),
            part_id=part_id,
            part_number=part_number,
            location_id=location_id,
            on_hand=Decimal("0"),
            allocated=Decimal("0"),
            on_order=Decimal("0"),
            unit_cost=Decimal("0"),
            total_value=Decimal("0"),
        )
        self.session.add(model)
        self.session.flush()
        return self._model_to_item(model)

    def list_items_by_part(self, part_id: str) -> list[InventoryItem]:
        """List all inventory items for a part across all locations."""
        models = self.session.query(InventoryItemModel).filter_by(part_id=part_id).all()
        return [self._model_to_item(m) for m in models]

    def list_items_by_location(self, location_id: str) -> list[InventoryItem]:
        """List all inventory items at a location."""
        models = self.session.query(InventoryItemModel).filter_by(location_id=location_id).all()
        return [self._model_to_item(m) for m in models]

    def list_items_needing_reorder(self) -> list[InventoryItem]:
        """List items where available <= reorder_point."""
        models = (
            self.session.query(InventoryItemModel)
            .filter(
                InventoryItemModel.reorder_point.isnot(None),
                (InventoryItemModel.on_hand - InventoryItemModel.allocated)
                <= InventoryItemModel.reorder_point,
            )
            .all()
        )
        return [self._model_to_item(m) for m in models]

    def update_item(self, item: InventoryItem) -> InventoryItem:
        """Update an inventory item."""
        model = self.session.query(InventoryItemModel).filter_by(id=item.id).first()
        if model:
            model.on_hand = item.on_hand
            model.allocated = item.allocated
            model.on_order = item.on_order
            model.unit_cost = item.unit_cost
            model.total_value = item.total_value
            model.last_count_date = item.last_count_date
            model.last_receipt_date = item.last_receipt_date
            model.last_issue_date = item.last_issue_date
            model.reorder_point = item.reorder_point
            model.reorder_qty = item.reorder_qty
            self.session.flush()
        return item

    def _model_to_item(self, model: InventoryItemModel) -> InventoryItem:
        """Convert DB model to domain model."""
        return InventoryItem(
            id=model.id,
            part_id=model.part_id,
            part_number=model.part_number,
            location_id=model.location_id,
            on_hand=model.on_hand,
            allocated=model.allocated,
            on_order=model.on_order,
            unit_cost=model.unit_cost,
            total_value=model.total_value,
            last_count_date=model.last_count_date,
            last_receipt_date=model.last_receipt_date,
            last_issue_date=model.last_issue_date,
            reorder_point=model.reorder_point,
            reorder_qty=model.reorder_qty,
        )

    # -------------------------------------------------------------------------
    # Transaction Operations
    # -------------------------------------------------------------------------

    def create_transaction(self, txn: InventoryTransaction) -> InventoryTransaction:
        """Create a new inventory transaction."""
        model = InventoryTransactionModel(
            id=txn.id or str(uuid4()),
            transaction_type=txn.transaction_type.value,
            part_id=txn.part_id,
            part_number=txn.part_number,
            quantity=txn.quantity,
            unit_of_measure=txn.unit_of_measure,
            location_id=txn.location_id,
            from_location_id=txn.from_location_id,
            to_location_id=txn.to_location_id,
            po_id=txn.po_id,
            project_id=txn.project_id,
            work_order_id=txn.work_order_id,
            unit_cost=txn.unit_cost,
            total_cost=txn.total_cost,
            transaction_date=txn.transaction_date,
            created_by=txn.created_by,
            notes=txn.notes,
            lot_number=txn.lot_number,
            serial_number=txn.serial_number,
        )
        self.session.add(model)
        self.session.flush()
        txn.id = model.id
        return txn

    def get_transaction(self, txn_id: str) -> Optional[InventoryTransaction]:
        """Get a transaction by ID."""
        model = self.session.query(InventoryTransactionModel).filter_by(id=txn_id).first()
        if not model:
            return None
        return self._model_to_transaction(model)

    def list_transactions(
        self,
        part_id: Optional[str] = None,
        location_id: Optional[str] = None,
        transaction_type: Optional[TransactionType] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> list[InventoryTransaction]:
        """List transactions with filters."""
        query = self.session.query(InventoryTransactionModel)

        if part_id:
            query = query.filter_by(part_id=part_id)
        if location_id:
            query = query.filter_by(location_id=location_id)
        if transaction_type:
            query = query.filter_by(transaction_type=transaction_type.value)
        if from_date:
            query = query.filter(InventoryTransactionModel.transaction_date >= from_date)
        if to_date:
            query = query.filter(InventoryTransactionModel.transaction_date <= to_date)

        query = query.order_by(InventoryTransactionModel.transaction_date.desc())
        query = query.limit(limit)

        return [self._model_to_transaction(m) for m in query.all()]

    def get_transaction_summary(
        self,
        part_id: str,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> dict[str, Decimal]:
        """Get transaction totals by type for a part."""
        query = self.session.query(
            InventoryTransactionModel.transaction_type,
            func.sum(InventoryTransactionModel.quantity).label("total"),
        ).filter_by(part_id=part_id)

        if from_date:
            query = query.filter(InventoryTransactionModel.transaction_date >= from_date)
        if to_date:
            query = query.filter(InventoryTransactionModel.transaction_date <= to_date)

        query = query.group_by(InventoryTransactionModel.transaction_type)

        return {row[0]: row[1] or Decimal("0") for row in query.all()}

    def _model_to_transaction(self, model: InventoryTransactionModel) -> InventoryTransaction:
        """Convert DB model to domain model."""
        return InventoryTransaction(
            id=model.id,
            transaction_type=TransactionType(model.transaction_type),
            part_id=model.part_id,
            part_number=model.part_number,
            quantity=model.quantity,
            unit_of_measure=model.unit_of_measure,
            location_id=model.location_id,
            from_location_id=model.from_location_id,
            to_location_id=model.to_location_id,
            po_id=model.po_id,
            project_id=model.project_id,
            work_order_id=model.work_order_id,
            unit_cost=model.unit_cost,
            total_cost=model.total_cost,
            transaction_date=model.transaction_date,
            created_by=model.created_by,
            notes=model.notes,
            lot_number=model.lot_number,
            serial_number=model.serial_number,
        )
