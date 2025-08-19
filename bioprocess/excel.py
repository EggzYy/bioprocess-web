"""
Excel export module.
Generates multi-sheet workbooks with facility design results.
"""

import io
from typing import Dict, Any, Optional, List
import pandas as pd

from .models import ScenarioResult, ScenarioInput


def format_currency(value: float) -> str:
    """Format value as currency string."""
    return f"${value:,.0f}"


def format_percentage(value: float) -> str:
    """Format value as percentage string."""
    return f"{value:.2%}"


def create_summary_sheet(result: ScenarioResult) -> pd.DataFrame:
    """Create executive summary sheet."""
    summary_data = {
        "Metric": [
            "Scenario Name",
            "Calculation Date",
            "",
            "--- KEY PERFORMANCE INDICATORS ---",
            "Net Present Value (NPV)",
            "Internal Rate of Return (IRR)",
            "Payback Period",
            "EBITDA Margin",
            "",
            "--- CAPACITY METRICS ---",
            "Annual Production",
            "Target Production",
            "Capacity Utilization",
            "System Bottleneck",
            "",
            "--- FINANCIAL SUMMARY ---",
            "Total CAPEX",
            "Annual Revenue",
            "Annual OPEX",
            "OPEX per kg",
            "",
            "--- EQUIPMENT CONFIGURATION ---",
            "Fermenter Volume",
            "Number of Fermenters",
            "Number of DS Lines",
            "Upstream Utilization",
            "Downstream Utilization",
        ],
        "Value": [
            result.scenario_name,
            result.timestamp,
            "",
            "",
            format_currency(result.kpis.get("npv", 0)),
            format_percentage(result.kpis.get("irr", 0)),
            f"{result.kpis.get('payback_years', 0):.1f} years",
            format_percentage(result.economics.ebitda_margin),
            "",
            "",
            f"{result.capacity.total_annual_kg:,.0f} kg",
            f"{result.kpis.get('tpa', 0):,.1f} TPA",
            format_percentage(
                result.capacity.total_annual_kg / (result.kpis.get("tpa", 10) * 1000)
            ),
            result.capacity.bottleneck.upper(),
            "",
            "",
            format_currency(result.economics.total_capex),
            format_currency(result.economics.annual_revenue),
            format_currency(result.economics.total_opex),
            f"${result.economics.total_opex / result.capacity.total_annual_kg:.2f}/kg",
            "",
            "",
            f"{result.equipment.specifications.get('fermenter_volume_l', 0):,.0f} L",
            str(list(result.equipment.counts.values())[0]),
            str(result.equipment.counts.get("lyophilizers", 0)),
            format_percentage(result.capacity.weighted_up_utilization),
            format_percentage(result.capacity.weighted_ds_utilization),
        ],
    }

    return pd.DataFrame(summary_data)


def create_capacity_sheet(result: ScenarioResult) -> pd.DataFrame:
    """Create capacity analysis sheet."""
    return pd.DataFrame(result.capacity.per_strain)


def create_equipment_sheet(result: ScenarioResult) -> pd.DataFrame:
    """Create equipment specifications sheet."""
    equipment_data = []

    for equipment_type, count in result.equipment.counts.items():
        equipment_data.append(
            {
                "Equipment Type": equipment_type.replace("_", " ").title(),
                "Quantity": count,
                "Unit Cost": "",
                "Total Cost": "",
            }
        )

    # Add specifications
    equipment_data.append(
        {"Equipment Type": "", "Quantity": "", "Unit Cost": "", "Total Cost": ""}
    )
    equipment_data.append(
        {
            "Equipment Type": "--- SPECIFICATIONS ---",
            "Quantity": "",
            "Unit Cost": "",
            "Total Cost": "",
        }
    )

    for spec_name, spec_value in result.equipment.specifications.items():
        if not isinstance(spec_value, dict):
            equipment_data.append(
                {
                    "Equipment Type": spec_name.replace("_", " ").title(),
                    "Quantity": str(spec_value),
                    "Unit Cost": "",
                    "Total Cost": "",
                }
            )

    return pd.DataFrame(equipment_data)


def create_capex_sheet(result: ScenarioResult) -> pd.DataFrame:
    """Create CAPEX breakdown sheet."""
    capex_data = [
        {"Component": "Land", "Cost (USD)": result.economics.land_cost},
        {
            "Component": "Building & Cleanrooms",
            "Cost (USD)": result.economics.building_cost,
        },
        {
            "Component": "Process Equipment",
            "Cost (USD)": result.economics.equipment_cost,
        },
        {"Component": "Installation", "Cost (USD)": result.equipment.installation_cost},
        {
            "Component": "Utilities Infrastructure",
            "Cost (USD)": result.equipment.utilities_cost,
        },
        {
            "Component": "Subtotal - Direct Costs",
            "Cost (USD)": result.economics.land_cost
            + result.economics.building_cost
            + result.economics.equipment_cost
            + result.equipment.installation_cost
            + result.equipment.utilities_cost,
        },
        {"Component": "Contingency", "Cost (USD)": result.economics.contingency},
        {
            "Component": "Working Capital",
            "Cost (USD)": result.economics.working_capital,
        },
        {
            "Component": "Licensing (Fixed)",
            "Cost (USD)": result.economics.licensing_fixed,
        },
        {"Component": "TOTAL CAPEX", "Cost (USD)": result.economics.total_capex},
    ]

    return pd.DataFrame(capex_data)


def create_opex_sheet(result: ScenarioResult) -> pd.DataFrame:
    """Create OPEX breakdown sheet."""
    opex_data = [
        {
            "Component": "Raw Materials",
            "Annual Cost (USD)": result.economics.raw_materials_cost,
            "Per kg": result.economics.raw_materials_cost
            / result.capacity.total_annual_kg,
        },
        {
            "Component": "Utilities",
            "Annual Cost (USD)": result.economics.utilities_cost,
            "Per kg": result.economics.utilities_cost / result.capacity.total_annual_kg,
        },
        {
            "Component": "Labor",
            "Annual Cost (USD)": result.economics.labor_cost,
            "Per kg": result.economics.labor_cost / result.capacity.total_annual_kg,
        },
        {
            "Component": "Maintenance",
            "Annual Cost (USD)": result.economics.maintenance_cost,
            "Per kg": result.economics.maintenance_cost
            / result.capacity.total_annual_kg,
        },
        {
            "Component": "G&A & Other",
            "Annual Cost (USD)": result.economics.ga_other_cost,
            "Per kg": result.economics.ga_other_cost / result.capacity.total_annual_kg,
        },
        {
            "Component": "TOTAL OPEX",
            "Annual Cost (USD)": result.economics.total_opex,
            "Per kg": result.economics.total_opex / result.capacity.total_annual_kg,
        },
    ]

    if result.economics.licensing_royalty_rate > 0:
        opex_data.append(
            {
                "Component": f"Licensing Royalty ({result.economics.licensing_royalty_rate:.2%} of EBITDA)",
                "Annual Cost (USD)": "Variable",
                "Per kg": "Variable",
            }
        )

    return pd.DataFrame(opex_data)


def create_cashflow_sheet(result: ScenarioResult) -> pd.DataFrame:
    """Create cash flow analysis sheet."""
    years = list(range(len(result.economics.cash_flows)))

    cashflow_data = {
        "Year": years,
        "Cash Flow (USD)": result.economics.cash_flows,
        "Cumulative Cash Flow (USD)": pd.Series(result.economics.cash_flows)
        .cumsum()
        .tolist(),
    }

    df = pd.DataFrame(cashflow_data)

    # Add NPV and IRR at the bottom
    summary_row = pd.DataFrame(
        {
            "Year": ["", "NPV", "IRR"],
            "Cash Flow (USD)": ["", result.economics.npv, result.economics.irr],
            "Cumulative Cash Flow (USD)": ["", "", ""],
        }
    )

    df = pd.concat([df, summary_row], ignore_index=True)

    return df


def create_sensitivity_sheet(
    sensitivity_result: Optional[pd.DataFrame],
) -> pd.DataFrame:
    """Create sensitivity analysis sheet."""
    if sensitivity_result is None or sensitivity_result.empty:
        return pd.DataFrame({"Note": ["Sensitivity analysis not performed"]})

    return sensitivity_result


def create_optimization_sheet(result: ScenarioResult) -> pd.DataFrame:
    """Create optimization results sheet."""
    if result.optimization is None:
        return pd.DataFrame({"Note": ["Optimization not performed"]})

    if result.optimization.pareto_front:
        return pd.DataFrame(result.optimization.pareto_front)
    else:
        return pd.DataFrame([result.optimization.best_solution])


def export_to_excel(
    result: ScenarioResult,
    scenario: Optional[ScenarioInput] = None,
    filename: Optional[str] = None,
) -> bytes:
    """
    Export complete results to Excel workbook.

    Args:
        result: Scenario calculation results
        scenario: Original scenario input (optional)
        filename: Output filename (optional)

    Returns:
        Excel file as bytes
    """
    # Create in-memory buffer
    output = io.BytesIO()

    # Create Excel writer
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        workbook = writer.book

        # Define formats
        currency_format = workbook.add_format({"num_format": "$#,##0"})
        percent_format = workbook.add_format({"num_format": "0.00%"})
        header_format = workbook.add_format(
            {"bold": True, "bg_color": "#D3D3D3", "border": 1}
        )

        # Create sheets
        sheets = {
            "Executive Summary": create_summary_sheet(result),
            "Capacity Analysis": create_capacity_sheet(result),
            "Equipment": create_equipment_sheet(result),
            "CAPEX Breakdown": create_capex_sheet(result),
            "OPEX Breakdown": create_opex_sheet(result),
            "Cash Flow": create_cashflow_sheet(result),
        }

        # Add optional sheets
        if result.sensitivity:
            sheets["Sensitivity"] = create_sensitivity_sheet(
                pd.DataFrame(result.sensitivity.tornado_data)
                if result.sensitivity.tornado_data
                else None
            )

        if result.optimization:
            sheets["Optimization"] = create_optimization_sheet(result)

        # Write each sheet
        for sheet_name, df in sheets.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)

            # Get worksheet
            worksheet = writer.sheets[sheet_name]

            # Auto-fit columns
            for i, col in enumerate(df.columns):
                column_len = max(df[col].astype(str).str.len().max(), len(col))
                worksheet.set_column(i, i, min(column_len + 2, 50))

        # Add charts if data is available
        if "Cash Flow" in sheets:
            add_cashflow_chart(
                workbook, writer.sheets["Cash Flow"], len(sheets["Cash Flow"])
            )

    # Get Excel file bytes
    excel_bytes = output.getvalue()
    output.close()

    return excel_bytes


def add_cashflow_chart(workbook, worksheet, num_rows: int):
    """Add cash flow chart to worksheet."""
    # Create chart
    chart = workbook.add_chart({"type": "line"})

    # Add data series
    chart.add_series(
        {
            "name": "Cash Flow",
            "categories": ["Cash Flow", 1, 0, num_rows - 4, 0],  # Exclude summary rows
            "values": ["Cash Flow", 1, 1, num_rows - 4, 1],
            "line": {"color": "blue", "width": 2},
        }
    )

    chart.add_series(
        {
            "name": "Cumulative Cash Flow",
            "categories": ["Cash Flow", 1, 0, num_rows - 4, 0],
            "values": ["Cash Flow", 1, 2, num_rows - 4, 2],
            "line": {"color": "green", "width": 2},
        }
    )

    # Set chart properties
    chart.set_title({"name": "Cash Flow Analysis"})
    chart.set_x_axis({"name": "Year"})
    chart.set_y_axis({"name": "Cash Flow (USD)", "num_format": "$#,##0"})
    chart.set_size({"width": 600, "height": 400})

    # Insert chart
    worksheet.insert_chart("E2", chart)


def create_strain_input_sheet(strains: List[Dict[str, Any]]) -> pd.DataFrame:
    """Create strain input parameters sheet."""
    return pd.DataFrame(strains)


def create_assumptions_sheet(assumptions: Dict[str, Any]) -> pd.DataFrame:
    """Create assumptions sheet."""
    assumptions_data = []

    for key, value in assumptions.items():
        assumptions_data.append(
            {
                "Parameter": key.replace("_", " ").title(),
                "Value": value,
                "Unit": get_unit_for_parameter(key),
            }
        )

    return pd.DataFrame(assumptions_data)


def get_unit_for_parameter(param: str) -> str:
    """Get unit string for a parameter."""
    units = {
        "hours_per_year": "hours",
        "upstream_availability": "%",
        "downstream_availability": "%",
        "quality_yield": "%",
        "discount_rate": "%",
        "tax_rate": "%",
        "variable_opex_share": "%",
        "maintenance_pct_of_equip": "%",
        "electricity_usd_per_kwh": "$/kWh",
        "steam_usd_per_kg": "$/kg",
        "water_usd_per_m3": "$/m³",
        "fermenter_volume_l": "L",
        "target_tpa": "TPA",
    }

    for key, unit in units.items():
        if key in param.lower():
            return unit

    if "cost" in param.lower() or "price" in param.lower() or "salary" in param.lower():
        return "USD"

    return ""
