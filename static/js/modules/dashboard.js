class DashboardPage {
    constructor() {
        this.init();
    }

    init() {
        const user = getCurrentUser();
        if (user) {
            const usernameEl = document.getElementById('username');
            if (usernameEl) {
                usernameEl.textContent = `${user.first_name} ${user.last_name}`;
            }
        }

        this.attachEventListeners();
        this.loadDashboard();
    }

    attachEventListeners() {
        const logoutBtn = document.querySelector('.logout-btn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', (e) => {
                e.preventDefault();
                logout();
            });
        }
    }

    async loadDashboard() {
        try {
            const ordersResponse = await API.orders.getAll({ status: 'in_progress' });
            if (ordersResponse.success) {
                document.getElementById('activeJobs').textContent = ordersResponse.data.length;
            }
            
            const allOrdersResponse = await API.orders.getAll();
            if (allOrdersResponse.success) {
                document.getElementById('totalOrders').textContent = allOrdersResponse.data.length;
                
                const recentOrders = allOrdersResponse.data.slice(0, 5);
                const ordersHtml = recentOrders.map(order => `
                    <div class="dashboard-item">
                        <strong>${order.order_number}</strong> - ${order.customer_name}<br>
                        <small>${createStatusBadge(order.status)}</small>
                    </div>
                `).join('');
                document.getElementById('recentOrders').innerHTML = ordersHtml || 'No recent orders';
            }
            
            const defectsResponse = await API.defects.getReplacementTickets({ status: 'pending_approval' });
            if (defectsResponse.success) {
                document.getElementById('pendingDefects').textContent = defectsResponse.data.length;
            }
            
            const maintenanceResponse = await API.maintenance.getTickets({ status: 'open' });
            if (maintenanceResponse.success) {
                document.getElementById('openMaintenance').textContent = maintenanceResponse.data.length;
            }
            
            const notificationsResponse = await API.notifications.getAll({ limit: 5 });
            if (notificationsResponse.success) {
                const notificationsHtml = notificationsResponse.data.map(notif => `
                    <div class="dashboard-item">
                        <strong>${notif.title}</strong><br>
                        <small>${notif.message}</small><br>
                        <small class="dashboard-item-timestamp">${formatDateTime(notif.created_at)}</small>
                    </div>
                `).join('');
                document.getElementById('recentNotifications').innerHTML = notificationsHtml || 'No notifications';
            }
        } catch (error) {
            console.error('Error loading dashboard:', error);
            showAlert('Failed to load dashboard data', 'danger');
        }
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => new DashboardPage());
} else {
    new DashboardPage();
}
