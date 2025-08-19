"""
Pydantic data models for bioprocess facility design.
Provides comprehensive validation and serialization for all inputs and outputs.
"""

from typing import Dict, List, Optional, Literal, Any
from pydantic import BaseModel, Field, field_validator
from pydantic.config import ConfigDict
from enum import Enum


# Enumerations
class AllocationPolicy(str, Enum):
    """Equipment allocation policies for strains."""

    EQUAL = "equal"
    PROPORTIONAL = "proportional"
    INVERSE_CT = "inverse_ct"


class OptimizationObjective(str, Enum):
    """Optimization objectives."""

    NPV = "npv"
    IRR = "irr"
    CAPEX = "capex"
    OPEX_PER_KG = "opex_per_kg"
    UTILIZATION = "utilization"
    PAYBACK = "payback"


class SimulationType(str, Enum):
    """Simulation types."""

    DETERMINISTIC = "deterministic"
    MONTE_CARLO = "monte_carlo"
    STOCHASTIC = "stochastic"


# Strain Models
class StrainInput(BaseModel):
    """Input model for a bacterial/yeast strain."""

    name: str = Field(..., description="Strain identifier")
    fermentation_time_h: float = Field(
        18.0, gt=0, description="Fed-batch fermentation time (hours)"
    )
    turnaround_time_h: float = Field(
        9.0, gt=0, description="Turnaround time between batches (hours)"
    )
    downstream_time_h: float = Field(
        4.0, gt=0, description="Downstream processing time (hours)"
    )

    # Yield and costs
    yield_g_per_L: float = Field(80.0, gt=0, description="Yield in grams per liter")
    media_cost_usd: float = Field(250.0, ge=0, description="Media cost per batch (USD)")
    cryo_cost_usd: float = Field(
        190.0, ge=0, description="Cryoprotectant cost per batch (USD)"
    )

    # Utility rates (with clear documentation)
    utility_rate_ferm_kw: float = Field(
        450.0, ge=0, description="Total kWh per batch for fermentation"
    )
    utility_rate_cent_kw: float = Field(
        7.5, ge=0, description="Power rate in kW/m³ for centrifugation"
    )
    utility_rate_lyo_kw: float = Field(
        0.15, ge=0, description="Power rate in kW per liter for lyophilization"
    )
    utility_cost_steam: float = Field(
        0.0228, ge=0, description="Steam cost per kg product (USD/kg)"
    )

    # Licensing
    licensing_fixed_cost_usd: float = Field(
        0.0, ge=0, description="One-time licensing fee (USD)"
    )
    licensing_royalty_pct: float = Field(
        0.0, ge=0, le=1, description="Royalty percentage on EBITDA"
    )

    # Monte Carlo parameters
    cv_ferm: Optional[float] = Field(
        0.1, ge=0, le=1, description="CV for fermentation time"
    )
    cv_turn: Optional[float] = Field(
        0.1, ge=0, le=1, description="CV for turnaround time"
    )
    cv_down: Optional[float] = Field(
        0.1, ge=0, le=1, description="CV for downstream time"
    )

    # Pydantic v2 config: ignore unknown fields (e.g., price_per_kg) and keep example
    model_config = ConfigDict(
        extra="ignore",
        json_schema_extra={
            "example": {
                "name": "L. acidophilus",
                "fermentation_time_h": 18.0,
                "turnaround_time_h": 9.0,
                "downstream_time_h": 4.0,
                "yield_g_per_L": 82.87,
                "media_cost_usd": 245.47,
                "cryo_cost_usd": 189.38,
                "utility_rate_ferm_kw": 324,
                "utility_rate_cent_kw": 15,
                "utility_rate_lyo_kw": 1.5,
                "utility_cost_steam": 0.0228,
            }
        },
    )

    @field_validator("yield_g_per_L", mode="before")
    @classmethod
    def map_titer_to_yield(cls, v, info):
        # Allow legacy alias titer_g_per_l
        data = getattr(info, "data", {})
        if v is not None:
            return v
        if isinstance(data, dict) and data.get("titer_g_per_l") not in (None, ""):
            return float(data["titer_g_per_l"])
        return v


# Economic Models
class EconomicAssumptions(BaseModel):
    """Economic assumptions for financial calculations."""

    hours_per_year: float = Field(8760.0, gt=0, description="Operating hours per year")
    upstream_availability: float = Field(
        0.92, gt=0, le=1, description="Upstream equipment availability"
    )
    downstream_availability: float = Field(
        0.90, gt=0, le=1, description="Downstream equipment availability"
    )
    quality_yield: float = Field(0.98, gt=0, le=1, description="Quality yield factor")

    discount_rate: float = Field(
        0.10, ge=0, le=1, description="Discount rate for NPV calculation"
    )
    tax_rate: float = Field(0.25, ge=0, le=1, description="Corporate tax rate")
    variable_opex_share: float = Field(
        0.85, ge=0, le=1, description="Variable OPEX as share of total"
    )
    maintenance_pct_of_equip: float = Field(
        0.09, ge=0, le=1, description="Maintenance as % of equipment cost"
    )
    ga_other_scale_factor: float = Field(10.84, gt=0, description="G&A scaling factor")

    depreciation_years: int = Field(10, gt=0, description="Depreciation period (years)")
    project_lifetime_years: int = Field(
        15, gt=0, description="Project lifetime (years)"
    )


class LaborConfig(BaseModel):
    """Labor configuration and costs."""

    plant_manager_salary: float = Field(
        104000, gt=0, description="Plant manager annual salary (USD)"
    )
    fermentation_specialist_salary: float = Field(
        39000, gt=0, description="Fermentation specialist salary"
    )
    downstream_process_operator_salary: float = Field(
        52000, gt=0, description="DS operator salary"
    )
    general_technician_salary: float = Field(
        32500, gt=0, description="General technician salary"
    )
    qaqc_lab_tech_salary: float = Field(
        39000, gt=0, description="QA/QC lab tech salary"
    )
    maintenance_tech_salary: float = Field(
        39000, gt=0, description="Maintenance tech salary"
    )
    utility_operator_salary: float = Field(
        39000, gt=0, description="Utility operator salary"
    )
    logistics_clerk_salary: float = Field(
        39000, gt=0, description="Logistics clerk salary"
    )
    office_clerk_salary: float = Field(32500, gt=0, description="Office clerk salary")

    # Headcount configuration
    min_fte: int = Field(15, gt=0, description="Minimum FTEs for facility")
    fte_per_tpa: float = Field(
        1.0, ge=0, description="Additional FTEs per TPA above minimum"
    )


class PriceTables(BaseModel):
    """Price tables for raw materials and products."""

    raw_prices: Dict[str, float] = Field(
        default_factory=lambda: {
            "Glucose": 0.22,
            "Dextrose": 0.61,
            "Sucrose": 0.36,
            "Fructose": 3.57,
            "Lactose": 0.93,
            "Molasses": 0.11,
            "Yeast Extract": 1.863,
            "Soy Peptone": 4.50,
            "Tryptone": 42.5,
            "Casein": 8.00,
            "Rye Protein Isolate": 18.00,
            "CSL": 0.85,
            "Monosodium_Glutamate": 1.00,
            "K2HPO4": 1.20,
            "KH2PO4": 1.00,
            "L-cysteine HCl": 26.50,
            "MgSO4x7H2O": 0.18,
            "Arginine": 8.00,
            "FeSO4": 0.15,
            "CaCl2": 1.70,
            "Sodium_Citrate": 0.90,
            "Simethicone": 3.00,
            "Inulin": 5.00,
            "Glycerol": 0.95,
            "Skim Milk": 2.50,
            "Trehalose": 30.00,
            "Sodium Ascorbate": 3.70,
            "Whey Powder": 1.74,
            "Tween_80": 4.00,
            "MnSO4xH2O": 1.5,
            "ZnSO4x7H2O": 1.2,
            "Sodium_Acetate": 1.00,
        },
        description="Raw material prices (USD/kg)",
    )
    product_prices: Dict[str, float] = Field(
        default_factory=lambda: {
            "yogurt": 400,
            "lacto_bifido": 400,
            "bacillus": 400,
            "sacco": 500,
        },
        description="Product sales prices (USD/kg)",
    )

    @field_validator("raw_prices")
    def validate_raw_prices(cls, v):
        # Must provide at least one raw price and all must be non-negative
        if not v:
            raise ValueError("raw_prices cannot be empty")
        for material, price in v.items():
            if price < 0:
                raise ValueError(f"Price for {material} cannot be negative")
        return v


# Equipment Models
class EquipmentConfig(BaseModel):
    """Equipment configuration for capacity calculations."""

    year_hours: float = Field(8760.0, gt=0, description="Operating hours per year")
    reactors_total: Optional[int] = Field(
        None, ge=1, description="Total number of reactors"
    )
    reactors_per_strain: Optional[Dict[str, int]] = Field(
        None, description="Reactors per strain"
    )
    ds_lines_total: Optional[int] = Field(
        None, ge=1, description="Total downstream lines"
    )
    ds_lines_per_strain: Optional[Dict[str, int]] = Field(
        None, description="DS lines per strain"
    )

    upstream_availability: float = Field(
        0.92, gt=0, le=1, description="Upstream availability"
    )
    downstream_availability: float = Field(
        0.90, gt=0, le=1, description="Downstream availability"
    )
    quality_yield: float = Field(0.98, gt=0, le=1, description="Quality yield")

    reactor_allocation_policy: AllocationPolicy = Field(
        AllocationPolicy.INVERSE_CT, description="Reactor allocation policy"
    )
    ds_allocation_policy: AllocationPolicy = Field(
        AllocationPolicy.INVERSE_CT, description="Downstream allocation policy"
    )
    shared_downstream: bool = Field(True, description="Whether downstream is shared")


class VolumePlan(BaseModel):
    """Fermenter volume configuration."""

    base_fermenter_vol_l: float = Field(
        2000, gt=0, description="Base fermenter volume (liters)"
    )
    volume_options_l: Optional[List[float]] = Field(
        None, description="List of volume options to evaluate (liters)"
    )
    working_volume_fraction: float = Field(
        0.8,
        gt=0,
        le=1,
        description="Working volume as fraction of total. Set to 1.0 for legacy validation.",
    )
    seed_fermenter_ratio: float = Field(
        0.125, gt=0, le=1, description="Seed fermenter size ratio"
    )
    media_tank_ratio: float = Field(1.25, gt=0, description="Media tank size ratio")


# CAPEX/OPEX Models
class CapexConfig(BaseModel):
    """Capital expenditure configuration."""

    # Parity mode toggles
    parity_mode: bool = Field(
        True, description="If True, use original CAPEX parity formulas by default"
    )
    building_to_equip_factor: float = Field(
        1.07, ge=0, description="Building cost as multiple of equipment cost (parity mode)"
    )
    land_to_equip_factor: float = Field(
        0.223, ge=0, description="Land cost as multiple of equipment cost (parity mode)"
    )

    land_cost_per_m2: float = Field(
        500, ge=0, description="Land cost per square meter (USD)"
    )
    building_cost_per_m2: float = Field(
        2000, ge=0, description="Building cost per square meter (USD)"
    )

    # Equipment costs
    fermenter_base_cost: float = Field(
        150000, gt=0, description="Base cost for 2000L fermenter"
    )
    fermenter_scale_exponent: float = Field(
        0.6, gt=0, le=1, description="Equipment scaling exponent"
    )
    centrifuge_cost: float = Field(200000, gt=0, description="Centrifuge cost (USD)")
    tff_skid_cost: float = Field(150000, gt=0, description="TFF skid cost (USD)")
    lyophilizer_cost_per_m2: float = Field(
        50000, gt=0, description="Lyophilizer cost per m² (USD)"
    )

    # Factors
    utilities_cost_factor: float = Field(
        0.25, ge=0, le=1, description="Utilities as % of process equipment"
    )
    installation_factor: float = Field(
        0.15, ge=0, le=1, description="Installation as % of equipment"
    )
    contingency_factor: float = Field(
        0.125, ge=0, le=0.5, description="Contingency factor"
    )
    working_capital_months: int = Field(
        3, gt=0, le=12, description="Working capital months"
    )


class OpexConfig(BaseModel):
    """Operating expenditure configuration."""

    electricity_usd_per_kwh: float = Field(
        0.107, gt=0, description="Electricity cost (USD/kWh)"
    )
    steam_usd_per_kg: float = Field(0.0228, gt=0, description="Steam cost (USD/kg)")
    water_usd_per_m3: float = Field(0.002, gt=0, description="Water cost (USD/m³)")
    natural_gas_usd_per_mmbtu: float = Field(
        3.50, gt=0, description="Natural gas cost (USD/MMBtu)"
    )

    raw_materials_markup: float = Field(
        1.0, ge=1, description="Raw materials markup factor"
    )
    utilities_efficiency: float = Field(
        0.85, gt=0, le=1, description="Utilities efficiency factor"
    )


# Optimization Models
class OptimizationConfig(BaseModel):
    """Optimization configuration."""

    enabled: bool = Field(False, description="Whether optimization is enabled")
    simulation_type: SimulationType = Field(
        SimulationType.DETERMINISTIC, description="Simulation type"
    )
    objectives: List[OptimizationObjective] = Field(
        [OptimizationObjective.IRR], description="Optimization objectives"
    )

    # Constraints
    min_tpa: Optional[float] = Field(None, gt=0, description="Minimum TPA constraint")
    max_capex_usd: Optional[float] = Field(
        None, gt=0, description="Maximum CAPEX constraint (USD)"
    )
    min_utilization: Optional[float] = Field(
        None, gt=0, le=1, description="Minimum utilization"
    )

    # Algorithm settings
    max_evaluations: int = Field(100, gt=0, le=10000, description="Maximum evaluations")
    population_size: int = Field(50, gt=0, description="Population size for GA")
    n_generations: int = Field(100, gt=0, description="Number of generations")

    # Monte Carlo settings
    n_monte_carlo_samples: int = Field(
        1000, gt=0, le=10000, description="Monte Carlo samples"
    )
    confidence_level: float = Field(
        0.95, gt=0, le=1, description="Confidence level for statistics"
    )

    # Parallel processing
    n_jobs: int = Field(-1, description="Number of parallel jobs (-1 for all CPUs)")


class SensitivityConfig(BaseModel):
    """Sensitivity analysis configuration."""

    enabled: bool = Field(False, description="Whether sensitivity analysis is enabled")
    parameters: List[str] = Field(
        default_factory=list, description="Parameters to vary in sensitivity analysis"
    )

    # One-at-a-time settings
    delta_percentage: float = Field(
        0.1, gt=0, le=1, description="Percentage change for tornado"
    )

    # Grid search settings
    grid_points: int = Field(
        5, gt=1, le=20, description="Number of grid points per parameter"
    )

    # Monte Carlo sensitivity
    n_samples: int = Field(
        1000, gt=0, le=10000, description="Samples for MC sensitivity"
    )


# Main Scenario Model
class ScenarioInput(BaseModel):
    """Complete scenario input for facility design."""

    name: str = Field(..., description="Scenario name")
    description: Optional[str] = Field(None, description="Scenario description")

    # Core inputs
    target_tpa: float = Field(
        ..., gt=0, description="Target production (tons per annum)"
    )
    strains: List[StrainInput] = Field(
        ..., min_length=1, description="List of strains to produce"
    )

    # Configuration
    assumptions: EconomicAssumptions = Field(default_factory=EconomicAssumptions)
    labor: LaborConfig = Field(default_factory=LaborConfig)
    prices: PriceTables = Field(default_factory=PriceTables)
    equipment: EquipmentConfig = Field(default_factory=EquipmentConfig)
    volumes: VolumePlan = Field(default_factory=VolumePlan)
    capex: CapexConfig = Field(default_factory=CapexConfig)
    opex: OpexConfig = Field(default_factory=OpexConfig)

    # Advanced features
    optimization: OptimizationConfig = Field(default_factory=OptimizationConfig)
    sensitivity: SensitivityConfig = Field(default_factory=SensitivityConfig)

    # Flags
    optimize_equipment: bool = Field(
        True, description="Whether to optimize equipment counts"
    )
    use_multiobjective: bool = Field(
        False, description="Use multi-objective optimization"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Baseline 10 TPA Facility",
                "target_tpa": 10,
                "strains": [
                    {
                        "name": "L. acidophilus",
                        "fermentation_time_h": 18.0,
                        "turnaround_time_h": 9.0,
                        "downstream_time_h": 4.0,
                        "yield_g_per_L": 82.87,
                        "media_cost_usd": 245.47,
                        "cryo_cost_usd": 189.38,
                        "utility_rate_ferm_kw": 324,
                        "utility_rate_cent_kw": 15,
                        "utility_rate_lyo_kw": 1.5,
                    }
                ],
            }
        })


# Output Models
class CapacityResult(BaseModel):
    """Capacity calculation results."""

    per_strain: List[Dict[str, Any]] = Field(
        ..., description="Per-strain capacity details"
    )
    total_feasible_batches: float = Field(
        ..., description="Total feasible batches per year"
    )
    total_good_batches: float = Field(
        ..., description="Total good batches after quality yield"
    )
    total_annual_kg: float = Field(..., description="Total annual production (kg)")

    # Utilization
    weighted_up_utilization: float = Field(
        ..., description="Weighted upstream utilization"
    )
    weighted_ds_utilization: float = Field(
        ..., description="Weighted downstream utilization"
    )
    bottleneck: Literal["upstream", "downstream", "balanced"] = Field(
        ..., description="System bottleneck"
    )

    # Monte Carlo results (if applicable)
    kg_p10: Optional[float] = Field(None, description="10th percentile production (kg)")
    kg_p50: Optional[float] = Field(None, description="50th percentile production (kg)")
    kg_p90: Optional[float] = Field(None, description="90th percentile production (kg)")


class EquipmentResult(BaseModel):
    """Equipment sizing and cost results."""

    counts: Dict[str, int] = Field(..., description="Equipment counts by type")
    specifications: Dict[str, Any] = Field(..., description="Equipment specifications")

    # Costs
    equipment_cost: float = Field(..., description="Total equipment cost (USD)")
    installation_cost: float = Field(..., description="Installation cost (USD)")
    utilities_cost: float = Field(
        ..., description="Utilities infrastructure cost (USD)"
    )
    total_installed_cost: float = Field(..., description="Total installed cost (USD)")


class EconomicsResult(BaseModel):
    """Economic analysis results."""

    # Revenue
    annual_revenue: float = Field(
        ..., description="Annual revenue at steady state (USD)"
    )

    # OPEX
    raw_materials_cost: float = Field(
        ..., description="Annual raw materials cost (USD)"
    )
    utilities_cost: float = Field(..., description="Annual utilities cost (USD)")
    labor_cost: float = Field(..., description="Annual labor cost (USD)")
    maintenance_cost: float = Field(..., description="Annual maintenance cost (USD)")
    ga_other_cost: float = Field(..., description="G&A and other costs (USD)")
    total_opex: float = Field(..., description="Total annual OPEX (USD)")

    # CAPEX
    land_cost: float = Field(..., description="Land cost (USD)")
    building_cost: float = Field(..., description="Building cost (USD)")
    equipment_cost: float = Field(..., description="Equipment cost (USD)")
    contingency: float = Field(..., description="Contingency (USD)")
    working_capital: float = Field(..., description="Working capital (USD)")
    total_capex: float = Field(..., description="Total CAPEX (USD)")

    # Financial metrics
    npv: float = Field(..., description="Net Present Value (USD)")
    irr: float = Field(..., description="Internal Rate of Return")
    payback_years: float = Field(..., description="Payback period (years)")
    ebitda_margin: float = Field(..., description="EBITDA margin at steady state")

    # Cash flows
    cash_flows: List[float] = Field(..., description="Annual cash flows")

    # Licensing
    licensing_fixed: float = Field(0, description="Fixed licensing cost (USD)")
    licensing_royalty_rate: float = Field(0, description="Weighted royalty rate")


class OptimizationResult(BaseModel):
    """Optimization results."""

    best_solution: Dict[str, Any] = Field(..., description="Best solution found")
    pareto_front: Optional[List[Dict[str, Any]]] = Field(
        None, description="Pareto optimal solutions"
    )

    # Metrics
    n_evaluations: int = Field(..., description="Number of evaluations performed")
    convergence_history: Optional[List[float]] = Field(
        None, description="Convergence history"
    )

    # Selected configuration
    selected_fermenter_volume: float = Field(
        ..., description="Selected fermenter volume (L)"
    )
    selected_reactors: int = Field(..., description="Selected number of reactors")
    selected_ds_lines: int = Field(..., description="Selected number of DS lines")


class SensitivityResult(BaseModel):
    """Sensitivity analysis results."""

    tornado_data: Optional[Dict[str, Dict[str, float]]] = Field(
        None, description="Tornado chart data"
    )

    grid_results: Optional[List[Dict[str, Any]]] = Field(
        None, description="Grid search results"
    )

    correlation_matrix: Optional[Dict[str, Dict[str, float]]] = Field(
        None, description="Parameter correlation matrix"
    )

    most_sensitive_parameters: List[str] = Field(
        default_factory=list, description="Parameters ordered by sensitivity"
    )


class ScenarioResult(BaseModel):
    """Complete scenario calculation results."""

    scenario_name: str = Field(..., description="Scenario name")
    timestamp: str = Field(..., description="Calculation timestamp")

    # Key performance indicators
    kpis: Dict[str, float] = Field(..., description="Key performance indicators")

    # Detailed results
    capacity: CapacityResult = Field(..., description="Capacity calculation results")
    equipment: EquipmentResult = Field(..., description="Equipment sizing results")
    economics: EconomicsResult = Field(..., description="Economic analysis results")

    # Optional results
    optimization: Optional[OptimizationResult] = Field(
        None, description="Optimization results"
    )
    sensitivity: Optional[SensitivityResult] = Field(
        None, description="Sensitivity analysis results"
    )

    # Metadata
    warnings: List[str] = Field(
        default_factory=list, description="Calculation warnings"
    )
    errors: List[str] = Field(default_factory=list, description="Calculation errors")
    calculation_time_s: float = Field(..., description="Calculation time in seconds")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "scenario_name": "Baseline 10 TPA",
                "timestamp": "2024-01-15T12:00:00Z",
                "kpis": {
                    "npv": 15000000,
                    "irr": 0.25,
                    "payback_years": 4.5,
                    "tpa": 10.5,
                },
                "capacity": {
                    "total_annual_kg": 10500,
                    "weighted_up_utilization": 0.85,
                    "weighted_ds_utilization": 0.82,
                    "bottleneck": "upstream",
                },
            }
        }
    )
