"""
Configuration Management Models

Manages product configurations, variants, options, and effectivity.
Enables tracking what parts/assemblies are valid for which configurations.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Optional


class ConfigurationType(str, Enum):
    """Types of configurations."""

    STANDARD = "standard"  # Base configuration
    OPTION = "option"  # Optional add-on
    VARIANT = "variant"  # Alternative version
    UPGRADE = "upgrade"  # Enhanced version
    REGIONAL = "regional"  # Region-specific


class EffectivityType(str, Enum):
    """Types of effectivity."""

    DATE = "date"  # Valid during date range
    SERIAL = "serial"  # Valid for serial number range
    LOT = "lot"  # Valid for lot number range
    UNIT = "unit"  # Valid for specific units


class RuleType(str, Enum):
    """Types of configuration rules."""

    REQUIRES = "requires"  # A requires B
    EXCLUDES = "excludes"  # A excludes B (mutual exclusion)
    RECOMMENDS = "recommends"  # A recommends B (soft)
    INCLUDES = "includes"  # A always includes B


@dataclass
class ConfigurationOption:
    """
    A configuration option or variant.

    Represents a selectable feature or alternative for a product.
    """

    id: str
    name: str
    code: str  # Short code like "OPT-SOLAR", "VAR-PREMIUM"
    description: str = ""

    option_type: ConfigurationType = ConfigurationType.OPTION

    # What this option affects
    part_id: Optional[str] = None  # Part this option belongs to
    bom_id: Optional[str] = None  # BOM this modifies

    # Pricing
    price_delta: Decimal = Decimal("0")  # Additional cost
    currency: str = "USD"

    # Grouping
    option_group: Optional[str] = None  # "Roofing", "HVAC", "Finishes"
    is_default: bool = False
    sort_order: int = 0

    # Status
    is_active: bool = True
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None

    # Metadata
    attributes: dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

    def is_effective(self, as_of: Optional[date] = None) -> bool:
        """Check if option is effective on a given date."""
        as_of = as_of or date.today()
        if self.effective_from and as_of < self.effective_from:
            return False
        if self.effective_to and as_of > self.effective_to:
            return False
        return self.is_active


@dataclass
class ConfigurationRule:
    """
    A rule governing configuration combinations.

    Defines constraints like "if A then B" or "A excludes C".
    """

    id: str
    name: str
    rule_type: RuleType

    # Options involved
    source_option_id: str  # If this is selected...
    target_option_id: str  # ...then this constraint applies

    # Optional condition
    condition: Optional[str] = None  # Expression for conditional rules

    # Messaging
    message: str = ""  # User-facing explanation
    is_hard: bool = True  # Hard = error, Soft = warning

    # Status
    is_active: bool = True

    def evaluate(
        self, selected_options: set[str], available_options: set[str]
    ) -> tuple[bool, Optional[str]]:
        """
        Evaluate if rule is satisfied.

        Returns (is_valid, error_message).
        """
        if not self.is_active:
            return True, None

        if self.source_option_id not in selected_options:
            # Rule doesn't apply if source not selected
            return True, None

        if self.rule_type == RuleType.REQUIRES:
            if self.target_option_id not in selected_options:
                return False, self.message or f"Option requires {self.target_option_id}"
            return True, None

        elif self.rule_type == RuleType.EXCLUDES:
            if self.target_option_id in selected_options:
                return False, self.message or f"Option conflicts with {self.target_option_id}"
            return True, None

        elif self.rule_type == RuleType.RECOMMENDS:
            # Soft rule - always valid but may generate warning
            if self.target_option_id not in selected_options:
                return True, self.message  # Return as info, not error
            return True, None

        elif self.rule_type == RuleType.INCLUDES:
            # Automatic inclusion - handled elsewhere
            return True, None

        return True, None


@dataclass
class Effectivity:
    """
    Effectivity record defining when a part/config is valid.

    Supports date, serial number, lot, or unit-based effectivity.
    """

    id: str
    effectivity_type: EffectivityType

    # What this applies to
    entity_type: str  # "part", "bom_item", "configuration"
    entity_id: str

    # Configuration context
    configuration_id: Optional[str] = None

    # Date effectivity
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None

    # Serial/lot effectivity
    from_serial: Optional[str] = None
    to_serial: Optional[str] = None
    lot_numbers: list[str] = field(default_factory=list)

    # Unit effectivity (specific units)
    unit_ids: list[str] = field(default_factory=list)

    # Status
    is_active: bool = True
    notes: Optional[str] = None

    def is_valid(
        self,
        as_of_date: Optional[date] = None,
        serial: Optional[str] = None,
        lot: Optional[str] = None,
        unit_id: Optional[str] = None,
    ) -> bool:
        """Check if effectivity is valid for given context."""
        if not self.is_active:
            return False

        if self.effectivity_type == EffectivityType.DATE:
            as_of = as_of_date or date.today()
            if self.effective_from and as_of < self.effective_from:
                return False
            if self.effective_to and as_of > self.effective_to:
                return False
            return True

        elif self.effectivity_type == EffectivityType.SERIAL:
            if not serial:
                return True  # No serial to check
            if self.from_serial and serial < self.from_serial:
                return False
            if self.to_serial and serial > self.to_serial:
                return False
            return True

        elif self.effectivity_type == EffectivityType.LOT:
            if not lot:
                return True
            return lot in self.lot_numbers if self.lot_numbers else True

        elif self.effectivity_type == EffectivityType.UNIT:
            if not unit_id:
                return True
            return unit_id in self.unit_ids if self.unit_ids else True

        return True


@dataclass
class ProductConfiguration:
    """
    A complete product configuration.

    Captures selected options for a specific product instance.
    """

    id: str
    name: str
    product_id: str  # Base product/part ID
    product_number: str

    # Selected options
    selected_options: list[str] = field(default_factory=list)  # Option IDs

    # Configuration state
    is_valid: bool = False
    validation_errors: list[str] = field(default_factory=list)
    validation_warnings: list[str] = field(default_factory=list)

    # Pricing
    base_price: Decimal = Decimal("0")
    options_price: Decimal = Decimal("0")
    total_price: Decimal = Decimal("0")

    # Effectivity
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None

    # Status
    status: str = "draft"  # draft, released, obsolete
    released_at: Optional[datetime] = None
    released_by: Optional[str] = None

    # Tracking
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # Reference
    project_id: Optional[str] = None
    notes: Optional[str] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()


@dataclass
class ConfigurationBaseline:
    """
    A frozen snapshot of product configuration.

    Used for production releases, audit trails, and version comparison.
    """

    id: str
    name: str
    configuration_id: str
    version: str  # "1.0", "2.0", etc.

    # Snapshot data
    product_id: str
    product_number: str
    selected_options: list[str] = field(default_factory=list)
    option_details: list[dict] = field(default_factory=list)  # Full option data at time of baseline

    # BOM snapshot
    bom_items: list[dict] = field(default_factory=list)  # Resolved BOM at time of baseline

    # Pricing at time of baseline
    total_price: Decimal = Decimal("0")

    # Lifecycle
    baseline_date: date = field(default_factory=date.today)
    baselined_by: Optional[str] = None
    status: str = "active"  # active, superseded, obsolete

    # Reference
    supersedes_id: Optional[str] = None  # Previous baseline
    superseded_by_id: Optional[str] = None  # Next baseline

    notes: Optional[str] = None
    created_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class ConfiguredBOMItem:
    """
    A BOM item with configuration effectivity.

    Represents a part that is only included for certain configurations.
    """

    id: str
    bom_id: str
    part_id: str
    part_number: str

    quantity: Decimal
    unit_of_measure: str = "EA"

    # Configuration condition
    included_in_options: list[str] = field(default_factory=list)  # Include if ANY of these
    excluded_in_options: list[str] = field(default_factory=list)  # Exclude if ANY of these
    always_include: bool = False  # Include regardless of options

    # Effectivity
    effectivities: list[Effectivity] = field(default_factory=list)

    # Substitutes
    substitute_parts: list[str] = field(default_factory=list)
    substitute_reason: Optional[str] = None

    notes: Optional[str] = None

    def is_included(self, selected_options: set[str]) -> bool:
        """Check if item should be included for given option selection."""
        if self.always_include:
            return True

        # Check exclusions first
        if self.excluded_in_options:
            if any(opt in selected_options for opt in self.excluded_in_options):
                return False

        # Check inclusions
        if self.included_in_options:
            return any(opt in selected_options for opt in self.included_in_options)

        # Default: include if no conditions
        return True
