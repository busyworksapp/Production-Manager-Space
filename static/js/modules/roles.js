let allRoles = [];

async function loadRoles() {
    try {
        const response = await fetch('/api/auth/roles', {
            headers: getAuthHeaders()
        });
        const data = await response.json();

        if (data.success) {
            allRoles = data.data;
            renderRoles(data.data);
        }
    } catch (error) {
        console.error('Error loading roles:', error);
        showNotification('Failed to load roles', 'error');
    }
}

function renderRoles(roles) {
    const tbody = document.getElementById('rolesTable');
    if (!tbody) return;

    if (roles.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align: center;">No roles found</td></tr>';
        return;
    }

    tbody.innerHTML = roles.map(role => `
        <tr>
            <td>${escapeHtml(role.name)}</td>
            <td>${escapeHtml(role.description || '-')}</td>
            <td>${role.users_count || 0}</td>
            <td><span class="badge badge-${role.is_active ? 'success' : 'secondary'}">${role.is_active ? 'Active' : 'Inactive'}</span></td>
            <td>${role.created_at ? new Date(role.created_at).toLocaleDateString() : '-'}</td>
            <td>
                <button class="btn btn-sm btn-secondary" onclick="editRole(${role.id})">Edit</button>
                ${role.users_count === 0 ? `<button class="btn btn-sm btn-danger" onclick="deleteRole(${role.id})">Delete</button>` : ''}
            </td>
        </tr>
    `).join('');
}

async function editRole(id) {
    try {
        const response = await fetch(`/api/auth/roles/${id}`, {
            headers: getAuthHeaders()
        });
        const data = await response.json();

        if (data.success) {
            const role = data.data;
            
            document.getElementById('editRoleId').value = role.id;
            document.getElementById('editRoleName').value = role.name;
            document.getElementById('editDescription').value = role.description || '';
            document.getElementById('editIsActive').checked = role.is_active;

            const permissionsContainer = document.getElementById('editPermissionsContainer');
            if (permissionsContainer && role.permissions) {
                permissionsContainer.innerHTML = renderPermissionCheckboxes(role.permissions, 'edit');
            }

            showModal('editRoleModal');
        }
    } catch (error) {
        console.error('Error loading role:', error);
        showNotification('Failed to load role', 'error');
    }
}

function renderPermissionCheckboxes(permissions, prefix = '') {
    const modules = ['planning', 'defects', 'sop', 'maintenance', 'finance', 'admin'];
    const perms = ['read', 'write', 'approve', 'delete'];

    return `
        <div class="grid grid-2">
            ${modules.map(module => `
                <div class="form-group">
                    <strong>${capitalizeFirst(module)} Module</strong>
                    ${perms.map(perm => `
                        <label>
                            <input type="checkbox" class="${prefix}permission-check" 
                                   data-module="${module}" 
                                   data-perm="${perm}"
                                   ${permissions[module] && permissions[module][perm] ? 'checked' : ''}>
                            ${capitalizeFirst(perm)}
                        </label>
                    `).join('')}
                </div>
            `).join('')}
        </div>
    `;
}

function capitalizeFirst(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
}

function getPermissionsFromCheckboxes(prefix = '') {
    const permissions = {};
    const checkboxes = document.querySelectorAll(`.${prefix}permission-check:checked`);
    
    checkboxes.forEach(cb => {
        const module = cb.dataset.module;
        const perm = cb.dataset.perm;
        
        if (!permissions[module]) permissions[module] = {};
        permissions[module][perm] = true;
    });

    return permissions;
}

document.getElementById('roleForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();

    const formData = {
        name: document.getElementById('roleName').value,
        description: document.getElementById('description').value,
        permissions: getPermissionsFromCheckboxes(''),
        is_active: document.getElementById('isActive').checked
    };

    try {
        const response = await fetch('/api/auth/roles', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(formData)
        });
        const data = await response.json();

        if (data.success) {
            showNotification('Role created successfully', 'success');
            hideModal('addRoleModal');
            loadRoles();
            document.getElementById('roleForm').reset();
        } else {
            showNotification(data.error || 'Failed to create role', 'error');
        }
    } catch (error) {
        console.error('Error creating role:', error);
        showNotification('Failed to create role', 'error');
    }
});

document.getElementById('editRoleForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();

    const roleId = document.getElementById('editRoleId').value;
    const formData = {
        name: document.getElementById('editRoleName').value,
        description: document.getElementById('editDescription').value,
        permissions: getPermissionsFromCheckboxes('edit'),
        is_active: document.getElementById('editIsActive').checked
    };

    try {
        const response = await fetch(`/api/auth/roles/${roleId}`, {
            method: 'PUT',
            headers: getAuthHeaders(),
            body: JSON.stringify(formData)
        });
        const data = await response.json();

        if (data.success) {
            showNotification('Role updated successfully', 'success');
            hideModal('editRoleModal');
            loadRoles();
        } else {
            showNotification(data.error || 'Failed to update role', 'error');
        }
    } catch (error) {
        console.error('Error updating role:', error);
        showNotification('Failed to update role', 'error');
    }
});

document.addEventListener('DOMContentLoaded', () => {
    loadRoles();
    
    const addModal = document.getElementById('addRoleModal');
    if (addModal) {
        const container = document.getElementById('permissionsContainer');
        if (container) {
            container.innerHTML = renderPermissionCheckboxes({}, '');
        }
    }
});
