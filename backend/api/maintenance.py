from flask import Blueprint, request
from backend.config.database import execute_query
from backend.utils.auth import token_required, permission_required
from backend.utils.response import success_response, error_response
from backend.utils.audit import log_audit
from backend.utils.notifications import create_notification
from datetime import datetime, timedelta

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

@maintenance_bp.route('/analytics', methods=['GET'])
@token_required
def get_maintenance_analytics():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    department_id = request.args.get('department_id')
    machine_id = request.args.get('machine_id')
    
    if not start_date:
        start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')
    
    where_clause = "WHERE mt.created_at BETWEEN %s AND %s"
    params = [start_date, end_date]
    
    if department_id:
        where_clause += " AND mt.department_id = %s"
        params.append(department_id)
    
    if machine_id:
        where_clause += " AND mt.machine_id = %s"
        params.append(machine_id)
    
    ticket_stats_query = f"""
        SELECT 
            COUNT(*) as total_tickets,
            SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_tickets,
            SUM(CASE WHEN status IN ('open', 'assigned', 'in_progress', 'awaiting_parts') THEN 1 ELSE 0 END) as open_tickets,
            SUM(downtime_minutes) as total_downtime_minutes,
            AVG(CASE WHEN status = 'completed' 
                THEN TIMESTAMPDIFF(MINUTE, created_at, completed_at) END) as avg_resolution_time,
            SUM(CASE WHEN severity = 'critical' THEN 1 ELSE 0 END) as critical_tickets,
            SUM(CASE WHEN severity = 'high' THEN 1 ELSE 0 END) as high_priority_tickets
        FROM maintenance_tickets mt
        {where_clause}
    """
    
    stats = execute_query(ticket_stats_query, tuple(params), fetch_one=True)
    
    machine_breakdown_query = f"""
        SELECT 
            m.id, m.machine_name, m.machine_number,
            COUNT(mt.id) as ticket_count,
            SUM(mt.downtime_minutes) as total_downtime,
            AVG(CASE WHEN mt.status = 'completed' 
                THEN TIMESTAMPDIFF(MINUTE, mt.created_at, mt.completed_at) END) as avg_repair_time
        FROM machines m
        LEFT JOIN maintenance_tickets mt ON m.id = mt.machine_id
        {where_clause.replace('mt.created_at', 'mt.created_at')}
        GROUP BY m.id, m.machine_name, m.machine_number
        ORDER BY ticket_count DESC
        LIMIT 10
    """
    
    machine_breakdown = execute_query(machine_breakdown_query, tuple(params), fetch_all=True)
    
    severity_breakdown_query = f"""
        SELECT 
            severity,
            COUNT(*) as count,
            SUM(downtime_minutes) as total_downtime
        FROM maintenance_tickets mt
        {where_clause}
        GROUP BY severity
        ORDER BY count DESC
    """
    
    severity_breakdown = execute_query(severity_breakdown_query, tuple(params), fetch_all=True)
    
    monthly_trends_query = f"""
        SELECT 
            DATE_FORMAT(created_at, '%Y-%m') as month,
            COUNT(*) as ticket_count,
            SUM(downtime_minutes) as total_downtime,
            AVG(CASE WHEN status = 'completed' 
                THEN TIMESTAMPDIFF(MINUTE, created_at, completed_at) END) as avg_resolution_time
        FROM maintenance_tickets mt
        {where_clause}
        GROUP BY DATE_FORMAT(created_at, '%Y-%m')
        ORDER BY month ASC
    """
    
    monthly_trends = execute_query(monthly_trends_query, tuple(params), fetch_all=True)
    
    for machine in machine_breakdown:
        machine['mtbf'] = 0
        machine['mttr'] = machine.get('avg_repair_time') or 0
        
        if machine['ticket_count'] and machine['ticket_count'] > 0:
            days_in_period = (datetime.strptime(end_date, '%Y-%m-%d') - datetime.strptime(start_date, '%Y-%m-%d')).days
            if days_in_period > 0:
                machine['mtbf'] = round(days_in_period * 24 / machine['ticket_count'], 2)
    
    return success_response({
        'summary': {
            'total_tickets': stats.get('total_tickets') or 0,
            'completed_tickets': stats.get('completed_tickets') or 0,
            'open_tickets': stats.get('open_tickets') or 0,
            'total_downtime_hours': round((stats.get('total_downtime_minutes') or 0) / 60, 2),
            'avg_resolution_time_hours': round((stats.get('avg_resolution_time') or 0) / 60, 2),
            'critical_tickets': stats.get('critical_tickets') or 0,
            'high_priority_tickets': stats.get('high_priority_tickets') or 0
        },
        'machine_breakdown': machine_breakdown,
        'severity_breakdown': severity_breakdown,
        'monthly_trends': monthly_trends,
        'date_range': {'start_date': start_date, 'end_date': end_date}
    })
