/**
 * Client ID Helper - Simple utility to get and display the client ID
 * 
 * Usage:
 * 1. Open the browser console (F12)
 * 2. Run: getClientInfo()
 * 3. Or paste this entire script in the console
 */

// Function to generate a client ID (same as SSEClient)
function generateClientId() {
    return `client_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

// Function to get or create client ID
function getClientInfo() {
    // Check if SSE client exists
    if (typeof sseClient !== 'undefined' && sseClient && sseClient.getClientId) {
        const clientId = sseClient.getClientId();
        console.log('═══════════════════════════════════════════');
        console.log('🔑 Current SSE Client ID:', clientId);
        console.log('═══════════════════════════════════════════');
        
        // Also display in a popup
        alert(`Your Client ID: ${clientId}`);
        
        // Copy to clipboard
        if (navigator.clipboard) {
            navigator.clipboard.writeText(clientId).then(() => {
                console.log('✅ Client ID copied to clipboard!');
            });
        }
        
        return clientId;
    } 
    
    // Check if AppState has a client ID
    else if (typeof AppState !== 'undefined' && AppState.clientId) {
        console.log('═══════════════════════════════════════════');
        console.log('🔑 Stored Client ID:', AppState.clientId);
        console.log('═══════════════════════════════════════════');
        
        alert(`Your Client ID: ${AppState.clientId}`);
        
        if (navigator.clipboard) {
            navigator.clipboard.writeText(AppState.clientId).then(() => {
                console.log('✅ Client ID copied to clipboard!');
            });
        }
        
        return AppState.clientId;
    }
    
    // Generate a new one if none exists
    else {
        const newClientId = generateClientId();
        console.log('═══════════════════════════════════════════');
        console.log('🆕 Generated New Client ID:', newClientId);
        console.log('═══════════════════════════════════════════');
        console.log('ℹ️ Note: SSE client not initialized yet');
        console.log('═══════════════════════════════════════════');
        
        // Store it globally for later use
        if (typeof AppState !== 'undefined') {
            AppState.clientId = newClientId;
        } else {
            window.clientId = newClientId;
        }
        
        alert(`New Client ID Generated: ${newClientId}`);
        
        if (navigator.clipboard) {
            navigator.clipboard.writeText(newClientId).then(() => {
                console.log('✅ Client ID copied to clipboard!');
            });
        }
        
        return newClientId;
    }
}

// Auto-display client ID when script loads
if (typeof window !== 'undefined') {
    // Wait a bit for any initialization
    setTimeout(() => {
        console.log('💡 To get your client ID, run: getClientInfo()');
        
        // Try to get it automatically
        try {
            const clientId = getClientInfo();
            
            // Add a visual indicator to the page
            const indicator = document.createElement('div');
            indicator.id = 'client-id-indicator';
            indicator.style.cssText = `
                position: fixed;
                bottom: 20px;
                right: 20px;
                background: #28a745;
                color: white;
                padding: 10px 15px;
                border-radius: 5px;
                font-family: monospace;
                font-size: 12px;
                z-index: 10000;
                cursor: pointer;
                box-shadow: 0 2px 5px rgba(0,0,0,0.2);
            `;
            indicator.innerHTML = `
                <strong>Client ID:</strong><br>
                ${clientId.substring(0, 20)}...
                <br><small>(click to copy)</small>
            `;
            indicator.title = clientId;
            indicator.onclick = () => {
                navigator.clipboard.writeText(clientId).then(() => {
                    indicator.style.background = '#007bff';
                    indicator.innerHTML = `
                        <strong>Copied!</strong><br>
                        ${clientId.substring(0, 20)}...
                    `;
                    setTimeout(() => {
                        indicator.style.background = '#28a745';
                        indicator.innerHTML = `
                            <strong>Client ID:</strong><br>
                            ${clientId.substring(0, 20)}...
                            <br><small>(click to copy)</small>
                        `;
                    }, 2000);
                });
            };
            
            // Remove any existing indicator
            const existing = document.getElementById('client-id-indicator');
            if (existing) existing.remove();
            
            // Add to page
            document.body.appendChild(indicator);
            
        } catch (e) {
            console.error('Could not auto-detect client ID:', e);
        }
    }, 1000);
}

// Export for use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { generateClientId, getClientInfo };
}
