let allReportConfigs = [];

async function loadReportConfigs() {
    try {
        const response = await fetch('/api/reports/configurations', {
            headers: getAuthHeaders()
        });
        const data = await response.json();

        if (data.success) {
            allReportConfigs = data.data;
            renderReportConfigs(data.data);
        }
    } catch (error) {
        console.error('Error loading report configurations:', error);
        showNotification('Failed to load report configurations', 'error');
    }
}

function renderReportConfigs(configs) {
    const tbody = document.getElementById('reportConfigsTable');
    if (!tbody) return;

    if (configs.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align: center;">No report configurations found</td></tr>';
        return;
    }

    tbody.innerHTML = configs.map(config => `
        <tr>
            <td>${escapeHtml(config.report_name)}</td>
            <td>${escapeHtml(config.report_type)}</td>
            <td>${config.schedule_info || 'Manual'}</td>
            <td>${config.recipient_count || 0}</td>
            <td>${config.last_run_at ? new Date(config.last_run_at).toLocaleString() : 'Never'}</td>
            <td><span class="badge badge-${config.is_active ? 'success' : 'secondary'}">${config.is_active ? 'Active' : 'Inactive'}</span></td>
            <td>
                <button class="btn btn-sm btn-secondary" onclick="viewReportConfig(${config.id})">View</button>
                <button class="btn btn-sm btn-primary" onclick="runReport(${config.id})">Run Now</button>
            </td>
        </tr>
    `).join('');
}

async function runReport(id) {
    try {
        const response = await fetch(`/api/reports/run/${id}`, {
            method: 'POST',
            headers: getAuthHeaders()
        });
        const data = await response.json();

        if (data.success) {
            showNotification('Report generated successfully', 'success');
            loadReportConfigs();
        } else {
            showNotification(data.error || 'Failed to run report', 'error');
        }
    } catch (error) {
        console.error('Error running report:', error);
        showNotification('Failed to run report', 'error');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    loadReportConfigs();
});
