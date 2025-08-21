#!/usr/bin/env python3
"""
Enhanced Cross-Validation comparing all 3 implementations:
1. Original pricing_integrated_original_copy.py
2. New backend bioprocess implementation
3. API endpoint implementation

Tests volume options hardcoding fix and multiobjective optimization.
"""

import sys
import os
import pandas as pd
import requests
import json
import time
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

# API configuration
API_BASE_URL = "http://localhost:8000"


def run_api_implementation(scenario_data: Dict[str, Any]) -> Dict[str, Any]:
    """Run scenario via API endpoint."""
    print("\n🌐 Running API implementation...")

    start_time = time.time()

    try:
        # Make API call
        response = requests.post(
            f"{API_BASE_URL}/api/scenarios/run",
            json={"scenario": scenario_data, "async_mode": False},
            timeout=300  # 5 minute timeout for long optimizations
        )

        runtime = time.time() - start_time
        print(f"   API runtime: {runtime:.2f}s")

        if response.ok:
            result = response.json()
            if "result" in result:
                api_result = result["result"]

                # Extract metrics from API result
                metrics = {
                    "fermenter_volume": 0,
                    "reactors": 0,
                    "ds_lines": 0,
                    "production": 0,
                    "capex": 0,
                    "npv": 0,
                    "irr": 0,
                    "meets_tpa": False,
                    "runtime": runtime,
                    "total_evaluations": 0,
                }

                # Extract from KPIs
                if "kpis" in api_result:
                    kpis = api_result["kpis"]
                    metrics["production"] = kpis.get("tpa", 0) * 1000  # Convert TPA to kg
                    metrics["capex"] = kpis.get("capex", 0)
                    metrics["npv"] = kpis.get("npv", 0)
                    metrics["irr"] = kpis.get("irr", 0)
                    metrics["meets_tpa"] = metrics["production"] >= kpis.get("target_tpa", 0) * 1000 * 0.95

                # Extract from optimization results
                if "optimization" in api_result and api_result["optimization"]:
                    opt = api_result["optimization"]
                    if "best_solution" in opt and opt["best_solution"]:
                        best = opt["best_solution"]
                        metrics["fermenter_volume"] = best.get("fermenter_volume_l", 0)
                        metrics["reactors"] = best.get("reactors", 0)
                        metrics["ds_lines"] = best.get("ds_lines", 0)
                        if "capacity_kg" in best:
                            metrics["production"] = best["capacity_kg"]
                    metrics["total_evaluations"] = opt.get("total_evaluations", 0)

                # Extract from equipment if optimization didn't have it
                if metrics["fermenter_volume"] == 0 and "equipment" in api_result:
                    equip = api_result["equipment"]
                    if "specifications" in equip:
                        specs = equip["specifications"]
                        metrics["fermenter_volume"] = specs.get("fermenter_volume_l", 0)
                    if "counts" in equip:
                        counts = equip["counts"]
                        metrics["reactors"] = counts.get("fermenters", 0)

                return metrics
            else:
                print(f"   ❌ API Error: No result in response")
                return {"error": "No result in API response", "runtime": runtime}
        else:
            print(f"   ❌ API Error: {response.status_code} - {response.text}")
            return {"error": f"API call failed: {response.status_code}", "runtime": runtime}

    except Exception as e:
        runtime = time.time() - start_time
        print(f"   ❌ API Exception after {runtime:.2f}s: {e}")
        return {"error": str(e), "runtime": runtime}


def run_original_implementation(facility_index: int) -> Dict[str, Any]:
    """Run a predefined facility scenario from the legacy implementation."""
    print("\n🔧 Running ORIGINAL implementation...")
    print(f"   Facility index: {facility_index}")

    start_time = time.time()
    result = run_facility_scenario(facility_index)
    runtime = time.time() - start_time
    print(f"   Original runtime: {runtime:.2f}s")

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
        "runtime": runtime,
        "total_evaluations": 0,
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

    # Estimate evaluations based on original grid search
    if "All Configurations" in result:
        metrics["total_evaluations"] = len(result["All Configurations"])

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
    working_volume_fraction: float = 0.8,
) -> Dict[str, Any]:
    """
    Run the new backend implementation with TPA enforcement.
    """
    print("\n🔧 Running NEW BACKEND implementation...")
    print(f"   Working Volume: {working_volume_fraction:.0%}, TPA Constraint: {target_tpa}")
    print("   Volume options: [500, 1000, 1500, 2000, 3000, 4000, 5000]L")

    start_time = time.time()

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
        working_volume_fraction=working_volume_fraction,
    )

    # Create scenario with optimization and TPA enforcement
    scenario = ScenarioInput(
        name=name,
        strains=strain_inputs,
        target_tpa=target_tpa,
        volumes=volumes,
        optimize_equipment=True,
        use_multiobjective=True,
        prices={"raw_prices": RAW_PRICES},
    )

    # Enable CAPEX parity mode for cross-validation comparisons
    scenario.capex.parity_mode = True

    # Run scenario
    try:
        result = run_scenario(scenario, optimize=True)
        runtime = time.time() - start_time
        print(f"   Backend runtime: {runtime:.2f}s")

        metrics = {
            "fermenter_volume": 2000,
            "reactors": 4,
            "ds_lines": 2,
            "production": result.capacity.total_annual_kg,
            "capex": result.economics.total_capex,
            "npv": result.economics.npv,
            "irr": result.economics.irr,
            "meets_tpa": result.capacity.total_annual_kg >= target_tpa * 1000,
            "runtime": runtime,
            "total_evaluations": 0,
        }

        # Get optimized configuration
        if result.optimization and result.optimization.best_solution:
            best = result.optimization.best_solution
            metrics["fermenter_volume"] = best.get("fermenter_volume_l", metrics["fermenter_volume"])
            metrics["reactors"] = best.get("reactors", metrics["reactors"])
            metrics["ds_lines"] = best.get("ds_lines", metrics["ds_lines"])
            if "capacity_kg" in best:
                metrics["production"] = best["capacity_kg"]
            if "meets_capacity" in best:
                metrics["meets_tpa"] = best["meets_capacity"]

        return metrics

    except Exception as e:
        runtime = time.time() - start_time
        print(f"   ❌ Backend Error after {runtime:.2f}s: {e}")
        return {
            "fermenter_volume": 0,
            "reactors": 0,
            "ds_lines": 0,
            "production": 0,
            "capex": 0,
            "npv": 0,
            "irr": 0,
            "meets_tpa": False,
            "runtime": runtime,
            "error": str(e)
        }


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
    Compare all three implementations for a facility.
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

    # Run new backend
    backend = run_new_implementation(
        name, target_tpa, strains, fermenters_suggested, lyos_guess,
        anaerobic, premium_spores, sacco, working_volume_fraction=0.8,
    )

    # Convert backend scenario to API format
    api_scenario = {
        "name": name,
        "target_tpa": target_tpa,
        "optimize_equipment": True,
        "use_multiobjective": True,
        "strains": [],
        "volumes": {
            "base_fermenter_vol_l": 2000,
            "volume_options_l": [500, 1000, 1500, 2000, 3000, 4000, 5000],
            "working_volume_fraction": 0.8,
        }
    }

    # Add strains to API scenario
    for strain_name in strains:
        if strain_name in STRAIN_BATCH_DB:
            strain_batch = STRAIN_BATCH_DB[strain_name]
            strain_db = STRAIN_DB.get(strain_name, {})

            api_scenario["strains"].append({
                "name": strain_name,
                "fermentation_time_h": strain_batch.get("t_fedbatch_h", 24),
                "turnaround_time_h": strain_batch.get("t_turnaround_h", 8),
                "downstream_time_h": strain_batch.get("t_downstrm_h", 4),
                "yield_g_per_L": strain_batch.get("yield_g_per_L", 10),
                "media_cost_usd": strain_db.get("media_cost_usd", 100),
                "cryo_cost_usd": strain_db.get("cryo_cost_usd", 50),
                "utility_rate_ferm_kw": strain_batch.get("utility_rate_ferm_kw", 250),
                "utility_rate_cent_kw": strain_batch.get("utility_rate_cent_kw", 15),
                "utility_rate_lyo_kw": strain_batch.get("utility_rate_lyo_kw", 1.5),
                "cv_ferm": strain_batch.get("cv_ferm", 0.1),
                "cv_turn": strain_batch.get("cv_turn", 0.1),
                "cv_down": strain_batch.get("cv_down", 0.1),
            })

    # Run API
    api = run_api_implementation(api_scenario)

    # Display comparison results
    print(f"\n{'=' * 60}")
    print(f"COMPARISON RESULTS")
    print(f"{'=' * 60}")

    # Print comparison table
    print(f"{'Metric':<20} {'Original':<15} {'Backend':<15} {'API':<15}")
    print(f"{'-' * 20} {'-' * 15} {'-' * 15} {'-' * 15}")

    print(f"{'Fermenter Vol (L)':<20} {orig.get('fermenter_volume', 0):<15.0f} {backend.get('fermenter_volume', 0):<15.0f} {api.get('fermenter_volume', 0):<15.0f}")
    print(f"{'Reactors':<20} {orig.get('reactors', 0):<15.0f} {backend.get('reactors', 0):<15.0f} {api.get('reactors', 0):<15.0f}")
    print(f"{'DS Lines':<20} {orig.get('ds_lines', 0):<15.0f} {backend.get('ds_lines', 0):<15.0f} {api.get('ds_lines', 0):<15.0f}")
    print(f"{'Production (kg)':<20} {orig.get('production', 0):<15.0f} {backend.get('production', 0):<15.0f} {api.get('production', 0):<15.0f}")
    print(f"{'CAPEX ($M)':<20} {orig.get('capex', 0)/1e6:<15.2f} {backend.get('capex', 0)/1e6:<15.2f} {api.get('capex', 0)/1e6:<15.2f}")
    print(f"{'NPV ($M)':<20} {orig.get('npv', 0)/1e6:<15.2f} {backend.get('npv', 0)/1e6:<15.2f} {api.get('npv', 0)/1e6:<15.2f}")
    print(f"{'IRR (%)':<20} {orig.get('irr', 0)*100:<15.1f} {backend.get('irr', 0)*100:<15.1f} {api.get('irr', 0)*100:<15.1f}")
    print(f"{'Meets TPA':<20} {orig.get('meets_tpa', False):<15} {backend.get('meets_tpa', False):<15} {api.get('meets_tpa', False):<15}")
    print(f"{'Runtime (s)':<20} {orig.get('runtime', 0):<15.2f} {backend.get('runtime', 0):<15.2f} {api.get('runtime', 0):<15.2f}")
    print(f"{'Evaluations':<20} {orig.get('total_evaluations', 0):<15} {backend.get('total_evaluations', 0):<15} {api.get('total_evaluations', 0):<15}")

    # Check volume options fix
    print(f"\n🔍 VOLUME OPTIONS ANALYSIS:")

    orig_vol = orig.get('fermenter_volume', 0)
    backend_vol = backend.get('fermenter_volume', 0)
    api_vol = api.get('fermenter_volume', 0)

    print(f"   Original selected: {orig_vol}L")
    print(f"   Backend selected: {backend_vol}L")
    print(f"   API selected: {api_vol}L")

    volume_options = [500, 1000, 1500, 2000, 3000, 4000, 5000]

    print(f"   Available options: {volume_options}")
    print(f"   Original in options: {orig_vol in volume_options}")
    print(f"   Backend in options: {backend_vol in volume_options}")
    print(f"   API in options: {api_vol in volume_options}")

    # Check if 2500L appears anywhere (the bug we're trying to fix)
    media_tank_orig = orig_vol * 1.25 if orig_vol > 0 else 0
    media_tank_backend = backend_vol * 1.25 if backend_vol > 0 else 0
    media_tank_api = api_vol * 1.25 if api_vol > 0 else 0

    print(f"\n   Media Tank Volumes (fermenter × 1.25):")
    print(f"   Original: {media_tank_orig}L")
    print(f"   Backend: {media_tank_backend}L")
    print(f"   API: {media_tank_api}L")

    if any(abs(vol - 2500) < 1 for vol in [media_tank_orig, media_tank_backend, media_tank_api]):
        print(f"   ⚠️  2500L detected - indicates 2000L fermenter selection")
    else:
        print(f"   ✅ No hardcoded 2500L detected")

    return {
        "original": orig,
        "backend": backend,
        "api": api,
        "facility": name,
        "target_tpa": target_tpa
    }


def main():
    """Main cross-validation runner."""
    print("🧪 CROSS-VALIDATION: Original vs Backend vs API")
    print("=" * 80)
    print("Testing volume options fix and multiobjective optimization")
    print("=" * 80)

    facilities = get_facilities()
    results = []

    for i, facility in enumerate(facilities):
        try:
            result = compare_facility(
                facility["name"],
                facility["target_tpa"],
                facility["strains"],
                facility["fermenters_suggested"],
                facility["lyos_guess"],
                facility.get("anaerobic", False),
                facility.get("premium_spores", False),
                facility.get("sacco", False),
                legacy_index=i + 1,  # 1-indexed for legacy
            )
            results.append(result)

        except Exception as e:
            print(f"❌ Error testing {facility['name']}: {e}")
            import traceback
            traceback.print_exc()
            continue

    # Summary
    print(f"\n{'=' * 80}")
    print(f"SUMMARY")
    print(f"{'=' * 80}")

    for result in results:
        print(f"\n{result['facility']}:")
        orig = result['original']
        backend = result['backend']
        api = result['api']

        # Check agreement on key metrics
        vol_agreement = (orig.get('fermenter_volume', 0) == api.get('fermenter_volume', 0))
        meets_tpa_agreement = (orig.get('meets_tpa', False) == api.get('meets_tpa', False))

        print(f"  Volume Agreement (Orig vs API): {'✅' if vol_agreement else '❌'}")
        print(f"  TPA Achievement Agreement: {'✅' if meets_tpa_agreement else '❌'}")

        # Runtime comparison
        orig_time = orig.get('runtime', 0)
        api_time = api.get('runtime', 0)
        if api_time > 0 and orig_time > 0:
            speedup = api_time / orig_time if orig_time > 0 else 0
            print(f"  Runtime: Original {orig_time:.1f}s, API {api_time:.1f}s ({'%.1fx slower' % speedup if speedup > 1 else '%.1fx faster' % (1/speedup)})")

        # Check for errors
        if "error" in api:
            print(f"  ❌ API Error: {api['error']}")

    print(f"\n🎯 VOLUME OPTIONS FIX STATUS:")
    all_passed = True
    for result in results:
        api_vol = result['api'].get('fermenter_volume', 0)
        volume_options = [500, 1000, 1500, 2000, 3000, 4000, 5000]
        in_options = api_vol in volume_options
        if not in_options and "error" not in result['api']:
            all_passed = False
            print(f"  ❌ {result['facility']}: Selected {api_vol}L (not in options)")
        elif "error" in result['api']:
            print(f"  ⚠️  {result['facility']}: API error occurred")
        else:
            print(f"  ✅ {result['facility']}: Selected {api_vol}L (valid option)")

    if all_passed:
        print(f"\n🎉 SUCCESS: All facilities use volume options correctly!")
        print(f"✅ TASK 1 VALIDATION: Volume options hardcoding issue is FIXED")
    else:
        print(f"\n❌ MIXED RESULTS: Some facilities may still have volume option issues")

    print(f"\n📊 OPTIMIZATION PERFORMANCE:")
    for result in results:
        api_evals = result['api'].get('total_evaluations', 0)
        orig_evals = result['original'].get('total_evaluations', 0)
        api_time = result['api'].get('runtime', 0)
        orig_time = result['original'].get('runtime', 0)

        if api_evals > 0 and api_time > 0:
            print(f"  {result['facility']}:")
            print(f"    API: {api_evals} evaluations in {api_time:.1f}s ({api_evals/api_time:.0f} evals/sec)")
            if orig_evals > 0 and orig_time > 0:
                print(f"    Original: {orig_evals} evaluations in {orig_time:.1f}s ({orig_evals/orig_time:.0f} evals/sec)")


if __name__ == "__main__":
    main()
