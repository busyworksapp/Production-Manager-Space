from flask import Blueprint, request
from backend.config.database import execute_query
from backend.utils.auth import token_required, permission_required
from backend.utils.response import success_response, error_response
from backend.utils.audit import log_audit

machines_bp = Blueprint('machines', __name__, url_prefix='/api/machines')

@machines_bp.route('', methods=['GET'])
@token_required
def get_machines():
    department_id = request.args.get('department_id')
    status = request.args.get('status')
    
    query = """
        SELECT m.*, d.name as department_name
        FROM machines m
        LEFT JOIN departments d ON m.department_id = d.id
        WHERE m.is_active = TRUE
    """
    
    params = []
    if department_id:
        query += " AND m.department_id = %s"
        params.append(department_id)
    
    if status:
        query += " AND m.status = %s"
        params.append(status)
    
    query += " ORDER BY m.machine_name"
    
    machines = execute_query(query, tuple(params) if params else None, fetch_all=True)
    return success_response(machines)

@machines_bp.route('/<int:id>', methods=['GET'])
@token_required
def get_machine(id):
    query = """
        SELECT m.*, d.name as department_name
        FROM machines m
        LEFT JOIN departments d ON m.department_id = d.id
        WHERE m.id = %s
    """
    machine = execute_query(query, (id,), fetch_one=True)
    
    if not machine:
        return error_response('Machine not found', 404)
    
    return success_response(machine)

@machines_bp.route('', methods=['POST'])
@token_required
@permission_required('admin', 'write')
def create_machine():
    data = request.get_json()
    user_id = request.current_user['user_id']
    
    required_fields = ['machine_number', 'machine_name', 'department_id']
    for field in required_fields:
        if not data.get(field):
            return error_response(f'{field} is required', 400)
    
    query = """
        INSERT INTO machines
        (machine_number, machine_name, department_id, machine_type,
         manufacturer, model, serial_number, purchase_date, status, config)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    try:
        machine_id = execute_query(
            query,
            (
                data['machine_number'],
                data['machine_name'],
                data['department_id'],
                data.get('machine_type'),
                data.get('manufacturer'),
                data.get('model'),
                data.get('serial_number'),
                data.get('purchase_date'),
                data.get('status', 'available'),
                data.get('config')
            ),
            commit=True
        )
        
        log_audit(user_id, 'CREATE', 'machine', machine_id, None, data)
        
        return success_response({'id': machine_id}, 'Machine created successfully', 201)
    except Exception as e:
        return error_response(str(e), 500)

@machines_bp.route('/<int:id>', methods=['PUT'])
@token_required
@permission_required('admin', 'write')
def update_machine(id):
    data = request.get_json()
    user_id = request.current_user['user_id']
    
    old_data = execute_query("SELECT * FROM machines WHERE id = %s", (id,), fetch_one=True)
    if not old_data:
        return error_response('Machine not found', 404)
    
    query = """
        UPDATE machines SET
            machine_number = %s, machine_name = %s, department_id = %s,
            machine_type = %s, manufacturer = %s, model = %s,
            serial_number = %s, purchase_date = %s, status = %s, config = %s
        WHERE id = %s
    """
    
    try:
        execute_query(
            query,
            (
                data.get('machine_number', old_data['machine_number']),
                data.get('machine_name', old_data['machine_name']),
                data.get('department_id', old_data['department_id']),
                data.get('machine_type', old_data['machine_type']),
                data.get('manufacturer', old_data['manufacturer']),
                data.get('model', old_data['model']),
                data.get('serial_number', old_data['serial_number']),
                data.get('purchase_date', old_data['purchase_date']),
                data.get('status', old_data['status']),
                data.get('config', old_data['config']),
                id
            ),
            commit=True
        )
        
        log_audit(user_id, 'UPDATE', 'machine', id, old_data, data)
        
        return success_response(message='Machine updated successfully')
    except Exception as e:
        return error_response(str(e), 500)

@machines_bp.route('/<int:id>/status', methods=['PATCH'])
@token_required
def update_machine_status(id):
    data = request.get_json()
    user_id = request.current_user['user_id']
    
    status = data.get('status')
    if status not in ['available', 'in_use', 'maintenance', 'broken', 'retired']:
        return error_response('Invalid status', 400)
    
    execute_query(
        "UPDATE machines SET status = %s WHERE id = %s",
        (status, id),
        commit=True
    )
    
    log_audit(user_id, 'UPDATE_STATUS', 'machine', id, None, {'status': status})
    
    return success_response(message='Machine status updated successfully')

@machines_bp.route('/availability', methods=['GET'])
@token_required
def get_machine_availability():
    department_id = request.args.get('department_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    query = """
        SELECT 
            m.id, m.machine_name, m.machine_number, m.status, m.department_id,
            d.name as department_name,
            (SELECT COUNT(*) FROM job_schedules js 
             WHERE js.machine_id = m.id 
             AND js.status IN ('scheduled', 'in_progress')
             AND js.scheduled_date BETWEEN %s AND %s) as scheduled_jobs,
            (SELECT COUNT(*) FROM maintenance_tickets mt 
             WHERE mt.machine_id = m.id 
             AND mt.status IN ('open', 'in_progress')) as open_maintenance
        FROM machines m
        LEFT JOIN departments d ON m.department_id = d.id
        WHERE m.is_active = TRUE
    """
    
    params = [start_date or '2024-01-01', end_date or '2099-12-31']
    
    if department_id:
        query += " AND m.department_id = %s"
        params.append(department_id)
    
    query += " ORDER BY m.machine_name"
    
    machines = execute_query(query, tuple(params), fetch_all=True)
    
    for machine in machines:
        if machine['status'] in ['broken', 'retired']:
            machine['availability_status'] = 'unavailable'
        elif machine['status'] == 'maintenance' or machine['open_maintenance'] > 0:
            machine['availability_status'] = 'maintenance'
        elif machine['scheduled_jobs'] > 5:
            machine['availability_status'] = 'busy'
        elif machine['scheduled_jobs'] > 0:
            machine['availability_status'] = 'limited'
        else:
            machine['availability_status'] = 'available'
    
    return success_response(machines)

@machines_bp.route('/<int:id>/capacity', methods=['GET'])
@token_required
def get_machine_capacity(id):
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    machine = execute_query("SELECT * FROM machines WHERE id = %s", (id,), fetch_one=True)
    if not machine:
        return error_response('Machine not found', 404)
    
    scheduled_jobs = execute_query(
        """SELECT js.*, o.order_number, o.customer_name
           FROM job_schedules js
           LEFT JOIN orders o ON js.order_id = o.id
           WHERE js.machine_id = %s
           AND js.scheduled_date BETWEEN %s AND %s
           ORDER BY js.scheduled_date""",
        (id, start_date or '2024-01-01', end_date or '2099-12-31'),
        fetch_all=True
    )
    
    maintenance_schedule = execute_query(
        """SELECT * FROM preventive_maintenance_schedules
           WHERE machine_id = %s AND is_active = TRUE
           ORDER BY next_due_at""",
        (id,),
        fetch_all=True
    )
    
    return success_response({
        'machine': machine,
        'scheduled_jobs': scheduled_jobs,
        'scheduled_jobs_count': len(scheduled_jobs),
        'maintenance_schedule': maintenance_schedule,
        'capacity_percentage': min(100, len(scheduled_jobs) * 10)
    })

@machines_bp.route('/calendar', methods=['GET'])
@token_required
def get_machine_calendar():
    """Get machine availability calendar data including preventive maintenance and downtime"""
    department_id = request.args.get('department_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if not start_date or not end_date:
        return error_response('start_date and end_date are required', 400)
    
    machines_query = """
        SELECT m.id, m.machine_name, m.machine_number, m.status, m.department_id,
               d.name as department_name
        FROM machines m
        LEFT JOIN departments d ON m.department_id = d.id
        WHERE m.is_active = TRUE
    """
    
    params = []
    if department_id:
        machines_query += " AND m.department_id = %s"
        params.append(department_id)
    
    machines_query += " ORDER BY m.machine_name"
    machines = execute_query(machines_query, tuple(params) if params else None, fetch_all=True)
    
    preventive_maintenance_query = """
        SELECT pms.*, m.machine_name, m.machine_number, m.department_id,
               CONCAT(e.first_name, ' ', e.last_name) as technician_name
        FROM preventive_maintenance_schedules pms
        LEFT JOIN machines m ON pms.machine_id = m.id
        LEFT JOIN employees e ON pms.assigned_technician_id = e.id
        WHERE pms.is_active = TRUE
        AND pms.next_due_at BETWEEN %s AND %s
    """
    
    pm_params = [start_date, end_date]
    if department_id:
        preventive_maintenance_query += " AND m.department_id = %s"
        pm_params.append(department_id)
    
    preventive_maintenance_query += " ORDER BY pms.next_due_at"
    pm_schedules = execute_query(preventive_maintenance_query, tuple(pm_params), fetch_all=True)
    
    maintenance_tickets_query = """
        SELECT mt.*, m.machine_name, m.machine_number, m.department_id,
               CONCAT(assigned.first_name, ' ', assigned.last_name) as assigned_to_name
        FROM maintenance_tickets mt
        LEFT JOIN machines m ON mt.machine_id = m.id
        LEFT JOIN users assigned ON mt.assigned_to_id = assigned.id
        WHERE mt.status IN ('open', 'assigned', 'in_progress', 'awaiting_parts')
    """
    
    mt_params = []
    if department_id:
        maintenance_tickets_query += " AND m.department_id = %s"
        mt_params.append(department_id)
    
    maintenance_tickets_query += " ORDER BY mt.created_at DESC"
    maintenance_tickets = execute_query(maintenance_tickets_query, tuple(mt_params) if mt_params else None, fetch_all=True)
    
    calendar_events = []
    
    for pm in pm_schedules:
        calendar_events.append({
            'id': f'pm_{pm["id"]}',
            'type': 'preventive_maintenance',
            'title': pm['schedule_name'],
            'machine_id': pm['machine_id'],
            'machine_name': pm['machine_name'],
            'start': pm['next_due_at'],
            'duration_minutes': pm['estimated_duration_minutes'] or 120,
            'priority': pm['priority'],
            'technician': pm['technician_name'],
            'description': pm['description'],
            'maintenance_type': pm['maintenance_type']
        })
    
    for mt in maintenance_tickets:
        start_time = mt.get('actual_start_time') or mt.get('expected_start_time') or mt['created_at']
        calendar_events.append({
            'id': f'mt_{mt["id"]}',
            'type': 'maintenance_ticket',
            'title': f"{mt['ticket_number']} - {mt['issue_description'][:50]}",
            'machine_id': mt['machine_id'],
            'machine_name': mt['machine_name'],
            'start': start_time,
            'status': mt['status'],
            'severity': mt['severity'],
            'assigned_to': mt['assigned_to_name'],
            'ticket_number': mt['ticket_number']
        })
    
    return success_response({
        'machines': machines,
        'events': calendar_events,
        'preventive_maintenance': pm_schedules,
        'maintenance_tickets': maintenance_tickets
    })
