/**
 * Enhanced Visualization Components for Bioprocess Web Application
 */

class ChartManager {
    constructor() {
        this.charts = {};
        this.colors = {
            primary: '#0d6efd',
            success: '#198754',
            warning: '#ffc107',
            danger: '#dc3545',
            info: '#0dcaf0',
            secondary: '#6c757d'
        };
    }

    /**
     * Create utilization gauge charts
     */
    createUtilizationGauges(capacity) {
        const upGauge = {
            type: "indicator",
            mode: "gauge+number+delta",
            value: capacity.weighted_up_utilization * 100,
            title: { text: "Upstream Utilization (%)" },
            gauge: {
                axis: { range: [null, 100] },
                bar: { color: this.getUtilizationColor(capacity.weighted_up_utilization) },
                steps: [
                    { range: [0, 50], color: "lightgray" },
                    { range: [50, 80], color: "#f0f0f0" },
                    { range: [80, 100], color: "#e0e0e0" }
                ],
                threshold: {
                    line: { color: "red", width: 4 },
                    thickness: 0.75,
                    value: 90
                }
            }
        };

        const dsGauge = {
            type: "indicator",
            mode: "gauge+number+delta",
            value: capacity.weighted_ds_utilization * 100,
            title: { text: "Downstream Utilization (%)" },
            gauge: {
                axis: { range: [null, 100] },
                bar: { color: this.getUtilizationColor(capacity.weighted_ds_utilization) },
                steps: [
                    { range: [0, 50], color: "lightgray" },
                    { range: [50, 80], color: "#f0f0f0" },
                    { range: [80, 100], color: "#e0e0e0" }
                ],
                threshold: {
                    line: { color: "red", width: 4 },
                    thickness: 0.75,
                    value: 90
                }
            }
        };

        const layout = {
            grid: { rows: 1, columns: 2, pattern: 'independent' },
            height: 300
        };

        Plotly.newPlot('utilizationChart', [upGauge, dsGauge], layout);
    }

    /**
     * Create production breakdown by strain
     */
    createProductionChart(capacity) {
        if (!capacity.per_strain || capacity.per_strain.length === 0) {
            return;
        }

        const strainNames = capacity.per_strain.map(s => s.name || 'Unknown');
        const production = capacity.per_strain.map(s => s.annual_kg || 0);
        const batches = capacity.per_strain.map(s => s.good_batches || 0);

        const trace1 = {
            x: strainNames,
            y: production,
            name: 'Annual Production (kg)',
            type: 'bar',
            marker: { color: this.colors.primary }
        };

        const trace2 = {
            x: strainNames,
            y: batches,
            name: 'Good Batches',
            type: 'bar',
            yaxis: 'y2',
            marker: { color: this.colors.success }
        };

        const layout = {
            title: 'Production by Strain',
            xaxis: { title: 'Strain' },
            yaxis: { title: 'Production (kg)', side: 'left' },
            yaxis2: {
                title: 'Batches',
                overlaying: 'y',
                side: 'right'
            },
            hovermode: 'x unified',
            height: 400
        };

        Plotly.newPlot('productionChart', [trace1, trace2], layout);
    }

    /**
     * Create capacity waterfall chart
     */
    createCapacityWaterfall(capacity) {
        const theoretical = capacity.total_feasible_batches * 1.1; // Assume 10% higher theoretical
        const feasible = capacity.total_feasible_batches;
        const good = capacity.total_good_batches;
        const final_kg = capacity.total_annual_kg;

        const trace = {
            type: "waterfall",
            orientation: "v",
            measure: ["absolute", "relative", "relative", "total"],
            x: ["Theoretical Max", "Availability Loss", "Quality Loss", "Final Production"],
            y: [theoretical, -(theoretical - feasible), -(feasible - good), final_kg/1000],
            text: [
                `${theoretical.toFixed(0)} batches`,
                `-${(theoretical - feasible).toFixed(0)} batches`,
                `-${(feasible - good).toFixed(0)} batches`,
                `${(final_kg/1000).toFixed(1)} tons`
            ],
            textposition: "outside",
            connector: { line: { color: "rgb(63, 63, 63)" } }
        };

        const layout = {
            title: "Capacity Waterfall Analysis",
            xaxis: { title: "Stage" },
            yaxis: { title: "Batches / Production" },
            height: 400,
            showlegend: false
        };

        Plotly.newPlot('capacityChart', [trace], layout);
    }

    /**
     * Create economic metrics over time
     */
    createFinancialTimeline(economics) {
        if (!economics.cash_flows || economics.cash_flows.length === 0) {
            return;
        }

        const years = Array.from({ length: economics.cash_flows.length }, (_, i) => i);
        const cumulative = [];
        let sum = 0;
        for (let cf of economics.cash_flows) {
            sum += cf;
            cumulative.push(sum);
        }

        const trace1 = {
            x: years,
            y: economics.cash_flows,
            type: 'bar',
            name: 'Annual Cash Flow',
            marker: {
                color: economics.cash_flows.map(v => v >= 0 ? this.colors.success : this.colors.danger)
            }
        };

        const trace2 = {
            x: years,
            y: cumulative,
            type: 'scatter',
            mode: 'lines+markers',
            name: 'Cumulative Cash Flow',
            yaxis: 'y2',
            line: { color: this.colors.primary, width: 2 }
        };

        const layout = {
            title: 'Financial Performance Over Time',
            xaxis: { title: 'Year' },
            yaxis: { title: 'Annual Cash Flow ($)', side: 'left' },
            yaxis2: {
                title: 'Cumulative Cash Flow ($)',
                overlaying: 'y',
                side: 'right'
            },
            hovermode: 'x unified',
            height: 400,
            shapes: [{
                type: 'line',
                x0: 0,
                y0: 0,
                x1: years[years.length - 1],
                y1: 0,
                line: {
                    color: 'gray',
                    width: 1,
                    dash: 'dot'
                }
            }]
        };

        Plotly.newPlot('cashFlowChart', [trace1, trace2], layout);
    }

    /**
     * Create Pareto frontier for optimization results
     */
    createParetoFrontier(optimizationResult) {
        if (!optimizationResult || !optimizationResult.pareto_front) {
            return;
        }

        const pareto = optimizationResult.pareto_front;
        
        const trace = {
            x: pareto.map(p => p.npv),
            y: pareto.map(p => p.irr * 100),
            mode: 'markers+lines',
            type: 'scatter',
            text: pareto.map(p => 
                `Reactors: ${p.reactors}<br>` +
                `DS Lines: ${p.ds_lines}<br>` +
                `Volume: ${p.fermenter_volume_l}L`
            ),
            marker: {
                size: 10,
                color: pareto.map(p => p.capex),
                colorscale: 'Viridis',
                showscale: true,
                colorbar: {
                    title: 'CAPEX ($)'
                }
            },
            line: {
                color: 'rgba(128, 128, 128, 0.3)',
                width: 1
            }
        };

        const layout = {
            title: 'Pareto Frontier - Multi-Objective Optimization',
            xaxis: { title: 'NPV ($)' },
            yaxis: { title: 'IRR (%)' },
            hovermode: 'closest',
            height: 500
        };

        Plotly.newPlot('paretoChart', [trace], layout);
    }

    /**
     * Create enhanced tornado chart for sensitivity
     */
    createTornadoChart(sensitivityData) {
        if (!sensitivityData || !sensitivityData.tornado_data) {
            return;
        }

        const params = Object.keys(sensitivityData.tornado_data);
        const baseNPV = sensitivityData.base_npv || 0;
        
        // Calculate impacts
        const impacts = params.map(p => {
            const data = sensitivityData.tornado_data[p];
            return {
                param: this.formatParameterName(p),
                downImpact: data.down_npv - baseNPV,
                upImpact: data.up_npv - baseNPV,
                range: Math.abs(data.up_npv - data.down_npv)
            };
        });

        // Sort by impact range
        impacts.sort((a, b) => b.range - a.range);

        const trace1 = {
            x: impacts.map(i => i.downImpact),
            y: impacts.map(i => i.param),
            name: '10% Decrease',
            type: 'bar',
            orientation: 'h',
            marker: { color: this.colors.danger },
            text: impacts.map(i => `$${(i.downImpact/1000).toFixed(0)}k`),
            textposition: 'auto'
        };

        const trace2 = {
            x: impacts.map(i => i.upImpact),
            y: impacts.map(i => i.param),
            name: '10% Increase',
            type: 'bar',
            orientation: 'h',
            marker: { color: this.colors.success },
            text: impacts.map(i => `$${(i.upImpact/1000).toFixed(0)}k`),
            textposition: 'auto'
        };

        const layout = {
            title: 'Sensitivity Analysis - NPV Impact',
            barmode: 'overlay',
            height: 400,
            xaxis: { 
                title: 'NPV Impact ($)',
                zeroline: true,
                zerolinewidth: 2,
                zerolinecolor: 'black'
            },
            yaxis: { title: '' },
            annotations: [{
                x: 0,
                y: -0.15,
                xref: 'x',
                yref: 'paper',
                text: `Base NPV: $${(baseNPV/1000000).toFixed(1)}M`,
                showarrow: false,
                font: { size: 12, color: 'gray' }
            }]
        };

        Plotly.newPlot('tornadoChart', [trace1, trace2], layout);
    }

    /**
     * Create equipment cost breakdown sunburst
     */
    createEquipmentSunburst(equipment) {
        if (!equipment.counts || !equipment.equipment_cost) {
            return;
        }

        const labels = ['Total'];
        const parents = [''];
        const values = [equipment.total_installed_cost];
        const colors = [this.colors.primary];

        // Add main categories
        labels.push('Equipment', 'Installation', 'Utilities');
        parents.push('Total', 'Total', 'Total');
        values.push(equipment.equipment_cost, equipment.installation_cost, equipment.utilities_cost);
        colors.push(this.colors.info, this.colors.warning, this.colors.success);

        // Add equipment subcategories if available
        if (equipment.counts) {
            Object.entries(equipment.counts).forEach(([key, count]) => {
                if (count > 0) {
                    labels.push(this.formatLabel(key));
                    parents.push('Equipment');
                    values.push(equipment.equipment_cost * 0.2); // Estimate
                    colors.push(this.colors.secondary);
                }
            });
        }

        const data = [{
            type: "sunburst",
            labels: labels,
            parents: parents,
            values: values,
            marker: { colors: colors },
            textinfo: "label+percent parent",
            hovertemplate: '<b>%{label}</b><br>Cost: $%{value:,.0f}<br>%{percentParent}<extra></extra>'
        }];

        const layout = {
            title: 'Equipment Cost Breakdown',
            height: 500
        };

        Plotly.newPlot('equipmentChart', data, layout);
    }

    /**
     * Create KPI summary radar chart
     */
    createKPIRadar(kpis) {
        // Normalize KPIs to 0-100 scale
        const metrics = {
            'NPV': this.normalizeValue(kpis.npv, 0, 20000000),
            'IRR': this.normalizeValue(kpis.irr, 0, 0.3),
            'Payback': this.normalizeValue(10 - kpis.payback_years, 0, 10),
            'Capacity': this.normalizeValue(kpis.tpa, 0, 50),
            'UP Utilization': kpis.up_utilization * 100,
            'DS Utilization': kpis.ds_utilization * 100
        };

        const data = [{
            type: 'scatterpolar',
            r: Object.values(metrics),
            theta: Object.keys(metrics),
            fill: 'toself',
            name: 'Current Scenario',
            marker: { color: this.colors.primary }
        }];

        const layout = {
            polar: {
                radialaxis: {
                    visible: true,
                    range: [0, 100]
                }
            },
            title: 'KPI Performance Radar',
            height: 400,
            showlegend: false
        };

        Plotly.newPlot('kpiRadarChart', data, layout);
    }

    // Helper methods
    getUtilizationColor(utilization) {
        if (utilization >= 0.9) return this.colors.danger;
        if (utilization >= 0.75) return this.colors.warning;
        if (utilization >= 0.5) return this.colors.success;
        return this.colors.info;
    }

    formatParameterName(param) {
        const nameMap = {
            'discount_rate': 'Discount Rate',
            'tax_rate': 'Tax Rate',
            'electricity_cost': 'Electricity Cost',
            'product_price': 'Product Price',
            'raw_material_cost': 'Raw Material Cost',
            'capex': 'CAPEX',
            'opex': 'OPEX'
        };
        return nameMap[param] || param.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    }

    formatLabel(key) {
        return key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    }

    normalizeValue(value, min, max) {
        return Math.min(100, Math.max(0, ((value - min) / (max - min)) * 100));
    }

    /**
     * Update all charts with new results
     */
    updateAllCharts(results) {
        if (results.capacity) {
            this.createCapacityWaterfall(results.capacity);
            this.createUtilizationGauges(results.capacity);
            this.createProductionChart(results.capacity);
        }

        if (results.economics) {
            this.createFinancialTimeline(results.economics);
        }

        if (results.equipment) {
            this.createEquipmentSunburst(results.equipment);
        }

        if (results.kpis) {
            this.createKPIRadar(results.kpis);
        }

        if (results.optimization) {
            this.createParetoFrontier(results.optimization);
        }

        if (results.sensitivity) {
            this.createTornadoChart(results.sensitivity);
        }
    }
}

// Export for use in main app
window.ChartManager = ChartManager;
