let allScheduledReports = [];
let reportTemplates = [];
let departments = [];
let recipientCounter = 0;

async function init() {
    const user = getCurrentUser();
    if (user) {
        document.getElementById('username').textContent = `${user.first_name} ${user.last_name}`;
    }
    
    attachEventListeners();
    await loadDepartments();
    await loadReportTemplates();
    await loadScheduledReports();
}

function attachEventListeners() {
    const logoutBtn = document.querySelector('.logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', () => logout());
    }

    const createReportBtn = document.getElementById('createReportBtn');
    if (createReportBtn) {
        createReportBtn.addEventListener('click', () => openCreateReportModal());
    }

    const reportForm = document.getElementById('reportForm');
    if (reportForm) {
        reportForm.addEventListener('submit', (e) => handleFormSubmit(e));
    }

    const scheduleType = document.getElementById('scheduleType');
    if (scheduleType) {
        scheduleType.addEventListener('change', () => handleScheduleTypeChange());
    }

    const reportType = document.getElementById('reportType');
    if (reportType) {
        reportType.addEventListener('change', () => handleReportTypeChange());
    }

    const testReportBtn = document.getElementById('testReportBtn');
    if (testReportBtn) {
        testReportBtn.addEventListener('click', () => testReport());
    }

    const scheduleTime = document.getElementById('scheduleTime');
    const scheduleDay = document.getElementById('scheduleDay');
    const scheduleDate = document.getElementById('scheduleDate');
    
    [scheduleTime, scheduleDay, scheduleDate].forEach(elem => {
        if (elem) {
            elem.addEventListener('change', () => updateSchedulePreview());
        }
    });
}

async function loadScheduledReports() {
    try {
        const response = await fetch('/api/reports/scheduled', {
            headers: getAuthHeaders()
        });
        const data = await response.json();

        if (data.success) {
            allScheduledReports = data.data;
            renderScheduledReports(data.data);
        }
    } catch (error) {
        console.error('Error loading scheduled reports:', error);
        showNotification('Failed to load scheduled reports', 'error');
    }
}

function renderScheduledReports(reports) {
    const tbody = document.getElementById('reportsTable');
    if (!tbody) return;

    if (reports.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" style="text-align: center;">No scheduled reports found. Click "Create Report Schedule" to get started.</td></tr>';
        return;
    }

    tbody.innerHTML = reports.map(report => {
        const recipients = JSON.parse(report.recipients || '[]');
        const scheduleConfig = JSON.parse(report.schedule_config || '{}');
        const scheduleText = getScheduleText(scheduleConfig);
        
        return `
            <tr>
                <td>${escapeHtml(report.report_name)}</td>
                <td><span class="badge badge-info">${getReportTypeName(report.report_type)}</span></td>
                <td>${scheduleText}</td>
                <td><span class="badge badge-secondary">${recipients.length}</span></td>
                <td>${report.last_run_at ? formatDateTime(report.last_run_at) : 'Never'}</td>
                <td>${report.next_run_at ? formatDateTime(report.next_run_at) : '-'}</td>
                <td><span class="badge badge-${report.is_active ? 'success' : 'secondary'}">${report.is_active ? 'Active' : 'Inactive'}</span></td>
                <td>
                    <button class="btn btn-sm btn-secondary" onclick="editReport(${report.id})">Edit</button>
                    <button class="btn btn-sm btn-primary" onclick="runReportNow(${report.id})">Run Now</button>
                    <button class="btn btn-sm btn-${report.is_active ? 'warning' : 'success'}" onclick="toggleReportStatus(${report.id}, ${report.is_active})">
                        ${report.is_active ? 'Deactivate' : 'Activate'}
                    </button>
                    <button class="btn btn-sm btn-danger" onclick="deleteReport(${report.id})">Delete</button>
                </td>
            </tr>
        `;
    }).join('');
}

async function loadReportTemplates() {
    try {
        const response = await fetch('/api/reports/templates', {
            headers: getAuthHeaders()
        });
        const data = await response.json();

        if (data.success) {
            reportTemplates = data.data;
            populateReportTypeSelect();
        }
    } catch (error) {
        console.error('Error loading report templates:', error);
        showNotification('Failed to load report templates', 'error');
    }
}

function populateReportTypeSelect() {
    const select = document.getElementById('reportType');
    if (!select) return;

    select.innerHTML = '<option value="">Select Type...</option>' +
        reportTemplates.map(template => 
            `<option value="${template.id}">${escapeHtml(template.name)}</option>`
        ).join('');
}

async function loadDepartments() {
    try {
        const response = await fetch('/api/departments', {
            headers: getAuthHeaders()
        });
        const data = await response.json();

        if (data.success) {
            departments = data.data;
            populateDepartmentFilter();
        }
    } catch (error) {
        console.error('Error loading departments:', error);
    }
}

function populateDepartmentFilter() {
    const select = document.getElementById('departmentFilter');
    if (!select) return;

    select.innerHTML = '<option value="">All Departments</option>' +
        departments.map(dept => 
            `<option value="${dept.id}">${escapeHtml(dept.name)}</option>`
        ).join('');
}

function openCreateReportModal() {
    document.getElementById('modalTitle').textContent = 'Create Automated Report';
    document.getElementById('reportForm').reset();
    document.getElementById('reportId').value = '';
    
    recipientCounter = 0;
    document.getElementById('recipientsContainer').innerHTML = '';
    addRecipient();
    
    handleScheduleTypeChange();
    updateSchedulePreview();
    
    showModal('reportModal');
}

async function editReport(id) {
    try {
        const response = await fetch(`/api/reports/scheduled/${id}`, {
            headers: getAuthHeaders()
        });
        const data = await response.json();

        if (data.success) {
            const report = data.data;
            
            document.getElementById('modalTitle').textContent = 'Edit Automated Report';
            document.getElementById('reportId').value = report.id;
            document.getElementById('reportName').value = report.report_name;
            document.getElementById('reportType').value = report.report_type;
            
            const reportConfig = JSON.parse(report.report_config || '{}');
            const scheduleConfig = JSON.parse(report.schedule_config || '{}');
            const recipients = JSON.parse(report.recipients || '[]');
            
            document.getElementById('dateRange').value = reportConfig.date_range || 'last_7_days';
            document.getElementById('departmentFilter').value = reportConfig.filters?.department || '';
            document.getElementById('outputFormat').value = reportConfig.output_format || 'pdf';
            document.getElementById('includeCharts').checked = reportConfig.include_charts !== false;
            
            document.getElementById('scheduleType').value = scheduleConfig.type || 'manual';
            handleScheduleTypeChange();
            
            if (scheduleConfig.hour !== undefined) {
                const hour = String(scheduleConfig.hour).padStart(2, '0');
                const minute = String(scheduleConfig.minute || 0).padStart(2, '0');
                document.getElementById('scheduleTime').value = `${hour}:${minute}`;
            }
            
            if (scheduleConfig.day_of_week !== undefined) {
                document.getElementById('scheduleDay').value = scheduleConfig.day_of_week;
            }
            
            if (scheduleConfig.day_of_month !== undefined) {
                document.getElementById('scheduleDate').value = scheduleConfig.day_of_month;
            }
            
            recipientCounter = 0;
            document.getElementById('recipientsContainer').innerHTML = '';
            recipients.forEach(email => addRecipient(email));
            
            handleReportTypeChange();
            updateSchedulePreview();
            
            showModal('reportModal');
        }
    } catch (error) {
        console.error('Error loading report:', error);
        showNotification('Failed to load report details', 'error');
    }
}

function handleScheduleTypeChange() {
    const scheduleType = document.getElementById('scheduleType').value;
    const timeGroup = document.getElementById('scheduleTimeGroup');
    const dayGroup = document.getElementById('scheduleDayGroup');
    const dateGroup = document.getElementById('scheduleDateGroup');
    
    timeGroup.style.display = 'none';
    dayGroup.style.display = 'none';
    dateGroup.style.display = 'none';
    
    if (scheduleType === 'daily') {
        timeGroup.style.display = 'block';
    } else if (scheduleType === 'weekly') {
        timeGroup.style.display = 'block';
        dayGroup.style.display = 'block';
    } else if (scheduleType === 'monthly') {
        timeGroup.style.display = 'block';
        dateGroup.style.display = 'block';
    }
    
    updateSchedulePreview();
}

function handleReportTypeChange() {
    const reportType = document.getElementById('reportType').value;
    const template = reportTemplates.find(t => t.id === reportType);
    
    const descDiv = document.getElementById('reportDescription');
    if (template && descDiv) {
        descDiv.innerHTML = `<p style="color: #666; font-style: italic; margin-top: 0.5rem;">${escapeHtml(template.description)}</p>`;
    } else if (descDiv) {
        descDiv.innerHTML = '';
    }
    
    const deptFilterGroup = document.getElementById('departmentFilterGroup');
    if (template && template.available_filters.includes('department')) {
        deptFilterGroup.style.display = 'block';
    } else {
        deptFilterGroup.style.display = 'none';
    }
}

function updateSchedulePreview() {
    const scheduleType = document.getElementById('scheduleType').value;
    const previewDiv = document.getElementById('schedulePreview');
    
    if (scheduleType === 'manual') {
        previewDiv.innerHTML = '<p style="color: #666; font-style: italic;">Report will only run when manually triggered.</p>';
        return;
    }
    
    const scheduleConfig = getScheduleConfigFromForm();
    const previewText = getSchedulePreviewText(scheduleConfig);
    
    previewDiv.innerHTML = `<p style="color: #2563eb; font-weight: 500;">📅 ${previewText}</p>`;
}

function getScheduleConfigFromForm() {
    const scheduleType = document.getElementById('scheduleType').value;
    const config = { type: scheduleType };
    
    if (scheduleType !== 'manual') {
        const time = document.getElementById('scheduleTime').value;
        if (time) {
            const [hour, minute] = time.split(':');
            config.hour = parseInt(hour);
            config.minute = parseInt(minute);
        }
        
        if (scheduleType === 'weekly') {
            config.day_of_week = parseInt(document.getElementById('scheduleDay').value);
        } else if (scheduleType === 'monthly') {
            config.day_of_month = parseInt(document.getElementById('scheduleDate').value);
        }
    }
    
    return config;
}

function getScheduleText(config) {
    if (config.type === 'manual') return 'Manual';
    
    const time = config.hour !== undefined ? `${String(config.hour).padStart(2, '0')}:${String(config.minute || 0).padStart(2, '0')}` : '';
    
    if (config.type === 'daily') {
        return `Daily at ${time}`;
    } else if (config.type === 'weekly') {
        const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
        return `Weekly on ${days[config.day_of_week]} at ${time}`;
    } else if (config.type === 'monthly') {
        return `Monthly on day ${config.day_of_month} at ${time}`;
    }
    
    return 'Manual';
}

function getSchedulePreviewText(config) {
    if (config.type === 'manual') return 'Manual execution only';
    
    const time = config.hour !== undefined ? `${String(config.hour).padStart(2, '0')}:${String(config.minute || 0).padStart(2, '0')}` : '';
    
    if (config.type === 'daily') {
        return `Report will be generated daily at ${time}`;
    } else if (config.type === 'weekly') {
        const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
        return `Report will be generated every ${days[config.day_of_week]} at ${time}`;
    } else if (config.type === 'monthly') {
        const suffix = getOrdinalSuffix(config.day_of_month);
        return `Report will be generated on the ${config.day_of_month}${suffix} of each month at ${time}`;
    }
    
    return 'Manual execution only';
}

function getOrdinalSuffix(num) {
    const j = num % 10;
    const k = num % 100;
    if (j === 1 && k !== 11) return 'st';
    if (j === 2 && k !== 12) return 'nd';
    if (j === 3 && k !== 13) return 'rd';
    return 'th';
}

function getReportTypeName(typeId) {
    const template = reportTemplates.find(t => t.id === typeId);
    return template ? template.name : typeId;
}

function addRecipient(email = '') {
    const container = document.getElementById('recipientsContainer');
    const id = recipientCounter++;
    
    const div = document.createElement('div');
    div.className = 'form-group';
    div.style.display = 'flex';
    div.style.gap = '0.5rem';
    div.style.alignItems = 'center';
    div.innerHTML = `
        <input type="email" class="form-input recipient-email" placeholder="recipient@example.com" value="${escapeHtml(email)}" required style="flex: 1;">
        <button type="button" class="btn btn-sm btn-danger" onclick="removeRecipient(this)">Remove</button>
    `;
    
    container.appendChild(div);
}

function removeRecipient(button) {
    const container = document.getElementById('recipientsContainer');
    if (container.children.length > 1) {
        button.closest('.form-group').remove();
    } else {
        showNotification('At least one recipient is required', 'warning');
    }
}

async function handleFormSubmit(e) {
    e.preventDefault();
    
    const reportId = document.getElementById('reportId').value;
    const reportName = document.getElementById('reportName').value;
    const reportType = document.getElementById('reportType').value;
    
    const recipients = Array.from(document.querySelectorAll('.recipient-email'))
        .map(input => input.value.trim())
        .filter(email => email);
    
    if (recipients.length === 0) {
        showNotification('At least one recipient email is required', 'error');
        return;
    }
    
    const scheduleConfig = getScheduleConfigFromForm();
    
    const filters = {};
    const deptFilter = document.getElementById('departmentFilter').value;
    if (deptFilter) {
        filters.department = parseInt(deptFilter);
    }
    
    const reportConfig = {
        date_range: document.getElementById('dateRange').value,
        output_format: document.getElementById('outputFormat').value,
        include_charts: document.getElementById('includeCharts').checked,
        filters: filters
    };
    
    const data = {
        report_name: reportName,
        report_type: reportType,
        recipients: recipients,
        schedule_config: scheduleConfig,
        filters: filters,
        output_format: reportConfig.output_format,
        include_charts: reportConfig.include_charts,
        date_range: reportConfig.date_range
    };
    
    try {
        let response;
        if (reportId) {
            response = await fetch(`/api/reports/scheduled/${reportId}`, {
                method: 'PUT',
                headers: {
                    ...getAuthHeaders(),
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });
        } else {
            response = await fetch('/api/reports/scheduled', {
                method: 'POST',
                headers: {
                    ...getAuthHeaders(),
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });
        }
        
        const result = await response.json();
        
        if (result.success) {
            showNotification(reportId ? 'Report schedule updated successfully' : 'Report schedule created successfully', 'success');
            closeModal();
            await loadScheduledReports();
        } else {
            showNotification(result.error || 'Failed to save report schedule', 'error');
        }
    } catch (error) {
        console.error('Error saving report:', error);
        showNotification('Failed to save report schedule', 'error');
    }
}

async function testReport() {
    const reportType = document.getElementById('reportType').value;
    if (!reportType) {
        showNotification('Please select a report type first', 'warning');
        return;
    }
    
    const filters = {};
    const deptFilter = document.getElementById('departmentFilter').value;
    if (deptFilter) {
        filters.department = parseInt(deptFilter);
    }
    
    const data = {
        report_type: reportType,
        date_range: document.getElementById('dateRange').value,
        output_format: document.getElementById('outputFormat').value,
        include_charts: document.getElementById('includeCharts').checked,
        filters: filters
    };
    
    try {
        showNotification('Generating test report...', 'info');
        
        const response = await fetch('/api/reports/generate-test', {
            method: 'POST',
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (result.success) {
            showNotification('Test report generated successfully! Check your email.', 'success');
        } else {
            showNotification(result.error || 'Failed to generate test report', 'error');
        }
    } catch (error) {
        console.error('Error generating test report:', error);
        showNotification('Failed to generate test report', 'error');
    }
}

async function runReportNow(id) {
    if (!confirm('Are you sure you want to run this report now?')) {
        return;
    }
    
    try {
        showNotification('Running report...', 'info');
        
        const response = await fetch(`/api/reports/scheduled/${id}/run`, {
            method: 'POST',
            headers: getAuthHeaders()
        });
        
        const result = await response.json();
        
        if (result.success) {
            showNotification('Report executed successfully! Recipients will receive it shortly.', 'success');
            await loadScheduledReports();
        } else {
            showNotification(result.error || 'Failed to run report', 'error');
        }
    } catch (error) {
        console.error('Error running report:', error);
        showNotification('Failed to run report', 'error');
    }
}

async function toggleReportStatus(id, currentStatus) {
    const newStatus = !currentStatus;
    const action = newStatus ? 'activate' : 'deactivate';
    
    if (!confirm(`Are you sure you want to ${action} this report?`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/reports/scheduled/${id}`, {
            method: 'PUT',
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ is_active: newStatus })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showNotification(`Report ${action}d successfully`, 'success');
            await loadScheduledReports();
        } else {
            showNotification(result.error || `Failed to ${action} report`, 'error');
        }
    } catch (error) {
        console.error('Error toggling report status:', error);
        showNotification('Failed to update report status', 'error');
    }
}

async function deleteReport(id) {
    if (!confirm('Are you sure you want to delete this report schedule? This action cannot be undone.')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/reports/scheduled/${id}/delete`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });
        
        const result = await response.json();
        
        if (result.success) {
            showNotification('Report schedule deleted successfully', 'success');
            await loadScheduledReports();
        } else {
            showNotification(result.error || 'Failed to delete report', 'error');
        }
    } catch (error) {
        console.error('Error deleting report:', error);
        showNotification('Failed to delete report', 'error');
    }
}

function closeModal() {
    hideModal('reportModal');
}

document.addEventListener('DOMContentLoaded', () => {
    init();
});
