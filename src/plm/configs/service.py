"""
Configuration Management Service

Business logic for managing product configurations, options, and effectivity.
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import uuid4

from .models import (
    ConfigurationOption,
    ConfigurationType,
    ConfigurationRule,
    RuleType,
    Effectivity,
    EffectivityType,
    ProductConfiguration,
    ConfigurationBaseline,
    ConfiguredBOMItem,
)


class ConfigurationError(Exception):
    """Base exception for configuration operations."""

    pass


class InvalidConfigurationError(ConfigurationError):
    """Raised when a configuration violates rules."""

    def __init__(self, errors: list[str], warnings: list[str] = None):
        self.errors = errors
        self.warnings = warnings or []
        super().__init__(f"Invalid configuration: {'; '.join(errors)}")


class OptionNotFoundError(ConfigurationError):
    """Raised when an option doesn't exist."""

    pass


@dataclass
class ValidationResult:
    """Result of configuration validation."""

    is_valid: bool
    errors: list[str]
    warnings: list[str]
    auto_included: list[str]  # Options auto-included by rules


@dataclass
class ResolvedBOM:
    """BOM resolved for a specific configuration."""

    configuration_id: str
    bom_id: str
    items: list[ConfiguredBOMItem]
    total_cost: Decimal
    total_weight: Optional[Decimal] = None


class ConfigurationService:
    """
    Service for managing product configurations.

    Handles option management, rule validation, effectivity,
    and configuration resolution.
    """

    def __init__(self):
        # In-memory storage for demo - would use repository in production
        self._options: dict[str, ConfigurationOption] = {}
        self._rules: dict[str, ConfigurationRule] = {}
        self._effectivities: dict[str, Effectivity] = {}
        self._configurations: dict[str, ProductConfiguration] = {}
        self._baselines: dict[str, ConfigurationBaseline] = {}
        self._configured_bom_items: dict[str, ConfiguredBOMItem] = {}

    # -------------------------------------------------------------------------
    # Option Management
    # -------------------------------------------------------------------------

    def create_option(self, option: ConfigurationOption) -> ConfigurationOption:
        """Create a new configuration option."""
        if not option.id:
            option.id = str(uuid4())
        self._options[option.id] = option
        return option

    def get_option(self, option_id: str) -> Optional[ConfigurationOption]:
        """Get an option by ID."""
        return self._options.get(option_id)

    def get_option_by_code(self, code: str) -> Optional[ConfigurationOption]:
        """Get an option by code."""
        for option in self._options.values():
            if option.code == code:
                return option
        return None

    def list_options(
        self,
        part_id: Optional[str] = None,
        option_group: Optional[str] = None,
        option_type: Optional[ConfigurationType] = None,
        is_active: bool = True,
    ) -> list[ConfigurationOption]:
        """List options with optional filters."""
        options = []
        for option in self._options.values():
            if is_active and not option.is_active:
                continue
            if part_id and option.part_id != part_id:
                continue
            if option_group and option.option_group != option_group:
                continue
            if option_type and option.option_type != option_type:
                continue
            options.append(option)
        return sorted(options, key=lambda o: (o.option_group or "", o.sort_order))

    def list_option_groups(self, part_id: Optional[str] = None) -> list[str]:
        """List distinct option groups."""
        groups = set()
        for option in self._options.values():
            if part_id and option.part_id != part_id:
                continue
            if option.option_group:
                groups.add(option.option_group)
        return sorted(groups)

    def update_option(self, option: ConfigurationOption) -> ConfigurationOption:
        """Update an option."""
        if option.id not in self._options:
            raise OptionNotFoundError(f"Option {option.id} not found")
        self._options[option.id] = option
        return option

    def deactivate_option(self, option_id: str) -> ConfigurationOption:
        """Deactivate an option."""
        option = self.get_option(option_id)
        if not option:
            raise OptionNotFoundError(f"Option {option_id} not found")
        option.is_active = False
        option.effective_to = date.today()
        return option

    # -------------------------------------------------------------------------
    # Rule Management
    # -------------------------------------------------------------------------

    def create_rule(self, rule: ConfigurationRule) -> ConfigurationRule:
        """Create a configuration rule."""
        if not rule.id:
            rule.id = str(uuid4())
        self._rules[rule.id] = rule
        return rule

    def get_rule(self, rule_id: str) -> Optional[ConfigurationRule]:
        """Get a rule by ID."""
        return self._rules.get(rule_id)

    def list_rules(
        self,
        source_option_id: Optional[str] = None,
        target_option_id: Optional[str] = None,
        rule_type: Optional[RuleType] = None,
        is_active: bool = True,
    ) -> list[ConfigurationRule]:
        """List rules with optional filters."""
        rules = []
        for rule in self._rules.values():
            if is_active and not rule.is_active:
                continue
            if source_option_id and rule.source_option_id != source_option_id:
                continue
            if target_option_id and rule.target_option_id != target_option_id:
                continue
            if rule_type and rule.rule_type != rule_type:
                continue
            rules.append(rule)
        return rules

    def get_rules_for_option(self, option_id: str) -> list[ConfigurationRule]:
        """Get all rules involving an option (as source or target)."""
        return [
            r
            for r in self._rules.values()
            if r.source_option_id == option_id or r.target_option_id == option_id
        ]

    # -------------------------------------------------------------------------
    # Configuration Validation
    # -------------------------------------------------------------------------

    def validate_configuration(
        self, selected_options: list[str], part_id: Optional[str] = None
    ) -> ValidationResult:
        """
        Validate a configuration selection.

        Returns validation result with errors, warnings, and auto-included options.
        """
        errors = []
        warnings = []
        auto_included = []

        # Get available options
        available_options = self.list_options(part_id=part_id)
        available_ids = {o.id for o in available_options}
        selected_set = set(selected_options)

        # Check that all selected options exist and are active
        for opt_id in selected_options:
            if opt_id not in available_ids:
                errors.append(f"Unknown option: {opt_id}")
            else:
                option = self.get_option(opt_id)
                if option and not option.is_effective():
                    errors.append(f"Option {option.name} is not currently effective")

        # Evaluate all rules
        for rule in self._rules.values():
            if not rule.is_active:
                continue

            is_valid, message = rule.evaluate(selected_set, available_ids)

            if not is_valid:
                if rule.is_hard:
                    errors.append(message)
                else:
                    warnings.append(message)
            elif message and rule.rule_type == RuleType.RECOMMENDS:
                warnings.append(message)

            # Handle auto-includes
            if (
                rule.rule_type == RuleType.INCLUDES
                and rule.source_option_id in selected_set
                and rule.target_option_id not in selected_set
            ):
                auto_included.append(rule.target_option_id)

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            auto_included=auto_included,
        )

    def get_available_options(
        self, selected_options: list[str], part_id: Optional[str] = None
    ) -> list[ConfigurationOption]:
        """
        Get options that can still be added to the configuration.

        Filters out options that would violate exclusion rules.
        """
        available = []
        selected_set = set(selected_options)

        for option in self.list_options(part_id=part_id):
            if option.id in selected_set:
                continue

            # Check if adding this option would violate any rules
            can_add = True
            for rule in self._rules.values():
                if not rule.is_active or rule.rule_type != RuleType.EXCLUDES:
                    continue

                # Check both directions of exclusion
                if (
                    rule.source_option_id in selected_set
                    and rule.target_option_id == option.id
                ):
                    can_add = False
                    break
                if (
                    rule.source_option_id == option.id
                    and rule.target_option_id in selected_set
                ):
                    can_add = False
                    break

            if can_add:
                available.append(option)

        return available

    # -------------------------------------------------------------------------
    # Configuration Management
    # -------------------------------------------------------------------------

    def create_configuration(
        self,
        name: str,
        product_id: str,
        product_number: str,
        selected_options: list[str] = None,
        project_id: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> ProductConfiguration:
        """Create a new product configuration."""
        config = ProductConfiguration(
            id=str(uuid4()),
            name=name,
            product_id=product_id,
            product_number=product_number,
            selected_options=selected_options or [],
            project_id=project_id,
            created_by=created_by,
        )

        # Validate and calculate price
        if config.selected_options:
            result = self.validate_configuration(config.selected_options, product_id)
            config.is_valid = result.is_valid
            config.validation_errors = result.errors
            config.validation_warnings = result.warnings

            # Auto-include options
            if result.auto_included:
                config.selected_options.extend(result.auto_included)

            # Calculate price
            config.options_price = self._calculate_options_price(config.selected_options)
            config.total_price = config.base_price + config.options_price

        self._configurations[config.id] = config
        return config

    def get_configuration(self, config_id: str) -> Optional[ProductConfiguration]:
        """Get a configuration by ID."""
        return self._configurations.get(config_id)

    def update_configuration(
        self, config_id: str, selected_options: list[str]
    ) -> ProductConfiguration:
        """Update a configuration's selected options."""
        config = self.get_configuration(config_id)
        if not config:
            raise ConfigurationError(f"Configuration {config_id} not found")

        if config.status != "draft":
            raise ConfigurationError(
                f"Cannot modify configuration in status {config.status}"
            )

        # Validate new selection
        result = self.validate_configuration(selected_options, config.product_id)

        config.selected_options = selected_options.copy()
        if result.auto_included:
            config.selected_options.extend(result.auto_included)

        config.is_valid = result.is_valid
        config.validation_errors = result.errors
        config.validation_warnings = result.warnings
        config.options_price = self._calculate_options_price(config.selected_options)
        config.total_price = config.base_price + config.options_price
        config.updated_at = datetime.now()

        return config

    def release_configuration(
        self, config_id: str, released_by: str
    ) -> ProductConfiguration:
        """Release a validated configuration."""
        config = self.get_configuration(config_id)
        if not config:
            raise ConfigurationError(f"Configuration {config_id} not found")

        if not config.is_valid:
            raise InvalidConfigurationError(config.validation_errors)

        config.status = "released"
        config.released_at = datetime.now()
        config.released_by = released_by
        config.updated_at = datetime.now()

        return config

    def _calculate_options_price(self, option_ids: list[str]) -> Decimal:
        """Calculate total price for selected options."""
        total = Decimal("0")
        for opt_id in option_ids:
            option = self.get_option(opt_id)
            if option:
                total += option.price_delta
        return total

    # -------------------------------------------------------------------------
    # Effectivity Management
    # -------------------------------------------------------------------------

    def create_effectivity(self, effectivity: Effectivity) -> Effectivity:
        """Create an effectivity record."""
        if not effectivity.id:
            effectivity.id = str(uuid4())
        self._effectivities[effectivity.id] = effectivity
        return effectivity

    def get_effectivity(self, effectivity_id: str) -> Optional[Effectivity]:
        """Get an effectivity by ID."""
        return self._effectivities.get(effectivity_id)

    def list_effectivities(
        self,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        configuration_id: Optional[str] = None,
    ) -> list[Effectivity]:
        """List effectivities with filters."""
        results = []
        for eff in self._effectivities.values():
            if entity_type and eff.entity_type != entity_type:
                continue
            if entity_id and eff.entity_id != entity_id:
                continue
            if configuration_id and eff.configuration_id != configuration_id:
                continue
            results.append(eff)
        return results

    def check_effectivity(
        self,
        entity_type: str,
        entity_id: str,
        as_of_date: Optional[date] = None,
        serial: Optional[str] = None,
        lot: Optional[str] = None,
        unit_id: Optional[str] = None,
    ) -> bool:
        """Check if an entity is effective in the given context."""
        effectivities = self.list_effectivities(
            entity_type=entity_type, entity_id=entity_id
        )

        if not effectivities:
            # No effectivity defined = always effective
            return True

        # At least one effectivity must be valid
        return any(
            eff.is_valid(as_of_date, serial, lot, unit_id) for eff in effectivities
        )

    # -------------------------------------------------------------------------
    # Baseline Management
    # -------------------------------------------------------------------------

    def create_baseline(
        self,
        configuration_id: str,
        name: str,
        version: str,
        baselined_by: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> ConfigurationBaseline:
        """Create a baseline snapshot of a configuration."""
        config = self.get_configuration(configuration_id)
        if not config:
            raise ConfigurationError(f"Configuration {configuration_id} not found")

        if not config.is_valid:
            raise InvalidConfigurationError(config.validation_errors)

        # Capture option details at this point in time
        option_details = []
        for opt_id in config.selected_options:
            option = self.get_option(opt_id)
            if option:
                option_details.append(
                    {
                        "id": option.id,
                        "name": option.name,
                        "code": option.code,
                        "price_delta": str(option.price_delta),
                        "option_type": option.option_type.value,
                        "option_group": option.option_group,
                    }
                )

        baseline = ConfigurationBaseline(
            id=str(uuid4()),
            name=name,
            configuration_id=configuration_id,
            version=version,
            product_id=config.product_id,
            product_number=config.product_number,
            selected_options=config.selected_options.copy(),
            option_details=option_details,
            total_price=config.total_price,
            baselined_by=baselined_by,
            notes=notes,
        )

        # Check for previous baseline and link
        prev_baselines = [
            b
            for b in self._baselines.values()
            if b.configuration_id == configuration_id and b.status == "active"
        ]
        if prev_baselines:
            latest = max(prev_baselines, key=lambda b: b.baseline_date)
            baseline.supersedes_id = latest.id
            latest.superseded_by_id = baseline.id
            latest.status = "superseded"

        self._baselines[baseline.id] = baseline
        return baseline

    def get_baseline(self, baseline_id: str) -> Optional[ConfigurationBaseline]:
        """Get a baseline by ID."""
        return self._baselines.get(baseline_id)

    def list_baselines(
        self,
        configuration_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> list[ConfigurationBaseline]:
        """List baselines with filters."""
        results = []
        for bl in self._baselines.values():
            if configuration_id and bl.configuration_id != configuration_id:
                continue
            if status and bl.status != status:
                continue
            results.append(bl)
        return sorted(results, key=lambda b: b.baseline_date, reverse=True)

    def compare_baselines(
        self, baseline1_id: str, baseline2_id: str
    ) -> dict[str, list]:
        """Compare two baselines and return differences."""
        bl1 = self.get_baseline(baseline1_id)
        bl2 = self.get_baseline(baseline2_id)

        if not bl1 or not bl2:
            raise ConfigurationError("One or both baselines not found")

        set1 = set(bl1.selected_options)
        set2 = set(bl2.selected_options)

        return {
            "added": list(set2 - set1),
            "removed": list(set1 - set2),
            "unchanged": list(set1 & set2),
            "price_delta": bl2.total_price - bl1.total_price,
        }

    # -------------------------------------------------------------------------
    # Configured BOM Resolution
    # -------------------------------------------------------------------------

    def add_configured_bom_item(self, item: ConfiguredBOMItem) -> ConfiguredBOMItem:
        """Add a configured BOM item."""
        if not item.id:
            item.id = str(uuid4())
        self._configured_bom_items[item.id] = item
        return item

    def resolve_bom(
        self,
        bom_id: str,
        selected_options: list[str],
        as_of_date: Optional[date] = None,
    ) -> ResolvedBOM:
        """
        Resolve a BOM for a specific configuration.

        Returns only items that are included for the given option selection.
        """
        selected_set = set(selected_options)
        as_of = as_of_date or date.today()

        included_items = []
        total_cost = Decimal("0")

        for item in self._configured_bom_items.values():
            if item.bom_id != bom_id:
                continue

            # Check configuration inclusion
            if not item.is_included(selected_set):
                continue

            # Check effectivity
            all_effective = True
            for eff in item.effectivities:
                if not eff.is_valid(as_of_date=as_of):
                    all_effective = False
                    break

            if item.effectivities and not all_effective:
                continue

            included_items.append(item)
            # Would calculate cost from part pricing in real implementation

        return ResolvedBOM(
            configuration_id="",  # Would be set from context
            bom_id=bom_id,
            items=included_items,
            total_cost=total_cost,
        )
