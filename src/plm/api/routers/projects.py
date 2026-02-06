"""
Projects API Router

Project management with milestones and deliverables.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from plm.api.deps import get_db_session
from plm.db.models import ProjectModel, MilestoneModel, DeliverableModel

router = APIRouter()


# ----- Pydantic Schemas -----


class ProjectCreate(BaseModel):
    project_number: str
    name: str
    project_type: Optional[str] = None
    description: Optional[str] = None
    customer_name: Optional[str] = None
    project_manager_name: Optional[str] = None
    start_date: Optional[str] = None
    target_end_date: Optional[str] = None
    budget: float = 0
    currency: str = "USD"


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    phase: Optional[str] = None
    description: Optional[str] = None
    customer_name: Optional[str] = None
    project_manager_name: Optional[str] = None
    target_end_date: Optional[str] = None
    budget: Optional[float] = None
    actual_cost: Optional[float] = None


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_number: str
    name: str
    status: str
    phase: str
    project_type: Optional[str]
    customer_name: Optional[str]
    project_manager_name: Optional[str]
    start_date: Optional[str]
    target_end_date: Optional[str]
    budget: float
    actual_cost: float
    currency: str


class MilestoneCreate(BaseModel):
    milestone_number: str
    name: str
    description: Optional[str] = None
    phase: Optional[str] = None
    planned_date: Optional[str] = None
    sequence: int = 0
    review_required: bool = False
    review_type: Optional[str] = None


class MilestoneUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    description: Optional[str] = None
    planned_date: Optional[str] = None
    forecast_date: Optional[str] = None
    actual_date: Optional[str] = None


class MilestoneResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    milestone_number: str
    name: str
    status: str
    phase: Optional[str]
    planned_date: Optional[str]
    actual_date: Optional[str]
    review_required: bool
    sequence: int


class DeliverableCreate(BaseModel):
    deliverable_number: str
    name: str
    deliverable_type: str = "document"
    description: Optional[str] = None
    milestone_id: Optional[str] = None
    due_date: Optional[str] = None
    assigned_to: Optional[str] = None
    assigned_name: Optional[str] = None


class DeliverableUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    percent_complete: Optional[int] = None
    due_date: Optional[str] = None
    assigned_name: Optional[str] = None


class DeliverableResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    milestone_id: Optional[str]
    deliverable_number: str
    name: str
    deliverable_type: str
    status: str
    percent_complete: int
    due_date: Optional[str]
    assigned_name: Optional[str]


# ----- Project Endpoints -----


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    status: Optional[str] = Query(None),
    phase: Optional[str] = Query(None),
    customer_name: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db_session),
):
    """List projects."""
    query = db.query(ProjectModel)

    if status:
        query = query.filter(ProjectModel.status == status)
    if phase:
        query = query.filter(ProjectModel.phase == phase)
    if customer_name:
        query = query.filter(ProjectModel.customer_name.ilike(f"%{customer_name}%"))
    if search:
        term = f"%{search}%"
        query = query.filter(
            (ProjectModel.project_number.ilike(term))
            | (ProjectModel.name.ilike(term))
        )

    return query.offset(offset).limit(limit).all()


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(
    project: ProjectCreate,
    db: Session = Depends(get_db_session),
):
    """Create a project."""
    existing = db.query(ProjectModel).filter(
        ProjectModel.project_number == project.project_number
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Project number already exists")

    model = ProjectModel(
        id=str(uuid4()),
        project_number=project.project_number,
        name=project.name,
        status="proposed",
        phase="concept",
        project_type=project.project_type,
        description=project.description,
        customer_name=project.customer_name,
        project_manager_name=project.project_manager_name,
        start_date=date.fromisoformat(project.start_date) if project.start_date else None,
        target_end_date=date.fromisoformat(project.target_end_date) if project.target_end_date else None,
        budget=Decimal(str(project.budget)),
        actual_cost=Decimal("0"),
        currency=project.currency,
        created_at=datetime.now(),
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    return model


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, db: Session = Depends(get_db_session)):
    """Get a project by ID."""
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    updates: ProjectUpdate,
    db: Session = Depends(get_db_session),
):
    """Update a project."""
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    for field, value in updates.model_dump(exclude_unset=True).items():
        if value is not None:
            if field in ["budget", "actual_cost"]:
                setattr(project, field, Decimal(str(value)))
            elif field == "target_end_date":
                setattr(project, field, date.fromisoformat(value))
            else:
                setattr(project, field, value)

    db.commit()
    db.refresh(project)
    return project


@router.post("/{project_id}/approve", response_model=ProjectResponse)
async def approve_project(
    project_id: str,
    approved_by: str = Query(...),
    db: Session = Depends(get_db_session),
):
    """Approve a project to start."""
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project.status = "active"
    project.approved_by = approved_by
    project.approved_date = datetime.now()
    if not project.start_date:
        project.start_date = date.today()

    db.commit()
    db.refresh(project)
    return project


# ----- Milestone Endpoints -----


@router.get("/{project_id}/milestones", response_model=list[MilestoneResponse])
async def list_milestones(project_id: str, db: Session = Depends(get_db_session)):
    """List milestones for a project."""
    return db.query(MilestoneModel).filter(
        MilestoneModel.project_id == project_id
    ).order_by(MilestoneModel.sequence).all()


@router.post("/{project_id}/milestones", response_model=MilestoneResponse, status_code=201)
async def create_milestone(
    project_id: str,
    milestone: MilestoneCreate,
    db: Session = Depends(get_db_session),
):
    """Create a milestone."""
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    model = MilestoneModel(
        id=str(uuid4()),
        project_id=project_id,
        milestone_number=milestone.milestone_number,
        name=milestone.name,
        status="not_started",
        description=milestone.description,
        phase=milestone.phase,
        planned_date=date.fromisoformat(milestone.planned_date) if milestone.planned_date else None,
        sequence=milestone.sequence,
        review_required=milestone.review_required,
        review_type=milestone.review_type,
        created_at=datetime.now(),
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    return model


@router.patch("/{project_id}/milestones/{milestone_id}", response_model=MilestoneResponse)
async def update_milestone(
    project_id: str,
    milestone_id: str,
    updates: MilestoneUpdate,
    db: Session = Depends(get_db_session),
):
    """Update a milestone."""
    milestone = db.query(MilestoneModel).filter(
        MilestoneModel.id == milestone_id,
        MilestoneModel.project_id == project_id,
    ).first()
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")

    for field, value in updates.model_dump(exclude_unset=True).items():
        if value is not None:
            if field in ["planned_date", "forecast_date", "actual_date"]:
                setattr(milestone, field, date.fromisoformat(value))
            else:
                setattr(milestone, field, value)

    db.commit()
    db.refresh(milestone)
    return milestone


@router.post("/{project_id}/milestones/{milestone_id}/complete", response_model=MilestoneResponse)
async def complete_milestone(
    project_id: str,
    milestone_id: str,
    completed_by: str = Query(...),
    db: Session = Depends(get_db_session),
):
    """Mark a milestone as completed."""
    milestone = db.query(MilestoneModel).filter(
        MilestoneModel.id == milestone_id,
        MilestoneModel.project_id == project_id,
    ).first()
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")

    milestone.status = "completed"
    milestone.actual_date = date.today()
    milestone.completed_by = completed_by

    db.commit()
    db.refresh(milestone)
    return milestone


# ----- Deliverable Endpoints -----


@router.get("/{project_id}/deliverables", response_model=list[DeliverableResponse])
async def list_deliverables(
    project_id: str,
    milestone_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db_session),
):
    """List deliverables for a project."""
    query = db.query(DeliverableModel).filter(DeliverableModel.project_id == project_id)

    if milestone_id:
        query = query.filter(DeliverableModel.milestone_id == milestone_id)
    if status:
        query = query.filter(DeliverableModel.status == status)

    return query.all()


@router.post("/{project_id}/deliverables", response_model=DeliverableResponse, status_code=201)
async def create_deliverable(
    project_id: str,
    deliverable: DeliverableCreate,
    db: Session = Depends(get_db_session),
):
    """Create a deliverable."""
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    model = DeliverableModel(
        id=str(uuid4()),
        project_id=project_id,
        milestone_id=deliverable.milestone_id,
        deliverable_number=deliverable.deliverable_number,
        name=deliverable.name,
        deliverable_type=deliverable.deliverable_type,
        status="not_started",
        description=deliverable.description,
        percent_complete=0,
        due_date=date.fromisoformat(deliverable.due_date) if deliverable.due_date else None,
        assigned_to=deliverable.assigned_to,
        assigned_name=deliverable.assigned_name,
        created_at=datetime.now(),
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    return model


@router.patch("/{project_id}/deliverables/{deliverable_id}", response_model=DeliverableResponse)
async def update_deliverable(
    project_id: str,
    deliverable_id: str,
    updates: DeliverableUpdate,
    db: Session = Depends(get_db_session),
):
    """Update a deliverable."""
    deliverable = db.query(DeliverableModel).filter(
        DeliverableModel.id == deliverable_id,
        DeliverableModel.project_id == project_id,
    ).first()
    if not deliverable:
        raise HTTPException(status_code=404, detail="Deliverable not found")

    for field, value in updates.model_dump(exclude_unset=True).items():
        if value is not None:
            if field == "due_date":
                setattr(deliverable, field, date.fromisoformat(value))
            else:
                setattr(deliverable, field, value)

    db.commit()
    db.refresh(deliverable)
    return deliverable
