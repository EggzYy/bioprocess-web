"""
Constants and configuration values for the bioprocess application.
Extracts magic numbers and provides default values.
"""

from typing import Dict, List, Tuple

# Fermentation parameters
DEFAULT_BASE_WORKING_VOLUME_L: float = 1600.0  # Base working volume (2000L @ 0.8)
DEFAULT_FERMENTER_VOLUME_L: float = 2000.0  # Default fermenter size
DEFAULT_WORKING_VOLUME_FRACTION: float = 0.8  # Default working volume fraction

# Equipment sizing defaults
BASE_VOLUME_EQUIPMENT_SIZING: float = 2000.0  # Base volume for equipment cost scaling
DEFAULT_SEED_FERMENTER_RATIO: float = 0.125  # Seed fermenter size as fraction of main
DEFAULT_MEDIA_TANK_RATIO: float = 1.25  # Media tank size as multiple of fermenter
DEFAULT_SEED_FERMENTER_COUNT_RATIO: float = 0.7  # Seed fermenters as ratio of main
DEFAULT_LYOPHILIZER_SIZE_M2: float = 20.0  # Default lyophilizer size

# Optimization constraints
DEFAULT_MAX_REACTORS: int = 60
DEFAULT_MAX_DS_LINES: int = 12
DEFAULT_MIN_REACTORS: int = 2
DEFAULT_MIN_DS_LINES: int = 1
MAX_ALLOWED_EXCESS: float = 0.2  # Maximum allowed excess capacity ratio

# Progressive excess tolerance tiers (for capacity enforcement)
EXCESS_TOLERANCE_TIERS: List[float] = [0.05, 0.15, 0.25]

# Economic parameters
DEFAULT_FTE_COUNT: float = 15.0  # Minimum FTE count in parity mode
DEFAULT_FTE_PER_TPA: float = 1.0  # FTE scaling factor
DEFAULT_PROJECT_YEARS: int = 12
DEFAULT_DEPRECIATION_YEARS: int = 10
CAPEX_YEAR_0_RATIO: float = 0.70  # Year 0 CAPEX investment ratio
CAPEX_YEAR_1_RATIO: float = 0.30  # Year 1 CAPEX investment ratio

# Ramp-up schedule
DEFAULT_RAMP_UP_SCHEDULE: List[float] = [0.40, 0.60, 0.75, 0.85] + [0.85] * 7

# Equipment costs (base values)
DEFAULT_BASE_FERMENTER_COST: float = 150000.0
DEFAULT_SEED_FERMENTER_BASE_COST_RATIO: float = 0.3  # Seed fermenter cost ratio
DEFAULT_MEDIA_TANK_BASE_COST_RATIO: float = 0.2  # Media tank cost ratio

# Utility infrastructure costs
UTILITY_INFRASTRUCTURE_COSTS: Dict[str, float] = {
    "autoclave": 100000,
    "purified_water": 150000,
    "wfi_system": 400000,
    "clean_steam": 120000,
    "cip_system": 250000,
}

# Auxiliary equipment costs
AUXILIARY_EQUIPMENT_COSTS: Dict[str, Tuple[int, float]] = {
    "cone_mill": (1, 50000),
    "v_blender": (1, 30000),
    "qc_lab": (1, 250000),
}

# Scaling exponents
DEFAULT_SCALE_EXPONENT: float = 0.6  # Six-tenths rule

# Depreciation rates (MACRS 7-year)
MACRS_7_YEAR: List[float] = [
    0.1429, 0.2449, 0.1749, 0.1249, 0.0893, 0.0892, 0.0893, 0.0446
]

# Facility area defaults (m²)
FACILITY_AREA_DEFAULTS: Dict[str, float] = {
    "base_area": 1000,
    "fermenter_area_per_unit": 50,
    "fermenter_area_volume_factor": 10,  # per 1000L
    "ds_area_per_line": 100,
    "seed_lab": 100,
    "qc_lab": 150,
    "warehouse_base": 200,
    "warehouse_per_fermenter": 20,
    "utilities_base": 150,
    "utilities_per_fermenter": 10,
    "offices": 200,
    "corridors_hvac_factor": 0.3,  # 30% of production area
}

# Product prices defaults
DEFAULT_PRODUCT_PRICE: float = 400.0  # $/kg default product price

# Raw material prices defaults
DEFAULT_RAW_PRICES: Dict[str, float] = {
    "Glucose": 0.5,
    "Yeast Extract": 2.5,
    "Peptone": 3.0,
    "Salt": 0.1,
    "Other": 1.0,
}

# Economic assumptions defaults
DEFAULT_DISCOUNT_RATE: float = 0.10
DEFAULT_TAX_RATE: float = 0.25
DEFAULT_MAINTENANCE_PCT: float = 0.09
DEFAULT_GA_OTHER_SCALE_FACTOR: float = 10.84
DEFAULT_VARIABLE_OPEX_SHARE: float = 0.85
DEFAULT_CONTINGENCY_FACTOR: float = 0.125
DEFAULT_INSTALLATION_FACTOR: float = 0.15
DEFAULT_WORKING_CAPITAL_MONTHS: float = 3.0

# Labor defaults
LABOR_ROLE_SALARIES: Dict[str, int] = {
    "plant_manager": 104000,
    "fermentation_specialist": 39000,
    "downstream_process_operator": 52000,
    "general_technician": 32500,
    "qaqc_lab_tech": 39000,
    "maintenance_tech": 39000,
    "utility_operator": 39000,
    "logistics_clerk": 39000,
    "office_clerk": 32500,
}

# API defaults
DEFAULT_MAX_BATCH_SIZE: int = 50
DEFAULT_PAGE_SIZE: int = 50
MAX_CONCURRENT_JOBS: int = 100

# Logging configuration
LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"

# Excluded files from processing (for testing/linting)
EXCLUDED_FILES: List[str] = [
    "bioprocess/pricing_integrated_original.py",
    "bioprocess/fermentation_capacity_calculator.py",
]
