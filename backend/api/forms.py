from flask import Blueprint, request
from backend.config.database import execute_query
from backend.utils.auth import token_required, permission_required
from backend.utils.response import success_response, error_response
from backend.utils.audit import log_audit
import json

forms_bp = Blueprint('forms', __name__, url_prefix='/api/forms')

@forms_bp.route('', methods=['GET'])
@token_required
def get_forms():
    module = request.args.get('module')
    is_active = request.args.get('is_active', 'true')
    
    query = "SELECT * FROM dynamic_forms WHERE 1=1"
    params = []
    
    if module:
        query += " AND module = %s"
        params.append(module)
    
    if is_active.lower() == 'true':
        query += " AND is_active = TRUE"
    
    query += " ORDER BY form_name"
    
    forms = execute_query(query, tuple(params) if params else None, fetch_all=True)
    return success_response(forms)

@forms_bp.route('/<int:id>', methods=['GET'])
@token_required
def get_form(id):
    form = execute_query("SELECT * FROM dynamic_forms WHERE id = %s", (id,), fetch_one=True)
    
    if not form:
        return error_response('Form not found', 404)
    
    return success_response(form)

@forms_bp.route('/by-code/<form_code>', methods=['GET'])
@token_required
def get_form_by_code(form_code):
    form = execute_query(
        "SELECT * FROM dynamic_forms WHERE form_code = %s AND is_active = TRUE",
        (form_code,),
        fetch_one=True
    )
    
    if not form:
        return error_response('Form not found', 404)
    
    return success_response(form)

@forms_bp.route('', methods=['POST'])
@token_required
@permission_required('admin', 'write')
def create_form():
    data = request.get_json()
    user_id = request.current_user['user_id']
    
    required_fields = ['form_name', 'form_code', 'module', 'form_definition']
    for field in required_fields:
        if not data.get(field):
            return error_response(f'{field} is required', 400)
    
    query = """
        INSERT INTO dynamic_forms
        (form_name, form_code, module, description, form_definition,
         validation_rules, workflow_config, sla_config, created_by_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    try:
        form_id = execute_query(
            query,
            (
                data['form_name'],
                data['form_code'],
                data['module'],
                data.get('description'),
                json.dumps(data['form_definition']),
                json.dumps(data.get('validation_rules', {})),
                json.dumps(data.get('workflow_config', {})),
                json.dumps(data.get('sla_config', {})),
                user_id
            ),
            commit=True
        )
        
        log_audit(user_id, 'CREATE', 'dynamic_form', form_id, None, data)
        
        return success_response({'id': form_id}, 'Form created successfully', 201)
    except Exception as e:
        return error_response(str(e), 500)

@forms_bp.route('/<int:id>', methods=['PUT'])
@token_required
@permission_required('admin', 'write')
def update_form(id):
    data = request.get_json()
    user_id = request.current_user['user_id']
    
    old_data = execute_query("SELECT * FROM dynamic_forms WHERE id = %s", (id,), fetch_one=True)
    if not old_data:
        return error_response('Form not found', 404)
    
    query = """
        UPDATE dynamic_forms SET
            form_name = %s, module = %s, description = %s,
            form_definition = %s, validation_rules = %s,
            workflow_config = %s, sla_config = %s, version = version + 1
        WHERE id = %s
    """
    
    try:
        execute_query(
            query,
            (
                data.get('form_name', old_data['form_name']),
                data.get('module', old_data['module']),
                data.get('description', old_data['description']),
                json.dumps(data.get('form_definition', old_data['form_definition'])),
                json.dumps(data.get('validation_rules', old_data['validation_rules'])),
                json.dumps(data.get('workflow_config', old_data['workflow_config'])),
                json.dumps(data.get('sla_config', old_data['sla_config'])),
                id
            ),
            commit=True
        )
        
        log_audit(user_id, 'UPDATE', 'dynamic_form', id, old_data, data)
        
        return success_response(message='Form updated successfully')
    except Exception as e:
        return error_response(str(e), 500)

@forms_bp.route('/submissions', methods=['POST'])
@token_required
def submit_form():
    data = request.get_json()
    user_id = request.current_user['user_id']
    
    form_id = data.get('form_id')
    submission_data = data.get('submission_data')
    
    if not form_id or not submission_data:
        return error_response('form_id and submission_data are required', 400)
    
    form = execute_query("SELECT * FROM dynamic_forms WHERE id = %s", (form_id,), fetch_one=True)
    if not form:
        return error_response('Form not found', 404)
    
    reference_number = f"{form['form_code']}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    query = """
        INSERT INTO form_submissions
        (form_id, reference_number, submission_data, submitted_by_id, department_id, workflow_state)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    
    try:
        submission_id = execute_query(
            query,
            (
                form_id,
                reference_number,
                json.dumps(submission_data),
                user_id,
                data.get('department_id'),
                json.dumps(data.get('workflow_state', {}))
            ),
            commit=True
        )
        
        log_audit(user_id, 'SUBMIT_FORM', 'form_submission', submission_id, None, data)
        
        return success_response(
            {'id': submission_id, 'reference_number': reference_number},
            'Form submitted successfully',
            201
        )
    except Exception as e:
        return error_response(str(e), 500)

@forms_bp.route('/submissions/<int:id>', methods=['GET'])
@token_required
def get_submission(id):
    query = """
        SELECT fs.*, df.form_name, df.form_code,
               CONCAT(u.first_name, ' ', u.last_name) as submitted_by_name
        FROM form_submissions fs
        LEFT JOIN dynamic_forms df ON fs.form_id = df.id
        LEFT JOIN users u ON fs.submitted_by_id = u.id
        WHERE fs.id = %s
    """
    submission = execute_query(query, (id,), fetch_one=True)
    
    if not submission:
        return error_response('Submission not found', 404)
    
    return success_response(submission)
