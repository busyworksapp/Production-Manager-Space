const navigationConfig = [
    {
        label: 'Dashboard',
        icon: '📊',
        href: '/dashboard',
        permission: null
    },
    {
        label: 'Planning',
        icon: '📅',
        permission: { module: 'planning', action: 'read' },
        children: [
            { label: 'Orders', href: '/planning/orders' },
            { label: 'Schedule', href: '/planning/schedule' },
            { label: 'Capacity Planning', href: '/planning/capacity' },
            { label: 'Machine Calendar', href: '/planning/machine-calendar' }
        ]
    },
    {
        label: 'Defects & QC',
        icon: '🔍',
        permission: { module: 'qc', action: 'read' },
        children: [
            { label: 'Replacement Tickets', href: '/defects/replacement-tickets' },
            { label: 'Customer Returns', href: '/defects/customer-returns' },
            { label: 'Cost Analysis', href: '/defects/cost-analysis' }
        ]
    },
    {
        label: 'SOP & NCR',
        icon: '📋',
        href: '/sop/tickets',
        permission: { module: 'sop', action: 'read' }
    },
    {
        label: 'Maintenance',
        icon: '🔧',
        permission: { module: 'maintenance', action: 'read' },
        children: [
            { label: 'Tickets', href: '/maintenance/tickets' },
            { label: 'Analytics', href: '/maintenance/analytics' },
            { label: 'Preventive', href: '/maintenance/preventive' }
        ]
    },
    {
        label: 'Finance',
        icon: '💰',
        permission: { module: 'finance', action: 'read' },
        children: [
            { label: 'BOM', href: '/finance/bom' },
            { label: 'Costs', href: '/finance/costs' }
        ]
    },
    {
        label: 'Reports',
        icon: '📈',
        href: '/reports/configuration',
        permission: { module: 'reports', action: 'read' }
    },
    {
        label: 'Admin',
        icon: '⚙️',
        permission: { module: 'admin', action: 'read' },
        children: [
            { label: 'Departments', href: '/admin/departments' },
            { label: 'Employees', href: '/admin/employees' },
            { label: 'Machines', href: '/admin/machines' },
            { label: 'Products', href: '/admin/products' },
            { label: 'Forms', href: '/admin/forms' },
            { label: 'Workflows', href: '/admin/workflows' },
            { label: 'SLA', href: '/admin/sla' },
            { label: 'Roles', href: '/admin/roles' },
            { label: 'D365 Integration', href: '/admin/d365' }
        ]
    }
];

function hasPermission(permission) {
    if (!permission) return true;
    
    const user = getCurrentUser();
    if (!user || !user.permissions) return false;
    
    let perms = user.permissions;
    if (typeof perms === 'string') {
        try {
            perms = JSON.parse(perms);
        } catch (e) {
            return false;
        }
    }
    
    if (perms.all) return true;
    
    const modulePerms = perms[permission.module];
    if (!modulePerms) return false;
    
    return modulePerms[permission.action] || modulePerms.all;
}

function renderSidebarNav() {
    const sidebarNav = document.querySelector('.sidebar-nav');
    if (!sidebarNav) return;
    
    sidebarNav.innerHTML = '';
    
    const section = document.createElement('div');
    section.className = 'nav-section';
    
    const items = document.createElement('ul');
    items.className = 'nav-items';
    
    navigationConfig.forEach(item => {
        if (item.permission && !hasPermission(item.permission)) {
            return;
        }
        
        const navItem = document.createElement('li');
        navItem.className = 'nav-item';
        
        if (item.children && item.children.length > 0) {
            const dropdown = document.createElement('div');
            dropdown.className = 'nav-dropdown';
            
            const trigger = document.createElement('button');
            trigger.className = 'dropdown-trigger';
            trigger.innerHTML = `
                <div style="display: flex; align-items: center; gap: 12px; flex: 1;">
                    <span class="nav-icon">${item.icon || '•'}</span>
                    <span>${item.label}</span>
                </div>
                <span class="dropdown-arrow">▼</span>
            `;
            
            const menu = document.createElement('div');
            menu.className = 'dropdown-menu';
            
            item.children.forEach(child => {
                const link = document.createElement('a');
                link.href = child.href;
                link.className = 'dropdown-item';
                link.textContent = child.label;
                
                if (window.location.pathname === child.href) {
                    link.classList.add('active');
                }
                
                menu.appendChild(link);
            });
            
            dropdown.appendChild(trigger);
            dropdown.appendChild(menu);
            navItem.appendChild(dropdown);
            
            trigger.addEventListener('click', (e) => {
                e.stopPropagation();
                dropdown.classList.toggle('open');
            });
        } else {
            const link = document.createElement('a');
            link.href = item.href;
            link.className = 'nav-link';
            link.innerHTML = `
                <span class="nav-icon">${item.icon || '•'}</span>
                <span>${item.label}</span>
            `;
            
            if (window.location.pathname === item.href) {
                link.classList.add('active');
            }
            
            navItem.appendChild(link);
        }
        
        items.appendChild(navItem);
    });
    
    section.appendChild(items);
    sidebarNav.appendChild(section);
}

function renderTopNav() {
    const nav = document.querySelector('.nav');
    if (!nav) return;
    
    nav.innerHTML = '';
    
    navigationConfig.forEach(item => {
        if (item.permission && !hasPermission(item.permission)) {
            return;
        }
        
        if (item.children && item.children.length > 0) {
            const dropdown = document.createElement('div');
            dropdown.className = 'nav-dropdown';
            
            const trigger = document.createElement('button');
            trigger.className = 'nav-link dropdown-trigger';
            trigger.textContent = item.label;
            
            const menu = document.createElement('div');
            menu.className = 'dropdown-menu';
            
            item.children.forEach(child => {
                const link = document.createElement('a');
                link.href = child.href;
                link.className = 'dropdown-item';
                link.textContent = child.label;
                
                if (window.location.pathname === child.href) {
                    link.classList.add('active');
                }
                
                menu.appendChild(link);
            });
            
            dropdown.appendChild(trigger);
            dropdown.appendChild(menu);
            nav.appendChild(dropdown);
            
            trigger.addEventListener('click', (e) => {
                e.stopPropagation();
                const wasOpen = dropdown.classList.contains('open');
                
                document.querySelectorAll('.nav-dropdown').forEach(d => {
                    d.classList.remove('open');
                });
                
                if (!wasOpen) {
                    dropdown.classList.add('open');
                }
            });
        } else {
            const link = document.createElement('a');
            link.href = item.href;
            link.className = 'nav-link';
            link.textContent = item.label;
            
            if (window.location.pathname === item.href) {
                link.classList.add('active');
            }
            
            nav.appendChild(link);
        }
    });
    
    document.addEventListener('click', () => {
        document.querySelectorAll('.nav-dropdown').forEach(d => {
            d.classList.remove('open');
        });
    });
}

function renderNavigation() {
    renderSidebarNav();
    renderTopNav();
}

if (window.location.pathname !== '/login') {
    document.addEventListener('DOMContentLoaded', renderNavigation);
    
    window.addEventListener('user-loaded', renderNavigation);
}
