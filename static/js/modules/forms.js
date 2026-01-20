let fieldCount = 0;
let editFieldCount = 0;
let currentFormId = null;

async function initForms() {
    const user = getCurrentUser();
    if (user) {
        document.getElementById('username').textContent = `${user.first_name} ${user.last_name}`;
    }
    
    await loadForms();
    
    document.getElementById('formBuilder').addEventListener('submit', handleCreateForm);
    document.getElementById('editFormBuilder').addEventListener('submit', handleUpdateForm);
}

async function loadForms() {
    try {
        const response = await API.forms.getAll();
        
        if (response.success) {
            renderFormsTable(response.data);
        }
    } catch (error) {
        console.error('Error loading forms:', error);
        showAlert('Failed to load forms', 'danger');
    }
}

function renderFormsTable(forms) {
    const tbody = document.getElementById('formsTable');
    
    if (forms.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align: center;">No forms created yet</td></tr>';
        return;
    }
    
    tbody.innerHTML = forms.map(form => {
        let fieldCount = 0;
        try {
            const formDef = typeof form.form_definition === 'string' ? 
                JSON.parse(form.form_definition) : form.form_definition;
            fieldCount = formDef?.fields?.length || 0;
        } catch (e) {
            fieldCount = 0;
        }
        
        return `
            <tr>
                <td>${form.form_code}</td>
                <td>${form.form_name}</td>
                <td><span class="badge badge-info">${form.module}</span></td>
                <td>${fieldCount} fields</td>
                <td>${createStatusBadge(form.is_active ? 'active' : 'inactive')}</td>
                <td>
                    <button class="btn btn-sm btn-primary" onclick="editForm(${form.id})">Edit</button>
                    <button class="btn btn-sm btn-info" onclick="previewForm(${form.id})">Preview</button>
                    <button class="btn btn-sm ${form.is_active ? 'btn-warning' : 'btn-success'}" 
                            onclick="toggleFormStatus(${form.id}, ${form.is_active})">
                        ${form.is_active ? 'Deactivate' : 'Activate'}
                    </button>
                </td>
            </tr>
        `;
    }).join('');
}

function addFormField() {
    fieldCount++;
    const container = document.getElementById('fieldsContainer');
    const fieldDiv = document.createElement('div');
    fieldDiv.className = 'card';
    fieldDiv.style.marginBottom = '1rem';
    fieldDiv.id = `field-${fieldCount}`;
    fieldDiv.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
            <h4>Field ${fieldCount}</h4>
            <button type="button" class="btn btn-sm btn-danger" onclick="removeField('field-${fieldCount}')">Remove</button>
        </div>
        <div class="grid grid-3">
            <div class="form-group">
                <label class="form-label">Field Name*</label>
                <input type="text" class="form-input field-name" required placeholder="e.g., customer_name">
            </div>
            <div class="form-group">
                <label class="form-label">Field Label*</label>
                <input type="text" class="form-input field-label" required placeholder="e.g., Customer Name">
            </div>
            <div class="form-group">
                <label class="form-label">Field Type*</label>
                <select class="form-select field-type" required onchange="handleFieldTypeChange(this, 'field-${fieldCount}')">
                    <option value="text">Text</option>
                    <option value="number">Number</option>
                    <option value="email">Email</option>
                    <option value="date">Date</option>
                    <option value="datetime">Date & Time</option>
                    <option value="textarea">Text Area</option>
                    <option value="select">Dropdown</option>
                    <option value="checkbox">Checkbox</option>
                    <option value="radio">Radio Buttons</option>
                    <option value="file">File Upload</option>
                </select>
            </div>
        </div>
        <div class="grid grid-3">
            <div class="form-group">
                <label class="form-label">Required</label>
                <select class="form-select field-required">
                    <option value="false">No</option>
                    <option value="true">Yes</option>
                </select>
            </div>
            <div class="form-group">
                <label class="form-label">Placeholder</label>
                <input type="text" class="form-input field-placeholder">
            </div>
            <div class="form-group">
                <label class="form-label">Default Value</label>
                <input type="text" class="form-input field-default">
            </div>
        </div>
        <div class="form-group options-container" style="display: none;">
            <label class="form-label">Options (comma-separated)*</label>
            <input type="text" class="form-input field-options" placeholder="Option 1, Option 2, Option 3">
        </div>
        <div class="form-group">
            <label class="form-label">Validation Rules (JSON)</label>
            <textarea class="form-textarea field-validation" rows="2" placeholder='{"min": 0, "max": 100}'></textarea>
        </div>
    `;
    container.appendChild(fieldDiv);
}

function addEditFormField() {
    editFieldCount++;
    const container = document.getElementById('editFieldsContainer');
    const fieldDiv = document.createElement('div');
    fieldDiv.className = 'card';
    fieldDiv.style.marginBottom = '1rem';
    fieldDiv.id = `edit-field-${editFieldCount}`;
    fieldDiv.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
            <h4>Field ${editFieldCount}</h4>
            <button type="button" class="btn btn-sm btn-danger" onclick="removeField('edit-field-${editFieldCount}')">Remove</button>
        </div>
        <div class="grid grid-3">
            <div class="form-group">
                <label class="form-label">Field Name*</label>
                <input type="text" class="form-input edit-field-name" required>
            </div>
            <div class="form-group">
                <label class="form-label">Field Label*</label>
                <input type="text" class="form-input edit-field-label" required>
            </div>
            <div class="form-group">
                <label class="form-label">Field Type*</label>
                <select class="form-select edit-field-type" required onchange="handleFieldTypeChange(this, 'edit-field-${editFieldCount}')">
                    <option value="text">Text</option>
                    <option value="number">Number</option>
                    <option value="email">Email</option>
                    <option value="date">Date</option>
                    <option value="datetime">Date & Time</option>
                    <option value="textarea">Text Area</option>
                    <option value="select">Dropdown</option>
                    <option value="checkbox">Checkbox</option>
                    <option value="radio">Radio Buttons</option>
                    <option value="file">File Upload</option>
                </select>
            </div>
        </div>
        <div class="grid grid-3">
            <div class="form-group">
                <label class="form-label">Required</label>
                <select class="form-select edit-field-required">
                    <option value="false">No</option>
                    <option value="true">Yes</option>
                </select>
            </div>
            <div class="form-group">
                <label class="form-label">Placeholder</label>
                <input type="text" class="form-input edit-field-placeholder">
            </div>
            <div class="form-group">
                <label class="form-label">Default Value</label>
                <input type="text" class="form-input edit-field-default">
            </div>
        </div>
        <div class="form-group edit-options-container" style="display: none;">
            <label class="form-label">Options (comma-separated)*</label>
            <input type="text" class="form-input edit-field-options" placeholder="Option 1, Option 2, Option 3">
        </div>
        <div class="form-group">
            <label class="form-label">Validation Rules (JSON)</label>
            <textarea class="form-textarea edit-field-validation" rows="2" placeholder='{"min": 0, "max": 100}'></textarea>
        </div>
    `;
    container.appendChild(fieldDiv);
}

function handleFieldTypeChange(selectElement, fieldId) {
    const fieldDiv = document.getElementById(fieldId);
    const fieldType = selectElement.value;
    const optionsContainer = fieldDiv.querySelector('.options-container, .edit-options-container');
    
    if (fieldType === 'select' || fieldType === 'radio') {
        optionsContainer.style.display = 'block';
    } else {
        optionsContainer.style.display = 'none';
    }
}

function removeField(fieldId) {
    const fieldDiv = document.getElementById(fieldId);
    if (fieldDiv) {
        fieldDiv.remove();
    }
}

async function handleCreateForm(e) {
    e.preventDefault();
    
    const fields = [];
    const fieldDivs = document.querySelectorAll('#fieldsContainer > div');
    
    fieldDivs.forEach((div, index) => {
        const fieldName = div.querySelector('.field-name').value;
        const fieldLabel = div.querySelector('.field-label').value;
        const fieldType = div.querySelector('.field-type').value;
        const required = div.querySelector('.field-required').value === 'true';
        const placeholder = div.querySelector('.field-placeholder').value;
        const defaultValue = div.querySelector('.field-default').value;
        const options = div.querySelector('.field-options').value;
        const validation = div.querySelector('.field-validation').value;
        
        const field = {
            field_order: index + 1,
            field_name: fieldName,
            field_label: fieldLabel,
            field_type: fieldType,
            required: required,
            placeholder: placeholder || null,
            default_value: defaultValue || null
        };
        
        if (options && (fieldType === 'select' || fieldType === 'radio')) {
            field.options = options.split(',').map(opt => opt.trim());
        }
        
        if (validation) {
            try {
                field.validation_rules = JSON.parse(validation);
            } catch (error) {
                console.error('Invalid validation JSON:', error);
            }
        }
        
        fields.push(field);
    });
    
    const formData = {
        form_code: document.getElementById('formCode').value,
        form_name: document.getElementById('formName').value,
        module: document.getElementById('module').value,
        description: document.getElementById('description').value,
        form_definition: {
            fields: fields,
            layout: 'standard'
        }
    };
    
    try {
        const response = await API.forms.create(formData);
        if (response.success) {
            showAlert('Form created successfully', 'success');
            hideModal('addFormModal');
            document.getElementById('formBuilder').reset();
            document.getElementById('fieldsContainer').innerHTML = '';
            fieldCount = 0;
            await loadForms();
        } else {
            showAlert(response.message || 'Failed to create form', 'danger');
        }
    } catch (error) {
        console.error('Error creating form:', error);
        showAlert('Failed to create form', 'danger');
    }
}

async function editForm(id) {
    try {
        const response = await API.forms.getById(id);
        if (response.success) {
            const form = response.data;
            
            document.getElementById('editFormId').value = form.id;
            document.getElementById('editFormCode').value = form.form_code;
            document.getElementById('editFormName').value = form.form_name;
            document.getElementById('editModule').value = form.module;
            document.getElementById('editDescription').value = form.description || '';
            
            const fieldsContainer = document.getElementById('editFieldsContainer');
            fieldsContainer.innerHTML = '';
            editFieldCount = 0;
            
            const formDef = typeof form.form_definition === 'string' ? 
                JSON.parse(form.form_definition) : form.form_definition;
            const fields = formDef?.fields || [];
            
            fields.forEach(field => {
                addEditFormField();
                const fieldDiv = document.getElementById(`edit-field-${editFieldCount}`);
                
                fieldDiv.querySelector('.edit-field-name').value = field.field_name || '';
                fieldDiv.querySelector('.edit-field-label').value = field.field_label || '';
                fieldDiv.querySelector('.edit-field-type').value = field.field_type || 'text';
                fieldDiv.querySelector('.edit-field-required').value = field.required ? 'true' : 'false';
                fieldDiv.querySelector('.edit-field-placeholder').value = field.placeholder || '';
                fieldDiv.querySelector('.edit-field-default').value = field.default_value || '';
                
                if (field.options) {
                    fieldDiv.querySelector('.edit-field-options').value = Array.isArray(field.options) ? 
                        field.options.join(', ') : field.options;
                }
                
                if (field.validation_rules) {
                    fieldDiv.querySelector('.edit-field-validation').value = JSON.stringify(field.validation_rules);
                }
                
                handleFieldTypeChange(fieldDiv.querySelector('.edit-field-type'), `edit-field-${editFieldCount}`);
            });
            
            showModal('editFormModal');
        }
    } catch (error) {
        console.error('Error loading form:', error);
        showAlert('Failed to load form', 'danger');
    }
}

async function handleUpdateForm(e) {
    e.preventDefault();
    
    const fields = [];
    const fieldDivs = document.querySelectorAll('#editFieldsContainer > div');
    
    fieldDivs.forEach((div, index) => {
        const fieldName = div.querySelector('.edit-field-name').value;
        const fieldLabel = div.querySelector('.edit-field-label').value;
        const fieldType = div.querySelector('.edit-field-type').value;
        const required = div.querySelector('.edit-field-required').value === 'true';
        const placeholder = div.querySelector('.edit-field-placeholder').value;
        const defaultValue = div.querySelector('.edit-field-default').value;
        const options = div.querySelector('.edit-field-options').value;
        const validation = div.querySelector('.edit-field-validation').value;
        
        const field = {
            field_order: index + 1,
            field_name: fieldName,
            field_label: fieldLabel,
            field_type: fieldType,
            required: required,
            placeholder: placeholder || null,
            default_value: defaultValue || null
        };
        
        if (options && (fieldType === 'select' || fieldType === 'radio')) {
            field.options = options.split(',').map(opt => opt.trim());
        }
        
        if (validation) {
            try {
                field.validation_rules = JSON.parse(validation);
            } catch (error) {
                console.error('Invalid validation JSON:', error);
            }
        }
        
        fields.push(field);
    });
    
    const formData = {
        form_name: document.getElementById('editFormName').value,
        module: document.getElementById('editModule').value,
        description: document.getElementById('editDescription').value,
        form_definition: {
            fields: fields,
            layout: 'standard'
        }
    };
    
    const formId = document.getElementById('editFormId').value;
    
    try {
        const response = await API.forms.update(formId, formData);
        if (response.success) {
            showAlert('Form updated successfully', 'success');
            hideModal('editFormModal');
            await loadForms();
        } else {
            showAlert(response.message || 'Failed to update form', 'danger');
        }
    } catch (error) {
        console.error('Error updating form:', error);
        showAlert('Failed to update form', 'danger');
    }
}

async function toggleFormStatus(id, currentStatus) {
    try {
        const response = await API.forms.update(id, { is_active: !currentStatus });
        if (response.success) {
            showAlert(`Form ${!currentStatus ? 'activated' : 'deactivated'} successfully`, 'success');
            await loadForms();
        } else {
            showAlert(response.message || 'Failed to update form status', 'danger');
        }
    } catch (error) {
        console.error('Error toggling form status:', error);
        showAlert('Failed to update form status', 'danger');
    }
}

async function previewForm(id) {
    try {
        const response = await API.forms.getById(id);
        if (response.success) {
            const form = response.data;
            const formDef = typeof form.form_definition === 'string' ? 
                JSON.parse(form.form_definition) : form.form_definition;
            
            let previewHTML = `
                <div class="modal" id="previewModal" style="display: block;">
                    <div class="modal-content" style="max-width: 800px;">
                        <div class="modal-header">${form.form_name} - Preview</div>
                        <div style="padding: 1rem;">
                            <p><strong>Module:</strong> ${form.module}</p>
                            <p><strong>Description:</strong> ${form.description || 'N/A'}</p>
                            <hr>
                            <form>
            `;
            
            formDef.fields.forEach(field => {
                previewHTML += `<div class="form-group">`;
                previewHTML += `<label class="form-label">${field.field_label}${field.required ? '*' : ''}</label>`;
                
                switch(field.field_type) {
                    case 'textarea':
                        previewHTML += `<textarea class="form-textarea" placeholder="${field.placeholder || ''}" ${field.required ? 'required' : ''}>${field.default_value || ''}</textarea>`;
                        break;
                    case 'select':
                        previewHTML += `<select class="form-select" ${field.required ? 'required' : ''}>`;
                        previewHTML += `<option value="">Select...</option>`;
                        if (field.options) {
                            field.options.forEach(opt => {
                                previewHTML += `<option value="${opt}">${opt}</option>`;
                            });
                        }
                        previewHTML += `</select>`;
                        break;
                    case 'radio':
                        if (field.options) {
                            field.options.forEach(opt => {
                                previewHTML += `<label><input type="radio" name="${field.field_name}" value="${opt}" ${field.required ? 'required' : ''}> ${opt}</label><br>`;
                            });
                        }
                        break;
                    case 'checkbox':
                        previewHTML += `<input type="checkbox" ${field.default_value === 'true' ? 'checked' : ''}>`;
                        break;
                    default:
                        previewHTML += `<input type="${field.field_type}" class="form-input" placeholder="${field.placeholder || ''}" value="${field.default_value || ''}" ${field.required ? 'required' : ''}>`;
                }
                
                previewHTML += `</div>`;
            });
            
            previewHTML += `
                            </form>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" onclick="closePreview()">Close</button>
                        </div>
                    </div>
                </div>
            `;
            
            const previewContainer = document.createElement('div');
            previewContainer.innerHTML = previewHTML;
            document.body.appendChild(previewContainer);
        }
    } catch (error) {
        console.error('Error previewing form:', error);
        showAlert('Failed to preview form', 'danger');
    }
}

function closePreview() {
    const previewModal = document.getElementById('previewModal');
    if (previewModal) {
        previewModal.parentElement.remove();
    }
}

document.addEventListener('DOMContentLoaded', initForms);
