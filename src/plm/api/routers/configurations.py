"""
Configurations API Router

Product configurations, options, and baselines.
"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from plm.configs import (
    ConfigurationService,
    ConfigurationError,
    InvalidConfigurationError,
    OptionNotFoundError,
    ConfigurationOption,
    ConfigurationType,
    ConfigurationRule,
    RuleType,
)

router = APIRouter()

# Shared service instance (in production, use dependency injection)
_service = ConfigurationService()


# ----- Pydantic Schemas -----


class OptionCreate(BaseModel):
    """Schema for creating an option."""

    name: str
    code: str
    description: str = ""
    option_type: str = "option"
    part_id: Optional[str] = None
    bom_id: Optional[str] = None
    price_delta: float = 0
    option_group: Optional[str] = None
    is_default: bool = False
    sort_order: int = 0


class OptionResponse(BaseModel):
    """Schema for option response."""

    id: str
    name: str
    code: str
    description: str
    option_type: str
    part_id: Optional[str]
    bom_id: Optional[str]
    price_delta: float
    option_group: Optional[str]
    is_default: bool
    sort_order: int
    is_active: bool
    effective_from: Optional[date]
    effective_to: Optional[date]


class RuleCreate(BaseModel):
    """Schema for creating a rule."""

    name: str
    rule_type: str  # requires, excludes, recommends, includes
    source_option_id: str
    target_option_id: str
    message: str = ""
    is_hard: bool = True


class RuleResponse(BaseModel):
    """Schema for rule response."""

    id: str
    name: str
    rule_type: str
    source_option_id: str
    target_option_id: str
    message: str
    is_hard: bool
    is_active: bool


class ConfigurationCreate(BaseModel):
    """Schema for creating a configuration."""

    name: str
    product_id: str
    product_number: str
    selected_options: list[str] = []
    project_id: Optional[str] = None


class ConfigurationUpdate(BaseModel):
    """Schema for updating a configuration."""

    selected_options: list[str]


class ConfigurationResponse(BaseModel):
    """Schema for configuration response."""

    id: str
    name: str
    product_id: str
    product_number: str
    selected_options: list[str]
    is_valid: bool
    validation_errors: list[str]
    validation_warnings: list[str]
    base_price: float
    options_price: float
    total_price: float
    status: str
    project_id: Optional[str]


class BaselineCreate(BaseModel):
    """Schema for creating a baseline."""

    name: str
    version: str
    notes: Optional[str] = None


class BaselineResponse(BaseModel):
    """Schema for baseline response."""

    id: str
    name: str
    configuration_id: str
    version: str
    product_id: str
    product_number: str
    selected_options: list[str]
    total_price: float
    baseline_date: date
    baselined_by: Optional[str]
    status: str
    supersedes_id: Optional[str]
    superseded_by_id: Optional[str]
    notes: Optional[str]


class ValidationRequest(BaseModel):
    """Schema for validation request."""

    selected_options: list[str]
    part_id: Optional[str] = None


class ValidationResponse(BaseModel):
    """Schema for validation response."""

    is_valid: bool
    errors: list[str]
    warnings: list[str]
    auto_included: list[str]


# ----- Option Endpoints -----


@router.get("/options", response_model=list[OptionResponse])
async def list_options(
    part_id: Optional[str] = Query(None),
    option_group: Optional[str] = Query(None),
    option_type: Optional[str] = Query(None),
    is_active: bool = Query(True),
):
    """List configuration options."""
    opt_type = ConfigurationType(option_type) if option_type else None
    options = _service.list_options(
        part_id=part_id,
        option_group=option_group,
        option_type=opt_type,
        is_active=is_active,
    )
    return [_option_to_response(opt) for opt in options]


@router.post("/options", response_model=OptionResponse, status_code=201)
async def create_option(option: OptionCreate):
    """Create a new configuration option."""
    from decimal import Decimal
    from uuid import uuid4

    opt = ConfigurationOption(
        id=str(uuid4()),
        name=option.name,
        code=option.code,
        description=option.description,
        option_type=ConfigurationType(option.option_type),
        part_id=option.part_id,
        bom_id=option.bom_id,
        price_delta=Decimal(str(option.price_delta)),
        option_group=option.option_group,
        is_default=option.is_default,
        sort_order=option.sort_order,
    )
    opt = _service.create_option(opt)
    return _option_to_response(opt)


@router.get("/options/{option_id}", response_model=OptionResponse)
async def get_option(option_id: str):
    """Get an option by ID."""
    option = _service.get_option(option_id)
    if not option:
        raise HTTPException(status_code=404, detail="Option not found")
    return _option_to_response(option)


@router.delete("/options/{option_id}")
async def deactivate_option(option_id: str):
    """Deactivate an option."""
    try:
        _service.deactivate_option(option_id)
        return {"status": "deactivated"}
    except OptionNotFoundError:
        raise HTTPException(status_code=404, detail="Option not found")


@router.get("/option-groups")
async def list_option_groups(part_id: Optional[str] = Query(None)):
    """List distinct option groups."""
    groups = _service.list_option_groups(part_id=part_id)
    return {"groups": groups}


# ----- Rule Endpoints -----


@router.get("/rules", response_model=list[RuleResponse])
async def list_rules(
    source_option_id: Optional[str] = Query(None),
    target_option_id: Optional[str] = Query(None),
    rule_type: Optional[str] = Query(None),
):
    """List configuration rules."""
    r_type = RuleType(rule_type) if rule_type else None
    rules = _service.list_rules(
        source_option_id=source_option_id,
        target_option_id=target_option_id,
        rule_type=r_type,
    )
    return [_rule_to_response(rule) for rule in rules]


@router.post("/rules", response_model=RuleResponse, status_code=201)
async def create_rule(rule: RuleCreate):
    """Create a configuration rule."""
    from uuid import uuid4

    r = ConfigurationRule(
        id=str(uuid4()),
        name=rule.name,
        rule_type=RuleType(rule.rule_type),
        source_option_id=rule.source_option_id,
        target_option_id=rule.target_option_id,
        message=rule.message,
        is_hard=rule.is_hard,
    )
    r = _service.create_rule(r)
    return _rule_to_response(r)


@router.get("/rules/{rule_id}", response_model=RuleResponse)
async def get_rule(rule_id: str):
    """Get a rule by ID."""
    rule = _service.get_rule(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return _rule_to_response(rule)


# ----- Validation Endpoint -----


@router.post("/validate", response_model=ValidationResponse)
async def validate_configuration(request: ValidationRequest):
    """Validate a configuration selection."""
    result = _service.validate_configuration(
        selected_options=request.selected_options,
        part_id=request.part_id,
    )
    return ValidationResponse(
        is_valid=result.is_valid,
        errors=result.errors,
        warnings=result.warnings,
        auto_included=result.auto_included,
    )


@router.get("/available-options", response_model=list[OptionResponse])
async def get_available_options(
    selected: list[str] = Query([]),
    part_id: Optional[str] = Query(None),
):
    """Get options that can still be added to a configuration."""
    options = _service.get_available_options(
        selected_options=selected, part_id=part_id
    )
    return [_option_to_response(opt) for opt in options]


# ----- Configuration Endpoints -----


@router.get("", response_model=list[ConfigurationResponse])
async def list_configurations():
    """List all configurations."""
    configs = list(_service._configurations.values())
    return [_config_to_response(c) for c in configs]


@router.post("", response_model=ConfigurationResponse, status_code=201)
async def create_configuration(
    config: ConfigurationCreate,
    created_by: str = Query("system"),
):
    """Create a new product configuration."""
    try:
        result = _service.create_configuration(
            name=config.name,
            product_id=config.product_id,
            product_number=config.product_number,
            selected_options=config.selected_options,
            project_id=config.project_id,
            created_by=created_by,
        )
        return _config_to_response(result)
    except ConfigurationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{config_id}", response_model=ConfigurationResponse)
async def get_configuration(config_id: str):
    """Get a configuration by ID."""
    config = _service.get_configuration(config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    return _config_to_response(config)


@router.patch("/{config_id}", response_model=ConfigurationResponse)
async def update_configuration(config_id: str, update: ConfigurationUpdate):
    """Update a configuration's selected options."""
    try:
        result = _service.update_configuration(config_id, update.selected_options)
        return _config_to_response(result)
    except ConfigurationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{config_id}/release", response_model=ConfigurationResponse)
async def release_configuration(
    config_id: str,
    released_by: str = Query(...),
):
    """Release a validated configuration."""
    try:
        result = _service.release_configuration(config_id, released_by)
        return _config_to_response(result)
    except InvalidConfigurationError as e:
        raise HTTPException(
            status_code=400,
            detail={"message": "Configuration invalid", "errors": e.errors},
        )
    except ConfigurationError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ----- Baseline Endpoints -----


@router.get("/{config_id}/baselines", response_model=list[BaselineResponse])
async def list_baselines(config_id: str):
    """List baselines for a configuration."""
    baselines = _service.list_baselines(configuration_id=config_id)
    return [_baseline_to_response(bl) for bl in baselines]


@router.post("/{config_id}/baselines", response_model=BaselineResponse, status_code=201)
async def create_baseline(
    config_id: str,
    baseline: BaselineCreate,
    baselined_by: str = Query("system"),
):
    """Create a baseline snapshot of a configuration."""
    try:
        result = _service.create_baseline(
            configuration_id=config_id,
            name=baseline.name,
            version=baseline.version,
            baselined_by=baselined_by,
            notes=baseline.notes,
        )
        return _baseline_to_response(result)
    except InvalidConfigurationError as e:
        raise HTTPException(
            status_code=400,
            detail={"message": "Configuration invalid", "errors": e.errors},
        )
    except ConfigurationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/baselines/{baseline_id}", response_model=BaselineResponse)
async def get_baseline(baseline_id: str):
    """Get a baseline by ID."""
    baseline = _service.get_baseline(baseline_id)
    if not baseline:
        raise HTTPException(status_code=404, detail="Baseline not found")
    return _baseline_to_response(baseline)


@router.get("/baselines/{baseline1_id}/compare/{baseline2_id}")
async def compare_baselines(baseline1_id: str, baseline2_id: str):
    """Compare two baselines."""
    try:
        diff = _service.compare_baselines(baseline1_id, baseline2_id)
        return {
            "added": diff["added"],
            "removed": diff["removed"],
            "unchanged": diff["unchanged"],
            "price_delta": float(diff["price_delta"]),
        }
    except ConfigurationError as e:
        raise HTTPException(status_code=400, detail=str(e))


def _option_to_response(option: ConfigurationOption) -> OptionResponse:
    """Convert option to response."""
    return OptionResponse(
        id=option.id,
        name=option.name,
        code=option.code,
        description=option.description,
        option_type=option.option_type.value,
        part_id=option.part_id,
        bom_id=option.bom_id,
        price_delta=float(option.price_delta),
        option_group=option.option_group,
        is_default=option.is_default,
        sort_order=option.sort_order,
        is_active=option.is_active,
        effective_from=option.effective_from,
        effective_to=option.effective_to,
    )


def _rule_to_response(rule: ConfigurationRule) -> RuleResponse:
    """Convert rule to response."""
    return RuleResponse(
        id=rule.id,
        name=rule.name,
        rule_type=rule.rule_type.value,
        source_option_id=rule.source_option_id,
        target_option_id=rule.target_option_id,
        message=rule.message,
        is_hard=rule.is_hard,
        is_active=rule.is_active,
    )


def _config_to_response(config) -> ConfigurationResponse:
    """Convert configuration to response."""
    return ConfigurationResponse(
        id=config.id,
        name=config.name,
        product_id=config.product_id,
        product_number=config.product_number,
        selected_options=config.selected_options,
        is_valid=config.is_valid,
        validation_errors=config.validation_errors,
        validation_warnings=config.validation_warnings,
        base_price=float(config.base_price),
        options_price=float(config.options_price),
        total_price=float(config.total_price),
        status=config.status,
        project_id=config.project_id,
    )


def _baseline_to_response(baseline) -> BaselineResponse:
    """Convert baseline to response."""
    return BaselineResponse(
        id=baseline.id,
        name=baseline.name,
        configuration_id=baseline.configuration_id,
        version=baseline.version,
        product_id=baseline.product_id,
        product_number=baseline.product_number,
        selected_options=baseline.selected_options,
        total_price=float(baseline.total_price),
        baseline_date=baseline.baseline_date,
        baselined_by=baseline.baselined_by,
        status=baseline.status,
        supersedes_id=baseline.supersedes_id,
        superseded_by_id=baseline.superseded_by_id,
        notes=baseline.notes,
    )
