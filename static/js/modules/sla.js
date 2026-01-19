let allSlas = [];
let escalationLevelCount = 0;

async function filterSlas() {
    const entityType = document.getElementById('filterEntityType')?.value;
    const department = document.getElementById('filterDepartment')?.value;
    const priority = document.getElementById('filterPriority')?.value;

    const params = new URLSearchParams();
    if (entityType) params.append('entity_type', entityType);
    if (department) params.append('department_id', department);
    if (priority) params.append('priority', priority);

    try {
        const response = await fetch(`/api/sla/configurations?${params.toString()}`, {
            headers: getAuthHeaders()
        });
        const data = await response.json();

        if (data.success) {
            allSlas = data.data;
            renderSlas(data.data);
        }
    } catch (error) {
        console.error('Error loading SLAs:', error);
        showNotification('Failed to load SLAs', 'error');
    }
}

function renderSlas(slas) {
    const tbody = document.getElementById('slasTable');
    if (!tbody) return;

    if (slas.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" style="text-align: center;">No SLAs found</td></tr>';
        return;
    }

    tbody.innerHTML = slas.map(sla => `
        <tr>
            <td>${escapeHtml(sla.sla_name)}</td>
            <td>${escapeHtml(sla.entity_type)}</td>
            <td>${escapeHtml(sla.department_name || 'All')}</td>
            <td><span class="badge badge-${getPriorityColor(sla.priority)}">${sla.priority}</span></td>
            <td>${formatMinutes(sla.response_time_minutes)}</td>
            <td>${formatMinutes(sla.resolution_time_minutes)}</td>
            <td>${sla.escalation_count || 0} levels</td>
            <td><span class="badge badge-${sla.is_active ? 'success' : 'secondary'}">${sla.is_active ? 'Active' : 'Inactive'}</span></td>
            <td>
                <button class="btn btn-sm btn-secondary" onclick="viewSla(${sla.id})">View</button>
            </td>
        </tr>
    `).join('');
}

function formatMinutes(minutes) {
    if (!minutes) return '-';
    if (minutes < 60) return `${minutes}m`;
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`;
}

function getPriorityColor(priority) {
    const colors = {
        low: 'info',
        normal: 'secondary',
        high: 'warning',
        critical: 'danger'
    };
    return colors[priority] || 'secondary';
}

function addEscalationLevel() {
    escalationLevelCount++;
    const container = document.getElementById('escalationLevelsContainer');
    if (!container) return;

    const levelHtml = `
        <div class="escalation-level card" data-level-id="${escalationLevelCount}" style="padding: 1rem; margin-bottom: 1rem; background: var(--color-bg-main);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                <strong>Escalation Level ${escalationLevelCount}</strong>
                <button type="button" class="btn btn-sm btn-danger" onclick="removeEscalationLevel(${escalationLevelCount})">Remove</button>
            </div>
            <div class="grid grid-2">
                <div class="form-group">
                    <label class="form-label">Time to Escalate (Minutes)*</label>
                    <input type="number" class="form-input escalation-time" required>
                </div>
                <div class="form-group">
                    <label class="form-label">Escalate To (Role/User)*</label>
                    <input type="text" class="form-input escalation-to" required>
                </div>
            </div>
        </div>
    `;

    container.insertAdjacentHTML('beforeend', levelHtml);
}

function removeEscalationLevel(levelId) {
    const level = document.querySelector(`.escalation-level[data-level-id="${levelId}"]`);
    if (level) level.remove();
}

async function loadDepartments() {
    try {
        const response = await fetch('/api/departments', {
            headers: getAuthHeaders()
        });
        const data = await response.json();

        if (data.success) {
            const selects = ['departmentId', 'filterDepartment'];
            selects.forEach(selectId => {
                const select = document.getElementById(selectId);
                if (select) {
                    const hasFilter = selectId.startsWith('filter');
                    select.innerHTML = (hasFilter ? '<option value="">All Departments</option>' : '<option value="">All Departments</option>') +
                        data.data.map(dept => `<option value="${dept.id}">${escapeHtml(dept.name)}</option>`).join('');
                }
            });
        }
    } catch (error) {
        console.error('Error loading departments:', error);
    }
}

async function viewSla(id) {
    try {
        const response = await fetch(`/api/sla/configurations/${id}`, {
            headers: getAuthHeaders()
        });
        const data = await response.json();

        if (data.success) {
            const sla = data.data;
            const detailsDiv = document.getElementById('slaDetails');
            if (detailsDiv) {
                detailsDiv.innerHTML = `
                    <div class="grid grid-2">
                        <div><strong>SLA Name:</strong> ${escapeHtml(sla.sla_name)}</div>
                        <div><strong>Entity Type:</strong> ${escapeHtml(sla.entity_type)}</div>
                        <div><strong>Department:</strong> ${escapeHtml(sla.department_name || 'All')}</div>
                        <div><strong>Priority:</strong> <span class="badge badge-${getPriorityColor(sla.priority)}">${sla.priority}</span></div>
                        <div><strong>Response Time:</strong> ${formatMinutes(sla.response_time_minutes)}</div>
                        <div><strong>Resolution Time:</strong> ${formatMinutes(sla.resolution_time_minutes)}</div>
                    </div>
                    ${sla.escalation_levels ? `
                        <div style="margin-top: 1.5rem;">
                            <strong>Escalation Levels:</strong>
                            <pre style="background: var(--color-bg-main); padding: 1rem; border-radius: var(--border-radius); overflow-x: auto;">${JSON.stringify(sla.escalation_levels, null, 2)}</pre>
                        </div>
                    ` : ''}
                `;
            }
            showModal('viewSlaModal');
        }
    } catch (error) {
        console.error('Error loading SLA details:', error);
        showNotification('Failed to load SLA details', 'error');
    }
}

document.getElementById('slaForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();

    const escalationLevels = [];
    document.querySelectorAll('.escalation-level').forEach((level, index) => {
        escalationLevels.push({
            level: index + 1,
            time_minutes: parseInt(level.querySelector('.escalation-time').value),
            escalate_to: level.querySelector('.escalation-to').value
        });
    });

    const formData = {
        sla_name: document.getElementById('slaName').value,
        entity_type: document.getElementById('entityType').value,
        department_id: document.getElementById('departmentId').value ? parseInt(document.getElementById('departmentId').value) : null,
        priority: document.getElementById('priority').value,
        response_time_minutes: parseInt(document.getElementById('responseTimeMinutes').value),
        resolution_time_minutes: parseInt(document.getElementById('resolutionTimeMinutes').value),
        escalation_levels: escalationLevels,
        is_active: document.getElementById('isActive').checked
    };

    try {
        const response = await fetch('/api/sla/configurations', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(formData)
        });
        const data = await response.json();

        if (data.success) {
            showNotification('SLA created successfully', 'success');
            hideModal('addSlaModal');
            filterSlas();
            document.getElementById('slaForm').reset();
            document.getElementById('escalationLevelsContainer').innerHTML = '';
            escalationLevelCount = 0;
        } else {
            showNotification(data.error || 'Failed to create SLA', 'error');
        }
    } catch (error) {
        console.error('Error creating SLA:', error);
        showNotification('Failed to create SLA', 'error');
    }
});

document.addEventListener('DOMContentLoaded', () => {
    loadDepartments();
    filterSlas();
});
