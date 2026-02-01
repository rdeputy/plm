"""
Procurement Repository

Data access layer for procurement operations.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import uuid4

from sqlalchemy import func
from sqlalchemy.orm import Session

from plm.db.models import (
    VendorModel,
    PriceAgreementModel,
    PurchaseOrderModel,
    POItemModel,
    ReceiptModel,
    ReceiptItemModel,
)
from .models import (
    Vendor,
    VendorContact,
    PurchaseOrder,
    POItem,
    POStatus,
    PriceAgreement,
    Receipt,
    ReceiptItem,
)


class ProcurementRepository:
    """Repository for procurement data access."""

    def __init__(self, session: Session):
        self.session = session

    # -------------------------------------------------------------------------
    # Vendor Operations
    # -------------------------------------------------------------------------

    def create_vendor(self, vendor: Vendor) -> Vendor:
        """Create a new vendor."""
        model = VendorModel(
            id=vendor.id or str(uuid4()),
            name=vendor.name,
            vendor_code=vendor.vendor_code,
            address=vendor.address,
            city=vendor.city,
            state=vendor.state,
            postal_code=vendor.postal_code,
            country=vendor.country,
            phone=vendor.phone,
            email=vendor.email,
            website=vendor.website,
            contacts=[c.__dict__ for c in vendor.contacts] if vendor.contacts else [],
            payment_terms=vendor.payment_terms,
            freight_terms=vendor.freight_terms,
            minimum_order=vendor.minimum_order,
            categories=vendor.categories,
            on_time_rate=vendor.on_time_rate,
            quality_rate=vendor.quality_rate,
            avg_lead_time_days=vendor.avg_lead_time_days,
            is_approved=vendor.is_approved,
            insurance_expiry=vendor.insurance_expiry,
            w9_on_file=vendor.w9_on_file,
            certifications=vendor.certifications,
            is_active=vendor.is_active,
            notes=vendor.notes,
        )
        self.session.add(model)
        self.session.flush()
        vendor.id = model.id
        return vendor

    def get_vendor(self, vendor_id: str) -> Optional[Vendor]:
        """Get a vendor by ID."""
        model = self.session.query(VendorModel).filter_by(id=vendor_id).first()
        if not model:
            return None
        return self._model_to_vendor(model)

    def get_vendor_by_code(self, vendor_code: str) -> Optional[Vendor]:
        """Get a vendor by code."""
        model = self.session.query(VendorModel).filter_by(vendor_code=vendor_code).first()
        if not model:
            return None
        return self._model_to_vendor(model)

    def list_vendors(
        self,
        is_active: Optional[bool] = None,
        is_approved: Optional[bool] = None,
        category: Optional[str] = None,
    ) -> list[Vendor]:
        """List vendors with optional filters."""
        query = self.session.query(VendorModel)
        if is_active is not None:
            query = query.filter_by(is_active=is_active)
        if is_approved is not None:
            query = query.filter_by(is_approved=is_approved)
        if category:
            query = query.filter(VendorModel.categories.contains([category]))
        return [self._model_to_vendor(m) for m in query.all()]

    def update_vendor(self, vendor: Vendor) -> Vendor:
        """Update a vendor."""
        model = self.session.query(VendorModel).filter_by(id=vendor.id).first()
        if model:
            model.name = vendor.name
            model.vendor_code = vendor.vendor_code
            model.address = vendor.address
            model.city = vendor.city
            model.state = vendor.state
            model.postal_code = vendor.postal_code
            model.country = vendor.country
            model.phone = vendor.phone
            model.email = vendor.email
            model.website = vendor.website
            model.contacts = [c.__dict__ for c in vendor.contacts] if vendor.contacts else []
            model.payment_terms = vendor.payment_terms
            model.freight_terms = vendor.freight_terms
            model.minimum_order = vendor.minimum_order
            model.categories = vendor.categories
            model.on_time_rate = vendor.on_time_rate
            model.quality_rate = vendor.quality_rate
            model.avg_lead_time_days = vendor.avg_lead_time_days
            model.is_approved = vendor.is_approved
            model.insurance_expiry = vendor.insurance_expiry
            model.w9_on_file = vendor.w9_on_file
            model.certifications = vendor.certifications
            model.is_active = vendor.is_active
            model.notes = vendor.notes
            self.session.flush()
        return vendor

    def _model_to_vendor(self, model: VendorModel) -> Vendor:
        """Convert DB model to domain model."""
        contacts = []
        if model.contacts:
            for c in model.contacts:
                contacts.append(
                    VendorContact(
                        name=c.get("name", ""),
                        title=c.get("title"),
                        email=c.get("email"),
                        phone=c.get("phone"),
                        is_primary=c.get("is_primary", False),
                    )
                )
        return Vendor(
            id=model.id,
            name=model.name,
            vendor_code=model.vendor_code,
            address=model.address,
            city=model.city,
            state=model.state,
            postal_code=model.postal_code,
            country=model.country,
            phone=model.phone,
            email=model.email,
            website=model.website,
            contacts=contacts,
            payment_terms=model.payment_terms,
            freight_terms=model.freight_terms,
            minimum_order=model.minimum_order or Decimal("0"),
            categories=model.categories or [],
            on_time_rate=model.on_time_rate or 0.0,
            quality_rate=model.quality_rate or 0.0,
            avg_lead_time_days=model.avg_lead_time_days or 0,
            is_approved=model.is_approved,
            insurance_expiry=model.insurance_expiry,
            w9_on_file=model.w9_on_file,
            certifications=model.certifications or [],
            is_active=model.is_active,
            notes=model.notes,
        )

    # -------------------------------------------------------------------------
    # Price Agreement Operations
    # -------------------------------------------------------------------------

    def create_price_agreement(self, agreement: PriceAgreement) -> PriceAgreement:
        """Create a new price agreement."""
        model = PriceAgreementModel(
            id=agreement.id or str(uuid4()),
            vendor_id=agreement.vendor_id,
            part_id=agreement.part_id,
            part_number=agreement.part_number,
            unit_price=agreement.unit_price,
            currency=agreement.currency,
            effective_date=agreement.effective_date,
            expiration_date=agreement.expiration_date,
            min_quantity=agreement.min_quantity,
            price_breaks=agreement.price_breaks,
            contract_number=agreement.contract_number,
            notes=agreement.notes,
        )
        self.session.add(model)
        self.session.flush()
        agreement.id = model.id
        return agreement

    def get_price_agreement(self, agreement_id: str) -> Optional[PriceAgreement]:
        """Get a price agreement by ID."""
        model = self.session.query(PriceAgreementModel).filter_by(id=agreement_id).first()
        if not model:
            return None
        return self._model_to_price_agreement(model)

    def get_current_price(
        self, vendor_id: str, part_id: str, as_of: Optional[date] = None
    ) -> Optional[PriceAgreement]:
        """Get current active price agreement for vendor/part."""
        as_of = as_of or date.today()
        model = (
            self.session.query(PriceAgreementModel)
            .filter_by(vendor_id=vendor_id, part_id=part_id)
            .filter(PriceAgreementModel.effective_date <= as_of)
            .filter(
                (PriceAgreementModel.expiration_date.is_(None))
                | (PriceAgreementModel.expiration_date >= as_of)
            )
            .order_by(PriceAgreementModel.effective_date.desc())
            .first()
        )
        if not model:
            return None
        return self._model_to_price_agreement(model)

    def list_price_agreements(
        self,
        vendor_id: Optional[str] = None,
        part_id: Optional[str] = None,
        active_only: bool = True,
    ) -> list[PriceAgreement]:
        """List price agreements with filters."""
        query = self.session.query(PriceAgreementModel)
        if vendor_id:
            query = query.filter_by(vendor_id=vendor_id)
        if part_id:
            query = query.filter_by(part_id=part_id)
        if active_only:
            today = date.today()
            query = query.filter(PriceAgreementModel.effective_date <= today).filter(
                (PriceAgreementModel.expiration_date.is_(None))
                | (PriceAgreementModel.expiration_date >= today)
            )
        return [self._model_to_price_agreement(m) for m in query.all()]

    def _model_to_price_agreement(self, model: PriceAgreementModel) -> PriceAgreement:
        """Convert DB model to domain model."""
        return PriceAgreement(
            id=model.id,
            vendor_id=model.vendor_id,
            part_id=model.part_id,
            part_number=model.part_number,
            unit_price=model.unit_price,
            currency=model.currency,
            effective_date=model.effective_date,
            expiration_date=model.expiration_date,
            min_quantity=model.min_quantity or Decimal("1"),
            price_breaks=model.price_breaks or {},
            contract_number=model.contract_number,
            notes=model.notes,
        )

    # -------------------------------------------------------------------------
    # Purchase Order Operations
    # -------------------------------------------------------------------------

    def create_purchase_order(self, po: PurchaseOrder) -> PurchaseOrder:
        """Create a new purchase order."""
        model = PurchaseOrderModel(
            id=po.id or str(uuid4()),
            po_number=po.po_number,
            vendor_id=po.vendor_id,
            vendor_name=po.vendor_name,
            status=po.status.value,
            subtotal=po.subtotal,
            tax=po.tax,
            shipping=po.shipping,
            total=po.total,
            order_date=po.order_date,
            required_date=po.required_date,
            promised_date=po.promised_date,
            ship_to_location_id=po.ship_to_location_id,
            ship_to_address=po.ship_to_address,
            freight_terms=po.freight_terms,
            payment_terms=po.payment_terms,
            project_id=po.project_id,
            requisition_id=po.requisition_id,
            notes=po.notes,
            created_by=po.created_by,
            approved_by=po.approved_by,
            approved_at=po.approved_at,
            created_at=po.created_at,
            updated_at=po.updated_at,
        )
        self.session.add(model)
        self.session.flush()
        po.id = model.id

        # Add items
        for item in po.items:
            self._create_po_item(po.id, item)

        return po

    def _create_po_item(self, po_id: str, item: POItem) -> POItem:
        """Create a PO line item."""
        model = POItemModel(
            id=item.id or str(uuid4()),
            po_id=po_id,
            line_number=item.line_number,
            part_id=item.part_id,
            part_number=item.part_number,
            description=item.description,
            quantity=item.quantity,
            unit_of_measure=item.unit_of_measure,
            received_quantity=item.received_quantity,
            unit_price=item.unit_price,
            extended_price=item.extended_price,
            required_date=item.required_date,
            promised_date=item.promised_date,
            project_id=item.project_id,
            planned_order_id=item.planned_order_id,
            is_closed=item.is_closed,
        )
        self.session.add(model)
        self.session.flush()
        item.id = model.id
        return item

    def get_purchase_order(self, po_id: str) -> Optional[PurchaseOrder]:
        """Get a purchase order by ID."""
        model = self.session.query(PurchaseOrderModel).filter_by(id=po_id).first()
        if not model:
            return None
        return self._model_to_purchase_order(model)

    def get_purchase_order_by_number(self, po_number: str) -> Optional[PurchaseOrder]:
        """Get a purchase order by PO number."""
        model = self.session.query(PurchaseOrderModel).filter_by(po_number=po_number).first()
        if not model:
            return None
        return self._model_to_purchase_order(model)

    def list_purchase_orders(
        self,
        vendor_id: Optional[str] = None,
        status: Optional[POStatus] = None,
        project_id: Optional[str] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> list[PurchaseOrder]:
        """List purchase orders with filters."""
        query = self.session.query(PurchaseOrderModel)
        if vendor_id:
            query = query.filter_by(vendor_id=vendor_id)
        if status:
            query = query.filter_by(status=status.value)
        if project_id:
            query = query.filter_by(project_id=project_id)
        if from_date:
            query = query.filter(PurchaseOrderModel.order_date >= from_date)
        if to_date:
            query = query.filter(PurchaseOrderModel.order_date <= to_date)
        query = query.order_by(PurchaseOrderModel.created_at.desc())
        return [self._model_to_purchase_order(m) for m in query.all()]

    def update_purchase_order(self, po: PurchaseOrder) -> PurchaseOrder:
        """Update a purchase order."""
        model = self.session.query(PurchaseOrderModel).filter_by(id=po.id).first()
        if model:
            model.status = po.status.value
            model.subtotal = po.subtotal
            model.tax = po.tax
            model.shipping = po.shipping
            model.total = po.total
            model.order_date = po.order_date
            model.required_date = po.required_date
            model.promised_date = po.promised_date
            model.ship_to_location_id = po.ship_to_location_id
            model.ship_to_address = po.ship_to_address
            model.freight_terms = po.freight_terms
            model.payment_terms = po.payment_terms
            model.notes = po.notes
            model.approved_by = po.approved_by
            model.approved_at = po.approved_at
            model.updated_at = datetime.now()
            self.session.flush()
        return po

    def update_po_item(self, item: POItem) -> POItem:
        """Update a PO line item."""
        model = self.session.query(POItemModel).filter_by(id=item.id).first()
        if model:
            model.quantity = item.quantity
            model.received_quantity = item.received_quantity
            model.unit_price = item.unit_price
            model.extended_price = item.extended_price
            model.required_date = item.required_date
            model.promised_date = item.promised_date
            model.is_closed = item.is_closed
            self.session.flush()
        return item

    def get_next_po_number(self) -> str:
        """Generate next PO number."""
        today = date.today()
        prefix = f"PO-{today.year}{today.month:02d}"
        result = (
            self.session.query(func.count(PurchaseOrderModel.id))
            .filter(PurchaseOrderModel.po_number.like(f"{prefix}%"))
            .scalar()
        )
        sequence = (result or 0) + 1
        return f"{prefix}-{sequence:04d}"

    def _model_to_purchase_order(self, model: PurchaseOrderModel) -> PurchaseOrder:
        """Convert DB model to domain model."""
        # Get items
        item_models = self.session.query(POItemModel).filter_by(po_id=model.id).all()
        items = [self._model_to_po_item(im) for im in item_models]

        return PurchaseOrder(
            id=model.id,
            po_number=model.po_number,
            vendor_id=model.vendor_id,
            vendor_name=model.vendor_name,
            status=POStatus(model.status),
            items=items,
            subtotal=model.subtotal,
            tax=model.tax,
            shipping=model.shipping,
            total=model.total,
            order_date=model.order_date,
            required_date=model.required_date,
            promised_date=model.promised_date,
            ship_to_location_id=model.ship_to_location_id,
            ship_to_address=model.ship_to_address,
            freight_terms=model.freight_terms,
            payment_terms=model.payment_terms,
            project_id=model.project_id,
            requisition_id=model.requisition_id,
            notes=model.notes,
            created_by=model.created_by,
            approved_by=model.approved_by,
            approved_at=model.approved_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _model_to_po_item(self, model: POItemModel) -> POItem:
        """Convert DB model to domain model."""
        return POItem(
            id=model.id,
            po_id=model.po_id,
            line_number=model.line_number,
            part_id=model.part_id,
            part_number=model.part_number,
            description=model.description,
            quantity=model.quantity,
            unit_of_measure=model.unit_of_measure,
            received_quantity=model.received_quantity,
            unit_price=model.unit_price,
            extended_price=model.extended_price,
            required_date=model.required_date,
            promised_date=model.promised_date,
            project_id=model.project_id,
            planned_order_id=model.planned_order_id,
            is_closed=model.is_closed,
        )

    # -------------------------------------------------------------------------
    # Receipt Operations
    # -------------------------------------------------------------------------

    def create_receipt(self, receipt: Receipt) -> Receipt:
        """Create a new receipt."""
        model = ReceiptModel(
            id=receipt.id or str(uuid4()),
            receipt_number=receipt.receipt_number,
            po_id=receipt.po_id,
            po_number=receipt.po_number,
            vendor_id=receipt.vendor_id,
            receipt_date=receipt.receipt_date,
            created_at=receipt.created_at,
            packing_slip=receipt.packing_slip,
            carrier=receipt.carrier,
            tracking_number=receipt.tracking_number,
            received_by=receipt.received_by,
            location_id=receipt.location_id,
            is_complete=receipt.is_complete,
            notes=receipt.notes,
        )
        self.session.add(model)
        self.session.flush()
        receipt.id = model.id

        # Add items
        for item in receipt.items:
            self._create_receipt_item(receipt.id, item)

        return receipt

    def _create_receipt_item(self, receipt_id: str, item: ReceiptItem) -> ReceiptItem:
        """Create a receipt line item."""
        model = ReceiptItemModel(
            id=item.id or str(uuid4()),
            receipt_id=receipt_id,
            po_item_id=item.po_item_id,
            part_id=item.part_id,
            part_number=item.part_number,
            quantity_received=item.quantity_received,
            quantity_accepted=item.quantity_accepted,
            quantity_rejected=item.quantity_rejected,
            unit_of_measure=item.unit_of_measure,
            lot_number=item.lot_number,
            serial_numbers=item.serial_numbers,
            location_id=item.location_id,
            inspection_required=item.inspection_required,
            inspection_status=item.inspection_status,
            inspection_notes=item.inspection_notes,
        )
        self.session.add(model)
        self.session.flush()
        item.id = model.id
        return item

    def get_receipt(self, receipt_id: str) -> Optional[Receipt]:
        """Get a receipt by ID."""
        model = self.session.query(ReceiptModel).filter_by(id=receipt_id).first()
        if not model:
            return None
        return self._model_to_receipt(model)

    def list_receipts(
        self,
        po_id: Optional[str] = None,
        vendor_id: Optional[str] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> list[Receipt]:
        """List receipts with filters."""
        query = self.session.query(ReceiptModel)
        if po_id:
            query = query.filter_by(po_id=po_id)
        if vendor_id:
            query = query.filter_by(vendor_id=vendor_id)
        if from_date:
            query = query.filter(ReceiptModel.receipt_date >= from_date)
        if to_date:
            query = query.filter(ReceiptModel.receipt_date <= to_date)
        query = query.order_by(ReceiptModel.receipt_date.desc())
        return [self._model_to_receipt(m) for m in query.all()]

    def get_next_receipt_number(self) -> str:
        """Generate next receipt number."""
        today = date.today()
        prefix = f"RCV-{today.year}{today.month:02d}"
        result = (
            self.session.query(func.count(ReceiptModel.id))
            .filter(ReceiptModel.receipt_number.like(f"{prefix}%"))
            .scalar()
        )
        sequence = (result or 0) + 1
        return f"{prefix}-{sequence:04d}"

    def _model_to_receipt(self, model: ReceiptModel) -> Receipt:
        """Convert DB model to domain model."""
        item_models = self.session.query(ReceiptItemModel).filter_by(receipt_id=model.id).all()
        items = [self._model_to_receipt_item(im) for im in item_models]

        return Receipt(
            id=model.id,
            receipt_number=model.receipt_number,
            po_id=model.po_id,
            po_number=model.po_number,
            vendor_id=model.vendor_id,
            items=items,
            receipt_date=model.receipt_date,
            created_at=model.created_at,
            packing_slip=model.packing_slip,
            carrier=model.carrier,
            tracking_number=model.tracking_number,
            received_by=model.received_by,
            location_id=model.location_id,
            is_complete=model.is_complete,
            notes=model.notes,
        )

    def _model_to_receipt_item(self, model: ReceiptItemModel) -> ReceiptItem:
        """Convert DB model to domain model."""
        return ReceiptItem(
            id=model.id,
            receipt_id=model.receipt_id,
            po_item_id=model.po_item_id,
            part_id=model.part_id,
            part_number=model.part_number,
            quantity_received=model.quantity_received,
            quantity_accepted=model.quantity_accepted,
            quantity_rejected=model.quantity_rejected,
            unit_of_measure=model.unit_of_measure,
            lot_number=model.lot_number,
            serial_numbers=model.serial_numbers or [],
            location_id=model.location_id,
            inspection_required=model.inspection_required,
            inspection_status=model.inspection_status,
            inspection_notes=model.inspection_notes,
        )
