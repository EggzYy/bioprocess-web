/**
 * Comprehensive Bioprocess Facility Designer Application
 * Main JavaScript file for the comprehensive UI
 */

// API Configuration
const API_BASE_URL = window.location.origin;
const API_ENDPOINTS = {
    runScenario: '/api/scenarios/run',
    batchRun: '/api/scenarios/batch',
    sensitivity: '/api/sensitivity/run',
    optimize: '/api/optimization/run',
    export: '/api/export/excel',
    defaults: '/api/defaults',
    rawPrices: '/api/defaults',
    strains: '/api/strains',
    jobs: '/api/jobs'
};

// Application State
class AppState {
    constructor() {
        this.currentScenario = this.getDefaultScenario();
        this.results = null;
        this.batchResults = [];
        this.sensitivityResults = null;
        this.optimizationResults = null;
        this.ws = null;
        this.rawPrices = {};
        this.availableStrains = {};
        this.activeStrains = [];
        this.isLoading = false;
    }

    getDefaultScenario() {
        return {
            name: 'New Scenario',
            description: '',
            
            // Basic Parameters
            annual_production: 1000,
            purity: 0.95,
            plant_lifetime: 15,
            construction_time: 2,
            
            // Strain Configuration
            strains: {
                selected_strain: 'ecoli',
                fermentation_titer: 100,
                fermentation_yield: 0.3,
                fermentation_time: 72,
                growth_rate: 0.25
            },
            
            // Equipment Configuration
            equipment: {
                fermenter_volume: 10000,
                fermenter_count: 3,
                working_volume_fraction: 0.8,
                separation_efficiency: 0.95,
                automation_level: 'medium'
            },
            
            // Economics Configuration
            economics: {
                discount_rate: 0.10,
                tax_rate: 0.21,
                depreciation_years: 10,
                inflation_rate: 0.02,
                working_capital_percent: 0.15
            },
            
            // Labor Configuration
            labor: {
                operators_per_shift: 2,
                shifts_per_day: 3,
                supervisor_ratio: 0.2,
                average_salary: 60000,
                benefits_percent: 0.30
            },
            
            // OPEX Configuration
            opex: {
                raw_material_cost: 500,
                utilities_per_batch: 5000,
                waste_treatment_cost: 100,
                maintenance_percent: 0.04,
                insurance_percent: 0.01
            },
            
            // CAPEX Configuration
            capex: {
                equipment_cost: 10000000,
                installation_factor: 1.5,
                building_cost_per_sqm: 2000,
                land_cost_per_sqm: 500,
                contingency_percent: 0.20
            },
            
            // Product Pricing
            pricing: {
                base_price: 5000,
                price_model: 'fixed',
                price_sensitivity: 0,
                volume_discount: 0
            },
            
            // Raw Material Prices
            raw_prices: {}
        };
    }

    updateScenario(updates) {
        this.currentScenario = {
            ...this.currentScenario,
            ...updates
        };
        this.saveToLocalStorage();
    }

    saveToLocalStorage() {
        localStorage.setItem('bioprocess_scenario', JSON.stringify(this.currentScenario));
    }

    loadFromLocalStorage() {
        const saved = localStorage.getItem('bioprocess_scenario');
        if (saved) {
            this.currentScenario = JSON.parse(saved);
            return true;
        }
        return false;
    }
}

// Initialize app state
const appState = new AppState();

// UI Helper Functions
function showLoading(message = 'Processing...') {
    appState.isLoading = true;
    const loadingEl = document.getElementById('loadingIndicator');
    if (loadingEl) {
        loadingEl.querySelector('.loading-message').textContent = message;
        loadingEl.style.display = 'flex';
    }
}

function hideLoading() {
    appState.isLoading = false;
    const loadingEl = document.getElementById('loadingIndicator');
    if (loadingEl) {
        loadingEl.style.display = 'none';
    }
}

function showAlert(message, type = 'info') {
    const alertContainer = document.getElementById('alertContainer');
    if (!alertContainer) return;

    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    alertContainer.appendChild(alertDiv);

    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

// Form Handling
function collectFormData() {
    const scenario = { ...appState.currentScenario };
    
    // Collect basic parameters
    scenario.name = document.querySelector('[name="scenario_name"]')?.value || 'Unnamed Scenario';
    scenario.target_tpa = parseFloat(document.querySelector('[name="target_tpa"]')?.value) || 10;
    
    // Collect strains from the individual strain cards
    const strainRows = document.querySelectorAll('.strain-row');
    const strains = [];
    
    strainRows.forEach(row => {
        const strainId = row.id;
        const strain = {
            // Use correct field names with suffixes as expected by API
            name: row.querySelector(`[name="strain_name_${strainId}"]`)?.value || '',
            fermentation_time_h: parseFloat(row.querySelector(`[name="ferm_time_${strainId}"]`)?.value) || 18,
            turnaround_time_h: parseFloat(row.querySelector(`[name="turn_time_${strainId}"]`)?.value) || 9,
            downstream_time_h: parseFloat(row.querySelector(`[name="down_time_${strainId}"]`)?.value) || 4,
            yield_g_per_L: parseFloat(row.querySelector(`[name="yield_${strainId}"]`)?.value) || 10,
            media_cost_usd: parseFloat(row.querySelector(`[name="media_cost_${strainId}"]`)?.value) || 100,
            cryo_cost_usd: parseFloat(row.querySelector(`[name="cryo_cost_${strainId}"]`)?.value) || 50,
            utility_rate_ferm_kw: parseFloat(row.querySelector(`[name="util_ferm_${strainId}"]`)?.value) || 300,
            utility_rate_cent_kw: parseFloat(row.querySelector(`[name="util_cent_${strainId}"]`)?.value) || 15,
            utility_rate_lyo_kw: parseFloat(row.querySelector(`[name="util_lyo_${strainId}"]`)?.value) || 1.5,
            utility_cost_steam: 0.0228,
            cv_ferm: parseFloat(row.querySelector(`[name="cv_ferm_${strainId}"]`)?.value) || 0.1,
            cv_turn: parseFloat(row.querySelector(`[name="cv_turn_${strainId}"]`)?.value) || 0.1,
            cv_down: parseFloat(row.querySelector(`[name="cv_down_${strainId}"]`)?.value) || 0.1
        };
        
        // Add optional fields if present
        const respirationType = row.querySelector(`[name="respiration_type_${strainId}"]`)?.value;
        if (respirationType) strain.respiration_type = respirationType;
        
        const requiresTff = row.querySelector(`[name="requires_tff_${strainId}"]`)?.value;
        if (requiresTff) strain.requires_tff = requiresTff === 'true';
        
        const dsComplexity = row.querySelector(`[name="downstream_complexity_${strainId}"]`)?.value;
        if (dsComplexity) strain.downstream_complexity = parseFloat(dsComplexity);
        
        strains.push(strain);
    });
    
    scenario.strains = strains;

    // Collect volumes
    scenario.volumes = {
        seed_volume_l: parseFloat(document.querySelector('[name="seed_volume"]')?.value) || 200,
        production_volume_l: parseFloat(document.querySelector('[name="production_volume"]')?.value) || 2000,
        base_fermenter_vol_l: parseFloat(document.querySelector('[name="fermenter_volume"]')?.value) || 2500,
        working_volume_fraction: parseFloat((document.querySelector('input[name="workingVolPro"]:checked')||{}).value || '0.8')
    };
    
    // Collect equipment parameters
    scenario.equipment = {
        reactors_total: parseInt(document.querySelector('[name="reactors_total"]')?.value) || 4,
        ds_lines_total: parseInt(document.querySelector('[name="ds_lines_total"]')?.value) || 2,
        upstream_availability: parseFloat(document.querySelector('[name="upstream_availability"]')?.value) || 0.92,
        downstream_availability: parseFloat(document.querySelector('[name="downstream_availability"]')?.value) || 0.90,
        quality_yield: parseFloat(document.querySelector('[name="quality_yield"]')?.value) || 0.98
    };

    // Collect economics parameters
    const economicsInputs = document.querySelectorAll('#economicsParams input');
    economicsInputs.forEach(input => {
        const name = input.name;
        if (name) {
            const value = parseFloat(input.value);
            if (!scenario.economics) scenario.economics = {};
            scenario.economics[name] = value;
        }
    });

    // Collect labor parameters
    const laborInputs = document.querySelectorAll('#laborParams input');
    laborInputs.forEach(input => {
        const name = input.name;
        if (name) {
            const value = parseFloat(input.value);
            if (!scenario.labor) scenario.labor = {};
            scenario.labor[name] = value;
        }
    });

    // Collect OPEX parameters
    const opexInputs = document.querySelectorAll('#opexParams input');
    opexInputs.forEach(input => {
        const name = input.name;
        if (name) {
            const value = parseFloat(input.value);
            if (!scenario.opex) scenario.opex = {};
            scenario.opex[name] = value;
        }
    });

    // Collect CAPEX parameters
    const capexInputs = document.querySelectorAll('#capexParams input');
    capexInputs.forEach(input => {
        const name = input.name;
        if (name) {
            const value = parseFloat(input.value);
            if (!scenario.capex) scenario.capex = {};
            scenario.capex[name] = value;
        }
    });

    // Collect pricing parameters
    const pricingInputs = document.querySelectorAll('#pricingParams input, #pricingParams select');
    pricingInputs.forEach(input => {
        const name = input.name;
        if (name) {
            const value = input.type === 'number' ? parseFloat(input.value) : input.value;
            if (!scenario.pricing) scenario.pricing = {};
            scenario.pricing[name] = value;
        }
    });

    // Collect prices
    scenario.prices = {
        product_prices: {
            default: parseFloat(document.querySelector('[name="product_price"]')?.value) || 400
        },
        raw_prices: appState.rawPrices
    };
    
    // Add default assumptions if not present
    if (!scenario.assumptions) {
        scenario.assumptions = {
            electricity_cost: 0.11,
            steam_cost: 0.0228,
            water_cost: 0.0025
        };
    }

    return scenario;
}

function populateForm(scenario) {
    // Populate basic parameters
    Object.keys(scenario).forEach(key => {
        if (typeof scenario[key] !== 'object') {
            const input = document.querySelector(`[name="${key}"]`);
            if (input) {
                input.value = scenario[key];
            }
        }
    });

    // Populate nested parameters
    ['strains', 'equipment', 'economics', 'labor', 'opex', 'capex', 'pricing'].forEach(section => {
        if (scenario[section]) {
            Object.keys(scenario[section]).forEach(key => {
                const input = document.querySelector(`[name="${key}"]`);
                if (input) {
                    input.value = scenario[section][key];
                }
            });
        }
    });
}

// Strain Management Functions
function addStrainRow() {
    const container = document.getElementById('strainsContainer');
    if (!container) return;
    
    // Clear placeholder text if present
    const placeholder = container.querySelector('.text-muted');
    if (placeholder) placeholder.remove();
    
    const strainId = `strain-${Date.now()}`;
    const strainRow = document.createElement('div');
    strainRow.className = 'strain-row card mb-3';
    strainRow.id = strainId;
    
    strainRow.innerHTML = `
        <div class="card-body">
            <div class="row">
                <div class="col-md-3">
                    <label class="form-label">Strain Name</label>
                    <input type="text" class="form-control" name="strain_name_${strainId}" placeholder="E.g., L. acidophilus">
                </div>
                <div class="col-md-2">
                    <label class="form-label">Fermentation Time (h)</label>
                    <input type="number" class="form-control" name="ferm_time_${strainId}" value="18" step="0.1">
                </div>
                <div class="col-md-2">
                    <label class="form-label">Turnaround Time (h)</label>
                    <input type="number" class="form-control" name="turn_time_${strainId}" value="9" step="0.1">
                </div>
                <div class="col-md-2">
                    <label class="form-label">Downstream Time (h)</label>
                    <input type="number" class="form-control" name="down_time_${strainId}" value="4" step="0.1">
                </div>
                <div class="col-md-2">
                    <label class="form-label">Yield (g/L)</label>
                    <input type="number" class="form-control" name="yield_${strainId}" value="82.87" step="0.01">
                </div>
                <div class="col-md-1">
                    <button class="btn btn-danger mt-4" onclick="removeStrain('${strainId}')">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            </div>
            <div class="row mt-2">
                <div class="col-md-3">
                    <label class="form-label">Media Cost ($/batch)</label>
                    <input type="number" class="form-control" name="media_cost_${strainId}" value="245" step="0.01">
                </div>
                <div class="col-md-3">
                    <label class="form-label">Cryo Cost ($/batch)</label>
                    <input type="number" class="form-control" name="cryo_cost_${strainId}" value="189" step="0.01">
                </div>
                <div class="col-md-2">
                    <label class="form-label">Utility Ferm (kWh)</label>
                    <input type="number" class="form-control" name="util_ferm_${strainId}" value="324" step="1">
                </div>
                <div class="col-md-2">
                    <label class="form-label">Utility Cent (kW/m³)</label>
                    <input type="number" class="form-control" name="util_cent_${strainId}" value="15" step="0.1">
                </div>
                <div class="col-md-2">
                    <label class="form-label">Utility Lyo (kW/L)</label>
                    <input type="number" class="form-control" name="util_lyo_${strainId}" value="1.5" step="0.1">
                </div>
            </div>
            <div class="row mt-2">
                <div class="col-md-3">
                    <label class="form-label">Respiration Type</label>
                    <select class="form-control" name="respiration_type_${strainId}">
                        <option value="aerobic">Aerobic</option>
                        <option value="anaerobic">Anaerobic</option>
                        <option value="facultative">Facultative</option>
                    </select>
                </div>
                <div class="col-md-3">
                    <label class="form-label">Requires TFF</label>
                    <select class="form-control" name="requires_tff_${strainId}">
                        <option value="false">No</option>
                        <option value="true">Yes</option>
                    </select>
                </div>
                <div class="col-md-3">
                    <label class="form-label">Downstream Complexity</label>
                    <input type="number" class="form-control" name="downstream_complexity_${strainId}" value="1.0" step="0.1" min="0.5" max="3.0" title="1.0 = standard, >1.0 = more complex">
                </div>
                <div class="col-md-3">
                    <label class="form-label">CV Values</label>
                    <div class="input-group input-group-sm">
                        <input type="number" class="form-control" name="cv_ferm_${strainId}" value="0.1" step="0.01" title="CV Fermentation" placeholder="CV-F">
                        <input type="number" class="form-control" name="cv_turn_${strainId}" value="0.1" step="0.01" title="CV Turnaround" placeholder="CV-T">
                        <input type="number" class="form-control" name="cv_down_${strainId}" value="0.1" step="0.01" title="CV Downstream" placeholder="CV-D">
                    </div>
                </div>
            </div>
        </div>
    `;
    
    container.appendChild(strainRow);
    appState.activeStrains.push(strainId);
    showAlert('Custom strain added. Configure the parameters above.', 'info');
}

function addSelectedStrain() {
    const selector = document.getElementById('strainSelector');
    if (!selector || !selector.value) {
        showAlert('Please select a strain from the dropdown first.', 'warning');
        return;
    }
    
    const container = document.getElementById('strainsContainer');
    if (!container) return;
    
    // Clear placeholder text if present
    const placeholder = container.querySelector('.text-muted');
    if (placeholder) placeholder.remove();
    
    // Find the selected strain data
    const selectedOption = selector.options[selector.selectedIndex];
    const strainName = selector.value;
    let strainData = {};
    
    try {
        if (selectedOption.dataset.strainData) {
            strainData = JSON.parse(selectedOption.dataset.strainData);
        }
    } catch (e) {
        console.error('Error parsing strain data:', e);
    }
    
    const strainId = `strain-${Date.now()}`;
    const strainRow = document.createElement('div');
    strainRow.className = 'strain-row card mb-3';
    strainRow.id = strainId;
    
    // Use data from the strain database with proper field names
    const fermTime = strainData.t_fedbatch_h || 18;
    const turnaroundTime = strainData.t_turnaround_h || 9;
    const downstreamTime = strainData.t_downstrm_h || 4;
    const yieldValue = strainData.yield_g_per_L || 82.87;
    const mediaCost = strainData.media_cost_usd || 245;
    const cryoCost = strainData.cryo_cost_usd || 189;
    const utilFerm = strainData.utility_rate_ferm_kw || 324;
    const utilCent = strainData.utility_rate_cent_kw || 15;
    const utilLyo = strainData.utility_rate_lyo_kw || 1.5;
    const cvFerm = strainData.cv_ferm || 0.1;
    const cvTurn = strainData.cv_turn || 0.1;
    const cvDown = strainData.cv_down || 0.1;
    const respirationType = strainData.respiration_type || "aerobic";
    const requiresTff = strainData.requires_tff || false;
    const downstreamComplexity = strainData.downstream_complexity || 1.0;
    
    strainRow.innerHTML = `
        <div class="card-body">
            <div class="card-header bg-success text-white">
                <strong>${strainName}</strong> (From Database)
            </div>
            <div class="row mt-2">
                <div class="col-md-3">
                    <label class="form-label">Strain Name</label>
                    <input type="text" class="form-control" name="strain_name_${strainId}" value="${strainName}" readonly>
                </div>
                <div class="col-md-2">
                    <label class="form-label">Fermentation Time (h)</label>
                    <input type="number" class="form-control" name="ferm_time_${strainId}" value="${fermTime}" step="0.1">
                </div>
                <div class="col-md-2">
                    <label class="form-label">Turnaround Time (h)</label>
                    <input type="number" class="form-control" name="turn_time_${strainId}" value="${turnaroundTime}" step="0.1">
                </div>
                <div class="col-md-2">
                    <label class="form-label">Downstream Time (h)</label>
                    <input type="number" class="form-control" name="down_time_${strainId}" value="${downstreamTime}" step="0.1">
                </div>
                <div class="col-md-2">
                    <label class="form-label">Yield (g/L)</label>
                    <input type="number" class="form-control" name="yield_${strainId}" value="${yieldValue}" step="0.01">
                </div>
                <div class="col-md-1">
                    <button class="btn btn-danger mt-4" onclick="removeStrain('${strainId}')">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            </div>
            <div class="row mt-2">
                <div class="col-md-3">
                    <label class="form-label">Media Cost ($/batch)</label>
                    <input type="number" class="form-control" name="media_cost_${strainId}" value="${mediaCost}" step="0.01">
                </div>
                <div class="col-md-3">
                    <label class="form-label">Cryo Cost ($/batch)</label>
                    <input type="number" class="form-control" name="cryo_cost_${strainId}" value="${cryoCost}" step="0.01">
                </div>
                <div class="col-md-2">
                    <label class="form-label">Utility Ferm (kWh)</label>
                    <input type="number" class="form-control" name="util_ferm_${strainId}" value="${utilFerm}" step="1">
                </div>
                <div class="col-md-2">
                    <label class="form-label">Utility Cent (kW/m³)</label>
                    <input type="number" class="form-control" name="util_cent_${strainId}" value="${utilCent}" step="0.1">
                </div>
                <div class="col-md-2">
                    <label class="form-label">Utility Lyo (kW/L)</label>
                    <input type="number" class="form-control" name="util_lyo_${strainId}" value="${utilLyo}" step="0.1">
                </div>
            </div>
            <div class="row mt-2">
                <div class="col-md-3">
                    <label class="form-label">Respiration Type</label>
                    <select class="form-control" name="respiration_type_${strainId}">
                        <option value="aerobic" ${respirationType === 'aerobic' ? 'selected' : ''}>Aerobic</option>
                        <option value="anaerobic" ${respirationType === 'anaerobic' ? 'selected' : ''}>Anaerobic</option>
                        <option value="facultative" ${respirationType === 'facultative' ? 'selected' : ''}>Facultative</option>
                    </select>
                </div>
                <div class="col-md-2">
                    <label class="form-label">Requires TFF</label>
                    <select class="form-control" name="requires_tff_${strainId}">
                        <option value="false" ${!requiresTff ? 'selected' : ''}>No</option>
                        <option value="true" ${requiresTff ? 'selected' : ''}>Yes</option>
                    </select>
                </div>
                <div class="col-md-2">
                    <label class="form-label">DS Complexity</label>
                    <input type="number" class="form-control" name="downstream_complexity_${strainId}" value="${downstreamComplexity}" step="0.1" min="0.5" max="3.0" title="1.0 = standard, >1.0 = more complex">
                </div>
                <div class="col-md-2">
                    <label class="form-label">CV Ferm</label>
                    <input type="number" class="form-control" name="cv_ferm_${strainId}" value="${cvFerm}" step="0.01" title="Coefficient of Variation for fermentation time">
                </div>
                <div class="col-md-2">
                    <label class="form-label">CV Turn</label>
                    <input type="number" class="form-control" name="cv_turn_${strainId}" value="${cvTurn}" step="0.01" title="Coefficient of Variation for turnaround time">
                </div>
                <div class="col-md-1">
                    <label class="form-label">CV Down</label>
                    <input type="number" class="form-control" name="cv_down_${strainId}" value="${cvDown}" step="0.01" title="Coefficient of Variation for downstream time">
                </div>
            </div>
        </div>
    `;
    
    container.appendChild(strainRow);
    appState.activeStrains.push({id: strainId, name: strainName, data: strainData});
    
    // Reset selector
    selector.value = '';
    
    showAlert(`${strainName} added from database with pre-configured values.`, 'success');
}

function removeStrain(strainId) {
    const element = document.getElementById(strainId);
    if (element) {
        element.remove();
        appState.activeStrains = appState.activeStrains.filter(id => id !== strainId);
        showAlert('Strain removed.', 'info');
    }
}

async function loadAvailableStrains() {
    try {
        const response = await fetch('/api/strains');
        if (response.ok) {
            const data = await response.json();
            appState.availableStrains = data.strains || [];
            populateStrainSelector();
            return data.strains;
        }
    } catch (error) {
        console.error('Error loading strains:', error);
    }
    return [];
}

function populateStrainSelector() {
    const selector = document.getElementById('strainSelector');
    if (!selector) return;
    
    selector.innerHTML = '<option value="">-- Select a strain --</option>';
    
    // Group strains by category if available
    const strainsByCategory = {};
    appState.availableStrains.forEach(strain => {
        const category = strain.category || 'Other';
        if (!strainsByCategory[category]) {
            strainsByCategory[category] = [];
        }
        strainsByCategory[category].push(strain);
    });
    
    // Add strains to selector
    Object.keys(strainsByCategory).forEach(category => {
        const optGroup = document.createElement('optgroup');
        optGroup.label = category;
        
        strainsByCategory[category].forEach(strain => {
            const option = document.createElement('option');
            option.value = strain.name;
            option.textContent = strain.name;
            option.dataset.strainData = JSON.stringify(strain.data);
            optGroup.appendChild(option);
        });
        
        selector.appendChild(optGroup);
    });
}

// Raw Material Price Management
function populateRawPrices() {
    const container = document.getElementById('rawPricesContainer');
    if (!container) return;
    
    container.innerHTML = '';
    
    // Create input fields for each raw material price
    Object.keys(appState.rawPrices).forEach(material => {
        const col = document.createElement('div');
        col.className = 'col-md-3 mb-2';
        col.innerHTML = `
            <label class="form-label">${material.replace(/_/g, ' ')}</label>
            <div class="input-group">
                <span class="input-group-text">$</span>
                <input type="number" 
                       class="form-control raw-price-input" 
                       data-material="${material}"
                       value="${appState.rawPrices[material]}" 
                       step="0.01"
                       min="0">
                <span class="input-group-text">/kg</span>
            </div>
        `;
        container.appendChild(col);
    });
    
    // Add event listeners to update prices
    container.querySelectorAll('.raw-price-input').forEach(input => {
        input.addEventListener('change', (e) => {
            const material = e.target.dataset.material;
            const value = parseFloat(e.target.value) || 0;
            appState.rawPrices[material] = value;
            showAlert(`Updated ${material} price to $${value}/kg`, 'success');
        });
    });
}

// API Functions
async function loadDefaults() {
    try {
        const response = await fetch(API_ENDPOINTS.defaults);
        if (response.ok) {
            const defaults = await response.json();
            // Store available strains from defaults
            if (defaults.available_strains) {
                // Convert to the expected format
                appState.availableStrains = Object.entries(defaults.available_strains).map(([name, data]) => ({
                    name: name,
                    data: data,
                    category: data.category || 'Probiotics'
                }));
                populateStrainSelector();
            }
            // Store raw prices
            if (defaults.raw_prices) {
                appState.rawPrices = defaults.raw_prices;
                populateRawPrices();
            }
            return defaults;
        }
    } catch (error) {
        console.error('Error loading defaults:', error);
    }
    return null;
}

async function loadRawPrices() {
    try {
        const response = await fetch(API_ENDPOINTS.rawPrices);
        if (response.ok) {
            const prices = await response.json();
            appState.rawPrices = prices;
            return prices;
        }
    } catch (error) {
        console.error('Error loading raw prices:', error);
    }
    return {};
}

async function runScenario() {
    const scenario = collectFormData();
    showLoading('Running scenario simulation...');

    try {
        // Wrap scenario in the expected API format
        const requestBody = {
            scenario: scenario,
            async_mode: false
        };
        
        const response = await fetch(API_ENDPOINTS.runScenario, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestBody)
        });

        if (response.ok) {
            const results = await response.json();
            appState.results = results;
            displayResults(results);
            showAlert('Scenario completed successfully!', 'success');
        } else {
            const error = await response.json();
            showAlert(`Error: ${error.detail || 'Failed to run scenario'}`, 'danger');
        }
    } catch (error) {
        console.error('Error running scenario:', error);
        showAlert('Failed to run scenario. Please check your connection.', 'danger');
    } finally {
        hideLoading();
    }
}

async function runOptimization() {
    const scenario = collectFormData();
    const optimizationParams = collectOptimizationParams();
    
    showLoading('Running optimization...');

    try {
        // Use 'scenario' field name to match API expectation
        const response = await fetch(API_ENDPOINTS.optimize, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                scenario: scenario,  // Changed from base_scenario
                max_reactors: 20,
                max_ds_lines: 10,
                objectives: optimizationParams.objectives || ['irr', 'capex']
            })
        });

        if (response.ok) {
            const results = await response.json();
            appState.optimizationResults = results;
            displayOptimizationResults(results);
            showAlert('Optimization completed successfully!', 'success');
        } else {
            const error = await response.json();
            showAlert(`Error: ${error.detail || 'Failed to run optimization'}`, 'danger');
        }
    } catch (error) {
        console.error('Error running optimization:', error);
        showAlert('Failed to run optimization. Please check your connection.', 'danger');
    } finally {
        hideLoading();
    }
}

async function runSensitivityAnalysis() {
    const scenario = collectFormData();
    const sensitivityParams = collectSensitivityParams();
    
    showLoading('Running sensitivity analysis...');

    try {
        const response = await fetch(API_ENDPOINTS.sensitivity, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                base_scenario: scenario,
                parameters: sensitivityParams
            })
        });

        if (response.ok) {
            const results = await response.json();
            appState.sensitivityResults = results;
            displaySensitivityResults(results);
            showAlert('Sensitivity analysis completed successfully!', 'success');
        } else {
            const error = await response.json();
            showAlert(`Error: ${error.detail || 'Failed to run sensitivity analysis'}`, 'danger');
        }
    } catch (error) {
        console.error('Error running sensitivity analysis:', error);
        showAlert('Failed to run sensitivity analysis. Please check your connection.', 'danger');
    } finally {
        hideLoading();
    }
}

function collectOptimizationParams() {
    // Collect optimization parameters from the UI
    return {
        objective: document.querySelector('[name="optimization_objective"]')?.value || 'npv',
        constraints: [],
        variables: []
    };
}

function collectSensitivityParams() {
    // Collect sensitivity analysis parameters from the UI
    const params = [];
    const checkboxes = document.querySelectorAll('#sensitivityParams input[type="checkbox"]:checked');
    checkboxes.forEach(checkbox => {
        params.push({
            name: checkbox.value,
            range: [-20, 20],  // ±20% variation
            steps: 5
        });
    });
    return params;
}

// Results Display Functions
function displayResults(results) {
    // Display KPIs
    displayKPIs(results.kpis);
    
    // Display capacity results
    displayCapacityResults(results.capacity);
    
    // Display economics results
    displayEconomicsResults(results.economics);
    
    // Create charts
    createResultCharts(results);
    
    // Switch to results tab
    const resultsTab = document.querySelector('[data-bs-target="#results"]');
    if (resultsTab) {
        resultsTab.click();
    }
}

function displayKPIs(kpis) {
    const kpiContainer = document.getElementById('kpiResults');
    if (!kpiContainer || !kpis) return;

    kpiContainer.innerHTML = `
        <div class="row">
            <div class="col-md-3">
                <div class="kpi-card">
                    <h6>NPV</h6>
                    <h3>$${formatNumber(kpis.npv || 0)}</h3>
                </div>
            </div>
            <div class="col-md-3">
                <div class="kpi-card">
                    <h6>IRR</h6>
                    <h3>${formatPercent(kpis.irr || 0)}</h3>
                </div>
            </div>
            <div class="col-md-3">
                <div class="kpi-card">
                    <h6>Payback Period</h6>
                    <h3>${formatNumber(kpis.payback_period || 0, 1)} years</h3>
                </div>
            </div>
            <div class="col-md-3">
                <div class="kpi-card">
                    <h6>ROI</h6>
                    <h3>${formatPercent(kpis.roi || 0)}</h3>
                </div>
            </div>
        </div>
    `;
}

function displayCapacityResults(capacity) {
    const container = document.getElementById('capacityResults');
    if (!container || !capacity) return;

    container.innerHTML = `
        <table class="table table-striped">
            <tbody>
                <tr>
                    <td>Annual Production</td>
                    <td>${formatNumber(capacity.annual_production || 0)} kg</td>
                </tr>
                <tr>
                    <td>Batches per Year</td>
                    <td>${formatNumber(capacity.batches_per_year || 0, 0)}</td>
                </tr>
                <tr>
                    <td>Batch Size</td>
                    <td>${formatNumber(capacity.batch_size || 0)} L</td>
                </tr>
                <tr>
                    <td>Utilization</td>
                    <td>${formatPercent(capacity.utilization || 0)}</td>
                </tr>
            </tbody>
        </table>
    `;
}

function displayEconomicsResults(economics) {
    const container = document.getElementById('economicsResults');
    if (!container || !economics) return;

    container.innerHTML = `
        <table class="table table-striped">
            <tbody>
                <tr>
                    <td>Total CAPEX</td>
                    <td>$${formatNumber(economics.total_capex || 0)}</td>
                </tr>
                <tr>
                    <td>Annual OPEX</td>
                    <td>$${formatNumber(economics.annual_opex || 0)}</td>
                </tr>
                <tr>
                    <td>Annual Revenue</td>
                    <td>$${formatNumber(economics.annual_revenue || 0)}</td>
                </tr>
                <tr>
                    <td>Gross Margin</td>
                    <td>${formatPercent(economics.gross_margin || 0)}</td>
                </tr>
            </tbody>
        </table>
    `;
}

function displayOptimizationResults(results) {
    // Display optimization results
    console.log('Optimization results:', results);
}

function displaySensitivityResults(results) {
    // Display sensitivity analysis results
    console.log('Sensitivity results:', results);
}

// Chart Functions
function createResultCharts(results) {
    createCashFlowChart(results.cashflow);
    createCostBreakdownChart(results.economics);
}

function createCashFlowChart(cashflow) {
    const container = document.getElementById('cashflowChart');
    if (!container || !cashflow) return;

    const trace = {
        x: cashflow.years || [],
        y: cashflow.values || [],
        type: 'scatter',
        mode: 'lines+markers',
        name: 'Cash Flow',
        line: { color: '#007bff' }
    };

    const layout = {
        title: 'Cash Flow Projection',
        xaxis: { title: 'Year' },
        yaxis: { title: 'Cash Flow ($)' },
        hovermode: 'x unified'
    };

    Plotly.newPlot(container, [trace], layout);
}

function createCostBreakdownChart(economics) {
    const container = document.getElementById('costBreakdownChart');
    if (!container || !economics) return;

    const data = [{
        values: [
            economics.raw_material_cost || 0,
            economics.utilities_cost || 0,
            economics.labor_cost || 0,
            economics.maintenance_cost || 0,
            economics.other_costs || 0
        ],
        labels: ['Raw Materials', 'Utilities', 'Labor', 'Maintenance', 'Other'],
        type: 'pie',
        hole: 0.4
    }];

    const layout = {
        title: 'Operating Cost Breakdown'
    };

    Plotly.newPlot(container, data, layout);
}

// Utility Functions
function formatNumber(value, decimals = 0) {
    return new Intl.NumberFormat('en-US', {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
    }).format(value);
}

function formatPercent(value) {
    return `${(value * 100).toFixed(1)}%`;
}

// WebSocket Functions
function initWebSocket() {
    const wsUrl = `ws://${window.location.host}/ws`;
    appState.ws = new WebSocket(wsUrl);

    appState.ws.onopen = () => {
        console.log('WebSocket connected');
        appState.ws.send(JSON.stringify({
            type: 'connection',
            client_id: 'web-app-' + Date.now()
        }));
    };

    appState.ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
    };

    appState.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
    };

    appState.ws.onclose = () => {
        console.log('WebSocket disconnected');
        // Attempt to reconnect after 5 seconds
        setTimeout(initWebSocket, 5000);
    };
}

function handleWebSocketMessage(data) {
    switch (data.type) {
        case 'progress':
            updateProgress(data.progress, data.message);
            break;
        case 'result':
            handleResult(data.result);
            break;
        case 'error':
            showAlert(data.message, 'danger');
            hideLoading();
            break;
        default:
            console.log('WebSocket message:', data);
    }
}

function updateProgress(progress, message) {
    const progressBar = document.querySelector('.progress-bar');
    if (progressBar) {
        progressBar.style.width = `${progress * 100}%`;
        progressBar.textContent = message || `${Math.round(progress * 100)}%`;
    }
}

function handleResult(result) {
    appState.results = result;
    displayResults(result);
    hideLoading();
}

// Scenario Management Functions
function saveScenario() {
    const scenario = collectFormData();
    const dataStr = JSON.stringify(scenario, null, 2);
    const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
    
    const link = document.createElement('a');
    link.setAttribute('href', dataUri);
    link.setAttribute('download', `scenario_${scenario.name || 'unnamed'}_${Date.now()}.json`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    showAlert('Scenario saved to file', 'success');
}

function loadScenario() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    
    input.onchange = (e) => {
        const file = e.target.files[0];
        if (!file) return;
        
        const reader = new FileReader();
        reader.onload = (event) => {
            try {
                const scenario = JSON.parse(event.target.result);
                appState.currentScenario = scenario;
                populateForm(scenario);
                showAlert('Scenario loaded successfully', 'success');
            } catch (error) {
                showAlert('Failed to load scenario file', 'danger');
                console.error('Error loading scenario:', error);
            }
        };
        reader.readAsText(file);
    };
    
    input.click();
}

function loadPreset(presetName) {
    // Load a preset scenario configuration
    const presets = {
        'facility_1_yogurt': {
            name: 'Yogurt Cultures Facility',
            target_tpa: 10,
            strains: ['S. thermophilus', 'L. delbrueckii subsp. bulgaricus']
        },
        'facility_2_lacto': {
            name: 'Lacto/Bifido Facility',
            target_tpa: 20,
            strains: ['L. acidophilus', 'B. animalis subsp. lactis', 'L. rhamnosus GG']
        },
        'facility_3_bacillus': {
            name: 'Bacillus Spores Facility',
            target_tpa: 15,
            strains: ['Bacillus coagulans', 'Bacillus subtilis']
        },
        'facility_4_yeast': {
            name: 'Yeast Probiotic Facility',
            target_tpa: 10,
            strains: ['Saccharomyces boulardii']
        },
        'facility_5_all': {
            name: 'Multi-Product Facility',
            target_tpa: 40,
            strains: ['L. acidophilus', 'B. animalis subsp. lactis', 'L. rhamnosus GG', 'Bacillus coagulans']
        }
    };
    
    const preset = presets[presetName];
    if (preset) {
        // Update basic fields
        document.getElementById('scenarioName').value = preset.name;
        document.getElementById('targetTPA').value = preset.target_tpa;
        
        // Clear existing strains and add preset strains
        const container = document.getElementById('strainsContainer');
        if (container) {
            container.innerHTML = '<p class="text-muted">No strains added yet. Use the controls above to add strains.</p>';
            appState.activeStrains = [];
        }
        
        showAlert(`Loaded preset: ${preset.name}`, 'info');
        showAlert('Add the specified strains from the strain selector to complete the setup', 'info');
    }
}

function cancelJob() {
    // Cancel the current running job
    if (appState.currentJobId) {
        fetch(`${API_ENDPOINTS.jobs}/${appState.currentJobId}`, {
            method: 'DELETE'
        })
        .then(response => {
            if (response.ok) {
                showAlert('Job cancelled', 'warning');
                hideLoading();
                appState.currentJobId = null;
            }
        })
        .catch(error => {
            console.error('Error cancelling job:', error);
        });
    }
}

// Export Functions
async function exportToExcel() {
    if (!appState.results) {
        // Try to run the scenario first
        showAlert('Running scenario before export...', 'info');
        await runScenario();
        // Wait a bit for results
        setTimeout(() => exportToExcel(), 2000);
        return;
    }

    try {
        const response = await fetch(API_ENDPOINTS.export, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                scenario_name: appState.currentScenario.name || 'Bioprocess Scenario',
                result: appState.results,
                scenario_input: appState.currentScenario
            })
        });

        if (response.ok) {
            const result = await response.json();
            // Download the file
            if (result.download_url) {
                window.open(result.download_url, '_blank');
                showAlert('Excel file generated successfully!', 'success');
            }
        } else {
            showAlert('Failed to export to Excel', 'danger');
        }
    } catch (error) {
        console.error('Error exporting to Excel:', error);
        showAlert('Failed to export to Excel', 'danger');
    }
}

async function exportResults(format = 'json') {
    if (!appState.results) {
        showAlert('No results to export. Please run a scenario first.', 'warning');
        return;
    }

    try {
        const response = await fetch(`${API_ENDPOINTS.export}?format=${format}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                scenario: appState.currentScenario,
                results: appState.results
            })
        });

        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `bioprocess-results-${Date.now()}.${format}`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            showAlert('Results exported successfully!', 'success');
        } else {
            showAlert('Failed to export results', 'danger');
        }
    } catch (error) {
        console.error('Error exporting results:', error);
        showAlert('Failed to export results', 'danger');
    }
}

// Make functions available globally for HTML onclick handlers
// Do this BEFORE DOMContentLoaded to ensure they're available immediately
window.addStrainRow = addStrainRow;
window.addSelectedStrain = addSelectedStrain;
window.removeStrain = removeStrain;
window.runScenario = runScenario;
window.runOptimization = runOptimization;
window.runSensitivityAnalysis = runSensitivityAnalysis;
window.exportToExcel = exportToExcel;
window.saveScenario = saveScenario;
window.loadScenario = loadScenario;
window.loadPreset = loadPreset;
window.cancelJob = cancelJob;

// Event Listeners
document.addEventListener('DOMContentLoaded', async () => {
    try {
        // Initialize WebSocket
        initWebSocket();

        // Load defaults and raw prices
        const [defaults, rawPrices] = await Promise.all([
            loadDefaults(),
            loadRawPrices()
        ]);

        // Load saved scenario or use defaults
        if (!appState.loadFromLocalStorage()) {
            if (defaults) {
                appState.currentScenario = { ...appState.currentScenario, ...defaults };
            }
        }

        // Populate form with current scenario
        populateForm(appState.currentScenario);

        // Setup event listeners
        const runButton = document.getElementById('runScenario');
        if (runButton) {
            runButton.addEventListener('click', runScenario);
        }

        const optimizeButton = document.getElementById('runOptimization');
        if (optimizeButton) {
            optimizeButton.addEventListener('click', runOptimization);
        }

        const sensitivityButton = document.getElementById('runSensitivity');
        if (sensitivityButton) {
            sensitivityButton.addEventListener('click', runSensitivityAnalysis);
        }

        const exportButton = document.getElementById('exportResults');
        if (exportButton) {
            exportButton.addEventListener('click', () => exportResults('xlsx'));
        }

        // Auto-save on input change
        document.querySelectorAll('input, select').forEach(element => {
            element.addEventListener('change', () => {
                appState.updateScenario(collectFormData());
            });
        });

        // Setup tooltips if Bootstrap is available
        if (typeof bootstrap !== 'undefined') {
            const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
            tooltipTriggerList.map(function (tooltipTriggerEl) {
                return new bootstrap.Tooltip(tooltipTriggerEl);
            });
        }

        console.log('Comprehensive Bioprocess Designer initialized');
    } catch (error) {
        console.error('Error during initialization:', error);
    }
});
