# Parity Mode: Economics and Optimizer Alignment

This document explains how the new implementation aligns with `bioprocess/pricing_integrated_original.py` while keeping improved optimization behavior.

## Overview
- parity_mode=True (default) activates original‑style CAPEX and OPEX ramp behaviors in the new stack.
- Optimizer continues to enforce capacity (TPA) and penalize excess, selecting a Pareto knee.
- UI is aligned: Working Volume Fraction is fixed to 0.8 (no user override). KPIs include meets_tpa and production_kg for parity verification.

## CAPEX (original style)
When `scenario.capex.parity_mode=True`, economics uses the original formulas via an override:
- Land and Building: computed per original facility area expressions (depend on fermenters and volume scale)
- Installation: 15% of equipment
- Contingency: 12.5% of direct (land + building + equipment + installation)
- Working Capital: 10% of direct
- Licensing Fixed: included in total CAPEX but excluded from depreciable base

The orchestrator computes original CAPEX with `calculate_capex_estimate_original(...)` and passes the breakdown into `econ.calculate_economics(capex_override=...)`.

## OPEX ramp and Labor
- Cash flows ramp only the variable portion of OPEX; fixed OPEX is constant across operating years:
  - `variable_opex_share` (default 0.85) controls the split
  - Ramp schedule: [0, 0, 0.40, 0.60, 0.75, 0.85] + [0.85] * 7
- Labor parity mode applies a baseline floor of 15 FTEs up to 15 TPA, then scales roughly linearly with TPA.

Unit tests: see `tests/test_econ_parity.py` for OPEX ramp split and labor floor validations.

## Working Volume Fraction (WVF)
- Both original and new implementations use WVF = 0.8 consistently.
- The original capacity builder sets batch mass using working volume (0.8 × volume), ensuring deterministic capacity parity.

## Optimizer behavior
- Original module (`pricing_integrated_original.py`) updated to:
  - Filter to feasible solutions (meets capacity)
  - Compute Pareto front (min CAPEX, max IRR)
  - Select knee with an excess penalty
- New optimizer already enforces capacity and includes progressive excess constraints; the selection is consistent in spirit.

## Cross-validation expectations
- Production parity at selected solutions
- CAPEX within a narrow band (typically <~5% difference)
- IRR/NPV may diverge due to optimizer selection differences; this is acceptable per current policy

## How to use
- Parity mode is on by default via `CapexConfig.parity_mode=True`.
- For end‑to‑end runs, build a `ScenarioInput`, then call orchestrator:
  - `run_optimization(scenario)` or `run_scenario(scenario)`
- For original reference runs, call `pricing_integrated_original.optimize_counts_multiobjective(...)`.

## Troubleshooting
- If CAPEX diverges, ensure `capex_override` is being passed and fermenter counts/volume are coming from the optimizer results in orchestrator.
- If OPEX ramp looks flat, verify `parity_mode=True` and that `variable_opex_share` is set (default 0.85).
- If WebSocket tests hang, check scenario preparation and early cancellation windows in `api/main.py`.

