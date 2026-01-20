from flask import Blueprint, request
from backend.config.database import execute_query
from backend.utils.auth import token_required, permission_required
from backend.utils.response import success_response, error_response
from backend.utils.audit import log_audit
from backend.utils.notifications import create_notification
from datetime import datetime, timedelta
import json

preventive_bp = Blueprint('preventive', __name__, url_prefix='/api/maintenance/preventive')

@preventive_bp.route('', methods=['GET'])
@token_required
def get_preventive_schedules():
    machine_id = request.args.get('machine_id')
    is_active = request.args.get('is_active', 'true')
    
    query = """
        SELECT ps.*, m.machine_name, m.machine_number,
               CONCAT(e.first_name, ' ', e.last_name) as technician_name,
               CONCAT(created.first_name, ' ', created.last_name) as created_by_name
        FROM preventive_maintenance_schedules ps
        LEFT JOIN machines m ON ps.machine_id = m.id
        LEFT JOIN employees e ON ps.assigned_technician_id = e.id
        LEFT JOIN users created ON ps.created_by_id = created.id
        WHERE 1=1
    """
    
    params = []
    if machine_id:
        query += " AND ps.machine_id = %s"
        params.append(machine_id)
    
    if is_active.lower() == 'true':
        query += " AND ps.is_active = TRUE"
    
    query += " ORDER BY ps.next_due_at"
    
    schedules = execute_query(query, tuple(params) if params else None, fetch_all=True)
    return success_response(schedules)

@preventive_bp.route('/<int:id>', methods=['GET'])
@token_required
def get_preventive_schedule(id):
    query = """
        SELECT ps.*, m.machine_name, m.machine_number, m.department_id,
               CONCAT(e.first_name, ' ', e.last_name) as technician_name,
               CONCAT(created.first_name, ' ', created.last_name) as created_by_name
        FROM preventive_maintenance_schedules ps
        LEFT JOIN machines m ON ps.machine_id = m.id
        LEFT JOIN employees e ON ps.assigned_technician_id = e.id
        LEFT JOIN users created ON ps.created_by_id = created.id
        WHERE ps.id = %s
    """
    
    schedule = execute_query(query, (id,), fetch_one=True)
    
    if not schedule:
        return error_response('Preventive maintenance schedule not found', 404)
    
    logs_query = """
        SELECT pml.*, CONCAT(e.first_name, ' ', e.last_name) as performed_by_name
        FROM preventive_maintenance_logs pml
        LEFT JOIN employees e ON pml.performed_by_id = e.id
        WHERE pml.schedule_id = %s
        ORDER BY pml.performed_at DESC
    """
    logs = execute_query(logs_query, (id,), fetch_all=True)
    schedule['logs'] = logs
    
    return success_response(schedule)

@preventive_bp.route('', methods=['POST'])
@token_required
@permission_required('maintenance', 'write')
def create_preventive_schedule():
    data = request.get_json()
    user_id = request.current_user['user_id']
    
    required_fields = ['schedule_name', 'machine_id', 'maintenance_type', 'frequency_type', 'frequency_value']
    for field in required_fields:
        if not data.get(field):
            return error_response(f'{field} is required', 400)
    
    next_due_at = calculate_next_due_date(
        data['frequency_type'],
        data['frequency_value'],
        data.get('last_performed_at')
    )
    
    query = """
        INSERT INTO preventive_maintenance_schedules
        (schedule_name, machine_id, maintenance_type, description, frequency_type,
         frequency_value, next_due_at, estimated_duration_minutes, assigned_technician_id,
         priority, checklist, parts_required, created_by_id)
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
                next_due_at,
                data.get('estimated_duration_minutes'),
                data.get('assigned_technician_id'),
                data.get('priority', 'medium'),
                json.dumps(data.get('checklist', [])),
                json.dumps(data.get('parts_required', [])),
                user_id
            ),
            commit=True
        )
        
        if data.get('assigned_technician_id'):
            emp = execute_query(
                "SELECT user_id FROM employees WHERE id = %s",
                (data['assigned_technician_id'],),
                fetch_one=True
            )
            if emp and emp['user_id']:
                create_notification(
                    emp['user_id'],
                    'preventive_maintenance',
                    'New Preventive Maintenance Schedule',
                    f'You have been assigned to {data["schedule_name"]}',
                    'preventive_schedule',
                    schedule_id,
                    priority='medium'
                )
        
        log_audit(user_id, 'CREATE', 'preventive_schedule', schedule_id, None, data)
        
        return success_response({'id': schedule_id}, 'Preventive maintenance schedule created successfully', 201)
    except Exception as e:
        return error_response(str(e), 500)

@preventive_bp.route('/<int:id>', methods=['PUT'])
@token_required
@permission_required('maintenance', 'write')
def update_preventive_schedule(id):
    data = request.get_json()
    user_id = request.current_user['user_id']
    
    old_data = execute_query(
        "SELECT * FROM preventive_maintenance_schedules WHERE id = %s",
        (id,),
        fetch_one=True
    )
    
    if not old_data:
        return error_response('Schedule not found', 404)
    
    query = """
        UPDATE preventive_maintenance_schedules SET
            schedule_name = %s, maintenance_type = %s, description = %s,
            frequency_type = %s, frequency_value = %s, estimated_duration_minutes = %s,
            assigned_technician_id = %s, priority = %s, checklist = %s,
            parts_required = %s, is_active = %s
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
                data.get('is_active', old_data['is_active']),
                id
            ),
            commit=True
        )
        
        log_audit(user_id, 'UPDATE', 'preventive_schedule', id, old_data, data)
        
        return success_response(message='Schedule updated successfully')
    except Exception as e:
        return error_response(str(e), 500)

@preventive_bp.route('/<int:id>', methods=['DELETE'])
@token_required
@permission_required('maintenance', 'write')
def delete_preventive_schedule(id):
    user_id = request.current_user['user_id']
    
    old_data = execute_query(
        "SELECT * FROM preventive_maintenance_schedules WHERE id = %s",
        (id,),
        fetch_one=True
    )
    
    if not old_data:
        return error_response('Schedule not found', 404)
    
    try:
        execute_query(
            "UPDATE preventive_maintenance_schedules SET is_active = FALSE WHERE id = %s",
            (id,),
            commit=True
        )
        
        log_audit(user_id, 'DELETE', 'preventive_schedule', id, old_data, None)
        
        return success_response(message='Schedule deactivated successfully')
    except Exception as e:
        return error_response(str(e), 500)

@preventive_bp.route('/<int:schedule_id>/log', methods=['POST'])
@token_required
@permission_required('maintenance', 'write')
def log_preventive_maintenance(schedule_id):
    data = request.get_json()
    user_id = request.current_user['user_id']
    
    employee = execute_query(
        "SELECT id FROM employees WHERE user_id = %s",
        (user_id,),
        fetch_one=True
    )
    
    if not employee:
        return error_response('Employee not found', 404)
    
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
                schedule_id,
                data.get('performed_at', datetime.now()),
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
        
        schedule = execute_query(
            "SELECT * FROM preventive_maintenance_schedules WHERE id = %s",
            (schedule_id,),
            fetch_one=True
        )
        
        if schedule:
            next_due = calculate_next_due_date(
                schedule['frequency_type'],
                schedule['frequency_value'],
                data.get('performed_at', datetime.now())
            )
            
            execute_query(
                """UPDATE preventive_maintenance_schedules 
                   SET last_performed_at = %s, next_due_at = %s
                   WHERE id = %s""",
                (data.get('performed_at', datetime.now()), next_due, schedule_id),
                commit=True
            )
            
            if data.get('status') == 'completed':
                execute_query(
                    """UPDATE machines 
                       SET status = 'available'
                       WHERE id = %s AND status = 'maintenance'""",
                    (schedule['machine_id'],),
                    commit=True
                )
        
        log_audit(user_id, 'LOG_PM', 'preventive_schedule', schedule_id, None, data)
        
        return success_response({'id': log_id}, 'Maintenance logged successfully', 201)
    except Exception as e:
        return error_response(str(e), 500)

@preventive_bp.route('/<int:schedule_id>/logs', methods=['GET'])
@token_required
def get_preventive_logs(schedule_id):
    query = """
        SELECT pml.*, CONCAT(e.first_name, ' ', e.last_name) as performed_by_name
        FROM preventive_maintenance_logs pml
        LEFT JOIN employees e ON pml.performed_by_id = e.id
        WHERE pml.schedule_id = %s
        ORDER BY pml.performed_at DESC
    """
    
    logs = execute_query(query, (schedule_id,), fetch_all=True)
    return success_response(logs)

@preventive_bp.route('/<int:schedule_id>/start', methods=['POST'])
@token_required
@permission_required('maintenance', 'write')
def start_preventive_maintenance(schedule_id):
    user_id = request.current_user['user_id']
    
    schedule = execute_query(
        "SELECT * FROM preventive_maintenance_schedules WHERE id = %s",
        (schedule_id,),
        fetch_one=True
    )
    
    if not schedule:
        return error_response('Schedule not found', 404)
    
    try:
        execute_query(
            """UPDATE machines 
               SET status = 'maintenance'
               WHERE id = %s""",
            (schedule['machine_id'],),
            commit=True
        )
        
        log_audit(user_id, 'START_PM', 'preventive_schedule', schedule_id, None, {'machine_id': schedule['machine_id']})
        
        return success_response(message='Machine marked as under maintenance')
    except Exception as e:
        return error_response(str(e), 500)

def calculate_next_due_date(frequency_type, frequency_value, last_performed=None):
    base_date = last_performed if last_performed else datetime.now()
    if isinstance(base_date, str):
        base_date = datetime.fromisoformat(base_date.replace('Z', '+00:00'))
    
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


# Export with the name expected by app.py
preventive_maintenance_bp = preventive_bp
