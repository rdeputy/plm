"""
Suppliers API Router

AML/AVL management - manufacturers and vendors.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from plm.api.deps import get_db_session
from plm.db.models import (
    ManufacturerModel,
    SupplierVendorModel,
    ApprovedManufacturerModel,
    ApprovedVendorModel,
)

router = APIRouter()


# ----- Pydantic Schemas -----


class ManufacturerCreate(BaseModel):
    manufacturer_code: str
    name: str
    country: Optional[str] = None
    address: Optional[str] = None
    contact_email: Optional[str] = None
    cage_code: Optional[str] = None


class ManufacturerUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    country: Optional[str] = None
    address: Optional[str] = None
    contact_email: Optional[str] = None
    audit_score: Optional[int] = None


class ManufacturerResponse(BaseModel):
    id: str
    manufacturer_code: str
    name: str
    status: str
    country: Optional[str]
    cage_code: Optional[str]
    audit_score: Optional[int]

    class Config:
        from_attributes = True


class VendorCreate(BaseModel):
    vendor_code: str
    name: str
    country: Optional[str] = None
    tier: str = "approved"
    payment_terms: Optional[str] = None
    currency: str = "USD"


class VendorUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    tier: Optional[str] = None
    on_time_delivery_rate: Optional[float] = None
    quality_rating: Optional[float] = None
    lead_time_days: Optional[int] = None


class VendorResponse(BaseModel):
    id: str
    vendor_code: str
    name: str
    status: str
    tier: str
    country: Optional[str]
    on_time_delivery_rate: Optional[float]
    quality_rating: Optional[float]

    class Config:
        from_attributes = True


class ApprovedManufacturerCreate(BaseModel):
    part_id: str
    part_number: str
    manufacturer_id: str
    manufacturer_name: str
    manufacturer_part_number: Optional[str] = None
    preference_rank: int = 1
    is_primary: bool = False


class ApprovedManufacturerResponse(BaseModel):
    id: str
    part_id: str
    part_number: str
    manufacturer_id: str
    manufacturer_name: str
    manufacturer_part_number: Optional[str]
    status: str
    qualification_status: str
    preference_rank: int
    is_primary: bool

    class Config:
        from_attributes = True


class ApprovedVendorCreate(BaseModel):
    part_id: str
    part_number: str
    vendor_id: str
    vendor_name: str
    vendor_part_number: Optional[str] = None
    unit_price: float = 0
    currency: str = "USD"
    lead_time_days: int = 0
    preference_rank: int = 1
    is_primary: bool = False


class ApprovedVendorResponse(BaseModel):
    id: str
    part_id: str
    part_number: str
    vendor_id: str
    vendor_name: str
    vendor_part_number: Optional[str]
    status: str
    unit_price: float
    currency: str
    lead_time_days: int
    preference_rank: int

    class Config:
        from_attributes = True


# ----- Manufacturer Endpoints -----


@router.get("/manufacturers", response_model=list[ManufacturerResponse])
async def list_manufacturers(
    status: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db_session),
):
    """List manufacturers."""
    query = db.query(ManufacturerModel)

    if status:
        query = query.filter(ManufacturerModel.status == status)
    if country:
        query = query.filter(ManufacturerModel.country == country)
    if search:
        term = f"%{search}%"
        query = query.filter(
            (ManufacturerModel.manufacturer_code.ilike(term))
            | (ManufacturerModel.name.ilike(term))
        )

    return query.offset(offset).limit(limit).all()


@router.post("/manufacturers", response_model=ManufacturerResponse, status_code=201)
async def create_manufacturer(
    mfr: ManufacturerCreate,
    db: Session = Depends(get_db_session),
):
    """Create a manufacturer."""
    existing = db.query(ManufacturerModel).filter(
        ManufacturerModel.manufacturer_code == mfr.manufacturer_code
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Manufacturer code already exists")

    model = ManufacturerModel(
        id=str(uuid4()),
        manufacturer_code=mfr.manufacturer_code,
        name=mfr.name,
        status="pending",
        country=mfr.country,
        address=mfr.address,
        contact_email=mfr.contact_email,
        cage_code=mfr.cage_code,
        created_at=datetime.now(),
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    return model


@router.get("/manufacturers/{mfr_id}", response_model=ManufacturerResponse)
async def get_manufacturer(mfr_id: str, db: Session = Depends(get_db_session)):
    """Get a manufacturer by ID."""
    mfr = db.query(ManufacturerModel).filter(ManufacturerModel.id == mfr_id).first()
    if not mfr:
        raise HTTPException(status_code=404, detail="Manufacturer not found")
    return mfr


@router.patch("/manufacturers/{mfr_id}", response_model=ManufacturerResponse)
async def update_manufacturer(
    mfr_id: str,
    updates: ManufacturerUpdate,
    db: Session = Depends(get_db_session),
):
    """Update a manufacturer."""
    mfr = db.query(ManufacturerModel).filter(ManufacturerModel.id == mfr_id).first()
    if not mfr:
        raise HTTPException(status_code=404, detail="Manufacturer not found")

    for field, value in updates.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(mfr, field, value)

    db.commit()
    db.refresh(mfr)
    return mfr


# ----- Vendor Endpoints -----


@router.get("/vendors", response_model=list[VendorResponse])
async def list_vendors(
    status: Optional[str] = Query(None),
    tier: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db_session),
):
    """List vendors."""
    query = db.query(SupplierVendorModel)

    if status:
        query = query.filter(SupplierVendorModel.status == status)
    if tier:
        query = query.filter(SupplierVendorModel.tier == tier)
    if search:
        term = f"%{search}%"
        query = query.filter(
            (SupplierVendorModel.vendor_code.ilike(term))
            | (SupplierVendorModel.name.ilike(term))
        )

    return query.offset(offset).limit(limit).all()


@router.post("/vendors", response_model=VendorResponse, status_code=201)
async def create_vendor(
    vendor: VendorCreate,
    db: Session = Depends(get_db_session),
):
    """Create a vendor."""
    existing = db.query(SupplierVendorModel).filter(
        SupplierVendorModel.vendor_code == vendor.vendor_code
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Vendor code already exists")

    model = SupplierVendorModel(
        id=str(uuid4()),
        vendor_code=vendor.vendor_code,
        name=vendor.name,
        status="pending",
        tier=vendor.tier,
        country=vendor.country,
        payment_terms=vendor.payment_terms,
        currency=vendor.currency,
        created_at=datetime.now(),
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    return model


@router.get("/vendors/{vendor_id}", response_model=VendorResponse)
async def get_vendor(vendor_id: str, db: Session = Depends(get_db_session)):
    """Get a vendor by ID."""
    vendor = db.query(SupplierVendorModel).filter(
        SupplierVendorModel.id == vendor_id
    ).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return vendor


@router.patch("/vendors/{vendor_id}", response_model=VendorResponse)
async def update_vendor(
    vendor_id: str,
    updates: VendorUpdate,
    db: Session = Depends(get_db_session),
):
    """Update a vendor."""
    vendor = db.query(SupplierVendorModel).filter(
        SupplierVendorModel.id == vendor_id
    ).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    for field, value in updates.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(vendor, field, value)

    db.commit()
    db.refresh(vendor)
    return vendor


# ----- AML Endpoints -----


@router.get("/parts/{part_id}/aml", response_model=list[ApprovedManufacturerResponse])
async def get_part_aml(part_id: str, db: Session = Depends(get_db_session)):
    """Get approved manufacturer list for a part."""
    return db.query(ApprovedManufacturerModel).filter(
        ApprovedManufacturerModel.part_id == part_id
    ).order_by(ApprovedManufacturerModel.preference_rank).all()


@router.post("/parts/{part_id}/aml", response_model=ApprovedManufacturerResponse, status_code=201)
async def add_to_aml(
    part_id: str,
    entry: ApprovedManufacturerCreate,
    db: Session = Depends(get_db_session),
):
    """Add manufacturer to part's AML."""
    model = ApprovedManufacturerModel(
        id=str(uuid4()),
        part_id=part_id,
        part_number=entry.part_number,
        manufacturer_id=entry.manufacturer_id,
        manufacturer_name=entry.manufacturer_name,
        manufacturer_part_number=entry.manufacturer_part_number,
        status="pending",
        qualification_status="not_started",
        preference_rank=entry.preference_rank,
        is_primary=entry.is_primary,
        created_at=datetime.now(),
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    return model


@router.delete("/parts/{part_id}/aml/{aml_id}", status_code=204)
async def remove_from_aml(
    part_id: str,
    aml_id: str,
    db: Session = Depends(get_db_session),
):
    """Remove manufacturer from part's AML."""
    entry = db.query(ApprovedManufacturerModel).filter(
        ApprovedManufacturerModel.id == aml_id,
        ApprovedManufacturerModel.part_id == part_id,
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail="AML entry not found")

    db.delete(entry)
    db.commit()


# ----- AVL Endpoints -----


@router.get("/parts/{part_id}/avl", response_model=list[ApprovedVendorResponse])
async def get_part_avl(part_id: str, db: Session = Depends(get_db_session)):
    """Get approved vendor list for a part."""
    return db.query(ApprovedVendorModel).filter(
        ApprovedVendorModel.part_id == part_id
    ).order_by(ApprovedVendorModel.preference_rank).all()


@router.post("/parts/{part_id}/avl", response_model=ApprovedVendorResponse, status_code=201)
async def add_to_avl(
    part_id: str,
    entry: ApprovedVendorCreate,
    db: Session = Depends(get_db_session),
):
    """Add vendor to part's AVL."""
    model = ApprovedVendorModel(
        id=str(uuid4()),
        part_id=part_id,
        part_number=entry.part_number,
        vendor_id=entry.vendor_id,
        vendor_name=entry.vendor_name,
        vendor_part_number=entry.vendor_part_number,
        status="pending",
        unit_price=Decimal(str(entry.unit_price)),
        currency=entry.currency,
        lead_time_days=entry.lead_time_days,
        preference_rank=entry.preference_rank,
        is_primary=entry.is_primary,
        created_at=datetime.now(),
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    return model


@router.delete("/parts/{part_id}/avl/{avl_id}", status_code=204)
async def remove_from_avl(
    part_id: str,
    avl_id: str,
    db: Session = Depends(get_db_session),
):
    """Remove vendor from part's AVL."""
    entry = db.query(ApprovedVendorModel).filter(
        ApprovedVendorModel.id == avl_id,
        ApprovedVendorModel.part_id == part_id,
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail="AVL entry not found")

    db.delete(entry)
    db.commit()
