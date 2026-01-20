class ReplacementTicketsPage {
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
                } else if (e.target.classList.contains('approve-ticket-btn')) {
                    const ticketId = parseInt(e.target.getAttribute('data-ticket-id'));
                    this.approveTicket(ticketId);
                }
            });
        }
    }

    async loadTickets() {
        const status = document.getElementById('statusFilter').value;
        const params = status ? { status } : {};
        
        try {
            const response = await API.defects.getReplacementTickets(params);
            
            if (response.success) {
                const tbody = document.getElementById('ticketsTable');
                tbody.innerHTML = response.data.map(ticket => `
                    <tr>
                        <td>${ticket.ticket_number}</td>
                        <td>${ticket.order_number}</td>
                        <td>${ticket.customer_name}</td>
                        <td>${ticket.department_name}</td>
                        <td>${ticket.quantity_rejected}</td>
                        <td>${ticket.rejection_type}</td>
                        <td>${createStatusBadge(ticket.status)}</td>
                        <td>
                            <button class="btn btn-sm btn-primary view-ticket-btn" data-ticket-id="${ticket.id}">View</button>
                            ${ticket.status === 'pending_approval' ? 
                                `<button class="btn btn-sm btn-success approve-ticket-btn" data-ticket-id="${ticket.id}">Approve</button>` :
                                ''}
                        </td>
                    </tr>
                `).join('');
            }
        } catch (error) {
            console.error('Error loading tickets:', error);
            showAlert('Failed to load tickets', 'danger');
        }
    }

    async approveTicket(id) {
        if (confirm('Are you sure you want to approve this replacement ticket?')) {
            try {
                const response = await API.defects.approveReplacementTicket(id);
                if (response.success) {
                    showAlert('Ticket approved successfully', 'success');
                    this.loadTickets();
                }
            } catch (error) {
                showAlert(error.message || 'Failed to approve ticket', 'danger');
            }
        }
    }

    viewTicket(id) {
        window.location.href = `/defects/replacement-tickets/${id}`;
    }

    async submitTicketForm(event) {
        event.preventDefault();
        
        const data = {
            order_number: document.getElementById('orderNumber').value,
            quantity_rejected: parseInt(document.getElementById('quantityRejected').value),
            rejection_type: document.getElementById('rejectionType').value,
            rejection_reason: document.getElementById('rejectionReason').value
        };
        
        try {
            const response = await API.defects.createReplacementTicket(data);
            
            if (response.success) {
                showAlert('Ticket created successfully', 'success');
                hideModal('addTicketModal');
                resetForm('ticketForm');
                this.loadTickets();
            }
        } catch (error) {
            showAlert(error.message || 'Failed to create ticket', 'danger');
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new ReplacementTicketsPage();
});
