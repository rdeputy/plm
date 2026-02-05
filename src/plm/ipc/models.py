"""
IPC Domain Models

Data structures for Illustrated Parts Catalog generation.

IPC elements:
- Effectivity: Serial/date ranges when parts apply
- Supersession: Part replacement history
- Hotspots: Callout coordinates on figures
- Figures: Exploded views linked to BOM items
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Optional


class EffectivityType(str, Enum):
    """Types of effectivity ranges."""
    SERIAL = "serial"           # Serial number range (S/N 001-050)
    DATE = "date"               # Date range (2024-01-01 to 2024-12-31)
    LOT = "lot"                 # Lot/batch number range
    MODEL = "model"             # Model/variant code
    CONFIGURATION = "config"    # Configuration option


@dataclass
class EffectivityRange:
    """
    Defines when a part/BOM item is effective.

    Used for IPC to show which parts apply to which
    serial numbers, dates, or configurations.
    """
    id: str
    effectivity_type: EffectivityType

    # For serial/lot ranges
    serial_from: Optional[str] = None     # "001", "A001"
    serial_to: Optional[str] = None       # "050", "A999"

    # For date ranges
    date_from: Optional[date] = None
    date_to: Optional[date] = None

    # For model/config effectivity
    model_codes: list[str] = field(default_factory=list)
    config_codes: list[str] = field(default_factory=list)

    # What this effectivity applies to
    part_id: Optional[str] = None
    bom_item_id: Optional[str] = None

    # Display text for IPC
    display_text: str = ""  # "S/N 001-050", "From Jan 2024"

    # Notes
    notes: Optional[str] = None

    created_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if not self.display_text:
            self.display_text = self._generate_display_text()

    def _generate_display_text(self) -> str:
        """Generate human-readable effectivity text."""
        if self.effectivity_type == EffectivityType.SERIAL:
            if self.serial_from and self.serial_to:
                return f"S/N {self.serial_from} thru {self.serial_to}"
            elif self.serial_from:
                return f"S/N {self.serial_from} and subsequent"
            elif self.serial_to:
                return f"S/N up to {self.serial_to}"
        elif self.effectivity_type == EffectivityType.DATE:
            if self.date_from and self.date_to:
                return f"{self.date_from.strftime('%b %Y')} thru {self.date_to.strftime('%b %Y')}"
            elif self.date_from:
                return f"From {self.date_from.strftime('%b %Y')}"
            elif self.date_to:
                return f"Until {self.date_to.strftime('%b %Y')}"
        elif self.effectivity_type == EffectivityType.LOT:
            if self.serial_from and self.serial_to:
                return f"Lot {self.serial_from} thru {self.serial_to}"
        elif self.effectivity_type == EffectivityType.MODEL:
            if self.model_codes:
                return f"Models: {', '.join(self.model_codes)}"
        elif self.effectivity_type == EffectivityType.CONFIGURATION:
            if self.config_codes:
                return f"Config: {', '.join(self.config_codes)}"
        return "All"

    def applies_to_serial(self, serial: str) -> bool:
        """Check if this effectivity applies to a serial number."""
        if self.effectivity_type != EffectivityType.SERIAL:
            return True
        if not self.serial_from and not self.serial_to:
            return True
        # Simple string comparison (works for numeric or alpha serials)
        if self.serial_from and serial < self.serial_from:
            return False
        if self.serial_to and serial > self.serial_to:
            return False
        return True

    def applies_to_date(self, check_date: date) -> bool:
        """Check if this effectivity applies to a date."""
        if self.effectivity_type != EffectivityType.DATE:
            return True
        if not self.date_from and not self.date_to:
            return True
        if self.date_from and check_date < self.date_from:
            return False
        if self.date_to and check_date > self.date_to:
            return False
        return True

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "effectivity_type": self.effectivity_type.value,
            "serial_from": self.serial_from,
            "serial_to": self.serial_to,
            "date_from": self.date_from.isoformat() if self.date_from else None,
            "date_to": self.date_to.isoformat() if self.date_to else None,
            "model_codes": self.model_codes,
            "config_codes": self.config_codes,
            "display_text": self.display_text,
            "part_id": self.part_id,
            "bom_item_id": self.bom_item_id,
        }


@dataclass
class Supersession:
    """
    Part supersession/replacement record.

    Tracks the history of part replacements for IPC.
    Forms a chain: PN-001 -> PN-002 -> PN-003
    """
    id: str
    superseded_part_id: str           # Old part being replaced
    superseded_part_number: str
    superseding_part_id: str          # New replacement part
    superseding_part_number: str

    # Supersession details
    supersession_type: str = "replacement"  # replacement, alternate, upgrade
    is_interchangeable: bool = True         # Can swap without modification?
    quantity_ratio: Decimal = Decimal("1")  # How many new parts per old? (usually 1:1)

    # Effectivity - when does supersession apply?
    effective_date: Optional[date] = None
    effective_serial: Optional[str] = None  # "From S/N 051"

    # Reason and notes
    reason: str = ""                        # "Improved durability"
    change_order_id: Optional[str] = None   # ECO that authorized this
    notes: Optional[str] = None

    # Timestamps
    created_at: Optional[datetime] = None
    created_by: Optional[str] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "superseded_part_id": self.superseded_part_id,
            "superseded_part_number": self.superseded_part_number,
            "superseding_part_id": self.superseding_part_id,
            "superseding_part_number": self.superseding_part_number,
            "supersession_type": self.supersession_type,
            "is_interchangeable": self.is_interchangeable,
            "quantity_ratio": float(self.quantity_ratio),
            "effective_date": self.effective_date.isoformat() if self.effective_date else None,
            "effective_serial": self.effective_serial,
            "reason": self.reason,
            "change_order_id": self.change_order_id,
        }


@dataclass
class FigureHotspot:
    """
    A clickable hotspot on an IPC figure.

    Links a callout number (index) on a drawing to a
    specific BOM item, with coordinates for the callout location.
    """
    id: str
    figure_id: str                    # Document containing the figure
    bom_item_id: str                  # BOM line item this hotspot references

    # Callout identification
    index_number: int                 # The callout number (1, 2, 3...)
    find_number: int                  # BOM find number (10, 20, 30...)

    # Position on figure (normalized 0-1 coordinates)
    # Origin is top-left, (1,1) is bottom-right
    x: float                          # Horizontal position (0.0 to 1.0)
    y: float                          # Vertical position (0.0 to 1.0)

    # Optional: for leader line endpoint (where arrow points)
    target_x: Optional[float] = None
    target_y: Optional[float] = None

    # Display options
    shape: str = "circle"             # circle, square, arrow
    size: float = 0.02                # Size as fraction of figure

    # Part info (denormalized for quick lookup)
    part_number: Optional[str] = None
    part_name: Optional[str] = None
    quantity: Optional[Decimal] = None

    # Page reference for multi-page figures
    page_number: int = 1

    # Notes
    notes: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "figure_id": self.figure_id,
            "bom_item_id": self.bom_item_id,
            "index_number": self.index_number,
            "find_number": self.find_number,
            "x": self.x,
            "y": self.y,
            "target_x": self.target_x,
            "target_y": self.target_y,
            "shape": self.shape,
            "size": self.size,
            "part_number": self.part_number,
            "part_name": self.part_name,
            "quantity": float(self.quantity) if self.quantity else None,
            "page_number": self.page_number,
        }


@dataclass
class IPCFigure:
    """
    An IPC figure (exploded view or assembly drawing).

    Links a document to a BOM with hotspot mappings.
    """
    id: str
    document_id: str                  # The drawing/figure document
    bom_id: str                       # BOM this figure illustrates
    figure_number: str                # "Figure 1", "Fig 2-1"
    title: str                        # "Main Assembly - Exploded View"

    # Figure metadata
    description: Optional[str] = None
    sheet_number: int = 1             # For multi-sheet drawings
    total_sheets: int = 1

    # Hotspots
    hotspots: list[FigureHotspot] = field(default_factory=list)

    # View information
    view_type: str = "exploded"       # exploded, section, detail, isometric
    scale: Optional[str] = None       # "1:10", "NTS"

    # Status
    is_current: bool = True           # False for superseded figures
    superseded_by: Optional[str] = None

    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

    def add_hotspot(self, hotspot: FigureHotspot) -> None:
        """Add a hotspot to this figure."""
        hotspot.figure_id = self.id
        self.hotspots.append(hotspot)

    def get_hotspot_by_index(self, index_number: int) -> Optional[FigureHotspot]:
        """Get hotspot by its index number."""
        for hs in self.hotspots:
            if hs.index_number == index_number:
                return hs
        return None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "document_id": self.document_id,
            "bom_id": self.bom_id,
            "figure_number": self.figure_number,
            "title": self.title,
            "description": self.description,
            "sheet_number": self.sheet_number,
            "total_sheets": self.total_sheets,
            "view_type": self.view_type,
            "scale": self.scale,
            "is_current": self.is_current,
            "hotspot_count": len(self.hotspots),
            "hotspots": [hs.to_dict() for hs in self.hotspots],
        }


@dataclass
class IPCEntry:
    """
    A single entry in an IPC parts list.

    Combines BOM item data with effectivity and supersession
    information for catalog output.
    """
    index_number: int                 # Callout number in figure
    find_number: int                  # BOM sequence (10, 20, 30)
    part_number: str
    part_name: str
    description: Optional[str] = None

    # Quantities
    quantity_per_assembly: Decimal = Decimal("1")
    unit_of_measure: str = "EA"

    # Effectivity
    effectivity: list[EffectivityRange] = field(default_factory=list)
    effectivity_text: str = "All"     # Human-readable effectivity

    # Supersession
    superseded_by: Optional[str] = None     # New part number if replaced
    supersedes: Optional[str] = None        # Old part number this replaces
    is_current: bool = True

    # Vendor/source
    vendor_codes: list[str] = field(default_factory=list)

    # Reference
    figure_refs: list[str] = field(default_factory=list)  # ["Fig 1", "Fig 2-1"]

    # Notes
    notes: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "index_number": self.index_number,
            "find_number": self.find_number,
            "part_number": self.part_number,
            "part_name": self.part_name,
            "description": self.description,
            "quantity_per_assembly": float(self.quantity_per_assembly),
            "unit_of_measure": self.unit_of_measure,
            "effectivity_text": self.effectivity_text,
            "superseded_by": self.superseded_by,
            "supersedes": self.supersedes,
            "is_current": self.is_current,
            "vendor_codes": self.vendor_codes,
            "figure_refs": self.figure_refs,
            "notes": self.notes,
        }
