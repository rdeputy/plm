"""
Workflow Engine Module

Generic approval workflow system for PLM entities.
Supports configurable workflow definitions with:
- Multiple approval stages
- Parallel and sequential approvers
- Conditional routing
- Delegation and escalation
"""
from .models import (
    WorkflowStatus,
    ApprovalDecision,
    WorkflowDefinition,
    WorkflowStage,
    WorkflowInstance,
    WorkflowTask,
    WorkflowTransition,
)
from .engine import WorkflowEngine, get_workflow_engine

__all__ = [
    # Models
    "WorkflowStatus",
    "ApprovalDecision",
    "WorkflowDefinition",
    "WorkflowStage",
    "WorkflowInstance",
    "WorkflowTask",
    "WorkflowTransition",
    # Engine
    "WorkflowEngine",
    "get_workflow_engine",
]
