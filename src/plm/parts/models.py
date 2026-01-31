"""
Part Models

Core part/component definitions for PLM.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Optional


class PartType(str, Enum):
    """Types of parts in the system."""
    RAW_MATERIAL = "raw_material"       # Lumber, concrete, wire
    COMPONENT = "component"             # Window, door, fixture
    ASSEMBLY = "assembly"               # Wall assembly, roof truss
    PRODUCT = "product"                 # Complete house, addition
    DOCUMENT = "document"               # Drawing, spec, report


class PartStatus(str, Enum):
    """Lifecycle status of a part."""
    CONCEPT = "concept"                 # Early design
    DRAFT = "draft"                     # Work in progress
    IN_REVIEW = "in_review"             # Pending approval
    RELEASED = "released"               # Approved for use
    HOLD = "hold"                       # Temporarily suspended
    OBSOLETE = "obsolete"               # No longer valid


class UnitOfMeasure(str, Enum):
    """Standard units."""
    EACH = "EA"
    LINEAR_FEET = "LF"
    SQUARE_FEET = "SF"
    CUBIC_FEET = "CF"
    CUBIC_YARDS = "CY"
    POUNDS = "LB"
    GALLONS = "GAL"
    BOARD_FEET = "BF"
    SHEETS = "SHT"
    ROLLS = "RL"
    BAGS = "BAG"
    TONS = "TON"


@dataclass
class Part:
    """
    A design component in the PLM system.

    Parts can be materials, components, assemblies, or complete products.
    Each part has a revision history and can be included in BOMs.
    """
    id: str
    part_number: str              # "SIDING-FIBER-4X8-001"
    revision: str                 # "A", "B", "C" or "1.0", "1.1"
    name: str                     # "Fiber Cement Siding 4x8"
    description: Optional[str] = None
    part_type: PartType = PartType.COMPONENT
    status: PartStatus = PartStatus.DRAFT

    # Classification
    category: Optional[str] = None        # "03 - Concrete", "06 - Wood"
    csi_code: Optional[str] = None        # "07 46 46" (Fiber Cement Siding)
    uniformat_code: Optional[str] = None  # "B2010" (Exterior Walls)

    # Physical properties
    unit_of_measure: UnitOfMeasure = UnitOfMeasure.EACH
    unit_weight: Optional[Decimal] = None
    unit_volume: Optional[Decimal] = None

    # Cost
    unit_cost: Optional[Decimal] = None
    cost_currency: str = "USD"
    cost_effective_date: Optional[date] = None

    # Procurement
    manufacturer: Optional[str] = None
    manufacturer_pn: Optional[str] = None  # Manufacturer part number
    vendor: Optional[str] = None
    lead_time_days: Optional[int] = None
    min_order_qty: Optional[Decimal] = None
    order_multiple: Optional[Decimal] = None

    # Design files
    model_file: Optional[str] = None      # Path to 3DM/DWG
    drawing_file: Optional[str] = None    # Path to PDF
    spec_file: Optional[str] = None       # Path to specification

    # Lifecycle
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    released_by: Optional[str] = None
    released_at: Optional[datetime] = None
    obsoleted_by: Optional[str] = None
    obsoleted_at: Optional[datetime] = None

    # Metadata
    attributes: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

    @property
    def full_part_number(self) -> str:
        """Part number with revision."""
        return f"{self.part_number}-{self.revision}"

    def can_release(self) -> bool:
        """Check if part can be released."""
        return self.status in [PartStatus.DRAFT, PartStatus.IN_REVIEW]

    def can_revise(self) -> bool:
        """Check if part can be revised."""
        return self.status == PartStatus.RELEASED

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "part_number": self.part_number,
            "revision": self.revision,
            "full_part_number": self.full_part_number,
            "name": self.name,
            "description": self.description,
            "part_type": self.part_type.value,
            "status": self.status.value,
            "category": self.category,
            "csi_code": self.csi_code,
            "uniformat_code": self.uniformat_code,
            "unit_of_measure": self.unit_of_measure.value,
            "unit_cost": float(self.unit_cost) if self.unit_cost else None,
            "manufacturer": self.manufacturer,
            "lead_time_days": self.lead_time_days,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "released_at": self.released_at.isoformat() if self.released_at else None,
        }


@dataclass
class PartRevision:
    """
    A specific revision of a part.

    Maintains full history of changes.
    """
    id: str
    part_id: str
    revision: str
    previous_revision: Optional[str] = None
    change_order_id: Optional[str] = None  # ECO that created this revision

    # What changed
    change_summary: str = ""
    change_details: Optional[str] = None

    # Approval
    status: PartStatus = PartStatus.DRAFT
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    approval_notes: Optional[str] = None

    # Timestamps
    created_at: Optional[datetime] = None
    released_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


def increment_revision(current: str) -> str:
    """
    Increment a revision string.

    "A" -> "B", "Z" -> "AA", "1.0" -> "1.1"
    """
    if current.replace(".", "").isdigit():
        # Numeric revision
        parts = current.split(".")
        parts[-1] = str(int(parts[-1]) + 1)
        return ".".join(parts)
    else:
        # Alpha revision
        if current == "Z":
            return "AA"
        elif current.endswith("Z"):
            return current[:-1] + "AA"
        else:
            return current[:-1] + chr(ord(current[-1]) + 1)
