class MachineManager {
    constructor() {
        this.currentMachine = null;
        this.init();
    }

    init() {
        this.attachEventListeners();
        this.loadMachines();
        this.loadDepartments();
    }

    attachEventListeners() {
        const addBtn = document.getElementById('addMachineBtn');
        const saveBtn = document.getElementById('saveMachineBtn');
        const cancelBtn = document.getElementById('cancelMachineBtn');
        const searchInput = document.getElementById('searchMachine');
        const statusFilter = document.getElementById('statusFilter');

        if (addBtn) addBtn.addEventListener('click', () => this.showAddModal());
        if (saveBtn) saveBtn.addEventListener('click', () => this.saveMachine());
        if (cancelBtn) cancelBtn.addEventListener('click', () => this.hideModal());
        if (searchInput) searchInput.addEventListener('input', (e) => this.filterMachines(e.target.value));
        if (statusFilter) statusFilter.addEventListener('change', (e) => this.loadMachines({ status: e.target.value }));
    }

    async loadMachines(params = {}) {
        try {
            const response = await API.machines.getAll(params);
            this.allMachines = response.data;
            this.renderMachines(response.data);
        } catch (error) {
            showNotification('Failed to load machines', 'error');
        }
    }

    async loadDepartments() {
        try {
            const response = await API.departments.getAll();
            const select = document.getElementById('machineDepartment');
            
            if (select) {
                select.innerHTML = '<option value="">Select Department</option>' +
                    response.data.map(dept => `<option value="${dept.id}">${escapeHtml(dept.name)}</option>`).join('');
            }
        } catch (error) {
            console.error('Failed to load departments', error);
        }
    }

    renderMachines(machines) {
        const tbody = document.getElementById('machinesTable');
        if (!tbody) return;

        tbody.innerHTML = machines.map(machine => `
            <tr data-id="${machine.id}">
                <td>${escapeHtml(machine.machine_number)}</td>
                <td>${escapeHtml(machine.machine_name)}</td>
                <td>${escapeHtml(machine.department_name || '-')}</td>
                <td>${escapeHtml(machine.machine_type || '-')}</td>
                <td><span class="status-badge status-${machine.status}">${machine.status}</span></td>
                <td>
                    <button class="btn btn-sm btn-secondary" data-action="edit" data-id="${machine.id}">Edit</button>
                    <button class="btn btn-sm btn-info" data-action="status" data-id="${machine.id}">Status</button>
                    <button class="btn btn-sm btn-warning" data-action="maintenance" data-id="${machine.id}">Maintenance</button>
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

    filterMachines(searchTerm) {
        if (!this.allMachines) return;
        
        const filtered = this.allMachines.filter(machine => 
            machine.machine_number.toLowerCase().includes(searchTerm.toLowerCase()) ||
            machine.machine_name.toLowerCase().includes(searchTerm.toLowerCase())
        );
        
        this.renderMachines(filtered);
    }

    async handleAction(action, id) {
        switch(action) {
            case 'edit':
                await this.editMachine(id);
                break;
            case 'status':
                await this.updateStatus(id);
                break;
            case 'maintenance':
                window.location.href = `/maintenance/tickets?machine_id=${id}`;
                break;
        }
    }

    showAddModal() {
        this.currentMachine = null;
        document.getElementById('machineForm').reset();
        document.getElementById('machineModalTitle').textContent = 'Add Machine';
        showModal('machineModal');
    }

    async editMachine(id) {
        try {
            const response = await API.machines.getById(id);
            const machine = response.data;
            this.currentMachine = machine;

            document.getElementById('machineNumber').value = machine.machine_number;
            document.getElementById('machineName').value = machine.machine_name;
            document.getElementById('machineDepartment').value = machine.department_id || '';
            document.getElementById('machineType').value = machine.machine_type || '';
            document.getElementById('manufacturer').value = machine.manufacturer || '';
            document.getElementById('model').value = machine.model || '';
            document.getElementById('serialNumber').value = machine.serial_number || '';
            document.getElementById('purchaseDate').value = machine.purchase_date || '';
            document.getElementById('machineStatus').value = machine.status;
            document.getElementById('machineActive').checked = machine.is_active;

            document.getElementById('machineModalTitle').textContent = 'Edit Machine';
            showModal('machineModal');
        } catch (error) {
            showNotification('Failed to load machine details', 'error');
        }
    }

    async saveMachine() {
        const data = {
            machine_number: document.getElementById('machineNumber').value,
            machine_name: document.getElementById('machineName').value,
            department_id: document.getElementById('machineDepartment').value || null,
            machine_type: document.getElementById('machineType').value || null,
            manufacturer: document.getElementById('manufacturer').value || null,
            model: document.getElementById('model').value || null,
            serial_number: document.getElementById('serialNumber').value || null,
            purchase_date: document.getElementById('purchaseDate').value || null,
            status: document.getElementById('machineStatus').value,
            is_active: document.getElementById('machineActive').checked
        };

        try {
            if (this.currentMachine) {
                await API.machines.update(this.currentMachine.id, data);
                showNotification('Machine updated successfully', 'success');
            } else {
                await API.machines.create(data);
                showNotification('Machine created successfully', 'success');
            }
            this.hideModal();
            this.loadMachines();
        } catch (error) {
            showNotification(error.message || 'Failed to save machine', 'error');
        }
    }

    async updateStatus(id) {
        const newStatus = prompt('Enter new status (available, in_use, maintenance, broken, retired):');
        if (!newStatus) return;

        const validStatuses = ['available', 'in_use', 'maintenance', 'broken', 'retired'];
        if (!validStatuses.includes(newStatus)) {
            showNotification('Invalid status', 'error');
            return;
        }

        try {
            await API.machines.updateStatus(id, newStatus);
            showNotification('Machine status updated', 'success');
            this.loadMachines();
        } catch (error) {
            showNotification('Failed to update machine status', 'error');
        }
    }

    hideModal() {
        hideModal('machineModal');
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => new MachineManager());
} else {
    new MachineManager();
}
