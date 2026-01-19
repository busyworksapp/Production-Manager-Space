from flask import Blueprint, request
from backend.config.database import execute_query
from backend.utils.auth import token_required, permission_required
from backend.utils.response import success_response, error_response
from backend.utils.audit import log_audit

field_permissions_bp = Blueprint('field_permissions', __name__, url_prefix='/api/field-permissions')

@field_permissions_bp.route('', methods=['GET'])
@token_required
def get_field_permissions():
    role_id = request.args.get('role_id')
    entity_type = request.args.get('entity_type')
    
    query = """
        SELECT fp.*, r.name as role_name
        FROM field_permissions fp
        LEFT JOIN roles r ON fp.role_id = r.id
        WHERE 1=1
    """
    params = []
    
    if role_id:
        query += " AND fp.role_id = %s"
        params.append(role_id)
    
    if entity_type:
        query += " AND fp.entity_type = %s"
        params.append(entity_type)
    
    query += " ORDER BY r.name, fp.entity_type, fp.field_name"
    
    permissions = execute_query(query, tuple(params) if params else None, fetch_all=True)
    return success_response(permissions)

@field_permissions_bp.route('/<int:id>', methods=['GET'])
@token_required
def get_field_permission(id):
    query = """
        SELECT fp.*, r.name as role_name
        FROM field_permissions fp
        LEFT JOIN roles r ON fp.role_id = r.id
        WHERE fp.id = %s
    """
    permission = execute_query(query, (id,), fetch_one=True)
    
    if not permission:
        return error_response('Field permission not found', 404)
    
    return success_response(permission)

@field_permissions_bp.route('', methods=['POST'])
@token_required
@permission_required('admin', 'write')
def create_field_permission():
    data = request.get_json()
    user_id = request.current_user['user_id']
    
    required_fields = ['role_id', 'entity_type', 'field_name', 'permission_type']
    for field in required_fields:
        if not data.get(field):
            return error_response(f'{field} is required', 400)
    
    existing = execute_query(
        "SELECT id FROM field_permissions WHERE role_id = %s AND entity_type = %s AND field_name = %s",
        (data['role_id'], data['entity_type'], data['field_name']),
        fetch_one=True
    )
    
    if existing:
        return error_response('Field permission already exists for this role and field', 400)
    
    query = """
        INSERT INTO field_permissions
        (role_id, entity_type, field_name, permission_type, conditional_rules, created_by_id)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    
    try:
        permission_id = execute_query(
            query,
            (
                data['role_id'],
                data['entity_type'],
                data['field_name'],
                data['permission_type'],
                data.get('conditional_rules'),
                user_id
            ),
            commit=True
        )
        
        log_audit(user_id, 'CREATE', 'field_permission', permission_id, None, data)
        
        return success_response({'id': permission_id}, 'Field permission created successfully', 201)
    except Exception as e:
        return error_response(str(e), 500)

@field_permissions_bp.route('/<int:id>', methods=['PUT'])
@token_required
@permission_required('admin', 'write')
def update_field_permission(id):
    data = request.get_json()
    user_id = request.current_user['user_id']
    
    old_data = execute_query("SELECT * FROM field_permissions WHERE id = %s", (id,), fetch_one=True)
    if not old_data:
        return error_response('Field permission not found', 404)
    
    query = """
        UPDATE field_permissions SET
            permission_type = %s,
            conditional_rules = %s
        WHERE id = %s
    """
    
    try:
        execute_query(
            query,
            (
                data.get('permission_type', old_data['permission_type']),
                data.get('conditional_rules', old_data['conditional_rules']),
                id
            ),
            commit=True
        )
        
        log_audit(user_id, 'UPDATE', 'field_permission', id, old_data, data)
        
        return success_response(message='Field permission updated successfully')
    except Exception as e:
        return error_response(str(e), 500)

@field_permissions_bp.route('/<int:id>', methods=['DELETE'])
@token_required
@permission_required('admin', 'write')
def delete_field_permission(id):
    user_id = request.current_user['user_id']
    
    old_data = execute_query("SELECT * FROM field_permissions WHERE id = %s", (id,), fetch_one=True)
    if not old_data:
        return error_response('Field permission not found', 404)
    
    try:
        execute_query("DELETE FROM field_permissions WHERE id = %s", (id,), commit=True)
        log_audit(user_id, 'DELETE', 'field_permission', id, old_data, None)
        
        return success_response(message='Field permission deleted successfully')
    except Exception as e:
        return error_response(str(e), 500)

@field_permissions_bp.route('/by-role/<int:role_id>', methods=['GET'])
@token_required
def get_permissions_by_role(role_id):
    query = """
        SELECT entity_type, field_name, permission_type, conditional_rules
        FROM field_permissions
        WHERE role_id = %s
        ORDER BY entity_type, field_name
    """
    
    permissions = execute_query(query, (role_id,), fetch_all=True)
    
    grouped = {}
    for perm in permissions:
        entity = perm['entity_type']
        if entity not in grouped:
            grouped[entity] = []
        grouped[entity].append({
            'field_name': perm['field_name'],
            'permission_type': perm['permission_type'],
            'conditional_rules': perm['conditional_rules']
        })
    
    return success_response(grouped)
