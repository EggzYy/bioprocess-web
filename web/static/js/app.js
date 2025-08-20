/**
 * Bioprocess Web Application - Main JavaScript
 */

// SSE Client
const sseClient = new SSEClient();
const chartManager = new ChartManager();

// API Configuration
const API_BASE_URL = '/api';

// Application State
const AppState = {
    scenario: {
        name: 'Baseline 10 TPA Facility',
        target_tpa: 10,
        strains: [],
        equipment: {
            reactors_total: 4,
            ds_lines_total: 2,
            reactor_allocation_policy: 'inverse_ct',
            ds_allocation_policy: 'inverse_ct',
            shared_downstream: true
        },
        volumes: {
            base_fermenter_vol_l: 2000,
            volume_options_l: [2000]
        },
        assumptions: {
            discount_rate: 0.10,
            tax_rate: 0.25,
            depreciation_years: 10,
            project_lifetime_years: 15
        },
        opex: {
            electricity_usd_per_kwh: 0.107,
            steam_usd_per_kg: 0.0228,
            water_usd_per_m3: 0.002
        },
        prices: {
            raw_prices: {},
            product_prices: {
                "yogurt": 400,
                "lacto_bifido": 400,
                "bacillus": 400,
                "sacco": 500
            }
        },
        optimization: {
            enabled: false,
            simulation_type: 'deterministic',
            n_monte_carlo_samples: 1000
        },
        sensitivity: {
            enabled: false,
            parameters: [],
            delta_percentage: 0.1
        },
        optimize_equipment: false
    },
    currentJobId: null,
    lastResult: null,
    strainDatabase: {},
    defaultAssumptions: {},
    rawPrices: {}  // Store raw prices separately
};

// Strain defaults from database
const STRAIN_DEFAULTS = {
    "S. thermophilus": {
        yield_g_per_L: 12.56,
        fermentation_time_h: 14.0,
        turnaround_time_h: 9.0,
        downstream_time_h: 4.0,
        media_cost_usd: 100.0,
        cryo_cost_usd: 50.0
    },
    "L. delbrueckii subsp. bulgaricus": {
        yield_g_per_L: 4.63,
        fermentation_time_h: 24.0,
        turnaround_time_h: 9.0,
        downstream_time_h: 4.0,
        media_cost_usd: 120.0,
        cryo_cost_usd: 55.0
    },
    "L. acidophilus": {
        yield_g_per_L: 82.87,
        fermentation_time_h: 18.0,
        turnaround_time_h: 9.0,
        downstream_time_h: 4.0,
        media_cost_usd: 245.47,
        cryo_cost_usd: 189.38
    }
};

// API Client
class APIClient {
    static async request(endpoint, options = {}) {
        const url = `${API_BASE_URL}${endpoint}`;
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json'
            }
        };
        
        const config = { ...defaultOptions, ...options };
        
        try {
            const response = await fetch(url, config);
            if (!response.ok) {
                throw new Error(`API Error: ${response.status} ${response.statusText}`);
            }
            return await response.json();
        } catch (error) {
            console.error('API Request failed:', error);
            showError(error.message);
            throw error;
        }
    }
    
    static async runScenario(scenario) {
        return this.request('/scenarios/run', {
            method: 'POST',
            body: JSON.stringify({
                scenario: scenario,
                async_mode: false
            })
        });
    }
    
    static async runScenarioAsync(scenario) {
        return this.request('/scenarios/run', {
            method: 'POST',
            body: JSON.stringify({
                scenario: scenario,
                async_mode: true
            })
        });
    }
    
    static async getJobStatus(jobId) {
        return this.request(`/jobs/${jobId}`);
    }
    
    static async getDefaults() {
        return this.request('/defaults');
    }
    
    static async getStrains() {
        return this.request('/strains');
    }
    
    static async exportExcel(scenarioName, result) {
        return this.request('/export/excel', {
            method: 'POST',
            body: JSON.stringify({
                scenario_name: scenarioName,
                result: result
            })
        });
    }
    
    static async runSensitivity(scenario, parameters) {
        return this.request('/sensitivity/run', {
            method: 'POST',
            body: JSON.stringify({
                scenario: scenario,
                base_configuration: {
                    reactors: scenario.equipment.reactors_total,
                    ds_lines: scenario.equipment.ds_lines_total,
                    fermenter_volume_l: scenario.volumes.base_fermenter_vol_l
                },
                parameters: parameters,
                delta_percentage: 0.1
            })
        });
    }

    static async addStrain(strain) {
        return this.request('/strains', {
            method: 'POST',
            body: JSON.stringify(strain)
        });
    }

    static async updateStrain(strainName, strain) {
        return this.request(`/strains/${strainName}`, {
            method: 'PUT',
            body: JSON.stringify(strain)
        });
    }

    static async deleteStrain(strainName) {
        return this.request(`/strains/${strainName}`, {
            method: 'DELETE'
        });
    }
}

// UI Helper Functions
function showError(message) {
    const toast = document.createElement('div');
    toast.className = 'toast align-items-center text-white bg-danger border-0 position-fixed top-0 end-0 m-3';
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    document.body.appendChild(toast);
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
    setTimeout(() => toast.remove(), 5000);
}

function showSuccess(message) {
    const toast = document.createElement('div');
    toast.className = 'toast align-items-center text-white bg-success border-0 position-fixed top-0 end-0 m-3';
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    document.body.appendChild(toast);
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
    setTimeout(() => toast.remove(), 5000);
}

function showProgress(progress, message) {
    const modal = bootstrap.Modal.getInstance(document.getElementById('progressModal')) || 
                  new bootstrap.Modal(document.getElementById('progressModal'));
    modal.show();
    
    document.getElementById('progressBar').style.width = `${progress * 100}%`;
    document.getElementById('progressMessage').textContent = message;
}

function hideProgress() {
    const modal = bootstrap.Modal.getInstance(document.getElementById('progressModal'));
    if (modal) {
        modal.hide();
    }
}

// Scenario Management
function collectScenarioData() {
    const scenario = { ...AppState.scenario };
    
    // Collect basic settings
    scenario.name = document.getElementById('scenarioName').value;
    scenario.target_tpa = parseFloat(document.getElementById('targetTPA').value);
    
    // Equipment settings
    scenario.equipment.reactors_total = parseInt(document.getElementById('reactors').value);
    scenario.equipment.ds_lines_total = parseInt(document.getElementById('dsLines').value);
    scenario.volumes.base_fermenter_vol_l = parseFloat(document.getElementById('fermenterVolume').value);
    // WVF fixed to 0.8 across app
    scenario.volumes.working_volume_fraction = 0.8;
    scenario.equipment.reactor_allocation_policy = document.getElementById('allocationPolicy').value;
    scenario.equipment.ds_allocation_policy = document.getElementById('allocationPolicy').value;
    scenario.equipment.shared_downstream = document.getElementById('sharedDownstream').checked;
    
    // Economic parameters
    scenario.assumptions.discount_rate = parseFloat(document.getElementById('discountRate').value) / 100;
    scenario.assumptions.tax_rate = parseFloat(document.getElementById('taxRate').value) / 100;
    scenario.assumptions.depreciation_years = parseInt(document.getElementById('depreciationYears').value);
    scenario.assumptions.project_lifetime_years = parseInt(document.getElementById('projectLifetime').value);
    scenario.opex.electricity_usd_per_kwh = parseFloat(document.getElementById('electricityCost').value);
    
    // Simulation type
    const simType = document.getElementById('simulationType').value;
    scenario.optimization.simulation_type = simType;
    if (simType === 'monte_carlo') {
        scenario.optimization.n_monte_carlo_samples = parseInt(document.getElementById('mcSamples').value);
    }
    
    // Optimization settings
    scenario.optimize_equipment = document.getElementById('enableOptimization').checked;
    
    return scenario;
}

async function runScenario() {
    try {
        const scenario = collectScenarioData();
        
        if (scenario.strains.length === 0) {
            showError('Please add at least one strain before running the analysis');
            return;
        }
        
        showProgress(0.05, 'Submitting scenario...'); // Show initial progress
        
        // The sseClient will handle the rest of the progress updates and the final result.
        await sseClient.runScenarioWithProgress(scenario);
        
    } catch (error) {
        console.error('Error starting scenario:', error);
        hideProgress();
        showError('Failed to start scenario: ' + error.message);
    }
}

// Results Display
function displayResults(result) {
    // Hide welcome message and show results
    document.getElementById('welcomeMessage').style.display = 'none';
    document.getElementById('kpiCards').style.display = 'flex';
    document.getElementById('resultsTabs').style.display = 'block';
    
    // Update KPI cards
    if (result.kpis) {
        document.getElementById('kpiNPV').textContent = formatCurrency(result.kpis.npv);
        document.getElementById('kpiIRR').textContent = formatPercent(result.kpis.irr);
        document.getElementById('kpiPayback').textContent = `${result.kpis.payback_years?.toFixed(1) || 'N/A'} years`;
        document.getElementById('kpiCapacity').textContent = `${result.kpis.tpa?.toFixed(1) || 0} TPA`;
    }
    
    // Use ChartManager to display all charts
    chartManager.updateAllCharts(result);
}

// Strain Management
function showStrainModal(strainToEdit = null) {
    const modalEl = document.getElementById('strainModal');
    const modal = new bootstrap.Modal(modalEl);

    // Add hidden fields if they don't exist
    if (!document.getElementById('strainModal-isEditMode')) {
        const hiddenFields = `
            <input type="hidden" id="strainModal-isEditMode">
            <input type="hidden" id="strainModal-originalName">
        `;
        modalEl.querySelector('.modal-body').insertAdjacentHTML('beforeend', hiddenFields);
    }

    const isEditModeInput = document.getElementById('strainModal-isEditMode');
    const originalNameInput = document.getElementById('strainModal-originalName');
    const title = modalEl.querySelector('.modal-title');

    if (strainToEdit) {
        title.textContent = 'Edit Strain';
        isEditModeInput.value = 'true';
        originalNameInput.value = strainToEdit.name;

        document.getElementById('strainName').value = strainToEdit.name;
        document.getElementById('strainYield').value = strainToEdit.yield_g_per_L;
        document.getElementById('strainFermTime').value = strainToEdit.fermentation_time_h;
        document.getElementById('strainTurnTime').value = strainToEdit.turnaround_time_h;
        document.getElementById('strainDSTime').value = strainToEdit.downstream_time_h;
        document.getElementById('strainMediaCost').value = strainToEdit.media_cost_usd;
        document.getElementById('strainCryoCost').value = strainToEdit.cryo_cost_usd;
    } else {
        title.textContent = 'Add Strain';
        isEditModeInput.value = 'false';
        originalNameInput.value = '';
        // Clear form fields
        modalEl.querySelectorAll('input[type="text"], input[type="number"], select').forEach(el => {
            if (el.id !== 'strainName') el.value = '';
        });
        document.getElementById('strainName').value = '';
    }

    modal.show();
}

function loadStrainDefaults() {
    const strainName = document.getElementById('strainName').value;
    const strainData = AppState.strainDatabase.find(s => s.name === strainName);
    
    if (strainData) {
        document.getElementById('strainYield').value = strainData.yield_g_per_L || '';
        document.getElementById('strainFermTime').value = strainData.fermentation_time_h || '';
        document.getElementById('strainTurnTime').value = strainData.turnaround_time_h || '';
        document.getElementById('strainDSTime').value = strainData.downstream_time_h || '';
        document.getElementById('strainMediaCost').value = strainData.media_cost_usd || '';
        document.getElementById('strainCryoCost').value = strainData.cryo_cost_usd || '';
    }
}

async function saveStrain() {
    const isEditMode = document.getElementById('strainModal-isEditMode').value === 'true';
    const originalName = document.getElementById('strainModal-originalName').value;

    const strain = {
        name: document.getElementById('strainName').value,
        yield_g_per_L: parseFloat(document.getElementById('strainYield').value),
        fermentation_time_h: parseFloat(document.getElementById('strainFermTime').value),
        turnaround_time_h: parseFloat(document.getElementById('strainTurnTime').value),
        downstream_time_h: parseFloat(document.getElementById('strainDSTime').value),
        media_cost_usd: parseFloat(document.getElementById('strainMediaCost').value),
        cryo_cost_usd: parseFloat(document.getElementById('strainCryoCost').value),
        utility_rate_ferm_kw: 300,
        utility_rate_cent_kw: 15,
        utility_rate_lyo_kw: 1.5,
        utility_cost_steam: 0.0228,
        licensing_fixed_cost_usd: 0,
        licensing_royalty_pct: 0,
        cv_ferm: 0.1,
        cv_turn: 0.1,
        cv_down: 0.1
    };

    // Client-side validation
    if (!strain.name) {
        showError('Strain name is required.');
        return;
    }
    const requiredNumericFields = [
        'yield_g_per_L', 'fermentation_time_h', 'turnaround_time_h',
        'downstream_time_h', 'media_cost_usd', 'cryo_cost_usd'
    ];
    for (const field of requiredNumericFields) {
        if (isNaN(strain[field]) || strain[field] < 0) {
            const friendlyName = field.replace(/_/g, ' ').replace('_usd', ' ($)').replace(' g per l', ' (g/L)').replace(' h', ' (h)');
            showError(`Invalid input: ${friendlyName} must be a non-negative number.`);
            return;
        }
    }

    try {
        if (isEditMode) {
            await APIClient.updateStrain(originalName, strain);
            const index = AppState.scenario.strains.findIndex(s => s.name === originalName);
            if (index > -1) {
                AppState.scenario.strains[index] = strain;
            }
            showSuccess(`Strain ${strain.name} updated successfully`);
        } else {
            await APIClient.addStrain(strain);
            AppState.scenario.strains.push(strain);
            showSuccess(`Strain ${strain.name} added successfully`);
        }

        await refreshStrains(); // Refreshes DB strains and dropdown
        updateStrainList(); // Re-renders the scenario strain list

        const modal = bootstrap.Modal.getInstance(document.getElementById('strainModal'));
        modal.hide();

    } catch (error) {
        console.error('Error saving strain:', error);
        showError(`Failed to save strain: ${error.message}`);
    }
}

function updateStrainList() {
    const listEl = document.getElementById('strainList');
    
    if (AppState.scenario.strains.length === 0) {
        listEl.innerHTML = '<div class="text-muted">No strains added yet</div>';
        return;
    }
    
    listEl.innerHTML = AppState.scenario.strains.map((strain, index) => `
        <div class="list-group-item d-flex justify-content-between align-items-center">
            <div class="strain-info">
                <div class="strain-name">${strain.name}</div>
                <div class="strain-details">
                    Yield: ${strain.yield_g_per_L} g/L | 
                    Ferm: ${strain.fermentation_time_h}h
                </div>
            </div>
            <div class="btn-group btn-group-sm">
                <button class="btn btn-outline-secondary" onclick='editStrain(${index})'>
                    <i class="bi bi-pencil"></i>
                </button>
                <button class="btn btn-outline-danger" onclick='deleteStrain("${strain.name}")'>
                    <i class="bi bi-trash"></i>
                </button>
            </div>
        </div>
    `).join('');
}

function editStrain(index) {
    const strain = AppState.scenario.strains[index];
    if (!strain) return;

    // We need to find the full strain object from the database to edit it
    const strainData = AppState.strainDatabase.find(s => s.name === strain.name);
    showStrainModal(strainData || strain);
}

async function deleteStrain(strainName) {
    if (!confirm(`Are you sure you want to delete the strain "${strainName}"? This cannot be undone.`)) {
        return;
    }

    try {
        await APIClient.deleteStrain(strainName);
        showSuccess(`Strain "${strainName}" deleted successfully.`);
        
        // Remove from scenario list if it's there
        AppState.scenario.strains = AppState.scenario.strains.filter(s => s.name !== strainName);

        await refreshStrains(); // Refreshes DB strains and dropdown
        updateStrainList(); // Re-renders the scenario strain list

    } catch (error) {
        console.error(`Error deleting strain ${strainName}:`, error);
        showError(`Failed to delete strain: ${error.message}`);
    }
}

async function refreshStrains() {
    try {
        const response = await APIClient.getStrains();
        const allStrains = response.strains.map(s => ({...s.data, name: s.name}));
        
        AppState.strainDatabase = allStrains;
        populateStrainDropdown(allStrains);

    } catch (error) {
        console.error('Error refreshing strains:', error);
        showError('Could not refresh strain list from server.');
    }
}

function removeStrain(index) {
    // This function is now more complex. We need to decide if we are removing from the scenario or deleting from DB.
    // For now, let's just remove from scenario. Deleting from DB is handled by deleteStrain.
    const removed = AppState.scenario.strains.splice(index, 1);
    updateStrainList();
    showSuccess(`Strain ${removed[0].name} removed from scenario.`);
}

// Sensitivity Analysis
async function runSensitivity() {
    // This function needs to be refactored to use the SSE client.
    showError("Sensitivity analysis is not yet implemented with the new SSE client.");
}

function displaySensitivityResults(sensitivity) {
    if (!sensitivity.tornado_data) {
        return;
    }
    
    // Create tornado chart
    const params = Object.keys(sensitivity.tornado_data);
    const downValues = params.map(p => sensitivity.tornado_data[p].down_npv);
    const upValues = params.map(p => sensitivity.tornado_data[p].up_npv);
    
    const trace1 = {
        x: downValues,
        y: params,
        name: 'Decrease',
        type: 'bar',
        orientation: 'h',
        marker: { color: 'red' }
    };
    
    const trace2 = {
        x: upValues,
        y: params,
        name: 'Increase',
        type: 'bar',
        orientation: 'h',
        marker: { color: 'green' }
    };
    
    const layout = {
        title: 'Sensitivity Analysis - Tornado Chart',
        barmode: 'relative',
        height: 400,
        xaxis: { title: 'NPV Impact ($)' },
        yaxis: { title: 'Parameter' }
    };
    
    Plotly.newPlot('tornadoChart', [trace1, trace2], layout);
}

// Export Functions
async function exportToExcel() {
    if (!AppState.lastResult) {
        showError('No results to export. Please run a scenario first.');
        return;
    }
    
    try {
        const response = await APIClient.exportExcel(
            AppState.scenario.name,
            AppState.lastResult
        );
        
        if (response.download_url) {
            // Download the file
            window.location.href = response.download_url;
            showSuccess('Excel file exported successfully');
        }
    } catch (error) {
        console.error('Error exporting to Excel:', error);
        showError('Failed to export to Excel');
    }
}

// Utility Functions
function formatCurrency(value) {
    if (value === null || value === undefined) return 'N/A';
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    }).format(value);
}

function formatPercent(value) {
    if (value === null || value === undefined) return 'N/A';
    return `${(value * 100).toFixed(1)}%`;
}

function formatNumber(value) {
    if (value === null || value === undefined) return 'N/A';
    return new Intl.NumberFormat('en-US').format(value);
}

function formatLabel(key) {
    return key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

// Event Listeners
document.addEventListener('DOMContentLoaded', async () => {
    // Initialize UI
    updateStrainList();

    // Connect SSE client
    sseClient.connect();

    // Handle SSE events
    sseClient.on('progress', (data) => {
        console.log('Progress:', data);
        const progressPercentage = (data.current_step || 0) / (data.total_steps || 10);
        showProgress(progressPercentage, data.message);
    });

    sseClient.on('result', (data) => {
        console.log('Result:', data);
        hideProgress();
        if (data.result) {
            AppState.lastResult = data.result;
            displayResults(data.result);
            showSuccess('Analysis completed successfully');
        } else {
            showError('Analysis failed: No results returned');
        }
    });

    sseClient.on('operation_error', (data) => {
        console.error('Operation Error:', data);
        hideProgress();
        showError(`Analysis failed: ${data.error}`);
    });
    
    // Load default data from API
    try {
        const defaults = await APIClient.getDefaults();
        AppState.defaultAssumptions = defaults;
        
        // Load strains database
        const strains = await APIClient.getStrains();
        AppState.strainDatabase = strains;
        
        // Populate strain dropdown
        populateStrainDropdown(strains.strains);
        
        // Apply default values to forms
        applyDefaultValues(defaults);
        
    } catch (error) {
        console.error('Error loading defaults:', error);
        showError('Failed to load default data from server');
    }
    
    // Attach event handlers
    attachEventHandlers();
    
    // Load defaults and raw prices
    try {
        const defaults = await APIClient.getDefaults();
        if (defaults.assumptions) {
            AppState.defaultAssumptions = defaults.assumptions;
        }
        // IMPORTANT: Set raw_prices from API defaults
        if (defaults.raw_prices) {
            AppState.scenario.prices.raw_prices = defaults.raw_prices;
            AppState.rawPrices = defaults.raw_prices;  // Store separately for reference
            console.log('Loaded raw prices:', Object.keys(defaults.raw_prices).length, 'materials');
        }
        // Set available strains
        if (defaults.available_strains) {
            console.log('Available strains:', defaults.available_strains);
        }
    } catch (error) {
        console.error('Failed to load defaults:', error);
    }
    
    // Setup event listeners
    document.getElementById('simulationType').addEventListener('change', (e) => {
        const mcSettings = document.getElementById('monteCarloSettings');
        mcSettings.style.display = e.target.value === 'monte_carlo' ? 'block' : 'none';
    });
    
    document.getElementById('enableOptimization').addEventListener('change', (e) => {
        const optParams = document.getElementById('optimizationParams');
        optParams.style.display = e.target.checked ? 'block' : 'none';
    });
    
    // Add default strains for testing
    AppState.scenario.strains = [
        {
            name: "S. thermophilus",
            yield_g_per_L: 12.56,
            fermentation_time_h: 14.0,
            turnaround_time_h: 9.0,
            downstream_time_h: 4.0,
            media_cost_usd: 100.0,
            cryo_cost_usd: 50.0,
            utility_rate_ferm_kw: 252,
            utility_rate_cent_kw: 15,
            utility_rate_lyo_kw: 1.5,
            utility_cost_steam: 0.0228,
            licensing_fixed_cost_usd: 0,
            licensing_royalty_pct: 0,
            cv_ferm: 0.1,
            cv_turn: 0.1,
            cv_down: 0.1
        },
        {
            name: "L. delbrueckii subsp. bulgaricus",
            yield_g_per_L: 4.63,
            fermentation_time_h: 24.0,
            turnaround_time_h: 9.0,
            downstream_time_h: 4.0,
            media_cost_usd: 120.0,
            cryo_cost_usd: 55.0,
            utility_rate_ferm_kw: 432,
            utility_rate_cent_kw: 15,
            utility_rate_lyo_kw: 1.5,
            utility_cost_steam: 0.0228,
            licensing_fixed_cost_usd: 0,
            licensing_royalty_pct: 0,
            cv_ferm: 0.1,
            cv_turn: 0.1,
            cv_down: 0.1
        }
    ];
    updateStrainList();
});

// Helper Functions for Dynamic Form Integration
function populateStrainDropdown(strains) {
    const select = document.getElementById('strainName');
    if (!select) return;
    
    // Clear existing options
    select.innerHTML = '<option value="">Select a strain...</option>';
    
    // Add strains from database
    if (strains && Array.isArray(strains)) {
        strains.forEach(strain => {
            const option = document.createElement('option');
            option.value = strain.name;
            option.textContent = strain.name;
            select.appendChild(option);
        });
    }
    
    // Also add default strains if not in database
    Object.keys(STRAIN_DEFAULTS).forEach(name => {
        if (!strains || !strains.find(s => s.name === name)) {
            const option = document.createElement('option');
            option.value = name;
            option.textContent = name;
            select.appendChild(option);
        }
    });
}

function applyDefaultValues(defaults) {
    if (!defaults) return;
    
    // Apply default assumptions
    if (defaults.assumptions) {
        const a = defaults.assumptions;
        if (a.discount_rate !== undefined) {
            document.getElementById('discountRate').value = a.discount_rate * 100;
            AppState.scenario.assumptions.discount_rate = a.discount_rate;
        }
        if (a.tax_rate !== undefined) {
            document.getElementById('taxRate').value = a.tax_rate * 100;
            AppState.scenario.assumptions.tax_rate = a.tax_rate;
        }
        if (a.depreciation_years !== undefined) {
            document.getElementById('depreciationYears').value = a.depreciation_years;
            AppState.scenario.assumptions.depreciation_years = a.depreciation_years;
        }
        if (a.project_lifetime_years !== undefined) {
            document.getElementById('projectLifetime').value = a.project_lifetime_years;
            AppState.scenario.assumptions.project_lifetime_years = a.project_lifetime_years;
        }
    }
    
    // Apply default OPEX values
    if (defaults.opex) {
        const o = defaults.opex;
        if (o.electricity_usd_per_kwh !== undefined) {
            document.getElementById('electricityCost').value = o.electricity_usd_per_kwh;
            AppState.scenario.opex.electricity_usd_per_kwh = o.electricity_usd_per_kwh;
        }
    }
    
    // Store raw prices if available
    if (defaults.raw_prices) {
        AppState.scenario.prices.raw_prices = defaults.raw_prices;
    }
    if (defaults.product_prices) {
        AppState.scenario.prices.product_prices = defaults.product_prices;
    }
}

function attachEventHandlers() {
    // Main action buttons
    const runBtn = document.getElementById('runScenarioBtn');
    if (runBtn) {
        runBtn.addEventListener('click', runScenario);
    }
    
    const exportBtn = document.getElementById('exportExcelBtn');
    if (exportBtn) {
        exportBtn.addEventListener('click', exportToExcel);
    }
    
    const sensitivityBtn = document.getElementById('runSensitivityBtn');
    if (sensitivityBtn) {
        sensitivityBtn.addEventListener('click', runSensitivity);
    }
    
    const addStrainBtn = document.getElementById('addStrainBtn');
    if (addStrainBtn) {
        addStrainBtn.addEventListener('click', showStrainModal);
    }
    
    const saveStrainBtn = document.getElementById('saveStrainBtn');
    if (saveStrainBtn) {
        saveStrainBtn.addEventListener('click', saveStrain);
    }
    
    const saveScenarioBtn = document.getElementById('saveScenarioBtn');
    if (saveScenarioBtn) {
        saveScenarioBtn.addEventListener('click', saveScenario);
    }
    
    const loadScenarioBtn = document.getElementById('loadScenarioBtn');
    if (loadScenarioBtn) {
        loadScenarioBtn.addEventListener('click', loadScenario);
    }
    
    // Form field change handlers for real-time updates
    const formFields = [
        { id: 'scenarioName', key: 'name' },
        { id: 'targetTPA', key: 'target_tpa', type: 'float' },
        { id: 'reactors', key: 'equipment.reactors_total', type: 'int' },
        { id: 'dsLines', key: 'equipment.ds_lines_total', type: 'int' },
        { id: 'fermenterVolume', key: 'volumes.base_fermenter_vol_l', type: 'float' },
        { id: 'allocationPolicy', key: 'equipment.reactor_allocation_policy' },
        { id: 'sharedDownstream', key: 'equipment.shared_downstream', type: 'bool' },
        { id: 'discountRate', key: 'assumptions.discount_rate', type: 'percent' },
        { id: 'taxRate', key: 'assumptions.tax_rate', type: 'percent' },
        { id: 'depreciationYears', key: 'assumptions.depreciation_years', type: 'int' },
        { id: 'projectLifetime', key: 'assumptions.project_lifetime_years', type: 'int' },
        { id: 'electricityCost', key: 'opex.electricity_usd_per_kwh', type: 'float' },
        { id: 'simulationType', key: 'optimization.simulation_type' },
        { id: 'mcSamples', key: 'optimization.n_monte_carlo_samples', type: 'int' },
        { id: 'enableOptimization', key: 'optimize_equipment', type: 'bool' }
    ];
    
    formFields.forEach(field => {
        const element = document.getElementById(field.id);
        if (element) {
            element.addEventListener('change', (e) => {
                updateScenarioState(field.key, e.target, field.type);
            });
        }
    });
    
    // Strain modal event handlers
    const strainNameSelect = document.getElementById('strainName');
    if (strainNameSelect) {
        strainNameSelect.addEventListener('change', loadStrainDefaults);
    }
    
    // Cancel job button in progress modal
    const cancelBtn = document.getElementById('cancelJobBtn');
    if (cancelBtn) {
        cancelBtn.addEventListener('click', cancelJob);
    }
}

function updateScenarioState(key, element, type) {
    let value = element.value;
    
    // Convert value based on type
    switch (type) {
        case 'int':
            value = parseInt(value) || 0;
            break;
        case 'float':
            value = parseFloat(value) || 0;
            break;
        case 'percent':
            value = parseFloat(value) / 100 || 0;
            break;
        case 'bool':
            value = element.checked;
            break;
    }
    
    // Navigate nested object path and set value
    const keys = key.split('.');
    let obj = AppState.scenario;
    
    for (let i = 0; i < keys.length - 1; i++) {
        if (!obj[keys[i]]) {
            obj[keys[i]] = {};
        }
        obj = obj[keys[i]];
    }
    
    obj[keys[keys.length - 1]] = value;
    
    // Special handling for certain fields
    if (key === 'optimization.simulation_type') {
        const mcSettings = document.getElementById('monteCarloSettings');
        if (mcSettings) {
            mcSettings.style.display = value === 'monte_carlo' ? 'block' : 'none';
        }
    }
    
    if (key === 'optimize_equipment') {
        const optParams = document.getElementById('optimizationParams');
        if (optParams) {
            optParams.style.display = value ? 'block' : 'none';
        }
    }
}

// Cancel Job
function cancelJob() {
    if (AppState.currentJobId) {
        // Implement job cancellation
        hideProgress();
        AppState.currentJobId = null;
    }
}

// Save/Load Scenario Functions
function saveScenario() {
    const scenario = collectScenarioData();
    const json = JSON.stringify(scenario, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${scenario.name.replace(/\s+/g, '_')}.json`;
    a.click();
    URL.revokeObjectURL(url);
    showSuccess('Scenario saved to file');
}

function loadScenario() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    input.onchange = async (e) => {
        const file = e.target.files[0];
        if (file) {
            try {
                const text = await file.text();
                const scenario = JSON.parse(text);
                AppState.scenario = scenario;
                // Update UI with loaded values
                updateUIFromScenario();
                showSuccess('Scenario loaded successfully');
            } catch (error) {
                showError('Failed to load scenario file');
            }
        }
    };
    input.click();
}

function updateUIFromScenario() {
    const s = AppState.scenario;
    document.getElementById('scenarioName').value = s.name;
    document.getElementById('targetTPA').value = s.target_tpa;
    document.getElementById('reactors').value = s.equipment.reactors_total;
    document.getElementById('dsLines').value = s.equipment.ds_lines_total;
    document.getElementById('fermenterVolume').value = s.volumes.base_fermenter_vol_l;
    // WVF fixed to 0.8 across app; no radio selection needed
    document.getElementById('allocationPolicy').value = s.equipment.reactor_allocation_policy;
    document.getElementById('sharedDownstream').checked = s.equipment.shared_downstream;
    document.getElementById('discountRate').value = s.assumptions.discount_rate * 100;
    document.getElementById('taxRate').value = s.assumptions.tax_rate * 100;
    document.getElementById('depreciationYears').value = s.assumptions.depreciation_years;
    document.getElementById('projectLifetime').value = s.assumptions.project_lifetime_years;
    document.getElementById('electricityCost').value = s.opex.electricity_usd_per_kwh;
    updateStrainList();
}
