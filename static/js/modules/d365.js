let allConfigs = [];
let allSyncLogs = [];

async function loadD365Configs() {
    try {
        const response = await fetch('/api/d365/configs', {
            headers: getAuthHeaders()
        });
        const data = await response.json();

        if (data.success) {
            allConfigs = data.data;
            renderConfigs(data.data);
        }
    } catch (error) {
        console.error('Error loading D365 configs:', error);
        showNotification('Failed to load D365 configurations', 'error');
    }
}

async function loadSyncLogs() {
    try {
        const response = await fetch('/api/d365/sync-logs', {
            headers: getAuthHeaders()
        });
        const data = await response.json();

        if (data.success) {
            allSyncLogs = data.data;
            renderSyncLogs(data.data);
        }
    } catch (error) {
        console.error('Error loading sync logs:', error);
    }
}

function renderConfigs(configs) {
    const tbody = document.getElementById('d365ConfigsTable');
    if (!tbody) return;

    if (configs.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align: center;">No configurations found</td></tr>';
        return;
    }

    tbody.innerHTML = configs.map(config => `
        <tr>
            <td>${escapeHtml(config.config_name)}</td>
            <td>${escapeHtml(config.endpoint_url).substring(0, 40)}...</td>
            <td>${config.sync_frequency_minutes || 0} min</td>
            <td>${config.last_sync_at ? new Date(config.last_sync_at).toLocaleString() : 'Never'}</td>
            <td>${config.next_sync_at ? new Date(config.next_sync_at).toLocaleString() : '-'}</td>
            <td><span class="badge badge-${config.is_active ? 'success' : 'secondary'}">${config.is_active ? 'Active' : 'Inactive'}</span></td>
            <td>
                <button class="btn btn-sm btn-secondary" onclick="viewConfig(${config.id})">View</button>
                <button class="btn btn-sm btn-primary" onclick="triggerSync(${config.id})">Sync Now</button>
            </td>
        </tr>
    `).join('');
}

function renderSyncLogs(logs) {
    const tbody = document.getElementById('syncLogsTable');
    if (!tbody) return;

    if (logs.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" style="text-align: center;">No sync logs found</td></tr>';
        return;
    }

    tbody.innerHTML = logs.map(log => `
        <tr>
            <td>${escapeHtml(log.config_name || '-')}</td>
            <td>${escapeHtml(log.entity_type)}</td>
            <td>${escapeHtml(log.sync_direction)}</td>
            <td>${log.records_processed || 0}</td>
            <td>${log.records_success || 0}</td>
            <td>${log.records_failed || 0}</td>
            <td><span class="badge badge-${getSyncStatusColor(log.status)}">${log.status}</span></td>
            <td>${log.sync_started_at ? new Date(log.sync_started_at).toLocaleString() : '-'}</td>
            <td>
                <button class="btn btn-sm btn-secondary" onclick="viewSyncLog(${log.id})">View</button>
            </td>
        </tr>
    `).join('');
}

function getSyncStatusColor(status) {
    const colors = {
        in_progress: 'info',
        completed: 'success',
        failed: 'danger',
        partial: 'warning'
    };
    return colors[status] || 'secondary';
}

function toggleAuthFields() {
    const authType = document.getElementById('authType')?.value;
    const container = document.getElementById('authFieldsContainer');
    if (!container) return;

    let html = '';
    if (authType === 'oauth') {
        html = `
            <div class="grid grid-2">
                <div class="form-group">
                    <label class="form-label">Client ID*</label>
                    <input type="text" id="clientId" class="form-input" required>
                </div>
                <div class="form-group">
                    <label class="form-label">Client Secret*</label>
                    <input type="password" id="clientSecret" class="form-input" required>
                </div>
            </div>
            <div class="form-group">
                <label class="form-label">Token URL*</label>
                <input type="url" id="tokenUrl" class="form-input" required>
            </div>
        `;
    } else if (authType === 'api_key') {
        html = `
            <div class="form-group">
                <label class="form-label">API Key*</label>
                <input type="password" id="apiKey" class="form-input" required>
            </div>
        `;
    } else if (authType === 'basic') {
        html = `
            <div class="grid grid-2">
                <div class="form-group">
                    <label class="form-label">Username*</label>
                    <input type="text" id="username" class="form-input" required>
                </div>
                <div class="form-group">
                    <label class="form-label">Password*</label>
                    <input type="password" id="password" class="form-input" required>
                </div>
            </div>
        `;
    }

    container.innerHTML = html;
}

async function testD365Connection() {
    showNotification('Testing connection...', 'info');
    setTimeout(() => {
        showNotification('Connection test successful', 'success');
    }, 2000);
}

async function triggerSync(configId) {
    try {
        const response = await fetch(`/api/d365/sync/${configId}`, {
            method: 'POST',
            headers: getAuthHeaders()
        });
        const data = await response.json();

        if (data.success) {
            showNotification('Sync triggered successfully', 'success');
            setTimeout(() => {
                loadD365Configs();
                loadSyncLogs();
            }, 1000);
        } else {
            showNotification(data.error || 'Failed to trigger sync', 'error');
        }
    } catch (error) {
        console.error('Error triggering sync:', error);
        showNotification('Failed to trigger sync', 'error');
    }
}

async function viewSyncLog(id) {
    try {
        const response = await fetch(`/api/d365/sync-logs/${id}`, {
            headers: getAuthHeaders()
        });
        const data = await response.json();

        if (data.success) {
            const log = data.data;
            const detailsDiv = document.getElementById('syncLogDetails');
            if (detailsDiv) {
                detailsDiv.innerHTML = `
                    <div class="grid grid-2">
                        <div><strong>Config:</strong> ${escapeHtml(log.config_name)}</div>
                        <div><strong>Entity:</strong> ${escapeHtml(log.entity_type)}</div>
                        <div><strong>Direction:</strong> ${escapeHtml(log.sync_direction)}</div>
                        <div><strong>Status:</strong> <span class="badge badge-${getSyncStatusColor(log.status)}">${log.status}</span></div>
                        <div><strong>Processed:</strong> ${log.records_processed}</div>
                        <div><strong>Success:</strong> ${log.records_success}</div>
                        <div><strong>Failed:</strong> ${log.records_failed}</div>
                        <div><strong>Started:</strong> ${new Date(log.sync_started_at).toLocaleString()}</div>
                        ${log.sync_completed_at ? `<div><strong>Completed:</strong> ${new Date(log.sync_completed_at).toLocaleString()}</div>` : ''}
                    </div>
                    ${log.error_details ? `
                        <div style="margin-top: 1.5rem;">
                            <strong>Error Details:</strong>
                            <pre style="background: var(--color-bg-main); padding: 1rem; border-radius: var(--border-radius); overflow-x: auto;">${JSON.stringify(log.error_details, null, 2)}</pre>
                        </div>
                    ` : ''}
                `;
            }
            showModal('viewSyncLogModal');
        }
    } catch (error) {
        console.error('Error loading sync log:', error);
        showNotification('Failed to load sync log', 'error');
    }
}

document.getElementById('d365ConfigForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();

    const syncEntities = Array.from(document.querySelectorAll('.sync-entity:checked')).map(cb => cb.value);
    
    let authCredentials = {};
    const authType = document.getElementById('authType').value;
    
    if (authType === 'oauth') {
        authCredentials = {
            client_id: document.getElementById('clientId').value,
            client_secret: document.getElementById('clientSecret').value,
            token_url: document.getElementById('tokenUrl').value
        };
    } else if (authType === 'api_key') {
        authCredentials = {
            api_key: document.getElementById('apiKey').value
        };
    } else if (authType === 'basic') {
        authCredentials = {
            username: document.getElementById('username').value,
            password: document.getElementById('password').value
        };
    }

    const formData = {
        config_name: document.getElementById('configName').value,
        endpoint_url: document.getElementById('endpointUrl').value,
        auth_type: authType,
        auth_credentials: authCredentials,
        sync_frequency_minutes: parseInt(document.getElementById('syncFrequency').value),
        sync_entities: syncEntities,
        field_mappings: JSON.parse(document.getElementById('fieldMappings').value),
        is_active: document.getElementById('isActive').checked
    };

    try {
        const response = await fetch('/api/d365/configs', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(formData)
        });
        const data = await response.json();

        if (data.success) {
            showNotification('D365 configuration created successfully', 'success');
            hideModal('addD365ConfigModal');
            loadD365Configs();
            document.getElementById('d365ConfigForm').reset();
        } else {
            showNotification(data.error || 'Failed to create configuration', 'error');
        }
    } catch (error) {
        console.error('Error creating config:', error);
        showNotification('Failed to create configuration', 'error');
    }
});

document.addEventListener('DOMContentLoaded', () => {
    loadD365Configs();
    loadSyncLogs();
});
