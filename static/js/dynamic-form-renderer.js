/**
 * Dynamic Form Renderer
 * Renders forms from JSON configuration with full validation, conditional logic, and field permissions
 */

class DynamicFormRenderer {
    constructor(containerEl, formConfig, options = {}) {
        this.container = containerEl;
        this.config = formConfig;
        this.options = {
            mode: options.mode || 'create',
            data: options.data || {},
            onSubmit: options.onSubmit || null,
            onCancel: options.onCancel || null,
            permissions: options.permissions || {},
            ...options
        };
        
        this.formData = { ...this.options.data };
        this.validationErrors = {};
        this.conditionalStates = {};
        this.fieldElements = {};
    }
    
    async render() {
        if (!this.config || !this.config.form_definition) {
            console.error('Invalid form configuration');
            return;
        }
        
        const formDef = typeof this.config.form_definition === 'string' 
            ? JSON.parse(this.config.form_definition) 
            : this.config.form_definition;
        
        const validationRules = this.config.validation_rules 
            ? (typeof this.config.validation_rules === 'string' 
                ? JSON.parse(this.config.validation_rules) 
                : this.config.validation_rules)
            : {};
        
        this.fieldPermissions = await this.loadFieldPermissions();
        
        const formEl = document.createElement('form');
        formEl.className = 'dynamic-form';
        formEl.id = `dynamic-form-${this.config.id || 'new'}`;
        
        if (formDef.sections && formDef.sections.length > 0) {
            formDef.sections.forEach(section => {
                const sectionEl = this.renderSection(section, validationRules);
                formEl.appendChild(sectionEl);
            });
        } else if (formDef.fields && formDef.fields.length > 0) {
            const defaultSection = {
                title: '',
                fields: formDef.fields
            };
            const sectionEl = this.renderSection(defaultSection, validationRules);
            formEl.appendChild(sectionEl);
        }
        
        const actionsEl = this.renderActions();
        formEl.appendChild(actionsEl);
        
        formEl.addEventListener('submit', (e) => this.handleSubmit(e));
        
        this.container.innerHTML = '';
        this.container.appendChild(formEl);
        
        this.evaluateAllConditionalLogic();
    }
    
    renderSection(section, validationRules) {
        const sectionEl = document.createElement('div');
        sectionEl.className = 'form-section';
        
        if (section.title) {
            const titleEl = document.createElement('h3');
            titleEl.className = 'form-section-title';
            titleEl.textContent = section.title;
            sectionEl.appendChild(titleEl);
        }
        
        if (section.description) {
            const descEl = document.createElement('p');
            descEl.className = 'form-section-description';
            descEl.textContent = section.description;
            sectionEl.appendChild(descEl);
        }
        
        const fieldsContainer = document.createElement('div');
        fieldsContainer.className = section.layout === 'grid' ? 'grid grid-2' : 'form-fields';
        
        section.fields.forEach(field => {
            const fieldEl = this.renderField(field, validationRules[field.name] || {});
            if (fieldEl) {
                fieldsContainer.appendChild(fieldEl);
            }
        });
        
        sectionEl.appendChild(fieldsContainer);
        return sectionEl;
    }
    
    renderField(field, validation) {
        const permission = this.getFieldPermission(field.name);
        
        if (permission === 'hidden') {
            return null;
        }
        
        const formGroupEl = document.createElement('div');
        formGroupEl.className = 'form-group';
        formGroupEl.dataset.fieldName = field.name;
        
        if (field.label) {
            const labelEl = document.createElement('label');
            labelEl.className = 'form-label';
            labelEl.textContent = field.label;
            if (validation.required || field.required) {
                labelEl.textContent += '*';
            }
            formGroupEl.appendChild(labelEl);
        }
        
        let inputEl;
        
        switch (field.type) {
            case 'text':
            case 'email':
            case 'url':
            case 'tel':
                inputEl = this.renderTextInput(field, validation);
                break;
            case 'number':
                inputEl = this.renderNumberInput(field, validation);
                break;
            case 'textarea':
                inputEl = this.renderTextarea(field, validation);
                break;
            case 'select':
            case 'dropdown':
                inputEl = this.renderSelect(field, validation);
                break;
            case 'date':
            case 'datetime':
            case 'time':
                inputEl = this.renderDateInput(field, validation);
                break;
            case 'checkbox':
                inputEl = this.renderCheckbox(field, validation);
                break;
            case 'radio':
                inputEl = this.renderRadioGroup(field, validation);
                break;
            case 'lookup':
            case 'autocomplete':
                inputEl = this.renderLookup(field, validation);
                break;
            case 'file':
                inputEl = this.renderFileInput(field, validation);
                break;
            default:
                inputEl = this.renderTextInput(field, validation);
        }
        
        if (permission === 'read_only' || this.options.mode === 'view') {
            inputEl.disabled = true;
            inputEl.readOnly = true;
        }
        
        this.fieldElements[field.name] = inputEl;
        formGroupEl.appendChild(inputEl);
        
        if (field.helpText) {
            const helpEl = document.createElement('small');
            helpEl.className = 'form-help-text';
            helpEl.textContent = field.helpText;
            formGroupEl.appendChild(helpEl);
        }
        
        const errorEl = document.createElement('div');
        errorEl.className = 'form-field-error';
        errorEl.style.display = 'none';
        formGroupEl.appendChild(errorEl);
        
        if (field.conditional) {
            this.setupConditionalLogic(field, formGroupEl);
        }
        
        return formGroupEl;
    }
    
    renderTextInput(field, validation) {
        const input = document.createElement('input');
        input.type = field.type || 'text';
        input.name = field.name;
        input.className = 'form-input';
        input.value = this.formData[field.name] || field.defaultValue || '';
        
        if (validation.required || field.required) input.required = true;
        if (validation.minLength) input.minLength = validation.minLength;
        if (validation.maxLength) input.maxLength = validation.maxLength;
        if (validation.pattern) input.pattern = validation.pattern;
        if (field.placeholder) input.placeholder = field.placeholder;
        
        input.addEventListener('input', (e) => this.handleFieldChange(field.name, e.target.value));
        input.addEventListener('blur', (e) => this.validateField(field.name, e.target.value, validation));
        
        return input;
    }
    
    renderNumberInput(field, validation) {
        const input = document.createElement('input');
        input.type = 'number';
        input.name = field.name;
        input.className = 'form-input';
        input.value = this.formData[field.name] || field.defaultValue || '';
        
        if (validation.required || field.required) input.required = true;
        if (validation.min !== undefined) input.min = validation.min;
        if (validation.max !== undefined) input.max = validation.max;
        if (validation.step) input.step = validation.step;
        if (field.placeholder) input.placeholder = field.placeholder;
        
        input.addEventListener('input', (e) => this.handleFieldChange(field.name, e.target.value));
        input.addEventListener('blur', (e) => this.validateField(field.name, e.target.value, validation));
        
        return input;
    }
    
    renderTextarea(field, validation) {
        const textarea = document.createElement('textarea');
        textarea.name = field.name;
        textarea.className = 'form-textarea';
        textarea.value = this.formData[field.name] || field.defaultValue || '';
        textarea.rows = field.rows || 4;
        
        if (validation.required || field.required) textarea.required = true;
        if (validation.minLength) textarea.minLength = validation.minLength;
        if (validation.maxLength) textarea.maxLength = validation.maxLength;
        if (field.placeholder) textarea.placeholder = field.placeholder;
        
        textarea.addEventListener('input', (e) => this.handleFieldChange(field.name, e.target.value));
        textarea.addEventListener('blur', (e) => this.validateField(field.name, e.target.value, validation));
        
        return textarea;
    }
    
    renderSelect(field, validation) {
        const select = document.createElement('select');
        select.name = field.name;
        select.className = 'form-select';
        
        if (validation.required || field.required) select.required = true;
        
        if (field.placeholder) {
            const placeholderOption = document.createElement('option');
            placeholderOption.value = '';
            placeholderOption.textContent = field.placeholder;
            placeholderOption.disabled = true;
            placeholderOption.selected = !this.formData[field.name];
            select.appendChild(placeholderOption);
        }
        
        const options = field.options || [];
        options.forEach(opt => {
            const option = document.createElement('option');
            option.value = opt.value || opt;
            option.textContent = opt.label || opt;
            option.selected = this.formData[field.name] === option.value;
            select.appendChild(option);
        });
        
        select.addEventListener('change', (e) => this.handleFieldChange(field.name, e.target.value));
        
        return select;
    }
    
    renderDateInput(field, validation) {
        const input = document.createElement('input');
        input.type = field.type;
        input.name = field.name;
        input.className = 'form-input';
        input.value = this.formData[field.name] || field.defaultValue || '';
        
        if (validation.required || field.required) input.required = true;
        if (validation.min) input.min = validation.min;
        if (validation.max) input.max = validation.max;
        
        input.addEventListener('change', (e) => this.handleFieldChange(field.name, e.target.value));
        
        return input;
    }
    
    renderCheckbox(field, validation) {
        const label = document.createElement('label');
        label.className = 'form-checkbox-label';
        
        const input = document.createElement('input');
        input.type = 'checkbox';
        input.name = field.name;
        input.checked = this.formData[field.name] || field.defaultValue || false;
        
        if (validation.required || field.required) input.required = true;
        
        input.addEventListener('change', (e) => this.handleFieldChange(field.name, e.target.checked));
        
        label.appendChild(input);
        label.appendChild(document.createTextNode(field.checkboxLabel || ''));
        
        return label;
    }
    
    renderRadioGroup(field, validation) {
        const container = document.createElement('div');
        container.className = 'form-radio-group';
        
        const options = field.options || [];
        options.forEach((opt, index) => {
            const label = document.createElement('label');
            label.className = 'form-radio-label';
            
            const input = document.createElement('input');
            input.type = 'radio';
            input.name = field.name;
            input.value = opt.value || opt;
            input.checked = this.formData[field.name] === input.value;
            
            if (validation.required || field.required) input.required = true;
            
            input.addEventListener('change', (e) => this.handleFieldChange(field.name, e.target.value));
            
            label.appendChild(input);
            label.appendChild(document.createTextNode(opt.label || opt));
            container.appendChild(label);
        });
        
        return container;
    }
    
    renderLookup(field, validation) {
        const input = document.createElement('input');
        input.type = 'text';
        input.name = field.name;
        input.className = 'form-input form-lookup';
        input.value = this.formData[field.name] || '';
        input.autocomplete = 'off';
        
        if (validation.required || field.required) input.required = true;
        if (field.placeholder) input.placeholder = field.placeholder;
        
        const resultsEl = document.createElement('div');
        resultsEl.className = 'lookup-results';
        resultsEl.style.display = 'none';
        
        input.addEventListener('input', debounce(async (e) => {
            const value = e.target.value;
            if (value.length < 2) {
                resultsEl.style.display = 'none';
                return;
            }
            
            const results = await this.fetchLookupResults(field.lookupSource, value);
            this.renderLookupResults(resultsEl, results, field, input);
        }, 300));
        
        const wrapper = document.createElement('div');
        wrapper.className = 'form-lookup-wrapper';
        wrapper.appendChild(input);
        wrapper.appendChild(resultsEl);
        
        return wrapper;
    }
    
    renderFileInput(field, validation) {
        const input = document.createElement('input');
        input.type = 'file';
        input.name = field.name;
        input.className = 'form-input';
        
        if (validation.required || field.required) input.required = true;
        if (field.accept) input.accept = field.accept;
        if (field.multiple) input.multiple = true;
        
        input.addEventListener('change', (e) => this.handleFieldChange(field.name, e.target.files));
        
        return input;
    }
    
    renderActions() {
        const actionsEl = document.createElement('div');
        actionsEl.className = 'form-actions modal-footer';
        
        if (this.options.mode !== 'view') {
            const submitBtn = document.createElement('button');
            submitBtn.type = 'submit';
            submitBtn.className = 'btn btn-primary';
            submitBtn.textContent = this.options.submitLabel || 'Submit';
            actionsEl.appendChild(submitBtn);
        }
        
        if (this.options.onCancel) {
            const cancelBtn = document.createElement('button');
            cancelBtn.type = 'button';
            cancelBtn.className = 'btn btn-secondary';
            cancelBtn.textContent = 'Cancel';
            cancelBtn.addEventListener('click', () => this.options.onCancel());
            actionsEl.appendChild(cancelBtn);
        }
        
        return actionsEl;
    }
    
    setupConditionalLogic(field, formGroupEl) {
        const condition = field.conditional;
        
        const evaluateCondition = () => {
            const dependentValue = this.formData[condition.field];
            let shouldShow = false;
            
            switch (condition.operator) {
                case '==':
                case 'equals':
                    shouldShow = dependentValue == condition.value;
                    break;
                case '!=':
                case 'not_equals':
                    shouldShow = dependentValue != condition.value;
                    break;
                case 'contains':
                    shouldShow = String(dependentValue).includes(condition.value);
                    break;
                case 'in':
                    shouldShow = condition.value.includes(dependentValue);
                    break;
                default:
                    shouldShow = !!dependentValue;
            }
            
            formGroupEl.style.display = shouldShow ? '' : 'none';
            this.conditionalStates[field.name] = shouldShow;
        };
        
        this.conditionalStates[field.name] = evaluateCondition;
        evaluateCondition();
    }
    
    evaluateAllConditionalLogic() {
        Object.values(this.conditionalStates).forEach(evaluate => {
            if (typeof evaluate === 'function') {
                evaluate();
            }
        });
    }
    
    handleFieldChange(fieldName, value) {
        this.formData[fieldName] = value;
        this.evaluateAllConditionalLogic();
        
        if (this.validationErrors[fieldName]) {
            delete this.validationErrors[fieldName];
            this.clearFieldError(fieldName);
        }
    }
    
    validateField(fieldName, value, validation) {
        const errors = [];
        
        if (validation.required && !value) {
            errors.push('This field is required');
        }
        
        if (value) {
            if (validation.minLength && value.length < validation.minLength) {
                errors.push(`Minimum length is ${validation.minLength} characters`);
            }
            if (validation.maxLength && value.length > validation.maxLength) {
                errors.push(`Maximum length is ${validation.maxLength} characters`);
            }
            if (validation.min !== undefined && parseFloat(value) < validation.min) {
                errors.push(`Minimum value is ${validation.min}`);
            }
            if (validation.max !== undefined && parseFloat(value) > validation.max) {
                errors.push(`Maximum value is ${validation.max}`);
            }
            if (validation.pattern && !new RegExp(validation.pattern).test(value)) {
                errors.push(validation.patternMessage || 'Invalid format');
            }
            if (validation.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
                errors.push('Invalid email address');
            }
            if (validation.custom && typeof validation.custom === 'function') {
                const customError = validation.custom(value, this.formData);
                if (customError) errors.push(customError);
            }
        }
        
        if (errors.length > 0) {
            this.validationErrors[fieldName] = errors;
            this.showFieldError(fieldName, errors[0]);
            return false;
        } else {
            delete this.validationErrors[fieldName];
            this.clearFieldError(fieldName);
            return true;
        }
    }
    
    showFieldError(fieldName, message) {
        const formGroup = this.container.querySelector(`[data-field-name="${fieldName}"]`);
        if (formGroup) {
            const errorEl = formGroup.querySelector('.form-field-error');
            if (errorEl) {
                errorEl.textContent = message;
                errorEl.style.display = 'block';
            }
            
            const inputEl = this.fieldElements[fieldName];
            if (inputEl) {
                inputEl.classList.add('error');
            }
        }
    }
    
    clearFieldError(fieldName) {
        const formGroup = this.container.querySelector(`[data-field-name="${fieldName}"]`);
        if (formGroup) {
            const errorEl = formGroup.querySelector('.form-field-error');
            if (errorEl) {
                errorEl.style.display = 'none';
            }
            
            const inputEl = this.fieldElements[fieldName];
            if (inputEl) {
                inputEl.classList.remove('error');
            }
        }
    }
    
    async handleSubmit(e) {
        e.preventDefault();
        
        this.validationErrors = {};
        let isValid = true;
        
        const formDef = typeof this.config.form_definition === 'string' 
            ? JSON.parse(this.config.form_definition) 
            : this.config.form_definition;
            
        const validationRules = this.config.validation_rules 
            ? (typeof this.config.validation_rules === 'string' 
                ? JSON.parse(this.config.validation_rules) 
                : this.config.validation_rules)
            : {};
        
        const allFields = formDef.sections 
            ? formDef.sections.flatMap(s => s.fields)
            : formDef.fields;
        
        allFields.forEach(field => {
            if (this.conditionalStates[field.name] === false) return;
            
            const value = this.formData[field.name];
            const validation = validationRules[field.name] || {};
            
            if (!this.validateField(field.name, value, validation)) {
                isValid = false;
            }
        });
        
        if (!isValid) {
            showAlert('Please fix validation errors', 'danger');
            return;
        }
        
        if (this.options.onSubmit) {
            await this.options.onSubmit(this.formData);
        }
    }
    
    async loadFieldPermissions() {
        const user = getCurrentUser();
        if (!user || !user.role_id) return {};
        
        try {
            const response = await API.fieldPermissions.getByRole(user.role_id);
            if (response.success) {
                const permissions = {};
                response.data.forEach(perm => {
                    if (perm.entity_type === this.config.module) {
                        permissions[perm.field_name] = perm.permission_type;
                    }
                });
                return permissions;
            }
        } catch (error) {
            console.error('Failed to load field permissions:', error);
        }
        
        return {};
    }
    
    getFieldPermission(fieldName) {
        return this.fieldPermissions[fieldName] || 'editable';
    }
    
    async fetchLookupResults(source, term) {
        if (!source) return [];
        
        try {
            if (source.type === 'api') {
                const response = await apiRequest(source.endpoint + `?term=${encodeURIComponent(term)}`);
                return response.data || [];
            } else if (source.type === 'static') {
                return source.data.filter(item => 
                    String(item.label).toLowerCase().includes(term.toLowerCase())
                );
            }
        } catch (error) {
            console.error('Lookup fetch error:', error);
        }
        
        return [];
    }
    
    renderLookupResults(resultsEl, results, field, inputEl) {
        resultsEl.innerHTML = '';
        
        if (results.length === 0) {
            resultsEl.style.display = 'none';
            return;
        }
        
        results.forEach(result => {
            const itemEl = document.createElement('div');
            itemEl.className = 'lookup-result-item';
            itemEl.textContent = result.label || result.name || result;
            itemEl.addEventListener('click', () => {
                inputEl.value = result.label || result.name || result;
                this.handleFieldChange(field.name, result.value || result.id || result);
                resultsEl.style.display = 'none';
            });
            resultsEl.appendChild(itemEl);
        });
        
        resultsEl.style.display = 'block';
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
