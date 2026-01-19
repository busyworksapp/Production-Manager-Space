class DepartmentManager {
    constructor() {
        this.currentDepartment = null;
        this.init();
    }

    init() {
        this.attachEventListeners();
        this.loadDepartments();
    }

    attachEventListeners() {
        const addBtn = document.getElementById('addDepartmentBtn');
        const saveBtn = document.getElementById('saveDepartmentBtn');
        const cancelBtn = document.getElementById('cancelDepartmentBtn');
        const addStageBtn = document.getElementById('addStageBtn');
        const departmentForm = document.getElementById('departmentForm');

        if (addBtn) addBtn.addEventListener('click', () => this.showAddModal());
        if (saveBtn) saveBtn.addEventListener('click', () => this.saveDepartment());
        if (cancelBtn) cancelBtn.addEventListener('click', () => this.hideModal());
        if (addStageBtn) addStageBtn.addEventListener('click', () => this.showAddStageModal());
        if (departmentForm) departmentForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.saveDepartment();
        });
    }

    async loadDepartments() {
        try {
            const response = await API.departments.getAll();
            this.renderDepartments(response.data);
        } catch (error) {
            showNotification('Failed to load departments', 'error');
        }
    }

    renderDepartments(departments) {
        const tbody = document.getElementById('departmentsTable');
        if (!tbody) return;

        tbody.innerHTML = departments.map(dept => `
            <tr data-id="${dept.id}">
                <td>${escapeHtml(dept.code)}</td>
                <td>${escapeHtml(dept.name)}</td>
                <td><span class="badge badge-${dept.department_type}">${dept.department_type}</span></td>
                <td>${dept.daily_target || '-'}</td>
                <td>${dept.weekly_target || '-'}</td>
                <td>${dept.monthly_target || '-'}</td>
                <td><span class="status-badge status-${dept.is_active ? 'active' : 'inactive'}">${dept.is_active ? 'Active' : 'Inactive'}</span></td>
                <td>
                    <button class="btn btn-sm btn-secondary" data-action="edit" data-id="${dept.id}">Edit</button>
                    <button class="btn btn-sm btn-info" data-action="stages" data-id="${dept.id}">Stages</button>
                    <button class="btn btn-sm btn-danger" data-action="delete" data-id="${dept.id}">Delete</button>
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

    async handleAction(action, id) {
        switch(action) {
            case 'edit':
                await this.editDepartment(id);
                break;
            case 'stages':
                await this.viewStages(id);
                break;
            case 'delete':
                await this.deleteDepartment(id);
                break;
        }
    }

    showAddModal() {
        this.currentDepartment = null;
        document.getElementById('departmentForm').reset();
        document.getElementById('departmentModalTitle').textContent = 'Add Department';
        showModal('departmentModal');
    }

    async editDepartment(id) {
        try {
            const response = await API.departments.getById(id);
            const dept = response.data;
            this.currentDepartment = dept;

            document.getElementById('departmentCode').value = dept.code;
            document.getElementById('departmentName').value = dept.name;
            document.getElementById('departmentDescription').value = dept.description || '';
            document.getElementById('departmentType').value = dept.department_type;
            document.getElementById('dailyTarget').value = dept.daily_target || '';
            document.getElementById('weeklyTarget').value = dept.weekly_target || '';
            document.getElementById('monthlyTarget').value = dept.monthly_target || '';
            document.getElementById('isActive').checked = dept.is_active;

            document.getElementById('departmentModalTitle').textContent = 'Edit Department';
            showModal('departmentModal');
        } catch (error) {
            showNotification('Failed to load department details', 'error');
        }
    }

    async saveDepartment() {
        const data = {
            code: document.getElementById('departmentCode').value,
            name: document.getElementById('departmentName').value,
            description: document.getElementById('departmentDescription').value,
            department_type: document.getElementById('departmentType').value,
            daily_target: document.getElementById('dailyTarget').value || null,
            weekly_target: document.getElementById('weeklyTarget').value || null,
            monthly_target: document.getElementById('monthlyTarget').value || null,
            is_active: document.getElementById('isActive').checked
        };

        try {
            if (this.currentDepartment) {
                await API.departments.update(this.currentDepartment.id, data);
                showNotification('Department updated successfully', 'success');
            } else {
                await API.departments.create(data);
                showNotification('Department created successfully', 'success');
            }
            this.hideModal();
            this.loadDepartments();
        } catch (error) {
            showNotification(error.message || 'Failed to save department', 'error');
        }
    }

    async deleteDepartment(id) {
        if (!confirm('Are you sure you want to delete this department?')) return;

        try {
            await API.departments.delete(id);
            showNotification('Department deleted successfully', 'success');
            this.loadDepartments();
        } catch (error) {
            showNotification('Failed to delete department', 'error');
        }
    }

    async viewStages(id) {
        try {
            const response = await API.departments.getById(id);
            const dept = response.data;
            this.currentDepartment = dept;
            this.renderStages(dept.stages || []);
            showModal('stagesModal');
        } catch (error) {
            showNotification('Failed to load stages', 'error');
        }
    }

    renderStages(stages) {
        const tbody = document.getElementById('stagesTable');
        if (!tbody) return;

        tbody.innerHTML = stages.map(stage => `
            <tr>
                <td>${stage.stage_order}</td>
                <td>${escapeHtml(stage.stage_name)}</td>
                <td>${stage.estimated_duration_minutes || '-'} min</td>
                <td><span class="status-badge status-${stage.is_active ? 'active' : 'inactive'}">${stage.is_active ? 'Active' : 'Inactive'}</span></td>
                <td>
                    <button class="btn btn-sm btn-danger" data-action="delete-stage" data-id="${stage.id}">Delete</button>
                </td>
            </tr>
        `).join('');

        tbody.querySelectorAll('[data-action="delete-stage"]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.deleteStage(parseInt(e.target.dataset.id));
            });
        });
    }

    showAddStageModal() {
        document.getElementById('stageForm').reset();
        showModal('addStageModal');
    }

    hideModal() {
        hideModal('departmentModal');
        hideModal('stagesModal');
        hideModal('addStageModal');
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => new DepartmentManager());
} else {
    new DepartmentManager();
}
