## Status update (2025-08-17)
- A1 Read and Extract: PARTIAL
    - optimizer_enhanced.optimize_with_capacity_enforcement exists and is used by orchestrator.run_optimization. It currently filters feasible and selects Pareto+knee but not with the 5/15/25% tiering nor original knee-only metric.
    - optimizer.evaluate_configuration:
        - Uses calculate_capex_estimate_original and passes capex_breakdown through capex_override to econ.calculate_economics.
    - econ.calculate_economics supports:
        - capex_override usage
        - ramp-up [0.40, 0.60, 0.75, 0.85] + [0.85]*7
        - depreciation base = (total_capex - licensing_fixed) * 0.5 / 10
        - royalty on pre‑royalty EBITDA
        - per-strain prices and WVF=0.8 usage
    - orchestrator.run_economic_analysis currently does not pass capex_override (that path uses equipment_result.equipment_cost); parity overrides are wired via optimizer path. We’ll need to ensure parity in orchestrator path as required by the Masterplan.
- A2 Optimizer: DONE
  - Implemented boolean-mask Pareto and original CAPEX/IRR-only knee selection; exact progressive tiers 5%/15%/25% with min-excess fallback; enforced capacity-first with fallback to max capacity; added fallback to lowest CAPEX/highest IRR when knee not computable.
- A3 Metrics parity: IN PROGRESS
  - WVF explicitly passed from scenario.volumes.working_volume_fraction into calculate_capacity_deterministic in optimizer.evaluate_configuration. Allocation defaults inverse_ct for both UP/DS and shared_downstream=True. Next: validate IRR/NPV parity vs original and confirm identical allocation policies applied end-to-end.
- B CAPEX (original): PARTIAL/DONE
  - calculate_capex_estimate_original exists and is used; breakdown passed into econ via override. Verified usage in optimizer.evaluate_configuration.
- API/WebSocket: IN PROGRESS
  - WebSocket now runs real orchestrator for run_scenario, run_batch, run_sensitivity; cancel_job cancels task and yields job_cancelled.
  - Next: add run_analysis path (similar to run_scenario but with analysis-specific flow), ensure REST and WS share orchestration consistently, and validate pytest websocket tests.

  - Converted a minimal direct API test to pytest (tests/test_api_direct_converted.py) to assert non-zero capacity and KPIs; left the original script file intact for manual diagnosis.

- C Economics parity: PARTIAL
  - capex_override, ramp-up, depreciation, and royalty parity implemented; validate totals and IRR/NPV parity post A2.
- G Progressive tolerance: UPDATED
  - Exact 5% → 15% → 25% tiers implemented; min-excess fallback in place.
  - Batch WS handler now preserves optimization path; uses heartbeat progress while scenarios compute and avoids forcing deterministic/no-opt.

- Cross-validation (WVF): PARTIAL
  - 0.8 WVF consistent; remove any 1.0 WVF comparisons explicitly.
- API wiring: PARTIAL
  - orchestrator uses optimizer_enhanced; ensure econ override parity in orchestrator analysis path and smoke test 2‑strain.
- Tests and sanity checks: UNKNOWN/PARTIAL
  - Add annual_revenue>0 assertions/logs; tighten deterministic capacity test.
- Deep dive next tasks (WebSocket batch + parity)
  - WS Batch: Add detailed logging at each stage (prepare, start, per-scenario progress heartbeat, complete); forward exceptions to client; ensure batch_complete is always emitted.
  - Tests: Switch WS tests to preset strains and optimization enabled with constrained volume options; consider using a fac1-like multi-strain scenario once stable.
  - Parity: Run cross_validation_proper.py with fac1 inputs and same optimization flags; compare CAPEX/IRR and capacity selections; record diffs.
  - If WS still flaky: consider background job model with periodic poll and streaming progress to align with client expectations.
- WS instrumentation: Added INFO logs for scenario preparation, optimization completion (best solution), capacity completion (total kg), and maintained progress streaming; exceptions are forwarded in batch and sensitivity paths.
- WS tests: Adjusted test_websocket.py to use exact fac1 strains with optimization and volume grid; updated server to accept strain names via prepare_scenario.


- fac1 parity (exact original inputs)
- CAPEX parity work (in progress)
  - Added CapexConfig.parity_mode with building_to_equip_factor=1.07 and land_to_equip_factor=0.223 to mirror original ratios when enabled.
  - Econ: when parity_mode=True, land/building derived from equipment cost; otherwise area-based remains.
  - Next: enable parity_mode for cross_validation_proper fac1 run, verify CAPEX delta closes; adjust factors if needed, then lock in constants.

  - Implemented original-style CAPEX in econ.calculate_economics when capex.parity_mode=True:
    - land = 250 * facility_area; building uses original multi-term formula scaling with volume and fermenters
    - include installation = 15% of equipment in direct CAPEX; contingency=12.5%; working capital=10% of direct
    - keep licensing fixed in total CAPEX and exclude from depreciable base
  - Next: Ensure fermenter count is accessible in econ (from equipment_result) during calculate_economics or pass via override
- OPEX parity (done for ramp handling):
  - build_cash_flows now ramps OPEX as fixed + variable when parity_mode=True (variable_opex_share=0.85)
  - Original's optimizer now uses Pareto + knee with excess penalty for selection
  - Cross-validation: fac1/fac2 production parity achieved; CAPEX within ~5%; IRR still higher in new due to labor/opex decomposition
  - Next: tighten labor parity in parity_mode by adding baseline headcount floor per original detailed P&L or equivalent fixed labor floor

- Labor parity (done):
  - Parity-mode labor floor implemented (>=15 FTE baseline). Unit tests added in tests/test_econ_parity.py.
- Unit tests:
  - Added tests/test_econ_parity.py to verify OPEX ramp split and labor parity floor.
- WebSocket regression:
  - Re-ran tests/test_websocket.py: 10 passed. Logs show optimized 500L/3R/1DS for fac1-like scenario.
- Cross-validation current state:
  - Production parity exact for fac1 and fac2. CAPEX ~5% lower (new). IRR divergence acceptable, attributed to optimizer differences per your guidance.
- Next tasks:
  - Strengthen parity-mode OPEX components only if needed in future; otherwise proceed with remaining Masterplan items (docs, tests, UI consistency).


  - Inputs (from pricing_integrated_original.py):
    - name: "Facility 1 - Yogurt Cultures (10 TPA)"
    - target_tpa: 10
    - strains: ["S. thermophilus","L. delbrueckii subsp. bulgaricus","L. acidophilus","B. animalis subsp. lactis"]
    - optimize_equipment: True
    - use_multiobjective: True
    - fermenter_volumes_to_test: [500, 1000, 1500, 2000, 3000, 4000, 5000]
    - flags: anaerobic=False, premium_spores=False, sacco=False
  - New-side scenario mapping:
    - volumes.base_fermenter_vol_l = 2000 (domain from volume_options_l for optimizer)
    - volumes.volume_options_l = [500, 1000, 1500, 2000, 3000, 4000, 5000]
    - volumes.working_volume_fraction = 0.8
    - prices.raw_prices/Product prices: use defaults from presets
    - optimization.enabled=True, optimization.simulation_type="deterministic", optimization.objectives=["irr"]
  - Validation steps:
    - Run: PYTHONPATH=. python cross_validation_proper.py
    - Compare: selected (volume, reactors, ds_lines), Production (kg/y), CAPEX, IRR, NPV
    - If divergence remains:
      - Reconfirm 0.8 WVF applied consistently
      - Check CAPEX override and economics (ramp-up/depr/royalty)
      - Dump feasible front and knee selection alignment

---

## TODO Masterplan (detailed and actionable)

Below is a comprehensive, step‑by‑step plan to bring the new implementation into exact parity with pricing_integrated_original.py. I will follow this plan in order.

### A. Optimizer: analyze and replicate original method exactly

1) Read and extract original optimization logic
- File/Functions to study:
  - pricing_integrated_original.py
    - optimize_counts_multiobjective (lines ~1646–1716)
    - _pareto_front (lines ~959–981)
    - _choose_knee_point (lines ~982–995)
    - _financials_for_counts (lines ~839–957) for how CAPEX/IRR are computed per candidate
- Capture details:
  - Grid search domain: fermenter volume options, reactors range, ds_lines range
  - Feasibility filter: enforce_capacity True filters meets_capacity rows; if none feasible, fallback to max plant_kg_good even if below target
  - Progressive narrowing? (Original uses enforce_capacity first; no explicit tiered excess but we will add progressive tolerance as per your requirement)
  - Pareto front: minimize CAPEX, maximize IRR; boolean mask identifying non‑dominated points
  - Knee selection: normalized distance to utopia (min CAPEX, max IRR)

2) Implement original Pareto + knee in new optimizer
- File to change: bioprocess/optimizer_enhanced.py
- Tasks:
  - Implement a boolean-mask Pareto function (similar to _pareto_front) that accepts DataFrame and returns a boolean Series
  - Implement a choose_knee_point(df) consistent with the original normalization of CAPEX and IRR (ignore excess in knee)
  - Enforce capacity first; if none feasible, return max capacity fallback (and annotate warning)
  - Add progressive excess tolerance tiers as required:
    - Try ≤5% excess first
    - If empty, try ≤15%
    - If empty, try ≤25%
    - If still empty, choose feasible with minimum excess (like original fallback)
  - Within the filtered feasible set, compute Pareto, then knee; if knee not computable, pick lowest CAPEX/highest IRR (like original)

3) Ensure optimizer produces the same metrics as original
- File(s): bioprocess/optimizer.py and optimizer_enhanced.py
- Tasks:
  - Ensure evaluate_configuration returns:
    - capex: computed with the original CAPEX methodology (see Section B)
    - irr/npv: computed from cash flows mirroring original economics (see Section C)
    - capacity_kg and meets_capacity matching capacity pipeline (identical allocation policies)
  - Confirm allocation policies are inverse_ct for both upstream and downstream (matching original defaults) and shared_downstream True

4) Validation for optimizer parity
- Commands:
  - PYTHONPATH=. python cross_validation_proper.py (should show matching configurations, producing comparable CAPEX/IRR, and both meeting TPA)
  - Spot-check optimizer outputs by dumping feasible_df/pareto_df for one facility to ensure correctness of the mask and knee

---

### B. CAPEX parity: replicate original capex_estimate_2

5) Read and extract original CAPEX logic
- File/Functions:
  - pricing_integrated_original.py capex_estimate_2 (lines ~503–561)
- Details to replicate:
  - Volume scaling via (volume/base)^(0.6) across equipment items
  - Equipment list and counts (fermenters, seed fermenters, media tanks, lyos, centrifuges, TFF, utilities block, QC lab)
  - Building/land cost formulas (facilityArea and buildingCost formulas used there)
  - Installation factor (15%), contingency (12.5%), working capital (10% of direct), plus licensing fixed included in total_capex

6) Implement original CAPEX function in new code
- File: bioprocess/sizing.py (new function)
- Tasks:
  - Add calculate_capex_estimate_original(target_tpa, fermenters, ds_lines, fermenter_volume_l, licensing_fixed_total) that returns (total_capex, breakdown) matching original keys:
    - {"equip", "building", "land", "install", "direct", "cont", "wc", "licensing_fixed_total"}
  - Do NOT change calculate_equipment_sizing (it can remain for UI/UX), but for optimization and economics parity, use the original‑style CAPEX function for consistency

7) Wire original CAPEX into optimizer and economics
- Files:
  - bioprocess/optimizer.py: evaluate_configuration()
  - bioprocess/optimizer_enhanced.py: where needed to build DataFrame rows
- Tasks:
  - Replace usage of calculate_capex_estimate with calculate_capex_estimate_original for optimization/evaluation
  - Pass capex breakdown forward so economics can use it (e.g., in a capex_override)

---

### C. Economics parity: replicate original cash flow + revenue/royalty

8) Read and extract the economics methodology
**Keep the per strain annual_production based revenue model in new implementation and modify pricing_integrated_original to match new implementation for annual_production_kg based revenue model in econ.py**
- File/Functions:
  - pricing_integrated_original.py
    - _financials_for_counts (lines ~839–957)
    - generate_detailed_opex_report + opex_block usage (lines ~1523–1535 and ~1757 onwards)
    - P&L builder block (lines ~2048–2067) and project-level cash flows
    - Monte Carlo block (for method parity, but base parity is deterministic)
- Key elements:
  - Price selection:
    - For single/facility types, _price_per_kg_from_flags uses constants (e.g., price_yogurt_usd_per_kg)
    - For multi-product facilities (ALL IN), weighted price per kg may be used
  - Variable vs fixed OPEX from total cash OPEX:
    - var_opex_per_kg = variable_share * total_cash_opex / steady_state_kg
    - fixed_opex = (1 - variable_share) * total_cash_opex
  - Cash flow build:
    - Year 0: -70% CAPEX; Year 1: -30% CAPEX
    - Years 2–12: ramp‑up capacities [0.40, 0.60, 0.75, 0.85] then 0.85 steady
    - Royalty applied to pre-royalty EBITDA
    - Depreciation excludes licensing fixed and uses 50% of process capital over 10 years (straight-line)
    - Taxed on EBT; UFCF = EBITDA - tax

9) Add parity path in econ.calculate_economics
- File: bioprocess/econ.py
- Tasks:
  - Add an optional capex_override parameter (capex breakdown dict from step 6) and when present, use it verbatim instead of re‑estimating CAPEX internally
  - Build cash flows with original ramp‑up profile: [0, 0, 0.40, 0.60, 0.75, 0.85] + [0.85]*7
  - Compute depreciation from (total_capex - licensing_fixed_total) * 0.5 / 10.0 each year (10-year horizon)
  - Apply royalty to pre‑royalty EBITDA, identical to original
  - For revenue per kg:
    - Use explicit per‑strain prices if present; otherwise, mimic original facility-level pricing (if facility flags exist), else fallback to average product price
  - Return results with npv, irr, payback identical to the original definitions

10) Minimize divergence from original OPEX computing
- Because original uses a large opex_block and we’re not porting the entire function here:
  - Compute total cash OPEX similarly to original inputs, or accept as a reasonable delta initially and focus on CAPEX, cashflow shape, and royalty, which dominate IRR/NPV
  - If discrepancies persist after optimizer/CAPEX alignment, port the necessary OPEX pieces for parity

11) Validation for economics parity
- Commands:
  - PYTHONPATH=. python cross_validation_proper.py
  - Inspect CAPEX breakdown against original (sanity compare equip/building/land/install/wc/cont vs original’s Excel sheets)
  - Check IRR/NPV qualitative movement: ensure royalty and depreciation are applied the same as original

---

### D. Cross-validation discrepancies investigation (after A/B/C are done)

12) Confirm both use 0.8 WVF and enforce_capacity
- Ensure cross_validation_proper.py only uses 0.8 WVF for both original and new
- Ensure orchestrator.run_optimization calls the capacity‑enforcing path

13) If discrepancies remain, isolate root cause
- Check allocation policy parity: both inverse_ct and shared downstream
- Compare the candidate set and Pareto front rows between original and new for a facility
  - Dump the feasible set to CSV for both original and new
  - Compare IRR/CAPEX per (reactors, ds_lines, volume)
- Confirm exact knee selection index matches

14) Fix any remaining gaps (documented changes)
- If pricing (per kg) causes variances, align price mapping
- If OPEX block is still skewing IRR, port those specific utilities/raw material elements

---

### E. Unit test failure diagnosis and strengthening

15) Diagnose why test_deterministic_capacity is weak
- File: tests/test_bioprocess.py::TestCapacityCalculations::test_deterministic_capacity
- Observations:
  - Only checks for >0 and presence of bottleneck
- Improve with meaningful assertions:
  - Sum of per_strain annual_kg is within 1% of total_annual_kg
  - With reactors_total doubled (e.g., 2 vs 4) capacity should not decrease; add a comparative check in a new test
  - Working_volume_fraction scaling check (1.0 vs 0.8) is no longer needed by policy; instead, check that changing volume_options or utilization changes capacity as expected

16) Implement improved assertions
- Modify or add tests to:
  - Assert numerical consistency between aggregated per_strain production and total
  - Assert increasing reactors increases or at least not decreases capacity for same other parameters
  - Assert utilizations remain in (0,1]

---

### F. API test producing zero outputs (fix pipeline)

17) Reproduce and debug test_api_direct zero outputs
- File: test_api_direct.py
- Actions:
  - Start uvicorn, call /api/scenarios/run synchronously
  - Print and verify the response format: RunScenarioResponse wraps result under .result in success branch
  - Ensure test reads nested result correctly (e.g., result["result"]["kpis"]["tpa"])
  - If orchestrator errors, capture /api logs and fix root cause (likely optimizer error fixed in A2)

18) Ensure API uses the updated optimizer and econ parity path
- Paths:
  - api/routers.py calls orchestrator.run_scenario
  - orchestrator.run_optimization -> optimizer_enhanced.optimize_with_capacity_enforcement
  - orchestrator.run_economic_analysis -> econ.calculate_economics (with capex_override integration from A/B)
- Validate that a simple two‑strain scenario returns non‑zero capacity/TPA and reasonable KPI values

---

### G. Implement progressive excess tolerance (already partly done)

19) Finalize progressive tolerance
- File: bioprocess/optimizer_enhanced.py
- Ensure the tiered tolerance is applied exactly before Pareto selection:
  - Attempt ≤5% excess, else ≤15%, else ≤25%, else fallback min excess feasible

20) Validation
- Cross-validation runs yield feasible configs within the tier when possible
- Log which tier was successful for traceability

---

### H. Remove working volume ratio testing

21) Clean up validation scripts and messages
- File: cross_validation_proper.py
- Remove 1.0 vs 0.8 paths and messaging; keep 0.8 throughout
- Update “KEY FINDINGS” to remove references to 100% WVF

22) Validation
- Re‑run cross_validation_proper.py and ensure the comparison focuses purely on optimizer/economics parity items

---

### I. Documentation updates

23) Document exact replication notes
- Add a short dev doc outlining:
  - Where Pareto mask and knee point are implemented in new code
  - Where original CAPEX formula is implemented and how to keep it in sync
  - Where cash flow parity is achieved and how revenue/royalty are applied

---

## Root Cause Analysis (brief initial findings; to be expanded with diffs when implementing)

- Optimizer discrepancy: We previously simplified selection to min CAPEX among feasible. The original uses a Pareto frontier (min CAPEX, max IRR) and then picks the knee. This difference can pick very different configs (affecting CAPEX and IRR).
- CAPEX discrepancy: New code used sizing.calculate_capex_estimate (modern) while original uses capex_estimate_2 with different building/land, equipment lists, and working capital formula; this explains persistent CAPEX and IRR differences.
- Economics discrepancy: Differences in ramp‑up schedule, depreciation base (excluding licensing, 50% of process capital), and royalty application timing can materially change IRR/NPV.
- API zeros: Stemming from optimizer bug (incorrect Pareto mask application) causing exceptions, leading to empty/zeroed result objects returned by the orchestrator.

---

## Concrete Fixes (what I will implement next)

- Optimizer (optimizer_enhanced.py):
  - Add proper Pareto mask function (boolean Series) and original knee selection
  - Keep progressive excess tiers (5% → 15% → 25% → min excess fallback)
  - Fix current bug where mask was misused (causing pandas TypeError)
- CAPEX (sizing.py):
  - Implement calculate_capex_estimate_original replicating capex_estimate_2 formulas and return the same breakdown
  - Use it in evaluate_configuration and pass its breakdown into economics via override
- Economics (econ.py):
  - Add capex_override parameter and use when provided
  - Align cash flows: ramp-up vector and depreciation as original; royalty on pre-royalty EBITDA
  - Keep 0.8 WVF logic for per‑strain mass
- Cross-validation:
  - Remove 1.0 WVF paths; keep 0.8 throughout
- Unit tests:
  - Improve deterministic capacity test assertions
- API:
  - Ensure test_api_direct reads nested result correctly and that the optimizer no longer throws

---

## Validation Steps

- Run: PYTHONPATH=. python cross_validation_proper.py
  - Expect close parity in selected configs (volume/reactors/DS) and CAPEX/IRR within tolerance
- Run: pytest -q
  - Strengthened tests should pass and provide meaningful coverage
- Run API test: python test_api_direct.py
  - Expect non‑zero productions, no silent failures, and reasonable kpis.tpa vs target

---

## Request for confirmation before code changes

- Please proceed to:
  1) Fix optimizer Pareto mask/knee and progressive tolerance (bug fix + parity)
  2) Implement original CAPEX function and wire it into optimization + economics (via override)
  3) Align economics cash flows (ramp‑up, depreciation, royalty application) with original
  4) Keep the per strain annual_production based revenue model in new implementation and modify pricing_integrated_original to match new implementation for annual_production_kg based revenue model in econ.py
  5) Remove 1.0 WVF from cross_validation_proper
  6) Strengthen deterministic capacity unit test
  7) Fix API test to read nested result and validate non-zero outputs
