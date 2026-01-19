from flask import Blueprint, request
from backend.config.database import execute_query
from backend.utils.auth import token_required, permission_required
from backend.utils.response import success_response, error_response
from backend.utils.audit import log_audit

departments_bp = Blueprint('departments', __name__, url_prefix='/api/departments')

@departments_bp.route('', methods=['GET'])
@token_required
def get_departments():
    query = """
        SELECT d.*, 
               CONCAT(u.first_name, ' ', u.last_name) as manager_name
        FROM departments d
        LEFT JOIN users u ON d.manager_id = u.id
        WHERE d.is_active = TRUE
        ORDER BY d.name
    """
    departments = execute_query(query, fetch_all=True)
    return success_response(departments)

@departments_bp.route('/<int:id>', methods=['GET'])
@token_required
def get_department(id):
    query = """
        SELECT d.*, 
               CONCAT(u.first_name, ' ', u.last_name) as manager_name
        FROM departments d
        LEFT JOIN users u ON d.manager_id = u.id
        WHERE d.id = %s
    """
    department = execute_query(query, (id,), fetch_one=True)
    
    if not department:
        return error_response('Department not found', 404)
    
    stages_query = """
        SELECT * FROM production_stages 
        WHERE department_id = %s AND is_active = TRUE
        ORDER BY stage_order
    """
    stages = execute_query(stages_query, (id,), fetch_all=True)
    department['stages'] = stages
    
    return success_response(department)

@departments_bp.route('', methods=['POST'])
@token_required
@permission_required('admin', 'write')
def create_department():
    data = request.get_json()
    user_id = request.current_user['user_id']
    
    required_fields = ['code', 'name', 'department_type']
    for field in required_fields:
        if not data.get(field):
            return error_response(f'{field} is required', 400)
    
    query = """
        INSERT INTO departments 
        (code, name, description, manager_id, department_type, 
         daily_target, weekly_target, monthly_target, config)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    try:
        dept_id = execute_query(
            query,
            (
                data['code'],
                data['name'],
                data.get('description'),
                data.get('manager_id'),
                data['department_type'],
                data.get('daily_target'),
                data.get('weekly_target'),
                data.get('monthly_target'),
                data.get('config')
            ),
            commit=True
        )
        
        log_audit(user_id, 'CREATE', 'department', dept_id, None, data)
        
        return success_response({'id': dept_id}, 'Department created successfully', 201)
    except Exception as e:
        return error_response(str(e), 500)

@departments_bp.route('/<int:id>', methods=['PUT'])
@token_required
@permission_required('admin', 'write')
def update_department(id):
    data = request.get_json()
    user_id = request.current_user['user_id']
    
    old_data = execute_query("SELECT * FROM departments WHERE id = %s", (id,), fetch_one=True)
    if not old_data:
        return error_response('Department not found', 404)
    
    query = """
        UPDATE departments SET
            code = %s, name = %s, description = %s, manager_id = %s,
            department_type = %s, daily_target = %s, weekly_target = %s,
            monthly_target = %s, config = %s
        WHERE id = %s
    """
    
    try:
        execute_query(
            query,
            (
                data.get('code', old_data['code']),
                data.get('name', old_data['name']),
                data.get('description', old_data['description']),
                data.get('manager_id', old_data['manager_id']),
                data.get('department_type', old_data['department_type']),
                data.get('daily_target', old_data['daily_target']),
                data.get('weekly_target', old_data['weekly_target']),
                data.get('monthly_target', old_data['monthly_target']),
                data.get('config', old_data['config']),
                id
            ),
            commit=True
        )
        
        log_audit(user_id, 'UPDATE', 'department', id, old_data, data)
        
        return success_response(message='Department updated successfully')
    except Exception as e:
        return error_response(str(e), 500)

@departments_bp.route('/<int:id>', methods=['DELETE'])
@token_required
@permission_required('admin', 'delete')
def delete_department(id):
    user_id = request.current_user['user_id']
    
    execute_query("UPDATE departments SET is_active = FALSE WHERE id = %s", (id,), commit=True)
    log_audit(user_id, 'DELETE', 'department', id)
    
    return success_response(message='Department deleted successfully')

@departments_bp.route('/<int:id>/stages', methods=['POST'])
@token_required
@permission_required('admin', 'write')
def add_production_stage(id):
    data = request.get_json()
    user_id = request.current_user['user_id']
    
    query = """
        INSERT INTO production_stages
        (department_id, stage_name, stage_order, description, estimated_duration_minutes, config)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    
    try:
        stage_id = execute_query(
            query,
            (
                id,
                data['stage_name'],
                data['stage_order'],
                data.get('description'),
                data.get('estimated_duration_minutes'),
                data.get('config')
            ),
            commit=True
        )
        
        log_audit(user_id, 'CREATE', 'production_stage', stage_id, None, data)
        
        return success_response({'id': stage_id}, 'Production stage added successfully', 201)
    except Exception as e:
        return error_response(str(e), 500)
