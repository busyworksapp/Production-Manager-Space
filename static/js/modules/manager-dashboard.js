class ManagerDashboardPage {
    constructor() {
        this.departmentData = null;
        this.departmentJobs = [];
        this.init();
    }

    async init() {
        const user = getCurrentUser();
        if (user) {
            document.getElementById('username').textContent = `${user.first_name} ${user.last_name}`;
        }
        
        this.attachEventListeners();
        await this.loadDepartmentData();
    }

    attachEventListeners() {
        const logoutBtn = document.querySelector('.logout-btn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', () => logout());
        }

        const tabButtons = document.querySelectorAll('.tab-button');
        tabButtons.forEach(btn => {
            btn.addEventListener('click', (e) => this.switchTab(e.target.dataset.tab));
        });

        const addAllocationBtn = document.querySelector('.add-allocation-btn');
        if (addAllocationBtn) {
            addAllocationBtn.addEventListener('click', () => showModal('addAllocationModal'));
        }

        const assignJobBtn = document.querySelector('.assign-job-btn');
        if (assignJobBtn) {
            assignJobBtn.addEventListener('click', () => showModal('assignJobModal'));
        }

        const allocationForm = document.getElementById('allocationForm');
        if (allocationForm) {
            allocationForm.addEventListener('submit', (e) => this.submitAllocation(e));
        }

        const editAllocationForm = document.getElementById('editAllocationForm');
        if (editAllocationForm) {
            editAllocationForm.addEventListener('submit', (e) => this.updateAllocation(e));
        }

        const assignJobForm = document.getElementById('assignJobForm');
        if (assignJobForm) {
            assignJobForm.addEventListener('submit', (e) => this.submitJobAssignment(e));
        }

        const closeAllocationModalBtn = document.querySelector('.close-allocation-modal-btn');
        if (closeAllocationModalBtn) {
            closeAllocationModalBtn.addEventListener('click', () => hideModal('addAllocationModal'));
        }

        const closeEditAllocationModalBtn = document.querySelector('.close-edit-allocation-modal-btn');
        if (closeEditAllocationModalBtn) {
            closeEditAllocationModalBtn.addEventListener('click', () => hideModal('editAllocationModal'));
        }

        const closeAssignJobModalBtn = document.querySelector('.close-assign-job-modal-btn');
        if (closeAssignJobModalBtn) {
            closeAssignJobModalBtn.addEventListener('click', () => hideModal('assignJobModal'));
        }

        const jobSelect = document.getElementById('jobSelect');
        if (jobSelect) {
            jobSelect.addEventListener('change', () => this.loadJobDetails());
        }

        const allocationsTable = document.getElementById('allocationsTable');
        if (allocationsTable) {
            allocationsTable.addEventListener('click', (e) => {
                if (e.target.classList.contains('edit-allocation-btn')) {
                    const allocationId = parseInt(e.target.getAttribute('data-allocation-id'));
                    this.editAllocation(allocationId);
                } else if (e.target.classList.contains('toggle-allocation-btn')) {
                    const allocationId = parseInt(e.target.getAttribute('data-allocation-id'));
                    const isActive = e.target.getAttribute('data-is-active') === 'true';
                    this.toggleAllocation(allocationId, isActive);
                }
            });
        }

        const jobsTable = document.getElementById('jobsTable');
        if (jobsTable) {
            jobsTable.addEventListener('click', (e) => {
                if (e.target.classList.contains('reassign-job-btn')) {
                    const jobId = parseInt(e.target.getAttribute('data-job-id'));
                    this.reassignJob(jobId);
                }
            });
        }
    }

    switchTab(tab) {
        const allocationsTab = document.getElementById('allocationsTab');
        const jobsTab = document.getElementById('jobsTab');
        const overviewTab = document.getElementById('overviewTab');
        const buttons = document.querySelectorAll('.tab-button');
        
        buttons.forEach(btn => btn.classList.remove('active'));
        
        allocationsTab.classList.add('tab-content-hidden');
        jobsTab.classList.add('tab-content-hidden');
        overviewTab.classList.add('tab-content-hidden');
        
        if (tab === 'allocations') {
            allocationsTab.classList.remove('tab-content-hidden');
            buttons[0].classList.add('active');
        } else if (tab === 'jobs') {
            jobsTab.classList.remove('tab-content-hidden');
            buttons[1].classList.add('active');
            this.loadDepartmentJobs();
        } else {
            overviewTab.classList.remove('tab-content-hidden');
            buttons[2].classList.add('active');
            this.loadDepartmentOverview();
        }
    }

    async loadDepartmentData() {
        try {
            const response = await fetch('/api/manager-controls/my-department', {
                headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
            });
            const data = await response.json();
            
            if (data.success) {
                this.departmentData = data.data;
                
                document.getElementById('departmentTitle').textContent = `${this.departmentData.name} - Manager Dashboard`;
                document.getElementById('totalEmployees').textContent = this.departmentData.employees?.length || 0;
                document.getElementById('totalMachines').textContent = this.departmentData.machines?.length || 0;
                
                this.populateEmployeeSelect();
                this.populateMachineSelect();
                this.loadAllocations();
                this.loadDepartmentStats();
            } else {
                showAlert(data.message || 'Failed to load department data', 'danger');
            }
        } catch (error) {
            console.error('Error loading department data:', error);
            showAlert('Failed to load department data', 'danger');
        }
    }

    populateEmployeeSelect() {
        const selects = [document.getElementById('employeeId'), document.getElementById('assignEmployee')];
        
        selects.forEach(select => {
            if (!select) return;
            select.innerHTML = '<option value="">Select Employee</option>';
            this.departmentData.employees?.forEach(emp => {
                const option = document.createElement('option');
                option.value = emp.id;
                option.textContent = `${emp.first_name} ${emp.last_name} (${emp.employee_number})`;
                select.appendChild(option);
            });
        });
    }

    populateMachineSelect() {
        const selects = [document.getElementById('machineId'), document.getElementById('assignMachine')];
        
        selects.forEach(select => {
            if (!select) return;
            select.innerHTML = '<option value="">Select Machine</option>';
            this.departmentData.machines?.forEach(machine => {
                const option = document.createElement('option');
                option.value = machine.id;
                option.textContent = `${machine.machine_name} (${machine.machine_number})`;
                select.appendChild(option);
            });
        });
    }

    async loadAllocations() {
        try {
            const response = await fetch('/api/manager-controls/employee-machine-allocations', {
                headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
            });
            const data = await response.json();
            
            if (data.success) {
                this.renderAllocations(data.data);
            }
        } catch (error) {
            console.error('Error loading allocations:', error);
            showAlert('Failed to load allocations', 'danger');
        }
    }

    renderAllocations(allocations) {
        const tbody = document.getElementById('allocationsTable');
        
        if (allocations.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="table-center-text">No allocations found</td></tr>';
            return;
        }
        
        tbody.innerHTML = allocations.map(allocation => `
            <tr>
                <td>${allocation.employee_name} (${allocation.employee_number})</td>
                <td>${allocation.machine_name} (${allocation.machine_number})</td>
                <td>${allocation.allocation_type}</td>
                <td>${allocation.start_date}</td>
                <td>${allocation.end_date || 'N/A'}</td>
                <td>${createStatusBadge(allocation.is_active ? 'active' : 'inactive')}</td>
                <td>
                    <button class="btn btn-sm btn-primary edit-allocation-btn" data-allocation-id="${allocation.id}">Edit</button>
                    <button class="btn btn-sm ${allocation.is_active ? 'btn-warning' : 'btn-success'} toggle-allocation-btn" 
                            data-allocation-id="${allocation.id}" 
                            data-is-active="${allocation.is_active}">
                        ${allocation.is_active ? 'Deactivate' : 'Activate'}
                    </button>
                </td>
            </tr>
        `).join('');
    }

    async loadDepartmentStats() {
        try {
            const response = await fetch('/api/manager-controls/department-stats', {
                headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
            });
            const data = await response.json();
            
            if (data.success) {
                const stats = data.data;
                document.getElementById('activeJobs').textContent = stats.active_jobs || 0;
                document.getElementById('pendingJobs').textContent = stats.pending_jobs || 0;
            }
        } catch (error) {
            console.error('Error loading stats:', error);
        }
    }

    async loadDepartmentJobs() {
        try {
            const response = await fetch('/api/manager-controls/department-jobs', {
                headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
            });
            const data = await response.json();
            
            if (data.success) {
                this.departmentJobs = data.data;
                this.renderJobs(data.data);
                this.populateJobSelect(data.data);
            }
        } catch (error) {
            console.error('Error loading jobs:', error);
            showAlert('Failed to load jobs', 'danger');
        }
    }

    renderJobs(jobs) {
        const tbody = document.getElementById('jobsTable');
        
        if (jobs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="9" class="table-center-text">No jobs found</td></tr>';
            return;
        }
        
        tbody.innerHTML = jobs.map(job => `
            <tr>
                <td>${job.id}</td>
                <td>${job.order_number}</td>
                <td>${job.product_name}</td>
                <td>${job.stage_name || 'N/A'}</td>
                <td>${job.assigned_employee_name || 'Unassigned'}</td>
                <td>${job.machine_name || 'N/A'}</td>
                <td>${job.scheduled_date}</td>
                <td>${createStatusBadge(job.status)}</td>
                <td>
                    <button class="btn btn-sm btn-primary reassign-job-btn" data-job-id="${job.id}">Reassign</button>
                </td>
            </tr>
        `).join('');
    }

    populateJobSelect(jobs) {
        const jobSelect = document.getElementById('jobSelect');
        if (!jobSelect) return;
        
        jobSelect.innerHTML = '<option value="">Select Job</option>';
        jobs.forEach(job => {
            const option = document.createElement('option');
            option.value = job.id;
            option.textContent = `Job #${job.id} - ${job.order_number} (${job.status})`;
            option.dataset.job = JSON.stringify(job);
            jobSelect.appendChild(option);
        });
    }

    loadDepartmentOverview() {
        if (!this.departmentData) return;
        
        const employeesList = document.getElementById('employeesList');
        employeesList.innerHTML = this.departmentData.employees?.map(emp => `
            <div class="overview-item">
                <strong>${emp.first_name} ${emp.last_name}</strong><br>
                <small>${emp.employee_number} - ${emp.employee_type || 'N/A'}</small>
            </div>
        `).join('') || 'No employees';
        
        const machinesList = document.getElementById('machinesList');
        machinesList.innerHTML = this.departmentData.machines?.map(machine => `
            <div class="overview-item">
                <strong>${machine.machine_name}</strong><br>
                <small>${machine.machine_number} - ${createStatusBadge(machine.status)}</small>
            </div>
        `).join('') || 'No machines';
        
        const stagesList = document.getElementById('stagesList');
        stagesList.innerHTML = this.departmentData.production_stages?.map(stage => `
            <div class="overview-item">
                <strong>${stage.stage_name}</strong> (Order: ${stage.stage_order})<br>
                <small>${stage.description || 'No description'}</small>
            </div>
        `).join('') || 'No production stages';
    }

    loadJobDetails() {
        const select = document.getElementById('jobSelect');
        const selectedOption = select.options[select.selectedIndex];
        const jobDetails = document.getElementById('jobDetails');
        
        if (selectedOption.value) {
            const job = JSON.parse(selectedOption.dataset.job);
            jobDetails.classList.remove('job-details-hidden');
            document.getElementById('jobOrderNumber').textContent = job.order_number;
            document.getElementById('jobProductName').textContent = job.product_name;
            document.getElementById('jobCurrentStatus').textContent = job.status;
            document.getElementById('jobId').value = job.id;
        } else {
            jobDetails.classList.add('job-details-hidden');
        }
    }

    async submitAllocation(e) {
        e.preventDefault();
        
        const allocationData = {
            employee_id: document.getElementById('employeeId').value,
            machine_id: document.getElementById('machineId').value,
            allocation_type: document.getElementById('allocationType').value,
            start_date: document.getElementById('startDate').value,
            end_date: document.getElementById('endDate').value || null,
            notes: document.getElementById('allocationNotes').value
        };
        
        try {
            const response = await fetch('/api/manager-controls/employee-machine-allocations', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                },
                body: JSON.stringify(allocationData)
            });
            const data = await response.json();
            
            if (data.success) {
                showAlert('Employee allocated successfully', 'success');
                hideModal('addAllocationModal');
                document.getElementById('allocationForm').reset();
                this.loadAllocations();
            } else {
                showAlert(data.message || 'Failed to allocate employee', 'danger');
            }
        } catch (error) {
            console.error('Error allocating employee:', error);
            showAlert('Failed to allocate employee', 'danger');
        }
    }

    async editAllocation(id) {
        try {
            const response = await fetch('/api/manager-controls/employee-machine-allocations', {
                headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
            });
            const data = await response.json();
            
            if (data.success) {
                const allocation = data.data.find(a => a.id === id);
                if (allocation) {
                    document.getElementById('editAllocationId').value = allocation.id;
                    document.getElementById('editAllocationType').value = allocation.allocation_type;
                    document.getElementById('editStartDate').value = allocation.start_date;
                    document.getElementById('editEndDate').value = allocation.end_date || '';
                    document.getElementById('editIsActive').value = allocation.is_active ? 'true' : 'false';
                    document.getElementById('editAllocationNotes').value = allocation.notes || '';
                    
                    showModal('editAllocationModal');
                }
            }
        } catch (error) {
            console.error('Error loading allocation:', error);
            showAlert('Failed to load allocation', 'danger');
        }
    }

    async updateAllocation(e) {
        e.preventDefault();
        
        const allocationId = document.getElementById('editAllocationId').value;
        const allocationData = {
            allocation_type: document.getElementById('editAllocationType').value,
            start_date: document.getElementById('editStartDate').value,
            end_date: document.getElementById('editEndDate').value || null,
            is_active: document.getElementById('editIsActive').value === 'true',
            notes: document.getElementById('editAllocationNotes').value
        };
        
        try {
            const response = await fetch(`/api/manager-controls/employee-machine-allocations/${allocationId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                },
                body: JSON.stringify(allocationData)
            });
            const data = await response.json();
            
            if (data.success) {
                showAlert('Allocation updated successfully', 'success');
                hideModal('editAllocationModal');
                this.loadAllocations();
            } else {
                showAlert(data.message || 'Failed to update allocation', 'danger');
            }
        } catch (error) {
            console.error('Error updating allocation:', error);
            showAlert('Failed to update allocation', 'danger');
        }
    }

    async toggleAllocation(id, isActive) {
        const action = isActive ? 'deactivate' : 'activate';
        if (!confirm(`Are you sure you want to ${action} this allocation?`)) return;
        
        try {
            const response = await fetch(`/api/manager-controls/employee-machine-allocations/${id}/toggle`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                },
                body: JSON.stringify({ is_active: !isActive })
            });
            const data = await response.json();
            
            if (data.success) {
                showAlert(`Allocation ${action}d successfully`, 'success');
                this.loadAllocations();
            } else {
                showAlert(data.message || `Failed to ${action} allocation`, 'danger');
            }
        } catch (error) {
            console.error(`Error ${action}ing allocation:`, error);
            showAlert(`Failed to ${action} allocation`, 'danger');
        }
    }

    async reassignJob(jobId) {
        const job = this.departmentJobs.find(j => j.id === jobId);
        if (job) {
            document.getElementById('jobId').value = job.id;
            document.getElementById('jobSelect').value = job.id;
            this.loadJobDetails();
            showModal('assignJobModal');
        }
    }

    async submitJobAssignment(e) {
        e.preventDefault();
        
        const jobId = document.getElementById('jobId').value || document.getElementById('jobSelect').value;
        const jobData = {
            assigned_employee_id: document.getElementById('assignEmployee').value,
            machine_id: document.getElementById('assignMachine').value,
            scheduled_date: document.getElementById('scheduledDate').value
        };
        
        try {
            const response = await fetch(`/api/manager-controls/jobs/${jobId}/assign`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                },
                body: JSON.stringify(jobData)
            });
            const data = await response.json();
            
            if (data.success) {
                showAlert('Job assigned successfully', 'success');
                hideModal('assignJobModal');
                document.getElementById('assignJobForm').reset();
                this.loadDepartmentJobs();
            } else {
                showAlert(data.message || 'Failed to assign job', 'danger');
            }
        } catch (error) {
            console.error('Error assigning job:', error);
            showAlert('Failed to assign job', 'danger');
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new ManagerDashboardPage();
});
