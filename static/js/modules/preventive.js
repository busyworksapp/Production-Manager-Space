let allSchedules = [];
let allLogs = [];

async function filterSchedules() {
    const department = document.getElementById('filterDepartment')?.value;
    const machine = document.getElementById('filterMachine')?.value;
    const priority = document.getElementById('filterPriority')?.value;
    const status = document.getElementById('filterStatus')?.value;

    const params = new URLSearchParams();
    if (department) params.append('department_id', department);
    if (machine) params.append('machine_id', machine);
    if (priority) params.append('priority', priority);
    if (status) params.append('is_active', status === 'active' ? 'true' : 'false');

    try {
        const response = await fetch(`/api/preventive-maintenance/schedules?${params.toString()}`, {
            headers: getAuthHeaders()
        });
        const data = await response.json();

        if (data.success) {
            allSchedules = data.data;
            renderSchedules(data.data);
        }
    } catch (error) {
        console.error('Error loading schedules:', error);
        showNotification('Failed to load schedules', 'error');
    }
}

async function loadLogs() {
    try {
        const response = await fetch('/api/preventive-maintenance/logs', {
            headers: getAuthHeaders()
        });
        const data = await response.json();

        if (data.success) {
            allLogs = data.data;
            renderLogs(data.data);
        }
    } catch (error) {
        console.error('Error loading logs:', error);
    }
}

function renderSchedules(schedules) {
    const tbody = document.getElementById('schedulesTable');
    if (!tbody) return;

    if (schedules.length === 0) {
        tbody.innerHTML = '<tr><td colspan="10" style="text-align: center;">No schedules found</td></tr>';
        return;
    }

    tbody.innerHTML = schedules.map(schedule => `
        <tr>
            <td>${escapeHtml(schedule.schedule_name)}</td>
            <td>${escapeHtml(schedule.machine_name || '-')}</td>
            <td>${escapeHtml(schedule.department_name || '-')}</td>
            <td>${escapeHtml(schedule.maintenance_type)}</td>
            <td>${formatFrequency(schedule.frequency_type, schedule.frequency_value)}</td>
            <td>${schedule.last_performed_at ? new Date(schedule.last_performed_at).toLocaleDateString() : 'Never'}</td>
            <td>${schedule.next_due_at ? new Date(schedule.next_due_at).toLocaleDateString() : '-'}</td>
            <td><span class="badge badge-${getPriorityColor(schedule.priority)}">${schedule.priority}</span></td>
            <td>${escapeHtml(schedule.technician_name || 'Unassigned')}</td>
            <td>
                <button class="btn btn-sm btn-secondary" onclick="viewSchedule(${schedule.id})">View</button>
                <button class="btn btn-sm btn-primary" onclick="performMaintenance(${schedule.id})">Log</button>
            </td>
        </tr>
    `).join('');
}

function renderLogs(logs) {
    const tbody = document.getElementById('logsTable');
    if (!tbody) return;

    if (logs.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align: center;">No logs found</td></tr>';
        return;
    }

    tbody.innerHTML = logs.map(log => `
        <tr>
            <td>${escapeHtml(log.schedule_name || '-')}</td>
            <td>${log.performed_at ? new Date(log.performed_at).toLocaleString() : '-'}</td>
            <td>${escapeHtml(log.performed_by || '-')}</td>
            <td>${log.duration_minutes || 0} min</td>
            <td><span class="badge badge-${getLogStatusColor(log.status)}">${log.status}</span></td>
            <td>${log.next_recommended_date ? new Date(log.next_recommended_date).toLocaleDateString() : '-'}</td>
            <td>
                <button class="btn btn-sm btn-secondary" onclick="viewLog(${log.id})">View</button>
            </td>
        </tr>
    `).join('');
}

function formatFrequency(type, value) {
    const typeMap = {
        daily: 'Daily',
        weekly: 'Weekly',
        monthly: 'Monthly',
        quarterly: 'Quarterly',
        yearly: 'Yearly',
        hours_based: 'Hours',
        cycles_based: 'Cycles'
    };
    return `${typeMap[type] || type} (${value})`;
}

function getPriorityColor(priority) {
    const colors = {
        low: 'info',
        medium: 'warning',
        high: 'danger',
        critical: 'danger'
    };
    return colors[priority] || 'secondary';
}

function getLogStatusColor(status) {
    const colors = {
        completed: 'success',
        partially_completed: 'warning',
        skipped: 'secondary',
        rescheduled: 'info'
    };
    return colors[status] || 'secondary';
}

async function loadDepartments() {
    try {
        const response = await fetch('/api/departments', {
            headers: getAuthHeaders()
        });
        const data = await response.json();

        if (data.success) {
            const select = document.getElementById('filterDepartment');
            if (select) {
                select.innerHTML = '<option value="">All Departments</option>' +
                    data.data.map(dept => `<option value="${dept.id}">${escapeHtml(dept.name)}</option>`).join('');
            }
        }
    } catch (error) {
        console.error('Error loading departments:', error);
    }
}

async function loadMachines() {
    try {
        const response = await fetch('/api/machines', {
            headers: getAuthHeaders()
        });
        const data = await response.json();

        if (data.success) {
            const selects = ['filterMachine', 'machineId'];
            selects.forEach(selectId => {
                const select = document.getElementById(selectId);
                if (select) {
                    const hasFilter = selectId.startsWith('filter');
                    select.innerHTML = (hasFilter ? '<option value="">All Machines</option>' : '<option value="">Select Machine</option>') +
                        data.data.map(machine => `<option value="${machine.id}">${escapeHtml(machine.machine_name)} (${escapeHtml(machine.machine_number)})</option>`).join('');
                }
            });
        }
    } catch (error) {
        console.error('Error loading machines:', error);
    }
}

async function loadTechnicians() {
    try {
        const response = await fetch('/api/employees?type=technician', {
            headers: getAuthHeaders()
        });
        const data = await response.json();

        if (data.success) {
            const select = document.getElementById('assignedTechnician');
            if (select) {
                select.innerHTML = '<option value="">Unassigned</option>' +
                    data.data.map(tech => `<option value="${tech.id}">${escapeHtml(tech.first_name)} ${escapeHtml(tech.last_name)}</option>`).join('');
            }
        }
    } catch (error) {
        console.error('Error loading technicians:', error);
    }
}

function performMaintenance(scheduleId) {
    document.getElementById('performScheduleId').value = scheduleId;
    const now = new Date();
    const dateTime = now.toISOString().slice(0, 16);
    document.getElementById('performedAt').value = dateTime;
    showModal('performMaintenanceModal');
}

document.getElementById('scheduleForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();

    const formData = {
        schedule_name: document.getElementById('scheduleName').value,
        machine_id: parseInt(document.getElementById('machineId').value),
        maintenance_type: document.getElementById('maintenanceType').value,
        description: document.getElementById('description').value,
        frequency_type: document.getElementById('frequencyType').value,
        frequency_value: parseInt(document.getElementById('frequencyValue').value),
        estimated_duration_minutes: document.getElementById('estimatedDuration').value ? parseInt(document.getElementById('estimatedDuration').value) : null,
        priority: document.getElementById('priority').value,
        assigned_technician_id: document.getElementById('assignedTechnician').value ? parseInt(document.getElementById('assignedTechnician').value) : null,
        checklist: document.getElementById('checklist').value ? JSON.parse(document.getElementById('checklist').value) : null,
        parts_required: document.getElementById('partsRequired').value ? JSON.parse(document.getElementById('partsRequired').value) : null,
        is_active: document.getElementById('isActive').checked
    };

    try {
        const response = await fetch('/api/preventive-maintenance/schedules', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(formData)
        });
        const data = await response.json();

        if (data.success) {
            showNotification('Schedule created successfully', 'success');
            hideModal('addScheduleModal');
            filterSchedules();
            document.getElementById('scheduleForm').reset();
        } else {
            showNotification(data.error || 'Failed to create schedule', 'error');
        }
    } catch (error) {
        console.error('Error creating schedule:', error);
        showNotification('Failed to create schedule', 'error');
    }
});

document.getElementById('performMaintenanceForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();

    const scheduleId = document.getElementById('performScheduleId').value;
    const formData = {
        performed_at: document.getElementById('performedAt').value,
        duration_minutes: parseInt(document.getElementById('durationMinutes').value),
        checklist_results: document.getElementById('checklistResults').value ? JSON.parse(document.getElementById('checklistResults').value) : null,
        parts_used: document.getElementById('partsUsed').value ? JSON.parse(document.getElementById('partsUsed').value) : null,
        observations: document.getElementById('observations').value,
        status: document.getElementById('status').value,
        next_recommended_date: document.getElementById('nextRecommendedDate').value || null
    };

    try {
        const response = await fetch(`/api/preventive-maintenance/schedules/${scheduleId}/log`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(formData)
        });
        const data = await response.json();

        if (data.success) {
            showNotification('Maintenance logged successfully', 'success');
            hideModal('performMaintenanceModal');
            filterSchedules();
            loadLogs();
            document.getElementById('performMaintenanceForm').reset();
        } else {
            showNotification(data.error || 'Failed to log maintenance', 'error');
        }
    } catch (error) {
        console.error('Error logging maintenance:', error);
        showNotification('Failed to log maintenance', 'error');
    }
});

document.addEventListener('DOMContentLoaded', () => {
    loadDepartments();
    loadMachines();
    loadTechnicians();
    filterSchedules();
    loadLogs();
});
