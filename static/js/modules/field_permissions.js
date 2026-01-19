let allPermissions = [];
let allRoles = [];

async function filterPermissions() {
    const roleId = document.getElementById('filterRole')?.value;
    const entityType = document.getElementById('filterEntity')?.value;
    const searchField = document.getElementById('searchField')?.value;

    const params = new URLSearchParams();
    if (roleId) params.append('role_id', roleId);
    if (entityType) params.append('entity_type', entityType);

    try {
        const response = await fetch(`/api/field-permissions?${params.toString()}`, {
            headers: getAuthHeaders()
        });
        const data = await response.json();

        if (data.success) {
            allPermissions = data.data;
            let filtered = data.data;

            if (searchField) {
                filtered = filtered.filter(p => 
                    p.field_name.toLowerCase().includes(searchField.toLowerCase())
                );
            }

            renderPermissions(filtered);
        }
    } catch (error) {
        console.error('Error loading field permissions:', error);
        showNotification('Failed to load field permissions', 'error');
    }
}

function renderPermissions(permissions) {
    const tbody = document.getElementById('permissionsTable');
    if (!tbody) return;

    if (permissions.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align: center;">No field permissions found</td></tr>';
        return;
    }

    tbody.innerHTML = permissions.map(perm => `
        <tr>
            <td>${escapeHtml(perm.role_name || '-')}</td>
            <td><span class="badge badge-info">${escapeHtml(perm.entity_type)}</span></td>
            <td><code>${escapeHtml(perm.field_name)}</code></td>
            <td><span class="badge badge-${getPermissionColor(perm.permission_type)}">${escapeHtml(perm.permission_type)}</span></td>
            <td>${perm.conditional_rules ? '<span class="badge badge-warning">Yes</span>' : '<span class="badge badge-secondary">No</span>'}</td>
            <td>${perm.created_at ? new Date(perm.created_at).toLocaleDateString() : '-'}</td>
            <td>
                ${perm.conditional_rules ? `<button class="btn btn-sm btn-secondary" onclick="viewConditions(${perm.id})">View</button>` : ''}
                <button class="btn btn-sm btn-secondary" onclick="editPermission(${perm.id})">Edit</button>
                <button class="btn btn-sm btn-danger" onclick="deletePermission(${perm.id})">Delete</button>
            </td>
        </tr>
    `).join('');
}

function getPermissionColor(type) {
    const colors = {
        'read': 'info',
        'write': 'success',
        'hidden': 'secondary',
        'required': 'warning'
    };
    return colors[type] || 'secondary';
}

async function loadRoles() {
    try {
        const response = await fetch('/api/auth/roles', {
            headers: getAuthHeaders()
        });
        const data = await response.json();

        if (data.success) {
            allRoles = data.data;
            const selects = ['roleId', 'filterRole'];
            selects.forEach(selectId => {
                const select = document.getElementById(selectId);
                if (select) {
                    const hasFilter = selectId.startsWith('filter');
                    select.innerHTML = (hasFilter ? '<option value="">All Roles</option>' : '<option value="">Select Role</option>') +
                        data.data.map(role => `<option value="${role.id}">${escapeHtml(role.name)}</option>`).join('');
                }
            });
        }
    } catch (error) {
        console.error('Error loading roles:', error);
    }
}

async function viewConditions(id) {
    const permission = allPermissions.find(p => p.id === id);
    if (!permission) return;

    const content = document.getElementById('conditionsContent');
    if (!content) return;

    try {
        const rules = typeof permission.conditional_rules === 'string' 
            ? JSON.parse(permission.conditional_rules) 
            : permission.conditional_rules;

        content.innerHTML = `
            <div class="form-group">
                <label class="form-label">Entity: ${escapeHtml(permission.entity_type)}</label>
                <label class="form-label">Field: ${escapeHtml(permission.field_name)}</label>
                <label class="form-label">Permission: ${escapeHtml(permission.permission_type)}</label>
            </div>
            <div class="form-group">
                <label class="form-label">Conditional Rules:</label>
                <pre style="background: var(--color-bg-main); padding: 1rem; border-radius: var(--border-radius); overflow-x: auto;">${JSON.stringify(rules, null, 2)}</pre>
            </div>
        `;
    } catch (e) {
        content.innerHTML = `
            <div class="alert alert-danger">Invalid JSON format in conditional rules</div>
            <pre style="background: var(--color-bg-main); padding: 1rem; border-radius: var(--border-radius);">${escapeHtml(permission.conditional_rules)}</pre>
        `;
    }

    showModal('viewConditionsModal');
}

async function editPermission(id) {
    try {
        const response = await fetch(`/api/field-permissions/${id}`, {
            headers: getAuthHeaders()
        });
        const data = await response.json();

        if (data.success) {
            const perm = data.data;
            
            document.getElementById('editPermissionId').value = perm.id;
            document.getElementById('editRoleName').value = perm.role_name || '';
            document.getElementById('editEntityType').value = perm.entity_type || '';
            document.getElementById('editFieldName').value = perm.field_name || '';
            document.getElementById('editPermissionType').value = perm.permission_type || '';
            
            const rulesValue = perm.conditional_rules 
                ? (typeof perm.conditional_rules === 'string' 
                    ? perm.conditional_rules 
                    : JSON.stringify(perm.conditional_rules, null, 2))
                : '';
            document.getElementById('editConditionalRules').value = rulesValue;

            showModal('editPermissionModal');
        }
    } catch (error) {
        console.error('Error loading permission:', error);
        showNotification('Failed to load permission', 'error');
    }
}

async function deletePermission(id) {
    if (!confirm('Are you sure you want to delete this field permission?')) return;

    try {
        const response = await fetch(`/api/field-permissions/${id}`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });
        const data = await response.json();

        if (data.success) {
            showNotification('Field permission deleted successfully', 'success');
            filterPermissions();
        } else {
            showNotification(data.message || 'Failed to delete field permission', 'error');
        }
    } catch (error) {
        console.error('Error deleting permission:', error);
        showNotification('Failed to delete field permission', 'error');
    }
}

document.getElementById('permissionForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();

    const conditionalRulesValue = document.getElementById('conditionalRules').value.trim();
    let conditionalRules = null;

    if (conditionalRulesValue) {
        try {
            conditionalRules = JSON.parse(conditionalRulesValue);
        } catch (error) {
            showNotification('Invalid JSON format in conditional rules', 'error');
            return;
        }
    }

    const formData = {
        role_id: parseInt(document.getElementById('roleId').value),
        entity_type: document.getElementById('entityType').value,
        field_name: document.getElementById('fieldName').value,
        permission_type: document.getElementById('permissionType').value,
        conditional_rules: conditionalRules ? JSON.stringify(conditionalRules) : null
    };

    try {
        const response = await fetch('/api/field-permissions', {
            method: 'POST',
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });
        const data = await response.json();

        if (data.success) {
            showNotification('Field permission created successfully', 'success');
            hideModal('addPermissionModal');
            document.getElementById('permissionForm').reset();
            filterPermissions();
        } else {
            showNotification(data.message || 'Failed to create field permission', 'error');
        }
    } catch (error) {
        console.error('Error creating permission:', error);
        showNotification('Failed to create field permission', 'error');
    }
});

document.getElementById('editPermissionForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();

    const id = document.getElementById('editPermissionId').value;
    const conditionalRulesValue = document.getElementById('editConditionalRules').value.trim();
    let conditionalRules = null;

    if (conditionalRulesValue) {
        try {
            conditionalRules = JSON.parse(conditionalRulesValue);
        } catch (error) {
            showNotification('Invalid JSON format in conditional rules', 'error');
            return;
        }
    }

    const formData = {
        permission_type: document.getElementById('editPermissionType').value,
        conditional_rules: conditionalRules ? JSON.stringify(conditionalRules) : null
    };

    try {
        const response = await fetch(`/api/field-permissions/${id}`, {
            method: 'PUT',
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });
        const data = await response.json();

        if (data.success) {
            showNotification('Field permission updated successfully', 'success');
            hideModal('editPermissionModal');
            filterPermissions();
        } else {
            showNotification(data.message || 'Failed to update field permission', 'error');
        }
    } catch (error) {
        console.error('Error updating permission:', error);
        showNotification('Failed to update field permission', 'error');
    }
});

window.addEventListener('DOMContentLoaded', async () => {
    await loadRoles();
    await filterPermissions();
});
