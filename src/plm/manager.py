"""
PLM Manager

Central service for Product Lifecycle Management.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
import uuid

from .parts import Part, PartRevision, PartStatus, PartType, UnitOfMeasure, increment_revision
from .boms import BOM, BOMItem, BOMType, BOMComparison, Effectivity, ExplodedBOMItem
from .changes import ChangeOrder, Change, Approval, ImpactAnalysis, ECOStatus


class PLMManager:
    """
    Central PLM service for design data management.

    Provides:
    - Part management (CRUD, revisions, lifecycle)
    - BOM management (create, explode, compare)
    - Change management (ECOs, approvals, implementation)
    - MRP interface
    """

    def __init__(self):
        # In-memory storage (would be database in production)
        self._parts: dict[str, Part] = {}
        self._part_revisions: dict[str, list[PartRevision]] = {}
        self._boms: dict[str, BOM] = {}
        self._ecos: dict[str, ChangeOrder] = {}

    # ========================================
    # Part Management
    # ========================================

    def create_part(
        self,
        part_number: str,
        name: str,
        part_type: PartType = PartType.COMPONENT,
        **kwargs
    ) -> Part:
        """Create a new part."""
        part_id = str(uuid.uuid4())
        part = Part(
            id=part_id,
            part_number=part_number,
            revision="A",
            name=name,
            part_type=part_type,
            status=PartStatus.DRAFT,
            **kwargs
        )
        self._parts[part_id] = part
        return part

    def get_part(self, part_id: str, revision: str = None) -> Optional[Part]:
        """Get a part by ID, optionally at specific revision."""
        part = self._parts.get(part_id)
        if part and revision and part.revision != revision:
            # Would look up historical revision in production
            return None
        return part

    def get_part_by_number(self, part_number: str, revision: str = None) -> Optional[Part]:
        """Get a part by part number."""
        for part in self._parts.values():
            if part.part_number == part_number:
                if revision is None or part.revision == revision:
                    return part
        return None

    def revise_part(self, part_id: str, change_summary: str, eco_id: str = None) -> Part:
        """Create a new revision of a part."""
        part = self._parts.get(part_id)
        if not part:
            raise ValueError(f"Part not found: {part_id}")
        if not part.can_revise():
            raise ValueError(f"Part cannot be revised in status {part.status}")

        # Create revision record
        revision = PartRevision(
            id=str(uuid.uuid4()),
            part_id=part_id,
            revision=part.revision,
            change_summary=change_summary,
            change_order_id=eco_id,
            status=PartStatus.RELEASED,
            released_at=datetime.now(),
        )
        if part_id not in self._part_revisions:
            self._part_revisions[part_id] = []
        self._part_revisions[part_id].append(revision)

        # Create new revision
        new_revision = increment_revision(part.revision)
        part.revision = new_revision
        part.status = PartStatus.DRAFT

        return part

    def release_part(self, part_id: str, approver: str) -> Part:
        """Release a part for use."""
        part = self._parts.get(part_id)
        if not part:
            raise ValueError(f"Part not found: {part_id}")
        if not part.can_release():
            raise ValueError(f"Part cannot be released in status {part.status}")

        part.status = PartStatus.RELEASED
        part.released_by = approver
        part.released_at = datetime.now()
        return part

    def obsolete_part(self, part_id: str, reason: str, replaced_by: str = None) -> Part:
        """Obsolete a part."""
        part = self._parts.get(part_id)
        if not part:
            raise ValueError(f"Part not found: {part_id}")

        part.status = PartStatus.OBSOLETE
        part.obsoleted_at = datetime.now()
        part.attributes["obsolete_reason"] = reason
        if replaced_by:
            part.attributes["replaced_by"] = replaced_by
        return part

    def search_parts(self, query: str, filters: dict = None) -> list[Part]:
        """Search parts by query string."""
        results = []
        query_lower = query.lower()
        for part in self._parts.values():
            if (query_lower in part.part_number.lower() or
                query_lower in part.name.lower() or
                (part.description and query_lower in part.description.lower())):
                results.append(part)

        if filters:
            if "status" in filters:
                results = [p for p in results if p.status.value == filters["status"]]
            if "part_type" in filters:
                results = [p for p in results if p.part_type.value == filters["part_type"]]

        return results

    # ========================================
    # BOM Management
    # ========================================

    def create_bom(
        self,
        bom_number: str,
        name: str,
        parent_part_id: str,
        bom_type: BOMType = BOMType.ENGINEERING,
        **kwargs
    ) -> BOM:
        """Create a new BOM."""
        bom_id = str(uuid.uuid4())
        parent_part = self._parts.get(parent_part_id)

        bom = BOM(
            id=bom_id,
            bom_number=bom_number,
            revision="A",
            name=name,
            parent_part_id=parent_part_id,
            parent_part_revision=parent_part.revision if parent_part else "A",
            bom_type=bom_type,
            **kwargs
        )
        self._boms[bom_id] = bom
        return bom

    def get_bom(self, bom_id: str, revision: str = None) -> Optional[BOM]:
        """Get a BOM by ID."""
        return self._boms.get(bom_id)

    def add_bom_item(
        self,
        bom_id: str,
        part_id: str,
        quantity: Decimal,
        **kwargs
    ) -> BOMItem:
        """Add an item to a BOM."""
        bom = self._boms.get(bom_id)
        if not bom:
            raise ValueError(f"BOM not found: {bom_id}")

        part = self._parts.get(part_id)
        if not part:
            raise ValueError(f"Part not found: {part_id}")

        item = BOMItem(
            id=str(uuid.uuid4()),
            bom_id=bom_id,
            part_id=part_id,
            part_number=part.part_number,
            part_revision=part.revision,
            quantity=quantity,
            unit_of_measure=part.unit_of_measure,
            **kwargs
        )
        bom.add_item(item)
        return item

    def remove_bom_item(self, bom_id: str, item_id: str) -> bool:
        """Remove an item from a BOM."""
        bom = self._boms.get(bom_id)
        if not bom:
            return False
        return bom.remove_item(item_id)

    def explode_bom(self, bom_id: str, levels: int = -1) -> list[ExplodedBOMItem]:
        """
        Explode a BOM to show all components.

        Args:
            bom_id: BOM to explode
            levels: Number of levels to explode (-1 = all)

        Returns:
            Flattened list of all components
        """
        bom = self._boms.get(bom_id)
        if not bom:
            return []

        result = []
        self._explode_recursive(bom, result, level=0, max_levels=levels, parent_qty=Decimal("1"), path="")
        return result

    def _explode_recursive(
        self,
        bom: BOM,
        result: list[ExplodedBOMItem],
        level: int,
        max_levels: int,
        parent_qty: Decimal,
        path: str,
    ) -> None:
        """Recursively explode BOM."""
        if max_levels >= 0 and level > max_levels:
            return

        for item in bom.items:
            part = self._parts.get(item.part_id)
            if not part:
                continue

            extended_qty = item.quantity * parent_qty
            item_path = f"{path}/{part.part_number}" if path else part.part_number

            # Check if this part has its own BOM
            child_bom = self._find_bom_for_part(item.part_id)
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

            # Recurse into child BOM
            if child_bom and (max_levels < 0 or level < max_levels):
                self._explode_recursive(
                    child_bom, result, level + 1, max_levels,
                    extended_qty, item_path
                )

    def _find_bom_for_part(self, part_id: str) -> Optional[BOM]:
        """Find the BOM that defines a part."""
        for bom in self._boms.values():
            if bom.parent_part_id == part_id:
                return bom
        return None

    def compare_boms(self, bom_id: str, rev_a: str, rev_b: str) -> BOMComparison:
        """Compare two revisions of a BOM."""
        # In production, would look up historical revisions
        # For now, return empty comparison
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

                part = self._parts.get(item.part_id)
                if part and part.category:
                    by_category[part.category] = by_category.get(part.category, Decimal("0")) + item.extended_cost

        return {
            "total_material_cost": float(total_material),
            "by_category": {k: float(v) for k, v in by_category.items()},
            "item_count": len(exploded),
        }

    def where_used(self, part_id: str) -> list[BOM]:
        """Find all BOMs that use a part."""
        result = []
        for bom in self._boms.values():
            for item in bom.items:
                if item.part_id == part_id:
                    result.append(bom)
                    break
        return result

    # ========================================
    # Change Management
    # ========================================

    def create_eco(
        self,
        title: str,
        description: str = "",
        project_id: str = None,
        **kwargs
    ) -> ChangeOrder:
        """Create a new Engineering Change Order."""
        eco_id = str(uuid.uuid4())

        # Generate ECO number
        eco_count = len(self._ecos) + 1
        eco_number = f"ECO-{datetime.now().year}-{eco_count:04d}"

        eco = ChangeOrder(
            id=eco_id,
            eco_number=eco_number,
            title=title,
            description=description,
            project_id=project_id,
            **kwargs
        )
        self._ecos[eco_id] = eco
        return eco

    def get_eco(self, eco_id: str) -> Optional[ChangeOrder]:
        """Get an ECO by ID."""
        return self._ecos.get(eco_id)

    def submit_eco(self, eco_id: str, submitter: str) -> ChangeOrder:
        """Submit an ECO for review."""
        eco = self._ecos.get(eco_id)
        if not eco:
            raise ValueError(f"ECO not found: {eco_id}")
        eco.submit(submitter)
        return eco

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
        eco = self._ecos.get(eco_id)
        if not eco:
            raise ValueError(f"ECO not found: {eco_id}")

        approval = Approval(
            id=str(uuid.uuid4()),
            eco_id=eco_id,
            approver_id=approver_id,
            approver_name=approver_name,
            approver_role=approver_role,
            decision=decision,
            comments=comments,
        )
        eco.add_approval(approval)
        return approval

    def implement_eco(self, eco_id: str, implementer: str, notes: str = None) -> ChangeOrder:
        """Implement an approved ECO."""
        eco = self._ecos.get(eco_id)
        if not eco:
            raise ValueError(f"ECO not found: {eco_id}")
        eco.implement(implementer, notes)
        return eco

    def get_pending_ecos(self, project_id: str = None) -> list[ChangeOrder]:
        """Get ECOs pending review/approval."""
        result = []
        for eco in self._ecos.values():
            if eco.status in [ECOStatus.SUBMITTED, ECOStatus.IN_REVIEW]:
                if project_id is None or eco.project_id == project_id:
                    result.append(eco)
        return result

    # ========================================
    # Revision History
    # ========================================

    def get_revision_history(self, part_id: str) -> list[PartRevision]:
        """Get revision history for a part."""
        return self._part_revisions.get(part_id, [])
