class EmployeeManager {
    constructor() {
        this.currentEmployee = null;
        this.init();
    }

    init() {
        this.attachEventListeners();
        this.loadEmployees();
        this.loadDepartments();
    }

    attachEventListeners() {
        const addBtn = document.getElementById('addEmployeeBtn');
        const saveBtn = document.getElementById('saveEmployeeBtn');
        const cancelBtn = document.getElementById('cancelEmployeeBtn');
        const searchInput = document.getElementById('searchEmployee');
        const departmentFilter = document.getElementById('departmentFilter');

        if (addBtn) addBtn.addEventListener('click', () => this.showAddModal());
        if (saveBtn) saveBtn.addEventListener('click', () => this.saveEmployee());
        if (cancelBtn) cancelBtn.addEventListener('click', () => this.hideModal());
        if (searchInput) searchInput.addEventListener('input', (e) => this.filterEmployees(e.target.value));
        if (departmentFilter) departmentFilter.addEventListener('change', (e) => this.loadEmployees({ department_id: e.target.value }));
    }

    async loadEmployees(params = {}) {
        try {
            const response = await API.employees.getAll(params);
            this.allEmployees = response.data;
            this.renderEmployees(response.data);
        } catch (error) {
            showNotification('Failed to load employees', 'error');
        }
    }

    async loadDepartments() {
        try {
            const response = await API.departments.getAll();
            const select = document.getElementById('employeeDepartment');
            const filter = document.getElementById('departmentFilter');
            
            if (select) {
                select.innerHTML = '<option value="">Select Department</option>' +
                    response.data.map(dept => `<option value="${dept.id}">${escapeHtml(dept.name)}</option>`).join('');
            }
            
            if (filter) {
                filter.innerHTML = '<option value="">All Departments</option>' +
                    response.data.map(dept => `<option value="${dept.id}">${escapeHtml(dept.name)}</option>`).join('');
            }
        } catch (error) {
            console.error('Failed to load departments', error);
        }
    }

    renderEmployees(employees) {
        const tbody = document.getElementById('employeesTable');
        if (!tbody) return;

        tbody.innerHTML = employees.map(emp => `
            <tr data-id="${emp.id}">
                <td>${escapeHtml(emp.employee_number)}</td>
                <td>${escapeHtml(emp.first_name)} ${escapeHtml(emp.last_name)}</td>
                <td>${escapeHtml(emp.email || '-')}</td>
                <td>${escapeHtml(emp.phone || '-')}</td>
                <td>${escapeHtml(emp.department_name || '-')}</td>
                <td><span class="badge badge-${emp.employee_type}">${emp.employee_type}</span></td>
                <td><span class="status-badge status-${emp.is_active ? 'active' : 'inactive'}">${emp.is_active ? 'Active' : 'Inactive'}</span></td>
                <td>
                    <button class="btn btn-sm btn-secondary" data-action="edit" data-id="${emp.id}">Edit</button>
                    <button class="btn btn-sm btn-danger" data-action="delete" data-id="${emp.id}">Delete</button>
                </td>
            </tr>
        `).join('');

        tbody.querySelectorAll('[data-action]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const action = e.target.dataset.action;
                const id = parseInt(e.target.dataset.id);
                this.handleAction(action, id);
            });
        });
    }

    filterEmployees(searchTerm) {
        if (!this.allEmployees) return;
        
        const filtered = this.allEmployees.filter(emp => 
            emp.employee_number.toLowerCase().includes(searchTerm.toLowerCase()) ||
            emp.first_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
            emp.last_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
            (emp.email && emp.email.toLowerCase().includes(searchTerm.toLowerCase()))
        );
        
        this.renderEmployees(filtered);
    }

    async handleAction(action, id) {
        if (action === 'edit') {
            await this.editEmployee(id);
        } else if (action === 'delete') {
            await this.deleteEmployee(id);
        }
    }

    showAddModal() {
        this.currentEmployee = null;
        document.getElementById('employeeForm').reset();
        document.getElementById('employeeModalTitle').textContent = 'Add Employee';
        showModal('employeeModal');
    }

    async editEmployee(id) {
        try {
            const response = await API.employees.getById(id);
            const emp = response.data;
            this.currentEmployee = emp;

            document.getElementById('employeeNumber').value = emp.employee_number;
            document.getElementById('firstName').value = emp.first_name;
            document.getElementById('lastName').value = emp.last_name;
            document.getElementById('employeeEmail').value = emp.email || '';
            document.getElementById('employeePhone').value = emp.phone || '';
            document.getElementById('employeeDepartment').value = emp.department_id || '';
            document.getElementById('employeePosition').value = emp.position || '';
            document.getElementById('employeeType').value = emp.employee_type;
            document.getElementById('employeeActive').checked = emp.is_active;

            document.getElementById('employeeModalTitle').textContent = 'Edit Employee';
            showModal('employeeModal');
        } catch (error) {
            showNotification('Failed to load employee details', 'error');
        }
    }

    async saveEmployee() {
        const data = {
            employee_number: document.getElementById('employeeNumber').value,
            first_name: document.getElementById('firstName').value,
            last_name: document.getElementById('lastName').value,
            email: document.getElementById('employeeEmail').value || null,
            phone: document.getElementById('employeePhone').value || null,
            department_id: document.getElementById('employeeDepartment').value || null,
            position: document.getElementById('employeePosition').value || null,
            employee_type: document.getElementById('employeeType').value,
            is_active: document.getElementById('employeeActive').checked
        };

        try {
            if (this.currentEmployee) {
                await API.employees.update(this.currentEmployee.id, data);
                showNotification('Employee updated successfully', 'success');
            } else {
                await API.employees.create(data);
                showNotification('Employee created successfully', 'success');
            }
            this.hideModal();
            this.loadEmployees();
        } catch (error) {
            showNotification(error.message || 'Failed to save employee', 'error');
        }
    }

    async deleteEmployee(id) {
        if (!confirm('Are you sure you want to delete this employee?')) return;

        try {
            await API.employees.delete(id);
            showNotification('Employee deleted successfully', 'success');
            this.loadEmployees();
        } catch (error) {
            showNotification('Failed to delete employee', 'error');
        }
    }

    hideModal() {
        hideModal('employeeModal');
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => new EmployeeManager());
} else {
    new EmployeeManager();
}
