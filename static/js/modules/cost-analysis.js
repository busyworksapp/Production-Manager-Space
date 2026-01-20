class CostAnalysisPage {
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
        this.loadAnalysis();
        this.attachEventListeners();
    }

    attachEventListeners() {
        const logoutBtn = document.querySelector('.logout-btn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', () => logout());
        }

        const loadBtn = document.getElementById('loadAnalysisBtn');
        if (loadBtn) {
            loadBtn.addEventListener('click', () => this.loadAnalysis());
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
        startDate.setDate(startDate.getDate() - 30);
        
        document.getElementById('startDate').value = startDate.toISOString().split('T')[0];
        document.getElementById('endDate').value = endDate.toISOString().split('T')[0];
    }

    async loadAnalysis() {
        try {
            const startDate = document.getElementById('startDate').value;
            const endDate = document.getElementById('endDate').value;
            const departmentId = document.getElementById('departmentFilter').value;
            
            let url = `/api/defects/cost-analysis?start_date=${startDate}&end_date=${endDate}`;
            if (departmentId) {
                url += `&department_id=${departmentId}`;
            }
            
            const response = await apiRequest(url, 'GET');
            
            if (response.success) {
                this.displayAnalysis(response.data);
            } else {
                showAlert('Failed to load cost analysis', 'danger');
            }
        } catch (error) {
            console.error('Failed to load cost analysis:', error);
            showAlert('Failed to load cost analysis', 'danger');
        }
    }

    displayAnalysis(data) {
        document.getElementById('totalDefects').textContent = data.summary.total_defects || 0;
        document.getElementById('totalQuantity').textContent = data.summary.total_quantity_rejected || 0;
        document.getElementById('totalMaterialCost').textContent = `R ${(data.summary.total_material_cost || 0).toLocaleString('en-ZA', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
        document.getElementById('totalCostImpact').textContent = `R ${(data.summary.total_cost_impact || 0).toLocaleString('en-ZA', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
        
        const deptTable = document.getElementById('departmentCostsTable');
        if (!data.department_costs || data.department_costs.length === 0) {
            deptTable.innerHTML = '<tr><td colspan="5" class="empty-state-center">No data available</td></tr>';
        } else {
            deptTable.innerHTML = data.department_costs.map(dept => `
                <tr>
                    <td><strong>${dept.department_name}</strong></td>
                    <td>${dept.total_defects || 0}</td>
                    <td>${dept.total_quantity_rejected || 0}</td>
                    <td>R ${(dept.total_material_cost || 0).toLocaleString('en-ZA', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                    <td class="text-danger"><strong>R ${(dept.total_cost_impact || 0).toLocaleString('en-ZA', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</strong></td>
                </tr>
            `).join('');
        }
        
        const defectsTable = document.getElementById('topDefectsTable');
        if (!data.top_defects || data.top_defects.length === 0) {
            defectsTable.innerHTML = '<tr><td colspan="4" class="empty-state-center">No data available</td></tr>';
        } else {
            defectsTable.innerHTML = data.top_defects.map(defect => `
                <tr>
                    <td>${defect.rejection_reason}</td>
                    <td>${defect.defect_count}</td>
                    <td>${defect.total_quantity}</td>
                    <td class="text-danger"><strong>R ${(defect.total_cost || 0).toLocaleString('en-ZA', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</strong></td>
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
                    <td>${trend.defect_count}</td>
                    <td>R ${(trend.material_cost || 0).toLocaleString('en-ZA', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                    <td class="text-danger"><strong>R ${(trend.total_cost || 0).toLocaleString('en-ZA', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</strong></td>
                </tr>
            `).join('');
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new CostAnalysisPage();
});
