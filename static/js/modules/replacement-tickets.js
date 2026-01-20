class ReplacementTicketsPage {
    constructor() {
        this.currentOrderItems = [];
        this.init();
    }

    init() {
        const user = getCurrentUser();
        if (user) {
            document.getElementById('username').textContent = `${user.first_name} ${user.last_name}`;
        }
        
        this.attachEventListeners();
        this.loadOrders();
        this.loadDepartments();
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

        const orderId = document.getElementById('orderId');
        if (orderId) {
            orderId.addEventListener('change', () => this.handleOrderChange());
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

    async loadOrders() {
        try {
            const response = await API.orders.getAll();
            if (response.success) {
                const select = document.getElementById('orderId');
                if (select) {
                    select.innerHTML = '<option value="">Select Order...</option>' +
                        response.data.map(order => 
                            `<option value="${order.id}">${escapeHtml(order.order_number)} - ${escapeHtml(order.customer_name)}</option>`
                        ).join('');
                }
            }
        } catch (error) {
            console.error('Error loading orders:', error);
        }
    }

    async loadDepartments() {
        try {
            const response = await API.departments.getAll();
            if (response.success) {
                const select = document.getElementById('departmentId');
                if (select) {
                    select.innerHTML = '<option value="">Select Department...</option>' +
                        response.data.map(dept => 
                            `<option value="${dept.id}">${escapeHtml(dept.name)}</option>`
                        ).join('');
                }
            }
        } catch (error) {
            console.error('Error loading departments:', error);
        }
    }

    async handleOrderChange() {
        const orderId = document.getElementById('orderId').value;
        const orderItemGroup = document.getElementById('orderItemGroup');
        const orderItemSelect = document.getElementById('orderItemId');
        
        if (!orderId) {
            orderItemGroup.style.display = 'none';
            orderItemSelect.innerHTML = '<option value="">Select Item...</option>';
            this.currentOrderItems = [];
            return;
        }
        
        try {
            const response = await API.orders.getItems(orderId);
            if (response.success && response.data && response.data.length > 0) {
                this.currentOrderItems = response.data;
                
                if (response.data.length > 1) {
                    orderItemGroup.style.display = 'block';
                    orderItemSelect.required = true;
                    orderItemSelect.innerHTML = '<option value="">Select Item...</option>' +
                        response.data.map(item => 
                            `<option value="${item.id}">${escapeHtml(item.product_name)} - Qty: ${item.quantity}</option>`
                        ).join('');
                } else {
                    orderItemGroup.style.display = 'none';
                    orderItemSelect.required = false;
                    orderItemSelect.value = response.data[0].id;
                }
            } else {
                orderItemGroup.style.display = 'none';
                orderItemSelect.innerHTML = '<option value="">Select Item...</option>';
                this.currentOrderItems = [];
            }
        } catch (error) {
            console.error('Error loading order items:', error);
            showAlert('Failed to load order items', 'danger');
        }
    }

    async loadTickets() {
        const status = document.getElementById('statusFilter').value;
        const params = status ? { status } : {};
        
        try {
            const response = await API.defects.getReplacementTickets(params);
            
            if (response.success) {
                const tbody = document.getElementById('ticketsTable');
                tbody.innerHTML = response.data.map(ticket => {
                    const costImpact = ticket.material_cost || ticket.cost_impact || 0;
                    return `
                        <tr>
                            <td>${ticket.ticket_number}</td>
                            <td>${ticket.order_number}</td>
                            <td>${ticket.customer_name || '-'}</td>
                            <td>${ticket.product_name || '-'}</td>
                            <td>${ticket.department_name || '-'}</td>
                            <td>${ticket.quantity_rejected}</td>
                            <td>${formatCurrency(costImpact)}</td>
                            <td><span class="badge badge-secondary">${ticket.rejection_type}</span></td>
                            <td>${createStatusBadge(ticket.status)}</td>
                            <td>
                                <button class="btn btn-sm btn-primary view-ticket-btn" data-ticket-id="${ticket.id}">View</button>
                                ${ticket.status === 'pending_approval' ? 
                                    `<button class="btn btn-sm btn-success approve-ticket-btn" data-ticket-id="${ticket.id}">Approve</button>` :
                                    ''}
                            </td>
                        </tr>
                    `;
                }).join('');
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
        
        const orderId = document.getElementById('orderId').value;
        const orderItemId = document.getElementById('orderItemId').value;
        const departmentId = document.getElementById('departmentId').value;
        
        if (!orderId) {
            showAlert('Please select an order', 'danger');
            return;
        }
        
        if (!departmentId) {
            showAlert('Please select a department', 'danger');
            return;
        }
        
        const data = {
            order_id: parseInt(orderId),
            department_id: parseInt(departmentId),
            quantity_rejected: parseInt(document.getElementById('quantityRejected').value),
            rejection_type: document.getElementById('rejectionType').value,
            rejection_reason: document.getElementById('rejectionReason').value,
            notes: document.getElementById('notes').value || null
        };
        
        if (orderItemId) {
            data.order_item_id = parseInt(orderItemId);
        }
        
        try {
            const response = await API.defects.createReplacementTicket(data);
            
            if (response.success) {
                const costMsg = response.data.material_cost > 0 
                    ? ` (Estimated cost: ${formatCurrency(response.data.material_cost)})`
                    : '';
                showAlert(`Ticket created successfully${costMsg}`, 'success');
                hideModal('addTicketModal');
                document.getElementById('ticketForm').reset();
                this.currentOrderItems = [];
                document.getElementById('orderItemGroup').style.display = 'none';
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
