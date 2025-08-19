#!/usr/bin/env python3
"""
Safe loader for strain databases from pricing_integrated.py
This avoids executing the file generation code at module level.
"""

# Define the strain databases directly to avoid importing and executing pricing_integrated.py
# These are copied from the parent file to avoid side effects

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
        "licensing_fixed_cost_usd": 0.0,
        "licensing_royalty_pct": 0.0,
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
        "licensing_fixed_cost_usd": 0.0,
        "licensing_royalty_pct": 0.0,
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
        "licensing_fixed_cost_usd": 100000.0,
        "licensing_royalty_pct": 0.0,
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
        "licensing_fixed_cost_usd": 100000.0,
        "licensing_royalty_pct": 0.0,
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
        "licensing_fixed_cost_usd": 100000.0,
        "licensing_royalty_pct": 0.0,
    },
    "L. casei": {
        "t_fedbatch_h": 24.0,
        "media_cost_usd": RAW_PRICES["Sucrose"] * 100
        + RAW_PRICES["CSL"] * 50
        + RAW_PRICES["Yeast Extract"] * 10
        + RAW_PRICES["K2HPO4"] * 5
        + RAW_PRICES["KH2PO4"] * 2,
        "cryo_cost_usd": RAW_PRICES["Skim Milk"] * 15 + RAW_PRICES["Sucrose"] * 5,
        "licensing_fixed_cost_usd": 100000.0,
        "licensing_royalty_pct": 0.0,
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
        "licensing_fixed_cost_usd": 100000.0,
        "licensing_royalty_pct": 0.0,
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
        "licensing_fixed_cost_usd": 100000.0,
        "licensing_royalty_pct": 0.0,
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
        "licensing_fixed_cost_usd": 100000.0,
        "licensing_royalty_pct": 0.0,
    },
    "Bacillus coagulans": {
        "t_fedbatch_h": 36.0,
        "media_cost_usd": RAW_PRICES["Glucose"] * 32
        + RAW_PRICES["Soy Peptone"] * 20
        + RAW_PRICES["K2HPO4"] * 3.2
        + RAW_PRICES["KH2PO4"] * 3.2,
        "cryo_cost_usd": RAW_PRICES["Skim Milk"] * 3 + RAW_PRICES["Sucrose"] * 3,
        "licensing_fixed_cost_usd": 100000.0,
        "licensing_royalty_pct": 0.0,
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
        "licensing_fixed_cost_usd": 100000.0,
        "licensing_royalty_pct": 0.0,
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
        "licensing_fixed_cost_usd": 100000.0,
        "licensing_royalty_pct": 0.0,
    },
}

STRAIN_BATCH_DB = {
    "S. thermophilus": {
        "t_fedbatch_h": 14.0,
        "t_turnaround_h": 9.0,
        "t_downstrm_h": 4.0,
        "cv_ferm": 0.1,
        "cv_turn": 0.1,
        "cv_down": 0.1,
        "yield_g_per_L": 3.0,
        "utility_rate_ferm_kw": 18 * 14,
        "utility_rate_cent_kw": 15,
        "utility_rate_lyo_kw": 1.5,
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
        "utility_rate_ferm_kw": 18 * 24,
        "utility_rate_cent_kw": 15,
        "utility_rate_lyo_kw": 1.5,
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
        "utility_rate_ferm_kw": 18 * 18,
        "utility_rate_cent_kw": 15,
        "utility_rate_lyo_kw": 1.5,
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
        "utility_rate_ferm_kw": 18 * 15,
        "utility_rate_cent_kw": 15,
        "utility_rate_lyo_kw": 1.5,
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
        "utility_rate_ferm_kw": 18 * 22,
        "utility_rate_cent_kw": 15,
        "utility_rate_lyo_kw": 1.5,
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
        "utility_rate_ferm_kw": 18 * 24,
        "utility_rate_cent_kw": 15,
        "utility_rate_lyo_kw": 1.5,
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
        "utility_rate_ferm_kw": 18 * 12,
        "utility_rate_cent_kw": 15,
        "utility_rate_lyo_kw": 1.5,
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
        "utility_rate_ferm_kw": 18 * 16,
        "utility_rate_cent_kw": 15,
        "utility_rate_lyo_kw": 1.5,
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
        "utility_rate_ferm_kw": 18 * 12,
        "utility_rate_cent_kw": 15,
        "utility_rate_lyo_kw": 1.5,
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
        "utility_rate_ferm_kw": 18 * 36,
        "utility_rate_cent_kw": 15,
        "utility_rate_lyo_kw": 1.5,
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
        "utility_rate_ferm_kw": 18 * 30,
        "utility_rate_cent_kw": 15,
        "utility_rate_lyo_kw": 1.5,
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
        "utility_rate_ferm_kw": 18 * 31,
        "utility_rate_cent_kw": 15,
        "utility_rate_lyo_kw": 1.5,
        "price_sacco_usd_per_kg": 500,
    },
}
