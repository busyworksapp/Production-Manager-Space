from flask import Blueprint, request
from backend.config.database import execute_query
from backend.utils.auth import token_required, permission_required
from backend.utils.response import success_response, error_response
from backend.utils.audit import log_audit
from datetime import datetime, timedelta
import json

preventive_maintenance_bp = Blueprint('preventive_maintenance', __name__, url_prefix='/api/preventive-maintenance')

@preventive_maintenance_bp.route('/schedules', methods=['GET'])
@token_required
def get_schedules():
    machine_id = request.args.get('machine_id')
    is_active = request.args.get('is_active', 'true')
    overdue = request.args.get('overdue')
    
    query = """
        SELECT pms.*, m.machine_name, m.machine_number,
               CONCAT(e.first_name, ' ', e.last_name) as technician_name,
               d.name as department_name
        FROM preventive_maintenance_schedules pms
        LEFT JOIN machines m ON pms.machine_id = m.id
        LEFT JOIN employees e ON pms.assigned_technician_id = e.id
        LEFT JOIN departments d ON m.department_id = d.id
        WHERE 1=1
    """
    params = []
    
    if machine_id:
        query += " AND pms.machine_id = %s"
        params.append(machine_id)
    
    if is_active.lower() == 'true':
        query += " AND pms.is_active = TRUE"
    
    if overdue and overdue.lower() == 'true':
        query += " AND pms.next_due_at <= NOW()"
    
    query += " ORDER BY pms.next_due_at"
    
    schedules = execute_query(query, tuple(params) if params else None, fetch_all=True)
    return success_response(schedules)

@preventive_maintenance_bp.route('/schedules/<int:id>', methods=['GET'])
@token_required
def get_schedule(id):
    query = """
        SELECT pms.*, m.machine_name, m.machine_number,
               CONCAT(e.first_name, ' ', e.last_name) as technician_name,
               d.name as department_name
        FROM preventive_maintenance_schedules pms
        LEFT JOIN machines m ON pms.machine_id = m.id
        LEFT JOIN employees e ON pms.assigned_technician_id = e.id
        LEFT JOIN departments d ON m.department_id = d.id
        WHERE pms.id = %s
    """
    schedule = execute_query(query, (id,), fetch_one=True)
    
    if not schedule:
        return error_response('Schedule not found', 404)
    
    return success_response(schedule)

@preventive_maintenance_bp.route('/schedules', methods=['POST'])
@token_required
@permission_required('maintenance', 'write')
def create_schedule():
    data = request.get_json()
    user_id = request.current_user['user_id']
    
    required_fields = ['schedule_name', 'machine_id', 'maintenance_type', 'frequency_type', 'frequency_value']
    for field in required_fields:
        if not data.get(field):
            return error_response(f'{field} is required', 400)
    
    next_due = calculate_next_due(data['frequency_type'], data['frequency_value'])
    
    query = """
        INSERT INTO preventive_maintenance_schedules
        (schedule_name, machine_id, maintenance_type, description,
         frequency_type, frequency_value, next_due_at,
         estimated_duration_minutes, assigned_technician_id, priority,
         checklist, parts_required, created_by_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    try:
        schedule_id = execute_query(
            query,
            (
                data['schedule_name'],
                data['machine_id'],
                data['maintenance_type'],
                data.get('description'),
                data['frequency_type'],
                data['frequency_value'],
                next_due,
                data.get('estimated_duration_minutes'),
                data.get('assigned_technician_id'),
                data.get('priority', 'medium'),
                json.dumps(data.get('checklist', [])),
                json.dumps(data.get('parts_required', [])),
                user_id
            ),
            commit=True
        )
        
        log_audit(user_id, 'CREATE', 'preventive_maintenance_schedule', schedule_id, None, data)
        
        return success_response({'id': schedule_id}, 'Schedule created successfully', 201)
    except Exception as e:
        return error_response(str(e), 500)

@preventive_maintenance_bp.route('/schedules/<int:id>', methods=['PUT'])
@token_required
@permission_required('maintenance', 'write')
def update_schedule(id):
    data = request.get_json()
    user_id = request.current_user['user_id']
    
    old_data = execute_query("SELECT * FROM preventive_maintenance_schedules WHERE id = %s", (id,), fetch_one=True)
    if not old_data:
        return error_response('Schedule not found', 404)
    
    query = """
        UPDATE preventive_maintenance_schedules SET
            schedule_name = %s, maintenance_type = %s, description = %s,
            frequency_type = %s, frequency_value = %s,
            estimated_duration_minutes = %s, assigned_technician_id = %s,
            priority = %s, checklist = %s, parts_required = %s
        WHERE id = %s
    """
    
    try:
        execute_query(
            query,
            (
                data.get('schedule_name', old_data['schedule_name']),
                data.get('maintenance_type', old_data['maintenance_type']),
                data.get('description', old_data['description']),
                data.get('frequency_type', old_data['frequency_type']),
                data.get('frequency_value', old_data['frequency_value']),
                data.get('estimated_duration_minutes', old_data['estimated_duration_minutes']),
                data.get('assigned_technician_id', old_data['assigned_technician_id']),
                data.get('priority', old_data['priority']),
                json.dumps(data.get('checklist', old_data['checklist'])),
                json.dumps(data.get('parts_required', old_data['parts_required'])),
                id
            ),
            commit=True
        )
        
        log_audit(user_id, 'UPDATE', 'preventive_maintenance_schedule', id, old_data, data)
        
        return success_response(message='Schedule updated successfully')
    except Exception as e:
        return error_response(str(e), 500)

@preventive_maintenance_bp.route('/schedules/<int:id>/perform', methods=['POST'])
@token_required
@permission_required('maintenance', 'write')
def perform_maintenance(id):
    data = request.get_json()
    user_id = request.current_user['user_id']
    
    employee = execute_query(
        "SELECT id FROM employees WHERE user_id = %s",
        (user_id,),
        fetch_one=True
    )
    
    if not employee:
        return error_response('Employee record not found', 404)
    
    schedule = execute_query("SELECT * FROM preventive_maintenance_schedules WHERE id = %s", (id,), fetch_one=True)
    if not schedule:
        return error_response('Schedule not found', 404)
    
    query = """
        INSERT INTO preventive_maintenance_logs
        (schedule_id, performed_at, performed_by_id, duration_minutes,
         checklist_results, parts_used, observations, next_recommended_date, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    try:
        log_id = execute_query(
            query,
            (
                id,
                datetime.now(),
                employee['id'],
                data.get('duration_minutes'),
                json.dumps(data.get('checklist_results', {})),
                json.dumps(data.get('parts_used', [])),
                data.get('observations'),
                data.get('next_recommended_date'),
                data.get('status', 'completed')
            ),
            commit=True
        )
        
        next_due = calculate_next_due(schedule['frequency_type'], schedule['frequency_value'])
        
        execute_query(
            "UPDATE preventive_maintenance_schedules SET last_performed_at = %s, next_due_at = %s WHERE id = %s",
            (datetime.now(), next_due, id),
            commit=True
        )
        
        if data.get('machine_status'):
            execute_query(
                "UPDATE machines SET status = %s WHERE id = %s",
                (data['machine_status'], schedule['machine_id']),
                commit=True
            )
        
        log_audit(user_id, 'PERFORM_MAINTENANCE', 'preventive_maintenance_log', log_id)
        
        return success_response({'id': log_id}, 'Maintenance performed successfully', 201)
    except Exception as e:
        return error_response(str(e), 500)

@preventive_maintenance_bp.route('/logs', methods=['GET'])
@token_required
def get_logs():
    schedule_id = request.args.get('schedule_id')
    machine_id = request.args.get('machine_id')
    
    query = """
        SELECT pml.*, pms.schedule_name, pms.maintenance_type,
               m.machine_name, m.machine_number,
               CONCAT(e.first_name, ' ', e.last_name) as performed_by_name
        FROM preventive_maintenance_logs pml
        LEFT JOIN preventive_maintenance_schedules pms ON pml.schedule_id = pms.id
        LEFT JOIN machines m ON pms.machine_id = m.id
        LEFT JOIN employees e ON pml.performed_by_id = e.id
        WHERE 1=1
    """
    params = []
    
    if schedule_id:
        query += " AND pml.schedule_id = %s"
        params.append(schedule_id)
    
    if machine_id:
        query += " AND pms.machine_id = %s"
        params.append(machine_id)
    
    query += " ORDER BY pml.performed_at DESC"
    
    logs = execute_query(query, tuple(params) if params else None, fetch_all=True)
    return success_response(logs)

@preventive_maintenance_bp.route('/dashboard', methods=['GET'])
@token_required
def get_dashboard():
    stats = {
        'overdue': execute_query(
            "SELECT COUNT(*) as count FROM preventive_maintenance_schedules WHERE next_due_at <= NOW() AND is_active = TRUE",
            fetch_one=True
        ),
        'due_this_week': execute_query(
            "SELECT COUNT(*) as count FROM preventive_maintenance_schedules WHERE next_due_at BETWEEN NOW() AND DATE_ADD(NOW(), INTERVAL 7 DAY) AND is_active = TRUE",
            fetch_one=True
        ),
        'completed_this_month': execute_query(
            "SELECT COUNT(*) as count FROM preventive_maintenance_logs WHERE performed_at >= DATE_FORMAT(NOW(), '%Y-%m-01')",
            fetch_one=True
        )
    }
    
    return success_response(stats)

def calculate_next_due(frequency_type, frequency_value, from_date=None):
    base_date = from_date or datetime.now()
    
    if frequency_type == 'daily':
        return base_date + timedelta(days=frequency_value)
    elif frequency_type == 'weekly':
        return base_date + timedelta(weeks=frequency_value)
    elif frequency_type == 'monthly':
        return base_date + timedelta(days=frequency_value * 30)
    elif frequency_type == 'quarterly':
        return base_date + timedelta(days=frequency_value * 90)
    elif frequency_type == 'yearly':
        return base_date + timedelta(days=frequency_value * 365)
    else:
        return base_date + timedelta(days=30)
