import pandas as pd
import numpy as np
from math import ceil
import sys

sys.path.append("/mnt/data")
# calculator module created earlier
from fermentation_capacity_calculator import (
    StrainSpec,
    EquipmentConfig,
    calculate_deterministic_capacity,
    monte_carlo_capacity,
)

# ---------- Paths ----------
out1 = "Facility1_Yogurt_Cultures_10TPA_calc.xlsx"
out2 = "Facility2_Lacto_Bifido_10TPA_calc.xlsx"
out3 = "Facility3_Bacillus_Spores_10TPA_calc.xlsx"
out4 = "Facility4_Yeast_Probiotic_10TPA_calc.xlsx"
out5 = "Facility5_ALL_IN_40TPA_calc.xlsx"


# ---------- Global assumptions (2025 USD) ----------
ASSUMPTIONS = {
    "hours_per_year": 8760.0,  # now equals a full calendar year; availability handled explicitly below
    "upstream_availability": 0.92,
    "downstream_availability": 0.90,
    "quality_yield": 0.98,
    "price_yogurt_usd_per_kg": 400,  #
    "price_lacto_bifido_usd_per_kg": 400,  #
    "price_bacillus_usd_per_kg": 400,  #
    "price_sacco_usd_per_kg": 500,  #
    "discount_rate": 0.10,
    "tax_rate": 0.25,
    "variable_opex_share": 0.85,
    "plant_manager_salary": 80000 * 1.3,
    "fermentation_specialist_salary": 30000 * 1.3,
    "downstream_process_operator_salary": 40000 * 1.3,
    "general_technician_salary": 25000 * 1.3,
    "qaqc_lab_tech_salary": 30000 * 1.3,
    "maintenance_tech_salary": 30000 * 1.3,
    "utility_operator_salary": 30000 * 1.3,
    "logistics_clerk_salary": 30000 * 1.3,
    "office_clerk_salary": 25000 * 1.3,
    "maintenance_pct_of_equip": 0.09,
    "ga_other_scale_factor": 460000 / 42445.0,
}

RAW_PRICES = {
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
}


def npv(rate, cashflows):
    return sum(cf / ((1 + rate) ** t) for t, cf in enumerate(cashflows))


def irr(cashflows, guess=0.2, tol=1e-6, maxiter=500):
    """
    Robust IRR:
      * Handles typical negative upfront CF followed by positives
      * Avoids division by zero when r -> -1
      * Uses bisection when a sign change exists; otherwise falls back to damped Newton
      * Returns NaN if no positive or no negative cashflow (IRR undefined)
    """
    import math

    if not any(cf > 0 for cf in cashflows) or not any(cf < 0 for cf in cashflows):
        return float("nan")

    def npv(r):
        total = 0.0
        denom = 1.0
        for t, cf in enumerate(cashflows):
            if t == 0:
                total += cf
            else:
                denom *= 1.0 + r
                if denom <= 0:
                    return float("inf") if cf >= 0 else -float("inf")
                total += cf / denom
        return total

    low = -0.9999
    high = 1.0
    f_low = npv(low)
    f_high = npv(high)
    while (
        math.isfinite(f_low)
        and math.isfinite(f_high)
        and f_low * f_high > 0
        and high < 1e3
    ):
        high *= 2.0
        f_high = npv(high)

    if math.isfinite(f_low) and math.isfinite(f_high) and f_low * f_high <= 0:
        for _ in range(maxiter):
            mid = (low + high) / 2.0
            f_mid = npv(mid)
            if not math.isfinite(f_mid) or abs(f_mid) < tol:
                return mid
            if f_low * f_mid <= 0:
                high, f_high = mid, f_mid
            else:
                low, f_low = mid, f_mid
        return (low + high) / 2.0

    r = guess
    for _ in range(maxiter):
        if r <= -0.9999:
            r = -0.9999 + 1e-6
        f = npv(r)
        try:
            fp = sum(
                -t * cf / ((1.0 + r) ** (t + 1))
                for t, cf in enumerate(cashflows[1:], start=1)
            )
        except ZeroDivisionError:
            fp = float("inf")
        if not math.isfinite(f) or abs(fp) < 1e-12:
            break
        r_new = r - f / fp
        if r_new <= -0.9999 or not math.isfinite(r_new):
            r_new = r - 0.5  # damp away from singularity
        if abs(r_new - r) < tol:
            return r_new
        r = r_new

    return r


# --- Media & Cryo cost DB (kept as-is from user's script) ---
# LICENSING FIELDS ADDED (2025-01):
# - licensing_fixed_cost_usd: One-time fixed fee per strain (affects CAPEX)
# - licensing_royalty_pct: Royalty percentage on EBITDA (e.g., 0.02 = 2%)
STRAIN_DB = {
    "S. thermophilus": {
        "t_fedbatch_h": 14.0,
        "media_cost_usd": RAW_PRICES["Lactose"] * 32
        + RAW_PRICES["Yeast Extract"] * 24
        + RAW_PRICES["K2HPO4"] * 3.2
        + RAW_PRICES["KH2PO4"] * 3.2,
        "cryo_cost_usd": RAW_PRICES["Skim Milk"] * 10.7
        + RAW_PRICES["Trehalose"] * 5.35
        + RAW_PRICES["Sucrose"] * 5.35,
        "licensing_fixed_cost_usd": 0.0,  # One-time licensing fee
        "licensing_royalty_pct": 0.0,  # Royalty on EBITDA
    },
    "L. delbrueckii subsp. bulgaricus": {
        "t_fedbatch_h": 24.0,
        "media_cost_usd": RAW_PRICES["Whey Powder"] * 64
        + RAW_PRICES["Yeast Extract"] * 10
        + RAW_PRICES["Dextrose"] * 20
        + RAW_PRICES["K2HPO4"] * 3.4,
        "cryo_cost_usd": RAW_PRICES["Skim Milk"] * 10.7
        + RAW_PRICES["Sucrose"] * 5.35
        + RAW_PRICES["Soy Peptone"] * 5.35,
        "licensing_fixed_cost_usd": 0.0,  # One-time licensing fee
        "licensing_royalty_pct": 0.0,  # Royalty on EBITDA
    },
    "L. acidophilus": {
        "t_fedbatch_h": 18.0,
        "media_cost_usd": RAW_PRICES["Whey Powder"] * 10 * 1.6
        + RAW_PRICES["Soy Peptone"] * 30 * 1.6
        + RAW_PRICES["Glucose"] * 5 * 1.6
        + RAW_PRICES["Tween_80"] * 1.0 * 1.6
        + RAW_PRICES["MgSO4x7H2O"] * 1.0 * 1.6
        + RAW_PRICES["MnSO4xH2O"] * 0.06 * 1.6
        + RAW_PRICES["ZnSO4x7H2O"] * 0.01 * 1.6,
        "cryo_cost_usd": RAW_PRICES["Skim Milk"] * 10.7
        + RAW_PRICES["Trehalose"] * 5.35
        + RAW_PRICES["Sucrose"] * 5.35
        + RAW_PRICES["Sodium Ascorbate"] * 0.7,
        "licensing_fixed_cost_usd": 100000.0,  # One-time licensing fee
        "licensing_royalty_pct": 0.0,  # Royalty on EBITDA
    },
    "B. animalis subsp. lactis": {
        "t_fedbatch_h": 15.0,
        "media_cost_usd": RAW_PRICES["Yeast Extract"] * 28.8
        + RAW_PRICES["Soy Peptone"] * 28.0
        + RAW_PRICES["Glucose"] * 6.2
        + RAW_PRICES["L-cysteine HCl"] * 2.8
        + RAW_PRICES["FeSO4"] * 0.055,
        "cryo_cost_usd": RAW_PRICES["Skim Milk"] * 15
        + RAW_PRICES["Lactose"] * 5
        + RAW_PRICES["Sucrose"] * 5
        + RAW_PRICES["Sodium Ascorbate"] * 1,
        "licensing_fixed_cost_usd": 100000.0,  # One-time licensing fee
        "licensing_royalty_pct": 0.0,  # Royalty on EBITDA
    },
    "L. rhamnosus GG": {
        "t_fedbatch_h": 22.0,
        "media_cost_usd": RAW_PRICES["Glucose"] * 112.5 * 1.6
        + RAW_PRICES["Molasses"] * 56.25 * 1.6
        + RAW_PRICES["Casein"] * 18.75 * 1.6
        + RAW_PRICES["Yeast Extract"] * 18.75 * 1.6
        + RAW_PRICES["K2HPO4"] * 13.13 * 1.6
        + RAW_PRICES["Tween_80"] * 1.88 * 1.6
        + RAW_PRICES["Simethicone"] * 1.25 * 1.6
        + RAW_PRICES["CaCl2"] * 0.1875 * 1.6
        + RAW_PRICES["MgSO4x7H2O"] * 0.375 * 1.6
        + RAW_PRICES["MnSO4xH2O"] * 0.075 * 1.6,
        "cryo_cost_usd": RAW_PRICES["Skim Milk"] * 10
        + RAW_PRICES["Trehalose"] * 5
        + RAW_PRICES["Sucrose"] * 5,
        "licensing_fixed_cost_usd": 100000.0,  # One-time licensing fee
        "licensing_royalty_pct": 0.0,  # Royalty on EBITDA
    },
    "L. casei": {
        "t_fedbatch_h": 24.0,
        "media_cost_usd": RAW_PRICES["Sucrose"] * 100
        + RAW_PRICES["CSL"] * 50
        + RAW_PRICES["Yeast Extract"] * 10
        + RAW_PRICES["K2HPO4"] * 5
        + RAW_PRICES["KH2PO4"] * 2,
        "cryo_cost_usd": RAW_PRICES["Skim Milk"] * 15 + RAW_PRICES["Sucrose"] * 5,
        "licensing_fixed_cost_usd": 100000.0,  # One-time licensing fee
        "licensing_royalty_pct": 0.0,  # Royalty on EBITDA
    },
    "L. plantarum": {
        "t_fedbatch_h": 12.0,
        "media_cost_usd": RAW_PRICES["Glucose"] * 50
        + RAW_PRICES["Soy Peptone"] * 20
        + RAW_PRICES["K2HPO4"] * 3.2
        + RAW_PRICES["KH2PO4"] * 3.2
        + RAW_PRICES["Sodium_Acetate"] * 5.0 * 1.6
        + RAW_PRICES["Tween_80"] * 0.2 * 1.6
        + RAW_PRICES["MgSO4x7H2O"] * 0.3 * 1.6
        + RAW_PRICES["MnSO4xH2O"] * 0.04 * 1.6,
        "cryo_cost_usd": RAW_PRICES["Skim Milk"] * 10
        + RAW_PRICES["Trehalose"] * 5
        + RAW_PRICES["Sucrose"] * 5,
        "licensing_fixed_cost_usd": 100000.0,  # One-time licensing fee
        "licensing_royalty_pct": 0.0,  # Royalty on EBITDA
    },
    "B. breve": {
        "t_fedbatch_h": 16.0,
        "media_cost_usd": RAW_PRICES["Yeast Extract"] * 28.8
        + RAW_PRICES["Soy Peptone"] * 28.0
        + RAW_PRICES["Glucose"] * 6.2
        + RAW_PRICES["L-cysteine HCl"] * 2.8
        + RAW_PRICES["FeSO4"] * 0.055,
        "cryo_cost_usd": RAW_PRICES["Skim Milk"] * 28
        + RAW_PRICES["Lactose"] * 10
        + RAW_PRICES["Sucrose"] * 10
        + RAW_PRICES["Sodium Ascorbate"] * 2,
        "licensing_fixed_cost_usd": 100000.0,  # One-time licensing fee
        "licensing_royalty_pct": 0.0,  # Royalty on EBITDA
    },
    "B. longum": {
        "t_fedbatch_h": 12.0,
        "media_cost_usd": RAW_PRICES["Yeast Extract"] * 28.8
        + RAW_PRICES["Soy Peptone"] * 28.0
        + RAW_PRICES["Glucose"] * 6.2
        + RAW_PRICES["L-cysteine HCl"] * 2.8
        + RAW_PRICES["FeSO4"] * 0.055
        + RAW_PRICES["MgSO4x7H2O"] * 1.0 * 1.6
        + RAW_PRICES["Sodium_Citrate"] * 1.0 * 1.6,
        "cryo_cost_usd": RAW_PRICES["Skim Milk"] * 25
        + RAW_PRICES["Lactose"] * 10
        + RAW_PRICES["Sucrose"] * 10
        + RAW_PRICES["Sodium Ascorbate"] * 1.5,
        "licensing_fixed_cost_usd": 100000.0,  # One-time licensing fee
        "licensing_royalty_pct": 0.0,  # Royalty on EBITDA
    },
    "Bacillus coagulans": {
        "t_fedbatch_h": 36.0,
        "media_cost_usd": RAW_PRICES["Glucose"] * 32
        + RAW_PRICES["Soy Peptone"] * 20
        + RAW_PRICES["K2HPO4"] * 3.2
        + RAW_PRICES["KH2PO4"] * 3.2,
        "cryo_cost_usd": RAW_PRICES["Skim Milk"] * 3 + RAW_PRICES["Sucrose"] * 3,
        "licensing_fixed_cost_usd": 100000.0,  # One-time licensing fee
        "licensing_royalty_pct": 0.0,  # Royalty on EBITDA
    },
    "Bacillus subtilis": {
        "t_fedbatch_h": 30.0,
        "media_cost_usd": (
            RAW_PRICES["Glucose"] * 20
            + RAW_PRICES["Soy Peptone"] * 20
            + RAW_PRICES["K2HPO4"] * 3.2
            + RAW_PRICES["MnSO4xH2O"] * 0.1
        )
        * 1.6,
        "cryo_cost_usd": RAW_PRICES["Skim Milk"] * 3 + RAW_PRICES["Sucrose"] * 3,
        "licensing_fixed_cost_usd": 100000.0,  # One-time licensing fee
        "licensing_royalty_pct": 0.0,  # Royalty on EBITDA
    },
    "Saccharomyces boulardii": {
        "t_fedbatch_h": 31.0,
        "media_cost_usd": RAW_PRICES["Glucose"] * 400
        + RAW_PRICES["Yeast Extract"] * 12
        + RAW_PRICES["K2HPO4"] * 4
        + RAW_PRICES["MgSO4x7H2O"] * 1.33,
        "cryo_cost_usd": RAW_PRICES["Skim Milk"] * 10
        + RAW_PRICES["Trehalose"] * 5
        + RAW_PRICES["Sucrose"] * 5
        + RAW_PRICES["Sodium Ascorbate"] * 1,
        "licensing_fixed_cost_usd": 100000.0,  # One-time licensing fee
        "licensing_royalty_pct": 0.0,  # Royalty on EBITDA
    },
}

# --- Batch-time DB with turnaround and downstream times ---
# IMPORTANT: Utility rate units documentation (Fix reference: 2025-01)
#
# RATIONALE: Historical legacy units from pilot scale data led to inconsistent scaling.
# This documentation clarifies the actual units to prevent future calculation errors:
#
# - utility_rate_ferm_kw: Total kWh per batch for fermentation (NOT a rate)
#   Legacy units stored as total energy = base_rate × fermentation_time_h
#   Example: 18 kW × 14 h = 252 kWh total per batch
#   DO NOT multiply by time again when computing costs
#
# - utility_rate_cent_kw: Power rate in kW per m³ for centrifugation
#   Energy per batch = utility_rate_cent_kw × downstream_time_h × (fermenter_volume_L/1000)
#   Must scale by both downstream processing time AND fermenter volume in m³
#
# - utility_rate_lyo_kw: Power rate in kW per (0.15 × fermenter volume in liter) for lyophilization
#   Energy per batch = utility_rate_lyo_kw × downstream_time_h × (fermenter_volume_L × 0.15)
#   The 0.15 factor represents the concentrated fraction after centrifugation
#   Must scale by downstream time AND 15% of fermenter volume in liter
#
STRAIN_BATCH_DB = {
    "S. thermophilus": {
        "t_fedbatch_h": 14.0,
        "t_turnaround_h": 9.0,
        "t_downstrm_h": 4.0,
        "cv_ferm": 0.1,
        "cv_turn": 0.1,
        "cv_down": 0.1,
        "yield_g_per_L": 3.0,
        "utility_rate_ferm_kw": 18
        * 14,  # Total kWh per batch (pre-computed, NOT a rate)
        "utility_rate_cent_kw": 15,  # kW/m³ rate - multiply by time AND volume
        "utility_rate_lyo_kw": 1.5,  # kW per liter of concentrate - multiply by time AND volume
        "price_yogurt_usd_per_kg": 400,
    },
    "L. delbrueckii subsp. bulgaricus": {
        "t_fedbatch_h": 24.0,
        "t_turnaround_h": 9.0,
        "t_downstrm_h": 4.0,
        "cv_ferm": 0.1,
        "cv_turn": 0.1,
        "cv_down": 0.1,
        "yield_g_per_L": 6.08,
        "utility_rate_ferm_kw": 18
        * 24,  # Total kWh per batch (pre-computed, NOT a rate)
        "utility_rate_cent_kw": 15,  # kW/m³ rate - multiply by time AND volume
        "utility_rate_lyo_kw": 1.5,  # kW per liter of concentrate - multiply by time AND volume
        "price_yogurt_usd_per_kg": 400,
    },
    "L. acidophilus": {
        "t_fedbatch_h": 18.0,
        "t_turnaround_h": 9.0,
        "t_downstrm_h": 4.0,
        "cv_ferm": 0.1,
        "cv_turn": 0.1,
        "cv_down": 0.1,
        "yield_g_per_L": 82.87,
        "utility_rate_ferm_kw": 18
        * 18,  # Total kWh per batch (pre-computed, NOT a rate)
        "utility_rate_cent_kw": 15,  # kW/m³ rate - multiply by time AND volume
        "utility_rate_lyo_kw": 1.5,  # kW per liter of concentrate - multiply by time AND volume
        "price_yogurt_usd_per_kg": 400,
    },
    "B. animalis subsp. lactis": {
        "t_fedbatch_h": 15.0,
        "t_turnaround_h": 9.0,
        "t_downstrm_h": 4.0,
        "cv_ferm": 0.1,
        "cv_turn": 0.1,
        "cv_down": 0.1,
        "yield_g_per_L": 34.1,
        "utility_rate_ferm_kw": 18
        * 15,  # Total kWh per batch (pre-computed, NOT a rate)
        "utility_rate_cent_kw": 15,  # kW/m³ rate - multiply by time AND volume
        "utility_rate_lyo_kw": 1.5,  # kW per liter of concentrate - multiply by time AND volume
        "price_yogurt_usd_per_kg": 400,
    },
    "L. rhamnosus GG": {
        "t_fedbatch_h": 22.0,
        "t_turnaround_h": 9.0,
        "t_downstrm_h": 4.0,
        "cv_ferm": 0.1,
        "cv_turn": 0.1,
        "cv_down": 0.1,
        "yield_g_per_L": 63.5,
        "utility_rate_ferm_kw": 18
        * 22,  # Total kWh per batch (pre-computed, NOT a rate)
        "utility_rate_cent_kw": 15,  # kW/m³ rate - multiply by time AND volume
        "utility_rate_lyo_kw": 1.5,  # kW per liter of concentrate - multiply by time AND volume
        "price_lacto_bifido_usd_per_kg": 400,
    },
    "L. casei": {
        "t_fedbatch_h": 24.0,
        "t_turnaround_h": 9.0,
        "t_downstrm_h": 4.0,
        "cv_ferm": 0.1,
        "cv_turn": 0.1,
        "cv_down": 0.1,
        "yield_g_per_L": 5.56,
        "utility_rate_ferm_kw": 18
        * 24,  # Total kWh per batch (pre-computed, NOT a rate)
        "utility_rate_cent_kw": 15,  # kW/m³ rate - multiply by time AND volume
        "utility_rate_lyo_kw": 1.5,  # kW per liter of concentrate - multiply by time AND volume
        "price_lacto_bifido_usd_per_kg": 400,
    },
    "L. plantarum": {
        "t_fedbatch_h": 12.0,
        "t_turnaround_h": 9.0,
        "t_downstrm_h": 4.0,
        "cv_ferm": 0.1,
        "cv_turn": 0.1,
        "cv_down": 0.1,
        "yield_g_per_L": 16.02,
        "utility_rate_ferm_kw": 18
        * 12,  # Total kWh per batch (pre-computed, NOT a rate)
        "utility_rate_cent_kw": 15,  # kW/m³ rate - multiply by time AND volume
        "utility_rate_lyo_kw": 1.5,  # kW per liter of concentrate - multiply by time AND volume
        "price_lacto_bifido_usd_per_kg": 400,
    },
    "B. breve": {
        "t_fedbatch_h": 16.0,
        "t_turnaround_h": 9.0,
        "t_downstrm_h": 4.0,
        "cv_ferm": 0.1,
        "cv_turn": 0.1,
        "cv_down": 0.1,
        "yield_g_per_L": 19.44,
        "utility_rate_ferm_kw": 18
        * 16,  # Total kWh per batch (pre-computed, NOT a rate)
        "utility_rate_cent_kw": 15,  # kW/m³ rate - multiply by time AND volume
        "utility_rate_lyo_kw": 1.5,  # kW per liter of concentrate - multiply by time AND volume
        "price_lacto_bifido_usd_per_kg": 400,
    },
    "B. longum": {
        "t_fedbatch_h": 12.0,
        "t_turnaround_h": 9.0,
        "t_downstrm_h": 4.0,
        "cv_ferm": 0.1,
        "cv_turn": 0.1,
        "cv_down": 0.1,
        "yield_g_per_L": 22.18,
        "utility_rate_ferm_kw": 18
        * 12,  # Total kWh per batch (pre-computed, NOT a rate)
        "utility_rate_cent_kw": 15,  # kW/m³ rate - multiply by time AND volume
        "utility_rate_lyo_kw": 1.5,  # kW per liter of concentrate - multiply by time AND volume
        "price_lacto_bifido_usd_per_kg": 400,
    },
    "Bacillus coagulans": {
        "t_fedbatch_h": 36.0,
        "t_turnaround_h": 9.0,
        "t_downstrm_h": 4.0,
        "cv_ferm": 0.1,
        "cv_turn": 0.1,
        "cv_down": 0.1,
        "yield_g_per_L": 30.00,
        "utility_rate_ferm_kw": 18
        * 36,  # Total kWh per batch (pre-computed, NOT a rate)
        "utility_rate_cent_kw": 15,  # kW/m³ rate - multiply by time AND volume
        "utility_rate_lyo_kw": 1.5,  # kW per liter of concentrate - multiply by time AND volume
        "price_bacillus_usd_per_kg": 400,
    },
    "Bacillus subtilis": {
        "t_fedbatch_h": 30.0,
        "t_turnaround_h": 9.0,
        "t_downstrm_h": 4.0,
        "cv_ferm": 0.1,
        "cv_turn": 0.1,
        "cv_down": 0.1,
        "yield_g_per_L": 88.00,
        "utility_rate_ferm_kw": 18
        * 30,  # Total kWh per batch (pre-computed, NOT a rate)
        "utility_rate_cent_kw": 15,  # kW/m³ rate - multiply by time AND volume
        "utility_rate_lyo_kw": 1.5,  # kW per liter of concentrate - multiply by time AND volume
        "price_bacillus_usd_per_kg": 400,
    },
    "Saccharomyces boulardii": {
        "t_fedbatch_h": 31.0,
        "t_turnaround_h": 9.0,
        "t_downstrm_h": 4.0,
        "cv_ferm": 0.1,
        "cv_turn": 0.1,
        "cv_down": 0.1,
        "yield_g_per_L": 32.09,
        "utility_rate_ferm_kw": 18
        * 31,  # Total kWh per batch (pre-computed, NOT a rate)
        "utility_rate_cent_kw": 15,  # kW/m³ rate - multiply by time AND volume
        "utility_rate_lyo_kw": 1.5,  # kW per liter of concentrate - multiply by time AND volume
        "price_sacco_usd_per_kg": 500,
    },
}


# ---------------- Helpers ----------------
def build_strainspecs(strain_names, fermenter_volume_L=2000):
    specs = []
    for s in strain_names:
        d = STRAIN_BATCH_DB[s]
        specs.append(
            StrainSpec(
                name=s,
                fermentation_time_h=d["t_fedbatch_h"],
                turnaround_time_h=d["t_turnaround_h"],
                downstream_time_h=d["t_downstrm_h"],
                batch_mass_kg=d["yield_g_per_L"] * fermenter_volume_L / 1000 * 0.8,
                utility_rate_ferm_kw=d["utility_rate_ferm_kw"],
                utility_rate_cent_kw=d["utility_rate_cent_kw"],
                utility_rate_lyo_kw=d["utility_rate_lyo_kw"],
                utility_cost_steam=0.0228,
            )
        )
    return specs


def capacity_given_counts(strain_names, reactors, ds_lines, fermenter_volume_L=2000):
    specs = build_strainspecs(strain_names, fermenter_volume_L)
    cfg = EquipmentConfig(
        year_hours=ASSUMPTIONS["hours_per_year"],
        reactors_total=reactors,
        ds_lines_total=ds_lines,
        upstream_availability=ASSUMPTIONS["upstream_availability"],
        downstream_availability=ASSUMPTIONS["downstream_availability"],
        quality_yield=ASSUMPTIONS["quality_yield"],
    )
    df, totals = calculate_deterministic_capacity(
        specs,
        cfg,
        reactor_allocation_policy="inverse_ct",
        ds_allocation_policy="inverse_ct",
    )
    # Add convenient plant-level metrics
    plant_batches_feasible = totals["total_feasible_batches"]
    plant_batches_good = totals["total_good_batches"]
    plant_kg_good = totals.get(
        "total_annual_kg_good", 0.0
    )  # Should always be provided by calculator
    per_reactor = plant_batches_feasible / max(reactors, 1)
    per_ds_line = plant_batches_feasible / max(ds_lines, 1)
    return (
        df,
        totals,
        {
            "plant_batches_feasible": plant_batches_feasible,
            "plant_batches_good": plant_batches_good,
            "plant_kg_good": plant_kg_good,
            "batches_per_fermenter_effective": per_reactor,
            "batches_per_ds_line_effective": per_ds_line,
        },
    )


# ---------------- Licensing Helper Functions ----------------
def licensing_fixed_total(strain_names):
    """Calculate total fixed licensing costs for selected strains.

    Args:
        strain_names: List of strain names

    Returns:
        float: Sum of all fixed licensing costs (one-time CAPEX)
    """
    return sum(STRAIN_DB[s].get("licensing_fixed_cost_usd", 0.0) for s in strain_names)


def weighted_royalty_rate(strain_names, fermenters, ds_lines, fermenter_volume_L):
    """Calculate production-weighted average royalty rate across strains.

    Uses actual capacity allocation to determine per-strain production volumes,
    then computes weighted average royalty rate based on production proportions.

    Args:
        strain_names: List of strain names
        fermenters: Number of fermenters/reactors
        ds_lines: Number of downstream lines
        fermenter_volume_L: Fermenter volume in liters

    Returns:
        tuple: (weighted_royalty_rate, per_strain_kg_dict)
            - weighted_royalty_rate: Production-weighted average royalty percentage
            - per_strain_kg_dict: Dictionary mapping strain names to annual production in kg
    """
    # Get actual strain batch allocations from capacity calculation
    specs = build_strainspecs(strain_names, fermenter_volume_L)
    cfg = EquipmentConfig(
        year_hours=ASSUMPTIONS["hours_per_year"],
        reactors_total=fermenters,
        ds_lines_total=ds_lines,
        upstream_availability=ASSUMPTIONS["upstream_availability"],
        downstream_availability=ASSUMPTIONS["downstream_availability"],
        quality_yield=ASSUMPTIONS["quality_yield"],
    )
    df_det, _ = calculate_deterministic_capacity(
        specs,
        cfg,
        reactor_allocation_policy="inverse_ct",
        ds_allocation_policy="inverse_ct",
    )

    # Calculate production volumes and weighted royalty
    working_volume_L = fermenter_volume_L * 0.8  # 80% working volume
    per_strain_kg = {}
    weighted_sum = 0.0
    total_kg = 0.0

    for _, row in df_det.iterrows():
        strain_name = row["name"]
        good_batches = row["good_batches"]

        # Get yield for this strain
        yield_g_per_L = STRAIN_BATCH_DB[strain_name]["yield_g_per_L"]
        kg_per_batch = yield_g_per_L * working_volume_L / 1000.0

        # Calculate annual production for this strain
        annual_kg = good_batches * kg_per_batch
        per_strain_kg[strain_name] = annual_kg

        # Get royalty rate for this strain (default to 0 if not specified)
        royalty_pct = STRAIN_DB[strain_name].get("licensing_royalty_pct", 0.0)

        # Add to weighted sum
        weighted_sum += annual_kg * royalty_pct
        total_kg += annual_kg

    # Calculate weighted average royalty rate (avoid division by zero)
    weighted_rate = weighted_sum / total_kg if total_kg > 0 else 0.0

    return weighted_rate, per_strain_kg


def capex_estimate_2(
    target_tpa,
    fermenters,
    ds_lines,
    fermenter_volume_L=2000,
    licensing_fixed_total_usd=0.0,
):
    """Calculate CAPEX including licensing fixed costs.

    Args:
        target_tpa: Target tons per annum
        fermenters: Number of fermenters
        ds_lines: Number of downstream lines
        fermenter_volume_L: Fermenter volume in liters
        licensing_fixed_total_usd: Total one-time licensing fees for all strains

    Returns:
        tuple: (total_capex, breakdown_dict)
    """
    # Map DS lines ~ lyophilizer trains (conservative)
    lyos_needed = max(2, ds_lines)
    centrifuges = ceil(lyos_needed * 0.4)
    tff_skids = ceil(lyos_needed * 0.4)

    # Scale fermenter cost with volume using six-tenths rule
    base_volume = 2000  # Base case volume in liters
    base_fermenter_cost = 150000  # Base cost for 2000L fermenter
    volume_scale_factor = (fermenter_volume_L / base_volume) ** 0.6
    facilityArea = 1000 + (fermenters * 500) * volume_scale_factor
    land_cost = 250 * facilityArea  # Clean side 2000 unclean 500
    buildingCost = (
        500 * 500
        + 500 * 2000 * volume_scale_factor
        + 2000 * (fermenters * 500 * volume_scale_factor)
    )  # Clean side 2000 unclean 500

    fermenterCost = fermenters * base_fermenter_cost * volume_scale_factor

    seedFermenterCost = (
        (max(2, ceil(fermenters * 0.7)) + 1) * 50000 * volume_scale_factor
    )
    mediatankCost = (
        ceil(fermenters * 4 / 7) * 75000 * volume_scale_factor
    )  # Media tanks scale with fermenter volume
    lyophilizerCost = max(1, ds_lines) * 400000 * volume_scale_factor
    centrifugeCost = centrifuges * 120000 * volume_scale_factor
    tffCost = tff_skids * 100000 * volume_scale_factor
    millblendcontaindetransferCost = max(1, ceil(tff_skids * 0.5)) * 125000

    utilitySystemsCost = max(1, ceil(tff_skids * 0.5)) * (
        100000 + 150000 + 400000 + 120000 + 250000
    )  # AutoClave, Purified Water, Water for Injection, Clean Steam, CIP

    qclabeqipment = 180000 / 20000 * target_tpa * 1000

    # automation = 750000+fermenters*80000 # ÇOK PAHALLI
    totalEquipmentCost = (
        fermenterCost
        + seedFermenterCost
        + mediatankCost
        + lyophilizerCost
        + centrifugeCost
        + tffCost
        + millblendcontaindetransferCost
        + utilitySystemsCost
        + qclabeqipment
    )

    installationCost = totalEquipmentCost * 0.15

    directCosts = buildingCost + totalEquipmentCost + installationCost

    contingency = directCosts * 0.125

    workingCapital = directCosts * 0.1

    # Include licensing fixed cost (one-time intangible, not part of direct costs)
    total_capex = directCosts + contingency + workingCapital + licensing_fixed_total_usd

    return total_capex, {
        "equip": totalEquipmentCost,
        "building": buildingCost,
        "land": land_cost,
        "install": installationCost,
        "direct": directCosts,
        "cont": contingency,
        "wc": workingCapital,
        "lyos_needed": lyos_needed,
        "licensing_fixed_total": licensing_fixed_total_usd,
    }


# ================= Financial Monte Carlo Analysis (Task 4.1) =================
def run_financial_monte_carlo(
    config,
    strain_names,
    target_tpa,
    n_sims=500,
    seed=42,
    anaerobic=False,
    premium_spores=False,
    sacco=False,
    fermenter_volume_L=2000,
):
    """
    Task 4.1: Financial simulation wrapper that runs Monte Carlo capacity simulation
    and calculates IRR/NPV distributions based on stochastic production output.

    Args:
        config: dict with 'reactors' and 'ds_lines' keys
        strain_names: list of strain names to simulate
        target_tpa: target tons per annum
        n_sims: number of Monte Carlo simulations
        seed: random seed for reproducibility
        anaerobic: boolean flag for anaerobic strains
        premium_spores: boolean flag for premium spore products
        sacco: boolean flag for sacco products
        fermenter_volume_L: fermenter volume in liters

    Returns:
        dict: {'irr_dist': [...], 'npv_dist': [...], 'kg_dist': [...],
               'irr_stats': {...}, 'npv_stats': {...}}
    """
    # Build strain specs with CV values for stochastic simulation
    specs = []
    for s in strain_names:
        d = STRAIN_BATCH_DB[s]
        specs.append(
            StrainSpec(
                name=s,
                fermentation_time_h=d["t_fedbatch_h"],
                turnaround_time_h=d["t_turnaround_h"],
                downstream_time_h=d["t_downstrm_h"],
                batch_mass_kg=d["yield_g_per_L"] * fermenter_volume_L / 1000,
                cv_ferm=d.get("cv_ferm", 0.1),  # Use CV values for variability
                cv_turn=d.get("cv_turn", 0.1),
                cv_down=d.get("cv_down", 0.1),
                utility_rate_ferm_kw=d["utility_rate_ferm_kw"],
                utility_rate_cent_kw=d["utility_rate_cent_kw"],
                utility_rate_lyo_kw=d["utility_rate_lyo_kw"],
                utility_cost_steam=0.0228,
            )
        )

    # Equipment configuration
    cfg = EquipmentConfig(
        year_hours=ASSUMPTIONS["hours_per_year"],
        reactors_total=config["reactors"],
        ds_lines_total=config["ds_lines"],
        upstream_availability=ASSUMPTIONS["upstream_availability"],
        downstream_availability=ASSUMPTIONS["downstream_availability"],
        quality_yield=ASSUMPTIONS["quality_yield"],
    )

    # Run Monte Carlo capacity simulation
    mc_summary = monte_carlo_capacity(
        specs,
        cfg,
        n_sims=n_sims,
        seed=seed,
        reactor_allocation_policy="inverse_ct",
        ds_allocation_policy="inverse_ct",
    )

    # Get the distribution of annual_kg_good from Monte Carlo
    # We need to run the full simulation to get individual samples
    np.random.seed(seed)
    kg_samples = []

    # Get deterministic allocation first
    df_det, _ = calculate_deterministic_capacity(
        specs,
        cfg,
        reactor_allocation_policy="inverse_ct",
        ds_allocation_policy="inverse_ct",
    )
    reactors_alloc = {
        row["name"]: float(row["reactors_assigned"]) for _, row in df_det.iterrows()
    }
    ds_alloc = {
        row["name"]: float(row["ds_lines_assigned"]) for _, row in df_det.iterrows()
    }

    # Generate samples
    for _ in range(n_sims):
        plant_kg = 0.0
        for s in specs:
            # Sample from lognormal distributions for process times
            ferm = (
                float(
                    np.random.lognormal(
                        np.log(s.fermentation_time_h)
                        - 0.5 * np.log(1 + (s.cv_ferm or 0.0) ** 2),
                        np.sqrt(np.log(1 + (s.cv_ferm or 0.0) ** 2)),
                        1,
                    )[0]
                )
                if s.cv_ferm and s.cv_ferm > 0
                else s.fermentation_time_h
            )

            turn = (
                float(
                    np.random.lognormal(
                        np.log(s.turnaround_time_h)
                        - 0.5 * np.log(1 + (s.cv_turn or 0.0) ** 2),
                        np.sqrt(np.log(1 + (s.cv_turn or 0.0) ** 2)),
                        1,
                    )[0]
                )
                if s.cv_turn and s.cv_turn > 0
                else s.turnaround_time_h
            )

            down = (
                float(
                    np.random.lognormal(
                        np.log(s.downstream_time_h)
                        - 0.5 * np.log(1 + (s.cv_down or 0.0) ** 2),
                        np.sqrt(np.log(1 + (s.cv_down or 0.0) ** 2)),
                        1,
                    )[0]
                )
                if s.cv_down and s.cv_down > 0
                else s.downstream_time_h
            )

            # Calculate capacity for this strain with sampled times
            ct_up = ferm + turn
            ct_ds = down
            up_hours = cfg.year_hours * cfg.upstream_availability
            ds_hours = cfg.year_hours * cfg.downstream_availability

            up_batches = reactors_alloc[s.name] * (up_hours / ct_up if ct_up > 0 else 0)
            ds_batches = ds_alloc[s.name] * (ds_hours / ct_ds if ct_ds > 0 else 0)

            feasible_batches = (
                min(up_batches, ds_batches)
                if (reactors_alloc[s.name] > 0 and ds_alloc[s.name] > 0)
                else 0.0
            )
            good_batches = feasible_batches * cfg.quality_yield

            if s.batch_mass_kg:
                plant_kg += good_batches * s.batch_mass_kg

        kg_samples.append(plant_kg)

    # Calculate financial metrics for each production sample
    irr_dist = []
    npv_dist = []

    # Get CAPEX and fixed costs (same for all simulations)
    # Include licensing fixed cost in CAPEX
    fixed_total = licensing_fixed_total(strain_names)
    capex, cap = capex_estimate_2(
        target_tpa,
        config["reactors"],
        config["ds_lines"],
        fermenter_volume_L,
        licensing_fixed_total_usd=fixed_total,
    )

    # Calculate average raw material costs
    df_media = pd.DataFrame(
        [
            {
                "Strain": s.name,
                "Media Cost/Batch (USD)": STRAIN_DB[s.name]["media_cost_usd"],
            }
            for s in specs
        ]
    )
    df_cryo = pd.DataFrame(
        [
            {
                "Strain": s.name,
                "Cryo Cost/Batch (USD)": STRAIN_DB[s.name]["cryo_cost_usd"],
            }
            for s in specs
        ]
    )
    avg_rm_cost_per_batch = (
        df_media["Media Cost/Batch (USD)"].mean()
        + df_cryo["Cryo Cost/Batch (USD)"].mean()
    )

    # Build OPEX components with actual optimized values
    # Get actual plant capacity from deterministic calculation
    _, totals, plant = capacity_given_counts(
        strain_names, config["reactors"], config["ds_lines"], fermenter_volume_L
    )
    plant_kg_good = plant["plant_kg_good"]
    plant_batches_good = plant["plant_batches_good"]

    opx = opex_block(
        target_tpa,
        avg_rm_cost_per_batch,
        cap["equip"],
        premium_spores,
        anaerobic,
        specs,
        plant_kg_good,
        plant_batches_good,
        fermenter_volume_L,
        strains=strain_names,
        fermenters=config["reactors"],
        ds_lines=config["ds_lines"],
    )

    # Get price per kg - use weighted average for multi-product facilities
    # Check if this is a multi-product facility (has all flags set)
    if anaerobic and premium_spores and sacco:
        price_per_kg = _get_weighted_price_per_kg(strain_names, fermenter_volume_L)
    else:
        price_per_kg = _price_per_kg_from_flags(anaerobic, premium_spores, sacco)

    # Get licensing royalty rate from OPEX block
    royalty_rate = opx.get("licensing_weighted_royalty_rate", 0.0)

    # Fixed and variable OPEX components
    fixed_opex = (1 - ASSUMPTIONS["variable_opex_share"]) * opx["total_cash_opex"]
    var_opex_base = (
        ASSUMPTIONS["variable_opex_share"]
        * opx["total_cash_opex"]
        / (target_tpa * 1000.0)
    )

    # Calculate IRR and NPV for each production sample
    for kg_annual in kg_samples:
        # Scale production across ramp-up years
        years = list(range(0, 13))
        capacities = [0, 0, 0.40, 0.60, 0.75, 0.85] + [0.85] * 7

        cashflows = []
        cashflows.append(-capex * 0.70)  # Year 0
        cashflows.append(-capex * 0.30)  # Year 1

        for i in range(2, 13):
            util = capacities[i]
            # Use actual stochastic production scaled by utilization
            kg = kg_annual * util
            revenue = kg * price_per_kg
            # Variable costs scale with actual production
            cogs = kg * var_opex_base + fixed_opex
            # Apply royalty on pre-royalty EBITDA
            ebitda_pre = revenue - cogs
            royalty_paid = max(0.0, ebitda_pre) * royalty_rate
            ebitda = ebitda_pre - royalty_paid
            # Depreciation excludes licensing (50% of process capital only)
            dep = (capex - cap.get("licensing_fixed_total", 0.0)) * 0.5 / 10.0
            ebt = ebitda - dep
            tax = max(0.0, ebt * ASSUMPTIONS["tax_rate"])
            ufcf = ebitda - tax
            cashflows.append(ufcf)

        # Calculate financial metrics
        calc_irr = irr(cashflows)
        calc_npv = npv(ASSUMPTIONS["discount_rate"], cashflows)

        if np.isfinite(calc_irr):
            irr_dist.append(float(calc_irr))
        npv_dist.append(float(calc_npv))

    # Calculate statistics
    irr_stats = {
        "mean": np.mean(irr_dist) if irr_dist else np.nan,
        "std": np.std(irr_dist) if irr_dist else np.nan,
        "p10": np.percentile(irr_dist, 10) if irr_dist else np.nan,
        "p50": np.percentile(irr_dist, 50) if irr_dist else np.nan,
        "p90": np.percentile(irr_dist, 90) if irr_dist else np.nan,
    }

    npv_stats = {
        "mean": np.mean(npv_dist),
        "std": np.std(npv_dist),
        "p10": np.percentile(npv_dist, 10),
        "p50": np.percentile(npv_dist, 50),
        "p90": np.percentile(npv_dist, 90),
    }

    kg_stats = {
        "mean": np.mean(kg_samples),
        "std": np.std(kg_samples),
        "p10": np.percentile(kg_samples, 10),
        "p50": np.percentile(kg_samples, 50),
        "p90": np.percentile(kg_samples, 90),
    }

    return {
        "irr_dist": irr_dist,
        "npv_dist": npv_dist,
        "kg_dist": kg_samples,
        "irr_stats": irr_stats,
        "npv_stats": npv_stats,
        "kg_stats": kg_stats,
        "config": config,
        "mc_summary": mc_summary,
    }


# ================= Multi-objective optimizer (min CAPEX, max IRR) =================
def _price_per_kg_from_flags(anaerobic: bool, premium_spores: bool, sacco: bool):
    """Legacy pricing function for single-product facilities.
    Should not be used for multi-product facilities like facility 5."""
    return (
        ASSUMPTIONS["price_bacillus_usd_per_kg"]
        if premium_spores
        else (
            ASSUMPTIONS["price_lacto_bifido_usd_per_kg"]
            if anaerobic
            else (
                ASSUMPTIONS["price_sacco_usd_per_kg"]
                if sacco
                else (ASSUMPTIONS["price_yogurt_usd_per_kg"])
            )
        )
    )


def _get_weighted_price_per_kg(strain_names, fermenter_volume_L=2000):
    """Calculate weighted average price per kg based on strain-specific prices and yields.

    For multi-product facilities, this function uses the price information from STRAIN_BATCH_DB
    and weights it by the production capacity of each strain.

    Args:
        strain_names: List of strain names being produced
        fermenter_volume_L: Fermenter volume in liters for yield calculations

    Returns:
        float: Weighted average price per kg in USD
    """
    total_weight = 0
    weighted_price = 0

    for strain in strain_names:
        # Get strain-specific data
        strain_data = STRAIN_BATCH_DB[strain]
        yield_per_batch = (
            strain_data["yield_g_per_L"] * fermenter_volume_L / 1000
        )  # kg per batch

        # Get strain-specific price
        price_per_kg = None
        if "price_yogurt_usd_per_kg" in strain_data:
            price_per_kg = strain_data["price_yogurt_usd_per_kg"]
        elif "price_lacto_bifido_usd_per_kg" in strain_data:
            price_per_kg = strain_data["price_lacto_bifido_usd_per_kg"]
        elif "price_bacillus_usd_per_kg" in strain_data:
            price_per_kg = strain_data["price_bacillus_usd_per_kg"]
        elif "price_sacco_usd_per_kg" in strain_data:
            price_per_kg = strain_data["price_sacco_usd_per_kg"]
        else:
            # Fallback to default pricing if not specified
            price_per_kg = ASSUMPTIONS["price_yogurt_usd_per_kg"]

        # Weight by production capacity
        weighted_price += price_per_kg * yield_per_batch
        total_weight += yield_per_batch

    # Return weighted average
    return (
        weighted_price / total_weight
        if total_weight > 0
        else ASSUMPTIONS["price_yogurt_usd_per_kg"]
    )


def _financials_for_counts(
    target_tpa,
    strain_names,
    reactors,
    ds_lines,
    anaerobic=False,
    premium_spores=False,
    sacco=False,
    fermenter_volume_L=2000,
    use_stochastic=False,
    n_sims=100,
):
    """
    Evaluate a specific (reactors, ds_lines) configuration:
      - Checks capacity (kg) using calculator
      - Computes CAPEX (capex_estimate)
      - Builds OPEX from equipment cost and media/cryo averages
      - Builds 12-year cashflows (2y build + 10y ops with ramp)
      - Returns IRR, NPV, utilizations, and other metrics
      - NEW: If use_stochastic=True, returns probabilistic metrics from Monte Carlo
    """
    # capacity
    _, totals, plant = capacity_given_counts(
        strain_names, reactors, ds_lines, fermenter_volume_L
    )
    plant_kg_good = plant["plant_kg_good"]
    # capex - include licensing fixed cost
    fixed_total = licensing_fixed_total(strain_names)
    capex, cap = capex_estimate_2(
        target_tpa,
        reactors,
        ds_lines,
        fermenter_volume_L,
        licensing_fixed_total_usd=fixed_total,
    )

    if use_stochastic:
        # Task 4.2: Use Monte Carlo simulation for probabilistic metrics
        config = {"reactors": reactors, "ds_lines": ds_lines}
        mc_results = run_financial_monte_carlo(
            config,
            strain_names,
            target_tpa,
            n_sims=n_sims,
            anaerobic=anaerobic,
            premium_spores=premium_spores,
            sacco=sacco,
            fermenter_volume_L=fermenter_volume_L,
        )

        # Return probabilistic metrics for risk-aware optimization
        return {
            "reactors": reactors,
            "ds_lines": ds_lines,
            "capex": float(capex),
            "irr": float(mc_results["irr_stats"]["p50"]),  # Median IRR
            "irr_p10": float(mc_results["irr_stats"]["p10"]),  # Conservative IRR
            "irr_p90": float(mc_results["irr_stats"]["p90"]),  # Optimistic IRR
            "irr_mean": float(mc_results["irr_stats"]["mean"]),
            "irr_std": float(mc_results["irr_stats"]["std"]),
            "npv": float(mc_results["npv_stats"]["p50"]),  # Median NPV
            "npv_p10": float(mc_results["npv_stats"]["p10"]),  # Conservative NPV
            "npv_p90": float(mc_results["npv_stats"]["p90"]),  # Optimistic NPV
            "npv_mean": float(mc_results["npv_stats"]["mean"]),
            "npv_std": float(mc_results["npv_stats"]["std"]),
            "plant_kg_good": float(plant_kg_good),  # Deterministic capacity
            "plant_kg_p50": float(mc_results["kg_stats"]["p50"]),  # Stochastic median
            "plant_kg_p10": float(
                mc_results["kg_stats"]["p10"]
            ),  # Conservative capacity
            "plant_batches_feasible": float(plant["plant_batches_feasible"]),
            "plant_batches_good": float(plant["plant_batches_good"]),
            "util_up": float(totals["weighted_up_utilization"]),
            "util_ds": float(totals["weighted_ds_utilization"]),
            "cap_breakdown": cap,
        }
    else:
        # Original deterministic calculation
        # media/cryo averages (recompute from STRAIN_DB for selected strains)
        df_media = pd.DataFrame(
            [
                {"Strain": s, "Media Cost/Batch (USD)": STRAIN_DB[s]["media_cost_usd"]}
                for s in strain_names
            ]
        )
        df_cryo = pd.DataFrame(
            [
                {"Strain": s, "Cryo Cost/Batch (USD)": STRAIN_DB[s]["cryo_cost_usd"]}
                for s in strain_names
            ]
        )
        avg_media_cost = df_media["Media Cost/Batch (USD)"].mean()
        avg_cryo_cost = df_cryo["Cryo Cost/Batch (USD)"].mean()
        avg_rm_cost_per_batch = float(avg_media_cost + avg_cryo_cost)

        # OPEX - includes licensing metadata
        strains_specs = build_strainspecs(strain_names, fermenter_volume_L)
        opx = opex_block(
            target_tpa,
            avg_rm_cost_per_batch,
            cap["equip"],
            premium_spores,
            anaerobic,
            strains_specs,
            plant_kg_good,
            plant["plant_batches_good"],
            fermenter_volume_L=fermenter_volume_L,
            strains=strain_names,
            fermenters=reactors,
            ds_lines=ds_lines,
        )

        # Extract licensing metadata
        royalty_rate = opx.get("licensing_weighted_royalty_rate", 0.0)
        licensing_fixed = opx.get("licensing_fixed_total", fixed_total)

        # Financials - use weighted average for multi-product facilities
        # Check if this is a multi-product facility (has all flags set)
        if anaerobic and premium_spores and sacco:
            price_per_kg = _get_weighted_price_per_kg(strain_names, fermenter_volume_L)
        else:
            price_per_kg = _price_per_kg_from_flags(anaerobic, premium_spores, sacco)
        steady_state_kg = target_tpa * 1000.0
        var_opex_per_kg = (
            ASSUMPTIONS["variable_opex_share"] * opx["total_cash_opex"]
        ) / steady_state_kg
        fixed_opex = (1 - ASSUMPTIONS["variable_opex_share"]) * opx["total_cash_opex"]
        years = list(range(0, 13))
        capex_spend = [0] * 13
        capex_spend[0] = -capex * 0.70
        capex_spend[1] = -capex * 0.30
        capacities = [0, 0, 0.40, 0.60, 0.75, 0.85] + [0.85] * 7

        cashflows = []
        for i, yr in enumerate(years):
            if i < 2:
                ufcf = capex_spend[i]
            else:
                util = capacities[i]
                kg = steady_state_kg * util
                revenue = kg * price_per_kg
                cogs = kg * var_opex_per_kg + fixed_opex
                # Apply royalty on pre-royalty EBITDA
                ebitda_pre = revenue - cogs
                royalty_paid = max(0.0, ebitda_pre) * royalty_rate
                ebitda = ebitda_pre - royalty_paid
                # Depreciation excludes licensing (50% of process capital only)
                dep = (capex - licensing_fixed) * 0.5 / 10.0
                ebt = ebitda - dep
                tax = max(0.0, ebt * ASSUMPTIONS["tax_rate"])
                ufcf = ebitda - tax
            cashflows.append(ufcf)

        calc_npv = npv(ASSUMPTIONS["discount_rate"], cashflows)
        calc_irr = irr(cashflows)

        return {
            "reactors": reactors,
            "ds_lines": ds_lines,
            "capex": float(capex),
            "irr": float(calc_irr) if np.isfinite(calc_irr) else np.nan,
            "npv": float(calc_npv),
            "plant_kg_good": float(plant_kg_good),
            "plant_batches_feasible": float(plant["plant_batches_feasible"]),
            "plant_batches_good": float(plant["plant_batches_good"]),
            "util_up": float(totals["weighted_up_utilization"]),
            "util_ds": float(totals["weighted_ds_utilization"]),
            "cap_breakdown": cap,
        }


def _pareto_front(df, minimize_cols=("capex",), maximize_cols=("irr",)):
    """Return a boolean mask marking non-dominated solutions (Pareto front)."""
    vals = df.copy()
    for c in minimize_cols:
        vals[c] = vals[c]
    for c in maximize_cols:
        vals[c] = -vals[c]  # convert to minimization by negating

    data = vals[list(minimize_cols) + list(maximize_cols)].to_numpy()
    n = data.shape[0]
    is_dominated = np.zeros(n, dtype=bool)
    for i in range(n):
        if is_dominated[i]:
            continue
        for j in range(n):
            if i == j:
                continue
            # x dominates y if x <= y on all objectives and < on at least one
            if np.all(data[j] <= data[i]) and np.any(data[j] < data[i]):
                is_dominated[i] = True
                break
    return ~is_dominated


def _choose_knee_point(pareto_df):
    """Pick the 'knee' (closest to utopia: min CAPEX, max IRR) with normalization."""
    if pareto_df.empty:
        return None
    cap_min, cap_max = pareto_df["capex"].min(), pareto_df["capex"].max()
    irr_min, irr_max = pareto_df["irr"].min(), pareto_df["irr"].max()

    # Normalize (lower capex better -> 0; higher irr better -> 0 after flipping sign)
    def norm_cap(x):
        return 0.0 if cap_max == cap_min else (x - cap_min) / (cap_max - cap_min)

    def norm_irr(x):
        return 0.0 if irr_max == irr_min else (irr_max - x) / (irr_max - irr_min)

    d = (
        pareto_df["capex"].apply(norm_cap) ** 2 + pareto_df["irr"].apply(norm_irr) ** 2
    ) ** 0.5
    idx = d.idxmin()
    return int(idx)


def parse_media_components(strain_name):
    """Parse media and cryo components with quantities for a specific strain.
    Returns dict with component names as keys and kg per 1600L working volume as values."""
    media_components = {}
    cryo_components = {}

    # Define the media formulations (kg per 1600L working volume)
    media_formulas = {
        "S. thermophilus": {
            "Lactose": 32,
            "Yeast Extract": 24,
            "K2HPO4": 3.2,
            "KH2PO4": 3.2,
        },
        "L. delbrueckii subsp. bulgaricus": {
            "Whey Powder": 64,
            "Yeast Extract": 10,
            "Dextrose": 20,
            "K2HPO4": 3.4,
        },
        "L. acidophilus": {
            "Whey Powder": 10 * 1.6,
            "Soy Peptone": 30 * 1.6,
            "Glucose": 5 * 1.6,
            "Tween_80": 1.0 * 1.6,
            "MgSO4x7H2O": 1.0 * 1.6,
            "MnSO4xH2O": 0.06 * 1.6,
            "ZnSO4x7H2O": 0.01 * 1.6,
        },
        "B. animalis subsp. lactis": {
            "Yeast Extract": 28.8,
            "Soy Peptone": 28.0,
            "Glucose": 6.2,
            "L-cysteine HCl": 2.8,
            "FeSO4": 0.055,
        },
        "L. rhamnosus GG": {
            "Glucose": 112.5 * 1.6,
            "Molasses": 56.25 * 1.6,
            "Casein": 18.75 * 1.6,
            "Yeast Extract": 18.75 * 1.6,
            "K2HPO4": 13.13 * 1.6,
            "Tween_80": 1.88 * 1.6,
            "Simethicone": 1.25 * 1.6,
            "CaCl2": 0.1875 * 1.6,
            "MgSO4x7H2O": 0.375 * 1.6,
            "MnSO4xH2O": 0.075 * 1.6,
        },
        "L. casei": {
            "Sucrose": 100,
            "CSL": 50,
            "Yeast Extract": 10,
            "K2HPO4": 5,
            "KH2PO4": 2,
        },
        "L. plantarum": {
            "Glucose": 50,
            "Soy Peptone": 20,
            "K2HPO4": 3.2,
            "KH2PO4": 3.2,
            "Sodium_Acetate": 5.0 * 1.6,
            "Tween_80": 0.2 * 1.6,
            "MgSO4x7H2O": 0.3 * 1.6,
            "MnSO4xH2O": 0.04 * 1.6,
        },
        "B. breve": {
            "Yeast Extract": 28.8,
            "Soy Peptone": 28.0,
            "Glucose": 6.2,
            "L-cysteine HCl": 2.8,
            "FeSO4": 0.055,
        },
        "B. longum": {
            "Yeast Extract": 28.8,
            "Soy Peptone": 28.0,
            "Glucose": 6.2,
            "L-cysteine HCl": 2.8,
            "FeSO4": 0.055,
            "MgSO4x7H2O": 1.0 * 1.6,
            "Sodium_Citrate": 1.0 * 1.6,
        },
        "Bacillus coagulans": {
            "Glucose": 32,
            "Soy Peptone": 20,
            "K2HPO4": 3.2,
            "KH2PO4": 3.2,
        },
        "Bacillus subtilis": {
            "Glucose": 20 * 1.6,
            "Soy Peptone": 20 * 1.6,
            "K2HPO4": 3.2 * 1.6,
            "MnSO4xH2O": 0.1 * 1.6,
        },
        "Saccharomyces boulardii": {
            "Glucose": 400,
            "Yeast Extract": 12,
            "K2HPO4": 4,
            "MgSO4x7H2O": 1.33,
        },
    }

    # Define cryo formulations (kg per 1600L working volume)
    cryo_formulas = {
        "S. thermophilus": {"Skim Milk": 10.7, "Trehalose": 5.35, "Sucrose": 5.35},
        "L. delbrueckii subsp. bulgaricus": {
            "Skim Milk": 10.7,
            "Sucrose": 5.35,
            "Soy Peptone": 5.35,
        },
        "L. acidophilus": {
            "Skim Milk": 10.7,
            "Trehalose": 5.35,
            "Sucrose": 5.35,
            "Sodium Ascorbate": 0.7,
        },
        "B. animalis subsp. lactis": {
            "Skim Milk": 15,
            "Lactose": 5,
            "Sucrose": 5,
            "Sodium Ascorbate": 1,
        },
        "L. rhamnosus GG": {"Skim Milk": 10, "Trehalose": 5, "Sucrose": 5},
        "L. casei": {"Skim Milk": 15, "Sucrose": 5},
        "L. plantarum": {"Skim Milk": 10, "Trehalose": 5, "Sucrose": 5},
        "B. breve": {
            "Skim Milk": 28,
            "Lactose": 10,
            "Sucrose": 10,
            "Sodium Ascorbate": 2,
        },
        "B. longum": {
            "Skim Milk": 25,
            "Lactose": 10,
            "Sucrose": 10,
            "Sodium Ascorbate": 1.5,
        },
        "Bacillus coagulans": {"Skim Milk": 3, "Sucrose": 3},
        "Bacillus subtilis": {"Skim Milk": 3, "Sucrose": 3},
        "Saccharomyces boulardii": {
            "Skim Milk": 10,
            "Trehalose": 5,
            "Sucrose": 5,
            "Sodium Ascorbate": 1,
        },
    }

    media_components = media_formulas.get(strain_name, {})
    cryo_components = cryo_formulas.get(strain_name, {})

    return media_components, cryo_components


def generate_detailed_opex_report(
    strains,
    fermenters,
    ds_lines,
    fermenter_volume_L,
    target_tpa,
    plant_kg_good,
    plant_batches_good,
    price_per_kg=None,
):
    """Generate detailed OPEX breakdown with component-level details."""
    opex_data = []

    # Calculate working volume (80% of fermenter volume)
    working_volume_L = fermenter_volume_L * 0.8
    scale_factor = working_volume_L / 1600.0  # Scale from base 1600L working volume

    # Get actual strain batch allocations from capacity calculation
    df_det, _ = calculate_deterministic_capacity(
        build_strainspecs(strains, fermenter_volume_L=fermenter_volume_L),
        EquipmentConfig(
            year_hours=ASSUMPTIONS["hours_per_year"],
            reactors_total=fermenters,
            ds_lines_total=ds_lines,
            upstream_availability=ASSUMPTIONS["upstream_availability"],
            downstream_availability=ASSUMPTIONS["downstream_availability"],
            quality_yield=ASSUMPTIONS["quality_yield"],
        ),
        reactor_allocation_policy="inverse_ct",
        ds_allocation_policy="inverse_ct",
    )

    # Create a mapping of strain to actual good batches
    strain_batches_map = {
        row["name"]: row["good_batches"] for _, row in df_det.iterrows()
    }

    # Raw materials breakdown by strain
    total_media_cost = 0
    total_cryo_cost = 0

    for strain in strains:
        strain_data = STRAIN_BATCH_DB[strain]
        # Calculate strain production metrics using actual batch allocation
        yield_per_batch = (
            strain_data["yield_g_per_L"] * working_volume_L / 1000
        )  # kg per batch
        batches_per_strain = strain_batches_map.get(
            strain, 0
        )  # Actual allocated batches
        annual_production = yield_per_batch * batches_per_strain

        # Get media components
        media_components, cryo_components = parse_media_components(strain)

        # Media components
        for component, kg_per_1600L in media_components.items():
            if component in RAW_PRICES:
                kg_per_batch = kg_per_1600L * scale_factor
                annual_kg = kg_per_batch * batches_per_strain
                annual_cost = annual_kg * RAW_PRICES[component]
                total_media_cost += annual_cost

                opex_data.append(
                    {
                        "Category": "Raw Materials - Media",
                        "Strain": strain,
                        "Component": component,
                        "Unit Price (USD/kg)": RAW_PRICES[component],
                        "Usage per Batch (kg)": round(kg_per_batch, 3),
                        "Annual Usage (kg)": round(annual_kg, 1),
                        "Annual Cost (USD)": round(annual_cost, 2),
                        "Cost per kg DCW (USD/kg)": round(
                            annual_cost / annual_production
                            if annual_production > 0
                            else 0,
                            2,
                        ),
                    }
                )

        # Cryo components
        for component, kg_per_1600L in cryo_components.items():
            if component in RAW_PRICES:
                kg_per_batch = kg_per_1600L * scale_factor
                annual_kg = kg_per_batch * batches_per_strain
                annual_cost = annual_kg * RAW_PRICES[component]
                total_cryo_cost += annual_cost

                opex_data.append(
                    {
                        "Category": "Raw Materials - Cryoprotectants",
                        "Strain": strain,
                        "Component": component,
                        "Unit Price (USD/kg)": RAW_PRICES[component],
                        "Usage per Batch (kg)": round(kg_per_batch, 3),
                        "Annual Usage (kg)": round(annual_kg, 1),
                        "Annual Cost (USD)": round(annual_cost, 2),
                        "Cost per kg DCW (USD/kg)": round(
                            annual_cost / annual_production
                            if annual_production > 0
                            else 0,
                            2,
                        ),
                    }
                )

    # Utilities breakdown
    electricity_rate = 0.107  # USD/kWh
    steam_rate = 0.0228  # USD/kg steam

    total_electricity_cost = 0
    total_steam_cost = 0

    for strain in strains:
        strain_data = STRAIN_BATCH_DB[strain]
        batches_per_strain = strain_batches_map.get(
            strain, 0
        )  # Use actual allocated batches

        # Electricity consumption
        ferm_kwh_per_batch = strain_data["utility_rate_ferm_kw"]
        cent_kwh_per_batch = (
            strain_data["utility_rate_cent_kw"]
            * strain_data["t_downstrm_h"]
            * (fermenter_volume_L / 1000)
        )
        lyo_kwh_per_batch = (
            strain_data["utility_rate_lyo_kw"]
            * strain_data["t_downstrm_h"]
            * fermenter_volume_L
        )

        total_kwh_per_batch = (
            ferm_kwh_per_batch + cent_kwh_per_batch + lyo_kwh_per_batch
        )
        annual_kwh = total_kwh_per_batch * batches_per_strain
        annual_electricity_cost = annual_kwh * electricity_rate
        total_electricity_cost += annual_electricity_cost

        opex_data.append(
            {
                "Category": "Utilities - Electricity",
                "Strain": strain,
                "Component": "Electricity (Fermentation + DS)",
                "Unit Price (USD/kg)": electricity_rate,
                "Usage per Batch (kg)": round(total_kwh_per_batch, 1),
                "Annual Usage (kg)": round(annual_kwh, 0),
                "Annual Cost (USD)": round(annual_electricity_cost, 2),
                "Cost per kg DCW (USD/kg)": round(
                    annual_electricity_cost
                    / (
                        strain_data["yield_g_per_L"]
                        * working_volume_L
                        * batches_per_strain
                        / 1000
                    )
                    if batches_per_strain > 0
                    else 0,
                    2,
                ),
            }
        )

        # Steam consumption
        batch_mass_kg = strain_data["yield_g_per_L"] * working_volume_L / 1000
        steam_per_batch = batch_mass_kg * 10  # Assume 10 kg steam per kg product
        annual_steam = steam_per_batch * batches_per_strain
        annual_steam_cost = annual_steam * steam_rate
        total_steam_cost += annual_steam_cost

        opex_data.append(
            {
                "Category": "Utilities - Steam",
                "Strain": strain,
                "Component": "Process Steam",
                "Unit Price (USD/kg)": steam_rate,
                "Usage per Batch (kg)": round(steam_per_batch, 1),
                "Annual Usage (kg)": round(annual_steam, 0),
                "Annual Cost (USD)": round(annual_steam_cost, 2),
                "Cost per kg DCW (USD/kg)": round(
                    annual_steam_cost / (batch_mass_kg * batches_per_strain)
                    if batches_per_strain > 0
                    else 0,
                    2,
                ),
            }
        )

    # Labor breakdown - scale with production like in opex_block
    # Base headcount for 15 TPA, scales linearly with production
    ftes_scaling = target_tpa / 15.0 if target_tpa >= 15 else 1.0

    labor_positions = [
        {
            "Position": "Plant Manager",
            "Count": 1,
            "Annual Salary": ASSUMPTIONS["plant_manager_salary"],
        },
        {
            "Position": "Fermentation Specialist",
            "Count": 3,
            "Annual Salary": ASSUMPTIONS["fermentation_specialist_salary"],
        },
        {
            "Position": "Downstream Process Operator",
            "Count": 3,
            "Annual Salary": ASSUMPTIONS["downstream_process_operator_salary"],
        },
        {
            "Position": "General Technician",
            "Count": 2,
            "Annual Salary": ASSUMPTIONS["general_technician_salary"],
        },
        {
            "Position": "QA/QC Lab Technician",
            "Count": 1,
            "Annual Salary": ASSUMPTIONS["qaqc_lab_tech_salary"],
        },
        {
            "Position": "Maintenance Technician",
            "Count": 1,
            "Annual Salary": ASSUMPTIONS["maintenance_tech_salary"],
        },
        {
            "Position": "Utility Operator",
            "Count": 2,
            "Annual Salary": ASSUMPTIONS["utility_operator_salary"],
        },
        {
            "Position": "Logistics Clerk",
            "Count": 1,
            "Annual Salary": ASSUMPTIONS["logistics_clerk_salary"],
        },
        {
            "Position": "Office Clerk",
            "Count": 1,
            "Annual Salary": ASSUMPTIONS["office_clerk_salary"],
        },
    ]

    total_labor_cost = 0
    for position in labor_positions:
        # Scale headcount with production for all positions
        scaled_count = position["Count"] * ftes_scaling
        annual_cost = scaled_count * position["Annual Salary"]
        total_labor_cost += annual_cost

        opex_data.append(
            {
                "Category": "Labor",
                "Strain": "Common",
                "Component": position["Position"],
                "Unit Price (USD/kg)": position["Annual Salary"],
                "Usage per Batch (kg)": round(scaled_count, 2),
                "Annual Usage (kg)": round(scaled_count, 2),
                "Annual Cost (USD)": round(annual_cost, 2),
                "Cost per kg DCW (USD/kg)": round(
                    annual_cost / plant_kg_good if plant_kg_good > 0 else 0, 2
                ),
            }
        )

    # Other OPEX components
    _, cap = capex_estimate_2(target_tpa, fermenters, ds_lines, fermenter_volume_L)
    maintenance_cost = ASSUMPTIONS["maintenance_pct_of_equip"] * cap["equip"]
    ga_cost = ASSUMPTIONS["ga_other_scale_factor"] * (target_tpa * 1000.0)

    opex_data.append(
        {
            "Category": "Maintenance",
            "Strain": "Common",
            "Component": "Equipment Maintenance (9% of equipment cost)",
            "Unit Price (USD/kg)": "-",
            "Usage per Batch (kg)": "-",
            "Annual Usage (kg)": "-",
            "Annual Cost (USD)": round(maintenance_cost, 2),
            "Cost per kg DCW (USD/kg)": round(
                maintenance_cost / plant_kg_good if plant_kg_good > 0 else 0, 2
            ),
        }
    )

    opex_data.append(
        {
            "Category": "G&A",
            "Strain": "Common",
            "Component": "General & Administrative",
            "Unit Price (USD/kg)": "-",
            "Usage per Batch (kg)": "-",
            "Annual Usage (kg)": "-",
            "Annual Cost (USD)": round(ga_cost, 2),
            "Cost per kg DCW (USD/kg)": round(
                ga_cost / plant_kg_good if plant_kg_good > 0 else 0, 2
            ),
        }
    )

    # Add licensing royalty information (before TOTAL OPEX)
    # Compute weighted royalty rate using the helper function
    royalty_rate, _ = weighted_royalty_rate(
        strains, fermenters, ds_lines, fermenter_volume_L
    )

    # Optionally calculate steady-state royalty estimate if price is provided
    licensing_royalty_estimate = 0
    if price_per_kg and price_per_kg > 0:
        # Calculate steady-state EBITDA_pre
        # Assume variable OPEX is 85% of total OPEX (from ASSUMPTIONS)
        var_opex_ratio = 0.85
        fixed_opex = total_opex * (1 - var_opex_ratio)
        var_opex_per_kg = (
            (total_opex * var_opex_ratio) / plant_kg_good if plant_kg_good > 0 else 0
        )
        steady_state_revenue = plant_kg_good * price_per_kg
        steady_state_cogs = plant_kg_good * var_opex_per_kg + fixed_opex
        ebitda_pre = steady_state_revenue - steady_state_cogs
        licensing_royalty_estimate = max(0, ebitda_pre) * royalty_rate

    opex_data.append(
        {
            "Category": "Licensing - Royalty",
            "Strain": "ALL",
            "Component": "Weighted Royalty Rate on EBITDA",
            "Unit Price (USD/kg)": f"{royalty_rate:.2%}",
            "Usage per Batch (kg)": "-",
            "Annual Usage (kg)": "-",
            "Annual Cost (USD)": round(licensing_royalty_estimate, 2)
            if price_per_kg
            else 0,
            "Cost per kg DCW (USD/kg)": round(
                licensing_royalty_estimate / plant_kg_good
                if plant_kg_good > 0 and price_per_kg
                else 0,
                2,
            ),
        }
    )

    # Summary row
    total_opex = (
        total_media_cost
        + total_cryo_cost
        + total_electricity_cost
        + total_steam_cost
        + total_labor_cost
        + maintenance_cost
        + ga_cost
    )

    opex_data.append(
        {
            "Category": "TOTAL OPEX",
            "Strain": "ALL",
            "Component": "Total Operating Expenses",
            "Unit Price (USD/kg)": "-",
            "Usage per Batch (kg)": "-",
            "Annual Usage (kg)": "-",
            "Annual Cost (USD)": round(total_opex, 2),
            "Cost per kg DCW (USD/kg)": round(
                total_opex / plant_kg_good if plant_kg_good > 0 else 0, 2
            ),
        }
    )

    return pd.DataFrame(opex_data)


def generate_detailed_capex_report(
    fermenters, ds_lines, fermenter_volume_L, target_tpa, strains=None
):
    """Generate detailed CAPEX breakdown with individual equipment costs."""
    capex_data = []

    # Calculate individual equipment quantities and costs
    base_volume = 2000
    base_fermenter_cost = 150000
    volume_scale_factor = (fermenter_volume_L / base_volume) ** 0.6

    # Fermenters (already includes spare when min 2 fermenters enforced)
    fermenter_cost = base_fermenter_cost * volume_scale_factor
    capex_data.append(
        {
            "Category": "Process Equipment",
            "Item": f"{fermenter_volume_L}L Fermenters (min 2, incl. 1 spare)",
            "Quantity": fermenters,
            "Unit Cost (USD)": round(fermenter_cost, 0),
            "Total Cost (USD)": round(fermenters * fermenter_cost, 0),
        }
    )

    # Seed fermenters
    seed_fermenters = max(2, ceil(fermenters * 0.7)) + 1
    seed_fermenter_cost = 50000 * volume_scale_factor
    capex_data.append(
        {
            "Category": "Process Equipment",
            "Item": f"{int(fermenter_volume_L * 0.125)}L Seed Fermenters",
            "Quantity": seed_fermenters,
            "Unit Cost (USD)": round(seed_fermenter_cost, 0),
            "Total Cost (USD)": round(seed_fermenters * seed_fermenter_cost, 0),
        }
    )

    # Media tanks scale with fermenters
    media_tanks = ceil(fermenters * 4 / 7)
    media_tank_cost = 75000 * volume_scale_factor
    capex_data.append(
        {
            "Category": "Process Equipment",
            "Item": f"{int(fermenter_volume_L * 1.25)}L Media Tanks",
            "Quantity": media_tanks,
            "Unit Cost (USD)": round(media_tank_cost, 0),
            "Total Cost (USD)": round(media_tanks * media_tank_cost, 0),
        }
    )

    # Lyophilizers
    lyo_cost = 400000 * volume_scale_factor
    capex_data.append(
        {
            "Category": "Process Equipment",
            "Item": "20m² Lyophilizers",
            "Quantity": max(1, ds_lines),
            "Unit Cost (USD)": round(lyo_cost, 0),
            "Total Cost (USD)": round(max(1, ds_lines) * lyo_cost, 0),
        }
    )

    # Centrifuges
    centrifuges = ceil(max(2, ds_lines) * 0.4)
    centrifuge_cost = 120000 * volume_scale_factor
    capex_data.append(
        {
            "Category": "Process Equipment",
            "Item": "Disc-Stack Centrifuges",
            "Quantity": centrifuges,
            "Unit Cost (USD)": round(centrifuge_cost, 0),
            "Total Cost (USD)": round(centrifuges * centrifuge_cost, 0),
        }
    )

    # TFF Skids
    tff_skids = ceil(max(2, ds_lines) * 0.4)
    tff_cost = 100000 * volume_scale_factor
    capex_data.append(
        {
            "Category": "Process Equipment",
            "Item": "TFF Skids",
            "Quantity": tff_skids,
            "Unit Cost (USD)": round(tff_cost, 0),
            "Total Cost (USD)": round(tff_skids * tff_cost, 0),
        }
    )

    # Mill/Blend/Container
    mill_blend_cost = 125000
    capex_data.append(
        {
            "Category": "Process Equipment",
            "Item": "Mill/Blend/Container Equipment",
            "Quantity": max(1, ceil(tff_skids * 0.5)),
            "Unit Cost (USD)": round(mill_blend_cost, 0),
            "Total Cost (USD)": round(
                max(1, ceil(tff_skids * 0.5)) * mill_blend_cost, 0
            ),
        }
    )

    # Utility systems
    utility_cost = 100000 + 150000 + 400000 + 120000 + 250000  # Various utility systems
    capex_data.append(
        {
            "Category": "Utilities",
            "Item": "Utility Systems (Autoclave, PW, WFI, Steam, CIP)",
            "Quantity": max(1, ceil(tff_skids * 0.5)),
            "Unit Cost (USD)": round(utility_cost, 0),
            "Total Cost (USD)": round(max(1, ceil(tff_skids * 0.5)) * utility_cost, 0),
        }
    )

    # QC Lab equipment
    qc_equipment_cost = 180000 / 20000 * target_tpa * 1000
    capex_data.append(
        {
            "Category": "QC Laboratory",
            "Item": "QC Lab Equipment",
            "Quantity": 1,
            "Unit Cost (USD)": round(qc_equipment_cost, 0),
            "Total Cost (USD)": round(qc_equipment_cost, 0),
        }
    )

    # Calculate totals for equipment
    total_equipment = sum([item["Total Cost (USD)"] for item in capex_data])

    # Installation
    installation_cost = total_equipment * 0.15
    capex_data.append(
        {
            "Category": "Installation",
            "Item": "Installation & Commissioning (15% of equipment)",
            "Quantity": 1,
            "Unit Cost (USD)": round(installation_cost, 0),
            "Total Cost (USD)": round(installation_cost, 0),
        }
    )

    # Building and land scale with fermenters
    facility_area = 1000 + (fermenters * 500) * volume_scale_factor
    land_cost = 250 * facility_area
    building_cost = (
        500 * 500
        + 500 * 2000 * volume_scale_factor
        + 2000 * (fermenters * 500 * volume_scale_factor)
    )

    capex_data.append(
        {
            "Category": "Infrastructure",
            "Item": f"Land ({round(facility_area, 0)} m²)",
            "Quantity": 1,
            "Unit Cost (USD)": round(land_cost, 0),
            "Total Cost (USD)": round(land_cost, 0),
        }
    )

    capex_data.append(
        {
            "Category": "Infrastructure",
            "Item": "Building & Cleanrooms",
            "Quantity": 1,
            "Unit Cost (USD)": round(building_cost, 0),
            "Total Cost (USD)": round(building_cost, 0),
        }
    )

    # Direct costs subtotal
    direct_costs = total_equipment + land_cost + building_cost + installation_cost

    # Contingency
    contingency = direct_costs * 0.125
    capex_data.append(
        {
            "Category": "Contingency",
            "Item": "Contingency (12.5% of direct costs)",
            "Quantity": 1,
            "Unit Cost (USD)": round(contingency, 0),
            "Total Cost (USD)": round(contingency, 0),
        }
    )

    # Working capital
    working_capital = direct_costs * 0.1
    capex_data.append(
        {
            "Category": "Working Capital",
            "Item": "Initial Working Capital (10% of direct costs)",
            "Quantity": 1,
            "Unit Cost (USD)": round(working_capital, 0),
            "Total Cost (USD)": round(working_capital, 0),
        }
    )

    # Licensing (fixed one-time fee)
    fixed_total = 0
    if strains:
        fixed_total = licensing_fixed_total(strains)
    if fixed_total > 0:
        capex_data.append(
            {
                "Category": "Licensing",
                "Item": "Strain Licensing (Fixed)",
                "Quantity": len(strains) if strains else "-",
                "Unit Cost (USD)": "-",
                "Total Cost (USD)": round(fixed_total, 0),
            }
        )

    # Total CAPEX - includes licensing if present
    total_capex = direct_costs + contingency + working_capital + fixed_total
    capex_data.append(
        {
            "Category": "TOTAL",
            "Item": "Total Initial Investment",
            "Quantity": "-",
            "Unit Cost (USD)": "-",
            "Total Cost (USD)": round(total_capex, 0),
        }
    )

    return pd.DataFrame(capex_data)


def generate_detailed_pl_statement(
    strains,
    fermenters,
    ds_lines,
    fermenter_volume_L,
    target_tpa,
    plant_kg_good,
    plant_batches_good,
    anaerobic,
    premium_spores,
    sacco,
):
    """Generate detailed 10-year P&L statement with payback analysis including licensing."""

    # Get price per kg
    if anaerobic and premium_spores and sacco:
        price_per_kg = _get_weighted_price_per_kg(
            strains, fermenter_volume_L * 0.8
        )  # Use working volume
    else:
        price_per_kg = _price_per_kg_from_flags(anaerobic, premium_spores, sacco)

    # Calculate licensing costs
    fixed_total = licensing_fixed_total(strains)
    royalty_rate, _ = weighted_royalty_rate(
        strains, fermenters, ds_lines, fermenter_volume_L
    )

    # Calculate CAPEX (includes licensing fixed cost)
    capex, cap = capex_estimate_2(
        target_tpa,
        fermenters,
        ds_lines,
        fermenter_volume_L,
        licensing_fixed_total_usd=fixed_total,
    )

    # Calculate detailed OPEX (without licensing royalty - that's calculated from EBITDA)
    opex_df = generate_detailed_opex_report(
        strains,
        fermenters,
        ds_lines,
        fermenter_volume_L,
        target_tpa,
        plant_kg_good,
        plant_batches_good,
    )
    total_opex = opex_df[opex_df["Category"] == "TOTAL OPEX"]["Annual Cost (USD)"].iloc[
        0
    ]

    # Variable vs fixed OPEX split
    variable_opex_ratio = ASSUMPTIONS["variable_opex_share"]
    fixed_opex = total_opex * (1 - variable_opex_ratio)
    variable_opex_per_kg = (
        (total_opex * variable_opex_ratio) / plant_kg_good if plant_kg_good > 0 else 0
    )

    # Build 10-year P&L
    years = list(range(0, 13))  # Years 0-12 (construction + 10 operational years)
    capacities = [0, 0, 0.40, 0.60, 0.80, 1.00] + [1.00] * 7  # Ramp-up schedule

    pl_data = []
    cumulative_cashflow = 0
    payback_year = None

    for year in years:
        if year < 2:
            # Construction phase
            capex_spend = -capex * 0.70 if year == 0 else -capex * 0.30
            revenue = 0
            production_kg = 0
            cogs = 0
            gross_profit = 0
            licensing_royalty = 0
            ebitda_pre_royalty = 0
            ebitda = 0
            depreciation = 0
            ebit = 0
            tax = 0
            net_income = 0
            cashflow = capex_spend
        else:
            # Operational phase
            capacity_util = capacities[year]
            production_kg = plant_kg_good * capacity_util
            revenue = production_kg * price_per_kg

            # COGS = Variable costs (scaled) + Fixed costs
            cogs = (production_kg * variable_opex_per_kg) + fixed_opex
            gross_profit = revenue - cogs

            # EBITDA before royalty
            ebitda_pre_royalty = gross_profit

            # Licensing royalty payment (% of pre-royalty EBITDA, capped at 0)
            licensing_royalty = max(0, ebitda_pre_royalty) * royalty_rate

            # EBITDA after royalty
            ebitda = ebitda_pre_royalty - licensing_royalty

            # Depreciation (10-year straight line, 50% of process capital only - excludes licensing)
            depreciation = (capex - fixed_total) * 0.5 / 10.0

            # EBIT
            ebit = ebitda - depreciation

            # Tax
            tax = max(0, ebit * ASSUMPTIONS["tax_rate"])

            # Net Income
            net_income = ebit - tax

            # Cash Flow (add back depreciation)
            cashflow = net_income + depreciation
            capex_spend = 0

        cumulative_cashflow += cashflow

        # Check for payback
        if payback_year is None and cumulative_cashflow > 0:
            payback_year = year

        pl_data.append(
            {
                "Year": year,
                "Capacity Utilization (%)": capacities[year] * 100 if year >= 2 else 0,
                "Production (kg)": round(production_kg, 0) if year >= 2 else 0,
                "Revenue (USD)": round(revenue, 0) if year >= 2 else 0,
                "COGS (USD)": round(cogs, 0) if year >= 2 else 0,
                "Gross Profit (USD)": round(gross_profit, 0) if year >= 2 else 0,
                "Gross Margin (%)": round(gross_profit / revenue * 100, 1)
                if revenue > 0
                else 0,
                "Licensing Royalty (USD)": round(licensing_royalty, 0)
                if year >= 2
                else 0,
                "EBITDA (USD)": round(ebitda, 0) if year >= 2 else 0,
                "Depreciation (USD)": round(depreciation, 0) if year >= 2 else 0,
                "EBIT (USD)": round(ebit, 0) if year >= 2 else 0,
                "Tax (USD)": round(tax, 0) if year >= 2 else 0,
                "Net Income (USD)": round(net_income, 0) if year >= 2 else 0,
                "CAPEX (USD)": round(capex_spend, 0) if capex_spend != 0 else 0,
                "Free Cash Flow (USD)": round(cashflow, 0),
                "Cumulative FCF (USD)": round(cumulative_cashflow, 0),
            }
        )

    pl_df = pd.DataFrame(pl_data)

    # Calculate financial metrics
    cashflows = [row["Free Cash Flow (USD)"] for row in pl_data]
    calc_npv = npv(ASSUMPTIONS["discount_rate"], cashflows)
    calc_irr = irr(cashflows)

    # Add summary metrics
    summary_data = [
        {"Metric": "Total Initial Investment (USD)", "Value": f"${capex:,.0f}"},
        {"Metric": "NPV @ 10% (USD)", "Value": f"${calc_npv:,.0f}"},
        {
            "Metric": "IRR (%)",
            "Value": f"{calc_irr:.1%}" if np.isfinite(calc_irr) else "N/A",
        },
        {
            "Metric": "Payback Period (years)",
            "Value": str(payback_year) if payback_year else ">10 years",
        },
        {
            "Metric": "Average Gross Margin (%)",
            "Value": f"{pl_df[pl_df['Year'] >= 2]['Gross Margin (%)'].mean():.1f}%",
        },
        {
            "Metric": "Steady State EBITDA Margin (%)",
            "Value": f"{(ebitda / revenue * 100):.1f}%" if revenue > 0 else "N/A",
        },
    ]

    summary_df = pd.DataFrame(summary_data)

    return pl_df, summary_df


def optimize_counts_multiobjective(
    target_tpa,
    strain_names,
    max_reactors=60,
    max_ds_lines=12,
    anaerobic=False,
    premium_spores=False,
    sacco=False,
    enforce_capacity=True,
    fermenter_volume_L=2000,
    fermenter_volumes_to_test=None,
    use_stochastic=False,
    stochastic_objective="irr_p10",
    n_sims=100,
):
    """
    Grid-search over (reactors, ds_lines, fermenter_volumes), build full feasible set,
    compute Pareto front for (min CAPEX, max IRR), and choose knee point.

    NEW: Support for stochastic optimization using probabilistic metrics.

    Args:
        use_stochastic: If True, use Monte Carlo simulation for financial metrics
        stochastic_objective: Which metric to optimize when using stochastic mode
                             Options: "irr_p10" (conservative), "irr_p50" (median), "irr_mean"
        n_sims: Number of Monte Carlo simulations per configuration

    Returns dict(best), pareto_df, all_df.
    """
    target_kg = target_tpa * 1000.0
    records = []

    # If no fermenter volumes specified, use the single provided volume
    if fermenter_volumes_to_test is None:
        fermenter_volumes_to_test = [fermenter_volume_L]

    for V in fermenter_volumes_to_test:
        for R in range(
            2, max_reactors + 1
        ):  # Start from 2 to ensure minimum 2 fermenters (1 spare)
            for D in range(1, max_ds_lines + 1):
                metrics = _financials_for_counts(
                    target_tpa,
                    strain_names,
                    R,
                    D,
                    anaerobic,
                    premium_spores,
                    sacco,
                    V,
                    use_stochastic=use_stochastic,
                    n_sims=n_sims,
                )
                metrics["meets_capacity"] = bool(
                    metrics["plant_kg_good"] + 1e-6 >= target_kg
                )
                metrics["fermenter_volume_L"] = V
                records.append(metrics)
    all_df = pd.DataFrame(records)

    # Filter feasibility if requested
    feas_df = all_df[all_df["meets_capacity"]] if enforce_capacity else all_df.copy()
    if feas_df.empty:
        # Fall back to the best capacity (max plant_kg_good) even if not meeting target
        fallback = (
            all_df.sort_values(
                ["plant_kg_good", "irr", "capex"], ascending=[False, False, True]
            )
            .head(1)
            .copy()
        )
        pareto_df = fallback.copy()
        best_row = fallback.iloc[0].to_dict()
        best_row["warning"] = "Target not reachable within search bounds"
        return best_row, pareto_df, all_df

    # Pareto front - use appropriate objective based on stochastic mode
    if use_stochastic and stochastic_objective in feas_df.columns:
        # Use risk-adjusted metric for Pareto optimization
        mask = _pareto_front(
            feas_df, minimize_cols=("capex",), maximize_cols=(stochastic_objective,)
        )
        pareto_df = (
            feas_df[mask]
            .sort_values(["capex", stochastic_objective], ascending=[True, False])
            .reset_index(drop=True)
        )
    else:
        # Original deterministic optimization
        mask = _pareto_front(feas_df, minimize_cols=("capex",), maximize_cols=("irr",))
        pareto_df = (
            feas_df[mask]
            .sort_values(["capex", "irr"], ascending=[True, False])
            .reset_index(drop=True)
        )

    # Choose knee point
    idx = _choose_knee_point(pareto_df)
    if idx is None:
        # pick lowest capex among feasibles
        if use_stochastic and stochastic_objective in feas_df.columns:
            chosen = feas_df.sort_values(
                ["capex", stochastic_objective], ascending=[True, False]
            ).iloc[0]
        else:
            chosen = feas_df.sort_values(
                ["capex", "irr"], ascending=[True, False]
            ).iloc[0]
    else:
        chosen = pareto_df.iloc[idx]

    best = chosen.to_dict()
    return best, pareto_df, all_df


# ===============================================================================


def optimize_counts_for_target(
    target_tpa, strain_names, max_reactors=40, max_ds_lines=12, fermenter_volume_L=2000
):
    target_kg = target_tpa * 1000.0
    best = None
    for R in range(
        2, max_reactors + 1
    ):  # Start from 2 to ensure minimum 2 fermenters (1 spare)
        for D in range(1, max_ds_lines + 1):
            _, totals, plant = capacity_given_counts(
                strain_names, R, D, fermenter_volume_L
            )
            if plant["plant_kg_good"] + 1e-6 >= target_kg:
                capex, cap = capex_estimate_2(target_tpa, R, D, fermenter_volume_L)
                score = capex
                candidate = {
                    "reactors": R,
                    "ds_lines": D,
                    "capex": capex,
                    "plant_batches_feasible": plant["plant_batches_feasible"],
                    "plant_batches_good": plant["plant_batches_good"],
                    "plant_kg_good": plant["plant_kg_good"],
                    "cap_breakdown": cap,
                    "util_up": totals["weighted_up_utilization"],
                    "util_ds": totals["weighted_ds_utilization"],
                }
                if (best is None) or (score < best["capex"]):
                    best = candidate
                break  # increasing D only increases capex; try next R
    if best is None:
        # If unreachable within search bounds, return last evaluated
        R, D = max_reactors, max_ds_lines
        _, totals, plant = capacity_given_counts(strain_names, R, D, fermenter_volume_L)
        capex, cap = capex_estimate_2(target_tpa, R, D, fermenter_volume_L)
        best = {
            "reactors": R,
            "ds_lines": D,
            "capex": capex,
            "plant_batches_feasible": plant["plant_batches_feasible"],
            "plant_batches_good": plant["plant_batches_good"],
            "plant_kg_good": plant["plant_kg_good"],
            "cap_breakdown": cap,
            "util_up": totals["weighted_up_utilization"],
            "util_ds": totals["weighted_ds_utilization"],
            "warning": "Target not reachable within search bounds",
        }
    return best


def opex_block(
    target_tpa,
    avg_rm_cost_per_batch,
    equip_cost,
    premium_spores,
    anaerobic,
    strains_specs,
    plant_kg_good,
    plant_batches_good,
    fermenter_volume_L=2000.0,
    strains=None,
    fermenters=None,
    ds_lines=None,
):
    """Calculate OPEX components including utilities with proper unit scaling.

    CRITICAL: Utility rates have mixed units due to legacy data:
    - Fermentation: Already total kWh per batch (do NOT multiply by time)
    - Centrifugation: kW/m³ rate (multiply by time AND volume)
    - Lyophilization: kW/(·V) rate (multiply by time AND 100% of volume)

    Volume-Scaling Formulas:
    - Fermentation electricity (kWh): utility_rate_ferm_kw (pre-computed total)
    - Centrifugation electricity (kWh): utility_rate_cent_kw × downstream_time_h × (fermenter_volume_L/1000)
    - Lyophilization electricity (kWh): utility_rate_lyo_kw × downstream_time_h × fermenter_volume_L
      Note: The lyo rate is per liter of concentrate (100% of fermenter volume)
    - Steam cost (USD): utility_cost_steam × batch_mass_kg

    Default Behavior:
    - fermenter_volume_L defaults to 2000.0 liters if not specified (backward compatibility)
    - When fermenter_volume_L changes, centrifugation and lyophilization electricity scale proportionally
    - Fermentation electricity does NOT scale with volume (legacy pre-computed totals)

    Args:
        target_tpa: Target tons per annum
        avg_rm_cost_per_batch: Average raw material cost per batch (USD)
        equip_cost: Total equipment cost (USD) for maintenance calculation
        premium_spores: Boolean flag for premium spore products
        anaerobic: Boolean flag for anaerobic strains
        strains_specs: List of StrainSpec objects with utility rates
        plant_kg_good: Total good product kg/year from capacity calculation
        plant_batches_good: Total good batches/year from capacity calculation
        fermenter_volume_L: Fermenter volume in liters (default 2000.0)

    Returns:
        dict: OPEX components including raw materials, utilities, labor, maintenance, G&A, and total
    """
    # Calculate raw materials based on actual strain batch allocations and volume scaling
    # We need the actual per-strain batch allocation from capacity calculation
    if strains and fermenters and ds_lines:
        # Get deterministic capacity allocation to see actual batches per strain
        df_det, _ = calculate_deterministic_capacity(
            build_strainspecs(strains, fermenter_volume_L=fermenter_volume_L),
            EquipmentConfig(
                year_hours=ASSUMPTIONS["hours_per_year"],
                reactors_total=fermenters,
                ds_lines_total=ds_lines,
                upstream_availability=ASSUMPTIONS["upstream_availability"],
                downstream_availability=ASSUMPTIONS["downstream_availability"],
                quality_yield=ASSUMPTIONS["quality_yield"],
            ),
            reactor_allocation_policy="inverse_ct",
            ds_allocation_policy="inverse_ct",
        )

        # Calculate raw materials cost based on actual strain allocations
        raw_materials_total = 0
        base_working_volume = 1600.0  # liters (80% of 2000L)
        actual_working_volume = fermenter_volume_L * 0.8
        volume_scale_factor = actual_working_volume / base_working_volume

        for _, row in df_det.iterrows():
            strain_name = row["name"]
            strain_good_batches = row["good_batches"]
            # Get media and cryo costs for this strain, scaled for volume
            media_cost = STRAIN_DB[strain_name]["media_cost_usd"] * volume_scale_factor
            cryo_cost = STRAIN_DB[strain_name]["cryo_cost_usd"] * volume_scale_factor
            strain_rm_cost_per_batch = media_cost + cryo_cost
            raw_materials_total += strain_rm_cost_per_batch * strain_good_batches
    else:
        # Fallback: use average cost * total batches with volume scaling
        batches_required = (
            plant_batches_good
            if plant_batches_good > 0
            else (target_tpa * 1000.0) / 25.6
        )
        base_working_volume = 1600.0
        actual_working_volume = fermenter_volume_L * 0.8
        volume_scale_factor = actual_working_volume / base_working_volume
        raw_materials_total = (
            avg_rm_cost_per_batch * volume_scale_factor * batches_required
        )

    # Calculate per-strain utility costs with volume-aware scaling
    utilities_total = 0
    electricity_rate_usd_per_kwh = (
        0.107  # Standard industrial electricity rate from ASSUMPTIONS
    )
    volume_m3 = fermenter_volume_L / 1000.0  # Convert to m³ for calculations

    # Get total batches for utilities calculation
    if strains and fermenters and ds_lines and "df_det" in locals():
        # Use actual strain allocations if available
        utilities_batches_map = {
            row["name"]: row["good_batches"] for _, row in df_det.iterrows()
        }
    else:
        # Fallback to equal distribution
        utilities_batches_map = None
        total_batches_for_utilities = (
            plant_batches_good
            if plant_batches_good > 0
            else (target_tpa * 1000.0) / 25.6
        )

    for i, strain_spec in enumerate(strains_specs):
        # Calculate number of batches for this strain
        if utilities_batches_map and strain_spec.name in utilities_batches_map:
            batches_for_this_strain = utilities_batches_map[strain_spec.name]
        else:
            # Equal distribution fallback
            batches_for_this_strain = total_batches_for_utilities / len(strains_specs)

        # Volume-aware electricity calculations per batch:
        # Each component scales differently with fermenter volume
        ferm_kwh = (
            strain_spec.utility_rate_ferm_kw
        )  # Already total kWh per batch (legacy units)
        cent_kwh = (
            strain_spec.utility_rate_cent_kw * strain_spec.downstream_time_h * volume_m3
        )  # Scales with full volume
        lyo_kwh = (
            strain_spec.utility_rate_lyo_kw
            * strain_spec.downstream_time_h
            * (fermenter_volume_L)
        )  # Scales with 100% of volume

        # Total electricity per batch for this strain
        electricity_kwh_per_batch = ferm_kwh + cent_kwh + lyo_kwh

        # Convert electricity to USD
        electricity_cost_per_batch = (
            electricity_kwh_per_batch * electricity_rate_usd_per_kwh
        )

        # Steam cost scales with batch mass (which already scales with volume)
        steam_cost_per_batch = (
            strain_spec.utility_cost_steam * strain_spec.batch_mass_kg
        )

        # Total utility cost per batch for this strain
        utilities_cost_per_batch = electricity_cost_per_batch + steam_cost_per_batch

        # Add to total utilities cost
        utilities_total += utilities_cost_per_batch * batches_for_this_strain

    ftes = target_tpa if target_tpa >= 15 else 15

    avg_labor_cost = (
        ASSUMPTIONS["plant_manager_salary"] * 1
        + ASSUMPTIONS["fermentation_specialist_salary"] * 3
        + ASSUMPTIONS["downstream_process_operator_salary"] * 3
        + ASSUMPTIONS["general_technician_salary"] * 2
        + ASSUMPTIONS["qaqc_lab_tech_salary"] * 1
        + ASSUMPTIONS["maintenance_tech_salary"] * 1
        + ASSUMPTIONS["utility_operator_salary"] * 2
        + ASSUMPTIONS["logistics_clerk_salary"] * 1
        + ASSUMPTIONS["office_clerk_salary"] * 1
    ) / 15
    labor_total = ftes * avg_labor_cost
    maintenance_total = ASSUMPTIONS["maintenance_pct_of_equip"] * equip_cost
    ga_other_total = ASSUMPTIONS["ga_other_scale_factor"] * (target_tpa * 1000.0)

    # Calculate licensing metadata if strains are provided
    # Note: Royalty amount is NOT included in total_cash_opex - it's applied later on EBITDA
    licensing_weighted_royalty_rate = 0.0
    licensing_per_strain_production_kg = {}
    licensing_fixed_total_cost = 0.0

    if strains and fermenters and ds_lines:
        # Calculate weighted royalty rate using actual production allocation
        licensing_weighted_royalty_rate, licensing_per_strain_production_kg = (
            weighted_royalty_rate(strains, fermenters, ds_lines, fermenter_volume_L)
        )
        # Calculate total fixed licensing cost
        licensing_fixed_total_cost = licensing_fixed_total(strains)

    return {
        "raw_materials_total": raw_materials_total,
        "utilities_total": utilities_total,
        "labor_total": labor_total,
        "maintenance_total": maintenance_total,
        "ga_other_total": ga_other_total,
        "total_cash_opex": raw_materials_total
        + utilities_total
        + labor_total
        + maintenance_total
        + ga_other_total,
        # Licensing metadata (not included in total_cash_opex)
        "licensing_weighted_royalty_rate": licensing_weighted_royalty_rate,
        "licensing_per_strain_production_kg": licensing_per_strain_production_kg,
        "licensing_fixed_total": licensing_fixed_total_cost,
    }


def facility_model(
    name,
    target_tpa,
    strains,
    fermenters_suggested,
    lyos_guess=None,
    anaerobic=False,
    premium_spores=False,
    sacco=False,
    optimize_equipment=True,
    use_multiobjective=True,
    fermenter_volume_L=2000,
    fermenter_volumes_to_test=None,
    use_stochastic=False,
    stochastic_objective="irr_p10",
    n_sims=100,
):
    """Model a fermentation facility's economics with optional fermenter volume optimization.

    This function calculates CAPEX, OPEX, and financial metrics for a fermentation facility
    producing probiotics. It can either use fixed equipment counts or optimize them based
    on target production capacity.

    Args:
        name: Facility/project name identifier
        target_tpa: Target production capacity in tons per annum
        strains: List of strain names to be produced (from STRAIN_DB)
        fermenters_suggested: Suggested number of fermenters (used when optimize_equipment=False)
        lyos_guess: Initial guess for number of lyophilizers (default: calculated based on target_tpa)
        anaerobic: Boolean flag for anaerobic strain processing requirements
        premium_spores: Boolean flag for premium spore product specifications
        sacco: Boolean flag for sacco (freeze-dried starter culture) products
        optimize_equipment: If True, optimizes fermenter and downstream line counts
        use_multiobjective: If True, uses multi-objective optimization (when optimize_equipment=True)
        fermenter_volume_L: Fixed fermenter volume in liters (default: 2000)
        fermenter_volumes_to_test: Optional list of fermenter volumes (in liters) to evaluate.
                                   When provided, the optimizer will test each volume and select
                                   the one with best economics. Only used when optimize_equipment=True
                                   and use_multiobjective=True. If None, uses fixed fermenter_volume_L.
        use_stochastic: If True, use Monte Carlo simulation for financial metrics in optimization
        stochastic_objective: Which metric to optimize when using stochastic mode
                             Options: "irr_p10" (conservative), "irr_p50" (median), "irr_mean"
        n_sims: Number of Monte Carlo simulations per configuration when use_stochastic=True

    Returns:
        dict: Comprehensive facility model including:
            - Equipment specifications and counts
            - CAPEX breakdown
            - OPEX breakdown
            - Financial metrics (NPV, IRR)
            - Capacity and utilization metrics
            - DataFrames with detailed tables
    """
    # Process parameters from STRAIN_DB for cost, and STRAIN_BATCH_DB for times
    df_proc = pd.DataFrame(
        [
            {
                "Strain": s,
                "Fed-batch Fermentation Time (h)": STRAIN_BATCH_DB[s]["t_fedbatch_h"],
                "Turnaround (h)": STRAIN_BATCH_DB[s]["t_turnaround_h"],
                "Downstream (h)": STRAIN_BATCH_DB[s]["t_downstrm_h"],
                "Batch Cycle (UP) (h)": STRAIN_BATCH_DB[s]["t_fedbatch_h"]
                + STRAIN_BATCH_DB[s]["t_turnaround_h"],
            }
            for s in strains
        ]
    )

    # Average costs - need to scale for fermenter volume
    # STRAIN_DB costs are for 1600L working volume (2000L * 0.8)
    base_working_volume = 1600.0  # liters
    actual_working_volume = fermenter_volume_L * 0.8
    volume_scale_factor = actual_working_volume / base_working_volume

    df_media = pd.DataFrame(
        [
            {
                "Strain": s,
                "Media Cost/Batch (USD)": STRAIN_DB[s]["media_cost_usd"]
                * volume_scale_factor,
            }
            for s in strains
        ]
    )
    df_cryo = pd.DataFrame(
        [
            {
                "Strain": s,
                "Cryo Cost/Batch (USD)": STRAIN_DB[s]["cryo_cost_usd"]
                * volume_scale_factor,
            }
            for s in strains
        ]
    )
    avg_media_cost = df_media["Media Cost/Batch (USD)"].mean()
    avg_cryo_cost = df_cryo["Cryo Cost/Batch (USD)"].mean()
    avg_rm_cost_per_batch = avg_media_cost + avg_cryo_cost

    # Initial guesses
    if lyos_guess is None:
        lyos_guess = max(1, ceil((target_tpa * 1000.0) / 7074.0))

    # Optimize equipment counts
    if optimize_equipment:
        if use_multiobjective:
            best_mo, pareto_df, all_df = optimize_counts_multiobjective(
                target_tpa,
                strains,
                max_reactors=60,
                max_ds_lines=max(lyos_guess, 12),
                anaerobic=anaerobic,
                premium_spores=premium_spores,
                sacco=sacco,
                enforce_capacity=True,
                fermenter_volume_L=fermenter_volume_L,
                fermenter_volumes_to_test=fermenter_volumes_to_test,
                use_stochastic=use_stochastic,
                stochastic_objective=stochastic_objective,
                n_sims=n_sims,
            )
            fermenters = int(best_mo["reactors"])
            ds_lines = int(best_mo["ds_lines"])
            capex = float(best_mo["capex"])
            cap = best_mo["cap_breakdown"]
            plant_batches_feasible = float(best_mo["plant_batches_feasible"])
            plant_batches_good = float(best_mo["plant_batches_good"])
            plant_kg_good = float(best_mo["plant_kg_good"])
            util_up, util_ds = float(best_mo["util_up"]), float(best_mo["util_ds"])
            # Get the optimized fermenter volume if multiple were tested
            if "fermenter_volume_L" in best_mo:
                fermenter_volume_L = best_mo["fermenter_volume_L"]
            # Log the selected configuration including fermenter volume
            print(
                f"{name} - Selected configuration: {fermenter_volume_L}L fermenters, {fermenters} reactors, {ds_lines} DS lines"
            )
        else:
            best = optimize_counts_for_target(
                target_tpa,
                strains,
                max_reactors=60,
                max_ds_lines=max(lyos_guess, 12),
                fermenter_volume_L=fermenter_volume_L,
            )
            fermenters = best["reactors"]
            ds_lines = best["ds_lines"]
            capex, cap = best["capex"], best["cap_breakdown"]
            plant_batches_feasible = best["plant_batches_feasible"]
            plant_batches_good = best["plant_batches_good"]
            plant_kg_good = best["plant_kg_good"]
            util_up, util_ds = best["util_up"], best["util_ds"]
            # Log the selected configuration including fermenter volume
            print(
                f"{name} - Selected configuration: {fermenter_volume_L}L fermenters, {fermenters} reactors, {ds_lines} DS lines"
            )
    else:
        fermenters = fermenters_suggested
        ds_lines = lyos_guess
        _, totals, plant = capacity_given_counts(
            strains, fermenters, ds_lines, fermenter_volume_L
        )
        capex, cap = capex_estimate_2(
            target_tpa, fermenters, ds_lines, fermenter_volume_L
        )
        plant_batches_feasible = plant["plant_batches_feasible"]
        plant_batches_good = plant["plant_batches_good"]
        plant_kg_good = plant["plant_kg_good"]
        util_up, util_ds = (
            totals["weighted_up_utilization"],
            totals["weighted_ds_utilization"],
        )
        # Log the selected configuration including fermenter volume
        print(
            f"{name} - Selected configuration: {fermenter_volume_L}L fermenters, {fermenters} reactors, {ds_lines} DS lines"
        )

    # Map DS lines to physical equipment
    lyos_needed = ds_lines
    centrifuges = max(1, ds_lines)
    tff_skids = max(1, ds_lines if anaerobic else 1)

    # OPEX block - now using the potentially optimized fermenter volume
    strains_specs = build_strainspecs(strains, fermenter_volume_L=fermenter_volume_L)
    opx = opex_block(
        target_tpa,
        avg_rm_cost_per_batch,
        cap["equip"],
        premium_spores,
        anaerobic,
        strains_specs,
        plant_kg_good,
        plant_batches_good,
        fermenter_volume_L,
        strains=strains,
        fermenters=fermenters,
        ds_lines=ds_lines,
    )

    # Financials (same structure as original but using calc-based kg if desired)
    # Use weighted average for multi-product facilities
    if anaerobic and premium_spores and sacco:
        price_per_kg = _get_weighted_price_per_kg(strains, fermenter_volume_L)
    else:
        price_per_kg = (
            ASSUMPTIONS["price_bacillus_usd_per_kg"]
            if premium_spores
            else (
                ASSUMPTIONS["price_lacto_bifido_usd_per_kg"]
                if anaerobic
                else (
                    ASSUMPTIONS["price_sacco_usd_per_kg"]
                    if sacco
                    else (ASSUMPTIONS["price_yogurt_usd_per_kg"])
                )
            )
        )
    steady_state_kg = target_tpa * 1000.0
    var_opex_per_kg = (
        ASSUMPTIONS["variable_opex_share"] * opx["total_cash_opex"]
    ) / steady_state_kg
    fixed_opex = (1 - ASSUMPTIONS["variable_opex_share"]) * opx["total_cash_opex"]

    years = list(range(0, 13))
    capex_spend = [0] * 13
    capex_spend[0] = -capex * 0.70
    capex_spend[1] = -capex * 0.30
    capacities = [0, 0, 0.40, 0.60, 0.80, 1.00] + [1.00] * 7

    # Get licensing info for financial calculations
    royalty_rate = opx.get("licensing_weighted_royalty_rate", 0.0)
    licensing_fixed = opx.get("licensing_fixed_total", 0.0)

    fin_rows = []
    cashflows = []
    for i, yr in enumerate(years):
        if i < 2:
            util = 0.0
            revenue = 0.0
            cogs = 0.0
            ebitda = 0.0
            dep = 0.0
            ebt = 0.0
            tax = 0.0
            ufcf = capex_spend[i]
        else:
            util = capacities[i]
            kg = steady_state_kg * util
            revenue = kg * price_per_kg
            cogs = kg * var_opex_per_kg + fixed_opex
            # Apply licensing royalty on EBITDA
            ebitda_pre = revenue - cogs
            licensing_royalty = max(0, ebitda_pre) * royalty_rate
            ebitda = ebitda_pre - licensing_royalty
            # Depreciation excludes licensing fixed cost
            dep = (capex - licensing_fixed) * 0.5 / 10.0
            ebt = ebitda - dep
            tax = max(0.0, ebt * ASSUMPTIONS["tax_rate"])
            ufcf = ebitda - tax
        cashflows.append(ufcf)
        fin_rows.append([yr, util, revenue, cogs, ebitda, dep, ebt, tax, ufcf])

    calc_npv = npv(ASSUMPTIONS["discount_rate"], cashflows)
    calc_irr = irr(cashflows)

    # Equipment list - dynamically sized based on fermenter volume
    # Media tank scales to 1.25x fermenter volume, seed fermenter is 12.5% of main fermenter
    media_tank_volume = int(fermenter_volume_L * 1.25)
    seed_fermenter_volume = int(fermenter_volume_L * 0.125)

    df_equip = pd.DataFrame(
        [
            {
                "Equipment": f"{fermenter_volume_L} L SS Fermenter",
                "Quantity": fermenters,
                "Notes": "cGMP SS316L (includes 1 spare in count)",
            },
            {
                "Equipment": f"{media_tank_volume} L SS Media Preparation Tank",
                "Quantity": fermenters,
                "Notes": "SS314L (1.25x fermenter volume)",
            },
            {
                "Equipment": f"{seed_fermenter_volume} L Seed Fermenter",
                "Quantity": max(2, ceil(fermenters * 0.7)),
                "Notes": "Upstream seed (12.5% of main)",
            },
            {
                "Equipment": "Disc-Stack Centrifuge",
                "Quantity": centrifuges,
                "Notes": "Harvest",
            },
            {
                "Equipment": "TFF Skid (Mobile)",
                "Quantity": tff_skids,
                "Notes": "Anaerobes/Shear-sensitive",
            },
            {
                "Equipment": "20 m² Lyophilizer",
                "Quantity": lyos_needed,
                "Notes": "Pass-through",
            },
            {"Equipment": "Cone Mill", "Quantity": 1, "Notes": "Product milling"},
            {
                "Equipment": "500 L V-Blender",
                "Quantity": 1,
                "Notes": "Product blending",
            },
            {
                "Equipment": "PW/WFI/Clean Steam/CIP",
                "Quantity": 1,
                "Notes": "Utility skids",
            },
            {
                "Equipment": "QC Lab",
                "Quantity": 1,
                "Notes": "Quality Control Laboratory",
            },
        ]
    )

    # CAPEX table from breakdown
    capex_rows = [
        ["Land Acquisition", cap["land"]],
        ["Building & Cleanrooms", cap["building"]],
        ["Process & Utility Equipment", cap["equip"]],
        ["Installation & Commissioning (15% Equip.)", cap["install"]],
        ["Subtotal - Direct Costs", cap["direct"]],
        ["Contingency (12.5%)", cap["cont"]],
        ["Initial Working Capital", cap["wc"]],
    ]

    # Add licensing fixed cost if present
    if cap.get("licensing_fixed_total", 0) > 0:
        capex_rows.append(["Licensing (Fixed)", cap["licensing_fixed_total"]])

    capex_rows.append(["Total Initial Investment", capex])
    df_capex = pd.DataFrame(capex_rows, columns=["CAPEX Component", "USD"])

    # OPEX table
    opex_rows = [
        ["Raw Materials (media + cryo)", opx["raw_materials_total"]],
        ["Utilities", opx["utilities_total"]],
        ["Labor (FTEs)", opx["labor_total"]],
        ["Maintenance", opx["maintenance_total"]],
        ["Other G&A", opx["ga_other_total"]],
        ["Total Cash OPEX", opx["total_cash_opex"]],
    ]

    # Add licensing royalty info row (informational - actual amount depends on EBITDA)
    if opx.get("licensing_weighted_royalty_rate", 0) > 0:
        opex_rows.append(
            [
                f"Licensing Royalty ({opx['licensing_weighted_royalty_rate']:.2%} of EBITDA)",
                "Variable",
            ]
        )

    df_opex = pd.DataFrame(opex_rows, columns=["OPEX Component", "USD"])

    # Deterministic per-strain capacity table for the chosen counts
    det_df, det_totals = calculate_deterministic_capacity(
        build_strainspecs(strains, fermenter_volume_L=fermenter_volume_L),
        EquipmentConfig(
            year_hours=ASSUMPTIONS["hours_per_year"],
            reactors_total=fermenters,
            ds_lines_total=ds_lines,
            upstream_availability=ASSUMPTIONS["upstream_availability"],
            downstream_availability=ASSUMPTIONS["downstream_availability"],
            quality_yield=ASSUMPTIONS["quality_yield"],
        ),
        reactor_allocation_policy="inverse_ct",
        ds_allocation_policy="inverse_ct",
    )
    det_df = det_df.sort_values("feasible_batches", ascending=False)

    # Summary block (now calculator-driven)
    # Calculate required batches based on actual average yield from selected strains
    avg_yield_per_batch = (
        plant_kg_good / plant_batches_good if plant_batches_good > 0 else 25.6
    )  # fallback
    required_batches = (target_tpa * 1000.0) / avg_yield_per_batch
    batches_per_fermenter_effective = plant_batches_feasible / max(fermenters, 1)
    annual_batches_capacity = plant_batches_feasible

    df_summary = pd.DataFrame(
        {
            "Metric": [
                "Target Output (TPA)",
                "Fermenter Volume (L)",
                "Reactors (optimized)",
                "DS Lines / Lyos (optimized)",
                "Plant Feasible Batches (y)",
                "Plant Good Batches (y)",
                "Avg Batches per Fermenter (effective)",
                "Required Batches (y)",
                "Meets Capacity?",
                "Upstream Utilization (weighted)",
                "Downstream Utilization (weighted)",
                "Likely Bottleneck",
                "Avg Media Cost/Batch",
                "Avg Cryo Cost/Batch",
                "Total CAPEX (USD)",
            ],
            "Value": [
                target_tpa,
                fermenter_volume_L,
                fermenters,
                ds_lines,
                round(plant_batches_feasible, 1),
                round(plant_batches_good, 1),
                round(batches_per_fermenter_effective, 2),
                round(required_batches, 1),
                bool(plant_kg_good + 1e-6 >= target_tpa * 1000.0),
                round(util_up, 3),
                round(util_ds, 3),
                "Downstream" if util_ds >= util_up else "Upstream",
                round(avg_media_cost, 2),
                round(avg_cryo_cost, 2),
                round(capex, 0),
            ],
        }
    )

    df_fin = pd.DataFrame(
        fin_rows,
        columns=[
            "Year",
            "Capacity Utilization",
            "Revenue (USD)",
            "COGS & Cash OPEX (USD)",
            "EBITDA (USD)",
            "Depreciation (USD)",
            "EBT (USD)",
            "Taxes (USD)",
            "Unlevered FCF (USD)",
        ],
    )

    # Enhanced Assumptions with facility-specific information
    facility_area = 1000 + (fermenters * 500)  # Calculate actual facility area

    # Create comprehensive assumptions DataFrame
    assumptions_data = [
        # Original assumptions
        *list(ASSUMPTIONS.items()),
        # Facility-specific optimized parameters
        ("", ""),  # Blank row separator
        ("--- OPTIMIZED FACILITY PARAMETERS ---", ""),
        ("Optimized Fermenter Volume (L)", fermenter_volume_L),
        ("Total Fermenters (min 2, includes 1 spare)", fermenters),
        ("Optimized DS Lines", ds_lines),
        ("Total Facility Area (m²)", facility_area),
        ("Actual Plant Capacity (kg/year)", round(plant_kg_good, 0)),
        ("Calculated IRR", f"{calc_irr:.2%}" if np.isfinite(calc_irr) else "N/A"),
        ("Calculated NPV (USD)", f"${calc_npv:,.0f}"),
        ("", ""),  # Blank row separator
        ("--- LICENSING INFORMATION ---", ""),
        ("Licensing Fixed Cost (USD)", f"${opx.get('licensing_fixed_total', 0):,.0f}"),
        (
            "Licensing Royalty Rate",
            f"{opx.get('licensing_weighted_royalty_rate', 0):.2%}",
        ),
        ("", ""),  # Blank row separator
        ("--- STRAIN SELECTION ---", ""),
        ("Selected Strains", ", ".join(strains)),
        (
            "Product Type",
            "Multi-Product (All Types)"
            if (anaerobic and premium_spores and sacco)
            else (
                "Premium Spores"
                if premium_spores
                else ("Anaerobic" if anaerobic else ("Sacco" if sacco else "Standard"))
            ),
        ),
        ("Price per kg (USD)", price_per_kg),
    ]
    df_assump = pd.DataFrame(assumptions_data, columns=["Parameter", "Value"])

    # Create strain process parameters DataFrame
    strain_params_data = []
    for s in strains:
        db_entry = STRAIN_BATCH_DB[s]
        strain_params_data.append(
            {
                "Strain": s,
                "Yield (g/L)": db_entry["yield_g_per_L"],
                "Fermentation (h)": db_entry["t_fedbatch_h"],
                "Turnaround (h)": db_entry["t_turnaround_h"],
                "Downstream (h)": db_entry["t_downstrm_h"],
                "CV Ferm": db_entry["cv_ferm"],
                "CV Turn": db_entry["cv_turn"],
                "CV Down": db_entry["cv_down"],
                "Media Cost (USD/batch)": STRAIN_DB[s]["media_cost_usd"],
                "Cryo Cost (USD/batch)": STRAIN_DB[s]["cryo_cost_usd"],
            }
        )
    df_strain_params = pd.DataFrame(strain_params_data)

    # Create raw material prices DataFrame
    df_raw_prices = pd.DataFrame(
        list(RAW_PRICES.items()), columns=["Material", "Price (USD/kg)"]
    )

    # Generate detailed reports
    detailed_opex_df = generate_detailed_opex_report(
        strains,
        fermenters,
        ds_lines,
        fermenter_volume_L,
        target_tpa,
        plant_kg_good,
        plant_batches_good,
    )
    detailed_capex_df = generate_detailed_capex_report(
        fermenters, ds_lines, fermenter_volume_L, target_tpa
    )
    pl_df, pl_summary_df = generate_detailed_pl_statement(
        strains,
        fermenters,
        ds_lines,
        fermenter_volume_L,
        target_tpa,
        plant_kg_good,
        plant_batches_good,
        anaerobic,
        premium_spores,
        sacco,
    )

    # Create output dictionary with detailed reports as first sheets
    out = {
        "Executive Summary": df_summary,  # Move summary to first
        "P&L Statement (10Y)": pl_df,
        "Financial Metrics": pl_summary_df,
        "Detailed OPEX Breakdown": detailed_opex_df,
        "Detailed CAPEX Breakdown": detailed_capex_df,
        "Calc-PerStrain": det_df,
        "Process Parameters": df_proc,
        "Media Costs": df_media,
        "Cryoprotectants": df_cryo,
        "Equipment Sizing": df_equip,
        "CAPEX Summary": df_capex,
        "OPEX Summary": df_opex,
        "Financials (10y)": df_fin,
        "Assumptions": df_assump,
        "Strain Parameters": df_strain_params,
        "Raw Material Prices": df_raw_prices,
    }
    if optimize_equipment and use_multiobjective:
        out["Pareto Frontier"] = pareto_df[
            [
                "fermenter_volume_L",
                "reactors",
                "ds_lines",
                "capex",
                "irr",
                "npv",
                "plant_kg_good",
                "util_up",
                "util_ds",
            ]
        ]
        out["All Feasible Configurations"] = all_df[all_df["meets_capacity"]][
            [
                "fermenter_volume_L",
                "reactors",
                "ds_lines",
                "capex",
                "irr",
                "npv",
                "plant_kg_good",
                "util_up",
                "util_ds",
            ]
        ]
    return out


# ============ Build models (same four facilities) ============
def write_book(path, model_dict):
    with pd.ExcelWriter(path, engine="xlsxwriter") as writer:
        for sheet, df in model_dict.items():
            df.to_excel(writer, sheet_name=sheet, index=False)
        wb = writer.book
        for sheet in model_dict.keys():
            ws = writer.sheets[sheet]
            ws.set_zoom(110)
            ws.set_column(0, max(2, len(model_dict[sheet].columns)), 18)


if __name__ == '__main__':
    fac1 = facility_model(
        "Facility 1 - Yogurt Cultures (10 TPA)",
        target_tpa=10,
        strains=[
            "S. thermophilus",
            "L. delbrueckii subsp. bulgaricus",
            "L. acidophilus",
            "B. animalis subsp. lactis",
        ],
        fermenters_suggested=4,
        lyos_guess=2,
        anaerobic=False,
        premium_spores=False,
        sacco=False,
        optimize_equipment=True,
        use_multiobjective=True,
        fermenter_volumes_to_test=[500, 1000, 1500, 2000, 3000, 4000, 5000],
        use_stochastic=False,
        stochastic_objective="irr_p10",
    )
    fac2 = facility_model(
        "Facility 2 - Lacto/Bifido (10 TPA)",
        target_tpa=10,
        strains=["L. rhamnosus GG", "L. casei", "L. plantarum", "B. breve", "B. longum"],
        fermenters_suggested=5,
        lyos_guess=2,
        anaerobic=True,
        premium_spores=False,
        sacco=False,
        optimize_equipment=True,
        use_multiobjective=True,
        fermenter_volumes_to_test=[500, 1000, 1500, 2000, 3000, 4000, 5000],
        use_stochastic=False,
        stochastic_objective="irr_p10",
    )
    fac3 = facility_model(
        "Facility 3 - Bacillus Spores (10 TPA)",
        target_tpa=10,
        strains=["Bacillus coagulans", "Bacillus subtilis"],
        fermenters_suggested=2,
        lyos_guess=1,
        anaerobic=False,
        premium_spores=True,
        sacco=False,
        optimize_equipment=True,
        use_multiobjective=True,
        fermenter_volumes_to_test=[500, 1000, 1500, 2000, 3000, 4000, 5000],
        use_stochastic=False,
        stochastic_objective="irr_p10",
    )
    fac4 = facility_model(
        "Facility 4 - Yeast Based Probiotic (10 TPA)",
        target_tpa=10,
        strains=["Saccharomyces boulardii"],
        fermenters_suggested=4,
        lyos_guess=2,
        anaerobic=False,
        premium_spores=False,
        sacco=True,
        optimize_equipment=True,
        use_multiobjective=True,
        fermenter_volumes_to_test=[500, 1000, 1500, 2000, 3000, 4000, 5000],
        use_stochastic=False,
        stochastic_objective="irr_p10",
    )
    fac5 = facility_model(
        "Facility 5 - ALL IN (40 TPA)",
        target_tpa=40,
        strains=[
            "Saccharomyces boulardii",
            "Bacillus coagulans",
            "Bacillus subtilis",
            "L. rhamnosus GG",
            "L. casei",
            "L. plantarum",
            "B. breve",
            "B. longum",
            "S. thermophilus",
            "L. delbrueckii subsp. bulgaricus",
            "L. acidophilus",
            "B. animalis subsp. lactis",
        ],
        fermenters_suggested=4,
        lyos_guess=2,
        anaerobic=True,
        premium_spores=True,
        sacco=True,
        optimize_equipment=True,
        use_multiobjective=True,
        fermenter_volumes_to_test=[500, 1000, 1500, 2000, 3000, 4000, 5000],
        use_stochastic=False,
        stochastic_objective="irr_p10",
    )
    write_book(out1, fac1)
    write_book(out2, fac2)
    write_book(out3, fac3)
    write_book(out4, fac4)
    write_book(out5, fac5)
    print("Created files:", out1, out2, out3, out4, out5)
