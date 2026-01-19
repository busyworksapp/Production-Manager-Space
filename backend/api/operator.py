from flask import Blueprint, request
from backend.config.database import execute_query
from backend.utils.auth import token_required, hash_password, verify_password, generate_token
from backend.utils.response import success_response, error_response
from backend.utils.audit import log_audit
from datetime import datetime

operator_bp = Blueprint('operator', __name__, url_prefix='/api/operator')

@operator_bp.route('/login', methods=['POST'])
def operator_login():
    data = request.get_json()
    employee_number = data.get('employee_number')
    
    if not employee_number:
        return error_response('Employee number is required', 400)
    
    query = """
        SELECT e.id as employee_id, e.first_name, e.last_name, e.employee_type,
               e.department_id, d.name as department_name,
               u.id as user_id, u.username, u.password_hash, u.role_id
        FROM employees e
        LEFT JOIN departments d ON e.department_id = d.id
        LEFT JOIN users u ON e.user_id = u.id
        WHERE e.employee_number = %s AND e.is_active = TRUE
    """
    
    employee = execute_query(query, (employee_number,), fetch_one=True)
    
    if not employee:
        return error_response('Invalid employee number', 401)
    
    if not employee['user_id']:
        return error_response('No user account associated with this employee', 401)
    
    if not verify_password(employee_number, employee['password_hash']):
        return error_response('Invalid credentials', 401)
    
    execute_query(
        "UPDATE users SET last_login = %s WHERE id = %s",
        (datetime.now(), employee['user_id']),
        commit=True
    )
    
    token = generate_token(employee['user_id'], employee['username'], employee['role_id'])
    
    log_audit(employee['user_id'], 'OPERATOR_LOGIN', 'employee', employee['employee_id'])
    
    return success_response({
        'token': token,
        'employee': {
            'id': employee['employee_id'],
            'name': f"{employee['first_name']} {employee['last_name']}",
            'employee_type': employee['employee_type'],
            'department_id': employee['department_id'],
            'department_name': employee['department_name']
        }
    })

@operator_bp.route('/my-jobs', methods=['GET'])
@token_required
def get_my_jobs():
    user_id = request.current_user['user_id']
    
    employee = execute_query(
        "SELECT id, department_id, employee_type FROM employees WHERE user_id = %s",
        (user_id,),
        fetch_one=True
    )
    
    if not employee:
        return error_response('Employee not found', 404)
    
    query = """
        SELECT js.*, o.order_number, o.customer_name, o.quantity as order_quantity,
               p.product_name, d.name as department_name, ps.stage_name,
               m.machine_name, CONCAT(e.first_name, ' ', e.last_name) as assigned_employee_name
        FROM job_schedules js
        LEFT JOIN orders o ON js.order_id = o.id
        LEFT JOIN products p ON o.product_id = p.id
        LEFT JOIN departments d ON js.department_id = d.id
        LEFT JOIN production_stages ps ON js.stage_id = ps.id
        LEFT JOIN machines m ON js.machine_id = m.id
        LEFT JOIN employees e ON js.assigned_employee_id = e.id
    """
    
    if employee['employee_type'] in ['applique_cutter', 'packer']:
        query += " WHERE js.department_id = %s"
        params = (employee['department_id'],)
    else:
        query += " WHERE (js.assigned_employee_id = %s OR js.department_id = %s)"
        params = (employee['id'], employee['department_id'])
    
    query += " AND js.status IN ('scheduled', 'in_progress') ORDER BY js.scheduled_date, js.created_at"
    
    jobs = execute_query(query, params, fetch_all=True)
    return success_response(jobs)

@operator_bp.route('/job/<int:job_id>/start', methods=['POST'])
@token_required
def start_job(job_id):
    data = request.get_json()
    user_id = request.current_user['user_id']
    
    employee = execute_query(
        "SELECT id FROM employees WHERE user_id = %s",
        (user_id,),
        fetch_one=True
    )
    
    if not employee:
        return error_response('Employee not found', 404)
    
    machine_id = data.get('machine_id')
    
    execute_query(
        """UPDATE job_schedules 
           SET status = 'in_progress', started_at = %s, 
               assigned_employee_id = %s, machine_id = %s
           WHERE id = %s""",
        (datetime.now(), employee['id'], machine_id, job_id),
        commit=True
    )
    
    if machine_id:
        execute_query(
            "UPDATE machines SET status = 'in_use' WHERE id = %s",
            (machine_id,),
            commit=True
        )
    
    job = execute_query("SELECT order_id FROM job_schedules WHERE id = %s", (job_id,), fetch_one=True)
    if job:
        execute_query(
            "UPDATE orders SET status = 'in_progress' WHERE id = %s",
            (job['order_id'],),
            commit=True
        )
    
    log_audit(user_id, 'START_JOB', 'job_schedule', job_id, None, data)
    
    return success_response(message='Job started successfully')

@operator_bp.route('/job/<int:job_id>/complete', methods=['POST'])
@token_required
def complete_job(job_id):
    data = request.get_json()
    user_id = request.current_user['user_id']
    
    actual_quantity = data.get('actual_quantity')
    if not actual_quantity:
        return error_response('Actual quantity is required', 400)
    
    job = execute_query(
        """SELECT js.*, o.quantity as order_quantity
           FROM job_schedules js
           LEFT JOIN orders o ON js.order_id = o.id
           WHERE js.id = %s""",
        (job_id,),
        fetch_one=True
    )
    
    if not job:
        return error_response('Job not found', 404)
    
    scheduled_qty = job['scheduled_quantity']
    variance = actual_quantity - scheduled_qty
    variance_percentage = round((variance / scheduled_qty) * 100, 2) if scheduled_qty > 0 else 0
    
    warning = None
    severity = 'info'
    
    if actual_quantity > scheduled_qty:
        if variance_percentage > 10:
            warning = f'Over-production: {variance} units ({variance_percentage}% excess)'
            severity = 'warning'
        else:
            warning = f'Actual quantity exceeds scheduled by {variance} units'
            severity = 'info'
        
        execute_query(
            """INSERT INTO audit_log (user_id, action, entity_type, entity_id, new_data)
               VALUES (%s, 'OVER_PRODUCTION', 'job_schedule', %s, %s)""",
            (user_id, job_id, f'{{"variance": {variance}, "percentage": {variance_percentage}}}'),
            commit=True
        )
    elif actual_quantity < scheduled_qty:
        if variance_percentage < -10:
            warning = f'Under-production: {abs(variance)} units short ({abs(variance_percentage)}% deficit)'
            severity = 'error'
        else:
            warning = f'Job incomplete - {abs(variance)} units short'
            severity = 'warning'
        
        execute_query(
            """INSERT INTO audit_log (user_id, action, entity_type, entity_id, new_data)
               VALUES (%s, 'UNDER_PRODUCTION', 'job_schedule', %s, %s)""",
            (user_id, job_id, f'{{"variance": {variance}, "percentage": {variance_percentage}}}'),
            commit=True
        )
    
    execute_query(
        """UPDATE job_schedules 
           SET status = 'completed', completed_at = %s, actual_quantity = %s, notes = %s
           WHERE id = %s""",
        (datetime.now(), actual_quantity, data.get('notes'), job_id),
        commit=True
    )
    
    if job['machine_id']:
        execute_query(
            "UPDATE machines SET status = 'available' WHERE id = %s",
            (job['machine_id'],),
            commit=True
        )
    
    log_audit(user_id, 'COMPLETE_JOB', 'job_schedule', job_id, None, data)
    
    response_data = {
        'message': 'Job completed successfully',
        'scheduled_quantity': scheduled_qty,
        'actual_quantity': actual_quantity,
        'variance': variance,
        'variance_percentage': variance_percentage
    }
    if warning:
        response_data['warning'] = warning
        response_data['severity'] = severity
    
    return success_response(response_data)

@operator_bp.route('/job/add-manual', methods=['POST'])
@token_required
def add_manual_job():
    data = request.get_json()
    user_id = request.current_user['user_id']
    
    order_number = data.get('order_number')
    if not order_number:
        return error_response('Order number is required', 400)
    
    employee = execute_query(
        "SELECT id, department_id FROM employees WHERE user_id = %s",
        (user_id,),
        fetch_one=True
    )
    
    if not employee:
        return error_response('Employee not found', 404)
    
    order = execute_query(
        "SELECT id, quantity FROM orders WHERE order_number = %s",
        (order_number,),
        fetch_one=True
    )
    
    if not order:
        return error_response('Order not found', 404)
    
    query = """
        INSERT INTO job_schedules
        (order_id, department_id, scheduled_date, scheduled_quantity, 
         assigned_employee_id, status)
        VALUES (%s, %s, %s, %s, %s, 'in_progress')
    """
    
    try:
        job_id = execute_query(
            query,
            (order['id'], employee['department_id'], datetime.now().date(), 
             order['quantity'], employee['id']),
            commit=True
        )
        
        log_audit(user_id, 'ADD_MANUAL_JOB', 'job_schedule', job_id, None, data)
        
        return success_response({'id': job_id}, 'Job added successfully', 201)
    except Exception as e:
        return error_response(str(e), 500)
