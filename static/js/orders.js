let currentOrderId = null;
let orderItems = [];
let productionPath = [];
let allProducts = [];
let allDepartments = [];
let allStages = [];

async function loadOrdersPage() {
    const user = getCurrentUser();
    if (user) {
        document.getElementById('username').textContent = `${user.first_name} ${user.last_name}`;
    }
    
    await Promise.all([loadProducts(), loadDepartments(), loadStages()]);
    loadOrders();
}

async function loadProducts() {
    try {
        const response = await API.products.getAll();
        if (response.success) {
            allProducts = response.data;
        }
    } catch (error) {
        console.error('Error loading products:', error);
    }
}

async function loadDepartments() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/departments`, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        });
        const data = await response.json();
        if (data.success) {
            allDepartments = data.data;
        }
    } catch (error) {
        console.error('Error loading departments:', error);
    }
}

async function loadStages() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/departments/stages`, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        });
        const data = await response.json();
        if (data.success) {
            allStages = data.data;
        }
    } catch (error) {
        console.error('Error loading stages:', error);
    }
}

async function loadOrders() {
    const status = document.getElementById('statusFilter').value;
    const params = status ? { status } : {};
    
    try {
        const response = await API.orders.getAll(params);
        
        if (response.success) {
            const tbody = document.getElementById('ordersTable');
            tbody.innerHTML = response.data.map(order => `
                <tr>
                    <td>${order.order_number}</td>
                    <td>${order.customer_name}</td>
                    <td>${order.product_name || 'Multiple Items'}</td>
                    <td>${order.quantity}</td>
                    <td>${formatCurrency(order.order_value)}</td>
                    <td>
                        Start: ${formatDate(order.start_date)}<br>
                        End: ${formatDate(order.end_date)}
                    </td>
                    <td>${createStatusBadge(order.status)}</td>
                    <td>
                        <button class="btn btn-sm btn-primary" onclick="viewOrder(${order.id})">View</button>
                        <button class="btn btn-sm btn-info" onclick="manageOrderItems(${order.id})">Items</button>
                        <button class="btn btn-sm btn-warning" onclick="manageProductionPath(${order.id})">Path</button>
                        <button class="btn btn-sm btn-success" onclick="scheduleOrder(${order.id})">Schedule</button>
                    </td>
                </tr>
            `).join('');
        }
    } catch (error) {
        console.error('Error loading orders:', error);
        showAlert('Failed to load orders', 'danger');
    }
}

async function manageOrderItems(orderId) {
    currentOrderId = orderId;
    
    try {
        const response = await API.orders.getItems(orderId);
        if (response.success) {
            orderItems = response.data;
            renderOrderItems();
            showModal('orderItemsModal');
        }
    } catch (error) {
        showAlert('Failed to load order items', 'danger');
    }
}

function renderOrderItems() {
    const tbody = document.getElementById('orderItemsTable');
    if (orderItems.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align: center;">No items added yet</td></tr>';
        return;
    }
    
    tbody.innerHTML = orderItems.map((item, idx) => `
        <tr>
            <td>${idx + 1}</td>
            <td>${item.product_name || item.product_code}</td>
            <td>${item.quantity}</td>
            <td>${formatCurrency(item.unit_price)}</td>
            <td>${formatCurrency(item.quantity * (item.unit_price || 0))}</td>
            <td>
                <button class="btn btn-sm btn-primary" onclick="editOrderItem(${item.id})">Edit</button>
                <button class="btn btn-sm btn-danger" onclick="deleteOrderItem(${item.id})">Delete</button>
            </td>
        </tr>
    `).join('');
}

function showAddItemForm() {
    document.getElementById('itemForm').reset();
    document.getElementById('itemFormTitle').textContent = 'Add Item';
    document.getElementById('itemId').value = '';
    
    const productSelect = document.getElementById('itemProductId');
    productSelect.innerHTML = '<option value="">Select Product</option>' + 
        allProducts.map(p => `<option value="${p.id}">${p.product_name} (${p.product_code})</option>`).join('');
    
    document.getElementById('itemFormContainer').style.display = 'block';
}

async function editOrderItem(itemId) {
    const item = orderItems.find(i => i.id === itemId);
    if (!item) return;
    
    document.getElementById('itemFormTitle').textContent = 'Edit Item';
    document.getElementById('itemId').value = item.id;
    document.getElementById('itemProductId').value = item.product_id;
    document.getElementById('itemQuantity').value = item.quantity;
    document.getElementById('itemUnitPrice').value = item.unit_price || '';
    document.getElementById('itemSpecifications').value = item.specifications || '';
    
    const productSelect = document.getElementById('itemProductId');
    productSelect.innerHTML = '<option value="">Select Product</option>' + 
        allProducts.map(p => `<option value="${p.id}" ${p.id === item.product_id ? 'selected' : ''}>${p.product_name} (${p.product_code})</option>`).join('');
    
    document.getElementById('itemFormContainer').style.display = 'block';
}

function cancelItemForm() {
    document.getElementById('itemFormContainer').style.display = 'none';
    document.getElementById('itemForm').reset();
}

async function saveOrderItem(event) {
    event.preventDefault();
    
    const itemId = document.getElementById('itemId').value;
    const data = {
        product_id: parseInt(document.getElementById('itemProductId').value),
        quantity: parseInt(document.getElementById('itemQuantity').value),
        unit_price: parseFloat(document.getElementById('itemUnitPrice').value) || null,
        specifications: document.getElementById('itemSpecifications').value
    };
    
    try {
        let response;
        if (itemId) {
            response = await API.orders.updateItem(currentOrderId, parseInt(itemId), data);
        } else {
            response = await API.orders.addItem(currentOrderId, data);
        }
        
        if (response.success) {
            showAlert(itemId ? 'Item updated successfully' : 'Item added successfully', 'success');
            cancelItemForm();
            
            const refreshResponse = await API.orders.getItems(currentOrderId);
            if (refreshResponse.success) {
                orderItems = refreshResponse.data;
                renderOrderItems();
            }
        }
    } catch (error) {
        showAlert(error.message || 'Failed to save item', 'danger');
    }
}

async function deleteOrderItem(itemId) {
    if (!confirm('Are you sure you want to delete this item?')) return;
    
    try {
        const response = await API.orders.deleteItem(currentOrderId, itemId);
        if (response.success) {
            showAlert('Item deleted successfully', 'success');
            
            const refreshResponse = await API.orders.getItems(currentOrderId);
            if (refreshResponse.success) {
                orderItems = refreshResponse.data;
                renderOrderItems();
            }
        }
    } catch (error) {
        showAlert('Failed to delete item', 'danger');
    }
}

async function manageProductionPath(orderId) {
    currentOrderId = orderId;
    
    try {
        const response = await API.orders.getProductionPath(orderId);
        if (response.success) {
            productionPath = response.data;
            renderProductionPath();
            showModal('productionPathModal');
        }
    } catch (error) {
        showAlert('Failed to load production path', 'danger');
    }
}

function renderProductionPath() {
    const tbody = document.getElementById('productionPathTable');
    if (productionPath.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align: center;">No production path configured</td></tr>';
        return;
    }
    
    tbody.innerHTML = productionPath.map((step, idx) => `
        <tr>
            <td>${step.path_sequence}</td>
            <td>${step.department_name}</td>
            <td>${step.stage_name || 'Any Stage'}</td>
            <td>${step.estimated_duration_minutes || 'N/A'} min</td>
            <td>${step.is_required ? 'Yes' : 'No'}</td>
            <td>
                <button class="btn btn-sm btn-primary" onclick="editPathStep(${step.id})">Edit</button>
                <button class="btn btn-sm btn-danger" onclick="deletePathStep(${step.id})">Delete</button>
                ${idx > 0 ? `<button class="btn btn-sm btn-secondary" onclick="movePathStep(${idx}, 'up')">↑</button>` : ''}
                ${idx < productionPath.length - 1 ? `<button class="btn btn-sm btn-secondary" onclick="movePathStep(${idx}, 'down')">↓</button>` : ''}
            </td>
        </tr>
    `).join('');
}

function showAddPathStepForm() {
    document.getElementById('pathStepForm').reset();
    document.getElementById('pathStepFormTitle').textContent = 'Add Production Step';
    document.getElementById('pathStepId').value = '';
    
    const deptSelect = document.getElementById('pathDepartmentId');
    deptSelect.innerHTML = '<option value="">Select Department</option>' + 
        allDepartments.map(d => `<option value="${d.id}">${d.name}</option>`).join('');
    
    document.getElementById('pathStepFormContainer').style.display = 'block';
}

async function editPathStep(stepId) {
    const step = productionPath.find(s => s.id === stepId);
    if (!step) return;
    
    document.getElementById('pathStepFormTitle').textContent = 'Edit Production Step';
    document.getElementById('pathStepId').value = step.id;
    document.getElementById('pathDepartmentId').value = step.department_id;
    
    await updateStageOptions(step.department_id, step.stage_id);
    
    document.getElementById('pathEstimatedDuration').value = step.estimated_duration_minutes || '';
    document.getElementById('pathIsRequired').checked = step.is_required;
    document.getElementById('pathNotes').value = step.notes || '';
    
    document.getElementById('pathStepFormContainer').style.display = 'block';
}

async function updateStageOptions(departmentId, selectedStageId = null) {
    const stageSelect = document.getElementById('pathStageId');
    const filteredStages = allStages.filter(s => s.department_id == departmentId);
    
    stageSelect.innerHTML = '<option value="">Any Stage</option>' + 
        filteredStages.map(s => `<option value="${s.id}" ${s.id === selectedStageId ? 'selected' : ''}>${s.stage_name}</option>`).join('');
}

function cancelPathStepForm() {
    document.getElementById('pathStepFormContainer').style.display = 'none';
    document.getElementById('pathStepForm').reset();
}

async function savePathStep(event) {
    event.preventDefault();
    
    const stepId = document.getElementById('pathStepId').value;
    const data = {
        department_id: parseInt(document.getElementById('pathDepartmentId').value),
        stage_id: document.getElementById('pathStageId').value ? parseInt(document.getElementById('pathStageId').value) : null,
        estimated_duration_minutes: parseInt(document.getElementById('pathEstimatedDuration').value) || null,
        is_required: document.getElementById('pathIsRequired').checked,
        notes: document.getElementById('pathNotes').value
    };
    
    try {
        let response;
        if (stepId) {
            response = await API.orders.updatePathStep(currentOrderId, parseInt(stepId), data);
        } else {
            const paths = [...productionPath, data];
            response = await API.orders.setProductionPath(currentOrderId, { paths });
        }
        
        if (response.success) {
            showAlert(stepId ? 'Step updated successfully' : 'Step added successfully', 'success');
            cancelPathStepForm();
            
            const refreshResponse = await API.orders.getProductionPath(currentOrderId);
            if (refreshResponse.success) {
                productionPath = refreshResponse.data;
                renderProductionPath();
            }
        }
    } catch (error) {
        showAlert(error.message || 'Failed to save production step', 'danger');
    }
}

async function deletePathStep(stepId) {
    if (!confirm('Are you sure you want to delete this step?')) return;
    
    try {
        const response = await API.orders.deletePathStep(currentOrderId, stepId);
        if (response.success) {
            showAlert('Step deleted successfully', 'success');
            
            const refreshResponse = await API.orders.getProductionPath(currentOrderId);
            if (refreshResponse.success) {
                productionPath = refreshResponse.data;
                renderProductionPath();
            }
        }
    } catch (error) {
        showAlert('Failed to delete step', 'danger');
    }
}

async function saveProductionPath() {
    const pathData = productionPath.map((step, idx) => ({
        department_id: step.department_id,
        stage_id: step.stage_id,
        estimated_duration_minutes: step.estimated_duration_minutes,
        is_required: step.is_required,
        notes: step.notes
    }));
    
    try {
        const response = await API.orders.setProductionPath(currentOrderId, { paths: pathData });
        if (response.success) {
            showAlert('Production path saved successfully', 'success');
            hideModal('productionPathModal');
        }
    } catch (error) {
        showAlert('Failed to save production path', 'danger');
    }
}

async function submitOrderForm(event) {
    event.preventDefault();
    
    const data = {
        order_number: document.getElementById('orderNumber').value,
        sales_order_number: document.getElementById('salesOrderNumber').value,
        customer_name: document.getElementById('customerName').value,
        quantity: parseInt(document.getElementById('quantity').value),
        order_value: parseFloat(document.getElementById('orderValue').value) || null,
        start_date: document.getElementById('startDate').value || null,
        end_date: document.getElementById('endDate').value || null,
        notes: document.getElementById('notes').value
    };
    
    try {
        const response = await API.orders.create(data);
        
        if (response.success) {
            showAlert('Order created successfully', 'success');
            hideModal('addOrderModal');
            resetForm('orderForm');
            loadOrders();
        }
    } catch (error) {
        showAlert(error.message || 'Failed to create order', 'danger');
    }
}

async function viewOrder(orderId) {
    window.location.href = `/planning/order/${orderId}`;
}

async function scheduleOrder(orderId) {
    window.location.href = `/planning/schedule?order=${orderId}`;
}
