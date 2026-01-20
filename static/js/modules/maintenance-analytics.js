class MaintenanceAnalyticsPage {
    constructor() {
        this.departments = [];
        this.init();
    }

    async init() {
        const user = getCurrentUser();
        if (user) {
            document.getElementById('username').textContent = `${user.first_name} ${user.last_name}`;
        }
        
        await this.loadDepartments();
        this.setDefaultDates();
        this.loadAnalytics();
        this.attachEventListeners();
    }

    attachEventListeners() {
        const logoutBtn = document.querySelector('.logout-btn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', () => logout());
        }

        const loadBtn = document.getElementById('loadAnalyticsBtn');
        if (loadBtn) {
            loadBtn.addEventListener('click', () => this.loadAnalytics());
        }
    }

    async loadDepartments() {
        try {
            const response = await API.departments.getAll();
            if (response.success) {
                this.departments = response.data;
                const select = document.getElementById('departmentFilter');
                select.innerHTML = '<option value="">All Departments</option>';
                this.departments.forEach(dept => {
                    const option = document.createElement('option');
                    option.value = dept.id;
                    option.textContent = dept.name;
                    select.appendChild(option);
                });
            }
        } catch (error) {
            console.error('Failed to load departments:', error);
        }
    }

    setDefaultDates() {
        const endDate = new Date();
        const startDate = new Date();
        startDate.setDate(startDate.getDate() - 90);
        
        document.getElementById('startDate').value = startDate.toISOString().split('T')[0];
        document.getElementById('endDate').value = endDate.toISOString().split('T')[0];
    }

    async loadAnalytics() {
        try {
            const startDate = document.getElementById('startDate').value;
            const endDate = document.getElementById('endDate').value;
            const departmentId = document.getElementById('departmentFilter').value;
            
            let url = `/api/maintenance/analytics?start_date=${startDate}&end_date=${endDate}`;
            if (departmentId) {
                url += `&department_id=${departmentId}`;
            }
            
            const response = await apiRequest(url, 'GET');
            
            if (response.success) {
                this.displayAnalytics(response.data);
            } else {
                showAlert('Failed to load maintenance analytics', 'danger');
            }
        } catch (error) {
            console.error('Failed to load analytics:', error);
            showAlert('Failed to load maintenance analytics', 'danger');
        }
    }

    displayAnalytics(data) {
        document.getElementById('totalTickets').textContent = data.summary.total_tickets || 0;
        document.getElementById('completedTickets').textContent = data.summary.completed_tickets || 0;
        document.getElementById('openTickets').textContent = data.summary.open_tickets || 0;
        document.getElementById('totalDowntime').textContent = `${data.summary.total_downtime_hours || 0} hrs`;
        document.getElementById('avgResolution').textContent = `${data.summary.avg_resolution_time_hours.toFixed(2) || 0} hrs`;
        document.getElementById('criticalTickets').textContent = data.summary.critical_tickets || 0;
        
        const machineTable = document.getElementById('machineBreakdownTable');
        if (!data.machine_breakdown || data.machine_breakdown.length === 0) {
            machineTable.innerHTML = '<tr><td colspan="5" class="empty-state-center">No data available</td></tr>';
        } else {
            machineTable.innerHTML = data.machine_breakdown.map(machine => `
                <tr>
                    <td><strong>${machine.machine_name}</strong> (${machine.machine_number || 'N/A'})</td>
                    <td>${machine.ticket_count || 0}</td>
                    <td>${((machine.total_downtime || 0) / 60).toFixed(2)}</td>
                    <td>${machine.mtbf || 0}</td>
                    <td>${(machine.mttr || 0).toFixed(0)}</td>
                </tr>
            `).join('');
        }
        
        const severityTable = document.getElementById('severityBreakdownTable');
        if (!data.severity_breakdown || data.severity_breakdown.length === 0) {
            severityTable.innerHTML = '<tr><td colspan="3" class="empty-state-center">No data available</td></tr>';
        } else {
            severityTable.innerHTML = data.severity_breakdown.map(severity => `
                <tr>
                    <td><span class="badge badge-${this.getSeverityColor(severity.severity)}">${severity.severity}</span></td>
                    <td>${severity.count}</td>
                    <td>${((severity.total_downtime || 0) / 60).toFixed(2)}</td>
                </tr>
            `).join('');
        }
        
        const trendsTable = document.getElementById('monthlyTrendsTable');
        if (!data.monthly_trends || data.monthly_trends.length === 0) {
            trendsTable.innerHTML = '<tr><td colspan="4" class="empty-state-center">No data available</td></tr>';
        } else {
            trendsTable.innerHTML = data.monthly_trends.map(trend => `
                <tr>
                    <td><strong>${trend.month}</strong></td>
                    <td>${trend.ticket_count}</td>
                    <td>${((trend.total_downtime || 0) / 60).toFixed(2)}</td>
                    <td>${((trend.avg_resolution_time || 0) / 60).toFixed(2)}</td>
                </tr>
            `).join('');
        }
    }

    getSeverityColor(severity) {
        const colors = {
            'critical': 'danger',
            'high': 'warning',
            'medium': 'info',
            'low': 'secondary'
        };
        return colors[severity] || 'secondary';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new MaintenanceAnalyticsPage();
});
