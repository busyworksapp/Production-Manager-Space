class PreventiveMaintenancePage {
    constructor() {
        this.allSchedules = [];
        this.allMachines = [];
        this.allTechnicians = [];
        this.allDepartments = [];
        this.init();
    }

    async init() {
        const user = getCurrentUser();
        if (user) {
            document.getElementById('username').textContent = `${user.first_name} ${user.last_name}`;
        }
        
        await Promise.all([
            this.loadMachines(),
            this.loadTechnicians(),
            this.loadDepartments()
        ]);
        
        this.populateFilters();
        this.attachEventListeners();
        await this.loadSchedules();
    }

    attachEventListeners() {
        const logoutBtn = document.querySelector('.logout-btn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', () => logout());
        }

        const createScheduleBtn = document.querySelector('.create-schedule-btn');
        if (createScheduleBtn) {
            createScheduleBtn.addEventListener('click', () => showModal('addScheduleModal'));
        }

        const filterDepartment = document.getElementById('filterDepartment');
        if (filterDepartment) {
            filterDepartment.addEventListener('change', () => this.renderSchedules());
        }

        const filterMachine = document.getElementById('filterMachine');
        if (filterMachine) {
            filterMachine.addEventListener('change', () => this.renderSchedules());
        }

        const filterPriority = document.getElementById('filterPriority');
        if (filterPriority) {
            filterPriority.addEventListener('change', () => this.renderSchedules());
        }

        const filterStatus = document.getElementById('filterStatus');
        if (filterStatus) {
            filterStatus.addEventListener('change', () => this.renderSchedules());
        }

        const scheduleForm = document.getElementById('scheduleForm');
        if (scheduleForm) {
            scheduleForm.addEventListener('submit', (e) => this.handleScheduleSubmit(e));
        }

        const performMaintenanceForm = document.getElementById('performMaintenanceForm');
        if (performMaintenanceForm) {
            performMaintenanceForm.addEventListener('submit', (e) => this.handlePerformMaintenance(e));
        }

        const closeScheduleModalBtn = document.querySelector('.close-schedule-modal-btn');
        if (closeScheduleModalBtn) {
            closeScheduleModalBtn.addEventListener('click', () => hideModal('addScheduleModal'));
        }

        const closePerformModalBtn = document.querySelector('.close-perform-modal-btn');
        if (closePerformModalBtn) {
            closePerformModalBtn.addEventListener('click', () => hideModal('performMaintenanceModal'));
        }

        const schedulesTable = document.getElementById('schedulesTable');
        if (schedulesTable) {
            schedulesTable.addEventListener('click', (e) => {
                if (e.target.classList.contains('view-schedule-btn')) {
                    const scheduleId = parseInt(e.target.getAttribute('data-schedule-id'));
                    this.viewScheduleDetails(scheduleId);
                } else if (e.target.classList.contains('perform-maintenance-btn')) {
                    const scheduleId = parseInt(e.target.getAttribute('data-schedule-id'));
                    this.performMaintenance(scheduleId);
                } else if (e.target.classList.contains('edit-schedule-btn')) {
                    const scheduleId = parseInt(e.target.getAttribute('data-schedule-id'));
                    this.editSchedule(scheduleId);
                }
            });
        }

        const logsTable = document.getElementById('logsTable');
        if (logsTable) {
            logsTable.addEventListener('click', (e) => {
                if (e.target.classList.contains('view-log-btn')) {
                    const logId = parseInt(e.target.getAttribute('data-log-id'));
                    this.viewLogDetails(logId);
                }
            });
        }
    }

    async loadMachines() {
        try {
            const response = await fetch(`${API_BASE_URL}/api/machines`, {
                headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
            });
            const data = await response.json();
            if (data.success) {
                this.allMachines = data.data;
                
                const machineSelect = document.getElementById('machineId');
                machineSelect.innerHTML = '<option value="">Select Machine</option>' +
                    this.allMachines.map(m => `<option value="${m.id}">${m.machine_name} (${m.machine_number})</option>`).join('');
            }
        } catch (error) {
            console.error('Error loading machines:', error);
        }
    }

    async loadTechnicians() {
        try {
            const response = await fetch(`${API_BASE_URL}/api/employees?type=technician`, {
                headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
            });
            const data = await response.json();
            if (data.success) {
                this.allTechnicians = data.data;
                
                const techSelect = document.getElementById('assignedTechnician');
                techSelect.innerHTML = '<option value="">Select Technician</option>' +
                    this.allTechnicians.map(t => `<option value="${t.id}">${t.first_name} ${t.last_name}</option>`).join('');
            }
        } catch (error) {
            console.error('Error loading technicians:', error);
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

    populateFilters() {
        const deptFilter = document.getElementById('filterDepartment');
        deptFilter.innerHTML = '<option value="">All Departments</option>' +
            this.allDepartments.map(d => `<option value="${d.id}">${d.name}</option>`).join('');
        
        const machineFilter = document.getElementById('filterMachine');
        machineFilter.innerHTML = '<option value="">All Machines</option>' +
            this.allMachines.map(m => `<option value="${m.id}">${m.machine_name}</option>`).join('');
    }

    async loadSchedules() {
        try {
            const response = await API.maintenance.getPreventiveSchedules({ is_active: 'true' });
            
            if (response.success) {
                this.allSchedules = response.data;
                this.renderSchedules();
            }
        } catch (error) {
            console.error('Error loading schedules:', error);
            showAlert('Failed to load schedules', 'danger');
        }
    }

    renderSchedules() {
        const tbody = document.getElementById('schedulesTable');
        
        let filtered = [...this.allSchedules];
        
        const deptFilter = document.getElementById('filterDepartment').value;
        const machineFilter = document.getElementById('filterMachine').value;
        const priorityFilter = document.getElementById('filterPriority').value;
        const statusFilter = document.getElementById('filterStatus').value;
        
        if (machineFilter) {
            filtered = filtered.filter(s => s.machine_id == machineFilter);
        }
        if (priorityFilter) {
            filtered = filtered.filter(s => s.priority === priorityFilter);
        }
        if (statusFilter) {
            filtered = filtered.filter(s => 
                statusFilter === 'active' ? s.is_active : !s.is_active
            );
        }
        
        if (filtered.length === 0) {
            tbody.innerHTML = '<tr><td colspan="10" class="table-center-text">No schedules found</td></tr>';
            return;
        }
        
        filtered.sort((a, b) => new Date(a.next_due_at) - new Date(b.next_due_at));
        
        tbody.innerHTML = filtered.map(schedule => {
            const dueDate = new Date(schedule.next_due_at);
            const today = new Date();
            const daysUntilDue = Math.ceil((dueDate - today) / (1000 * 60 * 60 * 24));
            
            let dueBadgeClass = 'badge-success';
            if (daysUntilDue < 0) {
                dueBadgeClass = 'badge-danger';
            } else if (daysUntilDue <= 7) {
                dueBadgeClass = 'badge-warning';
            }
            
            return `
                <tr>
                    <td>${schedule.schedule_name}</td>
                    <td>${schedule.machine_name || 'N/A'}</td>
                    <td>${this.getMachineDepartment(schedule.machine_id)}</td>
                    <td>${schedule.maintenance_type}</td>
                    <td>${this.formatFrequency(schedule.frequency_type, schedule.frequency_value)}</td>
                    <td>${formatDateTime(schedule.last_performed_at) || 'Never'}</td>
                    <td>
                        <span class="badge ${dueBadgeClass}">
                            ${formatDate(schedule.next_due_at)}
                            ${daysUntilDue < 0 ? '(OVERDUE)' : daysUntilDue === 0 ? '(TODAY)' : `(${daysUntilDue}d)`}
                        </span>
                    </td>
                    <td><span class="badge badge-${this.getPriorityClass(schedule.priority)}">${schedule.priority}</span></td>
                    <td>${schedule.technician_name || 'Unassigned'}</td>
                    <td>
                        <button class="btn btn-sm btn-primary view-schedule-btn" data-schedule-id="${schedule.id}">Details</button>
                        <button class="btn btn-sm btn-success perform-maintenance-btn" data-schedule-id="${schedule.id}">Perform</button>
                        <button class="btn btn-sm btn-warning edit-schedule-btn" data-schedule-id="${schedule.id}">Edit</button>
                    </td>
                </tr>
            `;
        }).join('');
    }

    getMachineDepartment(machineId) {
        const machine = this.allMachines.find(m => m.id === machineId);
        if (!machine) return 'N/A';
        
        const dept = this.allDepartments.find(d => d.id === machine.department_id);
        return dept ? dept.name : 'N/A';
    }

    formatFrequency(type, value) {
        const typeLabels = {
            daily: 'Daily',
            weekly: 'Weekly',
            monthly: 'Monthly',
            quarterly: 'Quarterly',
            yearly: 'Yearly',
            hours_based: 'Hours',
            cycles_based: 'Cycles'
        };
        
        return `Every ${value} ${typeLabels[type] || type}`;
    }

    getPriorityClass(priority) {
        const classes = {
            low: 'info',
            medium: 'primary',
            high: 'warning',
            critical: 'danger'
        };
        return classes[priority] || 'secondary';
    }

    async handleScheduleSubmit(e) {
        e.preventDefault();
        
        const checklist = document.getElementById('checklist').value;
        const partsRequired = document.getElementById('partsRequired').value;
        
        let checklistJSON = [];
        let partsJSON = [];
        
        try {
            if (checklist.trim()) {
                checklistJSON = JSON.parse(checklist);
            }
            if (partsRequired.trim()) {
                partsJSON = JSON.parse(partsRequired);
            }
        } catch (err) {
            showAlert('Invalid JSON format in checklist or parts required fields', 'danger');
            return;
        }
        
        const data = {
            schedule_name: document.getElementById('scheduleName').value,
            machine_id: parseInt(document.getElementById('machineId').value),
            maintenance_type: document.getElementById('maintenanceType').value,
            description: document.getElementById('description').value,
            frequency_type: document.getElementById('frequencyType').value,
            frequency_value: parseInt(document.getElementById('frequencyValue').value),
            estimated_duration_minutes: parseInt(document.getElementById('estimatedDuration').value) || null,
            priority: document.getElementById('priority').value,
            assigned_technician_id: document.getElementById('assignedTechnician').value ? 
                parseInt(document.getElementById('assignedTechnician').value) : null,
            checklist: checklistJSON,
            parts_required: partsJSON
        };
        
        try {
            const response = await API.maintenance.createPreventiveSchedule(data);
            
            if (response.success) {
                showAlert('Schedule created successfully', 'success');
                hideModal('addScheduleModal');
                document.getElementById('scheduleForm').reset();
                await this.loadSchedules();
            }
        } catch (error) {
            showAlert(error.message || 'Failed to create schedule', 'danger');
        }
    }

    async editSchedule(scheduleId) {
        const schedule = this.allSchedules.find(s => s.id === scheduleId);
        if (!schedule) return;
        
        document.getElementById('scheduleName').value = schedule.schedule_name;
        document.getElementById('machineId').value = schedule.machine_id;
        document.getElementById('maintenanceType').value = schedule.maintenance_type;
        document.getElementById('description').value = schedule.description || '';
        document.getElementById('frequencyType').value = schedule.frequency_type;
        document.getElementById('frequencyValue').value = schedule.frequency_value;
        document.getElementById('estimatedDuration').value = schedule.estimated_duration_minutes || '';
        document.getElementById('priority').value = schedule.priority;
        document.getElementById('assignedTechnician').value = schedule.assigned_technician_id || '';
        
        try {
            document.getElementById('checklist').value = schedule.checklist ? 
                JSON.stringify(JSON.parse(schedule.checklist), null, 2) : '';
            document.getElementById('partsRequired').value = schedule.parts_required ? 
                JSON.stringify(JSON.parse(schedule.parts_required), null, 2) : '';
        } catch (err) {
            document.getElementById('checklist').value = '';
            document.getElementById('partsRequired').value = '';
        }
        
        document.getElementById('isActive').checked = schedule.is_active;
        
        showModal('addScheduleModal');
    }

    async performMaintenance(scheduleId) {
        document.getElementById('performScheduleId').value = scheduleId;
        document.getElementById('performedAt').value = new Date().toISOString().slice(0, 16);
        
        const schedule = this.allSchedules.find(s => s.id === scheduleId);
        if (schedule && schedule.estimated_duration_minutes) {
            document.getElementById('durationMinutes').value = schedule.estimated_duration_minutes;
        }
        
        if (schedule && schedule.checklist) {
            try {
                const checklistArray = JSON.parse(schedule.checklist);
                const checklistResults = {};
                checklistArray.forEach(item => {
                    checklistResults[item] = 'completed';
                });
                document.getElementById('checklistResults').value = JSON.stringify(checklistResults, null, 2);
            } catch (err) {
                console.error('Error parsing checklist:', err);
            }
        }
        
        showModal('performMaintenanceModal');
    }

    async handlePerformMaintenance(e) {
        e.preventDefault();
        
        const scheduleId = parseInt(document.getElementById('performScheduleId').value);
        
        const checklistResults = document.getElementById('checklistResults').value;
        const partsUsed = document.getElementById('partsUsed').value;
        
        let checklistJSON = {};
        let partsJSON = [];
        
        try {
            if (checklistResults.trim()) {
                checklistJSON = JSON.parse(checklistResults);
            }
            if (partsUsed.trim()) {
                partsJSON = JSON.parse(partsUsed);
            }
        } catch (err) {
            showAlert('Invalid JSON format in checklist results or parts used fields', 'danger');
            return;
        }
        
        const data = {
            performed_at: document.getElementById('performedAt').value,
            duration_minutes: parseInt(document.getElementById('durationMinutes').value),
            checklist_results: checklistJSON,
            parts_used: partsJSON,
            observations: document.getElementById('observations').value,
            status: document.getElementById('status').value,
            next_recommended_date: document.getElementById('nextRecommendedDate').value || null
        };
        
        try {
            const response = await API.maintenance.logPreventiveMaintenance(scheduleId, data);
            
            if (response.success) {
                showAlert('Maintenance logged successfully', 'success');
                hideModal('performMaintenanceModal');
                document.getElementById('performMaintenanceForm').reset();
                await this.loadSchedules();
            }
        } catch (error) {
            showAlert(error.message || 'Failed to log maintenance', 'danger');
        }
    }

    async viewScheduleDetails(scheduleId) {
        try {
            const response = await fetch(`${API_BASE_URL}/api/maintenance/preventive/${scheduleId}`, {
                headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
            });
            const data = await response.json();
            
            if (data.success) {
                this.renderScheduleLogs(data.data.logs || []);
            }
        } catch (error) {
            showAlert('Failed to load schedule details', 'danger');
        }
    }

    renderScheduleLogs(logs) {
        const tbody = document.getElementById('logsTable');
        
        if (logs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="table-center-text">No maintenance logs found</td></tr>';
            return;
        }
        
        tbody.innerHTML = logs.map(log => `
            <tr>
                <td>${log.schedule_id}</td>
                <td>${formatDateTime(log.performed_at)}</td>
                <td>${log.performed_by_name || 'N/A'}</td>
                <td>${log.duration_minutes} min</td>
                <td><span class="badge badge-${this.getStatusClass(log.status)}">${log.status}</span></td>
                <td>${formatDate(log.next_recommended_date) || 'N/A'}</td>
                <td>
                    <button class="btn btn-sm btn-primary view-log-btn" data-log-id="${log.id}">View Details</button>
                </td>
            </tr>
        `).join('');
    }

    getStatusClass(status) {
        const classes = {
            completed: 'success',
            partially_completed: 'warning',
            skipped: 'secondary',
            rescheduled: 'info'
        };
        return classes[status] || 'secondary';
    }

    viewLogDetails(logId) {
        showAlert('Log details view coming soon', 'info');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new PreventiveMaintenancePage();
});
