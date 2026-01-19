let allTickets = [];

async function loadSopTickets() {
    const status = document.getElementById('filterStatus')?.value;
    const department = document.getElementById('filterDepartment')?.value;

    const params = new URLSearchParams();
    if (status) params.append('status', status);
    if (department) params.append('department_id', department);

    try {
        const response = await fetch(`/api/sop/tickets?${params.toString()}`, {
            headers: getAuthHeaders()
        });
        const data = await response.json();

        if (data.success) {
            allTickets = data.data;
            renderTickets(data.data);
        }
    } catch (error) {
        console.error('Error loading SOP tickets:', error);
        showNotification('Failed to load SOP tickets', 'error');
    }
}

function renderTickets(tickets) {
    const tbody = document.getElementById('ticketsTable');
    if (!tbody) return;

    if (tickets.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" style="text-align: center;">No tickets found</td></tr>';
        return;
    }

    tbody.innerHTML = tickets.map(ticket => `
        <tr>
            <td>${escapeHtml(ticket.ticket_number)}</td>
            <td>${escapeHtml(ticket.sop_reference)}</td>
            <td>${escapeHtml(ticket.charging_department || '-')}</td>
            <td>${escapeHtml(ticket.charged_department || '-')}</td>
            <td>${escapeHtml(ticket.failure_description || '-').substring(0, 50)}...</td>
            <td><span class="badge badge-${getStatusColor(ticket.status)}">${ticket.status}</span></td>
            <td>${ticket.created_at ? new Date(ticket.created_at).toLocaleDateString() : '-'}</td>
            <td>
                <button class="btn btn-sm btn-secondary" onclick="viewTicket(${ticket.id})">View</button>
                ${canTakeAction(ticket) ? `<button class="btn btn-sm btn-primary" onclick="showActions(${ticket.id})">Actions</button>` : ''}
            </td>
        </tr>
    `).join('');
}

function canTakeAction(ticket) {
    return ticket.status !== 'closed';
}

async function viewTicket(id) {
    try {
        const response = await fetch(`/api/sop/tickets/${id}`, {
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
                        <div><strong>SOP Reference:</strong> ${escapeHtml(ticket.sop_reference)}</div>
                        <div><strong>Created:</strong> ${new Date(ticket.created_at).toLocaleString()}</div>
                        <div><strong>Charging Department:</strong> ${escapeHtml(ticket.charging_department)}</div>
                        <div><strong>Charged Department:</strong> ${escapeHtml(ticket.charged_department)}</div>
                    </div>
                    <div style="margin-top: 1rem;">
                        <strong>Failure Description:</strong>
                        <p>${escapeHtml(ticket.failure_description)}</p>
                    </div>
                    ${ticket.impact_description ? `
                        <div style="margin-top: 1rem;">
                            <strong>Impact:</strong>
                            <p>${escapeHtml(ticket.impact_description)}</p>
                        </div>
                    ` : ''}
                    ${ticket.rejection_reason ? `
                        <div style="margin-top: 1rem;">
                            <strong>Rejection Reason:</strong>
                            <p>${escapeHtml(ticket.rejection_reason)}</p>
                        </div>
                    ` : ''}
                    ${ticket.reassignment_reason ? `
                        <div style="margin-top: 1rem;">
                            <strong>Reassignment Reason:</strong>
                            <p>${escapeHtml(ticket.reassignment_reason)}</p>
                        </div>
                    ` : ''}
                    ${ticket.ncr_completed_at ? `
                        <div style="margin-top: 1rem;">
                            <strong>NCR Completed At:</strong> ${new Date(ticket.ncr_completed_at).toLocaleString()}
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

function getStatusColor(status) {
    const colors = {
        open: 'warning',
        ncr_in_progress: 'info',
        ncr_completed: 'success',
        rejected: 'danger',
        reassigned: 'secondary',
        escalated: 'danger',
        closed: 'secondary'
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
            const selects = ['filterDepartment', 'chargingDepartment', 'chargedDepartment'];
            selects.forEach(selectId => {
                const select = document.getElementById(selectId);
                if (select) {
                    const hasFilter = selectId.startsWith('filter');
                    select.innerHTML = (hasFilter ? '<option value="">All Departments</option>' : '<option value="">Select Department</option>') +
                        data.data.map(dept => `<option value="${dept.id}">${escapeHtml(dept.name)}</option>`).join('');
                }
            });
        }
    } catch (error) {
        console.error('Error loading departments:', error);
    }
}

document.getElementById('sopTicketForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();

    const formData = {
        sop_reference: document.getElementById('sopReference').value,
        charging_department_id: parseInt(document.getElementById('chargingDepartment').value),
        charged_department_id: parseInt(document.getElementById('chargedDepartment').value),
        failure_description: document.getElementById('failureDescription').value,
        impact_description: document.getElementById('impactDescription').value
    };

    try {
        const response = await fetch('/api/sop/tickets', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(formData)
        });
        const data = await response.json();

        if (data.success) {
            showNotification('SOP ticket created successfully', 'success');
            hideModal('addSopTicketModal');
            loadSopTickets();
            document.getElementById('sopTicketForm').reset();
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
    loadSopTickets();
});
