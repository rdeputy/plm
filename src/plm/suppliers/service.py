"""
Suppliers Service

Business logic for manufacturer and vendor management.
"""

from typing import Optional
from dataclasses import dataclass

from sqlalchemy.orm import Session

from plm.suppliers.repository import (
    ManufacturerRepository,
    VendorRepository,
    ApprovedManufacturerRepository,
    ApprovedVendorRepository,
)
from plm.db.models import (
    ManufacturerModel,
    SupplierVendorModel,
    ApprovedManufacturerModel,
    ApprovedVendorModel,
)


@dataclass
class SupplierStats:
    """Statistics for suppliers."""

    total_manufacturers: int
    approved_manufacturers: int
    total_vendors: int
    vendors_by_tier: dict[str, int]


class ManufacturerService:
    """Service for manufacturer management."""

    def __init__(self, session: Session):
        self.session = session
        self.manufacturers = ManufacturerRepository(session)
        self.aml = ApprovedManufacturerRepository(session)

    def create_manufacturer(
        self,
        manufacturer_code: str,
        name: str,
        country: Optional[str] = None,
        website: Optional[str] = None,
        notes: str = "",
    ) -> ManufacturerModel:
        """Create a new manufacturer."""
        return self.manufacturers.create(
            manufacturer_code=manufacturer_code,
            name=name,
            country=country,
            website=website,
            notes=notes,
            status="pending",
        )

    def get_manufacturer(self, manufacturer_id: str) -> Optional[ManufacturerModel]:
        """Get manufacturer by ID."""
        return self.manufacturers.get(manufacturer_id)

    def get_manufacturer_by_code(self, code: str) -> Optional[ManufacturerModel]:
        """Get manufacturer by code."""
        return self.manufacturers.find_by_code(code)

    def approve_manufacturer(
        self,
        manufacturer_id: str,
        approved_by: Optional[str] = None,
    ) -> Optional[ManufacturerModel]:
        """Approve a manufacturer."""
        return self.manufacturers.update(
            manufacturer_id,
            status="approved",
        )

    def add_to_aml(
        self,
        part_id: str,
        manufacturer_id: str,
        manufacturer_part_number: str,
        is_primary: bool = False,
        preference_rank: int = 1,
    ) -> ApprovedManufacturerModel:
        """Add manufacturer to part's AML."""
        if is_primary:
            self.aml.set_primary(part_id, "")

        return self.aml.create(
            part_id=part_id,
            manufacturer_id=manufacturer_id,
            manufacturer_part_number=manufacturer_part_number,
            is_primary=is_primary,
            preference_rank=preference_rank,
            status="approved",
        )

    def get_part_aml(self, part_id: str) -> list[ApprovedManufacturerModel]:
        """Get AML for a part."""
        return self.aml.list_for_part(part_id)

    def get_primary_manufacturer(
        self,
        part_id: str,
    ) -> Optional[ApprovedManufacturerModel]:
        """Get primary manufacturer for a part."""
        return self.aml.get_primary(part_id)

    def set_primary_manufacturer(self, part_id: str, aml_id: str) -> None:
        """Set primary manufacturer for a part."""
        self.aml.set_primary(part_id, aml_id)

    def commit(self):
        """Commit transaction."""
        self.session.commit()


class VendorService:
    """Service for vendor management."""

    def __init__(self, session: Session):
        self.session = session
        self.vendors = VendorRepository(session)
        self.avl = ApprovedVendorRepository(session)

    def create_vendor(
        self,
        vendor_code: str,
        name: str,
        tier: str = "approved",
        country: Optional[str] = None,
        website: Optional[str] = None,
        notes: str = "",
    ) -> SupplierVendorModel:
        """Create a new vendor."""
        return self.vendors.create(
            vendor_code=vendor_code,
            name=name,
            tier=tier,
            country=country,
            website=website,
            notes=notes,
            status="pending",
        )

    def get_vendor(self, vendor_id: str) -> Optional[SupplierVendorModel]:
        """Get vendor by ID."""
        return self.vendors.get(vendor_id)

    def get_vendor_by_code(self, code: str) -> Optional[SupplierVendorModel]:
        """Get vendor by code."""
        return self.vendors.find_by_code(code)

    def approve_vendor(
        self,
        vendor_id: str,
    ) -> Optional[SupplierVendorModel]:
        """Approve a vendor."""
        return self.vendors.update(vendor_id, status="approved")

    def add_to_avl(
        self,
        part_id: str,
        vendor_id: str,
        unit_price: Optional[float] = None,
        lead_time_days: Optional[int] = None,
        min_order_qty: int = 1,
        is_primary: bool = False,
        preference_rank: int = 1,
    ) -> ApprovedVendorModel:
        """Add vendor to part's AVL."""
        return self.avl.create(
            part_id=part_id,
            vendor_id=vendor_id,
            unit_price=unit_price,
            lead_time_days=lead_time_days,
            min_order_qty=min_order_qty,
            is_primary=is_primary,
            preference_rank=preference_rank,
            status="approved",
        )

    def get_part_avl(self, part_id: str) -> list[ApprovedVendorModel]:
        """Get AVL for a part."""
        return self.avl.list_for_part(part_id)

    def get_primary_vendor(self, part_id: str) -> Optional[ApprovedVendorModel]:
        """Get primary vendor for a part."""
        return self.avl.get_primary(part_id)

    def get_lowest_cost_vendor(self, part_id: str) -> Optional[ApprovedVendorModel]:
        """Get lowest cost vendor for a part."""
        return self.avl.get_lowest_cost(part_id)

    def commit(self):
        """Commit transaction."""
        self.session.commit()


class SupplierService:
    """Combined service for suppliers (manufacturers and vendors)."""

    def __init__(self, session: Session):
        self.session = session
        self.manufacturer_service = ManufacturerService(session)
        self.vendor_service = VendorService(session)

    def get_stats(self) -> SupplierStats:
        """Get supplier statistics."""
        manufacturers = self.manufacturer_service.manufacturers
        vendors = self.vendor_service.vendors

        all_manufacturers = manufacturers.list(limit=10000)
        approved_manufacturers = manufacturers.list_approved()
        all_vendors = vendors.list(limit=10000)

        vendors_by_tier: dict[str, int] = {}
        for v in all_vendors:
            tier = v.tier or "unclassified"
            vendors_by_tier[tier] = vendors_by_tier.get(tier, 0) + 1

        return SupplierStats(
            total_manufacturers=len(all_manufacturers),
            approved_manufacturers=len(approved_manufacturers),
            total_vendors=len(all_vendors),
            vendors_by_tier=vendors_by_tier,
        )

    def commit(self):
        """Commit transaction."""
        self.session.commit()
