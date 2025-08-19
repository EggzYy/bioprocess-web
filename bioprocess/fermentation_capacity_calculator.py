
# Fermentation & Downstream Throughput Calculator
#
# This module provides deterministic and Monte Carlo capacity calculators for
# multi-strain, multi-reactor, multi-downstream-line bioprocess facilities.
#
# Update (2025-08-12):
# - Added "round-robin" (time-sharing) allocation when total reactors (or DS lines)
#   are fewer than the number of strains. Instead of assigning 0 units to some strains,
#   each strain receives a fractional share of the equipment capacity based on the
#   selected allocation policy (equal, proportional, inverse_ct).
# - Utilization calculations now respect fractional shares (no min 1.0 clamp in the denominator).
#
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple, Literal
import math
import json
import pandas as pd
import numpy as np

@dataclass
class StrainSpec:
    """Specification for a bacterial/yeast strain including process times and utility rates.
    
    IMPORTANT: Utility rate units (Fix reference: 2025-01)
    
    RATIONALE: Legacy pilot-scale data stored utility rates with inconsistent units.
    This led to incorrect scaling when computing electricity costs. The documentation
    below clarifies the actual units to ensure correct calculations:
    
    Attributes:
        name: Strain identifier
        fermentation_time_h: Fed-batch fermentation duration (hours)
        turnaround_time_h: Time for CIP, preparation between batches (hours)
        downstream_time_h: Time for centrifugation and lyophilization (hours)
        batch_mass_kg: Expected dry mass yield per batch (kg)
        cv_ferm: Coefficient of variation for fermentation time (for Monte Carlo)
        cv_turn: Coefficient of variation for turnaround time (for Monte Carlo)
        cv_down: Coefficient of variation for downstream time (for Monte Carlo)
        
        utility_rate_ferm_kw: Total kWh per batch for fermentation (NOT a rate!)
            - Legacy storage: base_rate × fermentation_time_h
            - Example: 18 kW × 14 h = 252 kWh total per batch
            - DO NOT multiply by time when computing costs
            
        utility_rate_cent_kw: Power rate in kW per m³ for centrifugation
            - Energy per batch = utility_rate_cent_kw × downstream_time_h × fermenter_volume_m³
            - Must scale by both time AND volume
            
        utility_rate_lyo_kw: Power rate in kW per (0.15 × fermenter volume in m³) for lyophilization
            - Energy per batch = utility_rate_lyo_kw × downstream_time_h × (fermenter_volume_L × 0.15/1000)
            - The 0.15 factor represents concentrated fraction after centrifugation
            - Must scale by time AND 15% of fermenter volume
            
        utility_cost_steam: Steam cost per kg of product (USD/kg)
    """
    name: str
    fermentation_time_h: float
    turnaround_time_h: float
    downstream_time_h: float
    batch_mass_kg: Optional[float] = None
    cv_ferm: Optional[float] = None
    cv_turn: Optional[float] = None
    cv_down: Optional[float] = None
    utility_rate_ferm_kw: Optional[float] = None
    utility_rate_cent_kw: Optional[float] = None
    utility_rate_lyo_kw: Optional[float] = None
    utility_cost_steam: Optional[float] = None

@dataclass
class EquipmentConfig:
    year_hours: float = 8760.0
    reactors_total: Optional[int] = None
    reactors_per_strain: Optional[Dict[str, int]] = None
    ds_lines_total: Optional[int] = None
    ds_lines_per_strain: Optional[Dict[str, int]] = None
    upstream_availability: float = 0.9
    downstream_availability: float = 0.9
    quality_yield: float = 0.98

def _safe_div(a: float, b: float) -> float:
    return a / b if (b is not None and b > 0) else 0.0

def _allocation_from_totals(names, totals, weights=None, policy="equal"):
    # Integer allocation (legacy behavior)
    n = len(names)
    if n == 0 or totals is None or totals <= 0:
        return {name: 0 for name in names}
    if policy == "equal" or weights is None:
        base = totals // n
        rem = totals - base * n
        alloc = {name: base for name in names}
        for i in range(rem):
            alloc[names[i % n]] += 1
        return alloc
    w = np.array(weights, dtype=float)
    w = np.maximum(w, 0.0)
    if w.sum() == 0:
        return _allocation_from_totals(names, totals, None, "equal")
    raw = w / w.sum() * totals
    floored = np.floor(raw).astype(int)
    alloc = {name: int(f) for name, f in zip(names, floored)}
    remainder = int(totals - floored.sum())
    frac_order = np.argsort(-(raw - floored))
    for idx in frac_order[:remainder]:
        alloc[names[idx]] += 1
    return alloc

def _share_allocation(names, total_units, weights=None, policy="equal"):
    # Fractional (time-share) allocation whose shares sum to total_units
    n = len(names)
    if n == 0 or total_units is None or total_units <= 0:
        return {name: 0.0 for name in names}
    if policy == "equal" or weights is None:
        share = float(total_units) / float(n)
        return {name: share for name in names}
    w = np.array(weights, dtype=float)
    w = np.maximum(w, 0.0)
    if w.sum() == 0:
        return _share_allocation(names, total_units, None, "equal")
    shares = (w / w.sum()) * float(total_units)
    return {name: float(s) for name, s in zip(names, shares)}

def _deterministic_per_strain_capacity(strain, reactors_assigned, lines_assigned, cfg):
    ct_up = strain.fermentation_time_h + strain.turnaround_time_h
    ct_ds = strain.downstream_time_h
    up_hours = cfg.year_hours * cfg.upstream_availability
    ds_hours = cfg.year_hours * cfg.downstream_availability

    # Allow fractional equipment shares
    up_batches = reactors_assigned * _safe_div(up_hours, ct_up)
    ds_batches = lines_assigned * _safe_div(ds_hours, ct_ds)

    feasible_batches = min(up_batches, ds_batches) if (reactors_assigned > 0 and lines_assigned > 0) else 0.0
    good_batches = feasible_batches * cfg.quality_yield

    # Utilization based on fractional shares (no min-1 clamp)
    up_util = 0.0
    ds_util = 0.0
    if reactors_assigned > 0:
        up_util = min(1.0, _safe_div(feasible_batches * ct_up, reactors_assigned * up_hours))
    if lines_assigned > 0:
        ds_util = min(1.0, _safe_div(feasible_batches * ct_ds, lines_assigned * ds_hours))

    out = {
        "ct_up_h": ct_up,
        "ct_ds_h": ct_ds,
        "reactors_assigned": reactors_assigned,
        "ds_lines_assigned": lines_assigned,
        "up_capacity_batches": up_batches,
        "ds_capacity_batches": ds_batches,
        "feasible_batches": feasible_batches,
        "good_batches": good_batches,
        "up_utilization": up_util,
        "ds_utilization": ds_util,
    }
    if strain.batch_mass_kg is not None:
        out["annual_kg_good"] = good_batches * strain.batch_mass_kg
    return out

def calculate_deterministic_capacity(
    strains: List[StrainSpec],
    cfg: EquipmentConfig,
    reactor_allocation_policy: Literal["equal", "proportional", "inverse_ct"] = "inverse_ct",
    ds_allocation_policy: Literal["equal", "proportional", "inverse_ct"] = "inverse_ct",
    shared_downstream: bool = True,
):
    names = [s.name for s in strains]

    # ---- Reactor allocation (supports time-sharing when reactors < strains) ----
    if cfg.reactors_per_strain is not None:
        reactors_alloc = {name: float(cfg.reactors_per_strain.get(name, 0)) for name in names}
    else:
        if cfg.reactors_total is None:
            reactors_alloc = {name: 1.0 for name in names}
        else:
            ct_up = np.array([s.fermentation_time_h + s.turnaround_time_h for s in strains], dtype=float)
            if reactor_allocation_policy in ("proportional", "inverse_ct"):
                weights = 1.0 / np.maximum(ct_up, 1e-9)
            else:
                weights = None
            total_R = float(cfg.reactors_total)
            if total_R >= len(names):
                # legacy integer allocation when we have at least as many reactors as strains
                int_alloc = _allocation_from_totals(names, int(round(total_R)), weights, 
                                                    "equal" if weights is None else "proportional")
                reactors_alloc = {k: float(v) for k, v in int_alloc.items()}
            else:
                # round-robin / time-share allocation
                reactors_alloc = _share_allocation(names, total_R, weights, 
                                                   "equal" if weights is None else "proportional")

    # ---- Downstream allocation (supports time-sharing when lines < strains) ----
    if cfg.ds_lines_per_strain is not None:
        ds_alloc = {name: float(cfg.ds_lines_per_strain.get(name, 0)) for name in names}
    else:
        if cfg.ds_lines_total is None:
            ds_alloc = {name: 1.0 for name in names}
        else:
            ct_ds = np.array([s.downstream_time_h for s in strains], dtype=float)
            if ds_allocation_policy in ("proportional", "inverse_ct"):
                weights = 1.0 / np.maximum(ct_ds, 1e-9)
            else:
                weights = None
            total_D = float(cfg.ds_lines_total)
            if total_D >= len(names):
                int_alloc = _allocation_from_totals(names, int(round(total_D)), weights, 
                                                    "equal" if weights is None else "proportional")
                ds_alloc = {k: float(v) for k, v in int_alloc.items()}
            else:
                ds_alloc = _share_allocation(names, total_D, weights, 
                                             "equal" if weights is None else "proportional")

    rows = []
    for s in strains:
        r = _deterministic_per_strain_capacity(
            strain=s,
            reactors_assigned=float(reactors_alloc.get(s.name, 0.0)),
            lines_assigned=float(ds_alloc.get(s.name, 0.0)),
            cfg=cfg,
        )
        rows.append({**asdict(s), **r})
    df = pd.DataFrame(rows)

    # Plant totals
    totals = {
        "total_feasible_batches": float(df["feasible_batches"].sum()),
        "total_good_batches": float(df["good_batches"].sum()),
        # Keep weighting stable; avoid zero weights
        "weighted_up_utilization": float(np.average(df["up_utilization"], weights=np.maximum(df["reactors_assigned"], 1e-6))),
        "weighted_ds_utilization": float(np.average(df["ds_utilization"], weights=np.maximum(df["ds_lines_assigned"], 1e-6))),
        "reactors_allocated_effective": float(sum(reactors_alloc.values())),
        "ds_lines_allocated_effective": float(sum(ds_alloc.values())),
    }
    if "annual_kg_good" in df.columns:
        totals["total_annual_kg_good"] = float(df.get("annual_kg_good", pd.Series(dtype=float)).sum())
    return df, totals

def _sample_lognormal_from_mean_cv(mean: float, cv: float, size: int) -> np.ndarray:
    if mean <= 0 or cv is None or cv <= 0:
        return np.full(size, mean)
    sigma2 = math.log(cv**2 + 1.0)
    sigma = math.sqrt(sigma2)
    mu = math.log(mean) - 0.5 * sigma2
    return np.random.lognormal(mean=mu, sigma=sigma, size=size)

def monte_carlo_capacity(
    strains: List[StrainSpec],
    cfg: EquipmentConfig,
    n_sims: int = 1000,
    seed: Optional[int] = 42,
    reactor_allocation_policy: Literal["equal", "proportional", "inverse_ct"] = "inverse_ct",
    ds_allocation_policy: Literal["equal", "proportional", "inverse_ct"] = "inverse_ct",
):
    if seed is not None:
        np.random.seed(seed)
    df_det, totals_det = calculate_deterministic_capacity(
        strains, cfg, reactor_allocation_policy, ds_allocation_policy
    )
    reactors_alloc = {row["name"]: float(row["reactors_assigned"]) for _, row in df_det.iterrows()}
    ds_alloc = {row["name"]: float(row["ds_lines_assigned"]) for _, row in df_det.iterrows()}
    results = []
    for _ in range(n_sims):
        plant_batches = 0.0
        plant_good = 0.0
        plant_kg = 0.0
        for s in strains:
            ferm = float(_sample_lognormal_from_mean_cv(s.fermentation_time_h, s.cv_ferm or 0.0, 1)[0])
            turn = float(_sample_lognormal_from_mean_cv(s.turnaround_time_h, s.cv_turn or 0.0, 1)[0])
            down = float(_sample_lognormal_from_mean_cv(s.downstream_time_h, s.cv_down or 0.0, 1)[0])
            s_tmp = StrainSpec(
                name=s.name,
                fermentation_time_h=ferm,
                turnaround_time_h=turn,
                downstream_time_h=down,
                batch_mass_kg=s.batch_mass_kg
            )
            r = _deterministic_per_strain_capacity(
                strain=s_tmp,
                reactors_assigned=reactors_alloc[s.name],
                lines_assigned=ds_alloc[s.name],
                cfg=cfg
            )
            plant_batches += r["feasible_batches"]
            plant_good += r["good_batches"]
            plant_kg += r.get("annual_kg_good", 0.0)
        results.append({"feasible_batches": plant_batches, "good_batches": plant_good, "annual_kg_good": plant_kg})
    df = pd.DataFrame(results)
    summary = df.agg(["mean", "std", "min", "max", "median", lambda x: x.quantile(0.05), lambda x: x.quantile(0.95)])
    summary.index = ["mean", "std", "min", "max", "median", "p05", "p95"]
    return summary
