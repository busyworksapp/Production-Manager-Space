function showAlert(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type}`;
    alertDiv.textContent = message;
    
    const container = document.querySelector('.container') || document.body;
    container.insertBefore(alertDiv, container.firstChild);
    
    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

function showModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('active');
    }
}

function hideModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('active');
    }
}

function formatDate(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-ZA');
}

function formatDateTime(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleString('en-ZA');
}

function formatCurrency(amount) {
    if (amount === null || amount === undefined) return 'R 0.00';
    return `R ${parseFloat(amount).toLocaleString('en-ZA', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function showLoading(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = '<div class="loading">Loading...</div>';
    }
}

function hideLoading(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        const loadingDiv = element.querySelector('.loading');
        if (loadingDiv) {
            loadingDiv.remove();
        }
    }
}

function getStatusBadgeClass(status) {
    const statusMap = {
        'completed': 'badge-success',
        'approved': 'badge-success',
        'active': 'badge-success',
        'available': 'badge-success',
        
        'pending': 'badge-warning',
        'in_progress': 'badge-warning',
        'scheduled': 'badge-warning',
        'assigned': 'badge-warning',
        
        'rejected': 'badge-danger',
        'cancelled': 'badge-danger',
        'failed': 'badge-danger',
        'broken': 'badge-danger',
        
        'on_hold': 'badge-info',
        'awaiting_parts': 'badge-info',
        'maintenance': 'badge-info'
    };
    
    return statusMap[status] || 'badge-secondary';
}

function createStatusBadge(status) {
    const badgeClass = getStatusBadgeClass(status);
    const displayText = status.replace(/_/g, ' ').toUpperCase();
    return `<span class="badge ${badgeClass}">${displayText}</span>`;
}

function validateForm(formId) {
    const form = document.getElementById(formId);
    if (!form) return false;
    
    const requiredFields = form.querySelectorAll('[required]');
    let isValid = true;
    
    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            field.classList.add('error');
            isValid = false;
        } else {
            field.classList.remove('error');
        }
    });
    
    return isValid;
}

function resetForm(formId) {
    const form = document.getElementById(formId);
    if (form) {
        form.reset();
        const errorFields = form.querySelectorAll('.error');
        errorFields.forEach(field => field.classList.remove('error'));
    }
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function confirmAction(message, callback) {
    if (confirm(message)) {
        callback();
    }
}

function exportToCSV(data, filename) {
    const csv = convertToCSV(data);
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.setAttribute('hidden', '');
    a.setAttribute('href', url);
    a.setAttribute('download', filename);
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
}

function convertToCSV(data) {
    if (!data || data.length === 0) return '';
    
    const headers = Object.keys(data[0]);
    const csvRows = [];
    
    csvRows.push(headers.join(','));
    
    for (const row of data) {
        const values = headers.map(header => {
            const value = row[header];
            return `"${value}"`;
        });
        csvRows.push(values.join(','));
    }
    
    return csvRows.join('\n');
}

async function updateNotificationCount() {
    try {
        const response = await API.notifications.getUnreadCount();
        if (response.success) {
            const badge = document.querySelector('.notification-badge .badge');
            if (badge) {
                if (response.data.count > 0) {
                    badge.textContent = response.data.count;
                    badge.style.display = 'block';
                } else {
                    badge.style.display = 'none';
                }
            }
        }
    } catch (error) {
        console.error('Failed to update notification count:', error);
    }
}

if (isAuthenticated()) {
    updateNotificationCount();
    setInterval(updateNotificationCount, 60000);
}

function showNotification(message, type = 'info') {
    showAlert(message, type);
}

function escapeHtml(text) {
    if (text === null || text === undefined) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function getCurrentUser() {
    const userStr = localStorage.getItem('user');
    return userStr ? JSON.parse(userStr) : null;
}

function hasPermission(module, action) {
    const user = getCurrentUser();
    if (!user || !user.permissions) return false;
    
    if (user.permissions.all) return true;
    
    const modulePerms = user.permissions[module];
    if (!modulePerms) return false;
    
    return modulePerms.all || modulePerms[action];
}

function isAuthenticated() {
    return !!localStorage.getItem('token');
}

function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    window.location.href = '/login';
}

function checkAuth() {
    const token = localStorage.getItem('token');
    const publicPaths = ['/login', '/'];
    
    if (!token && !publicPaths.includes(window.location.pathname)) {
        window.location.href = '/login';
        return false;
    }
    return true;
}

function updateUserDisplay() {
    const user = getCurrentUser();
    const usernameEl = document.getElementById('username');
    
    if (user && usernameEl) {
        usernameEl.textContent = user.first_name || user.username;
    }
}

function hideAllModals() {
    document.querySelectorAll('.modal').forEach(modal => {
        modal.classList.remove('active');
    });
}

function formatNumber(number, decimals = 0) {
    if (number === null || number === undefined) return '';
    return new Intl.NumberFormat('en-ZA', {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
    }).format(number);
}

function handleApiError(error) {
    console.error('API Error:', error);
    
    if (error.status === 401) {
        showNotification('Session expired. Please login again.', 'warning');
        setTimeout(() => logout(), 2000);
    } else if (error.status === 403) {
        showNotification('You do not have permission to perform this action', 'danger');
    } else if (error.status === 404) {
        showNotification('Resource not found', 'warning');
    } else if (error.status === 422) {
        showNotification(error.message || 'Validation error', 'warning');
    } else if (error.status === 500) {
        showNotification('Server error. Please try again later.', 'danger');
    } else {
        showNotification(error.message || 'An error occurred', 'danger');
    }
}

function downloadFile(data, filename, type = 'text/plain') {
    const blob = new Blob([data], { type });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
}

function copyToClipboard(text) {
    if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(() => {
            showNotification('Copied to clipboard', 'success');
        }).catch(() => {
            fallbackCopyToClipboard(text);
        });
    } else {
        fallbackCopyToClipboard(text);
    }
}

function fallbackCopyToClipboard(text) {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-9999px';
    document.body.appendChild(textArea);
    textArea.select();
    try {
        document.execCommand('copy');
        showNotification('Copied to clipboard', 'success');
    } catch (err) {
        showNotification('Failed to copy', 'danger');
    }
    document.body.removeChild(textArea);
}

window.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal')) {
        e.target.classList.remove('active');
    }
});

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        hideAllModals();
    }
});

if (checkAuth()) {
    updateUserDisplay();
}

window.addEventListener('storage', (e) => {
    if (e.key === 'token' && !e.newValue) {
        window.location.href = '/login';
    }
});
