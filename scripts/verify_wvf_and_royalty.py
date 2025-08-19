#!/usr/bin/env python3
"""
Ad-hoc verification script:
- Confirms working_volume_fraction propagation by comparing capacity at WVF=1.0 vs 0.8
- Triggers sanity checks (production ratio error, revenue <= 0 error)
- Compares weighted royalty rate vs original pricing_integrated_original.py

Run:
  python scripts/verify_wvf_and_royalty.py
"""

import logging
from typing import Dict

from bioprocess.models import (
    ScenarioInput,
    StrainInput,
    EquipmentConfig,
    VolumePlan,
    PriceTables,
)
from bioprocess.orchestrator import run_scenario
from bioprocess.presets import STRAIN_DB, STRAIN_BATCH_DB, RAW_PRICES
from bioprocess.econ import calculate_economics

# Original helper for royalty rate
import sys

sys.path.append("/home/eggzy/Downloads/Project_Hasan")
from pricing_integrated_original import weighted_royalty_rate  # type: ignore

logging.basicConfig(level=logging.INFO)


def build_strain(name: str) -> StrainInput:
    sb = STRAIN_BATCH_DB[name]
    sd = STRAIN_DB.get(name, {})
    return StrainInput(
        name=name,
        fermentation_time_h=sb["t_fedbatch_h"],
        turnaround_time_h=sb.get("t_turnaround_h", 9.0),
        downstream_time_h=sb["t_downstrm_h"],
        yield_g_per_L=sb["yield_g_per_L"],
        media_cost_usd=sd.get("media_cost_usd", 100),
        cryo_cost_usd=sd.get("cryo_cost_usd", 50),
        utility_rate_ferm_kw=sb.get("utility_rate_ferm_kw", 250),
        utility_rate_cent_kw=sb.get("utility_rate_cent_kw", 15),
        utility_rate_lyo_kw=sb.get("utility_rate_lyo_kw", 1.5),
    )


def verify_wvf_effect():
    s = build_strain("L. acidophilus")
    equip = EquipmentConfig(reactors_total=4, ds_lines_total=2)
    prices = PriceTables(raw_prices=RAW_PRICES)
    for wvf in (1.0, 0.8):
        scenario = ScenarioInput(
            name=f"WVF {wvf}",
            target_tpa=10,
            strains=[s],
            equipment=equip,
            volumes=VolumePlan(
                base_fermenter_vol_l=2000,
                volume_options_l=[2000],
                working_volume_fraction=wvf,
            ),
            prices=prices,
            optimize_equipment=False,
        )
        result = run_scenario(scenario)
        tpa = result.kpis.get("tpa", 0.0)
        kg = result.capacity.total_annual_kg
        print(f"WVF={wvf}: tpa={tpa:.3f}, kg={kg:,.1f}")
    print("Expect ~20% drop in kg/Tpa when moving from 1.0 to 0.8 working volume.")


def trigger_sanity_checks():
    # Production ratio error (<0.5x) with small equipment vs large target
    s = build_strain("L. acidophilus")
    equip = EquipmentConfig(reactors_total=2, ds_lines_total=1)
    scenario = ScenarioInput(
        name="Sanity Check - Prod Ratio",
        target_tpa=100,  # Very high target to force low ratio
        strains=[s],
        equipment=equip,
        volumes=VolumePlan(
            base_fermenter_vol_l=2000,
            volume_options_l=[2000],
            working_volume_fraction=0.8,
        ),
        optimize_equipment=False,
    )
    r = run_scenario(scenario)
    print("Sanity (prod ratio) errors:", r.errors)

    # Revenue <= 0 error by removing product prices and using custom strain w/o explicit price
    custom = StrainInput(
        name="CustomNoPrice",
        fermentation_time_h=18.0,
        turnaround_time_h=9.0,
        downstream_time_h=4.0,
        yield_g_per_L=10.0,
        media_cost_usd=0.0,
        cryo_cost_usd=0.0,
        utility_rate_ferm_kw=0.0,
        utility_rate_cent_kw=0.0,
        utility_rate_lyo_kw=0.0,
    )
    equip = EquipmentConfig(reactors_total=1, ds_lines_total=1)
    scenario2 = ScenarioInput(
        name="Sanity Check - Revenue",
        target_tpa=1,
        strains=[custom],
        equipment=equip,
        prices=PriceTables(
            raw_prices=RAW_PRICES, product_prices={}
        ),  # empty product prices
        volumes=VolumePlan(
            base_fermenter_vol_l=2000,
            volume_options_l=[2000],
            working_volume_fraction=0.8,
        ),
        optimize_equipment=False,
    )
    r2 = run_scenario(scenario2)
    print("Sanity (revenue<=0) errors:", r2.errors)


def compare_weighted_royalty():
    strains = ["L. acidophilus", "Bacillus subtilis"]
    s_inputs = [build_strain(n) for n in strains]
    equip = EquipmentConfig(reactors_total=4, ds_lines_total=2)
    # Run minimal capacity to get batches per strain via orchestrator
    from bioprocess.capacity import calculate_capacity_deterministic

    df, totals, cap = calculate_capacity_deterministic(
        s_inputs, equip, fermenter_volume_l=2000, working_volume_fraction=0.8
    )
    batches_per_strain: Dict[str, float] = {
        row["name"]: row.get("good_batches", 0.0) for _, row in df.iterrows()
    }

    # New implementation royalty rate (through calculate_economics)
    from bioprocess.models import (
        EconomicAssumptions,
        CapexConfig,
        OpexConfig,
        LaborConfig,
    )

    econ_res = calculate_economics(
        target_tpa=10.0,
        annual_production_kg=cap.total_annual_kg,
        total_batches=cap.total_good_batches,
        batches_per_strain=batches_per_strain,
        strains=s_inputs,
        fermenter_volume_l=2000,
        equipment_cost=0.0,
        assumptions=EconomicAssumptions(),
        labor_config=LaborConfig(),
        capex_config=CapexConfig(),
        opex_config=OpexConfig(),
        product_prices=PriceTables().product_prices,
        working_volume_fraction=0.8,
    )

    # Original implementation royalty rate
    wr, per_strain = weighted_royalty_rate(
        strains, fermenters=4, ds_lines=2, fermenter_volume_L=2000
    )

    print(f"New royalty rate: {econ_res.licensing_royalty_rate:.6f}")
    print(f"Orig royalty rate: {wr:.6f}")
    print("Per-strain kg (orig):", {k: round(v, 1) for k, v in per_strain.items()})


if __name__ == "__main__":
    print("--- Verify working_volume_fraction effect ---")
    verify_wvf_effect()
    print("\n--- Trigger sanity checks ---")
    trigger_sanity_checks()
    print("\n--- Compare weighted royalty rate ---")
    compare_weighted_royalty()
