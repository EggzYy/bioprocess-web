# Repository Map: Bioprocess Optimization System

## Directory Structure
```
Project_Hasan/
├── pricing_integrated.py           # Original generator (parent directory)
├── pricing_integrated_fixed.py     # Fixed version with 80% working volume
├── pricing_integrated_algae.py     # Algae variant
├── Facility*_calc.xlsx            # Generated Excel workbooks (9 files)
└── bioprocess-web/
    ├── cross_validation_proper.py     # Cross-validation driver (uses original + new)
    ├── tests/                          # Test suite (API, WebSocket, parity)
    ├── bioprocess/                     # New implementation modules
    │   ├── __init__.py
    │   ├── models.py                   # ScenarioInput, StrainInput, EquipmentConfig
    │   ├── orchestrator.py             # run_scenario() main entry point
    │   ├── presets.py                  # RAW_PRICES and constants
    │   ├── capacity.py                 # Capacity calculations
    │   ├── econ.py                     # Economics calculations
    │   ├── excel.py                    # Excel export utilities
    │   ├── equipment_optimizer.py      # Equipment optimization
    │   ├── optimizer.py                # Baseline optimizer used by orchestrator
    │   ├── optimizer_enhanced.py       # Enhanced optimizer with progressive excess constraints (optional)
    │   └── sizing.py                   # Equipment sizing
    ├── api/                            # FastAPI implementation
    ├── tests/                          # Test suite
    ├── docs/                           # Documentation
    └── tools/                          # Utilities (to be created)
```

## Key Components

### 1. Original Generator
- **Path:** `/home/eggzy/Downloads/Project_Hasan/pricing_integrated.py`
- **Purpose:** Generates Excel workbooks with facility calculations
- **Output:** Creates `Facility*_calc.xlsx` files with sheets:
  - Calc-PerStrain
  - CAPEX Summary / Detailed CAPEX Breakdown
  - OPEX Summary
  - Pareto Frontier / All Feasible Configurations
  - Executive Summary (NOT TO BE USED)
  - Financial Metrics (NOT TO BE USED)

### 2. Fixed Generator
- **Path:** `/home/eggzy/Downloads/Project_Hasan/pricing_integrated_fixed.py`
- **Purpose:** Wrapper around original with consistent 80% working volume
- **Key Functions:**
  - `build_strainspecs()` - overridden to use 80% volume
  - `weighted_royalty_rate()` - fixed for consistency
  - `facility_model()` - imported from original

### 3. Cross-Validation Driver
- **Path:** `/home/eggzy/Downloads/Project_Hasan/bioprocess-web/cross_validation_with_fixed.py`
- **Current Behavior:** 
  - Imports from `pricing_integrated_fixed`
  - Calls `facility_model()` directly (NEEDS REFACTORING)
  - Compares with new implementation via `run_scenario()`
- **Required Changes:**
  - Replace facility_model calls with Excel parsing
  - Read metrics from XLSX files per policy

### 4. New Implementation
- **Entry Point:** `bioprocess.orchestrator.run_scenario(scenario: ScenarioInput)`
- **Key Models:**
  - `ScenarioInput`: Main input container
  - `StrainInput`: Strain specifications
  - `EquipmentConfig`: Equipment configuration
- **Supporting Modules:**
  - `capacity.py`: Production capacity calculations
  - `econ.py`: Economic calculations
  - `presets.py`: Constants including RAW_PRICES

## Optimizer Modules

- optimizer.py: Baseline optimizer used by orchestrator (optimize_with_capacity_enforcement imported via optimizer_enhanced)
- optimizer_enhanced.py: Provides progressive excess tolerance and Pareto knee selection; orchestrator currently uses optimize_with_capacity_enforcement from this module

## Excel Workbook Locations

### Parent Directory (Primary)
- `/home/eggzy/Downloads/Project_Hasan/`
  - Facility1_Yogurt_Cultures_10TPA_calc.xlsx
  - Facility1_Yogurt_Cultures_20TPA_calc.xlsx
  - Facility2_Lacto_Bifido_10TPA_calc.xlsx
  - Facility2_Lacto_Bifido_20TPA_calc.xlsx
  - Facility3_Bacillus_Spores_10TPA_calc.xlsx
  - Facility3_Bacillus_Spores_20TPA_calc.xlsx
  - Facility4_Yeast_Probiotic_10TPA_calc.xlsx
  - Facility4_Yeast_Probiotic_20TPA_calc.xlsx
  - Facility5_ALL_IN_40TPA_calc.xlsx

### bioprocess-web Directory (Copies)
- `/home/eggzy/Downloads/Project_Hasan/bioprocess-web/`
  - Facility1_Yogurt_Cultures_10TPA_calc.xlsx
  - Facility2_Lacto_Bifido_10TPA_calc.xlsx
  - Facility3_Bacillus_Spores_10TPA_calc.xlsx
  - Facility4_Yeast_Probiotic_10TPA_calc.xlsx
  - Facility5_ALL_IN_40TPA_calc.xlsx

## Import Relationships

### cross_validation_with_fixed.py imports:
- `pricing_integrated_fixed` (parent dir) - TO BE REMOVED
- `bioprocess.models` - ScenarioInput, StrainInput, EquipmentConfig
- `bioprocess.orchestrator` - run_scenario
- `bioprocess.presets` - RAW_PRICES

### pricing_integrated_fixed.py imports:
- `pricing_integrated` - all functions and constants
- `fermentation_capacity_calculator` - StrainSpec, EquipmentConfig, calculations

## Refactoring Notes

1. **Excel Parser Module** (to be created at `tools/xlsx_metrics.py`):
   - Parse metrics from XLSX per policy
   - No Executive Summary or Financial Metrics sheets
   - Specific extraction rules for each metric

2. **Workbook Locator Module** (to be created at `tools/workbook_locator.py`):
   - Map facility names to file patterns
   - Resolve workbook paths deterministically

3. **Cross-Validation Refactoring**:
   - Remove dependency on pricing_integrated_fixed.facility_model
   - Use Excel parser for "original" metrics
   - Ensure 80% working volume consistency
