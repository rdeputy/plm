"""
BOM Models

Bill of Materials definitions for PLM.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from ..parts.models import PartStatus, UnitOfMeasure


class BOMType(str, Enum):
    """Types of BOMs."""
    ENGINEERING = "engineering"     # As-designed
    MANUFACTURING = "manufacturing" # As-built instructions
    SERVICE = "service"             # Replacement parts
    SALES = "sales"                 # Customer-facing options


class Effectivity(str, Enum):
    """When a BOM applies."""
    AS_DESIGNED = "as_designed"     # Original design intent
    AS_APPROVED = "as_approved"     # After ARC/permit approval
    AS_BUILT = "as_built"           # Actual construction
    AS_MAINTAINED = "as_maintained" # Post-construction changes


@dataclass
class BOMItem:
    """
    A line item in a BOM.
    """
    id: str
    bom_id: str

    # Part reference
    part_id: str
    part_number: str
    part_revision: str

    # Quantity
    quantity: Decimal
    unit_of_measure: UnitOfMeasure = UnitOfMeasure.EACH

    # Position
    find_number: int = 0              # Assembly sequence (10, 20, 30...)
    reference_designator: str = ""    # "WALL-NORTH-01", "WINDOW-FR-02"

    # Location
    location: Optional[str] = None    # Where in the assembly
    notes: Optional[str] = None

    # Options/variants
    is_optional: bool = False
    option_code: Optional[str] = None  # "UPG-WINDOWS" for upgrade package

    # Alternates
    alternate_parts: list[str] = field(default_factory=list)

    # Subassembly
    has_sub_bom: bool = False     # True if this part has its own BOM

    # For MRP
    low_level_code: int = 0       # Lowest level in any BOM (for MRP processing)

    @property
    def extended_quantity(self) -> Decimal:
        """Quantity for this item (for rollups)."""
        return self.quantity

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "bom_id": self.bom_id,
            "part_id": self.part_id,
            "part_number": self.part_number,
            "part_revision": self.part_revision,
            "quantity": float(self.quantity),
            "unit_of_measure": self.unit_of_measure.value,
            "find_number": self.find_number,
            "reference_designator": self.reference_designator,
            "location": self.location,
            "is_optional": self.is_optional,
            "option_code": self.option_code,
            "has_sub_bom": self.has_sub_bom,
        }


@dataclass
class BOM:
    """
    Bill of Materials - hierarchical parts list.

    A BOM defines what parts make up an assembly or product.
    """
    id: str
    bom_number: str               # "BOM-HOUSE-MODEL-A-001"
    revision: str
    name: str
    description: Optional[str] = None

    # Parent
    parent_part_id: str = ""          # The assembly/product this BOM defines
    parent_part_revision: str = ""

    # Type and effectivity
    bom_type: BOMType = BOMType.ENGINEERING
    effectivity: Effectivity = Effectivity.AS_DESIGNED

    # Validity
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None

    # Status
    status: PartStatus = PartStatus.DRAFT

    # Items
    items: list[BOMItem] = field(default_factory=list)

    # Metadata
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    released_by: Optional[str] = None
    released_at: Optional[datetime] = None

    # Project linkage
    project_id: Optional[str] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

    @property
    def item_count(self) -> int:
        """Number of line items."""
        return len(self.items)

    @property
    def full_bom_number(self) -> str:
        """BOM number with revision."""
        return f"{self.bom_number}-{self.revision}"

    def add_item(self, item: BOMItem) -> None:
        """Add an item to the BOM."""
        if item.find_number == 0:
            # Auto-assign find number
            max_find = max((i.find_number for i in self.items), default=0)
            item.find_number = max_find + 10
        self.items.append(item)

    def remove_item(self, item_id: str) -> bool:
        """Remove an item from the BOM."""
        for i, item in enumerate(self.items):
            if item.id == item_id:
                self.items.pop(i)
                return True
        return False

    def get_item(self, item_id: str) -> Optional[BOMItem]:
        """Get a specific item."""
        for item in self.items:
            if item.id == item_id:
                return item
        return None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "bom_number": self.bom_number,
            "revision": self.revision,
            "full_bom_number": self.full_bom_number,
            "name": self.name,
            "description": self.description,
            "parent_part_id": self.parent_part_id,
            "bom_type": self.bom_type.value,
            "effectivity": self.effectivity.value,
            "status": self.status.value,
            "item_count": self.item_count,
            "items": [item.to_dict() for item in self.items],
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


@dataclass
class BOMComparison:
    """
    Comparison between two BOM revisions.
    """
    bom_id: str
    from_revision: str
    to_revision: str

    added_items: list[BOMItem] = field(default_factory=list)
    removed_items: list[BOMItem] = field(default_factory=list)
    changed_items: list[dict] = field(default_factory=list)  # {item, field, old_value, new_value}

    cost_delta: Decimal = Decimal("0")
    weight_delta: Decimal = Decimal("0")

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "bom_id": self.bom_id,
            "from_revision": self.from_revision,
            "to_revision": self.to_revision,
            "added_items": [i.to_dict() for i in self.added_items],
            "removed_items": [i.to_dict() for i in self.removed_items],
            "changed_items": self.changed_items,
            "cost_delta": float(self.cost_delta),
            "weight_delta": float(self.weight_delta),
        }


@dataclass
class ExplodedBOMItem:
    """
    A fully exploded BOM item (flattened hierarchy).
    """
    part_id: str
    part_number: str
    part_name: str
    level: int                    # 0 = top, 1 = first child, etc.
    path: str                     # "HOUSE/WALL-N/STUD" hierarchy path
    quantity: Decimal             # Extended quantity at this level
    unit_of_measure: UnitOfMeasure
    unit_cost: Optional[Decimal]
    extended_cost: Optional[Decimal]
    reference_designator: str
    is_leaf: bool                 # True if no children

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "part_id": self.part_id,
            "part_number": self.part_number,
            "part_name": self.part_name,
            "level": self.level,
            "path": self.path,
            "quantity": float(self.quantity),
            "unit_of_measure": self.unit_of_measure.value,
            "unit_cost": float(self.unit_cost) if self.unit_cost else None,
            "extended_cost": float(self.extended_cost) if self.extended_cost else None,
            "reference_designator": self.reference_designator,
            "is_leaf": self.is_leaf,
        }
