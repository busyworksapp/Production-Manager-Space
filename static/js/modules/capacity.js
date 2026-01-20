let capacityData = [];
let allDepartments = [];
let currentDepartmentId = null;

async function init() {
    const user = getCurrentUser();
    if (user) {
        document.getElementById('username').textContent = `${user.first_name} ${user.last_name}`;
    }
    
    setDefaultDates();
    await loadDepartments();
    await loadCapacityData();
    
    setupEventListeners();
}

function setupEventListeners() {
    document.getElementById('logoutBtn').addEventListener('click', () => logout());
    document.getElementById('refreshBtn').addEventListener('click', () => loadCapacityData());
    document.getElementById('loadCapacityBtn').addEventListener('click', () => loadCapacityData());
    document.getElementById('validateCapacityBtn').addEventListener('click', () => showModal('validateScheduleModal'));
    document.getElementById('closeDepartmentDetailBtn').addEventListener('click', () => hideModal('departmentDetailModal'));
    document.getElementById('cancelUpdateCapacityBtn').addEventListener('click', () => hideModal('updateCapacityModal'));
    document.getElementById('cancelValidateBtn').addEventListener('click', () => hideModal('validateScheduleModal'));
    
    document.getElementById('updateCapacityForm').addEventListener('submit', handleUpdateCapacityTarget);
    document.getElementById('validateScheduleForm').addEventListener('submit', handleValidateSchedule);
}

function setDefaultDates() {
    const today = new Date();
    const thirtyDaysLater = new Date(today);
    thirtyDaysLater.setDate(thirtyDaysLater.getDate() + 30);
    
    document.getElementById('startDate').value = today.toISOString().split('T')[0];
    document.getElementById('endDate').value = thirtyDaysLater.toISOString().split('T')[0];
}

async function loadDepartments() {
    try {
        const response = await API.departments.getAll();
        if (response.success) {
            allDepartments = response.data;
            populateDepartmentSelect();
        }
    } catch (error) {
        console.error('Error loading departments:', error);
    }
}

function populateDepartmentSelect() {
    const select = document.getElementById('validateDepartment');
    select.innerHTML = '<option value="">Select Department</option>' +
        allDepartments.map(d => `<option value="${d.id}">${d.name}</option>`).join('');
}

async function loadCapacityData() {
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;
    
    if (!startDate || !endDate) {
        showAlert('Please select both start and end dates', 'warning');
        return;
    }
    
    try {
        const response = await fetch(
            `${API_BASE_URL}/api/capacity-planning/departments?start_date=${startDate}&end_date=${endDate}`,
            {
                headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
            }
        );
        const data = await response.json();
        
        if (data.success) {
            capacityData = data.data;
            renderCapacityOverview(data.data);
            renderCapacityTable(data.data);
        } else {
            showAlert(data.message || 'Failed to load capacity data', 'danger');
        }
    } catch (error) {
        console.error('Error loading capacity data:', error);
        showAlert('Failed to load capacity data', 'danger');
    }
}

function renderCapacityOverview(data) {
    const container = document.getElementById('capacityOverview');
    
    const totalDepartments = data.length;
    const overbooked = data.filter(d => d.capacity_status === 'overbooked').length;
    const highUtilization = data.filter(d => d.capacity_status === 'high').length;
    const avgUtilization = data.reduce((sum, d) => sum + (d.capacity_percentage || 0), 0) / totalDepartments;
    
    container.innerHTML = `
        <div class="stat-card">
            <div class="stat-label">Total Departments</div>
            <div class="stat-value">${totalDepartments}</div>
        </div>
        <div class="stat-card ${overbooked > 0 ? 'stat-danger' : ''}">
            <div class="stat-label">Overbooked</div>
            <div class="stat-value">${overbooked}</div>
        </div>
        <div class="stat-card ${highUtilization > 0 ? 'stat-warning' : ''}">
            <div class="stat-label">High Utilization</div>
            <div class="stat-value">${highUtilization}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Avg Utilization</div>
            <div class="stat-value">${avgUtilization.toFixed(1)}%</div>
        </div>
    `;
}

function renderCapacityTable(data) {
    const tbody = document.getElementById('capacityTable');
    
    if (data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" class="table-center-text">No capacity data available</td></tr>';
        return;
    }
    
    tbody.innerHTML = data.map(dept => {
        const available = dept.capacity_target - (dept.capacity_used || 0);
        const percentage = dept.capacity_percentage || 0;
        
        return `
            <tr class="capacity-row" data-dept-id="${dept.id}">
                <td><strong>${dept.name}</strong></td>
                <td>${dept.employee_count || 0}</td>
                <td>${dept.machine_count || 0}</td>
                <td>${formatNumber(dept.capacity_target)}</td>
                <td>${formatNumber(dept.capacity_used || 0)}</td>
                <td>${formatNumber(available)}</td>
                <td>
                    <div class="utilization-flex">
                        <div class="progress-bar utilization-bar">
                            <div class="progress-fill ${getProgressClass(percentage)}" 
                                 style="width: ${Math.min(percentage, 100)}%">
                            </div>
                        </div>
                        <span class="utilization-value">${percentage.toFixed(1)}%</span>
                    </div>
                </td>
                <td>
                    <span class="badge badge-${getStatusBadgeClass(dept.capacity_status)}">
                        ${dept.capacity_status}
                    </span>
                </td>
                <td>
                    <button class="btn btn-sm btn-primary view-detail-btn" data-dept-id="${dept.id}">
                        View Jobs
                    </button>
                    <button class="btn btn-sm btn-secondary update-target-btn" 
                            data-dept-id="${dept.id}" 
                            data-dept-name="${dept.name}"
                            data-current-target="${dept.capacity_target}">
                        Update Target
                    </button>
                </td>
            </tr>
        `;
    }).join('');
    
    document.querySelectorAll('.view-detail-btn').forEach(btn => {
        btn.addEventListener('click', () => viewDepartmentDetail(parseInt(btn.dataset.deptId)));
    });
    
    document.querySelectorAll('.update-target-btn').forEach(btn => {
        btn.addEventListener('click', () => showUpdateCapacityModal(
            parseInt(btn.dataset.deptId),
            btn.dataset.deptName,
            parseInt(btn.dataset.currentTarget)
        ));
    });
}

function getProgressClass(percentage) {
    if (percentage >= 100) return 'progress-danger';
    if (percentage >= 80) return 'progress-warning';
    if (percentage >= 50) return 'progress-info';
    return 'progress-success';
}

function getStatusBadgeClass(status) {
    const classes = {
        'overbooked': 'danger',
        'high': 'warning',
        'medium': 'info',
        'low': 'success'
    };
    return classes[status] || 'secondary';
}

async function viewDepartmentDetail(departmentId) {
    currentDepartmentId = departmentId;
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;
    
    try {
        const response = await fetch(
            `${API_BASE_URL}/api/capacity-planning/departments/${departmentId}?start_date=${startDate}&end_date=${endDate}`,
            {
                headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
            }
        );
        const data = await response.json();
        
        if (data.success) {
            renderDepartmentDetail(data.data);
            showModal('departmentDetailModal');
        } else {
            showAlert(data.message || 'Failed to load department details', 'danger');
        }
    } catch (error) {
        console.error('Error loading department details:', error);
        showAlert('Failed to load department details', 'danger');
    }
}

function renderDepartmentDetail(data) {
    document.getElementById('departmentDetailTitle').textContent = 
        `${data.department.name} - Capacity Details`;
    
    document.getElementById('detailCapacityTarget').textContent = 
        formatNumber(data.capacity_target);
    document.getElementById('detailScheduled').textContent = 
        formatNumber(data.scheduled_quantity);
    document.getElementById('detailAvailable').textContent = 
        formatNumber(data.available_capacity);
    
    const tbody = document.getElementById('departmentJobsTable');
    
    if (data.jobs.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="table-center-text">No jobs scheduled</td></tr>';
        return;
    }
    
    tbody.innerHTML = data.jobs.map(job => `
        <tr>
            <td>${formatDate(job.scheduled_date)}</td>
            <td>${job.order_number || 'N/A'}</td>
            <td>${job.customer_name || 'N/A'}</td>
            <td>${job.product_name || 'N/A'}</td>
            <td>${formatNumber(job.scheduled_quantity || 0)}</td>
            <td>${job.machine_name || 'N/A'}</td>
            <td>${job.employee_name || 'Unassigned'}</td>
            <td><span class="badge badge-${getJobStatusClass(job.status)}">${job.status}</span></td>
        </tr>
    `).join('');
}

function getJobStatusClass(status) {
    const classes = {
        'scheduled': 'info',
        'in_progress': 'warning',
        'completed': 'success',
        'cancelled': 'secondary'
    };
    return classes[status] || 'secondary';
}

function showUpdateCapacityModal(departmentId, departmentName, currentTarget) {
    document.getElementById('updateDepartmentId').value = departmentId;
    document.getElementById('updateDepartmentName').value = departmentName;
    document.getElementById('newCapacityTarget').value = currentTarget;
    showModal('updateCapacityModal');
}

async function handleUpdateCapacityTarget(e) {
    e.preventDefault();
    
    const departmentId = document.getElementById('updateDepartmentId').value;
    const newTarget = parseInt(document.getElementById('newCapacityTarget').value);
    
    try {
        const response = await fetch(
            `${API_BASE_URL}/api/capacity-planning/departments/${departmentId}/target`,
            {
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ capacity_target: newTarget })
            }
        );
        const data = await response.json();
        
        if (data.success) {
            showAlert('Capacity target updated successfully', 'success');
            hideModal('updateCapacityModal');
            await loadCapacityData();
        } else {
            showAlert(data.message || 'Failed to update capacity target', 'danger');
        }
    } catch (error) {
        console.error('Error updating capacity target:', error);
        showAlert('Failed to update capacity target', 'danger');
    }
}

async function handleValidateSchedule(e) {
    e.preventDefault();
    
    const departmentId = document.getElementById('validateDepartment').value;
    const scheduledDate = document.getElementById('validateDate').value;
    const quantity = parseInt(document.getElementById('validateQuantity').value);
    
    try {
        const response = await fetch(
            `${API_BASE_URL}/api/capacity-planning/validate`,
            {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    department_id: parseInt(departmentId),
                    scheduled_date: scheduledDate,
                    quantity: quantity
                })
            }
        );
        const data = await response.json();
        
        if (data.success) {
            renderValidationResults(data.data);
        } else {
            showAlert(data.message || 'Failed to validate capacity', 'danger');
        }
    } catch (error) {
        console.error('Error validating capacity:', error);
        showAlert('Failed to validate capacity', 'danger');
    }
}

function renderValidationResults(results) {
    const container = document.getElementById('validationResults');
    container.classList.remove('validation-results-hidden');
    container.classList.add('validation-results-visible');
    
    const statusClass = results.valid ? 'success' : 'danger';
    const statusText = results.valid ? 'Valid - Capacity Available' : 'Invalid - Capacity Exceeded';
    
    let warningHTML = '';
    if (results.warning) {
        const severityClass = results.severity === 'error' ? 'danger' : 'warning';
        warningHTML = `<div class="alert alert-${severityClass}">${results.warning}</div>`;
    }
    
    container.innerHTML = `
        <div class="card">
            <h4>Validation Results</h4>
            ${warningHTML}
            <div class="alert alert-${statusClass}">
                <strong>${statusText}</strong>
            </div>
            <table class="table">
                <tr>
                    <td><strong>Capacity Target:</strong></td>
                    <td>${formatNumber(results.capacity_target)}</td>
                </tr>
                <tr>
                    <td><strong>Currently Scheduled:</strong></td>
                    <td>${formatNumber(results.current_scheduled)}</td>
                </tr>
                <tr>
                    <td><strong>Requested Quantity:</strong></td>
                    <td>${formatNumber(results.requested_quantity)}</td>
                </tr>
                <tr>
                    <td><strong>Total After Scheduling:</strong></td>
                    <td class="${results.valid ? '' : 'text-danger'}">${formatNumber(results.total_after_scheduling)}</td>
                </tr>
                <tr>
                    <td><strong>Capacity Utilization:</strong></td>
                    <td>
                        <div class="progress-bar validation-bar-container">
                            <div class="progress-fill ${getProgressClass(results.capacity_percentage)}" 
                                 style="width: ${Math.min(results.capacity_percentage, 100)}%">
                            </div>
                        </div>
                        ${results.capacity_percentage.toFixed(1)}%
                    </td>
                </tr>
                <tr>
                    <td><strong>Available Capacity:</strong></td>
                    <td>${formatNumber(results.available_capacity)}</td>
                </tr>
                ${results.excess_quantity > 0 ? `
                <tr>
                    <td><strong>Excess Quantity:</strong></td>
                    <td class="text-danger">${formatNumber(results.excess_quantity)}</td>
                </tr>
                ` : ''}
            </table>
        </div>
    `;
}

function formatNumber(num) {
    return num ? num.toLocaleString() : '0';
}

document.addEventListener('DOMContentLoaded', init);
