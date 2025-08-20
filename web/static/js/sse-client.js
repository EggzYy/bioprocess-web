/**
 * SSE (Server-Sent Events) Client for real-time progress updates
 */

class SSEClient {
    constructor(baseUrl = '/api') {
        this.baseUrl = baseUrl;
        this.clientId = this.generateClientId();
        this.eventSource = null;
        this.listeners = new Map();
        this.progressCallbacks = new Map();
        this.connected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
    }

    /**
     * Generate unique client ID
     */
    generateClientId() {
        return `client_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    /**
     * Connect to SSE stream
     */
    connect() {
        if (this.eventSource) {
            this.disconnect();
        }

        const url = `${this.baseUrl}/sse/stream/${this.clientId}`;
        console.log(`Connecting to SSE: ${url}`);

        try {
            this.eventSource = new EventSource(url);
            this.setupEventHandlers();
        } catch (error) {
            console.error('Failed to create EventSource:', error);
            this.handleConnectionError();
        }
    }

    /**
     * Setup event handlers for SSE
     */
    setupEventHandlers() {
        // Connection opened
        this.eventSource.onopen = () => {
            console.log('SSE connection established');
            this.connected = true;
            this.reconnectAttempts = 0;
            this.emit('connected', { clientId: this.clientId });
        };

        // Handle errors
        this.eventSource.onerror = (error) => {
            console.error('SSE connection error:', error);
            this.connected = false;
            this.emit('error', error);
            this.handleConnectionError();
        };

        // Handle progress events
        this.eventSource.addEventListener('progress', (event) => {
            const data = JSON.parse(event.data);
            this.handleProgressUpdate(data);
        });

        // Handle result events
        this.eventSource.addEventListener('result', (event) => {
            const data = JSON.parse(event.data);
            this.handleResult(data);
        });

        // Handle error events
        this.eventSource.addEventListener('error', (event) => {
            const data = JSON.parse(event.data);
            this.handleError(data);
        });

        // Handle status events
        this.eventSource.addEventListener('status', (event) => {
            const data = JSON.parse(event.data);
            this.handleStatus(data);
        });

        // Handle log events
        this.eventSource.addEventListener('log', (event) => {
            const data = JSON.parse(event.data);
            this.handleLog(data);
        });

        // Handle heartbeat
        this.eventSource.addEventListener('heartbeat', (event) => {
            // Keep connection alive
            this.emit('heartbeat', JSON.parse(event.data));
        });
    }

    /**
     * Handle connection errors with reconnection logic
     */
    handleConnectionError() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
            
            console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
            
            setTimeout(() => {
                this.connect();
            }, delay);
        } else {
            console.error('Max reconnection attempts reached');
            this.emit('connection_failed', {
                attempts: this.reconnectAttempts,
                maxAttempts: this.maxReconnectAttempts
            });
        }
    }

    /**
     * Disconnect from SSE stream
     */
    disconnect() {
        if (this.eventSource) {
            this.eventSource.close();
            this.eventSource = null;
            this.connected = false;
            console.log('SSE connection closed');
            
            // Notify server
            fetch(`${this.baseUrl}/sse/disconnect/${this.clientId}`, {
                method: 'DELETE'
            }).catch(err => console.error('Failed to notify disconnect:', err));
        }
    }

    /**
     * Handle progress update
     */
    handleProgressUpdate(data) {
        const { operation_id, progress, message, details } = data;
        
        // Update progress UI
        // this.updateProgressBar(operation_id, progress, message);
        
        // Call registered callback
        const callback = this.progressCallbacks.get(operation_id);
        if (callback) {
            callback(data);
        }
        
        this.emit('progress', data);
    }

    /**
     * Handle result
     */
    handleResult(data) {
        const { operation_id, result } = data;
        
        // Complete progress
        this.updateProgressBar(operation_id, 100, 'Completed');
        
        // Call registered callback
        const callback = this.progressCallbacks.get(operation_id);
        if (callback) {
            callback({ type: 'result', result });
            this.progressCallbacks.delete(operation_id);
        }
        
        this.emit('result', data);
    }

    /**
     * Handle error
     */
    handleError(data) {
        const { operation_id, error } = data;
        
        // Update UI with error
        this.showError(operation_id, error);
        
        // Call registered callback
        const callback = this.progressCallbacks.get(operation_id);
        if (callback) {
            callback({ type: 'error', error });
            this.progressCallbacks.delete(operation_id);
        }
        
        this.emit('operation_error', data);
    }

    /**
     * Handle status update
     */
    handleStatus(data) {
        this.emit('status', data);
    }

    /**
     * Handle log message
     */
    handleLog(data) {
        const { level, message, details } = data;
        console.log(`[${level}] ${message}`, details);
        this.emit('log', data);
    }

    /**
     * Run scenario with progress tracking
     */
    async runScenarioWithProgress(scenario, onProgress) {
        const operationId = await this.startOperation('scenario', scenario, onProgress);
        
        try {
            const response = await fetch(`${this.baseUrl}/sse/scenario/${this.clientId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ scenario })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const result = await response.json();
            return result;
        } catch (error) {
            this.handleError({ operation_id: operationId, error: error.message });
            throw error;
        }
    }

    /**
     * Run Monte Carlo simulation with progress
     */
    async runMonteCarloWithProgress(scenario, nSimulations = 1000, onProgress) {
        const operationId = await this.startOperation('monte_carlo', { scenario, n_simulations: nSimulations }, onProgress);
        
        try {
            const response = await fetch(`${this.baseUrl}/sse/monte-carlo/${this.clientId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    scenario,
                    n_simulations: nSimulations
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const result = await response.json();
            return result;
        } catch (error) {
            this.handleError({ operation_id: operationId, error: error.message });
            throw error;
        }
    }

    /**
     * Run optimization with progress
     */
    async runOptimizationWithProgress(scenario, maxIterations = 100, onProgress) {
        const operationId = await this.startOperation('optimization', { scenario, max_iterations: maxIterations }, onProgress);
        
        try {
            const response = await fetch(`${this.baseUrl}/sse/optimization/${this.clientId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    scenario,
                    max_iterations: maxIterations
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const result = await response.json();
            return result;
        } catch (error) {
            this.handleError({ operation_id: operationId, error: error.message });
            throw error;
        }
    }

    /**
     * Export with progress tracking
     */
    async exportWithProgress(format = 'excel', onProgress) {
        const operationId = await this.startOperation('export', { format }, onProgress);
        
        try {
            const response = await fetch(`${this.baseUrl}/sse/export/${this.clientId}?format=${format}`, {
                method: 'POST'
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const result = await response.json();
            return result;
        } catch (error) {
            this.handleError({ operation_id: operationId, error: error.message });
            throw error;
        }
    }

    /**
     * Start an operation
     */
    async startOperation(type, data, onProgress) {
        const operationId = `${this.clientId}_${Date.now()}`;
        
        if (onProgress) {
            this.progressCallbacks.set(operationId, onProgress);
        }
        
        // Show progress UI
        // this.showProgressBar(operationId, type);
        
        return operationId;
    }

    /**
     * Update progress bar
     */
    updateProgressBar(operationId, progress, message) {
        const progressBar = document.getElementById(`progress-${operationId}`);
        if (progressBar) {
            progressBar.style.width = `${progress}%`;
            progressBar.setAttribute('aria-valuenow', progress);
            
            if (message) {
                const messageEl = document.getElementById(`progress-message-${operationId}`);
                if (messageEl) {
                    messageEl.textContent = message;
                }
            }
        }
    }

    /**
     * Show progress bar
     */
    showProgressBar(operationId, type) {
        // Create progress modal if it doesn't exist
        let modal = document.getElementById('progress-modal');
        if (!modal) {
            modal = this.createProgressModal();
        }
        
        // Add progress bar for this operation
        const container = document.getElementById('progress-container');
        const progressItem = document.createElement('div');
        progressItem.className = 'progress-item mb-3';
        progressItem.id = `progress-item-${operationId}`;
        progressItem.innerHTML = `
            <div class="d-flex justify-content-between align-items-center mb-1">
                <span class="text-sm">${type}</span>
                <span id="progress-message-${operationId}" class="text-sm text-muted">Initializing...</span>
            </div>
            <div class="progress">
                <div id="progress-${operationId}" 
                     class="progress-bar progress-bar-striped progress-bar-animated" 
                     role="progressbar" 
                     style="width: 0%" 
                     aria-valuenow="0" 
                     aria-valuemin="0" 
                     aria-valuemax="100">
                </div>
            </div>
        `;
        container.appendChild(progressItem);
        
        // Show modal
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
    }

    /**
     * Create progress modal
     */
    createProgressModal() {
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.id = 'progress-modal';
        modal.setAttribute('tabindex', '-1');
        modal.innerHTML = `
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Processing</h5>
                    </div>
                    <div class="modal-body">
                        <div id="progress-container"></div>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        return modal;
    }

    /**
     * Show error
     */
    showError(operationId, error) {
        const progressItem = document.getElementById(`progress-item-${operationId}`);
        if (progressItem) {
            progressItem.innerHTML += `
                <div class="alert alert-danger mt-2" role="alert">
                    <i class="bi bi-exclamation-triangle-fill"></i> ${error}
                </div>
            `;
        }
        
        // Remove progress callback
        this.progressCallbacks.delete(operationId);
    }

    /**
     * Add event listener
     */
    on(event, callback) {
        if (!this.listeners.has(event)) {
            this.listeners.set(event, []);
        }
        this.listeners.get(event).push(callback);
    }

    /**
     * Remove event listener
     */
    off(event, callback) {
        if (this.listeners.has(event)) {
            const callbacks = this.listeners.get(event);
            const index = callbacks.indexOf(callback);
            if (index > -1) {
                callbacks.splice(index, 1);
            }
        }
    }

    /**
     * Emit event
     */
    emit(event, data) {
        if (this.listeners.has(event)) {
            this.listeners.get(event).forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error(`Error in event listener for ${event}:`, error);
                }
            });
        }
    }

    /**
     * Get connection status
     */
    isConnected() {
        return this.connected;
    }

    /**
     * Get client ID
     */
    getClientId() {
        return this.clientId;
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SSEClient;
}
