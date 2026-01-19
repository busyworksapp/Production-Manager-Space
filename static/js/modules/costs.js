let allLaborCosts = [];
let allOverheadCosts = [];
let allProductionCosts = [];

async function loadLaborCosts() {
    try {
        const response = await fetch('/api/cost-models/labor', {
            headers: getAuthHeaders()
        });
        const data = await response.json();

        if (data.success) {
            allLaborCosts = data.data;
            renderLaborCosts(data.data);
        }
    } catch (error) {
        console.error('Error loading labor costs:', error);
        showNotification('Failed to load labor costs', 'error');
    }
}

async function loadOverheadCosts() {
    try {
        const response = await fetch('/api/cost-models/overhead', {
            headers: getAuthHeaders()
        });
        const data = await response.json();

        if (data.success) {
            allOverheadCosts = data.data;
            renderOverheadCosts(data.data);
        }
    } catch (error) {
        console.error('Error loading overhead costs:', error);
    }
}

async function filterProductionCosts() {
    const order = document.getElementById('filterOrder')?.value;
    const startDate = document.getElementById('startDate')?.value;
    const endDate = document.getElementById('endDate')?.value;

    const params = new URLSearchParams();
    if (order) params.append('order_number', order);
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);

    try {
        const response = await fetch(`/api/cost-models/production-costs?${params.toString()}`, {
            headers: getAuthHeaders()
        });
        const data = await response.json();

        if (data.success) {
            allProductionCosts = data.data;
            renderProductionCosts(data.data);
        }
    } catch (error) {
        console.error('Error loading production costs:', error);
    }
}

function renderLaborCosts(costs) {
    const tbody = document.getElementById('laborCostsTable');
    if (!tbody) return;

    if (costs.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" style="text-align: center;">No labor costs found</td></tr>';
        return;
    }

    tbody.innerHTML = costs.map(cost => `
        <tr>
            <td>${escapeHtml(cost.department_name || '-')}</td>
            <td>${escapeHtml(cost.position)}</td>
            <td>$${parseFloat(cost.hourly_rate).toFixed(2)}</td>
            <td>${cost.overtime_rate ? '$' + parseFloat(cost.overtime_rate).toFixed(2) : '-'}</td>
            <td>${cost.benefits_percentage ? parseFloat(cost.benefits_percentage).toFixed(2) + '%' : '-'}</td>
            <td>${cost.effective_from || '-'}</td>
            <td>${cost.effective_to || 'Current'}</td>
            <td><span class="badge badge-${cost.is_active ? 'success' : 'secondary'}">${cost.is_active ? 'Active' : 'Inactive'}</span></td>
            <td>
                <button class="btn btn-sm btn-secondary" onclick="editLaborCost(${cost.id})">Edit</button>
            </td>
        </tr>
    `).join('');
}

function renderOverheadCosts(costs) {
    const tbody = document.getElementById('overheadCostsTable');
    if (!tbody) return;

    if (costs.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" style="text-align: center;">No overhead costs found</td></tr>';
        return;
    }

    tbody.innerHTML = costs.map(cost => `
        <tr>
            <td>${escapeHtml(cost.department_name || '-')}</td>
            <td>${escapeHtml(cost.cost_category)}</td>
            <td>${escapeHtml(cost.cost_type)}</td>
            <td>${escapeHtml(cost.allocation_method)}</td>
            <td>$${parseFloat(cost.cost_amount).toFixed(2)}</td>
            <td>${cost.effective_from || '-'}</td>
            <td>${cost.effective_to || 'Current'}</td>
            <td><span class="badge badge-${cost.is_active ? 'success' : 'secondary'}">${cost.is_active ? 'Active' : 'Inactive'}</span></td>
            <td>
                <button class="btn btn-sm btn-secondary" onclick="editOverheadCost(${cost.id})">Edit</button>
            </td>
        </tr>
    `).join('');
}

function renderProductionCosts(costs) {
    const tbody = document.getElementById('productionCostsTable');
    if (!tbody) return;

    if (costs.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align: center;">No production costs found</td></tr>';
        return;
    }

    tbody.innerHTML = costs.map(cost => `
        <tr>
            <td>${escapeHtml(cost.order_number || '-')}</td>
            <td>$${parseFloat(cost.material_cost || 0).toFixed(2)}</td>
            <td>$${parseFloat(cost.labor_cost || 0).toFixed(2)}</td>
            <td>$${parseFloat(cost.overhead_cost || 0).toFixed(2)}</td>
            <td><strong>$${parseFloat(cost.total_cost || 0).toFixed(2)}</strong></td>
            <td>${cost.calculated_at ? new Date(cost.calculated_at).toLocaleString() : '-'}</td>
            <td>
                <button class="btn btn-sm btn-secondary" onclick="viewCostDetails(${cost.id})">Details</button>
            </td>
        </tr>
    `).join('');
}

async function loadDepartments() {
    try {
        const response = await fetch('/api/departments', {
            headers: getAuthHeaders()
        });
        const data = await response.json();

        if (data.success) {
            const selects = ['departmentId', 'overheadDepartmentId'];
            selects.forEach(selectId => {
                const select = document.getElementById(selectId);
                if (select) {
                    select.innerHTML = '<option value="">Select Department</option>' +
                        data.data.map(dept => `<option value="${dept.id}">${escapeHtml(dept.name)}</option>`).join('');
                }
            });
        }
    } catch (error) {
        console.error('Error loading departments:', error);
    }
}

document.getElementById('laborCostForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();

    const formData = {
        department_id: parseInt(document.getElementById('departmentId').value),
        position: document.getElementById('position').value,
        hourly_rate: parseFloat(document.getElementById('hourlyRate').value),
        overtime_rate: document.getElementById('overtimeRate').value ? parseFloat(document.getElementById('overtimeRate').value) : null,
        benefits_percentage: document.getElementById('benefitsPercentage').value ? parseFloat(document.getElementById('benefitsPercentage').value) : null,
        effective_from: document.getElementById('effectiveFrom').value,
        effective_to: document.getElementById('effectiveTo').value || null,
        is_active: document.getElementById('isActive').checked
    };

    try {
        const response = await fetch('/api/cost-models/labor', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(formData)
        });
        const data = await response.json();

        if (data.success) {
            showNotification('Labor cost created successfully', 'success');
            hideModal('addLaborCostModal');
            loadLaborCosts();
            document.getElementById('laborCostForm').reset();
        } else {
            showNotification(data.error || 'Failed to create labor cost', 'error');
        }
    } catch (error) {
        console.error('Error creating labor cost:', error);
        showNotification('Failed to create labor cost', 'error');
    }
});

document.getElementById('overheadCostForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();

    const formData = {
        department_id: parseInt(document.getElementById('overheadDepartmentId').value),
        cost_category: document.getElementById('costCategory').value,
        cost_description: document.getElementById('costDescription').value,
        cost_type: document.getElementById('costType').value,
        allocation_method: document.getElementById('allocationMethod').value,
        cost_amount: parseFloat(document.getElementById('costAmount').value),
        effective_from: document.getElementById('overheadEffectiveFrom').value,
        effective_to: document.getElementById('overheadEffectiveTo').value || null,
        is_active: document.getElementById('overheadIsActive').checked
    };

    try {
        const response = await fetch('/api/cost-models/overhead', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(formData)
        });
        const data = await response.json();

        if (data.success) {
            showNotification('Overhead cost created successfully', 'success');
            hideModal('addOverheadCostModal');
            loadOverheadCosts();
            document.getElementById('overheadCostForm').reset();
        } else {
            showNotification(data.error || 'Failed to create overhead cost', 'error');
        }
    } catch (error) {
        console.error('Error creating overhead cost:', error);
        showNotification('Failed to create overhead cost', 'error');
    }
});

document.addEventListener('DOMContentLoaded', () => {
    loadDepartments();
    loadLaborCosts();
    loadOverheadCosts();
    filterProductionCosts();
});
