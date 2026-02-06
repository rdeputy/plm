"""
Suppliers Repository

Database operations for manufacturers, vendors, AML/AVL.
"""

from typing import Optional

from sqlalchemy.orm import Session

from plm.db.repository import BaseRepository
from plm.db.models import (
    ManufacturerModel,
    SupplierVendorModel,
    ApprovedManufacturerModel,
    ApprovedVendorModel,
)


class ManufacturerRepository(BaseRepository[ManufacturerModel]):
    """Repository for manufacturers."""

    def __init__(self, session: Session):
        super().__init__(session, ManufacturerModel)

    def find_by_code(self, code: str) -> Optional[ManufacturerModel]:
        """Find manufacturer by code."""
        return self.get_by(manufacturer_code=code)

    def list_approved(self) -> list[ManufacturerModel]:
        """List approved manufacturers."""
        return self.list(status="approved", order_by="name")

    def search_manufacturers(
        self,
        search: str,
        status: Optional[str] = None,
        country: Optional[str] = None,
    ) -> list[ManufacturerModel]:
        """Search manufacturers."""
        return self.search(
            search,
            ["manufacturer_code", "name"],
            status=status,
            country=country,
        )


class VendorRepository(BaseRepository[SupplierVendorModel]):
    """Repository for vendors."""

    def __init__(self, session: Session):
        super().__init__(session, SupplierVendorModel)

    def find_by_code(self, code: str) -> Optional[SupplierVendorModel]:
        """Find vendor by code."""
        return self.get_by(vendor_code=code)

    def list_by_tier(self, tier: str) -> list[SupplierVendorModel]:
        """List vendors by tier."""
        return self.list(tier=tier, order_by="name")

    def search_vendors(
        self,
        search: str,
        status: Optional[str] = None,
        tier: Optional[str] = None,
    ) -> list[SupplierVendorModel]:
        """Search vendors."""
        return self.search(
            search,
            ["vendor_code", "name"],
            status=status,
            tier=tier,
        )


class ApprovedManufacturerRepository(BaseRepository[ApprovedManufacturerModel]):
    """Repository for AML entries."""

    def __init__(self, session: Session):
        super().__init__(session, ApprovedManufacturerModel)

    def list_for_part(self, part_id: str) -> list[ApprovedManufacturerModel]:
        """Get AML for a part."""
        return self.list(part_id=part_id, order_by="preference_rank")

    def get_primary(self, part_id: str) -> Optional[ApprovedManufacturerModel]:
        """Get primary manufacturer for a part."""
        return self.get_by(part_id=part_id, is_primary=True)

    def set_primary(self, part_id: str, aml_id: str) -> None:
        """Set primary manufacturer for a part."""
        # Clear existing primary
        for entry in self.list_for_part(part_id):
            if entry.is_primary:
                entry.is_primary = False

        # Set new primary
        self.update(aml_id, is_primary=True)


class ApprovedVendorRepository(BaseRepository[ApprovedVendorModel]):
    """Repository for AVL entries."""

    def __init__(self, session: Session):
        super().__init__(session, ApprovedVendorModel)

    def list_for_part(self, part_id: str) -> list[ApprovedVendorModel]:
        """Get AVL for a part."""
        return self.list(part_id=part_id, order_by="preference_rank")

    def get_primary(self, part_id: str) -> Optional[ApprovedVendorModel]:
        """Get primary vendor for a part."""
        return self.get_by(part_id=part_id, is_primary=True)

    def get_lowest_cost(self, part_id: str) -> Optional[ApprovedVendorModel]:
        """Get lowest cost vendor for a part."""
        vendors = self.list_for_part(part_id)
        if not vendors:
            return None
        return min(vendors, key=lambda v: v.unit_price or 0)
