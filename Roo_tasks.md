# Bioprocess Web Application - Remaining Frontend Issues Task List

## CONTEXT & BACKGROUND

### Current Status
- **API Validation Issue**: ✅ SOLVED - FastAPI endpoint now accepts browser requests after fixing validation mismatch
- **Strain Selection**: ✅ WORKING PARTIALLY - Users can add/remove default strains from dropdown list successfully. CUSTOM STRAINS DO NOT APPEAR TESTED.
- **Run Analysis Button**: ✅ WORKING - Button executes without 422 errors

### Critical Remaining Issues
The frontend form data collection and results display systems are fundamentally broken. While the API accepts requests, the frontend is not properly collecting user inputs or displaying results.

## IMMEDIATE PRIORITY TASKS

### 🔥 TASK 1: Investigate Volume Options Hardcoding Issue
**Problem**: Volume options always default to 2500L despite no 2500L checkbox existing in UI
**Evidence**: 
- HTML has volume checkboxes: 500L, 1000L, 2000L (checked), 5000L, 10000L, 20000L, 50000L
- User reports 2500L appears in results regardless of checkbox selection
- No 2500L option exists in the UI

**Investigation Steps**:
1. Search ALL JavaScript files for "2500" hardcoded values
2. Check API backend files for default volume handling
3. Examine request transformation logic in `api/routers.py` lines 113-233
4. Look for volume_options overrides in API processing
5. Check if `baseFermenterVolume` (set to 2000L) is being confused with volume options

**Files to Check**:
- `web/static/js/app-comprehensive.js` - volume collection logic
- `api/routers.py` - request transformation 
- `api/schemas.py` - data models
- `bioprocess/` modules - backend processing

**Expected Outcome**: Volume grid search should use exactly the volumes selected in UI checkboxes

### 🔥 TASK 2: Fix Form Data Collection System
**Problem**: All form input changes except strains are ignored - changes to Basic, Economics, Labor, OPEX, CAPEX, Pricing, Optimization, Sensitivity tabs have no effect

**Root Cause Analysis Needed**:
1. **Data Collection**: Check if `collectFormData()` function in `app-comprehensive.js` is properly gathering all form values
2. **Request Sending**: Verify collected data is being sent to API correctly by logging and testing
3. **API Processing**: Confirm API is using received form data instead of defaults by logging and testing

**Specific Form Sections Not Working**:
- **Economics Tab**: Discount rate, tax rate, depreciation, project lifetime, OPEX distribution
- **Labor Tab**: All salary fields and headcount configuration  
- **OPEX Tab**: Utility costs, raw materials markup, efficiency factors
- **CAPEX Tab**: Facility costs, equipment costs, CAPEX factors
- **Pricing Tab**: Product prices, raw material prices
- **Optimization Tab**: All optimization settings and constraints
- **Sensitivity Tab**: All sensitivity analysis parameters

**Testing Protocol**:
    **YOUR BROWSER TOOL IS NOT WORKING YOU HAVE TO USE DIRECT POST SENDING check data in `bioprocess/presets.py` also check the end of this file " SCENARIO EXAMPLE SCTRUCTURE IS AS BELOW title "**
1. Change values in each tab
2. Add browser console logging to verify data collection
3. Monitor network requests to see if changed values are transmitted
4. Verify API receives and processes the changed values

### 🔥 TASK 3: Fix Results Display System
**Problem**: No results, charts, or KPIs are displayed after successful analysis

**Components Not Working**:
- **KPI Cards**: NPV, IRR, Payback, Capacity values show "-"
- **Charts**: All Plotly.js charts are empty/not rendering
  - Capacity Chart
  - Utilization Chart  
  - CAPEX Chart
  - OPEX Chart
  - Cash Flow Chart
  - Tornado Chart (Sensitivity)

**Investigation Areas**:
1. **API Response**: Check if API returns complete results data
2. **JavaScript Processing**: Verify results data is received and parsed
3. **Chart Rendering**: Check Plotly.js integration and data formatting
4. **DOM Updates**: Ensure KPI values are being updated in HTML

**Files to Examine**:
- `web/static/js/charts.js` - chart rendering logic
- `web/static/js/app-comprehensive.js` - results processing
- `web/templates/index_comprehensive.html` lines 764-830 - results HTML structure

### 🔥 TASK 4: Fix Export Functionality
**Problem**: Export button does not work

**Requirements**:
- Export to Excel format
- Export to JSON format  
- Include all analysis results
- Handle error cases gracefully

**Implementation Needs**:
1. Check export button click handler
2. Verify API endpoint for exports exists
3. Test file download mechanism
4. Add proper error handling and user feedback

### 🔥 TASK 5: Implement Scenarios Management
**Problem**: Scenarios dropdown menu is not functional

**Required Features**:
1. **5 Default Preset Scenarios**:
   - Facility 1: Yogurt Cultures (10 TPA)
   - Facility 2: Lacto/Bifido (10 TPA) 
   - Facility 3: Bacillus Spores (10 TPA)
   - Facility 4: Yeast Probiotic (10 TPA)
   - Facility 5: ALL IN (40 TPA)

2. **User Scenario Management**:
   - Save current scenario
   - Load scenario from file
   - Scenario validation and error handling

**Data Sources**: You can extract scenario data from `bioprocess/presets.py` also check the end of this file " SCENARIO EXAMPLE SCTRUCTURE IS AS BELOW title "

## TECHNICAL DEBUGGING APPROACH

### Debug Strategy
1. **Add Comprehensive Logging**: Insert console.log statements throughout data flow
2. **Network Monitoring**: Use browser dev tools to inspect API requests/responses
3. **Step-by-Step Testing**: Test each component in isolation
4. **Data Validation**: Verify data integrity at each stage of processing

### Key Code Locations
- **Frontend Data Collection**: `web/static/js/app-comprehensive.js` lines 272-400+
- **API Request Processing**: `api/routers.py` lines 113-233
- **Results Processing**: `web/static/js/charts.js` and results handling in main JS
- **HTML Form Structure**: `web/templates/index_comprehensive.html` tabs

### Testing Protocol for Each Fix
1. Make specific changes to form inputs
2. Verify console shows correct data collection
3. Check network tab for proper API request
4. Confirm API processes data correctly
5. Validate results display updates properly

## SUCCESS CRITERIA

### Volume Options Fixed
- [ ] Selecting different volume checkboxes changes analysis volumes
- [ ] Multiple volume selection works for grid search
- [ ] No hardcoded 2500L values appear

### Form Data Collection Fixed  
- [ ] Changes in Economics tab affect results
- [ ] Changes in Labor tab affect results
- [ ] Changes in OPEX tab affect results
- [ ] Changes in CAPEX tab affect results
- [ ] Changes in Pricing tab affect results
- [ ] Changes in Optimization tab affect results
- [ ] Changes in Sensitivity tab affect results

### Results Display Fixed
- [ ] KPI cards show actual calculated values
- [ ] All charts render with real data
- [ ] Results update when form inputs change

### Export Fixed
- [ ] Excel export downloads valid file
- [ ] JSON export downloads valid file
- [ ] Export includes all analysis data

### Scenarios Fixed
- [ ] 5 preset scenarios load correctly
- [ ] Save scenario functionality works
- [ ] Load scenario from file works

## PRIORITY ORDER
1. **Volume Options** (blocking core functionality)
2. **Form Data Collection** (blocking all input processing)  
3. **Results Display** (blocking user feedback)
4. **Export Functionality** (important but not blocking)
5. **Scenarios Management** (nice-to-have feature)

## NOTES FOR NEXT ROO AGENT

### Working Components (Don't Break)
- Strain selection and management
- Basic API communication  
- Run Analysis button execution
- API validation and request transformation

### Critical Files to Focus On
- `web/static/js/app-comprehensive.js` - Main frontend logic
- `api/routers.py` - API request processing
- `web/static/js/charts.js` - Results visualization

### User Testing Approach
After each fix, test with this workflow:
1. Change specific form values
2. Select different volume options
3. Run analysis  
4. Verify results display correctly
5. Test export functionality

The user has confirmed that the core API issue is resolved and the Run Analysis button works. The focus now is entirely on frontend data collection, processing, and display systems.


### SCENARIO EXAMPLE SCTRUCTURE IS AS BELOW:
2025-08-20 23:12:08,997 - api.routers - INFO - Raw scenario request: {
  "scenario": {
    "name": "Unnamed Scenario",
    "description": "",
    "annual_production": 1000,
    "purity": 0.95,
    "plant_lifetime": 15,
    "construction_time": 2,
    "strains": [
      {
        "name": "Bacillus coagulans",
        "fermentation_time_h": 36,
        "turnaround_time_h": 9,
        "downstream_time_h": 4,
        "yield_g_per_L": 30,
        "media_cost_usd": 104.08000000000001,
        "cryo_cost_usd": 8.58,
        "utility_rate_ferm_kw": 648,
        "utility_rate_cent_kw": 15,
        "utility_rate_lyo_kw": 1.5,
        "utility_cost_steam": 0.0228,
        "cv_ferm": 0.1,
        "cv_turn": 0.1,
        "cv_down": 0.1,
        "respiration_type": "aerobic",
        "requires_tff": false,
        "downstream_complexity": 1.2
      }
    ],
    "equipment": {
      "reactors_total": 4,
      "ds_lines_total": 2,
      "upstream_availability": 0.92,
      "downstream_availability": 0.9,
      "quality_yield": 0.98
    },
    "economics": {
      "discount_rate": 0.1,
      "tax_rate": 0.21,
      "depreciation_years": 10,
      "inflation_rate": 0.02,
      "working_capital_percent": 0.15
    },
    "labor": {
      "operators_per_shift": 2,
      "shifts_per_day": 3,
      "supervisor_ratio": 0.2,
      "average_salary": 60000,
      "benefits_percent": 0.3
    },
    "opex": {
      "raw_material_cost": 500,
      "utilities_per_batch": 5000,
      "waste_treatment_cost": 100,
      "maintenance_percent": 0.04,
      "insurance_percent": 0.01
    },
    "capex": {
      "equipment_cost": 10000000,
      "installation_factor": 1.5,
      "building_cost_per_sqm": 2000,
      "land_cost_per_sqm": 500,
      "contingency_percent": 0.2
    },
    "pricing": {
      "base_price": 5000,
      "price_model": "fixed",
      "price_sensitivity": 0,
      "volume_discount": 0
    },
    "raw_prices": {
      "Glucose": 0.22,
      "Dextrose": 0.61,
      "Sucrose": 0.36,
      "Fructose": 3.57,
      "Lactose": 0.93,
      "Molasses": 0.11,
      "Yeast Extract": 1.863,
      "Soy Peptone": 4.5,
      "Tryptone": 42.5,
      "Casein": 8,
      "Rye Protein Isolate": 18,
      "CSL": 0.85,
      "Monosodium_Glutamate": 1,
      "K2HPO4": 1.2,
      "KH2PO4": 1,
      "L-cysteine HCl": 26.5,
      "MgSO4x7H2O": 0.18,
      "Arginine": 8,
      "FeSO4": 0.15,
      "CaCl2": 1.7,
      "Sodium_Citrate": 0.9,
      "Simethicone": 3,
      "Inulin": 5,
      "Glycerol": 0.95,
      "Skim Milk": 2.5,
      "Trehalose": 30,
      "Sodium Ascorbate": 3.7,
      "Whey Powder": 1.74,
      "Tween_80": 4,
      "MnSO4xH2O": 1.5,
      "ZnSO4x7H2O": 1.2,
      "Sodium_Acetate": 1
    },
    "assumptions": {
      "hours_per_year": 8760,
      "upstream_availability": 0.92,
      "downstream_availability": 0.9,
      "quality_yield": 0.98,
      "discount_rate": 0.1,
      "tax_rate": 0.25,
      "variable_opex_share": 0.85,
      "maintenance_pct_of_equip": 0.09,
      "ga_other_scale_factor": 10.837554482271175,
      "price_yogurt_usd_per_kg": 400,
      "price_lacto_bifido_usd_per_kg": 400,
      "price_bacillus_usd_per_kg": 400,
      "price_sacco_usd_per_kg": 500,
      "plant_manager_salary": 104000,
      "fermentation_specialist_salary": 39000,
      "downstream_process_operator_salary": 52000,
      "general_technician_salary": 32500,
      "qaqc_lab_tech_salary": 39000,
      "maintenance_tech_salary": 39000,
      "utility_operator_salary": 39000,
      "logistics_clerk_salary": 39000,
      "office_clerk_salary": 32500
    },
    "available_strains": {
      "B. animalis subsp. lactis": {
        "t_fedbatch_h": 15,
        "media_cost_usd": 255.22665,
        "cryo_cost_usd": 47.65,
        "licensing_fixed_cost_usd": 0,
        "licensing_royalty_pct": 0,
        "respiration_type": "anaerobic",
        "requires_tff": true,
        "downstream_complexity": 1,
        "t_turnaround_h": 9,
        "t_downstrm_h": 4,
        "cv_ferm": 0.1,
        "cv_turn": 0.1,
        "cv_down": 0.1,
        "yield_g_per_L": 34.1,
        "utility_rate_ferm_kw": 270,
        "utility_rate_cent_kw": 15,
        "utility_rate_lyo_kw": 1.5,
        "price_yogurt_usd_per_kg": 400
      },
      "B. breve": {
        "t_fedbatch_h": 16,
        "media_cost_usd": 255.22665,
        "cryo_cost_usd": 90.3,
        "licensing_fixed_cost_usd": 0,
        "licensing_royalty_pct": 0,
        "respiration_type": "anaerobic",
        "requires_tff": true,
        "downstream_complexity": 1,
        "t_turnaround_h": 9,
        "t_downstrm_h": 4,
        "cv_ferm": 0.1,
        "cv_turn": 0.1,
        "cv_down": 0.1,
        "yield_g_per_L": 19.44,
        "utility_rate_ferm_kw": 288,
        "utility_rate_cent_kw": 15,
        "utility_rate_lyo_kw": 1.5,
        "price_lacto_bifido_usd_per_kg": 400
      },
      "L. rhamnosus GG": {
        "t_fedbatch_h": 22,
        "media_cost_usd": 389.4296,
        "cryo_cost_usd": 176.8,
        "licensing_fixed_cost_usd": 0,
        "licensing_royalty_pct": 0,
        "respiration_type": "facultative",
        "requires_tff": true,
        "downstream_complexity": 1,
        "t_turnaround_h": 9,
        "t_downstrm_h": 4,
        "cv_ferm": 0.1,
        "cv_turn": 0.1,
        "cv_down": 0.1,
        "yield_g_per_L": 63.5,
        "utility_rate_ferm_kw": 396,
        "utility_rate_cent_kw": 15,
        "utility_rate_lyo_kw": 1.5,
        "price_lacto_bifido_usd_per_kg": 400
      },
      "Bacillus subtilis": {
        "t_fedbatch_h": 30,
        "media_cost_usd": 157.42400000000004,
        "cryo_cost_usd": 8.58,
        "licensing_fixed_cost_usd": 0,
        "licensing_royalty_pct": 0,
        "respiration_type": "aerobic",
        "requires_tff": false,
        "downstream_complexity": 1.2,
        "t_turnaround_h": 9,
        "t_downstrm_h": 4,
        "cv_ferm": 0.1,
        "cv_turn": 0.1,
        "cv_down": 0.1,
        "yield_g_per_L": 88,
        "utility_rate_ferm_kw": 540,
        "utility_rate_cent_kw": 15,
        "utility_rate_lyo_kw": 1.5,
        "price_bacillus_usd_per_kg": 400
      },
      "Saccharomyces boulardii": {
        "t_fedbatch_h": 31,
        "media_cost_usd": 115.3954,
        "cryo_cost_usd": 180.5,
        "licensing_fixed_cost_usd": 0,
        "licensing_royalty_pct": 0,
        "respiration_type": "aerobic",
        "requires_tff": false,
        "downstream_complexity": 1,
        "t_turnaround_h": 9,
        "t_downstrm_h": 4,
        "cv_ferm": 0.1,
        "cv_turn": 0.1,
        "cv_down": 0.1,
        "yield_g_per_L": 32.09,
        "utility_rate_ferm_kw": 558,
        "utility_rate_cent_kw": 15,
        "utility_rate_lyo_kw": 1.5,
        "price_sacco_usd_per_kg": 500
      },
      "B. longum": {
        "t_fedbatch_h": 12,
        "media_cost_usd": 256.95465,
        "cryo_cost_usd": 80.94999999999999,
        "licensing_fixed_cost_usd": 0,
        "licensing_royalty_pct": 0,
        "respiration_type": "anaerobic",
        "requires_tff": true,
        "downstream_complexity": 1,
        "t_turnaround_h": 9,
        "t_downstrm_h": 4,
        "cv_ferm": 0.1,
        "cv_turn": 0.1,
        "cv_down": 0.1,
        "yield_g_per_L": 22.18,
        "utility_rate_ferm_kw": 216,
        "utility_rate_cent_kw": 15,
        "utility_rate_lyo_kw": 1.5,
        "price_lacto_bifido_usd_per_kg": 400
      },
      "Bacillus coagulans": {
        "t_fedbatch_h": 36,
        "media_cost_usd": 104.08000000000001,
        "cryo_cost_usd": 8.58,
        "licensing_fixed_cost_usd": 0,
        "licensing_royalty_pct": 0,
        "respiration_type": "aerobic",
        "requires_tff": false,
        "downstream_complexity": 1.2,
        "t_turnaround_h": 9,
        "t_downstrm_h": 4,
        "cv_ferm": 0.1,
        "cv_turn": 0.1,
        "cv_down": 0.1,
        "yield_g_per_L": 30,
        "utility_rate_ferm_kw": 648,
        "utility_rate_cent_kw": 15,
        "utility_rate_lyo_kw": 1.5,
        "price_bacillus_usd_per_kg": 400
      },
      "S. thermophilus": {
        "t_fedbatch_h": 14,
        "media_cost_usd": 81.51200000000001,
        "cryo_cost_usd": 189.176,
        "licensing_fixed_cost_usd": 0,
        "licensing_royalty_pct": 0,
        "respiration_type": "aerobic",
        "requires_tff": false,
        "downstream_complexity": 1,
        "t_turnaround_h": 9,
        "t_downstrm_h": 4,
        "cv_ferm": 0.1,
        "cv_turn": 0.1,
        "cv_down": 0.1,
        "yield_g_per_L": 3,
        "utility_rate_ferm_kw": 252,
        "utility_rate_cent_kw": 15,
        "utility_rate_lyo_kw": 1.5,
        "price_yogurt_usd_per_kg": 400
      },
      "L. acidophilus": {
        "t_fedbatch_h": 18,
        "media_cost_usd": 252.45120000000003,
        "cryo_cost_usd": 191.766,
        "licensing_fixed_cost_usd": 0,
        "licensing_royalty_pct": 0,
        "respiration_type": "aerobic",
        "requires_tff": true,
        "downstream_complexity": 1,
        "t_turnaround_h": 9,
        "t_downstrm_h": 4,
        "cv_ferm": 0.1,
        "cv_turn": 0.1,
        "cv_down": 0.1,
        "yield_g_per_L": 82.87,
        "utility_rate_ferm_kw": 324,
        "utility_rate_cent_kw": 15,
        "utility_rate_lyo_kw": 1.5,
        "price_yogurt_usd_per_kg": 400
      },
      "L. delbrueckii subsp. bulgaricus": {
        "t_fedbatch_h": 24,
        "media_cost_usd": 146.27,
        "cryo_cost_usd": 52.751,
        "licensing_fixed_cost_usd": 0,
        "licensing_royalty_pct": 0,
        "respiration_type": "aerobic",
        "requires_tff": false,
        "downstream_complexity": 1,
        "t_turnaround_h": 9,
        "t_downstrm_h": 4,
        "cv_ferm": 0.1,
        "cv_turn": 0.1,
        "cv_down": 0.1,
        "yield_g_per_L": 6.08,
        "utility_rate_ferm_kw": 432,
        "utility_rate_cent_kw": 15,
        "utility_rate_lyo_kw": 1.5,
        "price_yogurt_usd_per_kg": 400
      },
      "L. plantarum": {
        "t_fedbatch_h": 12,
        "media_cost_usd": 117.50240000000001,
        "cryo_cost_usd": 176.8,
        "licensing_fixed_cost_usd": 0,
        "licensing_royalty_pct": 0,
        "respiration_type": "facultative",
        "requires_tff": true,
        "downstream_complexity": 1,
        "t_turnaround_h": 9,
        "t_downstrm_h": 4,
        "cv_ferm": 0.1,
        "cv_turn": 0.1,
        "cv_down": 0.1,
        "yield_g_per_L": 16.02,
        "utility_rate_ferm_kw": 216,
        "utility_rate_cent_kw": 15,
        "utility_rate_lyo_kw": 1.5,
        "price_lacto_bifido_usd_per_kg": 400
      },
      "L. casei": {
        "t_fedbatch_h": 24,
        "media_cost_usd": 105.13,
        "cryo_cost_usd": 39.3,
        "licensing_fixed_cost_usd": 0,
        "licensing_royalty_pct": 0,
        "respiration_type": "facultative",
        "requires_tff": true,
        "downstream_complexity": 1,
        "t_turnaround_h": 9,
        "t_downstrm_h": 4,
        "cv_ferm": 0.1,
        "cv_turn": 0.1,
        "cv_down": 0.1,
        "yield_g_per_L": 5.56,
        "utility_rate_ferm_kw": 432,
        "utility_rate_cent_kw": 15,
        "utility_rate_lyo_kw": 1.5,
        "price_lacto_bifido_usd_per_kg": 400
      }
    },
    "available_volumes": [
      500,
      1000,
      2000,
      5000,
      10000,
      20000,
      50000
    ],
    "allocation_policies": [
      "equal",
      "proportional",
      "inverse_ct"
    ],
    "optimization_objectives": [
      "npv",
      "irr",
      "capex",
      "opex",
      "payback"
    ],
    "target_tpa": 10,
    "volumes": {
      "seed_volume_l": 200,
      "production_volume_l": 2000,
      "base_fermenter_vol_l": 2500,
      "working_volume_fraction": 0.8
    },
    "prices": {
      "product_prices": {
        "default": 400
      },
      "raw_prices": {
        "assumptions": {
          "hours_per_year": 8760,
          "upstream_availability": 0.92,
          "downstream_availability": 0.9,
          "quality_yield": 0.98,
          "discount_rate": 0.1,
          "tax_rate": 0.25,
          "variable_opex_share": 0.85,
          "maintenance_pct_of_equip": 0.09,
          "ga_other_scale_factor": 10.837554482271175,
          "price_yogurt_usd_per_kg": 400,
          "price_lacto_bifido_usd_per_kg": 400,
          "price_bacillus_usd_per_kg": 400,
          "price_sacco_usd_per_kg": 500,
          "plant_manager_salary": 104000,
          "fermentation_specialist_salary": 39000,
          "downstream_process_operator_salary": 52000,
          "general_technician_salary": 32500,
          "qaqc_lab_tech_salary": 39000,
          "maintenance_tech_salary": 39000,
          "utility_operator_salary": 39000,
          "logistics_clerk_salary": 39000,
          "office_clerk_salary": 32500
        },
        "raw_prices": {
          "Glucose": 0.22,
          "Dextrose": 0.61,
          "Sucrose": 0.36,
          "Fructose": 3.57,
          "Lactose": 0.93,
          "Molasses": 0.11,
          "Yeast Extract": 1.863,
          "Soy Peptone": 4.5,
          "Tryptone": 42.5,
          "Casein": 8,
          "Rye Protein Isolate": 18,
          "CSL": 0.85,
          "Monosodium_Glutamate": 1,
          "K2HPO4": 1.2,
          "KH2PO4": 1,
          "L-cysteine HCl": 26.5,
          "MgSO4x7H2O": 0.18,
          "Arginine": 8,
          "FeSO4": 0.15,
          "CaCl2": 1.7,
          "Sodium_Citrate": 0.9,
          "Simethicone": 3,
          "Inulin": 5,
          "Glycerol": 0.95,
          "Skim Milk": 2.5,
          "Trehalose": 30,
          "Sodium Ascorbate": 3.7,
          "Whey Powder": 1.74,
          "Tween_80": 4,
          "MnSO4xH2O": 1.5,
          "ZnSO4x7H2O": 1.2,
          "Sodium_Acetate": 1
        },
        "available_strains": {
          "Bacillus coagulans": {
            "t_fedbatch_h": 36,
            "media_cost_usd": 104.08000000000001,
            "cryo_cost_usd": 8.58,
            "licensing_fixed_cost_usd": 0,
            "licensing_royalty_pct": 0,
            "respiration_type": "aerobic",
            "requires_tff": false,
            "downstream_complexity": 1.2,
            "t_turnaround_h": 9,
            "t_downstrm_h": 4,
            "cv_ferm": 0.1,
            "cv_turn": 0.1,
            "cv_down": 0.1,
            "yield_g_per_L": 30,
            "utility_rate_ferm_kw": 648,
            "utility_rate_cent_kw": 15,
            "utility_rate_lyo_kw": 1.5,
            "price_bacillus_usd_per_kg": 400
          },
          "Saccharomyces boulardii": {
            "t_fedbatch_h": 31,
            "media_cost_usd": 115.3954,
            "cryo_cost_usd": 180.5,
            "licensing_fixed_cost_usd": 0,
            "licensing_royalty_pct": 0,
            "respiration_type": "aerobic",
            "requires_tff": false,
            "downstream_complexity": 1,
            "t_turnaround_h": 9,
            "t_downstrm_h": 4,
            "cv_ferm": 0.1,
            "cv_turn": 0.1,
            "cv_down": 0.1,
            "yield_g_per_L": 32.09,
            "utility_rate_ferm_kw": 558,
            "utility_rate_cent_kw": 15,
            "utility_rate_lyo_kw": 1.5,
            "price_sacco_usd_per_kg": 500
          },
          "L. acidophilus": {
            "t_fedbatch_h": 18,
            "media_cost_usd": 252.45120000000003,
            "cryo_cost_usd": 191.766,
            "licensing_fixed_cost_usd": 0,
            "licensing_royalty_pct": 0,
            "respiration_type": "aerobic",
            "requires_tff": true,
            "downstream_complexity": 1,
            "t_turnaround_h": 9,
            "t_downstrm_h": 4,
            "cv_ferm": 0.1,
            "cv_turn": 0.1,
            "cv_down": 0.1,
            "yield_g_per_L": 82.87,
            "utility_rate_ferm_kw": 324,
            "utility_rate_cent_kw": 15,
            "utility_rate_lyo_kw": 1.5,
            "price_yogurt_usd_per_kg": 400
          },
          "B. animalis subsp. lactis": {
            "t_fedbatch_h": 15,
            "media_cost_usd": 255.22665,
            "cryo_cost_usd": 47.65,
            "licensing_fixed_cost_usd": 0,
            "licensing_royalty_pct": 0,
            "respiration_type": "anaerobic",
            "requires_tff": true,
            "downstream_complexity": 1,
            "t_turnaround_h": 9,
            "t_downstrm_h": 4,
            "cv_ferm": 0.1,
            "cv_turn": 0.1,
            "cv_down": 0.1,
            "yield_g_per_L": 34.1,
            "utility_rate_ferm_kw": 270,
            "utility_rate_cent_kw": 15,
            "utility_rate_lyo_kw": 1.5,
            "price_yogurt_usd_per_kg": 400
          },
          "L. casei": {
            "t_fedbatch_h": 24,
            "media_cost_usd": 105.13,
            "cryo_cost_usd": 39.3,
            "licensing_fixed_cost_usd": 0,
            "licensing_royalty_pct": 0,
            "respiration_type": "facultative",
            "requires_tff": true,
            "downstream_complexity": 1,
            "t_turnaround_h": 9,
            "t_downstrm_h": 4,
            "cv_ferm": 0.1,
            "cv_turn": 0.1,
            "cv_down": 0.1,
            "yield_g_per_L": 5.56,
            "utility_rate_ferm_kw": 432,
            "utility_rate_cent_kw": 15,
            "utility_rate_lyo_kw": 1.5,
            "price_lacto_bifido_usd_per_kg": 400
          },
          "S. thermophilus": {
            "t_fedbatch_h": 14,
            "media_cost_usd": 81.51200000000001,
            "cryo_cost_usd": 189.176,
            "licensing_fixed_cost_usd": 0,
            "licensing_royalty_pct": 0,
            "respiration_type": "aerobic",
            "requires_tff": false,
            "downstream_complexity": 1,
            "t_turnaround_h": 9,
            "t_downstrm_h": 4,
            "cv_ferm": 0.1,
            "cv_turn": 0.1,
            "cv_down": 0.1,
            "yield_g_per_L": 3,
            "utility_rate_ferm_kw": 252,
            "utility_rate_cent_kw": 15,
            "utility_rate_lyo_kw": 1.5,
            "price_yogurt_usd_per_kg": 400
          },
          "L. plantarum": {
            "t_fedbatch_h": 12,
            "media_cost_usd": 117.50240000000001,
            "cryo_cost_usd": 176.8,
            "licensing_fixed_cost_usd": 0,
            "licensing_royalty_pct": 0,
            "respiration_type": "facultative",
            "requires_tff": true,
            "downstream_complexity": 1,
            "t_turnaround_h": 9,
            "t_downstrm_h": 4,
            "cv_ferm": 0.1,
            "cv_turn": 0.1,
            "cv_down": 0.1,
            "yield_g_per_L": 16.02,
            "utility_rate_ferm_kw": 216,
            "utility_rate_cent_kw": 15,
            "utility_rate_lyo_kw": 1.5,
            "price_lacto_bifido_usd_per_kg": 400
          },
          "Bacillus subtilis": {
            "t_fedbatch_h": 30,
            "media_cost_usd": 157.42400000000004,
            "cryo_cost_usd": 8.58,
            "licensing_fixed_cost_usd": 0,
            "licensing_royalty_pct": 0,
            "respiration_type": "aerobic",
            "requires_tff": false,
            "downstream_complexity": 1.2,
            "t_turnaround_h": 9,
            "t_downstrm_h": 4,
            "cv_ferm": 0.1,
            "cv_turn": 0.1,
            "cv_down": 0.1,
            "yield_g_per_L": 88,
            "utility_rate_ferm_kw": 540,
            "utility_rate_cent_kw": 15,
            "utility_rate_lyo_kw": 1.5,
            "price_bacillus_usd_per_kg": 400
          },
          "L. delbrueckii subsp. bulgaricus": {
            "t_fedbatch_h": 24,
            "media_cost_usd": 146.27,
            "cryo_cost_usd": 52.751,
            "licensing_fixed_cost_usd": 0,
            "licensing_royalty_pct": 0,
            "respiration_type": "aerobic",
            "requires_tff": false,
            "downstream_complexity": 1,
            "t_turnaround_h": 9,
            "t_downstrm_h": 4,
            "cv_ferm": 0.1,
            "cv_turn": 0.1,
            "cv_down": 0.1,
            "yield_g_per_L": 6.08,
            "utility_rate_ferm_kw": 432,
            "utility_rate_cent_kw": 15,
            "utility_rate_lyo_kw": 1.5,
            "price_yogurt_usd_per_kg": 400
          },
          "B. breve": {
            "t_fedbatch_h": 16,
            "media_cost_usd": 255.22665,
            "cryo_cost_usd": 90.3,
            "licensing_fixed_cost_usd": 0,
            "licensing_royalty_pct": 0,
            "respiration_type": "anaerobic",
            "requires_tff": true,
            "downstream_complexity": 1,
            "t_turnaround_h": 9,
            "t_downstrm_h": 4,
            "cv_ferm": 0.1,
            "cv_turn": 0.1,
            "cv_down": 0.1,
            "yield_g_per_L": 19.44,
            "utility_rate_ferm_kw": 288,
            "utility_rate_cent_kw": 15,
            "utility_rate_lyo_kw": 1.5,
            "price_lacto_bifido_usd_per_kg": 400
          },
          "B. longum": {
            "t_fedbatch_h": 12,
            "media_cost_usd": 256.95465,
            "cryo_cost_usd": 80.94999999999999,
            "licensing_fixed_cost_usd": 0,
            "licensing_royalty_pct": 0,
            "respiration_type": "anaerobic",
            "requires_tff": true,
            "downstream_complexity": 1,
            "t_turnaround_h": 9,
            "t_downstrm_h": 4,
            "cv_ferm": 0.1,
            "cv_turn": 0.1,
            "cv_down": 0.1,
            "yield_g_per_L": 22.18,
            "utility_rate_ferm_kw": 216,
            "utility_rate_cent_kw": 15,
            "utility_rate_lyo_kw": 1.5,
            "price_lacto_bifido_usd_per_kg": 400
          },
          "L. rhamnosus GG": {
            "t_fedbatch_h": 22,
            "media_cost_usd": 389.4296,
            "cryo_cost_usd": 176.8,
            "licensing_fixed_cost_usd": 0,
            "licensing_royalty_pct": 0,
            "respiration_type": "facultative",
            "requires_tff": true,
            "downstream_complexity": 1,
            "t_turnaround_h": 9,
            "t_downstrm_h": 4,
            "cv_ferm": 0.1,
            "cv_turn": 0.1,
            "cv_down": 0.1,
            "yield_g_per_L": 63.5,
            "utility_rate_ferm_kw": 396,
            "utility_rate_cent_kw": 15,
            "utility_rate_lyo_kw": 1.5,
            "price_lacto_bifido_usd_per_kg": 400
          }
        },
        "available_volumes": [
          500,
          1000,
          2000,
          5000,
          10000,
          20000,
          50000
        ],
        "allocation_policies": [
          "equal",
          "proportional",
          "inverse_ct"
        ],
        "optimization_objectives": [
          "npv",
          "irr",
          "capex",
          "opex",
          "payback"
        ]
      }
    }
  },
  "async_mode": false
}