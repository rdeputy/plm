"""
MRP Engine

Material Requirements Planning engine for PLM.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Optional, Protocol


class ExceptionType(str, Enum):
    """MRP exception types."""
    RESCHEDULE_IN = "reschedule_in"      # Move order earlier
    RESCHEDULE_OUT = "reschedule_out"    # Move order later
    CANCEL = "cancel"                     # Cancel order (no longer needed)
    EXPEDITE = "expedite"                 # Order date in past


@dataclass
class MaterialRequirement:
    """A material requirement from the schedule."""
    part_id: str
    need_date: date
    quantity: Decimal
    source: str  # BOM item or demand source


@dataclass
class PlannedOrder:
    """A planned purchase or work order."""
    id: str
    part_id: str
    part_number: str
    quantity: Decimal
    unit_of_measure: str

    # Dates
    need_date: date           # When needed on site
    order_date: date          # When to place order (need - lead time)

    # Source
    demand_source: str        # BOM item reference
    pegging: list[str] = field(default_factory=list)  # Trace back to parent demands

    # Status
    status: str = "planned"   # planned, firmed, released
    released_po_id: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "part_id": self.part_id,
            "part_number": self.part_number,
            "quantity": float(self.quantity),
            "unit_of_measure": self.unit_of_measure,
            "need_date": self.need_date.isoformat(),
            "order_date": self.order_date.isoformat(),
            "demand_source": self.demand_source,
            "status": self.status,
            "released_po_id": self.released_po_id,
        }


@dataclass
class ExceptionMessage:
    """MRP exception requiring attention."""
    id: str
    part_id: str
    part_number: str
    exception_type: ExceptionType
    message: str
    current_date: Optional[date] = None
    suggested_date: Optional[date] = None
    quantity: Decimal = Decimal("0")
    priority: str = "info"    # critical, warning, info

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "part_id": self.part_id,
            "part_number": self.part_number,
            "exception_type": self.exception_type.value,
            "message": self.message,
            "current_date": self.current_date.isoformat() if self.current_date else None,
            "suggested_date": self.suggested_date.isoformat() if self.suggested_date else None,
            "quantity": float(self.quantity),
            "priority": self.priority,
        }


@dataclass
class MRPRun:
    """A complete MRP calculation run."""
    id: str
    project_id: str
    run_date: datetime
    planning_horizon_days: int
    status: str  # running, completed, failed

    # Results
    planned_orders: list[PlannedOrder] = field(default_factory=list)
    exception_messages: list[ExceptionMessage] = field(default_factory=list)

    # Statistics
    total_items_processed: int = 0
    total_planned_orders: int = 0
    total_exceptions: int = 0
    execution_time_ms: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "run_date": self.run_date.isoformat(),
            "planning_horizon_days": self.planning_horizon_days,
            "status": self.status,
            "planned_orders": [o.to_dict() for o in self.planned_orders],
            "exception_messages": [e.to_dict() for e in self.exception_messages],
            "statistics": {
                "total_items_processed": self.total_items_processed,
                "total_planned_orders": self.total_planned_orders,
                "total_exceptions": self.total_exceptions,
                "execution_time_ms": self.execution_time_ms,
            },
        }


# Protocol interfaces for external systems

class PLMInterface(Protocol):
    """Interface for PLM system."""
    def explode_bom(self, project_id: str, levels: int = -1) -> list: ...
    def get_part(self, part_id: str) -> object: ...


class ScheduleInterface(Protocol):
    """Interface for HCT schedule system."""
    def get_material_schedule(
        self, project_id: str, start_date: date, end_date: date
    ) -> dict: ...


class InventoryInterface(Protocol):
    """Interface for Procurement/Inventory system."""
    def get_inventory(self) -> dict[str, Decimal]: ...
    def get_open_orders(self) -> dict[str, Decimal]: ...


class MRPEngine:
    """
    Material Requirements Planning engine.

    Runs MRP calculation for a project based on:
    - BOM from PLM
    - Schedule from HCT
    - Inventory from Procurement
    """

    def __init__(
        self,
        plm: PLMInterface,
        schedule: ScheduleInterface,
        inventory: InventoryInterface,
    ):
        self.plm = plm
        self.schedule = schedule
        self.inventory = inventory
        self._order_counter = 0

    def run_mrp(self, project_id: str, horizon_days: int = 90) -> MRPRun:
        """
        Execute MRP for a project.

        Args:
            project_id: Project to run MRP for
            horizon_days: Planning horizon in days

        Returns:
            MRPRun with planned orders and exceptions
        """
        import time
        import uuid

        start_time = time.time()
        today = date.today()
        end_date = today + timedelta(days=horizon_days)

        run = MRPRun(
            id=str(uuid.uuid4()),
            project_id=project_id,
            run_date=datetime.now(),
            planning_horizon_days=horizon_days,
            status="running",
        )

        try:
            # 1. Explode BOM
            bom_items = self.plm.explode_bom(project_id, levels=-1)

            # 2. Get schedule requirements
            schedule_data = self.schedule.get_material_schedule(project_id, today, end_date)

            # 3. Get inventory position
            on_hand = self.inventory.get_inventory()
            on_order = self.inventory.get_open_orders()

            # 4. Process each item (sorted by low-level code)
            sorted_items = sorted(bom_items, key=lambda x: getattr(x, 'low_level_code', 0))

            for item in sorted_items:
                run.total_items_processed += 1
                self._process_item(
                    item=item,
                    schedule_data=schedule_data,
                    on_hand=on_hand,
                    on_order=on_order,
                    today=today,
                    run=run,
                )

            run.status = "completed"
            run.total_planned_orders = len(run.planned_orders)
            run.total_exceptions = len(run.exception_messages)

        except Exception as e:
            run.status = "failed"
            run.exception_messages.append(ExceptionMessage(
                id=str(uuid.uuid4()),
                part_id="",
                part_number="",
                exception_type=ExceptionType.CANCEL,
                message=f"MRP run failed: {str(e)}",
                priority="critical",
            ))

        run.execution_time_ms = int((time.time() - start_time) * 1000)
        return run

    def _process_item(
        self,
        item,
        schedule_data: dict,
        on_hand: dict[str, Decimal],
        on_order: dict[str, Decimal],
        today: date,
        run: MRPRun,
    ) -> None:
        """Process a single BOM item for MRP."""
        import uuid

        part_id = getattr(item, 'part_id', item.get('part_id') if isinstance(item, dict) else None)
        if not part_id:
            return

        # Get requirements from schedule
        requirements = schedule_data.get(part_id, [])
        if not requirements:
            return

        # Calculate available quantity
        available = on_hand.get(part_id, Decimal("0")) + on_order.get(part_id, Decimal("0"))

        # Get part info
        part = self.plm.get_part(part_id)
        lead_time = getattr(part, 'lead_time_days', 14) or 14
        part_number = getattr(part, 'part_number', str(part_id))
        unit = getattr(part, 'unit_of_measure', 'EA')
        if hasattr(unit, 'value'):
            unit = unit.value

        for req in requirements:
            need_date = req.need_date if hasattr(req, 'need_date') else req.get('need_date')
            req_qty = req.quantity if hasattr(req, 'quantity') else req.get('quantity', Decimal("0"))
            source = req.source if hasattr(req, 'source') else req.get('source', '')

            # Net requirements
            net_qty = req_qty - available
            if net_qty <= 0:
                available -= req_qty
                continue

            # Calculate order date
            order_date = need_date - timedelta(days=lead_time)

            # Apply lot sizing
            order_qty = self._lot_size(net_qty, part)

            # Check if order date is in past
            if order_date < today:
                days_late = (today - order_date).days
                run.exception_messages.append(ExceptionMessage(
                    id=str(uuid.uuid4()),
                    part_id=part_id,
                    part_number=part_number,
                    exception_type=ExceptionType.EXPEDITE,
                    message=f"Order should have been placed {days_late} days ago",
                    current_date=today,
                    suggested_date=today,
                    quantity=order_qty,
                    priority="critical" if days_late > 7 else "warning",
                ))
                order_date = today

            # Create planned order
            self._order_counter += 1
            run.planned_orders.append(PlannedOrder(
                id=str(uuid.uuid4()),
                part_id=part_id,
                part_number=part_number,
                quantity=order_qty,
                unit_of_measure=unit,
                need_date=need_date,
                order_date=order_date,
                demand_source=source,
                status="planned",
            ))

            # Update available for subsequent requirements
            available = order_qty - net_qty

    def _lot_size(self, quantity: Decimal, part) -> Decimal:
        """Apply lot sizing rules."""
        min_qty = getattr(part, 'min_order_qty', None) or Decimal("1")
        multiple = getattr(part, 'order_multiple', None) or Decimal("1")

        # Round up to minimum
        qty = max(quantity, min_qty)

        # Round up to multiple
        if multiple > 0 and qty % multiple != 0:
            qty = ((qty // multiple) + 1) * multiple

        return qty

    def release_orders(self, order_ids: list[str], run: MRPRun) -> list[PlannedOrder]:
        """
        Mark planned orders as released (firmed).

        In a full implementation, this would create actual POs.
        """
        released = []
        for order in run.planned_orders:
            if order.id in order_ids and order.status == "planned":
                order.status = "firmed"
                released.append(order)
        return released
