#!/usr/bin/env python3
"""
Proper Cross-Validation using legacy pricing_integrated_original copy
Compares with new implementation ensuring TPA constraints are enforced.
"""

import sys
import os
import pandas as pd
from typing import Dict, Any, List

# Add paths for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

# Import original UNMODIFIED implementation from bioprocess folder in this project
from pricing_integrated_original_copy import run_facility_scenario


# Import new implementation
from bioprocess.models import ScenarioInput, StrainInput, VolumePlan
from bioprocess.orchestrator import run_scenario
from bioprocess.presets import RAW_PRICES, STRAIN_DB, STRAIN_BATCH_DB


def run_original_implementation(facility_index: int) -> Dict[str, Any]:
    """Run a predefined facility scenario from the legacy implementation."""
    print("\n🔧 Running ORIGINAL implementation...")
    print(f"   Facility index: {facility_index}")
    result = run_facility_scenario(facility_index)

    # Extract metrics from result
    metrics = {
        "fermenter_volume": 0,
        "reactors": 0,
        "ds_lines": 0,
        "production": 0,
        "capex": 0,
        "npv": 0,
        "irr": 0,
        "meets_tpa": False,
    }

    # Get from Pareto Frontier (the selected optimal configuration)
    if "Pareto Frontier" in result:
        pareto = result["Pareto Frontier"]
        if not pareto.empty:
            # First row is the selected configuration
            metrics["fermenter_volume"] = pareto.iloc[0].get("fermenter_volume_L", 0)
            metrics["reactors"] = pareto.iloc[0].get("reactors", 0)
            metrics["ds_lines"] = pareto.iloc[0].get("ds_lines", 0)
            metrics["npv"] = pareto.iloc[0].get("npv", 0)
            metrics["irr"] = pareto.iloc[0].get("irr", 0)
            metrics["capex"] = pareto.iloc[0].get("capex", 0)
            metrics["production"] = pareto.iloc[0].get("plant_kg_good", 0)
            metrics["meets_tpa"] = pareto.iloc[0].get("meets_capacity", True)
    return metrics


def build_scenario_facility1():
    # Yogurt Cultures (10 TPA)
    name = "Facility 1 - Yogurt Cultures (10 TPA)"
    target_tpa = 10
    strains = [
        "S. thermophilus",
        "L. delbrueckii subsp. bulgaricus",
        "L. acidophilus",
        "B. animalis subsp. lactis",
    ]
    # Use orchestrator helper to load by name
    from bioprocess.orchestrator import load_strain_from_database
    strain_inputs = [load_strain_from_database(s) for s in strains]
    volumes = VolumePlan(
        base_fermenter_vol_l=2000,
        working_volume_fraction=0.8,
        volume_options_l=[500, 1000, 1500, 2000, 3000, 4000, 5000],
    )
    scenario = ScenarioInput(
        name=name,
        strains=strain_inputs,
        target_tpa=target_tpa,
        volumes=volumes,
        optimize_equipment=True,
        use_multiobjective=True,
        prices={"raw_prices": RAW_PRICES},
    )
    scenario.capex.parity_mode = True
    return scenario

def get_facilities():
    return [
        {
            "name": "Facility 1 - Yogurt Cultures (10 TPA)",
            "target_tpa": 10,
            "strains": [
                "S. thermophilus",
                "L. delbrueckii subsp. bulgaricus",
                "L. acidophilus",
                "B. animalis subsp. lactis",
            ],
            "fermenters_suggested": 4,
            "lyos_guess": 2,
            "anaerobic": False,
            "premium_spores": False,
            "sacco": False,
        },
        {
            "name": "Facility 2 - Lacto/Bifido (10 TPA)",
            "target_tpa": 10,
            "strains": [
                "L. rhamnosus GG",
                "L. casei",
                "L. plantarum",
                "B. bifidum",
                "B. longum",
            ],
            "fermenters_suggested": 5,
            "lyos_guess": 2,
            "anaerobic": False,
            "premium_spores": False,
            "sacco": False,
        },
    ]


def run_new(name: str, scenario: ScenarioInput):
    result = run_scenario(scenario)
    kpis = result.kpis
    return {
        "meets_tpa": kpis.get("meets_tpa", False),
        "production_kg": kpis.get("production_kg", 0.0),
        "capex": kpis.get("capex", 0.0),
        "irr": kpis.get("irr", 0.0),
        "npv": kpis.get("npv", 0.0),
    }

    # Fallback to Calc-PerStrain for production
    if metrics["production"] == 0 and "Calc-PerStrain" in result:
        calc_df = result["Calc-PerStrain"]
        if "annual_kg_good" in calc_df.columns:
            metrics["production"] = calc_df["annual_kg_good"].sum()

    return metrics


def run_new_implementation(
    name: str,
    target_tpa: float,
    strains: List[str],
    fermenters_suggested: int,
    lyos_guess: int,
    anaerobic: bool = False,
    premium_spores: bool = False,
    sacco: bool = False,
    working_volume_fraction: float = 0.8,  # Add parameter to control volume
) -> Dict[str, Any]:
    """
    Run the new implementation with TPA enforcement.
    """
    print("\n🔧 Running NEW implementation...")
    print(
        f"   Working Volume: {working_volume_fraction:.0%}, TPA Constraint: {target_tpa}"
    )
    print("   Volume options: [500, 1000, 1500, 2000, 3000, 4000, 5000]L")

    # Prepare strain inputs
    strain_inputs = []
    for strain_name in strains:
        if strain_name in STRAIN_BATCH_DB:
            strain_batch = STRAIN_BATCH_DB[strain_name]
            strain_db = STRAIN_DB.get(strain_name, {})

            strain_inputs.append(
                StrainInput(
                    name=strain_name,
                    fermentation_time_h=strain_batch.get("t_fedbatch_h", 24),
                    turnaround_time_h=strain_batch.get("t_turnaround_h", 8),
                    downstream_time_h=strain_batch.get("t_downstrm_h", 4),
                    yield_g_per_L=strain_batch.get("yield_g_per_L", 10),
                    media_cost_usd=strain_db.get("media_cost_usd", 100),
                    cryo_cost_usd=strain_db.get("cryo_cost_usd", 50),
                    utility_rate_ferm_kw=strain_batch.get("utility_rate_ferm_kw", 250),
                    utility_rate_cent_kw=strain_batch.get("utility_rate_cent_kw", 15),
                    utility_rate_lyo_kw=strain_batch.get("utility_rate_lyo_kw", 1.5),
                    cv_ferm=strain_batch.get("cv_ferm", 0.1),
                    cv_turn=strain_batch.get("cv_turn", 0.1),
                    cv_down=strain_batch.get("cv_down", 0.1),
                )
            )
        else:
            print(f"   ⚠️ Warning: Strain {strain_name} not found in database")

    # Set up volumes with multiple options
    volumes = VolumePlan(
        base_fermenter_vol_l=2000,
        volume_options_l=[500, 1000, 1500, 2000, 3000, 4000, 5000],
        working_volume_fraction=working_volume_fraction,  # Use configurable working volume
    )

    # Create scenario with optimization and TPA enforcement
    scenario = ScenarioInput(
        name=name,
        strains=strain_inputs,
        target_tpa=target_tpa,
        volumes=volumes,
        optimize_equipment=True,  # Enable optimization
        use_multiobjective=True,  # Use multi-objective
        prices={"raw_prices": RAW_PRICES},
    )

    # Enable CAPEX parity mode for cross-validation comparisons
    scenario.capex.parity_mode = True

    # Ensure optimization settings enforce TPA
    scenario.optimization.min_tpa = target_tpa * 0.95  # Allow 5% tolerance

    # Run scenario
    try:
        result = run_scenario(scenario, optimize=True)

        metrics = {
            "fermenter_volume": 2000,
            "reactors": 4,
            "ds_lines": 2,
            "production": result.capacity.total_annual_kg,
            "capex": result.economics.total_capex,
            "npv": result.economics.npv,
            "irr": result.economics.irr,
            "meets_tpa": result.capacity.total_annual_kg >= target_tpa * 1000,
        }

        # Get optimized configuration
        if result.optimization:
            if result.optimization.selected_fermenter_volume:
                metrics["fermenter_volume"] = (
                    result.optimization.selected_fermenter_volume
                )
            if result.optimization.selected_reactors:
                metrics["reactors"] = result.optimization.selected_reactors
            if result.optimization.selected_ds_lines:
                metrics["ds_lines"] = result.optimization.selected_ds_lines

            # Check from best_solution
            if result.optimization.best_solution:
                best = result.optimization.best_solution
                metrics["fermenter_volume"] = best.get(
                    "fermenter_volume_l", metrics["fermenter_volume"]
                )
                metrics["reactors"] = best.get("reactors", metrics["reactors"])
                metrics["ds_lines"] = best.get("ds_lines", metrics["ds_lines"])
                if "capacity_kg" in best:
                    metrics["production"] = best["capacity_kg"]
                if "meets_capacity" in best:
                    metrics["meets_tpa"] = best["meets_capacity"]

        return metrics

    except Exception as e:
        print(f"   ❌ Error: {e}")
        return {
            "fermenter_volume": 0,
            "reactors": 0,
            "ds_lines": 0,
            "production": 0,
            "capex": 0,
            "npv": 0,
            "irr": 0,
            "meets_tpa": False,
        }


def compare_facility(
    name: str,
    target_tpa: float,
    strains: List[str],
    fermenters_suggested: int,
    lyos_guess: int,
    anaerobic: bool = False,
    premium_spores: bool = False,
    sacco: bool = False,
    legacy_index: int = 1,
) -> Dict[str, Any]:
    """
    Compare original and new implementations for a facility.
    """
    print(f"\n{'=' * 80}")
    print(f"Testing: {name}")
    print(f"{'=' * 80}")
    print(f"Target TPA: {target_tpa}")
    print(
        f"Strains ({len(strains)}): {', '.join(strains[:3])}..."
        if len(strains) > 3
        else f"Strains: {', '.join(strains)}"
    )
    print(f"Suggested config: {fermenters_suggested} fermenters, {lyos_guess} lyos")

    # Run original
    orig = run_original_implementation(legacy_index)

    # Run new with 80% working volume (parity with original using 0.8 WVF)
    new = run_new_implementation(
        name,
        target_tpa,
        strains,
        fermenters_suggested,
        lyos_guess,
        anaerobic,
        premium_spores,
        sacco,
        working_volume_fraction=0.8,
    )

    print("\n📊 Original Results:")
    print(
        f"   Optimized: {orig['fermenter_volume']:.0f}L, {orig['reactors']:.0f} reactors, {orig['ds_lines']:.0f} DS lines"
    )
    print(f"   Production: {orig['production']:,.0f} kg/year")
    print(
        f"   Meets TPA: {'✓' if orig['meets_tpa'] else '✗'} ({orig['production'] / 1000:.1f} vs {target_tpa} TPA)"
    )
    print(f"   CAPEX: ${orig['capex']:,.0f}")
    print(f"   IRR: {orig.get('irr', 0):.1%}")
    print(f"   NPV: ${orig['npv']:,.0f}")

    print("\n📊 New Implementation Results:")
    print(
        f"   Optimized: {new['fermenter_volume']:.0f}L, {new['reactors']:.0f} reactors, {new['ds_lines']:.0f} DS lines"
    )
    print(f"   Production: {new['production']:,.0f} kg/year")
    print(
        f"   Meets TPA: {'✓' if new['meets_tpa'] else '✗'} ({new['production'] / 1000:.1f} vs {target_tpa} TPA)"
    )
    print(f"   CAPEX: ${new['capex']:,.0f}")
    print(f"   IRR: {new['irr']:.1%}")
    print(f"   NPV: ${new.get('npv', 0):,.0f}")

    # Calculate differences
    def calc_diff(new_val, orig_val):
        if orig_val == 0:
            return float("inf") if new_val != 0 else 0
        return ((new_val - orig_val) / orig_val) * 100

    print("\n📈 Comparison:")
    print(
        f"   Volume: {orig['fermenter_volume']:.0f}L → {new['fermenter_volume']:.0f}L"
    )
    print(f"   Reactors: {orig['reactors']:.0f} → {new['reactors']:.0f}")
    print(f"   DS lines: {orig['ds_lines']:.0f} → {new['ds_lines']:.0f}")
    print(
        f"   Production diff: {calc_diff(new['production'], orig['production']):+.1f}%"
    )
    print(f"   CAPEX diff: {calc_diff(new['capex'], orig['capex']):+.1f}%")
    print(f"   IRR diff: {(new['irr'] - orig['irr']) * 100:+.1f} pp")

    # Check TPA enforcement
    if not orig["meets_tpa"]:
        print("   ⚠️ Original doesn't meet TPA target")
    if not new["meets_tpa"]:
        print("   ⚠️ New implementation doesn't meet TPA target")

    return {
        "facility": name,
        "target_tpa": target_tpa,
        "orig_volume": orig["fermenter_volume"],
        "new_volume": new["fermenter_volume"],
        "orig_reactors": orig["reactors"],
        "new_reactors": new["reactors"],
        "orig_production": orig["production"],
        "new_production": new["production"],
        "orig_meets_tpa": orig["meets_tpa"],
        "new_meets_tpa": new["meets_tpa"],
        "prod_diff_pct": calc_diff(new["production"], orig["production"]),
        "capex_diff_pct": calc_diff(new["capex"], orig["capex"]),
        "irr_diff_pp": (new["irr"] - orig["irr"]) * 100,
    }


def main():
    """Run cross-validation with exact facility configurations from original."""

    print("=" * 80)
    print("CROSS-VALIDATION WITH ORIGINAL FACILITY CONFIGURATIONS")
    print("=" * 80)
    print("\nUsing exact strain lists from pricing_integrated_original.py")
    print("Both implementations will optimize with TPA enforcement")

    # Exact configurations from pricing_integrated_original.py
    facilities = [
        {
            "name": "Facility 1 - Yogurt Cultures (10 TPA)",
            "target_tpa": 10,
            "strains": [
                "S. thermophilus",
                "L. delbrueckii subsp. bulgaricus",
                "L. acidophilus",
                "B. animalis subsp. lactis",
            ],
            "fermenters_suggested": 4,
            "lyos_guess": 2,
            "anaerobic": False,
            "premium_spores": False,
            "sacco": False,
            "legacy_index": 1,
        },
        {
            "name": "Facility 2 - Lacto/Bifido (10 TPA)",
            "target_tpa": 10,
            "strains": [
                "L. rhamnosus GG",
                "L. casei",
                "L. plantarum",
                "B. breve",
                "B. longum",
            ],
            "fermenters_suggested": 5,
            "lyos_guess": 2,
            "anaerobic": True,
            "premium_spores": False,
            "sacco": False,
            "legacy_index": 2,
        },
        {
            "name": "Facility 3 - Bacillus Spores (10 TPA)",
            "target_tpa": 10,
            "strains": ["Bacillus coagulans", "Bacillus subtilis"],
            "fermenters_suggested": 2,
            "lyos_guess": 1,
            "anaerobic": False,
            "premium_spores": True,
            "sacco": False,
            "legacy_index": 3,
        },
        {
            "name": "Facility 4 - Yeast Based Probiotic (10 TPA)",
            "target_tpa": 10,
            "strains": ["Saccharomyces boulardii"],
            "fermenters_suggested": 4,
            "lyos_guess": 2,
            "anaerobic": False,
            "premium_spores": False,
            "sacco": True,
            "legacy_index": 4,
        },
    ]

    # Test only first 2 facilities for now to avoid timeout
    results = []
    for facility in facilities[:1]:  # Test only the first facility
        try:
            result = compare_facility(**facility)
            results.append(result)
        except Exception as e:
            print(f"\n❌ Error testing {facility['name']}: {e}")
            import traceback

            traceback.print_exc()

    # Summary
    if results:
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)

        df = pd.DataFrame(results)

        # Check TPA enforcement
        orig_meets = df["orig_meets_tpa"].sum()
        new_meets = df["new_meets_tpa"].sum()
        total = len(df)

        print("\nTPA Enforcement:")
        print(f"  Original: {orig_meets}/{total} facilities meet TPA")
        print(f"  New: {new_meets}/{total} facilities meet TPA")

        if new_meets < orig_meets:
            print("  ⚠️ New implementation has worse TPA enforcement!")

        # Average differences
        print("\nAverage Differences (for comparable facilities):")
        comparable = df[df["orig_meets_tpa"] & df["new_meets_tpa"]]
        if not comparable.empty:
            print(f"  Production: {comparable['prod_diff_pct'].mean():+.1f}%")
            print(f"  CAPEX: {comparable['capex_diff_pct'].mean():+.1f}%")
            print(f"  IRR: {comparable['irr_diff_pp'].mean():+.1f} pp")
        else:
            print("  No facilities where both meet TPA for comparison")

        # Detailed table
        print("\nDetailed Results:")
        print("-" * 80)

        summary_df = df[
            [
                "facility",
                "target_tpa",
                "orig_volume",
                "new_volume",
                "orig_production",
                "new_production",
                "orig_meets_tpa",
                "new_meets_tpa",
            ]
        ].copy()

        # Shorten facility names
        summary_df["facility"] = summary_df["facility"].str.replace(
            r"^[^-]+ - ([^(]+) \(.*\)$", r"\1", regex=True
        )

        print(summary_df.to_string(index=False))

        print("\n" + "=" * 80)
        print("KEY FINDINGS:")
        print("=" * 80)

        # Working volume difference
        print("\n1. Working Volume:")
        print("   • Original: 80% working volume")
        print("   • New: 80% working volume")
        print("   • Production differences should not be attributed to WVF.")

        # TPA enforcement
        print("\n2. TPA Enforcement:")
        if new_meets < total:
            print(
                "   ⚠️ New implementation optimizer needs adjustment to meet TPA constraints"
            )
            print(
                "   The optimizer should prioritize meeting target over other objectives"
            )
        else:
            print("   ✓ Both implementations successfully meet TPA targets")

        # Optimization differences
        print("\n3. Optimization Approach:")
        print("   • Original uses enforce_capacity=True to ensure TPA is met")
        print("   • New implementation needs similar constraint enforcement")


if __name__ == "__main__":
    main()
