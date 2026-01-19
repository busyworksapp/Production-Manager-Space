from flask import Blueprint, request
from backend.config.database import execute_query
from backend.utils.auth import token_required, permission_required, hash_password
from backend.utils.response import success_response, error_response
from backend.utils.audit import log_audit

employees_bp = Blueprint('employees', __name__, url_prefix='/api/employees')

@employees_bp.route('', methods=['GET'])
@token_required
def get_employees():
    department_id = request.args.get('department_id')
    employee_type = request.args.get('employee_type')
    
    query = """
        SELECT e.*, d.name as department_name
        FROM employees e
        LEFT JOIN departments d ON e.department_id = d.id
        WHERE e.is_active = TRUE
    """
    
    params = []
    if department_id:
        query += " AND e.department_id = %s"
        params.append(department_id)
    
    if employee_type:
        query += " AND e.employee_type = %s"
        params.append(employee_type)
    
    query += " ORDER BY e.first_name, e.last_name"
    
    employees = execute_query(query, tuple(params) if params else None, fetch_all=True)
    return success_response(employees)

@employees_bp.route('/<int:id>', methods=['GET'])
@token_required
def get_employee(id):
    query = """
        SELECT e.*, d.name as department_name, u.username
        FROM employees e
        LEFT JOIN departments d ON e.department_id = d.id
        LEFT JOIN users u ON e.user_id = u.id
        WHERE e.id = %s
    """
    employee = execute_query(query, (id,), fetch_one=True)
    
    if not employee:
        return error_response('Employee not found', 404)
    
    return success_response(employee)

@employees_bp.route('', methods=['POST'])
@token_required
@permission_required('admin', 'write')
def create_employee():
    data = request.get_json()
    user_id = request.current_user['user_id']
    
    required_fields = ['employee_number', 'first_name', 'last_name', 'employee_type']
    for field in required_fields:
        if not data.get(field):
            return error_response(f'{field} is required', 400)
    
    create_user_account = data.get('create_user_account', False)
    user_account_id = None
    
    if create_user_account:
        username = f"{data['first_name'].lower()}@barron"
        password = data['employee_number']
        
        user_query = """
            INSERT INTO users (username, password_hash, email, first_name, last_name, role_id)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        try:
            user_account_id = execute_query(
                user_query,
                (username, hash_password(password), data.get('email'), 
                 data['first_name'], data['last_name'], data.get('role_id', 4)),
                commit=True
            )
        except Exception as e:
            return error_response(f'Failed to create user account: {str(e)}', 500)
    
    query = """
        INSERT INTO employees
        (employee_number, first_name, last_name, email, phone,
         department_id, position, employee_type, user_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    try:
        emp_id = execute_query(
            query,
            (
                data['employee_number'],
                data['first_name'],
                data['last_name'],
                data.get('email'),
                data.get('phone'),
                data.get('department_id'),
                data.get('position'),
                data['employee_type'],
                user_account_id
            ),
            commit=True
        )
        
        log_audit(user_id, 'CREATE', 'employee', emp_id, None, data)
        
        return success_response({'id': emp_id}, 'Employee created successfully', 201)
    except Exception as e:
        return error_response(str(e), 500)

@employees_bp.route('/<int:id>', methods=['PUT'])
@token_required
@permission_required('admin', 'write')
def update_employee(id):
    data = request.get_json()
    user_id = request.current_user['user_id']
    
    old_data = execute_query("SELECT * FROM employees WHERE id = %s", (id,), fetch_one=True)
    if not old_data:
        return error_response('Employee not found', 404)
    
    query = """
        UPDATE employees SET
            employee_number = %s, first_name = %s, last_name = %s,
            email = %s, phone = %s, department_id = %s,
            position = %s, employee_type = %s
        WHERE id = %s
    """
    
    try:
        execute_query(
            query,
            (
                data.get('employee_number', old_data['employee_number']),
                data.get('first_name', old_data['first_name']),
                data.get('last_name', old_data['last_name']),
                data.get('email', old_data['email']),
                data.get('phone', old_data['phone']),
                data.get('department_id', old_data['department_id']),
                data.get('position', old_data['position']),
                data.get('employee_type', old_data['employee_type']),
                id
            ),
            commit=True
        )
        
        log_audit(user_id, 'UPDATE', 'employee', id, old_data, data)
        
        return success_response(message='Employee updated successfully')
    except Exception as e:
        return error_response(str(e), 500)

@employees_bp.route('/<int:id>', methods=['DELETE'])
@token_required
@permission_required('admin', 'delete')
def delete_employee(id):
    user_id = request.current_user['user_id']
    
    execute_query("UPDATE employees SET is_active = FALSE WHERE id = %s", (id,), commit=True)
    log_audit(user_id, 'DELETE', 'employee', id)
    
    return success_response(message='Employee deleted successfully')
