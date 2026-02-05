"""
Warranty Service

Business logic for warranty registration, claims, and RMAs.
"""

import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional

from .models import (
    WarrantyRegistration,
    WarrantyClaim,
    RMA,
    WarrantyPolicy,
    WarrantyMetrics,
    WarrantyStatus,
    WarrantyType,
    ClaimStatus,
    ClaimType,
    RMAStatus,
    DispositionAction,
    FailureCategory,
)


class WarrantyService:
    """
    Manages warranty registrations, claims, and RMAs.

    Integrates with quality module for NCR creation from
    confirmed failures.
    """

    def __init__(self):
        # In-memory storage (replace with database)
        self._registrations: dict[str, WarrantyRegistration] = {}
        self._claims: dict[str, WarrantyClaim] = {}
        self._rmas: dict[str, RMA] = {}
        self._policies: dict[str, WarrantyPolicy] = {}

        # Counters for generating numbers
        self._reg_counter = 0
        self._claim_counter = 0
        self._rma_counter = 0

    # =========================================================================
    # Warranty Registration
    # =========================================================================

    def register_warranty(
        self,
        part_id: str,
        part_number: str,
        serial_number: str,
        customer_name: str,
        purchase_date: date,
        warranty_months: int = 12,
        warranty_type: WarrantyType = WarrantyType.STANDARD,
        customer_email: Optional[str] = None,
        customer_phone: Optional[str] = None,
        customer_address: Optional[str] = None,
        lot_number: Optional[str] = None,
        invoice_number: Optional[str] = None,
        terms: str = "",
        created_by: Optional[str] = None,
    ) -> WarrantyRegistration:
        """Register a new warranty for a serialized product."""
        self._reg_counter += 1
        reg_id = str(uuid.uuid4())
        reg_number = f"WR-{datetime.now().year}-{self._reg_counter:04d}"

        # Calculate warranty end date
        start_date = purchase_date
        end_date = start_date + timedelta(days=warranty_months * 30)

        registration = WarrantyRegistration(
            id=reg_id,
            registration_number=reg_number,
            part_id=part_id,
            part_number=part_number,
            serial_number=serial_number,
            lot_number=lot_number,
            customer_name=customer_name,
            customer_email=customer_email,
            customer_phone=customer_phone,
            customer_address=customer_address,
            purchase_date=purchase_date,
            invoice_number=invoice_number,
            warranty_type=warranty_type,
            status=WarrantyStatus.ACTIVE,
            start_date=start_date,
            end_date=end_date,
            terms=terms,
            created_by=created_by,
        )

        self._registrations[reg_id] = registration
        return registration

    def get_registration(self, registration_id: str) -> Optional[WarrantyRegistration]:
        """Get warranty registration by ID."""
        return self._registrations.get(registration_id)

    def get_registration_by_serial(self, serial_number: str) -> Optional[WarrantyRegistration]:
        """Find warranty registration by serial number."""
        for reg in self._registrations.values():
            if reg.serial_number == serial_number:
                return reg
        return None

    def list_registrations(
        self,
        status: Optional[WarrantyStatus] = None,
        customer_name: Optional[str] = None,
        part_number: Optional[str] = None,
        expiring_within_days: Optional[int] = None,
    ) -> list[WarrantyRegistration]:
        """List warranty registrations with optional filters."""
        results = list(self._registrations.values())

        if status:
            results = [r for r in results if r.status == status]

        if customer_name:
            results = [r for r in results if customer_name.lower() in r.customer_name.lower()]

        if part_number:
            results = [r for r in results if r.part_number == part_number]

        if expiring_within_days:
            cutoff = date.today() + timedelta(days=expiring_within_days)
            results = [
                r for r in results
                if r.end_date and r.end_date <= cutoff and r.status == WarrantyStatus.ACTIVE
            ]

        return sorted(results, key=lambda r: r.created_at or datetime.min, reverse=True)

    def extend_warranty(
        self,
        registration_id: str,
        additional_months: int,
        extended_terms: str = "",
    ) -> Optional[WarrantyRegistration]:
        """Add extended warranty to a registration."""
        reg = self._registrations.get(registration_id)
        if not reg:
            return None

        base_end = reg.end_date or date.today()
        reg.extended_warranty = True
        reg.extended_end_date = base_end + timedelta(days=additional_months * 30)
        reg.extended_terms = extended_terms

        return reg

    def transfer_warranty(
        self,
        registration_id: str,
        new_customer_name: str,
        new_customer_email: Optional[str] = None,
        new_customer_phone: Optional[str] = None,
        new_customer_address: Optional[str] = None,
    ) -> Optional[WarrantyRegistration]:
        """Transfer warranty to new owner."""
        reg = self._registrations.get(registration_id)
        if not reg:
            return None

        reg.transferred_from = reg.customer_name
        reg.transfer_date = date.today()
        reg.customer_name = new_customer_name
        reg.customer_email = new_customer_email
        reg.customer_phone = new_customer_phone
        reg.customer_address = new_customer_address
        reg.status = WarrantyStatus.TRANSFERRED

        return reg

    def void_registration(
        self,
        registration_id: str,
        reason: str,
    ) -> Optional[WarrantyRegistration]:
        """Void a warranty registration."""
        reg = self._registrations.get(registration_id)
        if not reg:
            return None

        reg.status = WarrantyStatus.VOIDED
        reg.notes = f"Voided: {reason}"
        return reg

    def check_warranty_status(self, serial_number: str) -> dict:
        """Check warranty status for a serial number (customer-facing)."""
        reg = self.get_registration_by_serial(serial_number)
        if not reg:
            return {
                "covered": False,
                "message": "No warranty registration found for this serial number",
            }

        if reg.status == WarrantyStatus.VOIDED:
            return {
                "covered": False,
                "message": "Warranty has been voided",
            }

        if not reg.is_active:
            return {
                "covered": False,
                "message": "Warranty has expired",
                "expired_date": reg.end_date.isoformat() if reg.end_date else None,
            }

        return {
            "covered": True,
            "registration_number": reg.registration_number,
            "warranty_type": reg.warranty_type.value,
            "end_date": (reg.extended_end_date or reg.end_date).isoformat() if (reg.extended_end_date or reg.end_date) else None,
            "days_remaining": reg.days_remaining,
            "extended": reg.extended_warranty,
        }

    # =========================================================================
    # Warranty Claims
    # =========================================================================

    def create_claim(
        self,
        warranty_id: str,
        title: str,
        description: str,
        claim_type: ClaimType = ClaimType.DEFECT,
        priority: str = "medium",
        contact_name: str = "",
        contact_email: Optional[str] = None,
        contact_phone: Optional[str] = None,
        failure_date: Optional[date] = None,
        created_by: Optional[str] = None,
    ) -> Optional[WarrantyClaim]:
        """Create a new warranty claim."""
        reg = self._registrations.get(warranty_id)
        if not reg:
            return None

        self._claim_counter += 1
        claim_id = str(uuid.uuid4())
        claim_number = f"WC-{datetime.now().year}-{self._claim_counter:04d}"

        claim = WarrantyClaim(
            id=claim_id,
            claim_number=claim_number,
            warranty_id=warranty_id,
            registration_number=reg.registration_number,
            part_id=reg.part_id,
            part_number=reg.part_number,
            serial_number=reg.serial_number,
            claim_type=claim_type,
            status=ClaimStatus.SUBMITTED,
            priority=priority,
            title=title,
            description=description,
            failure_date=failure_date,
            contact_name=contact_name or reg.customer_name,
            contact_email=contact_email or reg.customer_email,
            contact_phone=contact_phone or reg.customer_phone,
            created_by=created_by,
        )

        self._claims[claim_id] = claim
        return claim

    def get_claim(self, claim_id: str) -> Optional[WarrantyClaim]:
        """Get claim by ID."""
        return self._claims.get(claim_id)

    def list_claims(
        self,
        warranty_id: Optional[str] = None,
        status: Optional[ClaimStatus] = None,
        claim_type: Optional[ClaimType] = None,
        priority: Optional[str] = None,
        part_number: Optional[str] = None,
    ) -> list[WarrantyClaim]:
        """List claims with optional filters."""
        results = list(self._claims.values())

        if warranty_id:
            results = [c for c in results if c.warranty_id == warranty_id]

        if status:
            results = [c for c in results if c.status == status]

        if claim_type:
            results = [c for c in results if c.claim_type == claim_type]

        if priority:
            results = [c for c in results if c.priority == priority]

        if part_number:
            results = [c for c in results if c.part_number == part_number]

        return sorted(results, key=lambda c: c.created_at or datetime.min, reverse=True)

    def review_claim(
        self,
        claim_id: str,
        reviewer_id: str,
        notes: str = "",
    ) -> Optional[WarrantyClaim]:
        """Mark claim as under review."""
        claim = self._claims.get(claim_id)
        if not claim:
            return None

        claim.status = ClaimStatus.UNDER_REVIEW
        claim.reviewed_by = reviewer_id
        claim.reviewed_date = datetime.now()
        claim.review_notes = notes

        return claim

    def approve_claim(
        self,
        claim_id: str,
        approver_id: str,
        reason: str = "",
        estimated_cost: Optional[Decimal] = None,
    ) -> Optional[WarrantyClaim]:
        """Approve a warranty claim."""
        claim = self._claims.get(claim_id)
        if not claim:
            return None

        claim.status = ClaimStatus.APPROVED
        claim.decision = "approved"
        claim.decision_by = approver_id
        claim.decision_date = datetime.now()
        claim.decision_reason = reason

        if estimated_cost:
            claim.estimated_cost = estimated_cost

        return claim

    def deny_claim(
        self,
        claim_id: str,
        denier_id: str,
        reason: str,
    ) -> Optional[WarrantyClaim]:
        """Deny a warranty claim."""
        claim = self._claims.get(claim_id)
        if not claim:
            return None

        claim.status = ClaimStatus.DENIED
        claim.decision = "denied"
        claim.decision_by = denier_id
        claim.decision_date = datetime.now()
        claim.decision_reason = reason

        return claim

    def close_claim(
        self,
        claim_id: str,
        resolution: str,
        closed_by: str,
        actual_cost: Optional[Decimal] = None,
        labor_cost: Optional[Decimal] = None,
        parts_cost: Optional[Decimal] = None,
        shipping_cost: Optional[Decimal] = None,
    ) -> Optional[WarrantyClaim]:
        """Close a resolved claim."""
        claim = self._claims.get(claim_id)
        if not claim:
            return None

        claim.status = ClaimStatus.CLOSED
        claim.resolution = resolution
        claim.resolution_date = datetime.now()
        claim.closed_at = datetime.now()
        claim.closed_by = closed_by

        if actual_cost:
            claim.actual_cost = actual_cost
        if labor_cost:
            claim.labor_cost = labor_cost
        if parts_cost:
            claim.parts_cost = parts_cost
        if shipping_cost:
            claim.shipping_cost = shipping_cost

        # Calculate actual if component costs provided
        if labor_cost or parts_cost or shipping_cost:
            claim.actual_cost = (
                (labor_cost or Decimal("0")) +
                (parts_cost or Decimal("0")) +
                (shipping_cost or Decimal("0"))
            )

        return claim

    # =========================================================================
    # RMA Management
    # =========================================================================

    def create_rma(
        self,
        claim_id: str,
        ship_to_address: str,
        quantity: int = 1,
        created_by: Optional[str] = None,
    ) -> Optional[RMA]:
        """Create RMA for an approved claim."""
        claim = self._claims.get(claim_id)
        if not claim:
            return None

        self._rma_counter += 1
        rma_id = str(uuid.uuid4())
        rma_number = f"RMA-{datetime.now().year}-{self._rma_counter:04d}"

        rma = RMA(
            id=rma_id,
            rma_number=rma_number,
            claim_id=claim_id,
            claim_number=claim.claim_number,
            part_id=claim.part_id,
            part_number=claim.part_number,
            serial_number=claim.serial_number,
            quantity=quantity,
            status=RMAStatus.ISSUED,
            ship_to_address=ship_to_address,
            created_by=created_by,
        )

        self._rmas[rma_id] = rma
        claim.rma_id = rma_id
        claim.status = ClaimStatus.IN_PROGRESS

        return rma

    def get_rma(self, rma_id: str) -> Optional[RMA]:
        """Get RMA by ID."""
        return self._rmas.get(rma_id)

    def list_rmas(
        self,
        claim_id: Optional[str] = None,
        status: Optional[RMAStatus] = None,
        part_number: Optional[str] = None,
    ) -> list[RMA]:
        """List RMAs with optional filters."""
        results = list(self._rmas.values())

        if claim_id:
            results = [r for r in results if r.claim_id == claim_id]

        if status:
            results = [r for r in results if r.status == status]

        if part_number:
            results = [r for r in results if r.part_number == part_number]

        return sorted(results, key=lambda r: r.created_at or datetime.min, reverse=True)

    def update_rma_shipping(
        self,
        rma_id: str,
        carrier: str,
        tracking_number: str,
        shipped_date: Optional[date] = None,
    ) -> Optional[RMA]:
        """Update RMA with customer shipping info."""
        rma = self._rmas.get(rma_id)
        if not rma:
            return None

        rma.carrier_to = carrier
        rma.tracking_to = tracking_number
        rma.shipped_date = shipped_date or date.today()
        rma.status = RMAStatus.SHIPPED

        return rma

    def receive_rma(
        self,
        rma_id: str,
        received_by: str,
        condition: str = "",
    ) -> Optional[RMA]:
        """Record receipt of RMA item."""
        rma = self._rmas.get(rma_id)
        if not rma:
            return None

        rma.status = RMAStatus.RECEIVED
        rma.received_date = date.today()
        rma.received_by = received_by
        rma.condition_received = condition

        return rma

    def inspect_rma(
        self,
        rma_id: str,
        inspector_id: str,
        failure_confirmed: bool,
        failure_category: Optional[FailureCategory] = None,
        failure_description: str = "",
        root_cause: str = "",
        inspection_notes: str = "",
    ) -> Optional[RMA]:
        """Record inspection results."""
        rma = self._rmas.get(rma_id)
        if not rma:
            return None

        rma.status = RMAStatus.INSPECTING
        rma.inspected_by = inspector_id
        rma.inspected_date = datetime.now()
        rma.inspection_notes = inspection_notes
        rma.failure_confirmed = failure_confirmed
        rma.failure_category = failure_category
        rma.failure_description = failure_description
        rma.root_cause = root_cause

        return rma

    def disposition_rma(
        self,
        rma_id: str,
        disposition: DispositionAction,
        disposition_by: str,
        notes: str = "",
        replacement_serial: Optional[str] = None,
        refund_amount: Optional[Decimal] = None,
        credit_amount: Optional[Decimal] = None,
    ) -> Optional[RMA]:
        """Set disposition for RMA."""
        rma = self._rmas.get(rma_id)
        if not rma:
            return None

        rma.disposition = disposition
        rma.disposition_by = disposition_by
        rma.disposition_date = datetime.now()
        rma.disposition_notes = notes

        if disposition == DispositionAction.REPAIR:
            rma.status = RMAStatus.REPAIRING
        elif disposition == DispositionAction.REPLACE:
            rma.status = RMAStatus.REPLACING
            rma.replacement_serial = replacement_serial
        elif disposition == DispositionAction.REFUND:
            rma.refund_amount = refund_amount or Decimal("0")
        elif disposition == DispositionAction.CREDIT:
            rma.credit_amount = credit_amount or Decimal("0")

        return rma

    def complete_repair(
        self,
        rma_id: str,
        labor_cost: Decimal,
        parts_cost: Decimal,
    ) -> Optional[RMA]:
        """Mark repair as complete."""
        rma = self._rmas.get(rma_id)
        if not rma:
            return None

        rma.status = RMAStatus.REPAIRED
        rma.repair_labor_cost = labor_cost
        rma.repair_parts_cost = parts_cost

        return rma

    def ship_rma_back(
        self,
        rma_id: str,
        carrier: str,
        tracking_number: str,
        shipping_cost: Decimal = Decimal("0"),
    ) -> Optional[RMA]:
        """Ship item back to customer."""
        rma = self._rmas.get(rma_id)
        if not rma:
            return None

        rma.status = RMAStatus.SHIPPING_BACK
        rma.carrier_from = carrier
        rma.tracking_from = tracking_number
        rma.shipped_back_date = date.today()
        rma.shipping_cost = shipping_cost

        return rma

    def complete_rma(
        self,
        rma_id: str,
    ) -> Optional[RMA]:
        """Mark RMA as complete."""
        rma = self._rmas.get(rma_id)
        if not rma:
            return None

        rma.status = RMAStatus.COMPLETED
        rma.completed_at = datetime.now()

        # Also close the related claim
        claim = self._claims.get(rma.claim_id)
        if claim:
            claim.status = ClaimStatus.COMPLETED

        return rma

    def link_ncr(
        self,
        rma_id: str,
        ncr_id: str,
    ) -> Optional[RMA]:
        """Link RMA to NCR in quality module."""
        rma = self._rmas.get(rma_id)
        if not rma:
            return None

        # Update the claim with NCR link
        claim = self._claims.get(rma.claim_id)
        if claim:
            claim.ncr_id = ncr_id

        return rma

    # =========================================================================
    # Warranty Policies
    # =========================================================================

    def create_policy(
        self,
        policy_code: str,
        name: str,
        duration_months: int,
        warranty_type: WarrantyType = WarrantyType.STANDARD,
        coverage_description: str = "",
        exclusions: str = "",
        part_id: Optional[str] = None,
        part_category: Optional[str] = None,
        transferable: bool = False,
    ) -> WarrantyPolicy:
        """Create a warranty policy template."""
        policy_id = str(uuid.uuid4())

        policy = WarrantyPolicy(
            id=policy_id,
            policy_code=policy_code,
            name=name,
            warranty_type=warranty_type,
            duration_months=duration_months,
            coverage_description=coverage_description,
            exclusions=exclusions,
            part_id=part_id,
            part_category=part_category,
            transferable=transferable,
        )

        self._policies[policy_id] = policy
        return policy

    def get_policy(self, policy_id: str) -> Optional[WarrantyPolicy]:
        """Get policy by ID."""
        return self._policies.get(policy_id)

    def get_policy_for_part(self, part_id: str) -> Optional[WarrantyPolicy]:
        """Find applicable policy for a part."""
        for policy in self._policies.values():
            if policy.is_active and policy.part_id == part_id:
                return policy
        return None

    def list_policies(
        self,
        active_only: bool = True,
    ) -> list[WarrantyPolicy]:
        """List warranty policies."""
        results = list(self._policies.values())
        if active_only:
            results = [p for p in results if p.is_active]
        return results

    # =========================================================================
    # Metrics and Reporting
    # =========================================================================

    def get_metrics(self) -> WarrantyMetrics:
        """Get aggregated warranty metrics."""
        today = date.today()
        thirty_days = today + timedelta(days=30)
        month_start = today.replace(day=1)

        # Registration stats
        active_regs = [r for r in self._registrations.values() if r.is_active]
        expiring = [
            r for r in active_regs
            if r.end_date and r.end_date <= thirty_days
        ]

        # Claim stats
        all_claims = list(self._claims.values())
        open_claims = [c for c in all_claims if c.status not in [ClaimStatus.CLOSED, ClaimStatus.DENIED]]
        month_claims = [
            c for c in all_claims
            if c.created_at and c.created_at.date() >= month_start
        ]

        approved = [c for c in all_claims if c.decision == "approved"]
        decided = [c for c in all_claims if c.decision in ["approved", "denied"]]
        approval_rate = len(approved) / len(decided) if decided else 0.0

        # Resolution time
        closed_claims = [c for c in all_claims if c.closed_at and c.created_at]
        if closed_claims:
            total_days = sum(
                (c.closed_at - c.created_at).days for c in closed_claims
            )
            avg_resolution = total_days / len(closed_claims)
        else:
            avg_resolution = 0.0

        # RMA stats
        all_rmas = list(self._rmas.values())
        open_rmas = [r for r in all_rmas if r.status != RMAStatus.COMPLETED]
        completed_rmas = [r for r in all_rmas if r.completed_at and r.created_at]
        if completed_rmas:
            total_rma_days = sum(
                (r.completed_at - r.created_at).days for r in completed_rmas
            )
            avg_turnaround = total_rma_days / len(completed_rmas)
        else:
            avg_turnaround = 0.0

        # Failure analysis
        failure_counts: dict[str, int] = {}
        for rma in all_rmas:
            if rma.failure_category:
                cat = rma.failure_category.value
                failure_counts[cat] = failure_counts.get(cat, 0) + 1

        top_failures = [
            {"category": k, "count": v}
            for k, v in sorted(failure_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        ]

        # Top failing parts
        part_failures: dict[str, int] = {}
        for rma in all_rmas:
            if rma.failure_confirmed:
                part_failures[rma.part_number] = part_failures.get(rma.part_number, 0) + 1

        top_parts = [
            {"part_number": k, "failure_count": v}
            for k, v in sorted(part_failures.items(), key=lambda x: x[1], reverse=True)[:5]
        ]

        # Costs
        total_cost = sum(c.actual_cost for c in all_claims)
        avg_cost = total_cost / len(all_claims) if all_claims else Decimal("0")

        return WarrantyMetrics(
            total_registrations=len(self._registrations),
            active_warranties=len(active_regs),
            expiring_30_days=len(expiring),
            total_claims=len(all_claims),
            open_claims=len(open_claims),
            claims_this_month=len(month_claims),
            approval_rate=approval_rate,
            avg_resolution_days=avg_resolution,
            total_rmas=len(all_rmas),
            open_rmas=len(open_rmas),
            avg_turnaround_days=avg_turnaround,
            top_failure_categories=top_failures,
            top_failing_parts=top_parts,
            total_warranty_cost=total_cost,
            avg_claim_cost=avg_cost,
        )

    def get_failure_analysis(
        self,
        part_number: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> dict:
        """Get failure analysis data for reporting."""
        rmas = list(self._rmas.values())

        if part_number:
            rmas = [r for r in rmas if r.part_number == part_number]

        if date_from:
            rmas = [r for r in rmas if r.created_at and r.created_at.date() >= date_from]

        if date_to:
            rmas = [r for r in rmas if r.created_at and r.created_at.date() <= date_to]

        # Aggregate by category
        by_category: dict[str, list] = {}
        for rma in rmas:
            if rma.failure_category:
                cat = rma.failure_category.value
                if cat not in by_category:
                    by_category[cat] = []
                by_category[cat].append({
                    "rma_number": rma.rma_number,
                    "part_number": rma.part_number,
                    "serial_number": rma.serial_number,
                    "description": rma.failure_description,
                    "root_cause": rma.root_cause,
                })

        return {
            "total_analyzed": len([r for r in rmas if r.failure_category]),
            "by_category": by_category,
            "confirmed_failures": len([r for r in rmas if r.failure_confirmed]),
            "no_fault_found": len([r for r in rmas if r.disposition == DispositionAction.NO_FAULT_FOUND]),
        }


# Singleton instance
_warranty_service: Optional[WarrantyService] = None


def get_warranty_service() -> WarrantyService:
    """Get the warranty service singleton."""
    global _warranty_service
    if _warranty_service is None:
        _warranty_service = WarrantyService()
    return _warranty_service
