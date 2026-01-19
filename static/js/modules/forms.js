let allForms = [];
let currentFormFields = [];

async function loadForms() {
    try {
        const response = await fetch('/api/forms', {
            headers: getAuthHeaders()
        });
        const data = await response.json();

        if (data.success) {
            allForms = data.data;
            renderForms(data.data);
        }
    } catch (error) {
        console.error('Error loading forms:', error);
        showNotification('Failed to load forms', 'error');
    }
}

function renderForms(forms) {
    const tbody = document.getElementById('formsTable');
    if (!tbody) return;

    if (forms.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align: center;">No forms found</td></tr>';
        return;
    }

    tbody.innerHTML = forms.map(form => `
        <tr>
            <td>${escapeHtml(form.form_name)}</td>
            <td>${escapeHtml(form.form_code)}</td>
            <td>${escapeHtml(form.module)}</td>
            <td>${form.fields_count || 0} fields</td>
            <td><span class="badge badge-${form.is_active ? 'success' : 'secondary'}">${form.is_active ? 'Active' : 'Inactive'}</span></td>
            <td>
                <button class="btn btn-sm btn-secondary" onclick="viewForm(${form.id})">View</button>
                <button class="btn btn-sm btn-primary" onclick="editForm(${form.id})">Edit</button>
            </td>
        </tr>
    `).join('');
}

async function viewForm(id) {
    try {
        const response = await fetch(`/api/forms/${id}`, {
            headers: getAuthHeaders()
        });
        const data = await response.json();

        if (data.success) {
            const form = data.data;
            const detailsDiv = document.getElementById('formDetails');
            if (detailsDiv) {
                detailsDiv.innerHTML = `
                    <div class="grid grid-2">
                        <div><strong>Form Name:</strong> ${escapeHtml(form.form_name)}</div>
                        <div><strong>Form Code:</strong> ${escapeHtml(form.form_code)}</div>
                        <div><strong>Module:</strong> ${escapeHtml(form.module)}</div>
                        <div><strong>Status:</strong> <span class="badge badge-${form.is_active ? 'success' : 'secondary'}">${form.is_active ? 'Active' : 'Inactive'}</span></div>
                    </div>
                    ${form.description ? `<div style="margin-top: 1rem;"><strong>Description:</strong><p>${escapeHtml(form.description)}</p></div>` : ''}
                    <div style="margin-top: 1.5rem;">
                        <strong>Form Fields:</strong>
                        <pre style="background: var(--color-bg-main); padding: 1rem; border-radius: var(--border-radius); overflow-x: auto;">${JSON.stringify(form.form_definition, null, 2)}</pre>
                    </div>
                `;
            }
            showModal('viewFormModal');
        }
    } catch (error) {
        console.error('Error loading form details:', error);
        showNotification('Failed to load form details', 'error');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    loadForms();
});
