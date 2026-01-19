from flask import Blueprint, request
from backend.config.database import execute_query
from backend.utils.auth import token_required, permission_required
from backend.utils.response import success_response, error_response
from backend.utils.audit import log_audit
from datetime import datetime
import json

manager_controls_bp = Blueprint('manager_controls', __name__, url_prefix='/api/manager-controls')

@manager_controls_bp.route('/my-department', methods=['GET'])
@token_required
def get_my_department():
    user_id = request.current_user['user_id']
    
    department = execute_query(
        "SELECT * FROM departments WHERE manager_id = %s AND is_active = TRUE",
        (user_id,),
        fetch_one=True
    )
    
    if not department:
        return error_response('No department found for this manager', 404)
    
    employees = execute_query(
        """SELECT e.*, CONCAT(e.first_name, ' ', e.last_name) as full_name,
                  u.username, u.email
           FROM employees e
           LEFT JOIN users u ON e.user_id = u.id
           WHERE e.department_id = %s AND e.is_active = TRUE
           ORDER BY e.first_name""",
        (department['id'],),
        fetch_all=True
    )
    
    machines = execute_query(
        "SELECT * FROM machines WHERE department_id = %s AND is_active = TRUE ORDER BY machine_name",
        (department['id'],),
        fetch_all=True
    )
    
    stages = execute_query(
        "SELECT * FROM production_stages WHERE department_id = %s AND is_active = TRUE ORDER BY stage_order",
        (department['id'],),
        fetch_all=True
    )
    
    department['employees'] = employees
    department['machines'] = machines
    department['production_stages'] = stages
    
    return success_response(department)

@manager_controls_bp.route('/employee-machine-allocations', methods=['GET'])
@token_required
def get_employee_machine_allocations():
    user_id = request.current_user['user_id']
    
    department = execute_query(
        "SELECT id FROM departments WHERE manager_id = %s",
        (user_id,),
        fetch_one=True
    )
    
    if not department:
        return error_response('No department found for this manager', 404)
    
    query = """
        SELECT ema.*, 
               CONCAT(e.first_name, ' ', e.last_name) as employee_name,
               e.employee_number,
               m.machine_name, m.machine_number,
               CONCAT(u.first_name, ' ', u.last_name) as allocated_by_name
        FROM employee_machine_allocations ema
        LEFT JOIN employees e ON ema.employee_id = e.id
        LEFT JOIN machines m ON ema.machine_id = m.id
        LEFT JOIN users u ON ema.allocated_by_id = u.id
        WHERE e.department_id = %s
        ORDER BY ema.is_active DESC, ema.created_at DESC
    """
    
    allocations = execute_query(query, (department['id'],), fetch_all=True)
    return success_response(allocations)

@manager_controls_bp.route('/employee-machine-allocations', methods=['POST'])
@token_required
@permission_required('department', 'manage_employees')
def allocate_employee_to_machine():
    data = request.get_json()
    user_id = request.current_user['user_id']
    
    required_fields = ['employee_id', 'machine_id', 'start_date']
    for field in required_fields:
        if not data.get(field):
            return error_response(f'{field} is required', 400)
    
    employee = execute_query("SELECT department_id FROM employees WHERE id = %s", (data['employee_id'],), fetch_one=True)
    department = execute_query("SELECT id FROM departments WHERE manager_id = %s", (user_id,), fetch_one=True)
    
    if not employee or not department or employee['department_id'] != department['id']:
        return error_response('Unauthorized or invalid employee', 403)
    
    query = """
        INSERT INTO employee_machine_allocations
        (employee_id, machine_id, allocation_type, start_date, end_date, notes, allocated_by_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    
    try:
        allocation_id = execute_query(
            query,
            (
                data['employee_id'],
                data['machine_id'],
                data.get('allocation_type', 'primary'),
                data['start_date'],
                data.get('end_date'),
                data.get('notes'),
                user_id
            ),
            commit=True
        )
        
        log_audit(user_id, 'ALLOCATE_EMPLOYEE', 'employee_machine_allocation', allocation_id, None, data)
        
        return success_response({'id': allocation_id}, 'Employee allocated to machine successfully', 201)
    except Exception as e:
        return error_response(str(e), 500)

@manager_controls_bp.route('/employee-machine-allocations/<int:id>', methods=['PUT'])
@token_required
@permission_required('department', 'manage_employees')
def update_employee_machine_allocation(id):
    data = request.get_json()
    user_id = request.current_user['user_id']
    
    old_data = execute_query("SELECT * FROM employee_machine_allocations WHERE id = %s", (id,), fetch_one=True)
    if not old_data:
        return error_response('Allocation not found', 404)
    
    query = """
        UPDATE employee_machine_allocations SET
            allocation_type = %s, start_date = %s, end_date = %s,
            is_active = %s, notes = %s
        WHERE id = %s
    """
    
    try:
        execute_query(
            query,
            (
                data.get('allocation_type', old_data['allocation_type']),
                data.get('start_date', old_data['start_date']),
                data.get('end_date', old_data['end_date']),
                data.get('is_active', old_data['is_active']),
                data.get('notes', old_data['notes']),
                id
            ),
            commit=True
        )
        
        log_audit(user_id, 'UPDATE', 'employee_machine_allocation', id, old_data, data)
        
        return success_response(message='Allocation updated successfully')
    except Exception as e:
        return error_response(str(e), 500)

@manager_controls_bp.route('/employee-machine-allocations/<int:id>/deactivate', methods=['POST'])
@token_required
@permission_required('department', 'manage_employees')
def deactivate_allocation(id):
    user_id = request.current_user['user_id']
    
    execute_query(
        "UPDATE employee_machine_allocations SET is_active = FALSE, end_date = CURDATE() WHERE id = %s",
        (id,),
        commit=True
    )
    
    log_audit(user_id, 'DEACTIVATE', 'employee_machine_allocation', id)
    
    return success_response(message='Allocation deactivated successfully')

@manager_controls_bp.route('/job-assignments', methods=['GET'])
@token_required
def get_job_assignments():
    user_id = request.current_user['user_id']
    
    department = execute_query(
        "SELECT id FROM departments WHERE manager_id = %s",
        (user_id,),
        fetch_one=True
    )
    
    if not department:
        return error_response('No department found for this manager', 404)
    
    query = """
        SELECT js.*, o.order_number, o.customer_name, o.quantity as order_quantity,
               p.product_name, ps.stage_name, m.machine_name,
               CONCAT(e.first_name, ' ', e.last_name) as employee_name
        FROM job_schedules js
        LEFT JOIN orders o ON js.order_id = o.id
        LEFT JOIN products p ON o.product_id = p.id
        LEFT JOIN production_stages ps ON js.stage_id = ps.id
        LEFT JOIN machines m ON js.machine_id = m.id
        LEFT JOIN employees e ON js.assigned_employee_id = e.id
        WHERE js.department_id = %s
        ORDER BY js.scheduled_date, js.status
    """
    
    jobs = execute_query(query, (department['id'],), fetch_all=True)
    return success_response(jobs)

@manager_controls_bp.route('/job-assignments/<int:job_id>/assign', methods=['POST'])
@token_required
@permission_required('department', 'manage_employees')
def assign_job_to_employee(job_id):
    data = request.get_json()
    user_id = request.current_user['user_id']
    
    department = execute_query(
        "SELECT id FROM departments WHERE manager_id = %s",
        (user_id,),
        fetch_one=True
    )
    
    if not department:
        return error_response('Unauthorized', 403)
    
    job = execute_query(
        "SELECT * FROM job_schedules WHERE id = %s AND department_id = %s",
        (job_id, department['id']),
        fetch_one=True
    )
    
    if not job:
        return error_response('Job not found or unauthorized', 404)
    
    execute_query(
        "UPDATE job_schedules SET assigned_employee_id = %s, machine_id = %s WHERE id = %s",
        (data.get('employee_id'), data.get('machine_id'), job_id),
        commit=True
    )
    
    log_audit(user_id, 'ASSIGN_JOB', 'job_schedule', job_id)
    
    return success_response(message='Job assigned successfully')

@manager_controls_bp.route('/job-assignments/<int:job_id>/reschedule', methods=['POST'])
@token_required
@permission_required('department', 'manage_employees')
def reschedule_job(job_id):
    data = request.get_json()
    user_id = request.current_user['user_id']
    
    department = execute_query(
        "SELECT id FROM departments WHERE manager_id = %s",
        (user_id,),
        fetch_one=True
    )
    
    if not department:
        return error_response('Unauthorized', 403)
    
    job = execute_query(
        "SELECT * FROM job_schedules WHERE id = %s AND department_id = %s",
        (job_id, department['id']),
        fetch_one=True
    )
    
    if not job:
        return error_response('Job not found or unauthorized', 404)
    
    execute_query(
        "UPDATE job_schedules SET scheduled_date = %s WHERE id = %s",
        (data.get('scheduled_date'), job_id),
        commit=True
    )
    
    log_audit(user_id, 'RESCHEDULE_JOB', 'job_schedule', job_id)
    
    return success_response(message='Job rescheduled successfully')

@manager_controls_bp.route('/dashboard', methods=['GET'])
@token_required
def get_manager_dashboard():
    user_id = request.current_user['user_id']
    
    department = execute_query(
        "SELECT * FROM departments WHERE manager_id = %s",
        (user_id,),
        fetch_one=True
    )
    
    if not department:
        return error_response('No department found for this manager', 404)
    
    stats = {
        'total_employees': execute_query(
            "SELECT COUNT(*) as count FROM employees WHERE department_id = %s AND is_active = TRUE",
            (department['id'],),
            fetch_one=True
        ),
        'total_machines': execute_query(
            "SELECT COUNT(*) as count FROM machines WHERE department_id = %s AND is_active = TRUE",
            (department['id'],),
            fetch_one=True
        ),
        'machines_in_use': execute_query(
            "SELECT COUNT(*) as count FROM machines WHERE department_id = %s AND status = 'in_use'",
            (department['id'],),
            fetch_one=True
        ),
        'machines_maintenance': execute_query(
            "SELECT COUNT(*) as count FROM machines WHERE department_id = %s AND status IN ('maintenance', 'broken')",
            (department['id'],),
            fetch_one=True
        ),
        'jobs_scheduled': execute_query(
            "SELECT COUNT(*) as count FROM job_schedules WHERE department_id = %s AND status = 'scheduled'",
            (department['id'],),
            fetch_one=True
        ),
        'jobs_in_progress': execute_query(
            "SELECT COUNT(*) as count FROM job_schedules WHERE department_id = %s AND status = 'in_progress'",
            (department['id'],),
            fetch_one=True
        ),
        'jobs_completed_today': execute_query(
            "SELECT COUNT(*) as count FROM job_schedules WHERE department_id = %s AND status = 'completed' AND DATE(completed_at) = CURDATE()",
            (department['id'],),
            fetch_one=True
        )
    }
    
    return success_response({
        'department': department,
        'stats': stats
    })

@manager_controls_bp.route('/department-stats', methods=['GET'])
@token_required
def get_department_stats():
    user_id = request.current_user['user_id']
    
    department = execute_query(
        "SELECT id FROM departments WHERE manager_id = %s",
        (user_id,),
        fetch_one=True
    )
    
    if not department:
        return error_response('No department found for this manager', 404)
    
    active_jobs = execute_query(
        "SELECT COUNT(*) as count FROM job_schedules WHERE department_id = %s AND status = 'in_progress'",
        (department['id'],),
        fetch_one=True
    )
    
    pending_jobs = execute_query(
        "SELECT COUNT(*) as count FROM job_schedules WHERE department_id = %s AND status = 'scheduled'",
        (department['id'],),
        fetch_one=True
    )
    
    return success_response({
        'active_jobs': active_jobs['count'] if active_jobs else 0,
        'pending_jobs': pending_jobs['count'] if pending_jobs else 0
    })

@manager_controls_bp.route('/department-jobs', methods=['GET'])
@token_required
def get_department_jobs():
    user_id = request.current_user['user_id']
    
    department = execute_query(
        "SELECT id FROM departments WHERE manager_id = %s",
        (user_id,),
        fetch_one=True
    )
    
    if not department:
        return error_response('No department found for this manager', 404)
    
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
        WHERE js.department_id = %s
        ORDER BY js.scheduled_date, js.status
    """
    
    jobs = execute_query(query, (department['id'],), fetch_all=True)
    return success_response(jobs)

@manager_controls_bp.route('/assign-job/<int:job_id>', methods=['POST'])
@token_required
@permission_required('department', 'manage_employees')
def assign_job(job_id):
    data = request.get_json()
    user_id = request.current_user['user_id']
    
    department = execute_query(
        "SELECT id FROM departments WHERE manager_id = %s",
        (user_id,),
        fetch_one=True
    )
    
    if not department:
        return error_response('Unauthorized', 403)
    
    job = execute_query(
        "SELECT * FROM job_schedules WHERE id = %s AND department_id = %s",
        (job_id, department['id']),
        fetch_one=True
    )
    
    if not job:
        return error_response('Job not found or unauthorized', 404)
    
    execute_query(
        "UPDATE job_schedules SET assigned_employee_id = %s, machine_id = %s, scheduled_date = %s WHERE id = %s",
        (data.get('assigned_employee_id'), data.get('machine_id'), data.get('scheduled_date'), job_id),
        commit=True
    )
    
    log_audit(user_id, 'ASSIGN_JOB', 'job_schedule', job_id, None, data)
    
    return success_response(message='Job assigned successfully')
