let stepCount = 0;
let escalationLevelCount = 0;
let departments = [];
let roles = [];
let allWorkflows = [];
let allSLAs = [];

async function init() {
    const user = getCurrentUser();
    if (user) {
        document.getElementById('username').textContent = `${user.first_name} ${user.last_name}`;
    }
    
    await loadDepartments();
    await loadRoles();
    await loadWorkflows();
    await loadSLAs();
    
    setupEventListeners();
}

function setupEventListeners() {
    document.getElementById('workflowForm').addEventListener('submit', handleWorkflowSubmit);
    document.getElementById('slaForm').addEventListener('submit', handleSLASubmit);
    
    const tabButtons = document.querySelectorAll('.tab-button');
    tabButtons.forEach((btn, index) => {
        btn.addEventListener('click', () => switchTab(index === 0 ? 'workflows' : 'sla'));
    });
}

function switchTab(tab) {
    const workflowsTab = document.getElementById('workflowsTab');
    const slaTab = document.getElementById('slaTab');
    const buttons = document.querySelectorAll('.tab-button');
    
    buttons.forEach(btn => btn.classList.remove('active'));
    
    if (tab === 'workflows') {
        workflowsTab.style.display = 'block';
        slaTab.style.display = 'none';
        buttons[0].classList.add('active');
    } else {
        workflowsTab.style.display = 'none';
        slaTab.style.display = 'block';
        buttons[1].classList.add('active');
    }
}

async function loadDepartments() {
    try {
        const response = await API.departments.getAll();
        if (response.success) {
            departments = response.data;
            populateDepartmentSelects();
        }
    } catch (error) {
        console.error('Error loading departments:', error);
    }
}

async function loadRoles() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/roles`, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        });
        const data = await response.json();
        if (data.success) {
            roles = data.data;
        }
    } catch (error) {
        console.error('Error loading roles:', error);
    }
}

function populateDepartmentSelects() {
    const select = document.getElementById('slaDepartment');
    if (select) {
        select.innerHTML = '<option value="">All Departments</option>' +
            departments.map(d => `<option value="${d.id}">${d.name}</option>`).join('');
    }
}

async function loadWorkflows() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/workflows`, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        });
        const data = await response.json();
        
        if (data.success) {
            allWorkflows = data.data;
            renderWorkflows(data.data);
        }
    } catch (error) {
        console.error('Error loading workflows:', error);
        showAlert('Failed to load workflows', 'danger');
    }
}

function renderWorkflows(workflows) {
    const tbody = document.getElementById('workflowsTable');
    
    if (workflows.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align: center;">No workflows found</td></tr>';
        return;
    }
    
    tbody.innerHTML = workflows.map(workflow => {
        let steps = [];
        try {
            steps = typeof workflow.workflow_steps === 'string' ? 
                JSON.parse(workflow.workflow_steps) : workflow.workflow_steps || [];
        } catch (e) {
            steps = [];
        }
        
        return `
            <tr>
                <td>${workflow.workflow_code}</td>
                <td>${workflow.workflow_name}</td>
                <td><span class="badge badge-info">${workflow.module}</span></td>
                <td>${steps.length} steps</td>
                <td>v${workflow.version}</td>
                <td>${createStatusBadge(workflow.is_active ? 'active' : 'inactive')}</td>
                <td>
                    <button class="btn btn-sm btn-primary" onclick="viewWorkflow(${workflow.id})">View</button>
                    <button class="btn btn-sm ${workflow.is_active ? 'btn-warning' : 'btn-success'}" 
                            onclick="toggleWorkflowStatus(${workflow.id}, ${workflow.is_active})">
                        ${workflow.is_active ? 'Deactivate' : 'Activate'}
                    </button>
                </td>
            </tr>
        `;
    }).join('');
}

async function loadSLAs() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/sla/configurations`, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        });
        const data = await response.json();
        
        if (data.success) {
            allSLAs = data.data;
            renderSLAs(data.data);
        }
    } catch (error) {
        console.error('Error loading SLAs:', error);
        showAlert('Failed to load SLAs', 'danger');
    }
}

function renderSLAs(slas) {
    const tbody = document.getElementById('slaTable');
    
    if (slas.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" style="text-align: center;">No SLAs found</td></tr>';
        return;
    }
    
    tbody.innerHTML = slas.map(sla => `
        <tr>
            <td>${sla.sla_name}</td>
            <td>${sla.entity_type}</td>
            <td>${sla.department_name || 'All'}</td>
            <td><span class="badge badge-${getPriorityClass(sla.priority)}">${sla.priority}</span></td>
            <td>${sla.response_time_minutes ? sla.response_time_minutes + ' min' : 'N/A'}</td>
            <td>${sla.resolution_time_minutes ? sla.resolution_time_minutes + ' min' : 'N/A'}</td>
            <td>${createStatusBadge(sla.is_active ? 'active' : 'inactive')}</td>
            <td>
                <button class="btn btn-sm btn-primary" onclick="viewSLA(${sla.id})">View</button>
                <button class="btn btn-sm ${sla.is_active ? 'btn-warning' : 'btn-success'}" 
                        onclick="toggleSLAStatus(${sla.id}, ${sla.is_active})">
                    ${sla.is_active ? 'Deactivate' : 'Activate'}
                </button>
            </td>
        </tr>
    `).join('');
}

function getPriorityClass(priority) {
    const classes = {
        low: 'info',
        normal: 'primary',
        high: 'warning',
        critical: 'danger'
    };
    return classes[priority] || 'secondary';
}

function addWorkflowStep() {
    stepCount++;
    const container = document.getElementById('stepsContainer');
    const stepDiv = document.createElement('div');
    stepDiv.className = 'card';
    stepDiv.style.marginBottom = '1rem';
    stepDiv.id = `step-${stepCount}`;
    stepDiv.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
            <h4>Step ${stepCount}</h4>
            <button type="button" class="btn btn-sm btn-danger" onclick="removeStep('step-${stepCount}')">Remove</button>
        </div>
        <div class="grid grid-2">
            <div class="form-group">
                <label class="form-label">Step Name*</label>
                <input type="text" class="form-input step-name" required>
            </div>
            <div class="form-group">
                <label class="form-label">Step Type*</label>
                <select class="form-select step-type" required>
                    <option value="approval">Approval</option>
                    <option value="review">Review</option>
                    <option value="action">Action</option>
                    <option value="notification">Notification</option>
                </select>
            </div>
        </div>
        <div class="grid grid-2">
            <div class="form-group">
                <label class="form-label">Assigned Role</label>
                <select class="form-select step-role">
                    <option value="">Select Role</option>
                    ${roles.map(r => `<option value="${r.id}">${r.name}</option>`).join('')}
                </select>
            </div>
            <div class="form-group">
                <label class="form-label">Duration (hours)</label>
                <input type="number" class="form-input step-duration" min="1">
            </div>
        </div>
        <div class="form-group">
            <label class="form-label">
                <input type="checkbox" class="step-required" checked>
                Required Step
            </label>
        </div>
    `;
    container.appendChild(stepDiv);
}

function removeStep(stepId) {
    const stepDiv = document.getElementById(stepId);
    if (stepDiv) {
        stepDiv.remove();
    }
}

function toggleEscalation() {
    const enabled = document.getElementById('escalationEnabled').value === 'true';
    document.getElementById('escalationTimeGroup').style.display = enabled ? 'block' : 'none';
}

async function handleWorkflowSubmit(e) {
    e.preventDefault();
    
    const steps = [];
    const stepDivs = document.querySelectorAll('#stepsContainer > div');
    
    stepDivs.forEach((div, index) => {
        steps.push({
            step_number: index + 1,
            step_name: div.querySelector('.step-name').value,
            step_type: div.querySelector('.step-type').value,
            assigned_role_id: div.querySelector('.step-role').value || null,
            duration_hours: parseInt(div.querySelector('.step-duration').value) || null,
            is_required: div.querySelector('.step-required').checked
        });
    });
    
    if (steps.length === 0) {
        showAlert('At least one workflow step is required', 'warning');
        return;
    }
    
    const escalationEnabled = document.getElementById('escalationEnabled').value === 'true';
    const escalationRules = escalationEnabled ? {
        enabled: true,
        escalation_time_hours: parseInt(document.getElementById('escalationTime').value) || 24
    } : {};
    
    const data = {
        workflow_code: document.getElementById('workflowCode').value,
        workflow_name: document.getElementById('workflowName').value,
        module: document.getElementById('workflowModule').value,
        description: document.getElementById('workflowDescription').value,
        workflow_steps: steps,
        escalation_rules: escalationRules
    };
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/workflows`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        const result = await response.json();
        
        if (result.success) {
            showAlert('Workflow created successfully', 'success');
            hideModal('addWorkflowModal');
            document.getElementById('workflowForm').reset();
            document.getElementById('stepsContainer').innerHTML = '';
            stepCount = 0;
            await loadWorkflows();
        } else {
            showAlert(result.message || 'Failed to create workflow', 'danger');
        }
    } catch (error) {
        showAlert('Failed to create workflow', 'danger');
    }
}

function addEscalationLevel() {
    escalationLevelCount++;
    const container = document.getElementById('escalationLevelsContainer');
    const levelDiv = document.createElement('div');
    levelDiv.className = 'card';
    levelDiv.style.marginBottom = '1rem';
    levelDiv.id = `escalation-level-${escalationLevelCount}`;
    levelDiv.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
            <h4>Escalation Level ${escalationLevelCount}</h4>
            <button type="button" class="btn btn-sm btn-danger" onclick="removeEscalationLevel('escalation-level-${escalationLevelCount}')">Remove</button>
        </div>
        <div class="grid grid-2">
            <div class="form-group">
                <label class="form-label">Time (minutes)*</label>
                <input type="number" class="form-input escalation-time" required min="1">
            </div>
            <div class="form-group">
                <label class="form-label">Escalate To Role</label>
                <select class="form-select escalation-role">
                    <option value="">Select Role</option>
                    ${roles.map(r => `<option value="${r.id}">${r.name}</option>`).join('')}
                </select>
            </div>
        </div>
        <div class="form-group">
            <label class="form-label">Notification Message</label>
            <textarea class="form-textarea escalation-message" rows="2"></textarea>
        </div>
    `;
    container.appendChild(levelDiv);
}

function removeEscalationLevel(levelId) {
    const levelDiv = document.getElementById(levelId);
    if (levelDiv) {
        levelDiv.remove();
    }
}

async function handleSLASubmit(e) {
    e.preventDefault();
    
    const escalationLevels = [];
    const levelDivs = document.querySelectorAll('#escalationLevelsContainer > div');
    
    levelDivs.forEach((div, index) => {
        escalationLevels.push({
            level: index + 1,
            escalation_time_minutes: parseInt(div.querySelector('.escalation-time').value),
            escalate_to_role_id: div.querySelector('.escalation-role').value || null,
            notification_message: div.querySelector('.escalation-message').value
        });
    });
    
    if (escalationLevels.length === 0) {
        showAlert('At least one escalation level is required', 'warning');
        return;
    }
    
    const data = {
        sla_name: document.getElementById('slaName').value,
        entity_type: document.getElementById('entityType').value,
        department_id: document.getElementById('slaDepartment').value || null,
        priority: document.getElementById('slaPriority').value,
        response_time_minutes: parseInt(document.getElementById('responseTime').value) || null,
        resolution_time_minutes: parseInt(document.getElementById('resolutionTime').value) || null,
        escalation_levels: escalationLevels
    };
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/sla/configurations`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        const result = await response.json();
        
        if (result.success) {
            showAlert('SLA configuration created successfully', 'success');
            hideModal('addSLAModal');
            document.getElementById('slaForm').reset();
            document.getElementById('escalationLevelsContainer').innerHTML = '';
            escalationLevelCount = 0;
            await loadSLAs();
        } else {
            showAlert(result.message || 'Failed to create SLA', 'danger');
        }
    } catch (error) {
        showAlert('Failed to create SLA', 'danger');
    }
}

async function viewWorkflow(id) {
    const workflow = allWorkflows.find(w => w.id === id);
    if (!workflow) return;
    
    let steps = [];
    try {
        steps = typeof workflow.workflow_steps === 'string' ? 
            JSON.parse(workflow.workflow_steps) : workflow.workflow_steps || [];
    } catch (e) {
        steps = [];
    }
    
    const stepsHTML = steps.map(step => `
        <div class="card" style="margin-bottom: 0.5rem;">
            <strong>Step ${step.step_number}: ${step.step_name}</strong>
            <div>Type: ${step.step_type}</div>
            ${step.duration_hours ? `<div>Duration: ${step.duration_hours} hours</div>` : ''}
            ${step.is_required ? '<div class="badge badge-warning">Required</div>' : ''}
        </div>
    `).join('');
    
    showAlert(`
        <h3>${workflow.workflow_name}</h3>
        <p><strong>Code:</strong> ${workflow.workflow_code}</p>
        <p><strong>Module:</strong> ${workflow.module}</p>
        <p><strong>Description:</strong> ${workflow.description || 'N/A'}</p>
        <h4>Workflow Steps:</h4>
        ${stepsHTML}
    `, 'info');
}

async function viewSLA(id) {
    const sla = allSLAs.find(s => s.id === id);
    if (!sla) return;
    
    let escalationLevels = [];
    try {
        escalationLevels = typeof sla.escalation_levels === 'string' ? 
            JSON.parse(sla.escalation_levels) : sla.escalation_levels || [];
    } catch (e) {
        escalationLevels = [];
    }
    
    const levelsHTML = escalationLevels.map(level => `
        <div class="card" style="margin-bottom: 0.5rem;">
            <strong>Level ${level.level}</strong>
            <div>After: ${level.escalation_time_minutes} minutes</div>
            ${level.notification_message ? `<div>${level.notification_message}</div>` : ''}
        </div>
    `).join('');
    
    showAlert(`
        <h3>${sla.sla_name}</h3>
        <p><strong>Entity Type:</strong> ${sla.entity_type}</p>
        <p><strong>Department:</strong> ${sla.department_name || 'All'}</p>
        <p><strong>Priority:</strong> ${sla.priority}</p>
        <p><strong>Response Time:</strong> ${sla.response_time_minutes || 'N/A'} minutes</p>
        <p><strong>Resolution Time:</strong> ${sla.resolution_time_minutes || 'N/A'} minutes</p>
        <h4>Escalation Levels:</h4>
        ${levelsHTML}
    `, 'info');
}

async function toggleWorkflowStatus(id, isActive) {
    const action = isActive ? 'deactivate' : 'activate';
    if (!confirm(`Are you sure you want to ${action} this workflow?`)) return;
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/workflows/${id}/${action}`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        });
        const result = await response.json();
        
        if (result.success) {
            showAlert(`Workflow ${action}d successfully`, 'success');
            await loadWorkflows();
        } else {
            showAlert(result.message || `Failed to ${action} workflow`, 'danger');
        }
    } catch (error) {
        showAlert(`Failed to ${action} workflow`, 'danger');
    }
}

async function toggleSLAStatus(id, isActive) {
    const action = isActive ? 'deactivate' : 'activate';
    if (!confirm(`Are you sure you want to ${action} this SLA?`)) return;
    
    try {
        const sla = allSLAs.find(s => s.id === id);
        const response = await fetch(`${API_BASE_URL}/api/sla/configurations/${id}`, {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ is_active: !isActive })
        });
        const result = await response.json();
        
        if (result.success) {
            showAlert(`SLA ${action}d successfully`, 'success');
            await loadSLAs();
        } else {
            showAlert(result.message || `Failed to ${action} SLA`, 'danger');
        }
    } catch (error) {
        showAlert(`Failed to ${action} SLA`, 'danger');
    }
}

document.addEventListener('DOMContentLoaded', init);
