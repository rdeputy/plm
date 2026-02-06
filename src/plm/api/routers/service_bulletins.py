"""
Service Bulletins API Router

Field service notices, maintenance schedules, and unit configurations.
"""

from datetime import datetime, date
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from plm.api.deps import get_db_session
from plm.db.models import (
    ServiceBulletinModel,
    BulletinComplianceModel,
    MaintenanceScheduleModel,
    UnitConfigurationModel,
)

router = APIRouter()


# ----- Pydantic Schemas -----


class ServiceBulletinCreate(BaseModel):
    bulletin_number: str
    bulletin_type: str
    title: str
    summary: Optional[str] = None
    description: Optional[str] = None
    action_required: Optional[str] = None
    safety_issue: bool = False
    affected_part_numbers: list[str] = []
    compliance_deadline: Optional[str] = None


class ServiceBulletinUpdate(BaseModel):
    status: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    action_required: Optional[str] = None
    compliance_deadline: Optional[str] = None


class ServiceBulletinResponse(BaseModel):
    id: str
    bulletin_number: str
    bulletin_type: str
    status: str
    title: str
    summary: Optional[str]
    safety_issue: bool
    compliance_deadline: Optional[str]
    effective_date: Optional[str]

    class Config:
        from_attributes = True


class BulletinComplianceCreate(BaseModel):
    bulletin_id: str
    bulletin_number: str
    serial_number: str
    part_id: Optional[str] = None
    part_number: Optional[str] = None


class BulletinComplianceUpdate(BaseModel):
    status: Optional[str] = None
    completed_by: Optional[str] = None
    work_order_number: Optional[str] = None
    labor_hours: Optional[float] = None
    notes: Optional[str] = None
    waived: bool = False
    waiver_reason: Optional[str] = None


class BulletinComplianceResponse(BaseModel):
    id: str
    bulletin_id: str
    bulletin_number: str
    serial_number: str
    status: str
    completed_date: Optional[str]
    waived: bool

    class Config:
        from_attributes = True


class MaintenanceScheduleCreate(BaseModel):
    schedule_code: str
    part_id: Optional[str] = None
    part_number: Optional[str] = None
    system: Optional[str] = None
    interval_type: str = "calendar"
    interval_value: int = 0
    interval_unit: str = ""
    task_description: Optional[str] = None


class MaintenanceScheduleResponse(BaseModel):
    id: str
    schedule_code: str
    part_number: Optional[str]
    system: Optional[str]
    interval_type: str
    interval_value: int
    interval_unit: str
    task_description: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True


class UnitConfigurationCreate(BaseModel):
    serial_number: str
    part_id: str
    part_number: str
    current_revision: str = ""
    build_date: Optional[str] = None
    owner_name: Optional[str] = None
    location: Optional[str] = None


class UnitConfigurationUpdate(BaseModel):
    current_revision: Optional[str] = None
    total_hours: Optional[float] = None
    total_cycles: Optional[int] = None
    owner_name: Optional[str] = None
    location: Optional[str] = None


class UnitConfigurationResponse(BaseModel):
    id: str
    serial_number: str
    part_id: str
    part_number: str
    current_revision: str
    total_hours: float
    total_cycles: int
    owner_name: Optional[str]
    location: Optional[str]

    class Config:
        from_attributes = True


# ----- Service Bulletin Endpoints -----


@router.get("", response_model=list[ServiceBulletinResponse])
async def list_bulletins(
    bulletin_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    safety_issue: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db_session),
):
    """List service bulletins."""
    query = db.query(ServiceBulletinModel)

    if bulletin_type:
        query = query.filter(ServiceBulletinModel.bulletin_type == bulletin_type)
    if status:
        query = query.filter(ServiceBulletinModel.status == status)
    if safety_issue is not None:
        query = query.filter(ServiceBulletinModel.safety_issue == safety_issue)
    if search:
        term = f"%{search}%"
        query = query.filter(
            (ServiceBulletinModel.bulletin_number.ilike(term))
            | (ServiceBulletinModel.title.ilike(term))
        )

    return query.offset(offset).limit(limit).all()


@router.post("", response_model=ServiceBulletinResponse, status_code=201)
async def create_bulletin(
    sb: ServiceBulletinCreate,
    db: Session = Depends(get_db_session),
):
    """Create a service bulletin."""
    existing = db.query(ServiceBulletinModel).filter(
        ServiceBulletinModel.bulletin_number == sb.bulletin_number
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Bulletin number already exists")

    model = ServiceBulletinModel(
        id=str(uuid4()),
        bulletin_number=sb.bulletin_number,
        bulletin_type=sb.bulletin_type,
        status="draft",
        title=sb.title,
        summary=sb.summary,
        description=sb.description,
        action_required=sb.action_required,
        safety_issue=sb.safety_issue,
        compliance_deadline=date.fromisoformat(sb.compliance_deadline) if sb.compliance_deadline else None,
        created_at=datetime.now(),
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    return model


@router.get("/{sb_id}", response_model=ServiceBulletinResponse)
async def get_bulletin(sb_id: str, db: Session = Depends(get_db_session)):
    """Get a service bulletin by ID."""
    sb = db.query(ServiceBulletinModel).filter(ServiceBulletinModel.id == sb_id).first()
    if not sb:
        raise HTTPException(status_code=404, detail="Bulletin not found")
    return sb


@router.patch("/{sb_id}", response_model=ServiceBulletinResponse)
async def update_bulletin(
    sb_id: str,
    updates: ServiceBulletinUpdate,
    db: Session = Depends(get_db_session),
):
    """Update a service bulletin."""
    sb = db.query(ServiceBulletinModel).filter(ServiceBulletinModel.id == sb_id).first()
    if not sb:
        raise HTTPException(status_code=404, detail="Bulletin not found")

    for field, value in updates.model_dump(exclude_unset=True).items():
        if value is not None:
            if field == "compliance_deadline":
                setattr(sb, field, date.fromisoformat(value))
            else:
                setattr(sb, field, value)

    db.commit()
    db.refresh(sb)
    return sb


@router.post("/{sb_id}/release", response_model=ServiceBulletinResponse)
async def release_bulletin(
    sb_id: str,
    approved_by: str = Query(...),
    db: Session = Depends(get_db_session),
):
    """Release a service bulletin."""
    sb = db.query(ServiceBulletinModel).filter(ServiceBulletinModel.id == sb_id).first()
    if not sb:
        raise HTTPException(status_code=404, detail="Bulletin not found")

    sb.status = "active"
    sb.approved_by = approved_by
    sb.approved_date = datetime.now()
    sb.effective_date = date.today()

    db.commit()
    db.refresh(sb)
    return sb


# ----- Bulletin Compliance Endpoints -----


@router.get("/{sb_id}/compliance", response_model=list[BulletinComplianceResponse])
async def list_bulletin_compliance(sb_id: str, db: Session = Depends(get_db_session)):
    """List compliance records for a bulletin."""
    return db.query(BulletinComplianceModel).filter(
        BulletinComplianceModel.bulletin_id == sb_id
    ).all()


@router.post("/{sb_id}/compliance", response_model=BulletinComplianceResponse, status_code=201)
async def create_compliance_record(
    sb_id: str,
    comp: BulletinComplianceCreate,
    db: Session = Depends(get_db_session),
):
    """Create a compliance record for a unit."""
    model = BulletinComplianceModel(
        id=str(uuid4()),
        bulletin_id=sb_id,
        bulletin_number=comp.bulletin_number,
        serial_number=comp.serial_number,
        part_id=comp.part_id,
        part_number=comp.part_number,
        status="pending",
        created_at=datetime.now(),
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    return model


@router.patch("/{sb_id}/compliance/{comp_id}", response_model=BulletinComplianceResponse)
async def update_compliance_record(
    sb_id: str,
    comp_id: str,
    updates: BulletinComplianceUpdate,
    db: Session = Depends(get_db_session),
):
    """Update a compliance record."""
    comp = db.query(BulletinComplianceModel).filter(
        BulletinComplianceModel.id == comp_id,
        BulletinComplianceModel.bulletin_id == sb_id,
    ).first()
    if not comp:
        raise HTTPException(status_code=404, detail="Compliance record not found")

    for field, value in updates.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(comp, field, value)

    if updates.status == "completed" and updates.completed_by:
        comp.completed_date = date.today()

    db.commit()
    db.refresh(comp)
    return comp


# ----- Maintenance Schedule Endpoints -----


@router.get("/maintenance/schedules", response_model=list[MaintenanceScheduleResponse])
async def list_maintenance_schedules(
    part_number: Optional[str] = Query(None),
    system: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db_session),
):
    """List maintenance schedules."""
    query = db.query(MaintenanceScheduleModel)

    if part_number:
        query = query.filter(MaintenanceScheduleModel.part_number == part_number)
    if system:
        query = query.filter(MaintenanceScheduleModel.system == system)
    if is_active is not None:
        query = query.filter(MaintenanceScheduleModel.is_active == is_active)

    return query.limit(limit).all()


@router.post("/maintenance/schedules", response_model=MaintenanceScheduleResponse, status_code=201)
async def create_maintenance_schedule(
    schedule: MaintenanceScheduleCreate,
    db: Session = Depends(get_db_session),
):
    """Create a maintenance schedule."""
    model = MaintenanceScheduleModel(
        id=str(uuid4()),
        schedule_code=schedule.schedule_code,
        part_id=schedule.part_id,
        part_number=schedule.part_number,
        system=schedule.system,
        interval_type=schedule.interval_type,
        interval_value=schedule.interval_value,
        interval_unit=schedule.interval_unit,
        task_description=schedule.task_description,
        is_active=True,
        created_at=datetime.now(),
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    return model


# ----- Unit Configuration Endpoints -----


@router.get("/units", response_model=list[UnitConfigurationResponse])
async def list_unit_configurations(
    part_number: Optional[str] = Query(None),
    owner_name: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db_session),
):
    """List unit configurations."""
    query = db.query(UnitConfigurationModel)

    if part_number:
        query = query.filter(UnitConfigurationModel.part_number == part_number)
    if owner_name:
        query = query.filter(UnitConfigurationModel.owner_name.ilike(f"%{owner_name}%"))
    if search:
        term = f"%{search}%"
        query = query.filter(UnitConfigurationModel.serial_number.ilike(term))

    return query.offset(offset).limit(limit).all()


@router.post("/units", response_model=UnitConfigurationResponse, status_code=201)
async def create_unit_configuration(
    unit: UnitConfigurationCreate,
    db: Session = Depends(get_db_session),
):
    """Create a unit configuration."""
    existing = db.query(UnitConfigurationModel).filter(
        UnitConfigurationModel.serial_number == unit.serial_number
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Serial number already exists")

    model = UnitConfigurationModel(
        id=str(uuid4()),
        serial_number=unit.serial_number,
        part_id=unit.part_id,
        part_number=unit.part_number,
        current_revision=unit.current_revision,
        build_date=date.fromisoformat(unit.build_date) if unit.build_date else None,
        owner_name=unit.owner_name,
        location=unit.location,
        total_hours=0.0,
        total_cycles=0,
        created_at=datetime.now(),
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    return model


@router.get("/units/{serial_number}", response_model=UnitConfigurationResponse)
async def get_unit_configuration(serial_number: str, db: Session = Depends(get_db_session)):
    """Get a unit configuration by serial number."""
    unit = db.query(UnitConfigurationModel).filter(
        UnitConfigurationModel.serial_number == serial_number
    ).first()
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")
    return unit


@router.patch("/units/{serial_number}", response_model=UnitConfigurationResponse)
async def update_unit_configuration(
    serial_number: str,
    updates: UnitConfigurationUpdate,
    db: Session = Depends(get_db_session),
):
    """Update a unit configuration."""
    unit = db.query(UnitConfigurationModel).filter(
        UnitConfigurationModel.serial_number == serial_number
    ).first()
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")

    for field, value in updates.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(unit, field, value)

    unit.last_updated = datetime.now()
    db.commit()
    db.refresh(unit)
    return unit
