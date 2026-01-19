from flask import Blueprint, request
from backend.config.database import execute_query
from backend.utils.auth import token_required, permission_required
from backend.utils.response import success_response, error_response
from backend.utils.audit import log_audit
from backend.utils.notifications import create_notification
from datetime import datetime

maintenance_bp = Blueprint('maintenance', __name__, url_prefix='/api/maintenance')

@maintenance_bp.route('/tickets', methods=['GET'])
@token_required
def get_maintenance_tickets():
    status = request.args.get('status')
    machine_id = request.args.get('machine_id')
    department_id = request.args.get('department_id')
    
    query = """
        SELECT mt.*, m.machine_name, m.machine_number, d.name as department_name,
               CONCAT(reported.first_name, ' ', reported.last_name) as reported_by_name,
               CONCAT(assigned.first_name, ' ', assigned.last_name) as assigned_to_name
        FROM maintenance_tickets mt
        LEFT JOIN machines m ON mt.machine_id = m.id
        LEFT JOIN departments d ON mt.department_id = d.id
        LEFT JOIN users reported ON mt.reported_by_id = reported.id
        LEFT JOIN users assigned ON mt.assigned_to_id = assigned.id
        WHERE 1=1
    """
    
    params = []
    if status:
        query += " AND mt.status = %s"
        params.append(status)
    
    if machine_id:
        query += " AND mt.machine_id = %s"
        params.append(machine_id)
    
    if department_id:
        query += " AND mt.department_id = %s"
        params.append(department_id)
    
    query += " ORDER BY mt.priority_order DESC, mt.created_at DESC"
    
    tickets = execute_query(query, tuple(params) if params else None, fetch_all=True)
    return success_response(tickets)

@maintenance_bp.route('/tickets/<int:id>', methods=['GET'])
@token_required
def get_maintenance_ticket(id):
    query = """
        SELECT mt.*, m.machine_name, m.machine_number, d.name as department_name,
               CONCAT(reported.first_name, ' ', reported.last_name) as reported_by_name,
               CONCAT(assigned.first_name, ' ', assigned.last_name) as assigned_to_name
        FROM maintenance_tickets mt
        LEFT JOIN machines m ON mt.machine_id = m.id
        LEFT JOIN departments d ON mt.department_id = d.id
        LEFT JOIN users reported ON mt.reported_by_id = reported.id
        LEFT JOIN users assigned ON mt.assigned_to_id = assigned.id
        WHERE mt.id = %s
    """
    ticket = execute_query(query, (id,), fetch_one=True)
    
    if not ticket:
        return error_response('Maintenance ticket not found', 404)
    
    return success_response(ticket)

@maintenance_bp.route('/tickets', methods=['POST'])
@token_required
def create_maintenance_ticket():
    data = request.get_json()
    user_id = request.current_user['user_id']
    
    required_fields = ['machine_id', 'department_id', 'issue_description']
    for field in required_fields:
        if not data.get(field):
            return error_response(f'{field} is required', 400)
    
    ticket_number = f"MAINT-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    query = """
        INSERT INTO maintenance_tickets
        (ticket_number, machine_id, department_id, issue_description, severity,
         reported_by_id, notes, config)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    try:
        ticket_id = execute_query(
            query,
            (
                ticket_number,
                data['machine_id'],
                data['department_id'],
                data['issue_description'],
                data.get('severity', 'medium'),
                user_id,
                data.get('notes'),
                data.get('config')
            ),
            commit=True
        )
        
        execute_query(
            "UPDATE machines SET status = 'maintenance' WHERE id = %s",
            (data['machine_id'],),
            commit=True
        )
        
        log_audit(user_id, 'CREATE', 'maintenance_ticket', ticket_id, None, data)
        
        return success_response({'id': ticket_id, 'ticket_number': ticket_number},
                              'Maintenance ticket created successfully', 201)
    except Exception as e:
        return error_response(str(e), 500)

@maintenance_bp.route('/tickets/<int:id>/assign', methods=['POST'])
@token_required
@permission_required('maintenance', 'assign')
def assign_maintenance_ticket(id):
    data = request.get_json()
    user_id = request.current_user['user_id']
    
    assigned_to = data.get('assigned_to_id')
    if not assigned_to:
        return error_response('assigned_to_id is required', 400)
    
    execute_query(
        """UPDATE maintenance_tickets 
           SET assigned_to_id = %s, status = 'assigned', 
               expected_start_time = %s, expected_completion_time = %s
           WHERE id = %s""",
        (assigned_to, data.get('expected_start_time'), 
         data.get('expected_completion_time'), id),
        commit=True
    )
    
    create_notification(
        assigned_to,
        'maintenance_assigned',
        'Maintenance Task Assigned',
        f'You have been assigned maintenance ticket #{id}',
        'maintenance_ticket',
        id,
        f'/maintenance/tickets/{id}',
        'normal'
    )
    
    log_audit(user_id, 'ASSIGN', 'maintenance_ticket', id, None, data)
    
    return success_response(message='Ticket assigned successfully')

@maintenance_bp.route('/tickets/<int:id>/status', methods=['PATCH'])
@token_required
def update_maintenance_status(id):
    data = request.get_json()
    user_id = request.current_user['user_id']
    
    status = data.get('status')
    if status not in ['open', 'assigned', 'in_progress', 'awaiting_parts', 'completed', 'cancelled']:
        return error_response('Invalid status', 400)
    
    update_data = {'status': status}
    
    if status == 'in_progress':
        update_data['actual_start_time'] = datetime.now()
    elif status == 'completed':
        update_data['actual_completion_time'] = datetime.now()
        update_data['work_performed'] = data.get('work_performed')
        update_data['parts_used'] = data.get('parts_used')
        
        ticket = execute_query(
            "SELECT machine_id FROM maintenance_tickets WHERE id = %s",
            (id,),
            fetch_one=True
        )
        
        if ticket:
            execute_query(
                "UPDATE machines SET status = 'available' WHERE id = %s",
                (ticket['machine_id'],),
                commit=True
            )
    
    set_clause = ', '.join([f"{k} = %s" for k in update_data.keys()])
    values = list(update_data.values()) + [id]
    
    execute_query(
        f"UPDATE maintenance_tickets SET {set_clause} WHERE id = %s",
        tuple(values),
        commit=True
    )
    
    log_audit(user_id, 'UPDATE_STATUS', 'maintenance_ticket', id, None, update_data)
    
    return success_response(message='Status updated successfully')

@maintenance_bp.route('/machine-history/<int:machine_id>', methods=['GET'])
@token_required
def get_machine_history(machine_id):
    query = """
        SELECT mt.*,
               CONCAT(reported.first_name, ' ', reported.last_name) as reported_by_name,
               CONCAT(assigned.first_name, ' ', assigned.last_name) as assigned_to_name
        FROM maintenance_tickets mt
        LEFT JOIN users reported ON mt.reported_by_id = reported.id
        LEFT JOIN users assigned ON mt.assigned_to_id = assigned.id
        WHERE mt.machine_id = %s
        ORDER BY mt.created_at DESC
    """
    
    history = execute_query(query, (machine_id,), fetch_all=True)
    return success_response(history)
