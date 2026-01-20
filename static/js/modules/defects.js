class CustomerReturnsPage {
    constructor() {
        this.allReturns = [];
        this.init();
    }

    init() {
        const user = getCurrentUser();
        if (user) {
            document.getElementById('username').textContent = `${user.first_name} ${user.last_name}`;
        }
        
        this.attachEventListeners();
        this.loadOrders();
        this.filterReturns();
    }

    attachEventListeners() {
        const logoutBtn = document.querySelector('.logout-btn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', () => logout());
        }

        const addReturnBtn = document.querySelector('.add-return-btn');
        if (addReturnBtn) {
            addReturnBtn.addEventListener('click', () => showModal('addReturnModal'));
        }

        const filterReturnType = document.getElementById('filterReturnType');
        if (filterReturnType) {
            filterReturnType.addEventListener('change', () => this.filterReturns());
        }

        const startDate = document.getElementById('startDate');
        if (startDate) {
            startDate.addEventListener('change', () => this.filterReturns());
        }

        const endDate = document.getElementById('endDate');
        if (endDate) {
            endDate.addEventListener('change', () => this.filterReturns());
        }

        const searchReturn = document.getElementById('searchReturn');
        if (searchReturn) {
            searchReturn.addEventListener('input', () => this.filterReturns());
        }

        const orderId = document.getElementById('orderId');
        if (orderId) {
            orderId.addEventListener('change', () => this.loadOrderProducts());
        }

        const returnForm = document.getElementById('returnForm');
        if (returnForm) {
            returnForm.addEventListener('submit', (e) => this.submitReturnForm(e));
        }

        const closeAddModalBtn = document.querySelector('.close-add-return-modal-btn');
        if (closeAddModalBtn) {
            closeAddModalBtn.addEventListener('click', () => hideModal('addReturnModal'));
        }

        const closeViewModalBtn = document.querySelector('.close-view-return-modal-btn');
        if (closeViewModalBtn) {
            closeViewModalBtn.addEventListener('click', () => hideModal('viewReturnModal'));
        }

        const returnsTable = document.getElementById('returnsTable');
        if (returnsTable) {
            returnsTable.addEventListener('click', (e) => {
                if (e.target.classList.contains('view-return-btn')) {
                    const returnId = parseInt(e.target.getAttribute('data-return-id'));
                    this.viewReturn(returnId);
                }
            });
        }
    }

    async filterReturns() {
        const type = document.getElementById('filterReturnType')?.value;
        const startDate = document.getElementById('startDate')?.value;
        const endDate = document.getElementById('endDate')?.value;
        const search = document.getElementById('searchReturn')?.value;

        const params = new URLSearchParams();
        if (type) params.append('return_type', type);
        if (startDate) params.append('start_date', startDate);
        if (endDate) params.append('end_date', endDate);
        if (search) params.append('search', search);

        try {
            const response = await fetch(`/api/defects/customer-returns?${params.toString()}`, {
                headers: getAuthHeaders()
            });
            const data = await response.json();

            if (data.success) {
                this.allReturns = data.data;
                this.renderReturns(data.data);
            }
        } catch (error) {
            console.error('Error loading returns:', error);
            showAlert('Failed to load returns', 'danger');
        }
    }

    renderReturns(returns) {
        const tbody = document.getElementById('returnsTable');
        if (!tbody) return;

        if (returns.length === 0) {
            tbody.innerHTML = '<tr><td colspan="9" class="table-center-text">No returns found</td></tr>';
            return;
        }

        tbody.innerHTML = returns.map(ret => `
            <tr>
                <td>${escapeHtml(ret.return_number)}</td>
                <td>${ret.return_date || '-'}</td>
                <td>${escapeHtml(ret.order_number || '-')}</td>
                <td>${escapeHtml(ret.product_name || '-')}</td>
                <td>${ret.quantity_returned || 0}</td>
                <td><span class="badge badge-${this.getReturnTypeColor(ret.return_type)}">${ret.return_type}</span></td>
                <td>${escapeHtml(ret.return_reason || '-').substring(0, 50)}...</td>
                <td>${escapeHtml(ret.recorded_by || '-')}</td>
                <td>
                    <button class="btn btn-sm btn-secondary view-return-btn" data-return-id="${ret.id}">View</button>
                </td>
            </tr>
        `).join('');
    }

    async loadOrders() {
        try {
            const response = await fetch('/api/orders', {
                headers: getAuthHeaders()
            });
            const data = await response.json();

            if (data.success) {
                const select = document.getElementById('orderId');
                if (select) {
                    select.innerHTML = '<option value="">Select Order</option>' +
                        data.data.map(order => `<option value="${order.id}">${escapeHtml(order.order_number)} - ${escapeHtml(order.customer_name)}</option>`).join('');
                }
            }
        } catch (error) {
            console.error('Error loading orders:', error);
        }
    }

    async loadOrderProducts() {
        const orderId = document.getElementById('orderId').value;
        if (!orderId) return;

        try {
            const response = await fetch(`/api/orders/${orderId}`, {
                headers: getAuthHeaders()
            });
            const data = await response.json();

            if (data.success && data.data.product_id) {
                const productSelect = document.getElementById('productId');
                if (productSelect) {
                    productSelect.innerHTML = `<option value="${data.data.product_id}">${escapeHtml(data.data.product_name)}</option>`;
                }
            }
        } catch (error) {
            console.error('Error loading order products:', error);
        }
    }

    async viewReturn(id) {
        try {
            const response = await fetch(`/api/defects/customer-returns/${id}`, {
                headers: getAuthHeaders()
            });
            const data = await response.json();

            if (data.success) {
                const ret = data.data;
                const detailsDiv = document.getElementById('returnDetails');
                if (detailsDiv) {
                    detailsDiv.innerHTML = `
                        <div class="grid grid-2">
                            <div><strong>Return Number:</strong> ${escapeHtml(ret.return_number)}</div>
                            <div><strong>Return Date:</strong> ${ret.return_date}</div>
                            <div><strong>Order Number:</strong> ${escapeHtml(ret.order_number)}</div>
                            <div><strong>Product:</strong> ${escapeHtml(ret.product_name || 'N/A')}</div>
                            <div><strong>Quantity:</strong> ${ret.quantity_returned}</div>
                            <div><strong>Return Type:</strong> ${ret.return_type}</div>
                        </div>
                        <div class="return-details-section">
                            <strong>Return Reason:</strong>
                            <p>${escapeHtml(ret.return_reason)}</p>
                        </div>
                        ${ret.customer_complaint ? `
                            <div class="return-details-section">
                                <strong>Customer Complaint:</strong>
                                <p>${escapeHtml(ret.customer_complaint)}</p>
                            </div>
                        ` : ''}
                        ${ret.notes ? `
                            <div class="return-details-section">
                                <strong>Notes:</strong>
                                <p>${escapeHtml(ret.notes)}</p>
                            </div>
                        ` : ''}
                        <div class="return-details-section">
                            <strong>Recorded By:</strong> ${escapeHtml(ret.recorded_by)}
                        </div>
                    `;
                }
                showModal('viewReturnModal');
            }
        } catch (error) {
            console.error('Error loading return details:', error);
            showAlert('Failed to load return details', 'danger');
        }
    }

    async submitReturnForm(e) {
        e.preventDefault();

        const formData = {
            return_number: document.getElementById('returnNumber').value,
            order_id: parseInt(document.getElementById('orderId').value),
            product_id: document.getElementById('productId').value ? parseInt(document.getElementById('productId').value) : null,
            quantity_returned: parseInt(document.getElementById('quantityReturned').value),
            return_date: document.getElementById('returnDate').value,
            return_type: document.getElementById('returnType').value,
            return_reason: document.getElementById('returnReason').value,
            customer_complaint: document.getElementById('customerComplaint').value,
            notes: document.getElementById('notes').value
        };

        try {
            const response = await fetch('/api/defects/customer-returns', {
                method: 'POST',
                headers: getAuthHeaders(),
                body: JSON.stringify(formData)
            });
            const data = await response.json();

            if (data.success) {
                showAlert('Return recorded successfully', 'success');
                hideModal('addReturnModal');
                this.filterReturns();
                document.getElementById('returnForm').reset();
            } else {
                showAlert(data.error || 'Failed to record return', 'danger');
            }
        } catch (error) {
            console.error('Error recording return:', error);
            showAlert('Failed to record return', 'danger');
        }
    }

    getReturnTypeColor(type) {
        const colors = {
            defect: 'danger',
            wrong_item: 'warning',
            damage: 'danger',
            other: 'secondary'
        };
        return colors[type] || 'secondary';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new CustomerReturnsPage();
});
