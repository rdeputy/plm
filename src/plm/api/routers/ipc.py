"""
IPC (Illustrated Parts Catalog) API Router

Endpoints for managing IPC data:
- Effectivity ranges (serial/date applicability)
- Supersession chains (part replacements)
- Figure hotspots (callout mapping)
- IPC generation
"""

from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter()


# =============================================================================
# Pydantic Schemas
# =============================================================================


class EffectivityRangeCreate(BaseModel):
    """Create an effectivity range."""
    effectivity_type: str = Field(..., description="serial, date, lot, model, config")
    serial_from: Optional[str] = None
    serial_to: Optional[str] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    model_codes: list[str] = Field(default_factory=list)
    config_codes: list[str] = Field(default_factory=list)
    part_id: Optional[str] = None
    bom_item_id: Optional[str] = None
    notes: Optional[str] = None


class EffectivityRangeResponse(BaseModel):
    """Effectivity range response."""
    id: str
    effectivity_type: str
    serial_from: Optional[str] = None
    serial_to: Optional[str] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    model_codes: list[str] = Field(default_factory=list)
    config_codes: list[str] = Field(default_factory=list)
    part_id: Optional[str] = None
    bom_item_id: Optional[str] = None
    display_text: str
    notes: Optional[str] = None


class SupersessionCreate(BaseModel):
    """Create a supersession record."""
    superseded_part_id: str
    superseded_part_number: str
    superseding_part_id: str
    superseding_part_number: str
    supersession_type: str = "replacement"  # replacement, alternate, upgrade
    is_interchangeable: bool = True
    quantity_ratio: float = 1.0
    effective_date: Optional[date] = None
    effective_serial: Optional[str] = None
    reason: str = ""
    change_order_id: Optional[str] = None
    notes: Optional[str] = None


class SupersessionResponse(BaseModel):
    """Supersession record response."""
    id: str
    superseded_part_id: str
    superseded_part_number: str
    superseding_part_id: str
    superseding_part_number: str
    supersession_type: str
    is_interchangeable: bool
    quantity_ratio: float
    effective_date: Optional[date] = None
    effective_serial: Optional[str] = None
    reason: str
    change_order_id: Optional[str] = None


class SupersessionChain(BaseModel):
    """Full supersession chain for a part."""
    part_id: str
    part_number: str
    predecessors: list["SupersessionResponse"] = Field(default_factory=list)
    successors: list["SupersessionResponse"] = Field(default_factory=list)
    current_part_number: str  # Latest in chain


class FigureHotspotCreate(BaseModel):
    """Create a figure hotspot."""
    bom_item_id: str
    index_number: int
    find_number: int
    x: float = Field(..., ge=0, le=1, description="X position (0-1)")
    y: float = Field(..., ge=0, le=1, description="Y position (0-1)")
    target_x: Optional[float] = Field(None, ge=0, le=1)
    target_y: Optional[float] = Field(None, ge=0, le=1)
    shape: str = "circle"
    size: float = 0.02
    part_number: Optional[str] = None
    part_name: Optional[str] = None
    quantity: Optional[float] = None
    page_number: int = 1
    notes: Optional[str] = None


class FigureHotspotResponse(BaseModel):
    """Figure hotspot response."""
    id: str
    figure_id: str
    bom_item_id: str
    index_number: int
    find_number: int
    x: float
    y: float
    target_x: Optional[float] = None
    target_y: Optional[float] = None
    shape: str
    size: float
    part_number: Optional[str] = None
    part_name: Optional[str] = None
    quantity: Optional[float] = None
    page_number: int


class IPCFigureCreate(BaseModel):
    """Create an IPC figure."""
    document_id: str
    bom_id: str
    figure_number: str
    title: str
    description: Optional[str] = None
    sheet_number: int = 1
    total_sheets: int = 1
    view_type: str = "exploded"
    scale: Optional[str] = None


class IPCFigureResponse(BaseModel):
    """IPC figure response."""
    id: str
    document_id: str
    bom_id: str
    figure_number: str
    title: str
    description: Optional[str] = None
    sheet_number: int
    total_sheets: int
    view_type: str
    scale: Optional[str] = None
    is_current: bool
    hotspot_count: int = 0
    hotspots: list[FigureHotspotResponse] = Field(default_factory=list)


class IPCEntryResponse(BaseModel):
    """IPC parts list entry."""
    index_number: int
    find_number: int
    part_number: str
    part_name: str
    description: Optional[str] = None
    quantity_per_assembly: float
    unit_of_measure: str
    effectivity_text: str = "All"
    superseded_by: Optional[str] = None
    supersedes: Optional[str] = None
    is_current: bool = True
    vendor_codes: list[str] = Field(default_factory=list)
    figure_refs: list[str] = Field(default_factory=list)


class IPCResponse(BaseModel):
    """Complete IPC for a BOM."""
    bom_id: str
    bom_number: str
    title: str
    figures: list[IPCFigureResponse]
    parts_list: list[IPCEntryResponse]
    generated_at: str


# =============================================================================
# In-Memory Storage (replace with DB in production)
# =============================================================================

_effectivity_ranges: dict[str, dict] = {}
_supersessions: dict[str, dict] = {}
_ipc_figures: dict[str, dict] = {}
_figure_hotspots: dict[str, dict] = {}


# =============================================================================
# Effectivity Endpoints
# =============================================================================


@router.post("/effectivity", response_model=EffectivityRangeResponse)
async def create_effectivity_range(data: EffectivityRangeCreate):
    """Create an effectivity range for a part or BOM item."""
    effectivity_id = str(uuid4())

    # Generate display text
    display_text = _generate_effectivity_display(data)

    record = {
        "id": effectivity_id,
        "effectivity_type": data.effectivity_type,
        "serial_from": data.serial_from,
        "serial_to": data.serial_to,
        "date_from": data.date_from,
        "date_to": data.date_to,
        "model_codes": data.model_codes,
        "config_codes": data.config_codes,
        "part_id": data.part_id,
        "bom_item_id": data.bom_item_id,
        "display_text": display_text,
        "notes": data.notes,
    }

    _effectivity_ranges[effectivity_id] = record
    return EffectivityRangeResponse(**record)


@router.get("/effectivity/{effectivity_id}", response_model=EffectivityRangeResponse)
async def get_effectivity_range(effectivity_id: str):
    """Get an effectivity range by ID."""
    if effectivity_id not in _effectivity_ranges:
        raise HTTPException(status_code=404, detail="Effectivity range not found")
    return EffectivityRangeResponse(**_effectivity_ranges[effectivity_id])


@router.get("/effectivity/by-part/{part_id}", response_model=list[EffectivityRangeResponse])
async def get_effectivity_by_part(part_id: str):
    """Get all effectivity ranges for a part."""
    ranges = [
        EffectivityRangeResponse(**r)
        for r in _effectivity_ranges.values()
        if r.get("part_id") == part_id
    ]
    return ranges


@router.get("/effectivity/by-bom-item/{bom_item_id}", response_model=list[EffectivityRangeResponse])
async def get_effectivity_by_bom_item(bom_item_id: str):
    """Get all effectivity ranges for a BOM item."""
    ranges = [
        EffectivityRangeResponse(**r)
        for r in _effectivity_ranges.values()
        if r.get("bom_item_id") == bom_item_id
    ]
    return ranges


@router.delete("/effectivity/{effectivity_id}")
async def delete_effectivity_range(effectivity_id: str):
    """Delete an effectivity range."""
    if effectivity_id not in _effectivity_ranges:
        raise HTTPException(status_code=404, detail="Effectivity range not found")
    del _effectivity_ranges[effectivity_id]
    return {"status": "deleted", "id": effectivity_id}


@router.get("/effectivity/check")
async def check_effectivity(
    part_id: str,
    serial: Optional[str] = None,
    check_date: Optional[date] = None,
):
    """Check if a part is effective for given serial/date."""
    ranges = [r for r in _effectivity_ranges.values() if r.get("part_id") == part_id]

    if not ranges:
        return {"effective": True, "reason": "No effectivity restrictions"}

    for r in ranges:
        if r["effectivity_type"] == "serial" and serial:
            if r.get("serial_from") and serial < r["serial_from"]:
                return {"effective": False, "reason": f"Before S/N {r['serial_from']}"}
            if r.get("serial_to") and serial > r["serial_to"]:
                return {"effective": False, "reason": f"After S/N {r['serial_to']}"}

        if r["effectivity_type"] == "date" and check_date:
            if r.get("date_from") and check_date < r["date_from"]:
                return {"effective": False, "reason": f"Before {r['date_from']}"}
            if r.get("date_to") and check_date > r["date_to"]:
                return {"effective": False, "reason": f"After {r['date_to']}"}

    return {"effective": True, "reason": "Within effectivity range"}


# =============================================================================
# Supersession Endpoints
# =============================================================================


@router.post("/supersession", response_model=SupersessionResponse)
async def create_supersession(data: SupersessionCreate):
    """Create a supersession record (part replacement)."""
    supersession_id = str(uuid4())

    record = {
        "id": supersession_id,
        "superseded_part_id": data.superseded_part_id,
        "superseded_part_number": data.superseded_part_number,
        "superseding_part_id": data.superseding_part_id,
        "superseding_part_number": data.superseding_part_number,
        "supersession_type": data.supersession_type,
        "is_interchangeable": data.is_interchangeable,
        "quantity_ratio": data.quantity_ratio,
        "effective_date": data.effective_date,
        "effective_serial": data.effective_serial,
        "reason": data.reason,
        "change_order_id": data.change_order_id,
        "notes": data.notes,
    }

    _supersessions[supersession_id] = record
    return SupersessionResponse(**record)


@router.get("/supersession/{supersession_id}", response_model=SupersessionResponse)
async def get_supersession(supersession_id: str):
    """Get a supersession record by ID."""
    if supersession_id not in _supersessions:
        raise HTTPException(status_code=404, detail="Supersession not found")
    return SupersessionResponse(**_supersessions[supersession_id])


@router.get("/supersession/chain/{part_id}", response_model=SupersessionChain)
async def get_supersession_chain(part_id: str):
    """
    Get the full supersession chain for a part.

    Returns all predecessors (parts this replaces) and
    successors (parts that replace this).
    """
    # Find all supersessions involving this part
    predecessors = []
    successors = []
    part_number = None

    for s in _supersessions.values():
        if s["superseding_part_id"] == part_id:
            # This part supersedes another
            predecessors.append(SupersessionResponse(**s))
            part_number = s["superseding_part_number"]
        if s["superseded_part_id"] == part_id:
            # This part is superseded by another
            successors.append(SupersessionResponse(**s))
            part_number = s["superseded_part_number"]

    # Find the current (latest) part in chain
    current_part_number = part_number or "Unknown"
    if successors:
        # Walk the chain to find the latest
        current_id = part_id
        while True:
            next_sup = next(
                (s for s in _supersessions.values() if s["superseded_part_id"] == current_id),
                None
            )
            if not next_sup:
                break
            current_id = next_sup["superseding_part_id"]
            current_part_number = next_sup["superseding_part_number"]

    return SupersessionChain(
        part_id=part_id,
        part_number=part_number or "Unknown",
        predecessors=predecessors,
        successors=successors,
        current_part_number=current_part_number,
    )


@router.get("/supersession/current/{part_id}")
async def get_current_part(part_id: str):
    """Get the current (latest) part number in a supersession chain."""
    chain = await get_supersession_chain(part_id)
    return {
        "original_part_id": part_id,
        "current_part_number": chain.current_part_number,
        "is_current": len(chain.successors) == 0,
    }


@router.delete("/supersession/{supersession_id}")
async def delete_supersession(supersession_id: str):
    """Delete a supersession record."""
    if supersession_id not in _supersessions:
        raise HTTPException(status_code=404, detail="Supersession not found")
    del _supersessions[supersession_id]
    return {"status": "deleted", "id": supersession_id}


# =============================================================================
# IPC Figure Endpoints
# =============================================================================


@router.post("/figures", response_model=IPCFigureResponse)
async def create_ipc_figure(data: IPCFigureCreate):
    """Create an IPC figure linking a document to a BOM."""
    figure_id = str(uuid4())

    record = {
        "id": figure_id,
        "document_id": data.document_id,
        "bom_id": data.bom_id,
        "figure_number": data.figure_number,
        "title": data.title,
        "description": data.description,
        "sheet_number": data.sheet_number,
        "total_sheets": data.total_sheets,
        "view_type": data.view_type,
        "scale": data.scale,
        "is_current": True,
        "hotspot_count": 0,
        "hotspots": [],
    }

    _ipc_figures[figure_id] = record
    return IPCFigureResponse(**record)


@router.get("/figures/{figure_id}", response_model=IPCFigureResponse)
async def get_ipc_figure(figure_id: str, include_hotspots: bool = True):
    """Get an IPC figure by ID."""
    if figure_id not in _ipc_figures:
        raise HTTPException(status_code=404, detail="Figure not found")

    figure = _ipc_figures[figure_id].copy()

    if include_hotspots:
        hotspots = [
            FigureHotspotResponse(**h)
            for h in _figure_hotspots.values()
            if h.get("figure_id") == figure_id
        ]
        figure["hotspots"] = hotspots
        figure["hotspot_count"] = len(hotspots)

    return IPCFigureResponse(**figure)


@router.get("/figures/by-bom/{bom_id}", response_model=list[IPCFigureResponse])
async def get_figures_by_bom(bom_id: str):
    """Get all IPC figures for a BOM."""
    figures = []
    for f in _ipc_figures.values():
        if f.get("bom_id") == bom_id:
            fig = f.copy()
            hotspots = [
                FigureHotspotResponse(**h)
                for h in _figure_hotspots.values()
                if h.get("figure_id") == f["id"]
            ]
            fig["hotspots"] = hotspots
            fig["hotspot_count"] = len(hotspots)
            figures.append(IPCFigureResponse(**fig))
    return figures


@router.delete("/figures/{figure_id}")
async def delete_ipc_figure(figure_id: str):
    """Delete an IPC figure and its hotspots."""
    if figure_id not in _ipc_figures:
        raise HTTPException(status_code=404, detail="Figure not found")

    # Delete associated hotspots
    hotspot_ids = [
        h["id"] for h in _figure_hotspots.values()
        if h.get("figure_id") == figure_id
    ]
    for hid in hotspot_ids:
        del _figure_hotspots[hid]

    del _ipc_figures[figure_id]
    return {"status": "deleted", "id": figure_id, "hotspots_deleted": len(hotspot_ids)}


# =============================================================================
# Hotspot Endpoints
# =============================================================================


@router.post("/figures/{figure_id}/hotspots", response_model=FigureHotspotResponse)
async def create_hotspot(figure_id: str, data: FigureHotspotCreate):
    """Add a hotspot to an IPC figure."""
    if figure_id not in _ipc_figures:
        raise HTTPException(status_code=404, detail="Figure not found")

    hotspot_id = str(uuid4())

    record = {
        "id": hotspot_id,
        "figure_id": figure_id,
        "bom_item_id": data.bom_item_id,
        "index_number": data.index_number,
        "find_number": data.find_number,
        "x": data.x,
        "y": data.y,
        "target_x": data.target_x,
        "target_y": data.target_y,
        "shape": data.shape,
        "size": data.size,
        "part_number": data.part_number,
        "part_name": data.part_name,
        "quantity": data.quantity,
        "page_number": data.page_number,
        "notes": data.notes,
    }

    _figure_hotspots[hotspot_id] = record
    return FigureHotspotResponse(**record)


@router.get("/figures/{figure_id}/hotspots", response_model=list[FigureHotspotResponse])
async def get_hotspots(figure_id: str, page: Optional[int] = None):
    """Get all hotspots for a figure."""
    hotspots = [
        FigureHotspotResponse(**h)
        for h in _figure_hotspots.values()
        if h.get("figure_id") == figure_id
        and (page is None or h.get("page_number") == page)
    ]
    return sorted(hotspots, key=lambda h: h.index_number)


@router.put("/hotspots/{hotspot_id}", response_model=FigureHotspotResponse)
async def update_hotspot(hotspot_id: str, data: FigureHotspotCreate):
    """Update a hotspot."""
    if hotspot_id not in _figure_hotspots:
        raise HTTPException(status_code=404, detail="Hotspot not found")

    record = _figure_hotspots[hotspot_id]
    record.update({
        "bom_item_id": data.bom_item_id,
        "index_number": data.index_number,
        "find_number": data.find_number,
        "x": data.x,
        "y": data.y,
        "target_x": data.target_x,
        "target_y": data.target_y,
        "shape": data.shape,
        "size": data.size,
        "part_number": data.part_number,
        "part_name": data.part_name,
        "quantity": data.quantity,
        "page_number": data.page_number,
        "notes": data.notes,
    })

    return FigureHotspotResponse(**record)


@router.delete("/hotspots/{hotspot_id}")
async def delete_hotspot(hotspot_id: str):
    """Delete a hotspot."""
    if hotspot_id not in _figure_hotspots:
        raise HTTPException(status_code=404, detail="Hotspot not found")
    del _figure_hotspots[hotspot_id]
    return {"status": "deleted", "id": hotspot_id}


# =============================================================================
# IPC Generation
# =============================================================================


@router.get("/generate/{bom_id}", response_model=IPCResponse)
async def generate_ipc(
    bom_id: str,
    serial: Optional[str] = Query(None, description="Filter by serial number"),
    effective_date: Optional[date] = Query(None, description="Filter by date"),
):
    """
    Generate a complete IPC for a BOM.

    Combines figures, hotspots, parts list, effectivity, and supersession
    data into a single IPC response.
    """
    from datetime import datetime

    # Get figures for this BOM
    figures = await get_figures_by_bom(bom_id)

    # Build parts list (in production, this would query BOM items)
    # For now, extract from hotspots
    parts_map: dict[str, IPCEntryResponse] = {}

    for figure in figures:
        for hotspot in figure.hotspots:
            if hotspot.part_number and hotspot.part_number not in parts_map:
                # Get effectivity for this part
                effectivity_ranges = [
                    r for r in _effectivity_ranges.values()
                    if r.get("bom_item_id") == hotspot.bom_item_id
                ]

                effectivity_text = "All"
                if effectivity_ranges:
                    texts = [r.get("display_text", "All") for r in effectivity_ranges]
                    effectivity_text = "; ".join(texts)

                # Check if superseded
                superseded_by = None
                supersedes = None
                is_current = True

                # Look for supersession records (would need part_id in production)

                parts_map[hotspot.part_number] = IPCEntryResponse(
                    index_number=hotspot.index_number,
                    find_number=hotspot.find_number,
                    part_number=hotspot.part_number,
                    part_name=hotspot.part_name or "",
                    quantity_per_assembly=hotspot.quantity or 1.0,
                    unit_of_measure="EA",
                    effectivity_text=effectivity_text,
                    superseded_by=superseded_by,
                    supersedes=supersedes,
                    is_current=is_current,
                    figure_refs=[figure.figure_number],
                )
            elif hotspot.part_number in parts_map:
                # Add figure reference
                entry = parts_map[hotspot.part_number]
                if figure.figure_number not in entry.figure_refs:
                    entry.figure_refs.append(figure.figure_number)

    # Sort parts list by find number
    parts_list = sorted(parts_map.values(), key=lambda p: p.find_number)

    return IPCResponse(
        bom_id=bom_id,
        bom_number=f"BOM-{bom_id[:8]}",  # Placeholder
        title=f"Illustrated Parts Catalog - BOM {bom_id[:8]}",
        figures=figures,
        parts_list=parts_list,
        generated_at=datetime.now().isoformat(),
    )


# =============================================================================
# Helper Functions
# =============================================================================


def _generate_effectivity_display(data: EffectivityRangeCreate) -> str:
    """Generate human-readable effectivity text."""
    if data.effectivity_type == "serial":
        if data.serial_from and data.serial_to:
            return f"S/N {data.serial_from} thru {data.serial_to}"
        elif data.serial_from:
            return f"S/N {data.serial_from} and subsequent"
        elif data.serial_to:
            return f"S/N up to {data.serial_to}"
    elif data.effectivity_type == "date":
        if data.date_from and data.date_to:
            return f"{data.date_from.strftime('%b %Y')} thru {data.date_to.strftime('%b %Y')}"
        elif data.date_from:
            return f"From {data.date_from.strftime('%b %Y')}"
        elif data.date_to:
            return f"Until {data.date_to.strftime('%b %Y')}"
    elif data.effectivity_type == "lot":
        if data.serial_from and data.serial_to:
            return f"Lot {data.serial_from} thru {data.serial_to}"
    elif data.effectivity_type == "model":
        if data.model_codes:
            return f"Models: {', '.join(data.model_codes)}"
    elif data.effectivity_type == "config":
        if data.config_codes:
            return f"Config: {', '.join(data.config_codes)}"
    return "All"
