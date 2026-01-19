from flask import Blueprint, request
from backend.config.database import execute_query
from backend.utils.auth import token_required, permission_required
from backend.utils.response import success_response, error_response
from backend.utils.audit import log_audit
import json

workflows_bp = Blueprint('workflows', __name__, url_prefix='/api/workflows')

@workflows_bp.route('', methods=['GET'])
@token_required
def get_workflows():
    module = request.args.get('module')
    is_active = request.args.get('is_active', 'true')
    
    query = "SELECT * FROM workflows WHERE 1=1"
    params = []
    
    if module:
        query += " AND module = %s"
        params.append(module)
    
    if is_active.lower() == 'true':
        query += " AND is_active = TRUE"
    
    query += " ORDER BY workflow_name"
    
    workflows = execute_query(query, tuple(params) if params else None, fetch_all=True)
    return success_response(workflows)

@workflows_bp.route('/<int:id>', methods=['GET'])
@token_required
def get_workflow(id):
    workflow = execute_query("SELECT * FROM workflows WHERE id = %s", (id,), fetch_one=True)
    
    if not workflow:
        return error_response('Workflow not found', 404)
    
    return success_response(workflow)

@workflows_bp.route('/by-code/<workflow_code>', methods=['GET'])
@token_required
def get_workflow_by_code(workflow_code):
    workflow = execute_query(
        "SELECT * FROM workflows WHERE workflow_code = %s AND is_active = TRUE",
        (workflow_code,),
        fetch_one=True
    )
    
    if not workflow:
        return error_response('Workflow not found', 404)
    
    return success_response(workflow)

@workflows_bp.route('', methods=['POST'])
@token_required
@permission_required('admin', 'write')
def create_workflow():
    data = request.get_json()
    user_id = request.current_user['user_id']
    
    required_fields = ['workflow_name', 'workflow_code', 'module', 'workflow_steps']
    for field in required_fields:
        if not data.get(field):
            return error_response(f'{field} is required', 400)
    
    query = """
        INSERT INTO workflows
        (workflow_name, workflow_code, module, description, workflow_steps,
         approval_rules, escalation_rules, created_by_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    try:
        workflow_id = execute_query(
            query,
            (
                data['workflow_name'],
                data['workflow_code'],
                data['module'],
                data.get('description'),
                json.dumps(data['workflow_steps']),
                json.dumps(data.get('approval_rules', {})),
                json.dumps(data.get('escalation_rules', {})),
                user_id
            ),
            commit=True
        )
        
        log_audit(user_id, 'CREATE', 'workflow', workflow_id, None, data)
        
        return success_response({'id': workflow_id}, 'Workflow created successfully', 201)
    except Exception as e:
        return error_response(str(e), 500)

@workflows_bp.route('/<int:id>', methods=['PUT'])
@token_required
@permission_required('admin', 'write')
def update_workflow(id):
    data = request.get_json()
    user_id = request.current_user['user_id']
    
    old_data = execute_query("SELECT * FROM workflows WHERE id = %s", (id,), fetch_one=True)
    if not old_data:
        return error_response('Workflow not found', 404)
    
    query = """
        UPDATE workflows SET
            workflow_name = %s, module = %s, description = %s,
            workflow_steps = %s, approval_rules = %s,
            escalation_rules = %s, version = version + 1
        WHERE id = %s
    """
    
    try:
        execute_query(
            query,
            (
                data.get('workflow_name', old_data['workflow_name']),
                data.get('module', old_data['module']),
                data.get('description', old_data['description']),
                json.dumps(data.get('workflow_steps', old_data['workflow_steps'])),
                json.dumps(data.get('approval_rules', old_data['approval_rules'])),
                json.dumps(data.get('escalation_rules', old_data['escalation_rules'])),
                id
            ),
            commit=True
        )
        
        log_audit(user_id, 'UPDATE', 'workflow', id, old_data, data)
        
        return success_response(message='Workflow updated successfully')
    except Exception as e:
        return error_response(str(e), 500)

@workflows_bp.route('/<int:id>/activate', methods=['POST'])
@token_required
@permission_required('admin', 'write')
def activate_workflow(id):
    user_id = request.current_user['user_id']
    
    execute_query("UPDATE workflows SET is_active = TRUE WHERE id = %s", (id,), commit=True)
    log_audit(user_id, 'ACTIVATE', 'workflow', id)
    
    return success_response(message='Workflow activated successfully')

@workflows_bp.route('/<int:id>/deactivate', methods=['POST'])
@token_required
@permission_required('admin', 'write')
def deactivate_workflow(id):
    user_id = request.current_user['user_id']
    
    execute_query("UPDATE workflows SET is_active = FALSE WHERE id = %s", (id,), commit=True)
    log_audit(user_id, 'DEACTIVATE', 'workflow', id)
    
    return success_response(message='Workflow deactivated successfully')

@workflows_bp.route('/instances', methods=['GET'])
@token_required
def get_workflow_instances():
    entity_type = request.args.get('entity_type')
    entity_id = request.args.get('entity_id')
    status = request.args.get('status')
    
    query = """
        SELECT wt.*, w.workflow_name, w.workflow_code,
               CONCAT(u.first_name, ' ', u.last_name) as assigned_to_name
        FROM workflow_instance_tracking wt
        LEFT JOIN workflows w ON wt.workflow_id = w.id
        LEFT JOIN users u ON wt.assigned_to_id = u.id
        WHERE 1=1
    """
    params = []
    
    if entity_type:
        query += " AND wt.entity_type = %s"
        params.append(entity_type)
    
    if entity_id:
        query += " AND wt.entity_id = %s"
        params.append(entity_id)
    
    if status:
        query += " AND wt.status = %s"
        params.append(status)
    
    query += " ORDER BY wt.started_at DESC"
    
    instances = execute_query(query, tuple(params) if params else None, fetch_all=True)
    return success_response(instances)

@workflows_bp.route('/instances/<int:id>', methods=['GET'])
@token_required
def get_workflow_instance(id):
    query = """
        SELECT wt.*, w.workflow_name, w.workflow_code, w.workflow_steps,
               CONCAT(u.first_name, ' ', u.last_name) as assigned_to_name
        FROM workflow_instance_tracking wt
        LEFT JOIN workflows w ON wt.workflow_id = w.id
        LEFT JOIN users u ON wt.assigned_to_id = u.id
        WHERE wt.id = %s
    """
    instance = execute_query(query, (id,), fetch_one=True)
    
    if not instance:
        return error_response('Workflow instance not found', 404)
    
    return success_response(instance)

@workflows_bp.route('/instances/<int:id>/advance', methods=['POST'])
@token_required
def advance_workflow(id):
    data = request.get_json()
    user_id = request.current_user['user_id']
    
    instance = execute_query(
        "SELECT * FROM workflow_instance_tracking WHERE id = %s",
        (id,),
        fetch_one=True
    )
    
    if not instance:
        return error_response('Workflow instance not found', 404)
    
    new_step = instance['current_step'] + 1
    workflow_state = json.loads(instance['workflow_state']) if instance['workflow_state'] else {}
    workflow_state[f'step_{instance["current_step"]}_completed_by'] = user_id
    workflow_state[f'step_{instance["current_step"]}_completed_at'] = str(datetime.now())
    workflow_state.update(data.get('state_updates', {}))
    
    query = """
        UPDATE workflow_instance_tracking
        SET current_step = %s, workflow_state = %s,
            assigned_to_id = %s, status = %s
        WHERE id = %s
    """
    
    execute_query(
        query,
        (
            new_step,
            json.dumps(workflow_state),
            data.get('assigned_to_id'),
            data.get('status', 'in_progress'),
            id
        ),
        commit=True
    )
    
    log_audit(user_id, 'ADVANCE_WORKFLOW', 'workflow_instance', id)
    
    return success_response(message='Workflow advanced successfully')
