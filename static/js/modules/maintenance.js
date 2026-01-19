let allTickets = [];

async function loadMaintenanceTickets() {
    const status = document.getElementById('filterStatus')?.value;
    const severity = document.getElementById('filterSeverity')?.value;
    const department = document.getElementById('filterDepartment')?.value;

    const params = new URLSearchParams();
    if (status) params.append('status', status);
    if (severity) params.append('severity', severity);
    if (department) params.append('department_id', department);

    try {
        const response = await fetch(`/api/maintenance/tickets?${params.toString()}`, {
            headers: getAuthHeaders()
        });
        const data = await response.json();

        if (data.success) {
            allTickets = data.data;
            renderTickets(data.data);
        }
    } catch (error) {
        console.error('Error loading tickets:', error);
        showNotification('Failed to load maintenance tickets', 'error');
    }
}

function renderTickets(tickets) {
    const tbody = document.getElementById('ticketsTable');
    if (!tbody) return;

    if (tickets.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" style="text-align: center;">No tickets found</td></tr>';
        return;
    }

    tbody.innerHTML = tickets.map(ticket => `
        <tr>
            <td>${escapeHtml(ticket.ticket_number)}</td>
            <td>${escapeHtml(ticket.machine_name || '-')}</td>
            <td>${escapeHtml(ticket.department_name || '-')}</td>
            <td>${escapeHtml(ticket.issue_description || '-').substring(0, 40)}...</td>
            <td><span class="badge badge-${getSeverityColor(ticket.severity)}">${ticket.severity}</span></td>
            <td><span class="badge badge-${getStatusColor(ticket.status)}">${ticket.status}</span></td>
            <td>${escapeHtml(ticket.assigned_to || '-')}</td>
            <td>${ticket.created_at ? new Date(ticket.created_at).toLocaleDateString() : '-'}</td>
            <td>
                <button class="btn btn-sm btn-secondary" onclick="viewTicket(${ticket.id})">View</button>
                ${ticket.status === 'open' ? `<button class="btn btn-sm btn-primary" onclick="assignTicket(${ticket.id})">Assign</button>` : ''}
            </td>
        </tr>
    `).join('');
}

async function viewTicket(id) {
    try {
        const response = await fetch(`/api/maintenance/tickets/${id}`, {
            headers: getAuthHeaders()
        });
        const data = await response.json();

        if (data.success) {
            const ticket = data.data;
            const detailsDiv = document.getElementById('ticketDetails');
            if (detailsDiv) {
                detailsDiv.innerHTML = `
                    <div class="grid grid-2">
                        <div><strong>Ticket Number:</strong> ${escapeHtml(ticket.ticket_number)}</div>
                        <div><strong>Status:</strong> <span class="badge badge-${getStatusColor(ticket.status)}">${ticket.status}</span></div>
                        <div><strong>Machine:</strong> ${escapeHtml(ticket.machine_name)}</div>
                        <div><strong>Department:</strong> ${escapeHtml(ticket.department_name)}</div>
                        <div><strong>Severity:</strong> <span class="badge badge-${getSeverityColor(ticket.severity)}">${ticket.severity}</span></div>
                        <div><strong>Reported By:</strong> ${escapeHtml(ticket.reported_by)}</div>
                        ${ticket.assigned_to ? `<div><strong>Assigned To:</strong> ${escapeHtml(ticket.assigned_to)}</div>` : ''}
                        <div><strong>Created:</strong> ${new Date(ticket.created_at).toLocaleString()}</div>
                    </div>
                    <div style="margin-top: 1rem;">
                        <strong>Issue Description:</strong>
                        <p>${escapeHtml(ticket.issue_description)}</p>
                    </div>
                    ${ticket.work_performed ? `
                        <div style="margin-top: 1rem;">
                            <strong>Work Performed:</strong>
                            <p>${escapeHtml(ticket.work_performed)}</p>
                        </div>
                    ` : ''}
                    ${ticket.parts_used ? `
                        <div style="margin-top: 1rem;">
                            <strong>Parts Used:</strong>
                            <p>${escapeHtml(ticket.parts_used)}</p>
                        </div>
                    ` : ''}
                    ${ticket.downtime_minutes ? `
                        <div style="margin-top: 1rem;">
                            <strong>Downtime:</strong> ${ticket.downtime_minutes} minutes
                        </div>
                    ` : ''}
                `;
            }
            showModal('viewTicketModal');
        }
    } catch (error) {
        console.error('Error loading ticket details:', error);
        showNotification('Failed to load ticket details', 'error');
    }
}

function getSeverityColor(severity) {
    const colors = {
        low: 'info',
        medium: 'warning',
        high: 'danger',
        critical: 'danger'
    };
    return colors[severity] || 'secondary';
}

function getStatusColor(status) {
    const colors = {
        open: 'warning',
        assigned: 'info',
        in_progress: 'info',
        awaiting_parts: 'secondary',
        completed: 'success',
        cancelled: 'secondary'
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
            const select = document.getElementById('machineId');
            if (select) {
                select.innerHTML = '<option value="">Select Machine</option>' +
                    data.data.map(machine => `<option value="${machine.id}">${escapeHtml(machine.machine_name)} (${escapeHtml(machine.machine_number)})</option>`).join('');
            }
        }
    } catch (error) {
        console.error('Error loading machines:', error);
    }
}

document.getElementById('maintenanceTicketForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();

    const formData = {
        machine_id: parseInt(document.getElementById('machineId').value),
        issue_description: document.getElementById('issueDescription').value,
        severity: document.getElementById('severity').value
    };

    try {
        const response = await fetch('/api/maintenance/tickets', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(formData)
        });
        const data = await response.json();

        if (data.success) {
            showNotification('Maintenance ticket created successfully', 'success');
            hideModal('addMaintenanceTicketModal');
            loadMaintenanceTickets();
            document.getElementById('maintenanceTicketForm').reset();
        } else {
            showNotification(data.error || 'Failed to create ticket', 'error');
        }
    } catch (error) {
        console.error('Error creating ticket:', error);
        showNotification('Failed to create ticket', 'error');
    }
});

document.addEventListener('DOMContentLoaded', () => {
    loadDepartments();
    loadMachines();
    loadMaintenanceTickets();
});
