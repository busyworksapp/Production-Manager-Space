let allBoms = [];
let bomItemCount = 0;

async function filterBoms() {
    const product = document.getElementById('filterProduct')?.value;
    const status = document.getElementById('filterStatus')?.value;
    const search = document.getElementById('searchBom')?.value;

    const params = new URLSearchParams();
    if (product) params.append('product_id', product);
    if (status) params.append('is_active', status === 'active' ? 'true' : 'false');
    if (search) params.append('search', search);

    try {
        const response = await fetch(`/api/finance/bom?${params.toString()}`, {
            headers: getAuthHeaders()
        });
        const data = await response.json();

        if (data.success) {
            allBoms = data.data;
            renderBoms(data.data);
        }
    } catch (error) {
        console.error('Error loading BOMs:', error);
        showNotification('Failed to load BOMs', 'error');
    }
}

function renderBoms(boms) {
    const tbody = document.getElementById('bomsTable');
    if (!tbody) return;

    if (boms.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" style="text-align: center;">No BOMs found</td></tr>';
        return;
    }

    tbody.innerHTML = boms.map(bom => `
        <tr>
            <td>${escapeHtml(bom.product_name || '-')}</td>
            <td>${escapeHtml(bom.version)}</td>
            <td>${bom.effective_date || '-'}</td>
            <td>${bom.total_cost ? '$' + parseFloat(bom.total_cost).toFixed(2) : '-'}</td>
            <td>${bom.items_count || 0}</td>
            <td><span class="badge badge-${bom.is_active ? 'success' : 'secondary'}">${bom.is_active ? 'Active' : 'Inactive'}</span></td>
            <td>${escapeHtml(bom.created_by || '-')}</td>
            <td>
                <button class="btn btn-sm btn-secondary" onclick="viewBom(${bom.id})">View</button>
            </td>
        </tr>
    `).join('');
}

async function loadProducts() {
    try {
        const response = await fetch('/api/products', {
            headers: getAuthHeaders()
        });
        const data = await response.json();

        if (data.success) {
            const selects = ['productId', 'filterProduct'];
            selects.forEach(selectId => {
                const select = document.getElementById(selectId);
                if (select) {
                    const hasFilter = selectId.startsWith('filter');
                    select.innerHTML = (hasFilter ? '<option value="">All Products</option>' : '<option value="">Select Product</option>') +
                        data.data.map(prod => `<option value="${prod.id}">${escapeHtml(prod.product_name)} (${escapeHtml(prod.product_code)})</option>`).join('');
                }
            });
        }
    } catch (error) {
        console.error('Error loading products:', error);
    }
}

function addBomItem() {
    bomItemCount++;
    const container = document.getElementById('bomItemsContainer');
    if (!container) return;

    const itemHtml = `
        <div class="bom-item card" data-item-id="${bomItemCount}" style="padding: 1rem; margin-bottom: 1rem; background: var(--color-bg-main);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                <strong>Item #${bomItemCount}</strong>
                <button type="button" class="btn btn-sm btn-danger" onclick="removeBomItem(${bomItemCount})">Remove</button>
            </div>
            <div class="grid grid-2">
                <div class="form-group">
                    <label class="form-label">Item Code*</label>
                    <input type="text" class="form-input item-code" required>
                </div>
                <div class="form-group">
                    <label class="form-label">Item Description*</label>
                    <input type="text" class="form-input item-description" required>
                </div>
            </div>
            <div class="grid grid-3">
                <div class="form-group">
                    <label class="form-label">Quantity*</label>
                    <input type="number" step="0.0001" class="form-input item-quantity" required oninput="calculateItemCost(${bomItemCount})">
                </div>
                <div class="form-group">
                    <label class="form-label">Unit Cost*</label>
                    <input type="number" step="0.01" class="form-input item-unit-cost" required oninput="calculateItemCost(${bomItemCount})">
                </div>
                <div class="form-group">
                    <label class="form-label">Total Cost</label>
                    <input type="text" class="form-input item-total-cost" readonly>
                </div>
            </div>
            <div class="grid grid-2">
                <div class="form-group">
                    <label class="form-label">Unit of Measure*</label>
                    <input type="text" class="form-input item-uom" required placeholder="e.g., pcs, kg, m">
                </div>
                <div class="form-group">
                    <label class="form-label">Material Type</label>
                    <input type="text" class="form-input item-material-type">
                </div>
            </div>
        </div>
    `;

    container.insertAdjacentHTML('beforeend', itemHtml);
}

function removeBomItem(itemId) {
    const item = document.querySelector(`.bom-item[data-item-id="${itemId}"]`);
    if (item) {
        item.remove();
        calculateTotalBomCost();
    }
}

function calculateItemCost(itemId) {
    const item = document.querySelector(`.bom-item[data-item-id="${itemId}"]`);
    if (!item) return;

    const qty = parseFloat(item.querySelector('.item-quantity').value) || 0;
    const unitCost = parseFloat(item.querySelector('.item-unit-cost').value) || 0;
    const totalCost = qty * unitCost;

    item.querySelector('.item-total-cost').value = totalCost.toFixed(2);
    calculateTotalBomCost();
}

function calculateTotalBomCost() {
    const items = document.querySelectorAll('.bom-item');
    let total = 0;

    items.forEach(item => {
        const itemTotal = parseFloat(item.querySelector('.item-total-cost').value) || 0;
        total += itemTotal;
    });

    const totalSpan = document.getElementById('totalBomCost');
    if (totalSpan) {
        totalSpan.textContent = total.toFixed(2);
    }
}

async function viewBom(id) {
    try {
        const response = await fetch(`/api/finance/bom/${id}`, {
            headers: getAuthHeaders()
        });
        const data = await response.json();

        if (data.success) {
            const bom = data.data;
            const detailsDiv = document.getElementById('bomDetails');
            if (detailsDiv) {
                detailsDiv.innerHTML = `
                    <div class="grid grid-2">
                        <div><strong>Product:</strong> ${escapeHtml(bom.product_name)}</div>
                        <div><strong>Version:</strong> ${escapeHtml(bom.version)}</div>
                        <div><strong>Effective Date:</strong> ${bom.effective_date}</div>
                        <div><strong>Status:</strong> <span class="badge badge-${bom.is_active ? 'success' : 'secondary'}">${bom.is_active ? 'Active' : 'Inactive'}</span></div>
                    </div>
                    ${bom.notes ? `<div style="margin-top: 1rem;"><strong>Notes:</strong><p>${escapeHtml(bom.notes)}</p></div>` : ''}
                    <div style="margin-top: 1.5rem;">
                        <strong>BOM Items:</strong>
                        <table class="table" style="margin-top: 0.5rem;">
                            <thead>
                                <tr>
                                    <th>Item Code</th>
                                    <th>Description</th>
                                    <th>Quantity</th>
                                    <th>UOM</th>
                                    <th>Unit Cost</th>
                                    <th>Total Cost</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${bom.items.map(item => `
                                    <tr>
                                        <td>${escapeHtml(item.item_code)}</td>
                                        <td>${escapeHtml(item.item_description)}</td>
                                        <td>${item.quantity_per_unit}</td>
                                        <td>${escapeHtml(item.unit_of_measure)}</td>
                                        <td>$${parseFloat(item.unit_cost).toFixed(2)}</td>
                                        <td>$${parseFloat(item.total_cost).toFixed(2)}</td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                    <div style="margin-top: 1rem; text-align: right;">
                        <strong>Total BOM Cost: $${bom.total_cost ? parseFloat(bom.total_cost).toFixed(2) : '0.00'}</strong>
                    </div>
                `;
            }
            showModal('viewBomModal');
        }
    } catch (error) {
        console.error('Error loading BOM details:', error);
        showNotification('Failed to load BOM details', 'error');
    }
}

document.getElementById('bomForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();

    const items = [];
    document.querySelectorAll('.bom-item').forEach(item => {
        items.push({
            item_code: item.querySelector('.item-code').value,
            item_description: item.querySelector('.item-description').value,
            quantity_per_unit: parseFloat(item.querySelector('.item-quantity').value),
            unit_cost: parseFloat(item.querySelector('.item-unit-cost').value),
            unit_of_measure: item.querySelector('.item-uom').value,
            material_type: item.querySelector('.item-material-type').value || null
        });
    });

    const formData = {
        product_id: parseInt(document.getElementById('productId').value),
        version: document.getElementById('version').value,
        effective_date: document.getElementById('effectiveDate').value,
        is_active: document.getElementById('isActive').checked,
        notes: document.getElementById('notes').value,
        items: items
    };

    try {
        const response = await fetch('/api/finance/bom', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(formData)
        });
        const data = await response.json();

        if (data.success) {
            showNotification('BOM created successfully', 'success');
            hideModal('addBomModal');
            filterBoms();
            document.getElementById('bomForm').reset();
            document.getElementById('bomItemsContainer').innerHTML = '';
            bomItemCount = 0;
        } else {
            showNotification(data.error || 'Failed to create BOM', 'error');
        }
    } catch (error) {
        console.error('Error creating BOM:', error);
        showNotification('Failed to create BOM', 'error');
    }
});

document.addEventListener('DOMContentLoaded', () => {
    loadProducts();
    filterBoms();
});
