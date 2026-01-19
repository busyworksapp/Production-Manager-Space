class ManagerDashboard {
    constructor() {
        this.currentTab = 'allocations';
        this.departmentId = null;
        this.init();
    }

    init() {
        this.getUserDepartment();
        this.attachEventListeners();
        this.loadStats();
    }

    async getUserDepartment() {
        try {
            const user = getCurrentUser();
            if (user && user.department_id) {
                this.departmentId = user.department_id;
                await this.loadDepartmentInfo();
            }
        } catch (error) {
            console.error('Failed to get user department', error);
        }
    }

    async loadDepartmentInfo() {
        try {
            const response = await API.departments.getById(this.departmentId);
            const dept = response.data;
            document.getElementById('departmentTitle').textContent = `${dept.name} - Manager Dashboard`;
        } catch (error) {
            console.error('Failed to load department info', error);
        }
    }

    attachEventListeners() {
        const tabButtons = document.querySelectorAll('.tab-button');
        tabButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const tab = e.target.getAttribute('data-tab') || e.target.textContent.toLowerCase().replace(/-/g, '');
                this.switchTab(tab);
            });
        });

        const allocateBtn = document.getElementById('addAllocationBtn');
        const assignJobBtn = document.getElementById('assignJobBtn');
        const saveAllocationBtn = document.getElementById('saveAllocationBtn');
        const saveJobBtn = document.getElementById('saveJobBtn');

        if (allocateBtn) allocateBtn.addEventListener('click', () => this.showAddAllocationModal());
        if (assignJobBtn) assignJobBtn.addEventListener('click', () => this.showAssignJobModal());
        if (saveAllocationBtn) saveAllocationBtn.addEventListener('click', () => this.saveAllocation());
        if (saveJobBtn) saveJobBtn.addEventListener('click', () => this.assignJob());
    }

    switchTab(tabName) {
        document.querySelectorAll('.tab-content').forEach(tab => tab.style.display = 'none');
        document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
        
        const targetTab = document.getElementById(`${tabName}Tab`);
        if (targetTab) {
            targetTab.style.display = 'block';
            const activeBtn = Array.from(document.querySelectorAll('.tab-button'))
                .find(btn => (btn.getAttribute('data-tab') || btn.textContent.toLowerCase().replace(/-/g, '')) === tabName);
            if (activeBtn) activeBtn.classList.add('active');
        }

        this.currentTab = tabName;
        
        if (tabName === 'allocations') {
            this.loadAllocations();
        } else if (tabName === 'jobs') {
            this.loadJobs();
        } else if (tabName === 'overview') {
            this.loadOverview();
        }
    }

    async loadStats() {
        try {
            const response = await API.manager.getStats(this.departmentId);
            const stats = response.data;

            document.getElementById('totalEmployees').textContent = stats.total_employees || 0;
            document.getElementById('totalMachines').textContent = stats.total_machines || 0;
            document.getElementById('activeJobs').textContent = stats.active_jobs || 0;
            document.getElementById('pendingJobs').textContent = stats.pending_jobs || 0;
        } catch (error) {
            console.error('Failed to load stats', error);
        }
    }

    async loadAllocations() {
        try {
            const response = await API.manager.getAllocations(this.departmentId);
            this.renderAllocations(response.data);
        } catch (error) {
            showNotification('Failed to load allocations', 'error');
        }
    }

    renderAllocations(allocations) {
        const tbody = document.getElementById('allocationsTable');
        if (!tbody) return;

        if (!allocations || allocations.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="text-center">No allocations found</td></tr>';
            return;
        }

        tbody.innerHTML = allocations.map(alloc => `
            <tr data-id="${alloc.id}">
                <td>${escapeHtml(alloc.employee_name)}</td>
                <td>${escapeHtml(alloc.machine_name)}</td>
                <td>${escapeHtml(alloc.allocation_type || 'permanent')}</td>
                <td>${formatDate(alloc.start_date)}</td>
                <td>${alloc.end_date ? formatDate(alloc.end_date) : 'Ongoing'}</td>
                <td><span class="status-badge status-${alloc.status}">${alloc.status}</span></td>
                <td>
                    <button class="btn btn-sm btn-secondary" data-action="edit-allocation" data-id="${alloc.id}">Edit</button>
                    <button class="btn btn-sm btn-danger" data-action="remove-allocation" data-id="${alloc.id}">Remove</button>
                </td>
            </tr>
        `).join('');

        tbody.querySelectorAll('[data-action]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const action = e.target.dataset.action;
                const id = parseInt(e.target.dataset.id);
                this.handleAllocationAction(action, id);
            });
        });
    }

    async handleAllocationAction(action, id) {
        if (action === 'edit-allocation') {
            await this.editAllocation(id);
        } else if (action === 'remove-allocation') {
            await this.removeAllocation(id);
        }
    }

    async loadJobs() {
        try {
            const response = await API.manager.getJobs(this.departmentId);
            this.renderJobs(response.data);
        } catch (error) {
            showNotification('Failed to load jobs', 'error');
        }
    }

    renderJobs(jobs) {
        const tbody = document.getElementById('jobsTable');
        if (!tbody) return;

        if (!jobs || jobs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" class="text-center">No jobs found</td></tr>';
            return;
        }

        tbody.innerHTML = jobs.map(job => `
            <tr data-id="${job.id}">
                <td>${job.id}</td>
                <td>${escapeHtml(job.order_number)}</td>
                <td>${escapeHtml(job.product_name || '-')}</td>
                <td>${escapeHtml(job.stage_name || '-')}</td>
                <td>${escapeHtml(job.assigned_employee_name || 'Unassigned')}</td>
                <td>${escapeHtml(job.machine_name || '-')}</td>
                <td>${formatDate(job.scheduled_date)}</td>
                <td><span class="status-badge status-${job.status}">${job.status}</span></td>
                <td>
                    <button class="btn btn-sm btn-secondary" data-action="reassign-job" data-id="${job.id}">Reassign</button>
                </td>
            </tr>
        `).join('');

        tbody.querySelectorAll('[data-action]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const action = e.target.dataset.action;
                const id = parseInt(e.target.dataset.id);
                this.handleJobAction(action, id);
            });
        });
    }

    async handleJobAction(action, id) {
        if (action === 'reassign-job') {
            await this.reassignJob(id);
        }
    }

    async loadOverview() {
        try {
            const response = await API.manager.getOverview(this.departmentId);
            const overview = response.data;
            this.renderOverview(overview);
        } catch (error) {
            showNotification('Failed to load overview', 'error');
        }
    }

    renderOverview(overview) {
        const container = document.getElementById('overviewContainer');
        if (!container) return;

        container.innerHTML = `
            <div class="grid grid-3">
                <div class="card">
                    <h3>Capacity Utilization</h3>
                    <div class="stat-value">${overview.capacity_utilization || 0}%</div>
                </div>
                <div class="card">
                    <h3>Completed Today</h3>
                    <div class="stat-value">${overview.completed_today || 0}</div>
                </div>
                <div class="card">
                    <h3>Pending Orders</h3>
                    <div class="stat-value">${overview.pending_orders || 0}</div>
                </div>
            </div>
        `;
    }

    showAddAllocationModal() {
        this.loadEmployeesForAllocation();
        this.loadMachinesForAllocation();
        showModal('addAllocationModal');
    }

    async loadEmployeesForAllocation() {
        try {
            const response = await API.employees.getAll({ department_id: this.departmentId });
            const select = document.getElementById('allocationEmployee');
            if (select) {
                select.innerHTML = '<option value="">Select Employee</option>' +
                    response.data.map(emp => `<option value="${emp.id}">${escapeHtml(emp.first_name)} ${escapeHtml(emp.last_name)}</option>`).join('');
            }
        } catch (error) {
            console.error('Failed to load employees', error);
        }
    }

    async loadMachinesForAllocation() {
        try {
            const response = await API.machines.getAll({ department_id: this.departmentId });
            const select = document.getElementById('allocationMachine');
            if (select) {
                select.innerHTML = '<option value="">Select Machine</option>' +
                    response.data.map(machine => `<option value="${machine.id}">${escapeHtml(machine.machine_name)}</option>`).join('');
            }
        } catch (error) {
            console.error('Failed to load machines', error);
        }
    }

    async saveAllocation() {
        const data = {
            employee_id: document.getElementById('allocationEmployee').value,
            machine_id: document.getElementById('allocationMachine').value,
            start_date: document.getElementById('allocationStartDate').value,
            end_date: document.getElementById('allocationEndDate').value || null
        };

        try {
            await API.manager.createAllocation(data);
            showNotification('Allocation created successfully', 'success');
            hideModal('addAllocationModal');
            this.loadAllocations();
        } catch (error) {
            showNotification(error.message || 'Failed to create allocation', 'error');
        }
    }

    async removeAllocation(id) {
        if (!confirm('Are you sure you want to remove this allocation?')) return;

        try {
            await API.manager.removeAllocation(id);
            showNotification('Allocation removed successfully', 'success');
            this.loadAllocations();
        } catch (error) {
            showNotification('Failed to remove allocation', 'error');
        }
    }

    showAssignJobModal() {
        showModal('assignJobModal');
    }

    async assignJob() {
        const data = {
            order_id: document.getElementById('jobOrder').value,
            machine_id: document.getElementById('jobMachine').value,
            employee_id: document.getElementById('jobEmployee').value,
            scheduled_date: document.getElementById('jobScheduleDate').value
        };

        try {
            await API.manager.assignJob(data);
            showNotification('Job assigned successfully', 'success');
            hideModal('assignJobModal');
            this.loadJobs();
        } catch (error) {
            showNotification(error.message || 'Failed to assign job', 'error');
        }
    }

    async reassignJob(id) {
        showModal('reassignJobModal');
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => new ManagerDashboard());
} else {
    new ManagerDashboard();
}
