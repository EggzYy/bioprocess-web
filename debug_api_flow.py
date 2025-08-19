#!/usr/bin/env python3
"""
Debug script to trace the API data flow and identify where production gets lost.
"""

import json
import sys
from pathlib import Path
from loguru import logger

# Add the parent directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from bioprocess.models import ScenarioInput
from bioprocess.orchestrator import run_scenario, load_strain_from_database
from bioprocess.presets import STRAIN_DB
from api.schemas import RunScenarioRequest


def create_test_scenario():
    """Create a test scenario matching the API structure."""

    # Get strain data from the database
    strain_names = [
        "S. thermophilus",
        "L. delbrueckii subsp. bulgaricus",
        "L. acidophilus",
    ]
    strains = []

    for strain_name in strain_names:
        if strain_name in STRAIN_DB:
            # Use the orchestrator's load function which properly combines STRAIN_DB and STRAIN_BATCH_DB
            strain_input = load_strain_from_database(strain_name)
            strains.append(strain_input)

    # Create scenario
    scenario = ScenarioInput(
        name="Debug Test",
        target_tpa=10,
        strains=strains,
        num_reactors=3,
        optimize_equipment=False,
        volumes={
            "base_fermenter_vol_l": 500,
            "volume_options_l": [500, 1000, 1500, 2000, 3000, 4000, 5000],
        },
        equipment={
            "num_reactors": 3,
            "num_ds_lines": 1,
            "reactor_allocation_policy": "inverse_ct",
            "working_volume_factor": 0.8,
        },
        prices={
            "price_per_unit": 120000,
            "media_cost_usd": 100,
            "utility_base_rate": 0.10,
            "labor_rate": 50000,
            "raw_prices": {
                "electricity": 0.10,
                "water": 0.001,
                "steam": 0.02,
                "natural_gas": 0.005,
            },
        },
        batch={"batch_failure_percent": 10.0, "batch_type": "fixed"},
        economics={
            "discount_rate": 0.1,
            "project_duration_years": 10,
            "capex_installment_factor": 0.15,
            "installation_factor": 0.15,
        },
        sensitivity={"enabled": False},
    )

    return scenario


def test_direct_orchestrator():
    """Test the orchestrator directly."""
    print("\n" + "=" * 80)
    print("Testing orchestrator directly (without API)")
    print("=" * 80)

    scenario = create_test_scenario()

    # Log the input
    logger.info(f"Input scenario: {json.dumps(scenario.dict(), indent=2, default=str)}")

    # Run the scenario
    result = run_scenario(scenario)

    # Log the result
    logger.info(f"Result capacity: {result.capacity}")
    logger.info(f"Result economics: {result.economics}")

    # Extract key metrics
    total_kg = result.capacity.total_annual_kg or 0
    total_tpa = total_kg / 1000

    print("\nDirect orchestrator result:")
    print(f"  Total production: {total_tpa:.2f} TPA")
    print(f"  Total batches: {result.capacity.total_good_batches or 0}")

    # Print per-strain details
    if result.capacity.per_strain:
        print("\n  Per-strain production:")
        for strain_data in result.capacity.per_strain:
            if isinstance(strain_data, dict):
                strain_kg = strain_data.get("annual_kg_good", 0)
                strain_name = strain_data.get("name", "Unknown")
                batch_mass = strain_data.get("batch_mass_kg", 0)
                good_batches = strain_data.get("good_batches", 0)
                ct_up = strain_data.get("ct_up_h", 0)
                reactors = strain_data.get("reactors_assigned", 0)
            else:
                strain_kg = getattr(strain_data, "annual_kg_good", 0)
                strain_name = getattr(strain_data, "name", "Unknown")
                batch_mass = getattr(strain_data, "batch_mass_kg", 0)
                good_batches = getattr(strain_data, "good_batches", 0)
                ct_up = getattr(strain_data, "ct_up_h", 0)
                reactors = getattr(strain_data, "reactors_assigned", 0)
            strain_tpa = strain_kg / 1000
            print(f"    {strain_name}:")
            print(f"      Batch mass: {batch_mass:.2f} kg")
            print(f"      Good batches: {good_batches:.1f}")
            print(f"      Annual production: {strain_tpa:.2f} TPA")
            print(f"      Cycle time: {ct_up:.1f} h")
            print(f"      Reactors assigned: {reactors:.1f}")

    return result


def test_api_request_structure():
    """Test the API request structure."""
    print("\n" + "=" * 80)
    print("Testing API request structure")
    print("=" * 80)

    scenario = create_test_scenario()

    # Create the API request as it would be sent
    request = RunScenarioRequest(scenario=scenario, async_mode=False)

    # Log the request
    logger.info(f"API request: {json.dumps(request.dict(), indent=2, default=str)}")

    # Simulate what the API does
    print("\nSimulating API handler...")

    # This is what happens in the API (from routers.py line 139)
    from bioprocess.presets import RAW_PRICES

    if not request.scenario.prices.raw_prices:
        request.scenario.prices.raw_prices = RAW_PRICES.copy()

    # Run the scenario as the API does
    result = run_scenario(request.scenario)

    # Extract key metrics
    total_kg = result.capacity.total_annual_kg or 0
    total_tpa = total_kg / 1000

    print("\nAPI simulation result:")
    print(f"  Total production: {total_tpa:.2f} TPA")
    print(f"  Total batches: {result.capacity.total_good_batches or 0}")

    # Print per-strain details
    if result.capacity.per_strain:
        print("\n  Per-strain production:")
        for strain_data in result.capacity.per_strain:
            strain_kg = (
                strain_data.get("annual_kg_good", 0)
                if isinstance(strain_data, dict)
                else getattr(strain_data, "annual_kg_good", 0)
            )
            strain_name = (
                strain_data.get("name", "Unknown")
                if isinstance(strain_data, dict)
                else getattr(strain_data, "name", "Unknown")
            )
            strain_tpa = strain_kg / 1000
            print(f"    {strain_name}: {strain_tpa:.2f} TPA")

    return result


def compare_results():
    """Compare direct and API-simulated results."""
    print("\n" + "=" * 80)
    print("COMPARISON TEST")
    print("=" * 80)

    # Test direct orchestrator
    direct_result = test_direct_orchestrator()

    # Test API structure
    api_result = test_api_request_structure()

    # Compare
    direct_tpa = (direct_result.capacity.total_annual_kg or 0) / 1000
    api_tpa = (api_result.capacity.total_annual_kg or 0) / 1000

    print("\n" + "=" * 80)
    print("COMPARISON RESULTS")
    print("=" * 80)
    print(f"Direct orchestrator: {direct_tpa:.2f} TPA")
    print(f"API simulation: {api_tpa:.2f} TPA")
    print(f"Difference: {abs(direct_tpa - api_tpa):.2f} TPA")

    if abs(direct_tpa - api_tpa) < 0.01:
        print("✓ Results match!")
    else:
        print("✗ Results differ!")

        # Show detailed differences
        print("\nDetailed comparison:")
        print(f"  Direct batches: {direct_result.capacity.total_good_batches or 0}")
        print(f"  API batches: {api_result.capacity.total_good_batches or 0}")


if __name__ == "__main__":
    compare_results()
