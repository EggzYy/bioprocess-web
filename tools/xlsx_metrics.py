#!/usr/bin/env python3
"""
Excel Metrics Parser - Policy-compliant extraction from bioprocess workbooks.

This module implements strict extraction rules:
- NEVER use Executive Summary or Financial Metrics sheets
- Follow specific source/fallback rules for each metric
- Handle 80% working volume (values already scaled in Excel)
"""

import pandas as pd
import numpy as np
import re
from typing import Dict, Tuple, Optional, Any, List
from pathlib import Path


def normalize_column_name(col: str) -> str:
    """Normalize column names for robust matching."""
    if pd.isna(col):
        return ""
    return (
        str(col)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("(", "")
        .replace(")", "")
        .replace("%", "pct")
        .replace("$", "usd")
    )


def coerce_numeric(value: Any) -> float:
    """Convert various formats to numeric, return NaN if not possible."""
    if pd.isna(value):
        return np.nan

    # If already numeric
    if isinstance(value, (int, float)):
        return float(value)

    # Convert string representations
    if isinstance(value, str):
        # Remove currency symbols and thousands separators
        cleaned = value.replace("$", "").replace(",", "").replace("USD", "").strip()

        # Handle percentage
        if "%" in cleaned:
            cleaned = cleaned.replace("%", "").strip()
            try:
                return float(cleaned) / 100.0
            except:
                return np.nan

        # Handle parentheses for negative
        if cleaned.startswith("(") and cleaned.endswith(")"):
            cleaned = "-" + cleaned[1:-1]

        try:
            return float(cleaned)
        except:
            return np.nan

    return np.nan


def safe_first_row(df: pd.DataFrame) -> Optional[pd.Series]:
    """Safely get the first data row from a DataFrame."""
    if df is None or df.empty:
        return None

    # Skip any rows that are all NaN (sometimes Excel has empty rows)
    for idx in range(min(5, len(df))):  # Check first 5 rows max
        row = df.iloc[idx]
        if not row.isna().all():
            return row
    return None


def load_workbook(path: str) -> Dict[str, pd.DataFrame]:
    """
    Load all sheets from an Excel workbook.

    Args:
        path: Path to the Excel file

    Returns:
        Dictionary mapping sheet names to DataFrames
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Workbook not found: {path}")

    try:
        xl_file = pd.ExcelFile(path, engine="openpyxl")
        sheets = {}

        for sheet_name in xl_file.sheet_names:
            try:
                df = pd.read_excel(xl_file, sheet_name=sheet_name)
                # Only keep non-empty sheets
                if not df.empty:
                    sheets[sheet_name] = df
            except Exception as e:
                print(f"Warning: Could not read sheet '{sheet_name}': {e}")

        return sheets
    except Exception as e:
        raise RuntimeError(f"Failed to load workbook {path}: {e}")


def get_irr_npv(dfs: Dict[str, pd.DataFrame]) -> Tuple[float, float, str]:
    """
    Extract IRR and NPV from Pareto Frontier (primary) or All Feasible Configurations (fallback).

    Returns:
        Tuple of (irr, npv, source) where source indicates where values came from
    """
    irr, npv = np.nan, np.nan
    source = "not found"

    # Try Pareto Frontier first
    if "Pareto Frontier" in dfs:
        df = dfs["Pareto Frontier"]
        first_row = safe_first_row(df)

        if first_row is not None:
            # Normalize column names for matching
            norm_cols = {normalize_column_name(col): col for col in df.columns}

            # Try to find IRR column
            irr_col = None
            for pattern in ["irr", "irr_pct"]:
                if pattern in norm_cols:
                    irr_col = norm_cols[pattern]
                    break

            # Try to find NPV column
            npv_col = None
            for pattern in ["npv", "npv_usd"]:
                if pattern in norm_cols:
                    npv_col = norm_cols[pattern]
                    break

            if irr_col:
                irr = coerce_numeric(first_row[irr_col])
            if npv_col:
                npv = coerce_numeric(first_row[npv_col])

            if not np.isnan(irr) or not np.isnan(npv):
                source = "Pareto Frontier (first row)"

    # Fallback to All Feasible Configurations
    if (np.isnan(irr) or np.isnan(npv)) and "All Feasible Configurations" in dfs:
        df = dfs["All Feasible Configurations"]
        first_row = safe_first_row(df)

        if first_row is not None:
            norm_cols = {normalize_column_name(col): col for col in df.columns}

            if np.isnan(irr):
                for pattern in ["irr", "irr_pct"]:
                    if pattern in norm_cols:
                        irr = coerce_numeric(first_row[norm_cols[pattern]])
                        if not np.isnan(irr):
                            break

            if np.isnan(npv):
                for pattern in ["npv", "npv_usd"]:
                    if pattern in norm_cols:
                        npv = coerce_numeric(first_row[norm_cols[pattern]])
                        if not np.isnan(npv):
                            break

            if source == "not found" and (not np.isnan(irr) or not np.isnan(npv)):
                source = "All Feasible Configurations (fallback)"

    return irr, npv, source


def get_capex_total(dfs: Dict[str, pd.DataFrame]) -> Tuple[float, str]:
    """
    Extract total CAPEX from CAPEX Summary or Detailed CAPEX Breakdown.

    Returns:
        Tuple of (capex, source)
    """
    capex = np.nan
    source = "not found"

    # Try CAPEX Summary first
    if "CAPEX Summary" in dfs:
        df = dfs["CAPEX Summary"]

        # Look for "Total Initial Investment" row
        for idx, row in df.iterrows():
            # Check first column (usually "CAPEX Component" or similar)
            first_col = df.columns[0]
            if pd.notna(row[first_col]) and "Total Initial Investment" in str(
                row[first_col]
            ):
                # Look for amount column
                for col in df.columns[1:]:
                    norm_col = normalize_column_name(col)
                    if any(x in norm_col for x in ["amount", "cost", "total", "usd"]):
                        capex = coerce_numeric(row[col])
                        if not np.isnan(capex):
                            source = "CAPEX Summary"
                            break
                if not np.isnan(capex):
                    break

    # Fallback to Detailed CAPEX Breakdown
    if np.isnan(capex) and "Detailed CAPEX Breakdown" in dfs:
        df = dfs["Detailed CAPEX Breakdown"]

        # Look for row where Category == "TOTAL" and Item == "Total Initial Investment"
        for idx, row in df.iterrows():
            category_match = False
            item_match = False

            # Check for Category column
            for col in df.columns:
                norm_col = normalize_column_name(col)
                if "category" in norm_col and pd.notna(row[col]):
                    if "TOTAL" in str(row[col]).upper():
                        category_match = True
                elif "item" in norm_col and pd.notna(row[col]):
                    if "Total Initial Investment" in str(row[col]):
                        item_match = True

            if category_match and item_match:
                # Find the cost column
                for col in df.columns:
                    norm_col = normalize_column_name(col)
                    if any(x in norm_col for x in ["total_cost", "cost", "amount"]):
                        capex = coerce_numeric(row[col])
                        if not np.isnan(capex):
                            source = "Detailed CAPEX Breakdown (fallback)"
                            break
                if not np.isnan(capex):
                    break

    return capex, source


def get_opex_total(dfs: Dict[str, pd.DataFrame]) -> Tuple[float, str]:
    """
    Extract total OPEX from OPEX Summary.

    Returns:
        Tuple of (opex, source)
    """
    opex = np.nan
    source = "not found"

    if "OPEX Summary" in dfs:
        df = dfs["OPEX Summary"]

        # Look for "Total Cash OPEX" row
        for idx, row in df.iterrows():
            first_col = df.columns[0]
            if pd.notna(row[first_col]) and "Total Cash OPEX" in str(row[first_col]):
                # Look for amount column
                for col in df.columns[1:]:
                    norm_col = normalize_column_name(col)
                    if any(x in norm_col for x in ["annual", "cost", "amount", "usd"]):
                        opex = coerce_numeric(row[col])
                        if not np.isnan(opex):
                            source = "OPEX Summary"
                            break
                if not np.isnan(opex):
                    break

    return opex, source


def get_production_and_batches(
    dfs: Dict[str, pd.DataFrame],
) -> Tuple[float, float, str]:
    """
    Extract production and batch counts from Calc-PerStrain sheet.
    Aggregates across all strain rows.

    Returns:
        Tuple of (annual_kg, total_batches, source)
    """
    annual_kg = 0.0
    total_batches = 0.0
    source = "not found"

    if "Calc-PerStrain" not in dfs:
        return np.nan, np.nan, "Calc-PerStrain sheet not found"

    df = dfs["Calc-PerStrain"]

    # Normalize column names
    norm_cols = {normalize_column_name(col): col for col in df.columns}

    # Check if annual_kg_good column exists
    annual_col = None
    for pattern in ["annual_kg_good", "annual_production", "annual_kg"]:
        if pattern in norm_cols:
            annual_col = norm_cols[pattern]
            break

    # Check for batch columns
    batch_mass_col = None
    good_batches_col = None

    for pattern in ["batch_mass_kg", "batch_mass", "mass_per_batch"]:
        if pattern in norm_cols:
            batch_mass_col = norm_cols[pattern]
            break

    for pattern in ["good_batches", "batches_good", "batches"]:
        if pattern in norm_cols:
            good_batches_col = norm_cols[pattern]
            break

    # Calculate production
    if annual_col:
        # Primary method: sum annual_kg_good
        annual_kg = df[annual_col].apply(coerce_numeric).sum()
        source = "Calc-PerStrain (annual_kg_good sum)"
    elif batch_mass_col and good_batches_col:
        # Fallback: calculate from batch_mass_kg * good_batches
        df["calculated_annual"] = df[batch_mass_col].apply(coerce_numeric) * df[
            good_batches_col
        ].apply(coerce_numeric)
        annual_kg = df["calculated_annual"].sum()
        source = "Calc-PerStrain (batch_mass_kg × good_batches)"

    # Calculate total batches
    if good_batches_col:
        total_batches = df[good_batches_col].apply(coerce_numeric).sum()

    return annual_kg, total_batches, source


def get_equipment_config(dfs: Dict[str, pd.DataFrame]) -> Tuple[int, int, float, str]:
    """
    Extract equipment configuration from Pareto Frontier or All Feasible Configurations.

    Returns:
        Tuple of (reactors, ds_lines, fermenter_volume_L, source)
    """
    reactors = 0
    ds_lines = 0
    fermenter_volume = 0.0
    source = "not found"

    # Try Pareto Frontier first
    if "Pareto Frontier" in dfs:
        df = dfs["Pareto Frontier"]
        first_row = safe_first_row(df)

        if first_row is not None:
            norm_cols = {normalize_column_name(col): col for col in df.columns}

            if "reactors" in norm_cols:
                reactors = int(coerce_numeric(first_row[norm_cols["reactors"]]))
            if "ds_lines" in norm_cols:
                ds_lines = int(coerce_numeric(first_row[norm_cols["ds_lines"]]))
            if "fermenter_volume_l" in norm_cols:
                fermenter_volume = coerce_numeric(
                    first_row[norm_cols["fermenter_volume_l"]]
                )

            if reactors > 0 or ds_lines > 0 or fermenter_volume > 0:
                source = "Pareto Frontier (first row)"

    # Fallback to All Feasible Configurations
    if (
        reactors == 0 or ds_lines == 0 or fermenter_volume == 0
    ) and "All Feasible Configurations" in dfs:
        df = dfs["All Feasible Configurations"]
        first_row = safe_first_row(df)

        if first_row is not None:
            norm_cols = {normalize_column_name(col): col for col in df.columns}

            if reactors == 0 and "reactors" in norm_cols:
                reactors = int(coerce_numeric(first_row[norm_cols["reactors"]]))
            if ds_lines == 0 and "ds_lines" in norm_cols:
                ds_lines = int(coerce_numeric(first_row[norm_cols["ds_lines"]]))
            if fermenter_volume == 0 and "fermenter_volume_l" in norm_cols:
                fermenter_volume = coerce_numeric(
                    first_row[norm_cols["fermenter_volume_l"]]
                )

            if source == "not found":
                source = "All Feasible Configurations (fallback)"

    return reactors, ds_lines, fermenter_volume, source


def get_strain_list(dfs: Dict[str, pd.DataFrame]) -> Tuple[List[str], str]:
    """
    Extract strain list from Calc-PerStrain or Strain Parameters.

    Returns:
        Tuple of (strain_list, source)
    """
    strains = []
    source = "not found"

    # Try Calc-PerStrain first
    if "Calc-PerStrain" in dfs:
        df = dfs["Calc-PerStrain"]

        # Look for name column
        norm_cols = {normalize_column_name(col): col for col in df.columns}
        name_col = None

        for pattern in ["name", "strain", "strain_name"]:
            if pattern in norm_cols:
                name_col = norm_cols[pattern]
                break

        # If no explicit name column, use first column
        if not name_col and len(df.columns) > 0:
            name_col = df.columns[0]

        if name_col:
            strains = df[name_col].dropna().unique().tolist()
            source = "Calc-PerStrain"

    # Fallback to Strain Parameters
    if not strains and "Strain Parameters" in dfs:
        df = dfs["Strain Parameters"]

        # Similar logic for Strain Parameters
        norm_cols = {normalize_column_name(col): col for col in df.columns}
        name_col = None

        for pattern in ["strain", "name", "strain_name"]:
            if pattern in norm_cols:
                name_col = norm_cols[pattern]
                break

        if not name_col and len(df.columns) > 0:
            name_col = df.columns[0]

        if name_col:
            strains = df[name_col].dropna().unique().tolist()
            source = "Strain Parameters (fallback)"

    return strains, source


def parse_target_tpa(filename: str) -> float:
    """
    Extract target TPA from filename.

    Args:
        filename: Name of the Excel file

    Returns:
        Target TPA value or NaN if not found
    """
    # Look for pattern like "10TPA" or "40TPA"
    match = re.search(r"(\d+)\s*TPA", filename, re.IGNORECASE)
    if match:
        return float(match.group(1))
    return np.nan


def parse_original_workbook(path: str, verbose: bool = False) -> Dict[str, Any]:
    """
    Parse all metrics from an original Excel workbook according to policy.

    Args:
        path: Path to the Excel file
        verbose: If True, print source information

    Returns:
        Dictionary containing all extracted metrics
    """
    path = Path(path)

    # Load all sheets
    dfs = load_workbook(path)

    if verbose:
        print(f"Loaded {len(dfs)} sheets from {path.name}")
        print(f"Sheets: {list(dfs.keys())}")

    # Extract metrics
    irr, npv, irr_npv_source = get_irr_npv(dfs)
    capex, capex_source = get_capex_total(dfs)
    opex, opex_source = get_opex_total(dfs)
    annual_kg, total_batches, prod_source = get_production_and_batches(dfs)
    reactors, ds_lines, fermenter_volume, equip_source = get_equipment_config(dfs)
    strains, strain_source = get_strain_list(dfs)
    target_tpa = parse_target_tpa(path.name)

    result = {
        "filename": path.name,
        "path": str(path),
        "target_tpa": target_tpa,
        "strains": strains,
        "fermenter_volume_l": fermenter_volume,
        "reactors": reactors,
        "ds_lines": ds_lines,
        "annual_kg_good": annual_kg,
        "total_good_batches": total_batches,
        "total_capex": capex,
        "total_opex": opex,
        "irr": irr,
        "npv": npv,
        "sources": {
            "irr_npv": irr_npv_source,
            "capex": capex_source,
            "opex": opex_source,
            "production": prod_source,
            "equipment": equip_source,
            "strains": strain_source,
        },
    }

    if verbose:
        print("\nExtracted Metrics:")
        print(f"  Target TPA: {target_tpa}")
        print(
            f"  Strains ({len(strains)}): {', '.join(strains[:3])}..."
            if len(strains) > 3
            else f"  Strains: {', '.join(strains)}"
        )
        print(
            f"  Equipment: {reactors} reactors, {ds_lines} DS lines, {fermenter_volume:.0f}L fermenters"
        )
        print(f"  Production: {annual_kg:.0f} kg/year in {total_batches:.0f} batches")
        print(f"  CAPEX: ${capex:,.0f}")
        print(f"  OPEX: ${opex:,.0f}")
        print(f"  IRR: {irr:.1%}" if not np.isnan(irr) else "  IRR: N/A")
        print(f"  NPV: ${npv:,.0f}" if not np.isnan(npv) else "  NPV: N/A")
        print("\nSources:")
        for key, source in result["sources"].items():
            print(f"  {key}: {source}")

    return result


def validate_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Validate extracted metrics and return list of warnings.

    Args:
        metrics: Dictionary of extracted metrics

    Returns:
        List of warning messages
    """
    warnings = []

    # Check for missing critical metrics
    if np.isnan(metrics.get("annual_kg_good", np.nan)):
        warnings.append("Missing annual production (kg)")
    elif metrics["annual_kg_good"] <= 0:
        warnings.append(f"Invalid annual production: {metrics['annual_kg_good']}")

    if np.isnan(metrics.get("total_capex", np.nan)):
        warnings.append("Missing CAPEX")
    elif metrics["total_capex"] <= 0:
        warnings.append(f"Invalid CAPEX: {metrics['total_capex']}")

    # Check IRR range
    irr = metrics.get("irr", np.nan)
    if not np.isnan(irr):
        if irr < -1.0:
            warnings.append(f"IRR below -100%: {irr:.1%}")
        elif irr > 2.0:
            warnings.append(f"IRR above 200%: {irr:.1%}")

    # Check fermenter volume range
    volume = metrics.get("fermenter_volume_l", 0)
    if volume > 0:
        if volume < 100 or volume > 10000:
            warnings.append(f"Unusual fermenter volume: {volume}L")

    # Check production vs batches consistency
    if (
        metrics.get("annual_kg_good", 0) > 0
        and metrics.get("total_good_batches", 0) == 0
    ):
        warnings.append("Production > 0 but batches = 0")

    return warnings


if __name__ == "__main__":
    # Test with one of the workbooks
    import sys

    if len(sys.argv) > 1:
        path = sys.argv[1]
    else:
        path = "Facility1_Yogurt_Cultures_10TPA_calc.xlsx"

    print(f"Testing parser with: {path}")
    print("=" * 80)

    metrics = parse_original_workbook(path, verbose=True)

    print("\n" + "=" * 80)
    print("Validation:")
    warnings = validate_metrics(metrics)
    if warnings:
        for warning in warnings:
            print(f"  ⚠️  {warning}")
    else:
        print("  ✅ All metrics valid")
