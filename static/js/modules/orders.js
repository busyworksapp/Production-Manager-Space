class OrdersPage {
    constructor() {
        this.currentOrderId = null;
        this.orderItems = [];
        this.productionPath = [];
        this.allProducts = [];
        this.allDepartments = [];
        this.allStages = [];
        this.init();
    }

    async init() {
        const user = getCurrentUser();
        if (user) {
            document.getElementById('username').textContent = `${user.first_name} ${user.last_name}`;
        }
        
        await Promise.all([this.loadProducts(), this.loadDepartments(), this.loadStages()]);
        this.loadOrders();
        this.attachEventListeners();
    }

    attachEventListeners() {
        const logoutBtn = document.querySelector('.logout-btn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', () => logout());
        }

        const addOrderBtn = document.querySelector('.add-order-btn');
        if (addOrderBtn) {
            addOrderBtn.addEventListener('click', () => showModal('addOrderModal'));
        }

        const statusFilter = document.getElementById('statusFilter');
        if (statusFilter) {
            statusFilter.addEventListener('change', () => this.loadOrders());
        }

        const orderForm = document.getElementById('orderForm');
        if (orderForm) {
            orderForm.addEventListener('submit', (e) => this.submitOrderForm(e));
        }

        const itemForm = document.getElementById('itemForm');
        if (itemForm) {
            itemForm.addEventListener('submit', (e) => this.saveOrderItem(e));
        }

        const pathStepForm = document.getElementById('pathStepForm');
        if (pathStepForm) {
            pathStepForm.addEventListener('submit', (e) => this.savePathStep(e));
        }

        const addItemBtn = document.querySelector('.add-item-btn');
        if (addItemBtn) {
            addItemBtn.addEventListener('click', () => this.showAddItemForm());
        }

        const addPathStepBtn = document.querySelector('.add-path-step-btn');
        if (addPathStepBtn) {
            addPathStepBtn.addEventListener('click', () => this.showAddPathStepForm());
        }

        const pathDepartmentSelect = document.getElementById('pathDepartmentId');
        if (pathDepartmentSelect) {
            pathDepartmentSelect.addEventListener('change', (e) => this.updateStageOptions(e.target.value));
        }

        document.querySelectorAll('.close-modal-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const modalId = e.target.getAttribute('data-modal');
                if (modalId) hideModal(modalId);
            });
        });

        const cancelItemBtn = document.querySelector('.cancel-item-btn');
        if (cancelItemBtn) {
            cancelItemBtn.addEventListener('click', () => this.cancelItemForm());
        }

        const cancelPathStepBtn = document.querySelector('.cancel-path-step-btn');
        if (cancelPathStepBtn) {
            cancelPathStepBtn.addEventListener('click', () => this.cancelPathStepForm());
        }

        const ordersTable = document.getElementById('ordersTable');
        if (ordersTable) {
            ordersTable.addEventListener('click', (e) => {
                if (e.target.classList.contains('view-order-btn')) {
                    const orderId = parseInt(e.target.getAttribute('data-order-id'));
                    this.viewOrder(orderId);
                } else if (e.target.classList.contains('manage-items-btn')) {
                    const orderId = parseInt(e.target.getAttribute('data-order-id'));
                    this.manageOrderItems(orderId);
                } else if (e.target.classList.contains('manage-path-btn')) {
                    const orderId = parseInt(e.target.getAttribute('data-order-id'));
                    this.manageProductionPath(orderId);
                } else if (e.target.classList.contains('schedule-order-btn')) {
                    const orderId = parseInt(e.target.getAttribute('data-order-id'));
                    this.scheduleOrder(orderId);
                }
            });
        }

        const orderItemsTable = document.getElementById('orderItemsTable');
        if (orderItemsTable) {
            orderItemsTable.addEventListener('click', (e) => {
                if (e.target.classList.contains('edit-item-btn')) {
                    const itemId = parseInt(e.target.getAttribute('data-item-id'));
                    this.editOrderItem(itemId);
                } else if (e.target.classList.contains('delete-item-btn')) {
                    const itemId = parseInt(e.target.getAttribute('data-item-id'));
                    this.deleteOrderItem(itemId);
                }
            });
        }

        const productionPathTable = document.getElementById('productionPathTable');
        if (productionPathTable) {
            productionPathTable.addEventListener('click', (e) => {
                if (e.target.classList.contains('edit-path-step-btn')) {
                    const stepId = parseInt(e.target.getAttribute('data-step-id'));
                    this.editPathStep(stepId);
                } else if (e.target.classList.contains('delete-path-step-btn')) {
                    const stepId = parseInt(e.target.getAttribute('data-step-id'));
                    this.deletePathStep(stepId);
                } else if (e.target.classList.contains('move-step-up-btn')) {
                    const index = parseInt(e.target.getAttribute('data-index'));
                    this.movePathStep(index, 'up');
                } else if (e.target.classList.contains('move-step-down-btn')) {
                    const index = parseInt(e.target.getAttribute('data-index'));
                    this.movePathStep(index, 'down');
                }
            });
        }
    }

    async loadProducts() {
        try {
            const response = await API.products.getAll();
            if (response.success) {
                this.allProducts = response.data;
            }
        } catch (error) {
            console.error('Error loading products:', error);
        }
    }

    async loadDepartments() {
        try {
            const response = await fetch(`${API_BASE_URL}/api/departments`, {
                headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
            });
            const data = await response.json();
            if (data.success) {
                this.allDepartments = data.data;
            }
        } catch (error) {
            console.error('Error loading departments:', error);
        }
    }

    async loadStages() {
        try {
            const response = await fetch(`${API_BASE_URL}/api/departments/stages`, {
                headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
            });
            const data = await response.json();
            if (data.success) {
                this.allStages = data.data;
            }
        } catch (error) {
            console.error('Error loading stages:', error);
        }
    }

    async loadOrders() {
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
                            <button class="btn btn-sm btn-primary view-order-btn" data-order-id="${order.id}">View</button>
                            <button class="btn btn-sm btn-info manage-items-btn" data-order-id="${order.id}">Items</button>
                            <button class="btn btn-sm btn-warning manage-path-btn" data-order-id="${order.id}">Path</button>
                            <button class="btn btn-sm btn-success schedule-order-btn" data-order-id="${order.id}">Schedule</button>
                        </td>
                    </tr>
                `).join('');
            }
        } catch (error) {
            console.error('Error loading orders:', error);
            showAlert('Failed to load orders', 'danger');
        }
    }

    async manageOrderItems(orderId) {
        this.currentOrderId = orderId;
        
        try {
            const response = await API.orders.getItems(orderId);
            if (response.success) {
                this.orderItems = response.data;
                this.renderOrderItems();
                showModal('orderItemsModal');
            }
        } catch (error) {
            showAlert('Failed to load order items', 'danger');
        }
    }

    renderOrderItems() {
        const tbody = document.getElementById('orderItemsTable');
        if (this.orderItems.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="table-center-text">No items added yet</td></tr>';
            return;
        }
        
        tbody.innerHTML = this.orderItems.map((item, idx) => `
            <tr>
                <td>${idx + 1}</td>
                <td>${item.product_name || item.product_code}</td>
                <td>${item.quantity}</td>
                <td>${formatCurrency(item.unit_price)}</td>
                <td>${formatCurrency(item.quantity * (item.unit_price || 0))}</td>
                <td>
                    <button class="btn btn-sm btn-primary edit-item-btn" data-item-id="${item.id}">Edit</button>
                    <button class="btn btn-sm btn-danger delete-item-btn" data-item-id="${item.id}">Delete</button>
                </td>
            </tr>
        `).join('');
    }

    showAddItemForm() {
        document.getElementById('itemForm').reset();
        document.getElementById('itemFormTitle').textContent = 'Add Item';
        document.getElementById('itemId').value = '';
        
        const productSelect = document.getElementById('itemProductId');
        productSelect.innerHTML = '<option value="">Select Product</option>' + 
            this.allProducts.map(p => `<option value="${p.id}">${p.product_name} (${p.product_code})</option>`).join('');
        
        document.getElementById('itemFormContainer').classList.add('active');
    }

    async editOrderItem(itemId) {
        const item = this.orderItems.find(i => i.id === itemId);
        if (!item) return;
        
        document.getElementById('itemFormTitle').textContent = 'Edit Item';
        document.getElementById('itemId').value = item.id;
        document.getElementById('itemProductId').value = item.product_id;
        document.getElementById('itemQuantity').value = item.quantity;
        document.getElementById('itemUnitPrice').value = item.unit_price || '';
        document.getElementById('itemSpecifications').value = item.specifications || '';
        
        const productSelect = document.getElementById('itemProductId');
        productSelect.innerHTML = '<option value="">Select Product</option>' + 
            this.allProducts.map(p => `<option value="${p.id}" ${p.id === item.product_id ? 'selected' : ''}>${p.product_name} (${p.product_code})</option>`).join('');
        
        document.getElementById('itemFormContainer').classList.add('active');
    }

    cancelItemForm() {
        document.getElementById('itemFormContainer').classList.remove('active');
        document.getElementById('itemForm').reset();
    }

    async saveOrderItem(event) {
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
                response = await API.orders.updateItem(this.currentOrderId, parseInt(itemId), data);
            } else {
                response = await API.orders.addItem(this.currentOrderId, data);
            }
            
            if (response.success) {
                showAlert(itemId ? 'Item updated successfully' : 'Item added successfully', 'success');
                this.cancelItemForm();
                
                const refreshResponse = await API.orders.getItems(this.currentOrderId);
                if (refreshResponse.success) {
                    this.orderItems = refreshResponse.data;
                    this.renderOrderItems();
                }
            }
        } catch (error) {
            showAlert(error.message || 'Failed to save item', 'danger');
        }
    }

    async deleteOrderItem(itemId) {
        if (!confirm('Are you sure you want to delete this item?')) return;
        
        try {
            const response = await API.orders.deleteItem(this.currentOrderId, itemId);
            if (response.success) {
                showAlert('Item deleted successfully', 'success');
                
                const refreshResponse = await API.orders.getItems(this.currentOrderId);
                if (refreshResponse.success) {
                    this.orderItems = refreshResponse.data;
                    this.renderOrderItems();
                }
            }
        } catch (error) {
            showAlert('Failed to delete item', 'danger');
        }
    }

    async manageProductionPath(orderId) {
        this.currentOrderId = orderId;
        
        try {
            const response = await API.orders.getProductionPath(orderId);
            if (response.success) {
                this.productionPath = response.data;
                this.renderProductionPath();
                showModal('productionPathModal');
            }
        } catch (error) {
            showAlert('Failed to load production path', 'danger');
        }
    }

    renderProductionPath() {
        const tbody = document.getElementById('productionPathTable');
        if (this.productionPath.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="table-center-text">No production path configured</td></tr>';
            return;
        }
        
        tbody.innerHTML = this.productionPath.map((step, idx) => `
            <tr>
                <td>${step.path_sequence}</td>
                <td>${step.department_name}</td>
                <td>${step.stage_name || 'Any Stage'}</td>
                <td>${step.estimated_duration_minutes || 'N/A'} min</td>
                <td>${step.is_required ? 'Yes' : 'No'}</td>
                <td>
                    <button class="btn btn-sm btn-primary edit-path-step-btn" data-step-id="${step.id}">Edit</button>
                    <button class="btn btn-sm btn-danger delete-path-step-btn" data-step-id="${step.id}">Delete</button>
                    ${idx > 0 ? `<button class="btn btn-sm btn-secondary move-step-up-btn" data-index="${idx}">↑</button>` : ''}
                    ${idx < this.productionPath.length - 1 ? `<button class="btn btn-sm btn-secondary move-step-down-btn" data-index="${idx}">↓</button>` : ''}
                </td>
            </tr>
        `).join('');
    }

    showAddPathStepForm() {
        document.getElementById('pathStepForm').reset();
        document.getElementById('pathStepFormTitle').textContent = 'Add Production Step';
        document.getElementById('pathStepId').value = '';
        
        const deptSelect = document.getElementById('pathDepartmentId');
        deptSelect.innerHTML = '<option value="">Select Department</option>' + 
            this.allDepartments.map(d => `<option value="${d.id}">${d.name}</option>`).join('');
        
        document.getElementById('pathStepFormContainer').classList.add('active');
    }

    async editPathStep(stepId) {
        const step = this.productionPath.find(s => s.id === stepId);
        if (!step) return;
        
        document.getElementById('pathStepFormTitle').textContent = 'Edit Production Step';
        document.getElementById('pathStepId').value = step.id;
        document.getElementById('pathDepartmentId').value = step.department_id;
        
        await this.updateStageOptions(step.department_id, step.stage_id);
        
        document.getElementById('pathEstimatedDuration').value = step.estimated_duration_minutes || '';
        document.getElementById('pathIsRequired').checked = step.is_required;
        document.getElementById('pathNotes').value = step.notes || '';
        
        document.getElementById('pathStepFormContainer').classList.add('active');
    }

    async updateStageOptions(departmentId, selectedStageId = null) {
        const stageSelect = document.getElementById('pathStageId');
        const filteredStages = this.allStages.filter(s => s.department_id == departmentId);
        
        stageSelect.innerHTML = '<option value="">Any Stage</option>' + 
            filteredStages.map(s => `<option value="${s.id}" ${s.id === selectedStageId ? 'selected' : ''}>${s.stage_name}</option>`).join('');
    }

    cancelPathStepForm() {
        document.getElementById('pathStepFormContainer').classList.remove('active');
        document.getElementById('pathStepForm').reset();
    }

    async savePathStep(event) {
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
                response = await API.orders.updatePathStep(this.currentOrderId, parseInt(stepId), data);
            } else {
                const paths = [...this.productionPath, data];
                response = await API.orders.setProductionPath(this.currentOrderId, { paths });
            }
            
            if (response.success) {
                showAlert(stepId ? 'Step updated successfully' : 'Step added successfully', 'success');
                this.cancelPathStepForm();
                
                const refreshResponse = await API.orders.getProductionPath(this.currentOrderId);
                if (refreshResponse.success) {
                    this.productionPath = refreshResponse.data;
                    this.renderProductionPath();
                }
            }
        } catch (error) {
            showAlert(error.message || 'Failed to save production step', 'danger');
        }
    }

    async deletePathStep(stepId) {
        if (!confirm('Are you sure you want to delete this step?')) return;
        
        try {
            const response = await API.orders.deletePathStep(this.currentOrderId, stepId);
            if (response.success) {
                showAlert('Step deleted successfully', 'success');
                
                const refreshResponse = await API.orders.getProductionPath(this.currentOrderId);
                if (refreshResponse.success) {
                    this.productionPath = refreshResponse.data;
                    this.renderProductionPath();
                }
            }
        } catch (error) {
            showAlert('Failed to delete step', 'danger');
        }
    }

    async movePathStep(index, direction) {
    }

    async submitOrderForm(event) {
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
                this.loadOrders();
            }
        } catch (error) {
            showAlert(error.message || 'Failed to create order', 'danger');
        }
    }

    viewOrder(orderId) {
        window.location.href = `/planning/order/${orderId}`;
    }

    scheduleOrder(orderId) {
        window.location.href = `/planning/schedule?order=${orderId}`;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new OrdersPage();
});
