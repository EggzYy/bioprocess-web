# Codex Tasks

This document tracks outstanding work required to achieve calculation parity between the new bioprocess web application and the original `pricing_integrated_original.py` script.

## Documentation and Planning
1. **Update task lists** – Ensure `UPDATED_TASK_LIST.md` and `TODO Masterplan (detailed and actiona.md` reflect current progress and known gaps.
2. **Maintain parity notes** – Document any deviations discovered during cross‑validation.

## Parity Validation
1. **Optimizer parity**
   - Confirm Pareto front and knee‑point selection matches the legacy algorithm.
   - Enforce progressive excess capacity tiers (5%, 15%, 25%) with minimum‑excess fallback.
   - Ensure optimizer uses parity-mode CAPEX and economics functions.
2. **CAPEX parity**
   - Verify `calculate_capex_estimate_original` reproduces legacy `capex_estimate_2` results.
   - Route parity-mode scenarios through this function and feed breakdowns into `econ.calculate_economics`.
3. **Economics parity**
   - Validate ramp-up schedule, depreciation base, and royalty application mirror the original script.
   - Add coverage for labor floor and cash-flow construction when parity mode is enabled.

## Cross-Validation
1. **Expand search space** – Ensure `pricing_integrated_original.py` and `cross_validation_proper.py` share the same optimization grid.
2. **Run `cross_validation_proper.py`** – Compare production, CAPEX, and IRR/NPV against the original; target ≤5% CAPEX variance and identical production.
3. **Debug differences** – Iterate on optimizer/CAPEX/economics until parity thresholds are met.

## Finalization
1. **Update documentation** – Mark backend tasks as completed once parity is verified.
2. **Create final report** – Summarize methodology, validation results, and remaining follow-up work.
