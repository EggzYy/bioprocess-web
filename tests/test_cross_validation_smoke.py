import math
import pytest
# Import from top-level module path
from cross_validation_proper import build_scenario_facility1, run_original_implementation as run_original, run_new


def test_facility1_parity_mode_smoke():
    scenario = build_scenario_facility1()
    # Ensure parity mode is on by default; leave volumes/options to defaults used by cross_validation
    orig = run_original(1)
    new = run_new("Facility 1 - Yogurt Cultures (10 TPA)", scenario)

    # Both should meet TPA (new may coerce bool to float in KPIs model)
    assert bool(orig["meets_tpa"]) is True
    assert bool(new["meets_tpa"]) is True

    # Production parity within tolerance (note: original uses 'production' key)
    assert math.isclose(orig.get("production", orig.get("production_kg", 0.0)), new["production_kg"], rel_tol=5e-2)

    # CAPEX within reasonable window under parity mode (<= 7.5%)
    capex_diff = abs(new["capex"] - orig["capex"]) / max(orig["capex"], 1.0)
    assert capex_diff <= 0.075
