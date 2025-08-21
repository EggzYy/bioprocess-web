"""
Orchestrator module.
Main entry point that coordinates all calculations and returns complete results.
"""

import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
import pandas as pd

from .models import (
    ScenarioInput,
    ScenarioResult,
    StrainInput,
    CapacityResult,
    EquipmentResult,
    EconomicsResult,
    OptimizationResult,
    SensitivityResult,
)
from .presets import STRAIN_DB, STRAIN_BATCH_DB, RAW_PRICES
from .capacity import calculate_capacity_deterministic, calculate_capacity_monte_carlo
from .sizing import calculate_equipment_sizing
from .econ import calculate_economics
from .optimizer_enhanced import (
    optimize_with_capacity_enforcement,
)
from .excel import export_to_excel

# Setup logger
logger = logging.getLogger(__name__)


def load_strain_from_database(strain_name: str) -> StrainInput:
    """
    Load strain data from preset database.

    Args:
        strain_name: Name of the strain

    Returns:
        StrainInput model with strain data
    """
    if strain_name not in STRAIN_DB:
        raise ValueError(f"Strain '{strain_name}' not found in database")

    strain_db = STRAIN_DB[strain_name]
    batch_db = STRAIN_BATCH_DB.get(strain_name, {})

    return StrainInput(
        name=strain_name,
        fermentation_time_h=batch_db.get("t_fedbatch_h", 24.0),
        turnaround_time_h=batch_db.get("t_turnaround_h", 9.0),
        downstream_time_h=batch_db.get("t_downstrm_h", 4.0),
        yield_g_per_L=batch_db.get("yield_g_per_L", 10.0),
        media_cost_usd=strain_db.get("media_cost_usd", 100.0),
        cryo_cost_usd=strain_db.get("cryo_cost_usd", 50.0),
        utility_rate_ferm_kw=batch_db.get("utility_rate_ferm_kw", 300),
        utility_rate_cent_kw=batch_db.get("utility_rate_cent_kw", 15),
        utility_rate_lyo_kw=batch_db.get("utility_rate_lyo_kw", 1.5),
        utility_cost_steam=0.0228,
        licensing_fixed_cost_usd=strain_db.get("licensing_fixed_cost_usd", 0.0),
        licensing_royalty_pct=strain_db.get("licensing_royalty_pct", 0.0),
        cv_ferm=batch_db.get("cv_ferm", 0.1),
        cv_turn=batch_db.get("cv_turn", 0.1),
        cv_down=batch_db.get("cv_down", 0.1),
    )


def prepare_scenario(scenario: ScenarioInput) -> ScenarioInput:
    """
    Prepare scenario by loading defaults and validating.

    Args:
        scenario: Input scenario

    Returns:
        Prepared scenario with defaults
    """
    # Load raw prices if not provided
    if not scenario.prices.raw_prices:
        scenario.prices.raw_prices = RAW_PRICES.copy()

    # Ensure strains are properly loaded
    for i, strain in enumerate(scenario.strains):
        if isinstance(strain, str):
            # Load from database if string name provided
            scenario.strains[i] = load_strain_from_database(strain)

    # Set volume options if not provided
    if not scenario.volumes.volume_options_l:
        scenario.volumes.volume_options_l = [scenario.volumes.base_fermenter_vol_l]

    return scenario


def run_capacity_calculation(
    scenario: ScenarioInput, fermenter_volume_l: float, reactors: int, ds_lines: int
) -> Tuple[CapacityResult, Dict[str, float]]:
    """
    Run capacity calculation for given configuration.

    Args:
        scenario: Scenario input
        fermenter_volume_l: Fermenter volume
        reactors: Number of reactors
        ds_lines: Number of DS lines

    Returns:
        Tuple of (capacity_result, batches_per_strain)
    """
    # Update equipment configuration
    scenario.equipment.reactors_total = reactors
    scenario.equipment.ds_lines_total = ds_lines

    # Run capacity calculation
    if scenario.optimization.simulation_type.value == "monte_carlo":
        _, _, capacity_result = calculate_capacity_monte_carlo(
            scenario.strains,
            scenario.equipment,
            fermenter_volume_l,
            n_samples=scenario.optimization.n_monte_carlo_samples,
            working_volume_fraction=scenario.volumes.working_volume_fraction,
        )
    else:
        _, _, capacity_result = calculate_capacity_deterministic(
            scenario.strains,
            scenario.equipment,
            fermenter_volume_l,
            working_volume_fraction=scenario.volumes.working_volume_fraction,
        )

    # Extract batches per strain
    batches_per_strain = {
        strain["name"]: strain.get("good_batches", 0)
        for strain in capacity_result.per_strain
    }

    return capacity_result, batches_per_strain


def run_equipment_sizing(
    scenario: ScenarioInput,
    fermenter_volume_l: float,
    reactors: int,
    ds_lines: int,
    target_tpa: float,
) -> EquipmentResult:
    """
    Run equipment sizing calculations.

    Args:
        scenario: Scenario input
        fermenter_volume_l: Fermenter volume
        reactors: Number of reactors
        ds_lines: Number of DS lines

    Returns:
        EquipmentResult with sizing and costs
    """
    # Convert strains to list of dictionaries with processing properties
    from .presets import get_strain_info

    strain_data = []
    for strain in scenario.strains:
        if isinstance(strain, str):
            # Load from database if string name provided
            strain_info = get_strain_info(strain)
            strain_info["name"] = strain
            strain_data.append(strain_info)
        elif hasattr(strain, "name"):
            # Get strain info from database and merge with any custom properties
            try:
                strain_info = get_strain_info(strain.name)
                strain_info["name"] = strain.name
                # Merge any custom properties from the strain object
                if hasattr(strain, "respiration_type"):
                    strain_info["respiration_type"] = strain.respiration_type
                if hasattr(strain, "requires_tff"):
                    strain_info["requires_tff"] = strain.requires_tff
                if hasattr(strain, "downstream_complexity"):
                    strain_info["downstream_complexity"] = strain.downstream_complexity
                strain_data.append(strain_info)
            except ValueError:
                # Custom strain not in database
                strain_data.append(
                    {
                        "name": strain.name,
                        "respiration_type": getattr(
                            strain, "respiration_type", "aerobic"
                        ),
                        "requires_tff": getattr(strain, "requires_tff", False),
                        "downstream_complexity": getattr(
                            strain, "downstream_complexity", 1.0
                        ),
                    }
                )
        else:
            # Dictionary or other format
            strain_data.append(strain)

    return calculate_equipment_sizing(
        reactors,
        ds_lines,
        fermenter_volume_l,
        strain_data,  # Pass full strain data
        scenario.volumes,
        scenario.capex,
        target_tpa,
    )


def run_economic_analysis(
    scenario: ScenarioInput,
    capacity_result: CapacityResult,
    equipment_result: EquipmentResult,
    batches_per_strain: Dict[str, float],
    fermenter_volume_l: float,
) -> EconomicsResult:
    """
    Run economic analysis.

    Args:
        scenario: Scenario input
        capacity_result: Capacity calculation results
        equipment_result: Equipment sizing results
        batches_per_strain: Batches per strain
        fermenter_volume_l: Fermenter volume

    Returns:
        EconomicsResult with financial metrics
    """
    # If parity_mode, compute exact original-style CAPEX breakdown and pass as override
    capex_override = None
    if getattr(scenario.capex, "parity_mode", False):
        from .sizing import calculate_capex_estimate_original
        total_capex, breakdown = calculate_capex_estimate_original(
            target_tpa=scenario.target_tpa,
            fermenters=equipment_result.counts.get("fermenters", 0),
            ds_lines=equipment_result.counts.get("lyophilizers", 0) or equipment_result.counts.get("ds_lines", 0),
            fermenter_volume_l=fermenter_volume_l,
            licensing_fixed_total=sum(s.licensing_fixed_cost_usd for s in scenario.strains),
        )
        capex_override = breakdown

    return calculate_economics(
        scenario.target_tpa,
        capacity_result.total_annual_kg,
        capacity_result.total_good_batches,
        batches_per_strain,
        scenario.strains,
        fermenter_volume_l,
        equipment_result.equipment_cost,
        scenario.assumptions,
        scenario.labor,
        scenario.capex,
        scenario.opex,
        scenario.prices.product_prices,
        working_volume_fraction=scenario.volumes.working_volume_fraction,
        capex_override=capex_override,
    )


def run_optimization(scenario: ScenarioInput) -> Optional[OptimizationResult]:
    """
    Run optimization if enabled.

    Args:
        scenario: Scenario input

    Returns:
        OptimizationResult or None
    """
    if not scenario.optimize_equipment:
        return None

    # Determine optimization approach based on scenario settings
    volume_options = scenario.volumes.volume_options_l or [
        scenario.volumes.base_fermenter_vol_l
    ]

    logger.info("Starting optimization...")
    logger.info(f"Volume options: {volume_options}")
    logger.info(f"Target TPA: {scenario.target_tpa}")

    # Enforce capacity strictly (align with original behavior)
    best_solution, all_results_df = optimize_with_capacity_enforcement(
        scenario,
        max_reactors=getattr(scenario, "max_reactors", 60),  # Match original
        max_ds_lines=getattr(scenario, "max_ds_lines", 12),  # Match original
        volume_options=volume_options,
        enforce_capacity=True,
        max_allowed_excess=0.2,
    )

    logger.info("Optimization finished.")
    if best_solution:
        tpa = best_solution.get("capacity_kg", 0) / 1000.0
        logger.info(
            f"Best solution found: {tpa:.2f} TPA with {best_solution.get('reactors')} reactors, {best_solution.get('ds_lines')} DS lines, {best_solution.get('fermenter_volume_l')}L fermenters."
        )
    else:
        logger.error("Optimization did not find a feasible solution.")
        return None

    # Create pareto_df from best solution for consistency
    pareto_df = pd.DataFrame([best_solution]) if best_solution else pd.DataFrame()

    return OptimizationResult(
        best_solution=best_solution,
        pareto_front=pareto_df.to_dict("records") if not pareto_df.empty else [],
        n_evaluations=len(all_results_df),
        selected_fermenter_volume=best_solution.get(
            "fermenter_volume_l", scenario.volumes.base_fermenter_vol_l
        ),
        selected_reactors=best_solution.get("reactors", 4),
        selected_ds_lines=best_solution.get("ds_lines", 2),
    )


def run_sensitivity_analysis(
    scenario: ScenarioInput, base_configuration: Dict[str, Any]
) -> Optional[SensitivityResult]:
    """
    Run sensitivity analysis if enabled.

    Args:
        scenario: Scenario input
        base_configuration: Base equipment configuration

    Returns:
        SensitivityResult or None
    """
    if not scenario.sensitivity.enabled:
        return None

    if not scenario.sensitivity.parameters:
        # Default parameters for sensitivity
        scenario.sensitivity.parameters = [
            "discount_rate",
            "tax_rate",
            "electricity_cost",
            "product_price",
            "raw_material_cost",
        ]

    from .optimizer import sensitivity_analysis

    sensitivity_df = sensitivity_analysis(
        scenario,
        base_configuration,
        scenario.sensitivity.parameters,
        scenario.sensitivity.delta_percentage,
    )

    # Create tornado data
    tornado_data = {}
    for param in scenario.sensitivity.parameters:
        param_data = sensitivity_df[sensitivity_df["parameter"] == param]
        if not param_data.empty:
            tornado_data[param] = {
                "down_npv": param_data[param_data["direction"] == "down"]["npv"].values[
                    0
                ],
                "up_npv": param_data[param_data["direction"] == "up"]["npv"].values[0],
                "down_irr": param_data[param_data["direction"] == "down"]["irr"].values[
                    0
                ],
                "up_irr": param_data[param_data["direction"] == "up"]["irr"].values[0],
            }

    return SensitivityResult(
        tornado_data=tornado_data, most_sensitive_parameters=list(tornado_data.keys())
    )


def run_scenario(
    scenario: ScenarioInput,
    optimize: Optional[bool] = None,
    skip_snap_opt: bool = False,
) -> ScenarioResult:
    """
    Main orchestration function to run complete scenario analysis.

    Args:
        scenario: Complete scenario input
        optimize: Override optimization setting (optional)
        skip_snap_opt: If True, do not run snap-to-optimization fallback when under target

    Returns:
        ScenarioResult with all calculations
    """
    start_time = time.time()
    warnings = []
    errors = []

    try:
        # Prepare scenario
        scenario = prepare_scenario(scenario)

        # Override optimization if specified
        if optimize is not None:
            scenario.optimize_equipment = optimize

        optimization_result = None
        if scenario.optimize_equipment:
            optimization_result = run_optimization(scenario)
            if optimization_result and optimization_result.best_solution:
                best = optimization_result.best_solution
                fermenter_volume_l = best.get(
                    "fermenter_volume_l", scenario.volumes.base_fermenter_vol_l
                )
                reactors = best.get("reactors", 4)
                ds_lines = best.get("ds_lines", 2)

                # Check if optimizer missed the target
                tpa_vs_target = best.get("capacity_kg", 0) / (
                    scenario.target_tpa * 1000
                )
                if abs(1 - tpa_vs_target) > 0.05:
                    msg = f"Optimizer best solution ({tpa_vs_target:.2f}x) misses target by >5%."
                    logger.error(msg)
                    errors.append(msg)
            else:
                errors.append(
                    "Optimization failed to find a solution, using default configuration."
                )
                fermenter_volume_l = scenario.volumes.base_fermenter_vol_l
                reactors = scenario.equipment.reactors_total or 4
                ds_lines = scenario.equipment.ds_lines_total or 2
                optimization_result = None
        else:
            fermenter_volume_l = scenario.volumes.base_fermenter_vol_l
            reactors = scenario.equipment.reactors_total or 4
            ds_lines = scenario.equipment.ds_lines_total or 2

        # Run capacity calculation
        capacity_result, batches_per_strain = run_capacity_calculation(
            scenario, fermenter_volume_l, reactors, ds_lines
        )

        # Sanity checks
        prod_ratio = (
            (capacity_result.total_annual_kg / (scenario.target_tpa * 1000.0))
            if scenario.target_tpa > 0
            else 0.0
        )
        if (
            not skip_snap_opt
            and not scenario.optimize_equipment
            and (prod_ratio < 0.95)
        ):
            msg = f"Production is low vs target: {prod_ratio:.2f}x. Consider enabling optimization for a recommendation."
            warnings.append(msg)
            logger.warning(msg)
            # "Snap-to-optimization" fallback
            warnings.append(
                "Running a quick optimization to suggest a better configuration..."
            )
            snap_opt_result = run_optimization(
                scenario.model_copy(update={"optimize_equipment": True})
            )
            if snap_opt_result and snap_opt_result.best_solution:
                best = snap_opt_result.best_solution
                warnings.append(
                    f"Recommendation: Use {best.get('fermenter_volume_l')}L fermenters, {best.get('reactors')} reactors, and {best.get('ds_lines')} DS lines to meet target."
                )

        if prod_ratio < 0.5 or prod_ratio > 1.5:
            msg = f"Production ratio is out of sensible range: {prod_ratio:.2f}x. (Target: 0.5x-1.5x)"
            warnings.append(msg)
            logger.warning(msg)

        # Run equipment sizing and economic analysis
        equipment_result = run_equipment_sizing(
            scenario,
            fermenter_volume_l,
            reactors,
            ds_lines,
            target_tpa=scenario.target_tpa,
        )
        economics_result = run_economic_analysis(
            scenario,
            capacity_result,
            equipment_result,
            batches_per_strain,
            fermenter_volume_l,
        )

        if economics_result.annual_revenue <= 0:
            msg = "Annual revenue is non-positive; check strain prices and product mix mapping."
            errors.append(msg)
            logger.error(msg)

        # Run sensitivity analysis if enabled
        sensitivity_result = None
        if scenario.sensitivity.enabled:
            base_config = {
                "fermenter_volume_l": fermenter_volume_l,
                "reactors": reactors,
                "ds_lines": ds_lines,
            }
            sensitivity_result = run_sensitivity_analysis(scenario, base_config)

        kpis = {
            "npv": economics_result.npv,
            "irr": economics_result.irr,
            "payback_years": economics_result.payback_years,
            "tpa": capacity_result.total_annual_kg / 1000,
            "target_tpa": scenario.target_tpa,
            "capex": economics_result.total_capex,
            "opex": economics_result.total_opex,
            "opex_per_kg": (
                economics_result.total_opex / capacity_result.total_annual_kg
            )
            if capacity_result.total_annual_kg > 0
            else 0,
            "ebitda_margin": economics_result.ebitda_margin,
            "up_utilization": capacity_result.weighted_up_utilization,
            "ds_utilization": capacity_result.weighted_ds_utilization,
            # Parity marker for tests: meets target within enforced policy
            "meets_tpa": capacity_result.total_annual_kg + 1e-6 >= scenario.target_tpa * 1000,
            "production_kg": capacity_result.total_annual_kg,
        }

        result = ScenarioResult(
            scenario_name=scenario.name,
            timestamp=datetime.now().isoformat(),
            kpis=kpis,
            capacity=capacity_result,
            equipment=equipment_result,
            economics=economics_result,
            optimization=optimization_result,
            sensitivity=sensitivity_result,
            warnings=warnings,
            errors=errors,
            calculation_time_s=time.time() - start_time,
        )

        return result

    except Exception as e:
        logger.error(f"Unhandled exception in run_scenario: {e}", exc_info=True)
        errors.append(str(e))

        return ScenarioResult(
            scenario_name=scenario.name,
            timestamp=datetime.now().isoformat(),
            kpis={},
            capacity=CapacityResult(
                per_strain=[],
                total_feasible_batches=0,
                total_good_batches=0,
                total_annual_kg=0,
                weighted_up_utilization=0,
                weighted_ds_utilization=0,
                bottleneck="balanced",
            ),
            equipment=EquipmentResult(
                counts={},
                specifications={},
                equipment_cost=0,
                installation_cost=0,
                utilities_cost=0,
                total_installed_cost=0,
            ),
            economics=EconomicsResult(
                annual_revenue=0,
                raw_materials_cost=0,
                utilities_cost=0,
                labor_cost=0,
                maintenance_cost=0,
                ga_other_cost=0,
                total_opex=0,
                land_cost=0,
                building_cost=0,
                equipment_cost=0,
                contingency=0,
                working_capital=0,
                total_capex=0,
                npv=0,
                irr=0,
                payback_years=float("inf"),
                ebitda_margin=0,
                cash_flows=[],
                licensing_fixed=0,
                licensing_royalty_rate=0,
            ),
            warnings=warnings,
            errors=errors,
            calculation_time_s=time.time() - start_time,
        )


def generate_excel_report(
    result: ScenarioResult, scenario: Optional[ScenarioInput] = None
) -> bytes:
    """
    Generate Excel report from results.

    Args:
        result: Scenario calculation results
        scenario: Original scenario input (optional)

    Returns:
        Excel file as bytes
    """
    return export_to_excel(result, scenario)


def run_batch_scenarios(scenarios: List[ScenarioInput]) -> List[ScenarioResult]:
    """
    Run multiple scenarios in batch.

    Args:
        scenarios: List of scenarios to run

    Returns:
        List of results
    """
    results = []
    for scenario in scenarios:
        result = run_scenario(scenario)
        results.append(result)
    return results
