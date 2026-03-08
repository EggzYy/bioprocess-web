"""
Constrained optimizer module that properly minimizes excess capacity.
Matches original behavior: find minimum equipment that just meets target.

This module is maintained for backward compatibility.
Use optimizer_consolidated.py for new code.
"""

from .optimizer_consolidated import (
    evaluate_configuration,
    optimize_for_minimal_excess,
    optimize_with_constrained_pareto,
    optimize_equipment_configuration,
    sensitivity_analysis,
)

__all__ = [
    "evaluate_configuration",
    "optimize_for_minimal_excess",
    "optimize_with_constrained_pareto",
    "optimize_equipment_configuration",
    "sensitivity_analysis",
]
