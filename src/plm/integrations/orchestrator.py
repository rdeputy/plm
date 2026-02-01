"""
Orchestrator Integration

Integration with the Orchestrator workflow system.
Allows PLM to:
- Register as a workflow system
- Receive workflow step executions
- Trigger workflows for ECO approval, procurement, etc.
- Report status back to orchestrator
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Optional

import httpx


class TaskStatus(str, Enum):
    """Status of a task dispatched to orchestrator."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class WorkflowTask:
    """A task in an orchestrator workflow."""

    id: str
    workflow_id: str
    step_name: str
    status: TaskStatus
    input_data: dict[str, Any]
    output_data: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class OrchestratorClient:
    """
    Client for communicating with the Orchestrator.

    Used by PLM to:
    - Trigger workflows (e.g., ECO approval workflow)
    - Report step completion
    - Query workflow status
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: Optional[str] = None,
        timeout: int = 30,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.headers = {"Content-Type": "application/json"}
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"

    def trigger_workflow(
        self,
        workflow_name: str,
        input_data: dict[str, Any],
        context: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Trigger a workflow in the orchestrator.

        Args:
            workflow_name: Name of the workflow (e.g., "eco_approval")
            input_data: Initial input for the workflow
            context: Additional context (project_id, etc.)

        Returns:
            Workflow instance info including ID
        """
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                f"{self.base_url}/api/workflows/trigger",
                headers=self.headers,
                json={
                    "workflow_name": workflow_name,
                    "input_data": input_data,
                    "context": context or {},
                },
            )
            response.raise_for_status()
            return response.json()

    def get_workflow_status(self, workflow_id: str) -> dict[str, Any]:
        """Get current status of a workflow instance."""
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(
                f"{self.base_url}/api/workflows/{workflow_id}",
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()

    def report_step_completion(
        self,
        workflow_id: str,
        step_id: str,
        output_data: dict[str, Any],
        success: bool = True,
        error: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Report completion of a workflow step.

        Called when PLM finishes processing a step dispatched by orchestrator.
        """
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                f"{self.base_url}/api/workflows/{workflow_id}/steps/{step_id}/complete",
                headers=self.headers,
                json={
                    "success": success,
                    "output_data": output_data,
                    "error": error,
                },
            )
            response.raise_for_status()
            return response.json()

    def cancel_workflow(self, workflow_id: str, reason: str) -> dict[str, Any]:
        """Cancel a running workflow."""
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                f"{self.base_url}/api/workflows/{workflow_id}/cancel",
                headers=self.headers,
                json={"reason": reason},
            )
            response.raise_for_status()
            return response.json()

    # ----- PLM-Specific Workflow Triggers -----

    def trigger_eco_approval(
        self,
        eco_id: str,
        eco_number: str,
        title: str,
        urgency: str,
        affected_parts: list[str],
        project_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Trigger ECO approval workflow."""
        return self.trigger_workflow(
            workflow_name="eco_approval",
            input_data={
                "eco_id": eco_id,
                "eco_number": eco_number,
                "title": title,
                "urgency": urgency,
                "affected_parts": affected_parts,
            },
            context={"project_id": project_id, "source": "plm"},
        )

    def trigger_procurement_review(
        self,
        po_id: str,
        po_number: str,
        vendor_id: str,
        total_value: Decimal,
        project_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Trigger procurement review workflow for high-value POs."""
        return self.trigger_workflow(
            workflow_name="procurement_review",
            input_data={
                "po_id": po_id,
                "po_number": po_number,
                "vendor_id": vendor_id,
                "total_value": float(total_value),
            },
            context={"project_id": project_id, "source": "plm"},
        )

    def trigger_inventory_alert(
        self,
        part_id: str,
        part_number: str,
        location_id: str,
        current_quantity: Decimal,
        reorder_point: Decimal,
        priority: str,
    ) -> dict[str, Any]:
        """Trigger inventory reorder workflow."""
        return self.trigger_workflow(
            workflow_name="inventory_reorder",
            input_data={
                "part_id": part_id,
                "part_number": part_number,
                "location_id": location_id,
                "current_quantity": float(current_quantity),
                "reorder_point": float(reorder_point),
                "priority": priority,
            },
            context={"source": "plm"},
        )


class PLMTaskHandler:
    """
    Handler for tasks dispatched from orchestrator to PLM.

    Registered as callbacks for different task types.
    """

    def __init__(self, plm_services: dict):
        """
        Initialize with PLM service instances.

        services should include:
        - inventory_service: InventoryService
        - procurement_service: ProcurementService
        - etc.
        """
        self.services = plm_services
        self._handlers = {
            "check_inventory": self._handle_check_inventory,
            "create_po": self._handle_create_po,
            "update_po_status": self._handle_update_po_status,
            "check_part_availability": self._handle_check_availability,
            "get_bom_cost": self._handle_get_bom_cost,
            "reserve_inventory": self._handle_reserve_inventory,
            "release_inventory": self._handle_release_inventory,
        }

    def handle_task(self, task_type: str, input_data: dict) -> dict[str, Any]:
        """
        Handle a task from the orchestrator.

        Returns output data for the workflow.
        """
        handler = self._handlers.get(task_type)
        if not handler:
            return {"error": f"Unknown task type: {task_type}"}

        try:
            return handler(input_data)
        except Exception as e:
            return {"error": str(e)}

    def _handle_check_inventory(self, data: dict) -> dict:
        """Check inventory levels for parts."""
        service = self.services.get("inventory_service")
        if not service:
            return {"error": "Inventory service not available"}

        part_ids = data.get("part_ids", [])
        location_id = data.get("location_id")

        results = []
        for part_id in part_ids:
            item = service.get_stock_at_location(part_id, location_id)
            if item:
                results.append(
                    {
                        "part_id": part_id,
                        "on_hand": float(item.on_hand),
                        "available": float(item.available),
                        "needs_reorder": item.needs_reorder(),
                    }
                )
            else:
                results.append({"part_id": part_id, "on_hand": 0, "available": 0})

        return {"inventory": results}

    def _handle_create_po(self, data: dict) -> dict:
        """Create a purchase order from workflow."""
        service = self.services.get("procurement_service")
        if not service:
            return {"error": "Procurement service not available"}

        po = service.create_purchase_order(
            vendor_id=data["vendor_id"],
            items=data["items"],
            ship_to_location_id=data.get("location_id"),
            required_date=data.get("required_date"),
            project_id=data.get("project_id"),
            created_by=data.get("created_by", "orchestrator"),
        )

        return {
            "po_id": po.id,
            "po_number": po.po_number,
            "total": float(po.total),
            "status": po.status.value,
        }

    def _handle_update_po_status(self, data: dict) -> dict:
        """Update PO status from workflow."""
        service = self.services.get("procurement_service")
        if not service:
            return {"error": "Procurement service not available"}

        po_id = data["po_id"]
        action = data["action"]

        if action == "approve":
            po = service.approve_purchase_order(
                po_id, data.get("approved_by", "orchestrator")
            )
        elif action == "send":
            po = service.send_purchase_order(po_id)
        elif action == "cancel":
            po = service.cancel_purchase_order(po_id, data.get("reason", "Workflow"))
        else:
            return {"error": f"Unknown action: {action}"}

        return {"po_id": po.id, "status": po.status.value}

    def _handle_check_availability(self, data: dict) -> dict:
        """Check if parts are available for a project."""
        service = self.services.get("inventory_service")
        if not service:
            return {"error": "Inventory service not available"}

        requirements = data.get("requirements", [])  # [{part_id, quantity, location_id}]
        all_available = True
        shortages = []

        for req in requirements:
            item = service.get_stock_at_location(req["part_id"], req["location_id"])
            available = item.available if item else Decimal("0")
            needed = Decimal(str(req["quantity"]))

            if available < needed:
                all_available = False
                shortages.append(
                    {
                        "part_id": req["part_id"],
                        "needed": float(needed),
                        "available": float(available),
                        "shortage": float(needed - available),
                    }
                )

        return {"all_available": all_available, "shortages": shortages}

    def _handle_get_bom_cost(self, data: dict) -> dict:
        """Calculate BOM cost."""
        # This would integrate with BOM service
        return {"cost": 0, "currency": "USD", "message": "BOM cost calculation pending"}

    def _handle_reserve_inventory(self, data: dict) -> dict:
        """Reserve inventory for a project."""
        service = self.services.get("inventory_service")
        if not service:
            return {"error": "Inventory service not available"}

        reservations = data.get("reservations", [])
        results = []

        for res in reservations:
            try:
                txn = service.reserve(
                    part_id=res["part_id"],
                    location_id=res["location_id"],
                    quantity=Decimal(str(res["quantity"])),
                    project_id=data.get("project_id"),
                    created_by=data.get("created_by", "orchestrator"),
                )
                results.append(
                    {
                        "part_id": res["part_id"],
                        "reserved": True,
                        "transaction_id": txn.id,
                    }
                )
            except Exception as e:
                results.append(
                    {"part_id": res["part_id"], "reserved": False, "error": str(e)}
                )

        return {"reservations": results}

    def _handle_release_inventory(self, data: dict) -> dict:
        """Release reserved inventory."""
        service = self.services.get("inventory_service")
        if not service:
            return {"error": "Inventory service not available"}

        releases = data.get("releases", [])
        results = []

        for rel in releases:
            try:
                txn = service.unreserve(
                    part_id=rel["part_id"],
                    location_id=rel["location_id"],
                    quantity=Decimal(str(rel["quantity"])),
                    project_id=data.get("project_id"),
                    created_by=data.get("created_by", "orchestrator"),
                )
                results.append(
                    {
                        "part_id": rel["part_id"],
                        "released": True,
                        "transaction_id": txn.id,
                    }
                )
            except Exception as e:
                results.append(
                    {"part_id": rel["part_id"], "released": False, "error": str(e)}
                )

        return {"releases": results}
