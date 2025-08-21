# Bioprocess Web Application - Remaining Frontend Issues Task List

## CONTEXT & BACKGROUND

### Current Status
- **API Validation Issue**: ✅ SOLVED - FastAPI endpoint now accepts browser requests after fixing validation mismatch
- **Strain Selection**: XXX NOT WORKING !!! - Users can add/remove default strains from dropdown list successfully. CUSTOM STRAINS NOT ALL PARAMETERS CAN BE ADDED.
- **Run Analysis Button**: ✅ WORKING - Button executes without 422 errors

### Critical Remaining Issues
The frontend form data collection and results display systems are fundamentally broken. While the API accepts requests, the frontend is not properly collecting user inputs or displaying results.

## IMMEDIATE PRIORITY TASKS.

### ✅ TASK 1: COMPLETED - Volume Options Hardcoding Issue FIXED
**SOLUTION IMPLEMENTED**: Root cause was optimizer using wrong limits (max_reactors=20 vs 60) causing suboptimal volume selection and 2500L media tank display.

**Key Fixes Applied**:
- ✅ Fixed `bioprocess/orchestrator.py` line 290: Changed max_reactors from 20→60, max_ds_lines from 10→12 to match original
- ✅ Fixed `api/routers.py` line 99: Set use_multiobjective=True by default
- ✅ Fixed `web/static/js/app-comprehensive.js`: Added optimize_equipment=true, use_multiobjective=true by default
- ✅ Added proper JSON serialization handling in API responses
- ✅ Enhanced results display to handle nested API response structure

**VALIDATION RESULTS**:
- Volume options now work correctly: Selects 500L from [500, 1000, 2000, 5000]L options
- Optimization runs properly: 2,832 evaluations (vs 190 before), 6.9s runtime
- Achieves target TPA: 11.7 vs 10.0 target (1.17x ratio) ✅
- Media tank scales correctly: 625L (500L fermenter × 1.25) - no more hardcoded 2500L
- Performance: 14x faster than original while maintaining accuracy

**Files Modified**:
- `bioprocess/orchestrator.py` - Fixed optimization limits
- `api/routers.py` - Enabled multiobjective by default
- `web/static/js/app-comprehensive.js` - Fixed form data collection
- `bioprocess/optimizer_enhanced.py` - Added logger, improved grid search

**Cross-Validation Complete**: All 3 implementations (original, backend, API) now work correctly with proper volume selection.

### 🔥 TASK 2: COMPLETED Form Data Collection System FIXED

**NOTES FOR NEXT PROGRAMMER**:
⚠️ CRITICAL: Task 1 optimization fixes affect this task! The system now defaults to optimization=true, so form data collection issues may be masked by optimization overriding user inputs. Test both optimization and non-optimization modes.

**Updated Context**: With Task 1 fixes, the system now:
- Runs full grid search optimization by default (2,832 evaluations)
- Takes ~7 seconds per scenario (vs 0.5s before)
- Properly uses volume_options_l from checkboxes
- Returns detailed optimization results with best_solution

**Testing Approach**:
1. Test form collection with optimize_equipment=false to isolate form issues
2. Verify form data flows correctly through API transformation layer
3. Check both comprehensive and simple UI forms
4. Validate that optimization results don't hide form data collection bugs

### 🔥 TASK 2B: Fix Critical Optimization Algorithm Issues [URGENT - POST TASK 2]
**IMPORTANT NOTICE** `cross_validation_proper.py` and `cross_validation_api.py` works but `test_frontend_from_collection.py` is failing the target TPA v.s. annual production TPA comparison.
**STATUS**: ✅ TASK 2 COMPLETED - Form data collection is working perfectly, but comprehensive testing revealed critical optimization algorithm issues.

**CRITICAL ISSUES DISCOVERED**:
⚠️ **Issue 1: Target TPA Constraint Completely Ignored**
- Target TPA: 12.5 TPA
- Basic scenarios produce: 328.1 TPA (26.3x target!)
- Optimized scenarios produce: 55.9 TPA (4.5x target)
- **Root Cause**: Optimization algorithm is not enforcing target TPA constraints

⚠️ **Issue 2: Multiobjective Optimization Not Working**
- Equipment Optimization and Multiobjective Optimization produce IDENTICAL results
- Same NPV: $59,667,504
- Same configuration: 2 Reactors × 1 DS Line × 1500L
- Same evaluation count: 4248 evaluations
- **Root Cause**: Multiobjective mode appears to be non-functional or auto-enabled

⚠️ **Issue 3: Pareto Front Generation Failure**
- Multiobjective optimization returns only 1 solution (should be multiple for trade-offs)
- No exploration of NPV vs IRR trade-offs
- **Root Cause**: Algorithm not properly generating Pareto front solutions

**BACKEND VALIDATION REQUIRED**:
1. **Cross-Validation Analysis**: Use existing validation files to compare API vs original algorithms
   - Modify `cross_validation_proper.py` to test TPA constraint enforcement
   - Modify `cross_validation_api.py` to validate optimization modes
   - Compare results between original backend and API implementation

2. **Original Algorithm Analysis**: Investigate if original algorithms properly handle:
   - Target TPA constraints in optimization
   - Multiobjective vs single-objective modes
   - Pareto front generation for trade-off analysis

**ROOT CAUSE INVESTIGATION LOCATIONS**:
- **Optimization Engine**: `bioprocess/optimizer_enhanced.py` - grid search implementation
- **Orchestrator**: `bioprocess/orchestrator.py` - optimization mode selection
- **Models**: `bioprocess/models.py` - optimization configuration validation
- **API Layer**: `api/routers.py` - optimization request handling

**SPECIFIC DEBUGGING TASKS**:

**Task 2B.1: Target TPA Constraint Enforcement**
```python
# In optimizer_enhanced.py - verify constraint checking
def optimize_with_capacity_enforcement():
    # Check if target_tpa is being used as a constraint
    # Verify feasible_batches calculation respects target_tpa
    # Debug why optimization allows 4.5x target production
```

**Task 2B.2: Multiobjective Mode Investigation**
```python
# Check if multiobjective flag is properly processed
# Verify objectives list is used in optimization
# Debug why single and multiobjective produce identical results
```

**Task 2B.3: Cross-Validation Setup**
Modify validation files to test these specific scenarios:
- Target TPA = 12.5, expect actual TPA ≈ 12.5 (±20%)
- Single objective (NPV only) vs Multiobjective (NPV+IRR) should differ
- Pareto front should contain multiple solutions for multiobjective

**VALIDATION PROTOCOL**:
1. **Check and validate cross_validation_proper.py**:
   ```python
   # Add TPA constraint validation
   def test_tpa_constraint_enforcement():
       target_tpa = 12.5
       result = run_original_algorithm(target_tpa=target_tpa)
       actual_tpa = result.capacity_kg / 1000
       assert 0.8 <= actual_tpa/target_tpa <= 1.2, f"TPA mismatch: {actual_tpa} vs {target_tpa}"

   # Add optimization mode comparison
   def test_optimization_modes():
       single_obj = run_optimization(objectives=["npv"])
       multi_obj = run_optimization(objectives=["npv", "irr"])
       assert single_obj.npv != multi_obj.npv, "Optimization modes should differ"
   ```

2. **Check and validate cross_validation_api.py**:
   ```python
   # Test API optimization endpoints
   def test_api_optimization_consistency():
       # Compare /api/scenarios/run vs /api/optimization/run
       # Verify target TPA constraint enforcement
       # Validate multiobjective vs single objective differences
   ```

**EXPECTED OUTCOMES**:
- Target TPA should be enforced within ±20% tolerance
- Multiobjective optimization should produce different results than single-objective
- Pareto front should contain 3+ solutions for meaningful trade-off analysis
- Cross-validation should confirm API matches original algorithm behavior

**SUCCESS CRITERIA**:
- [ ] Target TPA constraint properly enforced (actual TPA within 0.8-1.2x target)
- [ ] Multiobjective optimization produces different results than single-objective
- [ ] Pareto front generation works (>1 solution for multiobjective)
- [ ] Cross-validation confirms API matches original algorithm
- [ ] Equipment optimization and multiobjective optimization produce different results

**TESTING APPROACH**:
1. Run modified cross_validation_proper.py to test original algorithms
2. Run modified cross_validation_api.py to test API endpoints
3. Use comprehensive_form_test_results to validate fixes
4. Test with multiple target TPA values (5, 10, 15, 20 TPA)
5. Verify optimization constraint parameters are respected

**PRIORITY**: HIGH - These optimization issues significantly impact system reliability and user trust. Target TPA constraints are fundamental to bioprocess design.
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
- [x] Selecting different volume checkboxes changes analysis volumes
- [x] Multiple volume selection works for grid search
- [x] No hardcoded 2500L values appear
- [x] Optimization runs full grid search (2,832+ evaluations)
- [x] Achieves target TPA through proper volume selection
- [x] Media tank volume scales correctly (fermenter_volume × 1.25)

### Form Data Collection Fixed
- [x] Changes in Economics tab affect results
- [x] Changes in Labor tab affect results
- [x] Changes in OPEX tab affect results
- [x] Changes in CAPEX tab affect results
- [x] Changes in Pricing tab affect results
- [x] Changes in Optimization tab affect results
- [x] Changes in Sensitivity tab affect results

### Optimization Algorithm Fixed (Task 2B)
- [ ] Target TPA constraint properly enforced (actual TPA within 0.8-1.2x target)
- [ ] Multiobjective optimization produces different results than single-objective
- [ ] Pareto front generation works (>1 solution for multiobjective)
- [ ] Cross-validation confirms API matches original algorithm
- [ ] Equipment optimization and multiobjective optimization produce different results
- [ ] Optimization respects min_tpa, max_capex, min_utilization constraints
- [ ] Grid search evaluations match expected count based on configuration space

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
1. ✅ **Volume Options** - COMPLETED
2. ✅ **Form Data Collection** - COMPLETED (all form tabs working)
3. 🔥 **Task 2B: Optimization Algorithm Issues** - URGENT (target TPA constraints broken, multiobjective not working)
4. **Results Display** (blocking user feedback)
5. **Export Functionality** (important but not blocking)
6. **Scenarios Management** (nice-to-have feature)

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
