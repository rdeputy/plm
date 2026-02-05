"""
PLM Manager

Central service for Product Lifecycle Management.
Backed by SQLAlchemy database layer.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
import uuid

from sqlalchemy.orm import Session

from .parts import Part, PartRevision, PartStatus, PartType, UnitOfMeasure, increment_revision
from .boms import BOM, BOMItem, BOMType, BOMComparison, Effectivity, ExplodedBOMItem
from .changes import ChangeOrder, Change, Approval, ImpactAnalysis, ECOStatus
from .db.models import (
    PartModel,
    PartRevisionModel,
    BOMModel,
    BOMItemModel,
    ChangeOrderModel,
    ChangeModel,
    ApprovalModel,
)


class PLMManager:
    """
    Central PLM service for design data management.

    Provides:
    - Part management (CRUD, revisions, lifecycle)
    - BOM management (create, explode, compare)
    - Change management (ECOs, approvals, implementation)
    - MRP interface
    """

    def __init__(self, session: Session):
        self._session = session

    # ========================================
    # Part Management
    # ========================================

    def create_part(
        self,
        part_number: str,
        name: str,
        part_type: PartType = PartType.COMPONENT,
        **kwargs,
    ) -> Part:
        """Create a new part."""
        part_id = str(uuid.uuid4())
        model = PartModel(
            id=part_id,
            part_number=part_number,
            revision="A",
            name=name,
            part_type=part_type.value,
            status=PartStatus.DRAFT.value,
            unit_of_measure=kwargs.get("unit_of_measure", UnitOfMeasure.EACH).value
            if isinstance(kwargs.get("unit_of_measure"), UnitOfMeasure)
            else kwargs.get("unit_of_measure", "EA"),
            description=kwargs.get("description"),
            category=kwargs.get("category"),
            csi_code=kwargs.get("csi_code"),
            unit_cost=kwargs.get("unit_cost"),
            manufacturer=kwargs.get("manufacturer"),
            manufacturer_pn=kwargs.get("manufacturer_pn"),
            lead_time_days=kwargs.get("lead_time_days"),
            created_at=datetime.now(),
        )
        self._session.add(model)
        self._session.flush()
        return self._model_to_part(model)

    def get_part(self, part_id: str, revision: str = None) -> Optional[Part]:
        """Get a part by ID, optionally at specific revision."""
        query = self._session.query(PartModel).filter(PartModel.id == part_id)
        if revision:
            query = query.filter(PartModel.revision == revision)
        model = query.first()
        return self._model_to_part(model) if model else None

    def get_part_by_number(self, part_number: str, revision: str = None) -> Optional[Part]:
        """Get a part by part number."""
        query = self._session.query(PartModel).filter(PartModel.part_number == part_number)
        if revision:
            query = query.filter(PartModel.revision == revision)
        model = query.first()
        return self._model_to_part(model) if model else None

    def revise_part(self, part_id: str, change_summary: str, eco_id: str = None) -> Part:
        """Create a new revision of a part."""
        model = self._session.query(PartModel).filter(PartModel.id == part_id).first()
        if not model:
            raise ValueError(f"Part not found: {part_id}")
        if model.status not in [PartStatus.RELEASED.value]:
            raise ValueError(f"Part cannot be revised in status {model.status}")

        # Store revision record
        rev = PartRevisionModel(
            id=str(uuid.uuid4()),
            part_id=part_id,
            revision=model.revision,
            change_summary=change_summary,
            change_order_id=eco_id,
            status=PartStatus.RELEASED.value,
            released_at=datetime.now(),
            created_at=datetime.now(),
        )
        self._session.add(rev)

        # Create new revision entry
        new_revision = increment_revision(model.revision)
        new_model = PartModel(
            id=str(uuid.uuid4()),
            part_number=model.part_number,
            revision=new_revision,
            name=model.name,
            description=model.description,
            part_type=model.part_type,
            status=PartStatus.DRAFT.value,
            category=model.category,
            csi_code=model.csi_code,
            unit_of_measure=model.unit_of_measure,
            unit_cost=model.unit_cost,
            manufacturer=model.manufacturer,
            manufacturer_pn=model.manufacturer_pn,
            lead_time_days=model.lead_time_days,
            created_at=datetime.now(),
        )
        self._session.add(new_model)
        self._session.flush()
        return self._model_to_part(new_model)

    def release_part(self, part_id: str, approver: str) -> Part:
        """Release a part for use."""
        model = self._session.query(PartModel).filter(PartModel.id == part_id).first()
        if not model:
            raise ValueError(f"Part not found: {part_id}")
        if model.status not in [PartStatus.DRAFT.value, PartStatus.IN_REVIEW.value]:
            raise ValueError(f"Part cannot be released in status {model.status}")

        model.status = PartStatus.RELEASED.value
        model.released_by = approver
        model.released_at = datetime.now()
        self._session.flush()
        return self._model_to_part(model)

    def obsolete_part(self, part_id: str, reason: str, replaced_by: str = None) -> Part:
        """Obsolete a part."""
        model = self._session.query(PartModel).filter(PartModel.id == part_id).first()
        if not model:
            raise ValueError(f"Part not found: {part_id}")

        model.status = PartStatus.OBSOLETE.value
        model.obsoleted_at = datetime.now()
        attrs = model.attributes or {}
        attrs["obsolete_reason"] = reason
        if replaced_by:
            attrs["replaced_by"] = replaced_by
        model.attributes = attrs
        self._session.flush()
        return self._model_to_part(model)

    def search_parts(self, query: str, filters: dict = None) -> list[Part]:
        """Search parts by query string."""
        search_term = f"%{query}%"
        q = self._session.query(PartModel).filter(
            (PartModel.part_number.ilike(search_term))
            | (PartModel.name.ilike(search_term))
            | (PartModel.description.ilike(search_term))
        )

        if filters:
            if "status" in filters:
                q = q.filter(PartModel.status == filters["status"])
            if "part_type" in filters:
                q = q.filter(PartModel.part_type == filters["part_type"])

        return [self._model_to_part(m) for m in q.all()]

    # ========================================
    # BOM Management
    # ========================================

    def create_bom(
        self,
        bom_number: str,
        name: str,
        parent_part_id: str,
        bom_type: BOMType = BOMType.ENGINEERING,
        **kwargs,
    ) -> BOM:
        """Create a new BOM."""
        bom_id = str(uuid.uuid4())
        parent = self._session.query(PartModel).filter(PartModel.id == parent_part_id).first()

        model = BOMModel(
            id=bom_id,
            bom_number=bom_number,
            revision="A",
            name=name,
            parent_part_id=parent_part_id,
            parent_part_revision=parent.revision if parent else "A",
            bom_type=bom_type.value,
            status=PartStatus.DRAFT.value,
            created_at=datetime.now(),
            project_id=kwargs.get("project_id"),
        )
        self._session.add(model)
        self._session.flush()
        return self._model_to_bom(model)

    def get_bom(self, bom_id: str, revision: str = None) -> Optional[BOM]:
        """Get a BOM by ID."""
        query = self._session.query(BOMModel).filter(BOMModel.id == bom_id)
        if revision:
            query = query.filter(BOMModel.revision == revision)
        model = query.first()
        return self._model_to_bom(model) if model else None

    def add_bom_item(
        self,
        bom_id: str,
        part_id: str,
        quantity: Decimal,
        **kwargs,
    ) -> BOMItem:
        """Add an item to a BOM."""
        bom = self._session.query(BOMModel).filter(BOMModel.id == bom_id).first()
        if not bom:
            raise ValueError(f"BOM not found: {bom_id}")

        part = self._session.query(PartModel).filter(PartModel.id == part_id).first()
        if not part:
            raise ValueError(f"Part not found: {part_id}")

        # Auto-assign find number
        max_find = (
            max((i.find_number for i in bom.items), default=0) if bom.items else 0
        )

        item_id = str(uuid.uuid4())
        item_model = BOMItemModel(
            id=item_id,
            bom_id=bom_id,
            part_id=part_id,
            part_number=part.part_number,
            part_revision=part.revision,
            quantity=quantity,
            unit_of_measure=part.unit_of_measure,
            find_number=kwargs.get("find_number", max_find + 10),
            reference_designator=kwargs.get("reference_designator", ""),
            location=kwargs.get("location"),
            notes=kwargs.get("notes"),
            is_optional=kwargs.get("is_optional", False),
            option_code=kwargs.get("option_code"),
        )
        self._session.add(item_model)
        self._session.flush()

        return BOMItem(
            id=item_id,
            bom_id=bom_id,
            part_id=part_id,
            part_number=part.part_number,
            part_revision=part.revision,
            quantity=quantity,
        )

    def remove_bom_item(self, bom_id: str, item_id: str) -> bool:
        """Remove an item from a BOM."""
        item = (
            self._session.query(BOMItemModel)
            .filter(BOMItemModel.id == item_id, BOMItemModel.bom_id == bom_id)
            .first()
        )
        if not item:
            return False
        self._session.delete(item)
        self._session.flush()
        return True

    def explode_bom(self, bom_id: str, levels: int = -1) -> list[ExplodedBOMItem]:
        """Explode a BOM to show all components."""
        bom_model = self._session.query(BOMModel).filter(BOMModel.id == bom_id).first()
        if not bom_model:
            return []

        result: list[ExplodedBOMItem] = []
        self._explode_recursive(bom_model, result, level=0, max_levels=levels, parent_qty=Decimal("1"), path="")
        return result

    def _explode_recursive(
        self,
        bom_model: BOMModel,
        result: list[ExplodedBOMItem],
        level: int,
        max_levels: int,
        parent_qty: Decimal,
        path: str,
    ) -> None:
        """Recursively explode BOM."""
        if max_levels >= 0 and level > max_levels:
            return

        for item in bom_model.items:
            part = self._session.query(PartModel).filter(PartModel.id == item.part_id).first()
            if not part:
                continue

            extended_qty = item.quantity * parent_qty
            item_path = f"{path}/{part.part_number}" if path else part.part_number

            child_bom = (
                self._session.query(BOMModel)
                .filter(BOMModel.parent_part_id == item.part_id)
                .first()
            )
            is_leaf = child_bom is None

            extended_cost = None
            if part.unit_cost:
                extended_cost = part.unit_cost * extended_qty

            result.append(ExplodedBOMItem(
                part_id=item.part_id,
                part_number=part.part_number,
                part_name=part.name,
                level=level,
                path=item_path,
                quantity=extended_qty,
                unit_of_measure=part.unit_of_measure,
                unit_cost=part.unit_cost,
                extended_cost=extended_cost,
                reference_designator=item.reference_designator,
                is_leaf=is_leaf,
            ))

            if child_bom and (max_levels < 0 or level < max_levels):
                self._explode_recursive(
                    child_bom, result, level + 1, max_levels,
                    extended_qty, item_path,
                )

    def compare_boms(self, bom_id: str, rev_a: str, rev_b: str) -> BOMComparison:
        """Compare two revisions of a BOM."""
        return BOMComparison(
            bom_id=bom_id,
            from_revision=rev_a,
            to_revision=rev_b,
        )

    def roll_up_costs(self, bom_id: str) -> dict:
        """Calculate total cost by rolling up BOM."""
        exploded = self.explode_bom(bom_id)

        total_material = Decimal("0")
        by_category: dict[str, Decimal] = {}

        for item in exploded:
            if item.is_leaf and item.extended_cost:
                total_material += item.extended_cost

                part = self._session.query(PartModel).filter(PartModel.id == item.part_id).first()
                if part and part.category:
                    by_category[part.category] = by_category.get(part.category, Decimal("0")) + item.extended_cost

        return {
            "total_material_cost": float(total_material),
            "by_category": {k: float(v) for k, v in by_category.items()},
            "item_count": len(exploded),
        }

    def where_used(self, part_id: str) -> list[BOM]:
        """Find all BOMs that use a part."""
        items = self._session.query(BOMItemModel).filter(BOMItemModel.part_id == part_id).all()
        bom_ids = {item.bom_id for item in items}
        boms = self._session.query(BOMModel).filter(BOMModel.id.in_(bom_ids)).all()
        return [self._model_to_bom(b) for b in boms]

    # ========================================
    # Change Management
    # ========================================

    def create_eco(
        self,
        title: str,
        description: str = "",
        project_id: str = None,
        **kwargs,
    ) -> ChangeOrder:
        """Create a new Engineering Change Order."""
        eco_id = str(uuid.uuid4())

        eco_count = self._session.query(ChangeOrderModel).count() + 1
        eco_number = f"ECO-{datetime.now().year}-{eco_count:04d}"

        model = ChangeOrderModel(
            id=eco_id,
            eco_number=eco_number,
            title=title,
            description=description,
            project_id=project_id,
            status=ECOStatus.DRAFT.value,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            reason=kwargs.get("reason", "customer_request"),
            urgency=kwargs.get("urgency", "standard"),
        )
        self._session.add(model)
        self._session.flush()
        return self._model_to_eco(model)

    def get_eco(self, eco_id: str) -> Optional[ChangeOrder]:
        """Get an ECO by ID."""
        model = self._session.query(ChangeOrderModel).filter(ChangeOrderModel.id == eco_id).first()
        return self._model_to_eco(model) if model else None

    def submit_eco(self, eco_id: str, submitter: str) -> ChangeOrder:
        """Submit an ECO for review."""
        model = self._session.query(ChangeOrderModel).filter(ChangeOrderModel.id == eco_id).first()
        if not model:
            raise ValueError(f"ECO not found: {eco_id}")
        if model.status != ECOStatus.DRAFT.value:
            raise ValueError(f"Cannot submit ECO in status {model.status}")

        model.status = ECOStatus.SUBMITTED.value
        model.submitted_by = submitter
        model.submitted_at = datetime.now()
        model.updated_at = datetime.now()
        self._session.flush()
        return self._model_to_eco(model)

    def approve_eco(
        self,
        eco_id: str,
        approver_id: str,
        approver_name: str,
        approver_role: str,
        decision: str,
        comments: str = None,
    ) -> Approval:
        """Record an approval decision on an ECO."""
        model = self._session.query(ChangeOrderModel).filter(ChangeOrderModel.id == eco_id).first()
        if not model:
            raise ValueError(f"ECO not found: {eco_id}")

        approval_model = ApprovalModel(
            id=str(uuid.uuid4()),
            eco_id=eco_id,
            approver_id=approver_id,
            approver_name=approver_name,
            approver_role=approver_role,
            decision=decision,
            comments=comments,
            decided_at=datetime.now(),
        )
        self._session.add(approval_model)
        model.updated_at = datetime.now()
        self._session.flush()

        return Approval(
            id=approval_model.id,
            eco_id=eco_id,
            approver_id=approver_id,
            approver_name=approver_name,
            approver_role=approver_role,
            decision=decision,
            comments=comments,
        )

    def implement_eco(self, eco_id: str, implementer: str, notes: str = None) -> ChangeOrder:
        """Implement an approved ECO."""
        model = self._session.query(ChangeOrderModel).filter(ChangeOrderModel.id == eco_id).first()
        if not model:
            raise ValueError(f"ECO not found: {eco_id}")
        if model.status != ECOStatus.APPROVED.value:
            raise ValueError(f"ECO cannot be implemented in status {model.status}")

        from datetime import date

        model.status = ECOStatus.IMPLEMENTED.value
        model.implemented_by = implementer
        model.implementation_date = date.today()
        model.implementation_notes = notes
        model.updated_at = datetime.now()
        self._session.flush()
        return self._model_to_eco(model)

    def get_pending_ecos(self, project_id: str = None) -> list[ChangeOrder]:
        """Get ECOs pending review/approval."""
        query = self._session.query(ChangeOrderModel).filter(
            ChangeOrderModel.status.in_([ECOStatus.SUBMITTED.value, ECOStatus.IN_REVIEW.value])
        )
        if project_id:
            query = query.filter(ChangeOrderModel.project_id == project_id)
        return [self._model_to_eco(m) for m in query.all()]

    # ========================================
    # Revision History
    # ========================================

    def get_revision_history(self, part_id: str) -> list[PartRevision]:
        """Get revision history for a part."""
        models = (
            self._session.query(PartRevisionModel)
            .filter(PartRevisionModel.part_id == part_id)
            .order_by(PartRevisionModel.created_at)
            .all()
        )
        return [
            PartRevision(
                id=m.id,
                part_id=m.part_id,
                revision=m.revision,
                change_summary=m.change_summary,
                change_order_id=m.change_order_id,
                status=PartStatus(m.status) if isinstance(m.status, str) else m.status,
                released_at=m.released_at,
            )
            for m in models
        ]

    # ========================================
    # Internal Helpers
    # ========================================

    @staticmethod
    def _model_to_part(model: PartModel) -> Part:
        """Convert ORM model to domain Part."""
        return Part(
            id=model.id,
            part_number=model.part_number,
            revision=model.revision,
            name=model.name,
            part_type=PartType(model.part_type) if isinstance(model.part_type, str) else model.part_type,
            status=PartStatus(model.status) if isinstance(model.status, str) else model.status,
            description=model.description,
            category=model.category,
            csi_code=model.csi_code,
            unit_of_measure=UnitOfMeasure(model.unit_of_measure) if isinstance(model.unit_of_measure, str) else model.unit_of_measure,
            unit_cost=model.unit_cost,
            manufacturer=model.manufacturer,
            manufacturer_pn=model.manufacturer_pn,
            lead_time_days=model.lead_time_days,
            released_by=model.released_by,
            released_at=model.released_at,
            attributes=model.attributes or {},
        )

    @staticmethod
    def _model_to_bom(model: BOMModel) -> BOM:
        """Convert ORM model to domain BOM."""
        items = [
            BOMItem(
                id=item.id,
                bom_id=item.bom_id,
                part_id=item.part_id,
                part_number=item.part_number,
                part_revision=item.part_revision,
                quantity=item.quantity,
                find_number=item.find_number,
                reference_designator=item.reference_designator,
                location=item.location,
                notes=item.notes,
                is_optional=item.is_optional,
                option_code=item.option_code,
            )
            for item in (model.items or [])
        ]
        return BOM(
            id=model.id,
            bom_number=model.bom_number,
            revision=model.revision,
            name=model.name,
            description=model.description,
            parent_part_id=model.parent_part_id,
            parent_part_revision=model.parent_part_revision,
            bom_type=BOMType(model.bom_type) if isinstance(model.bom_type, str) else model.bom_type,
            status=PartStatus(model.status) if isinstance(model.status, str) else model.status,
            items=items,
            created_at=model.created_at,
            project_id=model.project_id,
        )

    @staticmethod
    def _model_to_eco(model: ChangeOrderModel) -> ChangeOrder:
        """Convert ORM model to domain ChangeOrder."""
        changes = [
            Change(
                id=c.id,
                eco_id=c.eco_id,
                change_type=c.change_type,
                entity_type=c.entity_type,
                entity_id=c.entity_id,
                field_name=c.field_name,
                old_value=c.old_value,
                new_value=c.new_value,
                justification=c.justification,
            )
            for c in (model.changes or [])
        ]
        approvals = [
            Approval(
                id=a.id,
                eco_id=a.eco_id,
                approver_id=a.approver_id,
                approver_name=a.approver_name,
                approver_role=a.approver_role,
                decision=a.decision,
                comments=a.comments,
                decided_at=a.decided_at,
            )
            for a in (model.approvals or [])
        ]
        return ChangeOrder(
            id=model.id,
            eco_number=model.eco_number,
            title=model.title,
            description=model.description,
            reason=model.reason,
            urgency=model.urgency,
            project_id=model.project_id,
            status=ECOStatus(model.status) if isinstance(model.status, str) else model.status,
            submitted_by=model.submitted_by,
            submitted_at=model.submitted_at,
            changes=changes,
            approvals=approvals,
            affected_parts=model.affected_parts or [],
            affected_boms=model.affected_boms or [],
            affected_documents=model.affected_documents or [],
            implementation_date=model.implementation_date,
            implemented_by=model.implemented_by,
            implementation_notes=model.implementation_notes,
            created_at=model.created_at,
            updated_at=model.updated_at,
            closed_at=model.closed_at,
        )
