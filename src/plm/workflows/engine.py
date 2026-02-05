"""
Workflow Engine

Core execution logic for approval workflows.

The engine manages:
- Starting workflow instances
- Processing approval decisions
- Advancing through stages
- Handling rejections and recalls
- Tracking history
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import uuid4

from .models import (
    ApprovalDecision,
    ApprovalMode,
    StageType,
    WorkflowDefinition,
    WorkflowInstance,
    WorkflowStage,
    WorkflowStatus,
    WorkflowTask,
    WorkflowTransition,
    create_eco_workflow,
    create_document_review_workflow,
    create_part_release_workflow,
)

logger = logging.getLogger(__name__)


class WorkflowEngine:
    """
    Workflow execution engine.

    Manages workflow lifecycle from initiation through completion.
    """

    def __init__(self):
        # In-memory storage (replace with DB in production)
        self._definitions: dict[str, WorkflowDefinition] = {}
        self._instances: dict[str, WorkflowInstance] = {}

        # Load built-in workflows
        self._load_builtin_workflows()

    def _load_builtin_workflows(self) -> None:
        """Load pre-built workflow definitions."""
        for wf in [
            create_eco_workflow(),
            create_document_review_workflow(),
            create_part_release_workflow(),
        ]:
            self._definitions[wf.id] = wf

    # =========================================================================
    # Definition Management
    # =========================================================================

    def register_definition(self, definition: WorkflowDefinition) -> None:
        """Register a workflow definition."""
        self._definitions[definition.id] = definition
        logger.info(f"Registered workflow definition: {definition.name}")

    def get_definition(self, definition_id: str) -> Optional[WorkflowDefinition]:
        """Get a workflow definition by ID."""
        return self._definitions.get(definition_id)

    def get_definitions_for_entity(self, entity_type: str) -> list[WorkflowDefinition]:
        """Get all workflow definitions for an entity type."""
        return [
            d for d in self._definitions.values()
            if entity_type in d.entity_types and d.is_active
        ]

    def list_definitions(self) -> list[WorkflowDefinition]:
        """List all workflow definitions."""
        return list(self._definitions.values())

    # =========================================================================
    # Instance Management
    # =========================================================================

    def start_workflow(
        self,
        definition_id: str,
        entity_type: str,
        entity_id: str,
        entity_number: str,
        initiated_by: str,
        comments: str = "",
        context: dict[str, Any] | None = None,
    ) -> WorkflowInstance:
        """
        Start a new workflow instance.

        Args:
            definition_id: ID of workflow definition
            entity_type: Type of entity (eco, document, part)
            entity_id: Entity ID
            entity_number: Display number for entity
            initiated_by: User starting the workflow
            comments: Optional submission comments
            context: Additional context data

        Returns:
            New WorkflowInstance
        """
        definition = self.get_definition(definition_id)
        if not definition:
            raise ValueError(f"Workflow definition not found: {definition_id}")

        instance = WorkflowInstance(
            id=str(uuid4()),
            definition_id=definition_id,
            definition_name=definition.name,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_number=entity_number,
            status=WorkflowStatus.ACTIVE,
            initiated_by=initiated_by,
            submission_comments=comments,
            context=context or {},
        )

        # Add initial transition
        instance.add_transition(WorkflowTransition(
            id=str(uuid4()),
            instance_id=instance.id,
            timestamp=datetime.now(),
            from_status=WorkflowStatus.DRAFT,
            to_status=WorkflowStatus.ACTIVE,
            triggered_by=initiated_by,
            trigger_type="initiation",
            comments=comments,
        ))

        # Move to first stage
        first_stage = definition.get_first_stage()
        if first_stage:
            self._enter_stage(instance, definition, first_stage, initiated_by)

        self._instances[instance.id] = instance
        logger.info(f"Started workflow {instance.id} for {entity_type} {entity_number}")

        return instance

    def get_instance(self, instance_id: str) -> Optional[WorkflowInstance]:
        """Get a workflow instance by ID."""
        return self._instances.get(instance_id)

    def get_instances_for_entity(self, entity_type: str, entity_id: str) -> list[WorkflowInstance]:
        """Get all workflow instances for an entity."""
        return [
            i for i in self._instances.values()
            if i.entity_type == entity_type and i.entity_id == entity_id
        ]

    def get_active_instances(self) -> list[WorkflowInstance]:
        """Get all active workflow instances."""
        active_statuses = [WorkflowStatus.ACTIVE, WorkflowStatus.PENDING_APPROVAL]
        return [i for i in self._instances.values() if i.status in active_statuses]

    def get_tasks_for_user(self, user_id: str) -> list[WorkflowTask]:
        """Get all pending tasks assigned to a user."""
        tasks = []
        for instance in self._instances.values():
            for task in instance.pending_tasks:
                if task.assignee_id == user_id:
                    tasks.append(task)
        return tasks

    def get_tasks_for_role(self, role: str) -> list[WorkflowTask]:
        """Get all pending tasks for a role."""
        tasks = []
        for instance in self._instances.values():
            for task in instance.pending_tasks:
                if task.assignee_type == "role" and task.assignee_id == role:
                    tasks.append(task)
        return tasks

    # =========================================================================
    # Task Processing
    # =========================================================================

    def process_decision(
        self,
        instance_id: str,
        task_id: str,
        decision: ApprovalDecision,
        user_id: str,
        comments: str = "",
        conditions: list[str] | None = None,
    ) -> WorkflowInstance:
        """
        Process an approval decision.

        Args:
            instance_id: Workflow instance ID
            task_id: Task ID being decided
            decision: The approval decision
            user_id: User making the decision
            comments: Optional comments
            conditions: Optional conditions (for conditional approval)

        Returns:
            Updated WorkflowInstance
        """
        instance = self.get_instance(instance_id)
        if not instance:
            raise ValueError(f"Workflow instance not found: {instance_id}")

        task = instance.get_task(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")

        if task.is_complete:
            raise ValueError(f"Task already completed: {task_id}")

        definition = self.get_definition(instance.definition_id)
        if not definition:
            raise ValueError(f"Workflow definition not found: {instance.definition_id}")

        # Update task
        task.decision = decision
        task.decision_date = datetime.now()
        task.completed_at = datetime.now()
        task.comments = comments
        if conditions:
            task.conditions = conditions

        # Record transition
        instance.add_transition(WorkflowTransition(
            id=str(uuid4()),
            instance_id=instance.id,
            timestamp=datetime.now(),
            from_stage_id=instance.current_stage_id,
            from_stage_name=instance.current_stage_name,
            to_stage_id=instance.current_stage_id,
            to_stage_name=instance.current_stage_name,
            triggered_by=user_id,
            trigger_type="decision",
            task_id=task_id,
            decision=decision,
            comments=comments,
        ))

        # Evaluate stage completion
        stage = definition.get_stage(instance.current_stage_id or "")
        if stage:
            self._evaluate_stage(instance, definition, stage, user_id)

        logger.info(
            f"Processed decision {decision.value} for task {task_id} "
            f"in workflow {instance_id}"
        )

        return instance

    def delegate_task(
        self,
        instance_id: str,
        task_id: str,
        from_user: str,
        to_user: str,
        to_user_name: str,
        comments: str = "",
    ) -> WorkflowTask:
        """
        Delegate a task to another user.

        Args:
            instance_id: Workflow instance ID
            task_id: Task ID to delegate
            from_user: User delegating
            to_user: User receiving delegation
            to_user_name: Display name of receiving user
            comments: Delegation comments

        Returns:
            Updated WorkflowTask
        """
        instance = self.get_instance(instance_id)
        if not instance:
            raise ValueError(f"Workflow instance not found: {instance_id}")

        task = instance.get_task(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")

        if task.is_complete:
            raise ValueError(f"Task already completed: {task_id}")

        # Create new task for delegatee
        new_task = WorkflowTask(
            id=str(uuid4()),
            instance_id=instance_id,
            stage_id=task.stage_id,
            stage_name=task.stage_name,
            assignee_id=to_user,
            assignee_name=to_user_name,
            assignee_type="user",
            delegated_from=from_user,
            due_date=task.due_date,
        )
        instance.add_task(new_task)

        # Mark original task as delegated
        task.decision = ApprovalDecision.DELEGATE
        task.completed_at = datetime.now()
        task.delegated_to = to_user
        task.comments = comments

        logger.info(f"Delegated task {task_id} from {from_user} to {to_user}")

        return new_task

    def recall_workflow(
        self,
        instance_id: str,
        user_id: str,
        reason: str = "",
    ) -> WorkflowInstance:
        """
        Recall a workflow (cancel by submitter).

        Args:
            instance_id: Workflow instance ID
            user_id: User recalling (must be initiator)
            reason: Reason for recall

        Returns:
            Updated WorkflowInstance
        """
        instance = self.get_instance(instance_id)
        if not instance:
            raise ValueError(f"Workflow instance not found: {instance_id}")

        if instance.initiated_by != user_id:
            raise ValueError("Only the initiator can recall a workflow")

        if instance.status not in [WorkflowStatus.ACTIVE, WorkflowStatus.PENDING_APPROVAL]:
            raise ValueError(f"Cannot recall workflow in status: {instance.status.value}")

        # Mark all pending tasks as recalled
        for task in instance.pending_tasks:
            task.decision = ApprovalDecision.RECALLED
            task.completed_at = datetime.now()

        # Update instance
        old_status = instance.status
        instance.status = WorkflowStatus.CANCELLED
        instance.completed_at = datetime.now()
        instance.final_comments = reason

        # Record transition
        instance.add_transition(WorkflowTransition(
            id=str(uuid4()),
            instance_id=instance.id,
            timestamp=datetime.now(),
            from_stage_id=instance.current_stage_id,
            from_stage_name=instance.current_stage_name,
            from_status=old_status,
            to_status=WorkflowStatus.CANCELLED,
            triggered_by=user_id,
            trigger_type="recall",
            comments=reason,
        ))

        logger.info(f"Recalled workflow {instance_id}")

        return instance

    # =========================================================================
    # Internal Methods
    # =========================================================================

    def _enter_stage(
        self,
        instance: WorkflowInstance,
        definition: WorkflowDefinition,
        stage: WorkflowStage,
        triggered_by: str,
    ) -> None:
        """Enter a new workflow stage."""
        old_stage_id = instance.current_stage_id
        old_stage_name = instance.current_stage_name

        instance.current_stage_id = stage.id
        instance.current_stage_name = stage.name
        instance.status = WorkflowStatus.PENDING_APPROVAL

        # Create tasks for this stage
        due_date = datetime.now() + timedelta(days=stage.due_days)

        if stage.approver_users:
            # Specific users
            for user_id in stage.approver_users:
                task = WorkflowTask(
                    id=str(uuid4()),
                    instance_id=instance.id,
                    stage_id=stage.id,
                    stage_name=stage.name,
                    assignee_id=user_id,
                    assignee_name=user_id,  # Would look up real name
                    assignee_type="user",
                    due_date=due_date,
                )
                instance.add_task(task)

        if stage.approver_roles:
            # Role-based assignment
            for role in stage.approver_roles:
                task = WorkflowTask(
                    id=str(uuid4()),
                    instance_id=instance.id,
                    stage_id=stage.id,
                    stage_name=stage.name,
                    assignee_id=role,
                    assignee_name=role.replace("_", " ").title(),
                    assignee_type="role",
                    due_date=due_date,
                )
                instance.add_task(task)

        # Record transition
        instance.add_transition(WorkflowTransition(
            id=str(uuid4()),
            instance_id=instance.id,
            timestamp=datetime.now(),
            from_stage_id=old_stage_id,
            from_stage_name=old_stage_name,
            to_stage_id=stage.id,
            to_stage_name=stage.name,
            triggered_by=triggered_by,
            trigger_type="stage_advance",
        ))

        logger.info(f"Entered stage {stage.name} for workflow {instance.id}")

    def _evaluate_stage(
        self,
        instance: WorkflowInstance,
        definition: WorkflowDefinition,
        stage: WorkflowStage,
        triggered_by: str,
    ) -> None:
        """Evaluate if stage is complete and what happens next."""
        stage_tasks = instance.current_stage_tasks
        pending = [t for t in stage_tasks if not t.is_complete]
        completed = [t for t in stage_tasks if t.is_complete]

        # Check for rejections
        rejections = [t for t in completed if t.decision == ApprovalDecision.REJECTED]
        if rejections:
            self._handle_rejection(instance, definition, stage, rejections[0], triggered_by)
            return

        # Check completion based on approval mode
        approvals = [
            t for t in completed
            if t.decision in [ApprovalDecision.APPROVED, ApprovalDecision.APPROVED_WITH_CONDITIONS]
        ]

        stage_complete = False
        if stage.approval_mode == ApprovalMode.ALL:
            stage_complete = len(pending) == 0 and len(approvals) == len(completed)
        elif stage.approval_mode == ApprovalMode.ANY:
            stage_complete = len(approvals) > 0
        elif stage.approval_mode == ApprovalMode.MAJORITY:
            total = len(stage_tasks)
            stage_complete = len(approvals) > total / 2
        elif stage.approval_mode == ApprovalMode.FIRST:
            stage_complete = len(completed) > 0

        if stage_complete:
            # Advance to next stage
            next_stage = definition.get_next_stage(stage.id)
            if next_stage:
                self._enter_stage(instance, definition, next_stage, triggered_by)
            else:
                # Workflow complete
                self._complete_workflow(instance, triggered_by)

    def _handle_rejection(
        self,
        instance: WorkflowInstance,
        definition: WorkflowDefinition,
        stage: WorkflowStage,
        rejection_task: WorkflowTask,
        triggered_by: str,
    ) -> None:
        """Handle a workflow rejection."""
        old_status = instance.status
        instance.status = WorkflowStatus.REJECTED
        instance.completed_at = datetime.now()
        instance.final_comments = rejection_task.comments

        # Record transition
        instance.add_transition(WorkflowTransition(
            id=str(uuid4()),
            instance_id=instance.id,
            timestamp=datetime.now(),
            from_stage_id=instance.current_stage_id,
            from_stage_name=instance.current_stage_name,
            from_status=old_status,
            to_status=WorkflowStatus.REJECTED,
            triggered_by=triggered_by,
            trigger_type="rejection",
            task_id=rejection_task.id,
            decision=ApprovalDecision.REJECTED,
            comments=rejection_task.comments,
        ))

        logger.info(f"Workflow {instance.id} rejected at stage {stage.name}")

    def _complete_workflow(
        self,
        instance: WorkflowInstance,
        triggered_by: str,
    ) -> None:
        """Complete a workflow successfully."""
        old_status = instance.status
        instance.status = WorkflowStatus.COMPLETED
        instance.completed_at = datetime.now()

        # Record transition
        instance.add_transition(WorkflowTransition(
            id=str(uuid4()),
            instance_id=instance.id,
            timestamp=datetime.now(),
            from_stage_id=instance.current_stage_id,
            from_stage_name=instance.current_stage_name,
            from_status=old_status,
            to_status=WorkflowStatus.COMPLETED,
            triggered_by=triggered_by,
            trigger_type="completion",
        ))

        logger.info(f"Workflow {instance.id} completed successfully")


# Singleton engine instance
_engine: Optional[WorkflowEngine] = None


def get_workflow_engine() -> WorkflowEngine:
    """Get the singleton workflow engine instance."""
    global _engine
    if _engine is None:
        _engine = WorkflowEngine()
    return _engine
