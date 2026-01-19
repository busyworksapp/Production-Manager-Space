let allReturns = [];

async function filterReturns() {
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
            allReturns = data.data;
            renderReturns(data.data);
        }
    } catch (error) {
        console.error('Error loading returns:', error);
        showNotification('Failed to load returns', 'error');
    }
}

function renderReturns(returns) {
    const tbody = document.getElementById('returnsTable');
    if (!tbody) return;

    if (returns.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" style="text-align: center;">No returns found</td></tr>';
        return;
    }

    tbody.innerHTML = returns.map(ret => `
        <tr>
            <td>${escapeHtml(ret.return_number)}</td>
            <td>${ret.return_date || '-'}</td>
            <td>${escapeHtml(ret.order_number || '-')}</td>
            <td>${escapeHtml(ret.product_name || '-')}</td>
            <td>${ret.quantity_returned || 0}</td>
            <td><span class="badge badge-${getReturnTypeColor(ret.return_type)}">${ret.return_type}</span></td>
            <td>${escapeHtml(ret.return_reason || '-').substring(0, 50)}...</td>
            <td>${escapeHtml(ret.recorded_by || '-')}</td>
            <td>
                <button class="btn btn-sm btn-secondary" onclick="viewReturn(${ret.id})">View</button>
            </td>
        </tr>
    `).join('');
}

async function loadOrders() {
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

async function loadOrderProducts() {
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

async function viewReturn(id) {
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
                    <div style="margin-top: 1rem;">
                        <strong>Return Reason:</strong>
                        <p>${escapeHtml(ret.return_reason)}</p>
                    </div>
                    ${ret.customer_complaint ? `
                        <div style="margin-top: 1rem;">
                            <strong>Customer Complaint:</strong>
                            <p>${escapeHtml(ret.customer_complaint)}</p>
                        </div>
                    ` : ''}
                    ${ret.notes ? `
                        <div style="margin-top: 1rem;">
                            <strong>Notes:</strong>
                            <p>${escapeHtml(ret.notes)}</p>
                        </div>
                    ` : ''}
                    <div style="margin-top: 1rem;">
                        <strong>Recorded By:</strong> ${escapeHtml(ret.recorded_by)}
                    </div>
                `;
            }
            showModal('viewReturnModal');
        }
    } catch (error) {
        console.error('Error loading return details:', error);
        showNotification('Failed to load return details', 'error');
    }
}

document.getElementById('returnForm')?.addEventListener('submit', async (e) => {
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
            showNotification('Return recorded successfully', 'success');
            hideModal('addReturnModal');
            filterReturns();
            document.getElementById('returnForm').reset();
        } else {
            showNotification(data.error || 'Failed to record return', 'error');
        }
    } catch (error) {
        console.error('Error recording return:', error);
        showNotification('Failed to record return', 'error');
    }
});

document.addEventListener('DOMContentLoaded', () => {
    loadOrders();
    filterReturns();
});

function getReturnTypeColor(type) {
    const colors = {
        defect: 'danger',
        wrong_item: 'warning',
        damage: 'danger',
        other: 'secondary'
    };
    return colors[type] || 'secondary';
}
