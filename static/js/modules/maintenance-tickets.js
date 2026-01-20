class MaintenanceTicketsPage {
    constructor() {
        this.init();
    }

    init() {
        const user = getCurrentUser();
        if (user) {
            document.getElementById('username').textContent = `${user.first_name} ${user.last_name}`;
        }
        
        this.attachEventListeners();
        this.loadTickets();
    }

    attachEventListeners() {
        const logoutBtn = document.querySelector('.logout-btn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', () => logout());
        }

        const createTicketBtn = document.querySelector('.create-ticket-btn');
        if (createTicketBtn) {
            createTicketBtn.addEventListener('click', () => showModal('addTicketModal'));
        }

        const statusFilter = document.getElementById('statusFilter');
        if (statusFilter) {
            statusFilter.addEventListener('change', () => this.loadTickets());
        }

        const ticketForm = document.getElementById('ticketForm');
        if (ticketForm) {
            ticketForm.addEventListener('submit', (e) => this.submitTicketForm(e));
        }

        const closeModalBtn = document.querySelector('.close-ticket-modal-btn');
        if (closeModalBtn) {
            closeModalBtn.addEventListener('click', () => hideModal('addTicketModal'));
        }

        const ticketsTable = document.getElementById('ticketsTable');
        if (ticketsTable) {
            ticketsTable.addEventListener('click', (e) => {
                if (e.target.classList.contains('view-ticket-btn')) {
                    const ticketId = parseInt(e.target.getAttribute('data-ticket-id'));
                    this.viewTicket(ticketId);
                }
            });
        }
    }

    async loadTickets() {
        const status = document.getElementById('statusFilter')?.value;
        const params = status ? { status } : {};
        
        try {
            const response = await API.maintenance.getTickets(params);
            
            if (response.success) {
                this.renderTickets(response.data);
            } else {
                showAlert(response.message || 'Failed to load tickets', 'danger');
            }
        } catch (error) {
            console.error('Error loading tickets:', error);
            showAlert('Failed to load tickets', 'danger');
        }
    }

    renderTickets(tickets) {
        const tbody = document.getElementById('ticketsTable');
        
        if (tickets.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" class="table-center-text">No tickets found</td></tr>';
            return;
        }
        
        tbody.innerHTML = tickets.map(ticket => `
            <tr>
                <td>${ticket.ticket_number}</td>
                <td>${ticket.machine_name} (${ticket.machine_number})</td>
                <td>${ticket.department_name}</td>
                <td>${ticket.issue_description.substring(0, 50)}...</td>
                <td><span class="badge ${this.getSeverityBadgeClass(ticket.severity)}">${ticket.severity.toUpperCase()}</span></td>
                <td>${createStatusBadge(ticket.status)}</td>
                <td>${ticket.assigned_to_name || 'Unassigned'}</td>
                <td>
                    <button class="btn btn-sm btn-primary view-ticket-btn" data-ticket-id="${ticket.id}">View</button>
                </td>
            </tr>
        `).join('');
    }

    getSeverityBadgeClass(severity) {
        const classes = {
            'critical': 'badge-danger',
            'high': 'badge-warning',
            'medium': 'badge-info',
            'low': 'badge-secondary'
        };
        return classes[severity] || 'badge-secondary';
    }

    async submitTicketForm(e) {
        e.preventDefault();
        
        const formData = {
            issue_description: document.getElementById('issueDescription').value,
            severity: document.getElementById('severity').value,
            notes: document.getElementById('notes').value
        };
        
        try {
            const response = await API.maintenance.createTicket(formData);
            
            if (response.success) {
                showAlert('Maintenance ticket created successfully', 'success');
                hideModal('addTicketModal');
                document.getElementById('ticketForm').reset();
                this.loadTickets();
            } else {
                showAlert(response.message || 'Failed to create ticket', 'danger');
            }
        } catch (error) {
            console.error('Error creating ticket:', error);
            showAlert('Failed to create ticket', 'danger');
        }
    }

    viewTicket(ticketId) {
        window.location.href = `/maintenance/tickets/${ticketId}`;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new MaintenanceTicketsPage();
});
