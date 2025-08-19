"""
Default configurations, assumptions, and strain database.
Extracted from pricing_integrated.py for modular use.
"""

from typing import Dict, Any

# Global economic assumptions (2025 USD)
ASSUMPTIONS: Dict[str, Any] = {
    "hours_per_year": 8760.0,
    "upstream_availability": 0.92,
    "downstream_availability": 0.90,
    "quality_yield": 0.98,
    "discount_rate": 0.10,
    "tax_rate": 0.25,
    "variable_opex_share": 0.85,
    "maintenance_pct_of_equip": 0.09,
    "ga_other_scale_factor": 460000 / 42445.0,
    # Product prices (USD/kg)
    "price_yogurt_usd_per_kg": 400,
    "price_lacto_bifido_usd_per_kg": 400,
    "price_bacillus_usd_per_kg": 400,
    "price_sacco_usd_per_kg": 500,
    # Labor costs (USD/year with 30% benefits)
    "plant_manager_salary": 80000 * 1.3,
    "fermentation_specialist_salary": 30000 * 1.3,
    "downstream_process_operator_salary": 40000 * 1.3,
    "general_technician_salary": 25000 * 1.3,
    "qaqc_lab_tech_salary": 30000 * 1.3,
    "maintenance_tech_salary": 30000 * 1.3,
    "utility_operator_salary": 30000 * 1.3,
    "logistics_clerk_salary": 30000 * 1.3,
    "office_clerk_salary": 25000 * 1.3,
}

# Raw material prices (USD/kg)
RAW_PRICES: Dict[str, float] = {
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

# Strain database with media and cryo costs
STRAIN_DB: Dict[str, Dict[str, Any]] = {
    "S. thermophilus": {
        "t_fedbatch_h": 14.0,
        "media_cost_usd": (
            RAW_PRICES["Lactose"] * 32
            + RAW_PRICES["Yeast Extract"] * 24
            + RAW_PRICES["K2HPO4"] * 3.2
            + RAW_PRICES["KH2PO4"] * 3.2
        ),
        "cryo_cost_usd": (
            RAW_PRICES["Skim Milk"] * 10.7
            + RAW_PRICES["Trehalose"] * 5.35
            + RAW_PRICES["Sucrose"] * 5.35
        ),
        "licensing_fixed_cost_usd": 0.0,
        "licensing_royalty_pct": 0.0,
        "respiration_type": "aerobic",
        "requires_tff": False,
        "downstream_complexity": 1.0,
    },
    "L. delbrueckii subsp. bulgaricus": {
        "t_fedbatch_h": 24.0,
        "media_cost_usd": (
            RAW_PRICES["Whey Powder"] * 64
            + RAW_PRICES["Yeast Extract"] * 10
            + RAW_PRICES["Dextrose"] * 20
            + RAW_PRICES["K2HPO4"] * 3.4
        ),
        "cryo_cost_usd": (
            RAW_PRICES["Skim Milk"] * 10.7
            + RAW_PRICES["Sucrose"] * 5.35
            + RAW_PRICES["Soy Peptone"] * 5.35
        ),
        "licensing_fixed_cost_usd": 0.0,
        "licensing_royalty_pct": 0.0,
        "respiration_type": "aerobic",
        "requires_tff": False,
        "downstream_complexity": 1.0,
    },
    "L. acidophilus": {
        "t_fedbatch_h": 18.0,
        "media_cost_usd": (
            RAW_PRICES["Whey Powder"] * 10 * 1.6
            + RAW_PRICES["Soy Peptone"] * 30 * 1.6
            + RAW_PRICES["Glucose"] * 5 * 1.6
            + RAW_PRICES["Tween_80"] * 1.0 * 1.6
            + RAW_PRICES["MgSO4x7H2O"] * 1.0 * 1.6
            + RAW_PRICES["MnSO4xH2O"] * 0.06 * 1.6
            + RAW_PRICES["ZnSO4x7H2O"] * 0.01 * 1.6
        ),
        "cryo_cost_usd": (
            RAW_PRICES["Skim Milk"] * 10.7
            + RAW_PRICES["Trehalose"] * 5.35
            + RAW_PRICES["Sucrose"] * 5.35
            + RAW_PRICES["Sodium Ascorbate"] * 0.7
        ),
        "licensing_fixed_cost_usd": 0.0,
        "licensing_royalty_pct": 0.0,
        "respiration_type": "aerobic",
        "requires_tff": True,  # Shear-sensitive
        "downstream_complexity": 1.0,
    },
    "B. animalis subsp. lactis": {
        "t_fedbatch_h": 15.0,
        "media_cost_usd": (
            RAW_PRICES["Yeast Extract"] * 28.8
            + RAW_PRICES["Soy Peptone"] * 28.0
            + RAW_PRICES["Glucose"] * 6.2
            + RAW_PRICES["L-cysteine HCl"] * 2.8
            + RAW_PRICES["FeSO4"] * 0.055
        ),
        "cryo_cost_usd": (
            RAW_PRICES["Skim Milk"] * 15
            + RAW_PRICES["Lactose"] * 5
            + RAW_PRICES["Sucrose"] * 5
            + RAW_PRICES["Sodium Ascorbate"] * 1
        ),
        "licensing_fixed_cost_usd": 0.0,
        "licensing_royalty_pct": 0.0,
        "respiration_type": "anaerobic",  # Bifidobacterium are obligate anaerobes
        "requires_tff": True,
        "downstream_complexity": 1.0,
    },
    "L. rhamnosus GG": {
        "t_fedbatch_h": 22.0,
        "media_cost_usd": (
            RAW_PRICES["Glucose"] * 112.5 * 1.6
            + RAW_PRICES["Molasses"] * 56.25 * 1.6
            + RAW_PRICES["Casein"] * 18.75 * 1.6
            + RAW_PRICES["Yeast Extract"] * 18.75 * 1.6
            + RAW_PRICES["K2HPO4"] * 13.13 * 1.6
            + RAW_PRICES["Tween_80"] * 1.88 * 1.6
            + RAW_PRICES["Simethicone"] * 1.25 * 1.6
            + RAW_PRICES["CaCl2"] * 0.1875 * 1.6
            + RAW_PRICES["MgSO4x7H2O"] * 0.375 * 1.6
            + RAW_PRICES["MnSO4xH2O"] * 0.075 * 1.6
        ),
        "cryo_cost_usd": (
            RAW_PRICES["Skim Milk"] * 10
            + RAW_PRICES["Trehalose"] * 5
            + RAW_PRICES["Sucrose"] * 5
        ),
        "licensing_fixed_cost_usd": 0.0,
        "licensing_royalty_pct": 0.0,
        "respiration_type": "facultative",  # Can grow aerobically or anaerobically
        "requires_tff": True,
        "downstream_complexity": 1.0,
    },
    "L. casei": {
        "t_fedbatch_h": 24.0,
        "media_cost_usd": (
            RAW_PRICES["Sucrose"] * 100
            + RAW_PRICES["CSL"] * 50
            + RAW_PRICES["Yeast Extract"] * 10
            + RAW_PRICES["K2HPO4"] * 5
            + RAW_PRICES["KH2PO4"] * 2
        ),
        "cryo_cost_usd": (RAW_PRICES["Skim Milk"] * 15 + RAW_PRICES["Sucrose"] * 5),
        "licensing_fixed_cost_usd": 0.0,
        "licensing_royalty_pct": 0.0,
        "respiration_type": "facultative",
        "requires_tff": True,
        "downstream_complexity": 1.0,
    },
    "L. plantarum": {
        "t_fedbatch_h": 12.0,
        "media_cost_usd": (
            RAW_PRICES["Glucose"] * 50
            + RAW_PRICES["Soy Peptone"] * 20
            + RAW_PRICES["K2HPO4"] * 3.2
            + RAW_PRICES["KH2PO4"] * 3.2
            + RAW_PRICES["Sodium_Acetate"] * 5.0 * 1.6
            + RAW_PRICES["Tween_80"] * 0.2 * 1.6
            + RAW_PRICES["MgSO4x7H2O"] * 0.3 * 1.6
            + RAW_PRICES["MnSO4xH2O"] * 0.04 * 1.6
        ),
        "cryo_cost_usd": (
            RAW_PRICES["Skim Milk"] * 10
            + RAW_PRICES["Trehalose"] * 5
            + RAW_PRICES["Sucrose"] * 5
        ),
        "licensing_fixed_cost_usd": 0.0,
        "licensing_royalty_pct": 0.0,
        "respiration_type": "facultative",
        "requires_tff": True,
        "downstream_complexity": 1.0,
    },
    "B. breve": {
        "t_fedbatch_h": 16.0,
        "media_cost_usd": (
            RAW_PRICES["Yeast Extract"] * 28.8
            + RAW_PRICES["Soy Peptone"] * 28.0
            + RAW_PRICES["Glucose"] * 6.2
            + RAW_PRICES["L-cysteine HCl"] * 2.8
            + RAW_PRICES["FeSO4"] * 0.055
        ),
        "cryo_cost_usd": (
            RAW_PRICES["Skim Milk"] * 28
            + RAW_PRICES["Lactose"] * 10
            + RAW_PRICES["Sucrose"] * 10
            + RAW_PRICES["Sodium Ascorbate"] * 2
        ),
        "licensing_fixed_cost_usd": 0.0,
        "licensing_royalty_pct": 0.0,
        "respiration_type": "anaerobic",  # Bifidobacterium are obligate anaerobes
        "requires_tff": True,
        "downstream_complexity": 1.0,
    },
    "B. longum": {
        "t_fedbatch_h": 12.0,
        "media_cost_usd": (
            RAW_PRICES["Yeast Extract"] * 28.8
            + RAW_PRICES["Soy Peptone"] * 28.0
            + RAW_PRICES["Glucose"] * 6.2
            + RAW_PRICES["L-cysteine HCl"] * 2.8
            + RAW_PRICES["FeSO4"] * 0.055
            + RAW_PRICES["MgSO4x7H2O"] * 1.0 * 1.6
            + RAW_PRICES["Sodium_Citrate"] * 1.0 * 1.6
        ),
        "cryo_cost_usd": (
            RAW_PRICES["Skim Milk"] * 25
            + RAW_PRICES["Lactose"] * 10
            + RAW_PRICES["Sucrose"] * 10
            + RAW_PRICES["Sodium Ascorbate"] * 1.5
        ),
        "licensing_fixed_cost_usd": 0.0,
        "licensing_royalty_pct": 0.0,
        "respiration_type": "anaerobic",  # Bifidobacterium are obligate anaerobes
        "requires_tff": True,
        "downstream_complexity": 1.0,
    },
    "Bacillus coagulans": {
        "t_fedbatch_h": 36.0,
        "media_cost_usd": (
            RAW_PRICES["Glucose"] * 32
            + RAW_PRICES["Soy Peptone"] * 20
            + RAW_PRICES["K2HPO4"] * 3.2
            + RAW_PRICES["KH2PO4"] * 3.2
        ),
        "cryo_cost_usd": (RAW_PRICES["Skim Milk"] * 3 + RAW_PRICES["Sucrose"] * 3),
        "licensing_fixed_cost_usd": 0.0,
        "licensing_royalty_pct": 0.0,
        "respiration_type": "aerobic",  # Spore-formers are typically aerobic
        "requires_tff": False,
        "downstream_complexity": 1.2,  # Spores require additional processing
    },
    "Bacillus subtilis": {
        "t_fedbatch_h": 30.0,
        "media_cost_usd": (
            (
                RAW_PRICES["Glucose"] * 20
                + RAW_PRICES["Soy Peptone"] * 20
                + RAW_PRICES["K2HPO4"] * 3.2
                + RAW_PRICES["MnSO4xH2O"] * 0.1
            )
            * 1.6
        ),
        "cryo_cost_usd": (RAW_PRICES["Skim Milk"] * 3 + RAW_PRICES["Sucrose"] * 3),
        "licensing_fixed_cost_usd": 0.0,
        "licensing_royalty_pct": 0.0,
        "respiration_type": "aerobic",  # Spore-formers are typically aerobic
        "requires_tff": False,
        "downstream_complexity": 1.2,  # Spores require additional processing
    },
    "Saccharomyces boulardii": {
        "t_fedbatch_h": 31.0,
        "media_cost_usd": (
            RAW_PRICES["Glucose"] * 400
            + RAW_PRICES["Yeast Extract"] * 12
            + RAW_PRICES["K2HPO4"] * 4
            + RAW_PRICES["MgSO4x7H2O"] * 1.33
        ),
        "cryo_cost_usd": (
            RAW_PRICES["Skim Milk"] * 10
            + RAW_PRICES["Trehalose"] * 5
            + RAW_PRICES["Sucrose"] * 5
            + RAW_PRICES["Sodium Ascorbate"] * 1
        ),
        "licensing_fixed_cost_usd": 0.0,
        "licensing_royalty_pct": 0.0,
        "respiration_type": "aerobic",  # Yeast are typically aerobic
        "requires_tff": False,
        "downstream_complexity": 1.0,  # Standard yeast processing
    },
}

# Strain batch database with process times and yields
STRAIN_BATCH_DB: Dict[str, Dict[str, Any]] = {
    "S. thermophilus": {
        "t_fedbatch_h": 14.0,
        "t_turnaround_h": 9.0,
        "t_downstrm_h": 4.0,
        "cv_ferm": 0.1,
        "cv_turn": 0.1,
        "cv_down": 0.1,
        "yield_g_per_L": 3.0,
        "utility_rate_ferm_kw": 18 * 14,  # Total kWh per batch
        "utility_rate_cent_kw": 15,  # kW/m³ rate
        "utility_rate_lyo_kw": 1.5,  # kW per liter of concentrate
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

# Default facility configurations
DEFAULT_FACILITIES = {
    "facility_1_yogurt": {
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
    "facility_2_lacto": {
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
    },
    "facility_3_bacillus": {
        "name": "Facility 3 - Bacillus Spores (10 TPA)",
        "target_tpa": 10,
        "strains": ["Bacillus coagulans", "Bacillus subtilis"],
        "fermenters_suggested": 2,
        "lyos_guess": 1,
        "anaerobic": False,
        "premium_spores": True,
        "sacco": False,
    },
    "facility_4_yeast": {
        "name": "Facility 4 - Yeast Based Probiotic (10 TPA)",
        "target_tpa": 10,
        "strains": ["Saccharomyces boulardii"],
        "fermenters_suggested": 4,
        "lyos_guess": 2,
        "anaerobic": False,
        "premium_spores": False,
        "sacco": True,
    },
    "facility_5_all": {
        "name": "Facility 5 - ALL IN (40 TPA)",
        "target_tpa": 40,
        "strains": [
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
        "fermenters_suggested": 4,
        "lyos_guess": 2,
        "anaerobic": True,
        "premium_spores": True,
        "sacco": True,
    },
}

# Utility rates
UTILITY_RATES = {
    "electricity_usd_per_kwh": 0.107,
    "steam_usd_per_kg": 0.0228,
    "water_usd_per_m3": 0.002,
    "natural_gas_usd_per_mmbtu": 3.50,
}

# Equipment cost factors
EQUIPMENT_COST_FACTORS = {
    "fermenter_base_cost": 150000,  # Base cost for 2000L fermenter
    "fermenter_scale_exponent": 0.6,  # Cost scaling exponent
    "centrifuge_cost": 200000,
    "tff_skid_cost": 150000,
    "lyophilizer_cost_per_m2": 50000,
    "utilities_cost_factor": 0.25,  # As fraction of process equipment
    "installation_factor": 0.15,  # Installation as fraction of equipment
}

# Financial parameters for different scenarios
FINANCIAL_SCENARIOS = {
    "conservative": {
        "discount_rate": 0.12,
        "tax_rate": 0.30,
        "contingency_factor": 0.15,
    },
    "base": {
        "discount_rate": 0.10,
        "tax_rate": 0.25,
        "contingency_factor": 0.125,
    },
    "optimistic": {
        "discount_rate": 0.08,
        "tax_rate": 0.20,
        "contingency_factor": 0.10,
    },
}


def get_default_assumptions() -> Dict[str, Any]:
    """Get a copy of default assumptions."""
    return ASSUMPTIONS.copy()


def get_raw_prices() -> Dict[str, float]:
    """Get a copy of raw material prices."""
    return RAW_PRICES.copy()


def get_strain_info(strain_name: str) -> Dict[str, Any]:
    """Get information for a specific strain."""
    if strain_name in STRAIN_DB:
        return {**STRAIN_DB[strain_name], **STRAIN_BATCH_DB.get(strain_name, {})}
    raise ValueError(f"Strain '{strain_name}' not found in database")


def get_all_strains() -> Dict[str, Dict[str, Any]]:
    """Get dictionary of all available strains with their data."""
    result = {}
    # Get all unique strain names from both databases
    all_strain_names = set(STRAIN_DB.keys()) | set(STRAIN_BATCH_DB.keys())

    for strain_name in all_strain_names:
        # Start with empty dict
        strain_data = {}

        # Add data from STRAIN_DB if exists
        if strain_name in STRAIN_DB:
            strain_data.update(STRAIN_DB[strain_name])

        # Add/merge data from STRAIN_BATCH_DB if exists
        if strain_name in STRAIN_BATCH_DB:
            strain_data.update(STRAIN_BATCH_DB[strain_name])

        result[strain_name] = strain_data

    return result


def parse_media_components(
    strain_name: str,
) -> tuple[Dict[str, float], Dict[str, float]]:
    """Parse media and cryo components with quantities for a specific strain.
    Returns tuple of (media_components, cryo_components) dicts with component names as keys
    and kg per 1600L working volume as values.
    """
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
