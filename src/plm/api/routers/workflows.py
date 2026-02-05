"""
Workflow API Router

Endpoints for managing approval workflows.
"""

from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ...workflows import (
    ApprovalDecision,
    WorkflowDefinition,
    WorkflowInstance,
    WorkflowStatus,
    get_workflow_engine,
)

router = APIRouter()


# =============================================================================
# Pydantic Schemas
# =============================================================================


class WorkflowStageResponse(BaseModel):
    """Workflow stage response."""
    id: str
    name: str
    stage_type: str
    sequence: int
    approver_roles: list[str]
    approver_users: list[str]
    approval_mode: str
    due_days: int
    required: bool
    instructions: str


class WorkflowDefinitionResponse(BaseModel):
    """Workflow definition response."""
    id: str
    name: str
    description: str
    version: str
    entity_types: list[str]
    stages: list[WorkflowStageResponse]
    is_active: bool


class StartWorkflowRequest(BaseModel):
    """Request to start a workflow."""
    definition_id: str
    entity_type: str
    entity_id: str
    entity_number: str
    comments: str = ""
    context: dict = Field(default_factory=dict)


class WorkflowTaskResponse(BaseModel):
    """Workflow task response."""
    id: str
    instance_id: str
    stage_id: str
    stage_name: str
    assignee_id: str
    assignee_name: str
    assignee_type: str
    decision: str
    decision_date: Optional[str] = None
    comments: str
    conditions: list[str]
    due_date: Optional[str] = None
    is_complete: bool
    is_overdue: bool


class WorkflowTransitionResponse(BaseModel):
    """Workflow transition response."""
    id: str
    timestamp: str
    from_stage: Optional[str] = None
    to_stage: Optional[str] = None
    from_status: Optional[str] = None
    to_status: Optional[str] = None
    triggered_by: str
    trigger_type: str
    decision: Optional[str] = None
    comments: str


class WorkflowInstanceResponse(BaseModel):
    """Workflow instance response."""
    id: str
    definition_id: str
    definition_name: str
    entity_type: str
    entity_id: str
    entity_number: str
    status: str
    current_stage_id: Optional[str] = None
    current_stage_name: Optional[str] = None
    initiated_by: Optional[str] = None
    initiated_at: Optional[str] = None
    completed_at: Optional[str] = None
    pending_tasks: int
    completed_tasks: int
    tasks: list[WorkflowTaskResponse] = Field(default_factory=list)
    transitions: list[WorkflowTransitionResponse] = Field(default_factory=list)


class DecisionRequest(BaseModel):
    """Request to process an approval decision."""
    decision: str = Field(..., description="approved, rejected, approved_with_conditions")
    comments: str = ""
    conditions: list[str] = Field(default_factory=list)


class DelegateRequest(BaseModel):
    """Request to delegate a task."""
    to_user_id: str
    to_user_name: str
    comments: str = ""


class RecallRequest(BaseModel):
    """Request to recall a workflow."""
    reason: str = ""


# =============================================================================
# Definition Endpoints
# =============================================================================


@router.get("/definitions", response_model=list[WorkflowDefinitionResponse])
async def list_definitions(entity_type: Optional[str] = None):
    """List all workflow definitions, optionally filtered by entity type."""
    engine = get_workflow_engine()

    if entity_type:
        definitions = engine.get_definitions_for_entity(entity_type)
    else:
        definitions = engine.list_definitions()

    return [
        WorkflowDefinitionResponse(
            id=d.id,
            name=d.name,
            description=d.description,
            version=d.version,
            entity_types=d.entity_types,
            stages=[
                WorkflowStageResponse(
                    id=s.id,
                    name=s.name,
                    stage_type=s.stage_type.value,
                    sequence=s.sequence,
                    approver_roles=s.approver_roles,
                    approver_users=s.approver_users,
                    approval_mode=s.approval_mode.value,
                    due_days=s.due_days,
                    required=s.required,
                    instructions=s.instructions,
                )
                for s in d.stages
            ],
            is_active=d.is_active,
        )
        for d in definitions
    ]


@router.get("/definitions/{definition_id}", response_model=WorkflowDefinitionResponse)
async def get_definition(definition_id: str):
    """Get a workflow definition by ID."""
    engine = get_workflow_engine()
    d = engine.get_definition(definition_id)

    if not d:
        raise HTTPException(status_code=404, detail="Workflow definition not found")

    return WorkflowDefinitionResponse(
        id=d.id,
        name=d.name,
        description=d.description,
        version=d.version,
        entity_types=d.entity_types,
        stages=[
            WorkflowStageResponse(
                id=s.id,
                name=s.name,
                stage_type=s.stage_type.value,
                sequence=s.sequence,
                approver_roles=s.approver_roles,
                approver_users=s.approver_users,
                approval_mode=s.approval_mode.value,
                due_days=s.due_days,
                required=s.required,
                instructions=s.instructions,
            )
            for s in d.stages
        ],
        is_active=d.is_active,
    )


# =============================================================================
# Instance Endpoints
# =============================================================================


@router.post("/instances", response_model=WorkflowInstanceResponse)
async def start_workflow(data: StartWorkflowRequest, user_id: str = Query(...)):
    """Start a new workflow instance."""
    engine = get_workflow_engine()

    try:
        instance = engine.start_workflow(
            definition_id=data.definition_id,
            entity_type=data.entity_type,
            entity_id=data.entity_id,
            entity_number=data.entity_number,
            initiated_by=user_id,
            comments=data.comments,
            context=data.context,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return _instance_to_response(instance)


@router.get("/instances", response_model=list[WorkflowInstanceResponse])
async def list_instances(
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    status: Optional[str] = None,
    active_only: bool = False,
):
    """List workflow instances with optional filters."""
    engine = get_workflow_engine()

    if entity_type and entity_id:
        instances = engine.get_instances_for_entity(entity_type, entity_id)
    elif active_only:
        instances = engine.get_active_instances()
    else:
        instances = list(engine._instances.values())

    if status:
        try:
            status_enum = WorkflowStatus(status)
            instances = [i for i in instances if i.status == status_enum]
        except ValueError:
            pass

    return [_instance_to_response(i) for i in instances]


@router.get("/instances/{instance_id}", response_model=WorkflowInstanceResponse)
async def get_instance(instance_id: str):
    """Get a workflow instance by ID."""
    engine = get_workflow_engine()
    instance = engine.get_instance(instance_id)

    if not instance:
        raise HTTPException(status_code=404, detail="Workflow instance not found")

    return _instance_to_response(instance)


@router.post("/instances/{instance_id}/recall", response_model=WorkflowInstanceResponse)
async def recall_workflow(instance_id: str, data: RecallRequest, user_id: str = Query(...)):
    """Recall (cancel) a workflow."""
    engine = get_workflow_engine()

    try:
        instance = engine.recall_workflow(
            instance_id=instance_id,
            user_id=user_id,
            reason=data.reason,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return _instance_to_response(instance)


# =============================================================================
# Task Endpoints
# =============================================================================


@router.get("/tasks", response_model=list[WorkflowTaskResponse])
async def list_my_tasks(user_id: str = Query(...), role: Optional[str] = None):
    """List pending tasks for a user or role."""
    engine = get_workflow_engine()

    tasks = engine.get_tasks_for_user(user_id)
    if role:
        tasks.extend(engine.get_tasks_for_role(role))

    return [_task_to_response(t) for t in tasks]


@router.post("/instances/{instance_id}/tasks/{task_id}/decide", response_model=WorkflowInstanceResponse)
async def process_decision(
    instance_id: str,
    task_id: str,
    data: DecisionRequest,
    user_id: str = Query(...),
):
    """Process an approval decision on a task."""
    engine = get_workflow_engine()

    try:
        decision = ApprovalDecision(data.decision)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid decision: {data.decision}. Valid: approved, rejected, approved_with_conditions"
        )

    try:
        instance = engine.process_decision(
            instance_id=instance_id,
            task_id=task_id,
            decision=decision,
            user_id=user_id,
            comments=data.comments,
            conditions=data.conditions if data.conditions else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return _instance_to_response(instance)


@router.post("/instances/{instance_id}/tasks/{task_id}/delegate", response_model=WorkflowTaskResponse)
async def delegate_task(
    instance_id: str,
    task_id: str,
    data: DelegateRequest,
    user_id: str = Query(...),
):
    """Delegate a task to another user."""
    engine = get_workflow_engine()

    try:
        task = engine.delegate_task(
            instance_id=instance_id,
            task_id=task_id,
            from_user=user_id,
            to_user=data.to_user_id,
            to_user_name=data.to_user_name,
            comments=data.comments,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return _task_to_response(task)


# =============================================================================
# Helper Functions
# =============================================================================


def _instance_to_response(instance: WorkflowInstance) -> WorkflowInstanceResponse:
    """Convert WorkflowInstance to response model."""
    return WorkflowInstanceResponse(
        id=instance.id,
        definition_id=instance.definition_id,
        definition_name=instance.definition_name,
        entity_type=instance.entity_type,
        entity_id=instance.entity_id,
        entity_number=instance.entity_number,
        status=instance.status.value,
        current_stage_id=instance.current_stage_id,
        current_stage_name=instance.current_stage_name,
        initiated_by=instance.initiated_by,
        initiated_at=instance.initiated_at.isoformat() if instance.initiated_at else None,
        completed_at=instance.completed_at.isoformat() if instance.completed_at else None,
        pending_tasks=len(instance.pending_tasks),
        completed_tasks=len(instance.completed_tasks),
        tasks=[_task_to_response(t) for t in instance.tasks],
        transitions=[_transition_to_response(tr) for tr in instance.transitions],
    )


def _task_to_response(task) -> WorkflowTaskResponse:
    """Convert WorkflowTask to response model."""
    return WorkflowTaskResponse(
        id=task.id,
        instance_id=task.instance_id,
        stage_id=task.stage_id,
        stage_name=task.stage_name,
        assignee_id=task.assignee_id,
        assignee_name=task.assignee_name,
        assignee_type=task.assignee_type,
        decision=task.decision.value,
        decision_date=task.decision_date.isoformat() if task.decision_date else None,
        comments=task.comments,
        conditions=task.conditions,
        due_date=task.due_date.isoformat() if task.due_date else None,
        is_complete=task.is_complete,
        is_overdue=task.is_overdue,
    )


def _transition_to_response(transition) -> WorkflowTransitionResponse:
    """Convert WorkflowTransition to response model."""
    return WorkflowTransitionResponse(
        id=transition.id,
        timestamp=transition.timestamp.isoformat(),
        from_stage=transition.from_stage_name,
        to_stage=transition.to_stage_name,
        from_status=transition.from_status.value if transition.from_status else None,
        to_status=transition.to_status.value if transition.to_status else None,
        triggered_by=transition.triggered_by,
        trigger_type=transition.trigger_type,
        decision=transition.decision.value if transition.decision else None,
        comments=transition.comments,
    )
