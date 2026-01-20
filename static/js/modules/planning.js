let allSchedules = [];
let allOrders = [];
let allDepartments = [];
let allStages = [];
let allMachines = [];
let allEmployees = [];

async function loadSchedule() {
    const department = document.getElementById('filterDepartment').value;
    const status = document.getElementById('filterStatus').value;
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;

    const params = new URLSearchParams();
    if (department) params.append('department_id', department);
    if (status) params.append('status', status);
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);

    try {
        const response = await fetch(`/api/orders/schedules?${params.toString()}`, {
            headers: getAuthHeaders()
        });
        const data = await response.json();

        if (data.success) {
            allSchedules = data.data;
            renderSchedule(data.data);
        }
    } catch (error) {
        console.error('Error loading schedule:', error);
        showNotification('Failed to load schedule', 'error');
    }

    await loadCapacityOverview();
}

async function loadCapacityOverview() {
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;

    const params = new URLSearchParams();
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);

    try {
        const response = await fetch(`/api/capacity-planning/departments?${params.toString()}`, {
            headers: getAuthHeaders()
        });
        const data = await response.json();

        if (data.success) {
            renderCapacityOverview(data.data);
        }
    } catch (error) {
        console.error('Error loading capacity:', error);
    }
}

function renderCapacityOverview(departments) {
    const container = document.getElementById('capacityOverview');
    if (!container) return;

    container.innerHTML = departments.map(dept => {
        const percentage = dept.capacity_percentage || 0;
        const barClass = percentage >= 100 ? 'capacity-bar-danger' : percentage >= 80 ? 'capacity-bar-warning' : 'capacity-bar-success';
        return `
        <div class="card capacity-card">
            <div class="capacity-card-title">${escapeHtml(dept.name)}</div>
            <div class="capacity-stats">
                <div class="capacity-stat-row">
                    <span>Capacity Used:</span>
                    <span>${percentage}%</span>
                </div>
                <div class="capacity-bar-bg">
                    <div class="capacity-bar-fill ${barClass}" style="width: ${Math.min(100, percentage)}%;"></div>
                </div>
            </div>
        </div>
    `;
    }).join('');
}

function renderSchedule(schedules) {
    const tbody = document.getElementById('scheduleTable');
    if (!tbody) return;

    if (schedules.length === 0) {
        tbody.innerHTML = '<tr><td colspan="11" class="schedule-table-center">No schedules found</td></tr>';
        return;
    }

    tbody.innerHTML = schedules.map(schedule => `
        <tr>
            <td>${schedule.scheduled_date || '-'}</td>
            <td>${escapeHtml(schedule.order_number || '-')}</td>
            <td>${escapeHtml(schedule.customer_name || '-')}</td>
            <td>${escapeHtml(schedule.product_name || '-')}</td>
            <td>${escapeHtml(schedule.department_name || '-')}</td>
            <td>${escapeHtml(schedule.stage_name || '-')}</td>
            <td>${escapeHtml(schedule.machine_name || '-')}</td>
            <td>${escapeHtml(schedule.employee_name || '-')}</td>
            <td>${schedule.scheduled_quantity || 0}</td>
            <td><span class="badge badge-${getStatusColor(schedule.status)}">${schedule.status || 'scheduled'}</span></td>
            <td>
                <button class="btn btn-sm btn-secondary edit-schedule-btn" data-schedule-id="${schedule.id}">Edit</button>
                ${schedule.status === 'on_hold' ? `<button class="btn btn-sm btn-warning suggest-alternatives-btn" data-schedule-id="${schedule.id}">Suggest</button>` : ''}
            </td>
        </tr>
    `).join('');
    
    tbody.querySelectorAll('.edit-schedule-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const scheduleId = parseInt(e.target.getAttribute('data-schedule-id'));
            editSchedule(scheduleId);
        });
    });
    
    tbody.querySelectorAll('.suggest-alternatives-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const scheduleId = parseInt(e.target.getAttribute('data-schedule-id'));
            suggestAlternatives(scheduleId);
        });
    });
}

async function loadUnscheduledOrders() {
    try {
        const response = await fetch('/api/orders?status=unscheduled', {
            headers: getAuthHeaders()
        });
        const data = await response.json();

        if (data.success) {
            const select = document.getElementById('orderId');
            if (select) {
                select.innerHTML = '<option value="">Select Order</option>' +
                    data.data.map(order => `<option value="${order.id}">${escapeHtml(order.order_number)} - ${escapeHtml(order.customer_name)}</option>`).join('');
            }
        }
    } catch (error) {
        console.error('Error loading orders:', error);
    }
}

async function loadDepartments() {
    try {
        const response = await fetch('/api/departments', {
            headers: getAuthHeaders()
        });
        const data = await response.json();

        if (data.success) {
            allDepartments = data.data;
            const selects = ['filterDepartment', 'departmentId'];
            selects.forEach(selectId => {
                const select = document.getElementById(selectId);
                if (select) {
                    const hasAll = selectId.startsWith('filter');
                    select.innerHTML = (hasAll ? '<option value="">All Departments</option>' : '<option value="">Select Department</option>') +
                        data.data.map(dept => `<option value="${dept.id}">${escapeHtml(dept.name)}</option>`).join('');
                }
            });
        }
    } catch (error) {
        console.error('Error loading departments:', error);
    }
}

async function loadStagesAndMachines() {
    const deptId = document.getElementById('departmentId').value;
    const scheduledDate = document.getElementById('scheduledDate').value;
    if (!deptId) return;

    try {
        const startDate = scheduledDate || new Date().toISOString().split('T')[0];
        const endDate = new Date(new Date(startDate).getTime() + 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];

        const [stagesResp, machinesResp, employeesResp] = await Promise.all([
            fetch(`/api/departments/${deptId}/stages`, { headers: getAuthHeaders() }),
            fetch(`/api/machines/availability?department_id=${deptId}&start_date=${startDate}&end_date=${endDate}`, { headers: getAuthHeaders() }),
            fetch(`/api/employees?department_id=${deptId}&type=operator`, { headers: getAuthHeaders() })
        ]);

        const stagesData = await stagesResp.json();
        const machinesData = await machinesResp.json();
        const employeesData = await employeesResp.json();

        const stageSelect = document.getElementById('stageId');
        if (stageSelect && stagesData.success) {
            stageSelect.innerHTML = '<option value="">No Specific Stage</option>' +
                stagesData.data.map(stage => `<option value="${stage.id}">${escapeHtml(stage.stage_name)}</option>`).join('');
        }

        const machineSelect = document.getElementById('machineId');
        if (machineSelect && machinesData.success) {
            allMachines = machinesData.data;
            machineSelect.innerHTML = '<option value="">No Specific Machine</option>' +
                machinesData.data
                    .filter(m => m.status !== 'broken' && m.status !== 'retired')
                    .map(machine => {
                        const statusIcon = getMachineAvailabilityIcon(machine.availability_status);
                        const statusText = getMachineAvailabilityText(machine.availability_status);
                        return `<option value="${machine.id}" data-availability="${machine.availability_status}">${escapeHtml(machine.machine_name)} ${statusIcon} (${statusText})</option>`;
                    }).join('');
            
            if (machinesData.data.length > 0) {
                showMachineAvailabilityLegend();
            }
        }

        const employeeSelect = document.getElementById('assignedEmployeeId');
        if (employeeSelect && employeesData.success) {
            employeeSelect.innerHTML = '<option value="">No Assignment</option>' +
                employeesData.data.map(emp => `<option value="${emp.id}">${escapeHtml(emp.first_name)} ${escapeHtml(emp.last_name)}</option>`).join('');
        }
    } catch (error) {
        console.error('Error loading department data:', error);
    }
}

function getMachineAvailabilityIcon(status) {
    const icons = {
        'available': '✓',
        'limited': '⚠',
        'busy': '⚠⚠',
        'maintenance': '🔧',
        'unavailable': '✗'
    };
    return icons[status] || '';
}

function getMachineAvailabilityText(status) {
    const texts = {
        'available': 'Available',
        'limited': 'Limited',
        'busy': 'Busy',
        'maintenance': 'Maintenance',
        'unavailable': 'Unavailable'
    };
    return texts[status] || status;
}

function showMachineAvailabilityLegend() {
    const machineGroup = document.getElementById('machineId')?.closest('.form-group');
    if (!machineGroup) return;
    
    let legend = machineGroup.querySelector('.availability-legend');
    if (!legend) {
        legend = document.createElement('small');
        legend.className = 'availability-legend';
        legend.innerHTML = `
            <strong>Availability:</strong> 
            ✓ Available | ⚠ Limited | ⚠⚠ Busy | 🔧 Maintenance | ✗ Unavailable
        `;
        machineGroup.appendChild(legend);
    }
}

async function validateCapacity() {
    const deptId = document.getElementById('departmentId').value;
    const date = document.getElementById('scheduledDate').value;
    const qty = document.getElementById('scheduledQuantity').value;

    if (!deptId || !date || !qty) return;

    try {
        const response = await fetch('/api/capacity-planning/validate', {
            method: 'POST',
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                department_id: parseInt(deptId),
                scheduled_date: date,
                quantity: parseInt(qty)
            })
        });
        const data = await response.json();

        const validationDiv = document.getElementById('capacityValidation');
        if (data.success && validationDiv) {
            const result = data.data;
            if (result.warning) {
                validationDiv.className = `alert alert-${result.severity}`;
                validationDiv.innerHTML = `
                    ${result.warning} 
                    <button class="btn btn-sm btn-primary capacity-alternatives-btn">
                        View Alternatives
                    </button>
                `;
                validationDiv.classList.remove('capacity-validation-hidden');
                
                const altBtn = validationDiv.querySelector('.capacity-alternatives-btn');
                if (altBtn) {
                    altBtn.addEventListener('click', showCapacityAlternatives);
                }
            } else {
                validationDiv.classList.add('capacity-validation-hidden');
            }
        }
    } catch (error) {
        console.error('Error validating capacity:', error);
    }
}

async function showCapacityAlternatives() {
    const deptId = document.getElementById('departmentId').value;
    const date = document.getElementById('scheduledDate').value;
    const qty = document.getElementById('scheduledQuantity').value;
    const orderId = document.getElementById('orderId').value;

    if (!deptId || !date || !qty) return;

    try {
        const response = await fetch('/api/capacity-planning/suggest-alternatives', {
            method: 'POST',
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                department_id: parseInt(deptId),
                scheduled_date: date,
                quantity: parseInt(qty),
                order_id: orderId ? parseInt(orderId) : null
            })
        });
        const data = await response.json();

        if (data.success) {
            showAlternativesModal(data.data);
        } else {
            showNotification(data.message || 'Failed to load alternatives', 'error');
        }
    } catch (error) {
        console.error('Error loading alternatives:', error);
        showNotification('Failed to load alternative suggestions', 'error');
    }
}

function showAlternativesModal(alternatives) {
    const modalHtml = `
        <div id="alternativesModal" class="modal active">
            <div class="modal-content" style="max-width: 800px;">
                <div class="modal-header">Alternative Scheduling Options</div>
                <div>
                    <p><strong>Original Request:</strong> ${alternatives.original_department} on ${alternatives.original_date} (${alternatives.requested_quantity} units)</p>
                    
                    ${alternatives.date_alternatives.length > 0 ? `
                        <h3 style="margin-top: 1.5rem;">Alternative Dates (Same Department)</h3>
                        <div style="max-height: 300px; overflow-y: auto;">
                            ${alternatives.date_alternatives.map(alt => `
                                <div class="card" style="padding: 1rem; margin: 0.5rem 0; cursor: pointer; border: 2px solid var(--color-border);" 
                                     onclick="applyAlternativeDate('${alt.suggested_date}')">
                                    <div style="display: flex; justify-content: space-between; align-items: center;">
                                        <div>
                                            <strong>${alt.suggested_date}</strong> 
                                            <span class="badge badge-info">+${alt.days_from_original} days</span>
                                            <br>
                                            <small>${alt.reason}</small>
                                        </div>
                                        <div style="text-align: right;">
                                            <div>Available: <strong>${alt.available_capacity}</strong> units</div>
                                            <div>Utilization: <strong>${alt.capacity_percentage_after}%</strong></div>
                                        </div>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    ` : '<p style="color: var(--color-text-secondary);">No alternative dates available in the next 2 weeks</p>'}
                    
                    ${alternatives.department_alternatives.length > 0 ? `
                        <h3 style="margin-top: 1.5rem;">Alternative Departments (Same Date)</h3>
                        <div style="max-height: 300px; overflow-y: auto;">
                            ${alternatives.department_alternatives.map(alt => `
                                <div class="card" style="padding: 1rem; margin: 0.5rem 0; cursor: pointer; border: 2px solid var(--color-border);" 
                                     onclick="applyAlternativeDepartment(${alt.department_id}, '${escapeHtml(alt.department_name)}')">
                                    <div style="display: flex; justify-content: space-between; align-items: center;">
                                        <div>
                                            <strong>${escapeHtml(alt.department_name)}</strong>
                                            <br>
                                            <small>${alt.reason}</small>
                                        </div>
                                        <div style="text-align: right;">
                                            <div>Available: <strong>${alt.available_capacity}</strong> units</div>
                                            <div>Utilization: <strong>${alt.capacity_percentage_after}%</strong></div>
                                        </div>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    ` : '<p style="color: var(--color-text-secondary);">No alternative departments available</p>'}
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" onclick="closeAlternativesModal()">Cancel</button>
                </div>
            </div>
        </div>
    `;
    
    const existing = document.getElementById('alternativesModal');
    if (existing) existing.remove();
    
    document.body.insertAdjacentHTML('beforeend', modalHtml);
}

function applyAlternativeDate(date) {
    document.getElementById('scheduledDate').value = date;
    closeAlternativesModal();
    validateCapacity();
    showNotification('Date updated. Please review and submit.', 'success');
}

function applyAlternativeDepartment(deptId, deptName) {
    document.getElementById('departmentId').value = deptId;
    closeAlternativesModal();
    loadStagesAndMachines();
    validateCapacity();
    showNotification(`Department changed to ${deptName}. Please review and submit.`, 'success');
}

function closeAlternativesModal() {
    const modal = document.getElementById('alternativesModal');
    if (modal) modal.remove();
}

async function suggestAlternatives(scheduleId) {
    try {
        const response = await fetch(`/api/orders/schedules/${scheduleId}/alternatives`, {
            headers: getAuthHeaders()
        });
        const data = await response.json();

        if (data.success) {
            const listDiv = document.getElementById('alternativeOrdersList');
            if (listDiv) {
                listDiv.innerHTML = data.data.map(order => `
                    <div class="card" style="padding: 1rem; margin: 0.5rem 0;">
                        <strong>${escapeHtml(order.order_number)}</strong> - ${escapeHtml(order.customer_name)}
                        <p style="margin: 0.5rem 0;">${escapeHtml(order.product_name)} (Qty: ${order.quantity})</p>
                        <button class="btn btn-sm btn-primary" onclick="scheduleAlternative(${order.id})">Schedule This</button>
                    </div>
                `).join('');
            }
            showModal('suggestAlternativeModal');
        }
    } catch (error) {
        console.error('Error loading alternatives:', error);
        showNotification('Failed to load alternative orders', 'error');
    }
}

document.getElementById('scheduleJobForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();

    const formData = {
        order_id: parseInt(document.getElementById('orderId').value),
        department_id: parseInt(document.getElementById('departmentId').value),
        stage_id: document.getElementById('stageId').value ? parseInt(document.getElementById('stageId').value) : null,
        scheduled_date: document.getElementById('scheduledDate').value,
        scheduled_quantity: parseInt(document.getElementById('scheduledQuantity').value),
        machine_id: document.getElementById('machineId').value ? parseInt(document.getElementById('machineId').value) : null,
        assigned_employee_id: document.getElementById('assignedEmployeeId').value ? parseInt(document.getElementById('assignedEmployeeId').value) : null,
        notes: document.getElementById('notes').value
    };

    try {
        const response = await fetch('/api/orders/schedules', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(formData)
        });
        const data = await response.json();

        if (data.success) {
            showNotification('Job scheduled successfully', 'success');
            hideModal('scheduleJobModal');
            loadSchedule();
            document.getElementById('scheduleJobForm').reset();
        } else {
            showNotification(data.error || 'Failed to schedule job', 'error');
        }
    } catch (error) {
        console.error('Error scheduling job:', error);
        showNotification('Failed to schedule job', 'error');
    }
});

document.addEventListener('DOMContentLoaded', () => {
    const today = new Date().toISOString().split('T')[0];
    const next30 = new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
    
    document.getElementById('startDate').value = today;
    document.getElementById('endDate').value = next30;

    const scheduledDateInput = document.getElementById('scheduledDate');
    if (scheduledDateInput) {
        scheduledDateInput.addEventListener('change', () => {
            const deptId = document.getElementById('departmentId')?.value;
            if (deptId) {
                loadStagesAndMachines();
            }
        });
    }

    const scheduledQtyInput = document.getElementById('scheduledQuantity');
    if (scheduledQtyInput) {
        scheduledQtyInput.addEventListener('change', validateCapacity);
        scheduledQtyInput.addEventListener('blur', validateCapacity);
    }

    loadDepartments();
    loadUnscheduledOrders();
    loadSchedule();
});

function getStatusColor(status) {
    const colors = {
        scheduled: 'info',
        in_progress: 'warning',
        completed: 'success',
        on_hold: 'secondary',
        rejected: 'danger'
    };
    return colors[status] || 'secondary';
}
