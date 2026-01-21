const API_BASE_URL = '';

async function apiRequest(endpoint, method = 'GET', data = null, requiresAuth = true) {
    const options = {
        method: method,
        headers: {
            'Content-Type': 'application/json'
        }
    };
    
    if (requiresAuth) {
        const token = localStorage.getItem('token');
        if (token) {
            options.headers['Authorization'] = `Bearer ${token}`;
        } else {
            window.location.href = '/login';
            return;
        }
    }
    
    if (data && (method === 'POST' || method === 'PUT' || method === 'PATCH')) {
        options.body = JSON.stringify(data);
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, options);
        const result = await response.json();
        
        if (response.status === 401) {
            localStorage.removeItem('token');
            localStorage.removeItem('user');
            window.location.href = '/login';
            return { success: false, error: 'Unauthorized' };
        }
        
        if (!response.ok) {
            return { success: false, error: result.error || 'Request failed' };
        }
        
        return result;
    } catch (error) {
        console.error('API Request Error:', error);
        return { success: false, error: error.message };
    }
}

const API = {
    auth: {
        login: (credentials) => apiRequest('/api/auth/login', 'POST', credentials, false),
        getMe: () => apiRequest('/api/auth/me'),
        changePassword: (data) => apiRequest('/api/auth/change-password', 'POST', data)
    },
    
    departments: {
        getAll: () => apiRequest('/api/departments'),
        getById: (id) => apiRequest(`/api/departments/${id}`),
        create: (data) => apiRequest('/api/departments', 'POST', data),
        update: (id, data) => apiRequest(`/api/departments/${id}`, 'PUT', data),
        delete: (id) => apiRequest(`/api/departments/${id}`, 'DELETE'),
        addStage: (id, data) => apiRequest(`/api/departments/${id}/stages`, 'POST', data)
    },
    
    employees: {
        getAll: (params = {}) => {
            const queryString = new URLSearchParams(params).toString();
            return apiRequest(`/api/employees${queryString ? '?' + queryString : ''}`);
        },
        getById: (id) => apiRequest(`/api/employees/${id}`),
        create: (data) => apiRequest('/api/employees', 'POST', data),
        update: (id, data) => apiRequest(`/api/employees/${id}`, 'PUT', data),
        delete: (id) => apiRequest(`/api/employees/${id}`, 'DELETE')
    },
    
    machines: {
        getAll: (params = {}) => {
            const queryString = new URLSearchParams(params).toString();
            return apiRequest(`/api/machines${queryString ? '?' + queryString : ''}`);
        },
        getById: (id) => apiRequest(`/api/machines/${id}`),
        create: (data) => apiRequest('/api/machines', 'POST', data),
        update: (id, data) => apiRequest(`/api/machines/${id}`, 'PUT', data),
        updateStatus: (id, status) => apiRequest(`/api/machines/${id}/status`, 'PATCH', { status })
    },
    
    products: {
        getAll: (params = {}) => {
            const queryString = new URLSearchParams(params).toString();
            return apiRequest(`/api/products${queryString ? '?' + queryString : ''}`);
        },
        getById: (id) => apiRequest(`/api/products/${id}`),
        create: (data) => apiRequest('/api/products', 'POST', data),
        update: (id, data) => apiRequest(`/api/products/${id}`, 'PUT', data),
        search: (term) => apiRequest(`/api/products/search?term=${encodeURIComponent(term)}`)
    },
    
    orders: {
        getAll: (params = {}) => {
            const queryString = new URLSearchParams(params).toString();
            return apiRequest(`/api/orders${queryString ? '?' + queryString : ''}`);
        },
        getById: (id) => apiRequest(`/api/orders/${id}`),
        create: (data) => apiRequest('/api/orders', 'POST', data),
        update: (id, data) => apiRequest(`/api/orders/${id}`, 'PUT', data),
        schedule: (id, data) => apiRequest(`/api/orders/${id}/schedule`, 'POST', data),
        hold: (id, reason) => apiRequest(`/api/orders/${id}/hold`, 'POST', { hold_reason: reason }),
        getSuggestions: (id) => apiRequest(`/api/orders/${id}/suggestions`),
        suggestAlternatives: (data) => apiRequest('/api/orders/suggest-alternatives', 'POST', data),
        
        getItems: (orderId) => apiRequest(`/api/orders/${orderId}/items`),
        addItem: (orderId, data) => apiRequest(`/api/orders/${orderId}/items`, 'POST', data),
        updateItem: (orderId, itemId, data) => apiRequest(`/api/orders/${orderId}/items/${itemId}`, 'PUT', data),
        deleteItem: (orderId, itemId) => apiRequest(`/api/orders/${orderId}/items/${itemId}`, 'DELETE'),
        
        getProductionPath: (orderId) => apiRequest(`/api/orders/${orderId}/production-path`),
        setProductionPath: (orderId, data) => apiRequest(`/api/orders/${orderId}/production-path`, 'POST', data),
        updatePathStep: (orderId, pathId, data) => apiRequest(`/api/orders/${orderId}/production-path/${pathId}`, 'PUT', data),
        deletePathStep: (orderId, pathId) => apiRequest(`/api/orders/${orderId}/production-path/${pathId}`, 'DELETE'),
        
        importPreview: (file) => {
            const formData = new FormData();
            formData.append('file', file);
            return fetch(`${API_BASE_URL}/api/orders/import/preview`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                },
                body: formData
            }).then(r => r.json());
        },
        import: (file, mapping) => {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('mapping', JSON.stringify(mapping));
            return fetch(`${API_BASE_URL}/api/orders/import`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                },
                body: formData
            }).then(r => r.json());
        }
    },
    
    defects: {
        getReplacementTickets: (params = {}) => {
            const queryString = new URLSearchParams(params).toString();
            return apiRequest(`/api/defects/replacement-tickets${queryString ? '?' + queryString : ''}`);
        },
        createReplacementTicket: (data) => apiRequest('/api/defects/replacement-tickets', 'POST', data),
        approveReplacementTicket: (id) => apiRequest(`/api/defects/replacement-tickets/${id}/approve`, 'POST'),
        updateReplacementStatus: (id, status) => apiRequest(`/api/defects/replacement-tickets/${id}/status`, 'PATCH', { status }),
        
        getCustomerReturns: (params = {}) => {
            const queryString = new URLSearchParams(params).toString();
            return apiRequest(`/api/defects/customer-returns${queryString ? '?' + queryString : ''}`);
        },
        createCustomerReturn: (data) => apiRequest('/api/defects/customer-returns', 'POST', data)
    },
    
    sop: {
        getTickets: (params = {}) => {
            const queryString = new URLSearchParams(params).toString();
            return apiRequest(`/api/sop/tickets${queryString ? '?' + queryString : ''}`);
        },
        getTicket: (id) => apiRequest(`/api/sop/tickets/${id}`),
        createTicket: (data) => apiRequest('/api/sop/tickets', 'POST', data),
        reassignTicket: (id, data) => apiRequest(`/api/sop/tickets/${id}/reassign`, 'POST', data),
        rejectTicket: (id, reason) => apiRequest(`/api/sop/tickets/${id}/reject`, 'POST', { reason }),
        createNCR: (id, data) => apiRequest(`/api/sop/tickets/${id}/ncr`, 'POST', data),
        hodDecision: (id, data) => apiRequest(`/api/sop/tickets/${id}/hod-decision`, 'POST', data),
        getEscalatedTickets: () => apiRequest('/api/sop/tickets/escalated')
    },
    
    maintenance: {
        getTickets: (params = {}) => {
            const queryString = new URLSearchParams(params).toString();
            return apiRequest(`/api/maintenance/tickets${queryString ? '?' + queryString : ''}`);
        },
        getTicket: (id) => apiRequest(`/api/maintenance/tickets/${id}`),
        createTicket: (data) => apiRequest('/api/maintenance/tickets', 'POST', data),
        assignTicket: (id, data) => apiRequest(`/api/maintenance/tickets/${id}/assign`, 'POST', data),
        updateStatus: (id, data) => apiRequest(`/api/maintenance/tickets/${id}/status`, 'PATCH', data),
        getMachineHistory: (machineId) => apiRequest(`/api/maintenance/machine-history/${machineId}`),
        
        getPreventiveSchedules: (params = {}) => {
            const queryString = new URLSearchParams(params).toString();
            return apiRequest(`/api/maintenance/preventive${queryString ? '?' + queryString : ''}`);
        },
        createPreventiveSchedule: (data) => apiRequest('/api/maintenance/preventive', 'POST', data),
        updatePreventiveSchedule: (id, data) => apiRequest(`/api/maintenance/preventive/${id}`, 'PUT', data),
        deletePreventiveSchedule: (id) => apiRequest(`/api/maintenance/preventive/${id}`, 'DELETE'),
        logPreventiveMaintenance: (scheduleId, data) => apiRequest(`/api/maintenance/preventive/${scheduleId}/log`, 'POST', data),
        getPreventiveLogs: (scheduleId) => apiRequest(`/api/maintenance/preventive/${scheduleId}/logs`)
    },
    
    finance: {
        getBOMs: (params = {}) => {
            const queryString = new URLSearchParams(params).toString();
            return apiRequest(`/api/finance/bom${queryString ? '?' + queryString : ''}`);
        },
        getBOM: (id) => apiRequest(`/api/finance/bom/${id}`),
        createBOM: (data) => apiRequest('/api/finance/bom', 'POST', data),
        updateBOM: (id, data) => apiRequest(`/api/finance/bom/${id}`, 'PUT', data),
        approveBOM: (id) => apiRequest(`/api/finance/bom/${id}/approve`, 'POST'),
        getDefectsCostAnalysis: (params = {}) => {
            const queryString = new URLSearchParams(params).toString();
            return apiRequest(`/api/finance/cost-analysis/defects${queryString ? '?' + queryString : ''}`);
        }
    },
    
    operator: {
        login: (employeeNumber) => apiRequest('/api/operator/login', 'POST', { employee_number: employeeNumber }, false),
        getMyJobs: () => apiRequest('/api/operator/my-jobs'),
        startJob: (jobId, data) => apiRequest(`/api/operator/job/${jobId}/start`, 'POST', data),
        completeJob: (jobId, data) => apiRequest(`/api/operator/job/${jobId}/complete`, 'POST', data),
        addManualJob: (data) => apiRequest('/api/operator/job/add-manual', 'POST', data)
    },
    
    forms: {
        getAll: (params = {}) => {
            const queryString = new URLSearchParams(params).toString();
            return apiRequest(`/api/forms${queryString ? '?' + queryString : ''}`);
        },
        getById: (id) => apiRequest(`/api/forms/${id}`),
        getByCode: (code) => apiRequest(`/api/forms/by-code/${code}`),
        create: (data) => apiRequest('/api/forms', 'POST', data),
        update: (id, data) => apiRequest(`/api/forms/${id}`, 'PUT', data),
        submitForm: (data) => apiRequest('/api/forms/submissions', 'POST', data),
        getSubmission: (id) => apiRequest(`/api/forms/submissions/${id}`)
    },
    
    notifications: {
        getAll: (params = {}) => {
            const queryString = new URLSearchParams(params).toString();
            return apiRequest(`/api/notifications${queryString ? '?' + queryString : ''}`);
        },
        markRead: (id) => apiRequest(`/api/notifications/${id}/read`, 'POST'),
        markAllRead: () => apiRequest('/api/notifications/mark-all-read', 'POST'),
        getUnreadCount: () => apiRequest('/api/notifications/unread-count')
    },
    
    reports: {
        getScheduled: () => apiRequest('/api/reports/scheduled'),
        getScheduledById: (id) => apiRequest(`/api/reports/scheduled/${id}`),
        createScheduled: (data) => apiRequest('/api/reports/scheduled', 'POST', data),
        updateScheduled: (id, data) => apiRequest(`/api/reports/scheduled/${id}`, 'PUT', data),
        deleteScheduled: (id) => apiRequest(`/api/reports/scheduled/${id}`, 'DELETE'),
        runScheduled: (id) => apiRequest(`/api/reports/scheduled/${id}/run`, 'POST'),
        defectsSummary: (params = {}) => {
            const queryString = new URLSearchParams(params).toString();
            return apiRequest(`/api/reports/defects/summary${queryString ? '?' + queryString : ''}`);
        },
        productionSummary: (params = {}) => {
            const queryString = new URLSearchParams(params).toString();
            return apiRequest(`/api/reports/production/summary${queryString ? '?' + queryString : ''}`);
        },
        maintenanceSummary: (params = {}) => {
            const queryString = new URLSearchParams(params).toString();
            return apiRequest(`/api/reports/maintenance/summary${queryString ? '?' + queryString : ''}`);
        },
        sopSummary: (params = {}) => {
            const queryString = new URLSearchParams(params).toString();
            return apiRequest(`/api/reports/sop/summary${queryString ? '?' + queryString : ''}`);
        },
        capacityAnalysis: (params = {}) => {
            const queryString = new URLSearchParams(params).toString();
            return apiRequest(`/api/reports/capacity/analysis${queryString ? '?' + queryString : ''}`);
        },
        costAnalysis: (params = {}) => {
            const queryString = new URLSearchParams(params).toString();
            return apiRequest(`/api/reports/cost/analysis${queryString ? '?' + queryString : ''}`);
        },
        quantityVariance: (params = {}) => {
            const queryString = new URLSearchParams(params).toString();
            return apiRequest(`/api/reports/quantity/variance${queryString ? '?' + queryString : ''}`);
        }
    },
    
    workflows: {
        getAll: (params = {}) => {
            const queryString = new URLSearchParams(params).toString();
            return apiRequest(`/api/workflows${queryString ? '?' + queryString : ''}`);
        },
        getById: (id) => apiRequest(`/api/workflows/${id}`),
        getByCode: (code) => apiRequest(`/api/workflows/by-code/${code}`),
        create: (data) => apiRequest('/api/workflows', 'POST', data),
        update: (id, data) => apiRequest(`/api/workflows/${id}`, 'PUT', data),
        activate: (id) => apiRequest(`/api/workflows/${id}/activate`, 'POST'),
        deactivate: (id) => apiRequest(`/api/workflows/${id}/deactivate`, 'POST')
    },
    
    sla: {
        getAll: (params = {}) => {
            const queryString = new URLSearchParams(params).toString();
            return apiRequest(`/api/sla${queryString ? '?' + queryString : ''}`);
        },
        getById: (id) => apiRequest(`/api/sla/${id}`),
        create: (data) => apiRequest('/api/sla', 'POST', data),
        update: (id, data) => apiRequest(`/api/sla/${id}`, 'PUT', data),
        delete: (id) => apiRequest(`/api/sla/${id}`, 'DELETE'),
        getTracking: (entityType, entityId) => apiRequest(`/api/sla/tracking/${entityType}/${entityId}`)
    },
    
    roles: {
        getAll: () => apiRequest('/api/roles'),
        getById: (id) => apiRequest(`/api/roles/${id}`),
        create: (data) => apiRequest('/api/roles', 'POST', data),
        update: (id, data) => apiRequest(`/api/roles/${id}`, 'PUT', data),
        delete: (id) => apiRequest(`/api/roles/${id}`, 'DELETE')
    },
    
    fieldPermissions: {
        getAll: (params = {}) => {
            const queryString = new URLSearchParams(params).toString();
            return apiRequest(`/api/field-permissions${queryString ? '?' + queryString : ''}`);
        },
        getByRole: (roleId) => apiRequest(`/api/field-permissions/role/${roleId}`),
        create: (data) => apiRequest('/api/field-permissions', 'POST', data),
        update: (id, data) => apiRequest(`/api/field-permissions/${id}`, 'PUT', data),
        delete: (id) => apiRequest(`/api/field-permissions/${id}`, 'DELETE')
    }
};
