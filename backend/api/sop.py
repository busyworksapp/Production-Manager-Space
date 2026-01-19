from flask import Blueprint, request
from backend.config.database import execute_query
from backend.utils.auth import token_required, permission_required
from backend.utils.response import success_response, error_response
from backend.utils.audit import log_audit
from backend.utils.notifications import create_notification
from datetime import datetime

sop_bp = Blueprint('sop', __name__, url_prefix='/api/sop')

@sop_bp.route('/tickets', methods=['GET'])
@token_required
def get_sop_tickets():
    status = request.args.get('status')
    department_id = request.args.get('department_id')
    
    query = """
        SELECT st.*,
               charging_dept.name as charging_department_name,
               charged_dept.name as charged_department_name,
               CONCAT(created.first_name, ' ', created.last_name) as created_by_name,
               CONCAT(assigned.first_name, ' ', assigned.last_name) as assigned_to_name
        FROM sop_failure_tickets st
        LEFT JOIN departments charging_dept ON st.charging_department_id = charging_dept.id
        LEFT JOIN departments charged_dept ON st.charged_department_id = charged_dept.id
        LEFT JOIN users created ON st.created_by_id = created.id
        LEFT JOIN users assigned ON st.assigned_to_id = assigned.id
        WHERE 1=1
    """
    
    params = []
    if status:
        query += " AND st.status = %s"
        params.append(status)
    
    if department_id:
        query += " AND (st.charging_department_id = %s OR st.charged_department_id = %s)"
        params.extend([department_id, department_id])
    
    query += " ORDER BY st.created_at DESC"
    
    tickets = execute_query(query, tuple(params) if params else None, fetch_all=True)
    return success_response(tickets)

@sop_bp.route('/tickets/<int:id>', methods=['GET'])
@token_required
def get_sop_ticket(id):
    query = """
        SELECT st.*,
               charging_dept.name as charging_department_name,
               charged_dept.name as charged_department_name,
               CONCAT(created.first_name, ' ', created.last_name) as created_by_name
        FROM sop_failure_tickets st
        LEFT JOIN departments charging_dept ON st.charging_department_id = charging_dept.id
        LEFT JOIN departments charged_dept ON st.charged_department_id = charged_dept.id
        LEFT JOIN users created ON st.created_by_id = created.id
        WHERE st.id = %s
    """
    ticket = execute_query(query, (id,), fetch_one=True)
    
    if not ticket:
        return error_response('SOP ticket not found', 404)
    
    ncr_query = """
        SELECT ncr.*,
               CONCAT(responsible.first_name, ' ', responsible.last_name) as responsible_person_name,
               CONCAT(completed.first_name, ' ', completed.last_name) as completed_by_name
        FROM ncr_reports ncr
        LEFT JOIN users responsible ON ncr.responsible_person_id = responsible.id
        LEFT JOIN users completed ON ncr.completed_by_id = completed.id
        WHERE ncr.sop_ticket_id = %s
    """
    ncr = execute_query(ncr_query, (id,), fetch_one=True)
    ticket['ncr'] = ncr
    
    return success_response(ticket)

@sop_bp.route('/tickets', methods=['POST'])
@token_required
def create_sop_ticket():
    data = request.get_json()
    user_id = request.current_user['user_id']
    
    required_fields = ['sop_reference', 'failure_description', 'charging_department_id', 'charged_department_id']
    for field in required_fields:
        if not data.get(field):
            return error_response(f'{field} is required', 400)
    
    ticket_number = f"SOP-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    query = """
        INSERT INTO sop_failure_tickets
        (ticket_number, sop_reference, failure_description, impact_description,
         charging_department_id, charged_department_id, original_charged_department_id,
         created_by_id, notes, config)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    try:
        ticket_id = execute_query(
            query,
            (
                ticket_number,
                data['sop_reference'],
                data['failure_description'],
                data.get('impact_description'),
                data['charging_department_id'],
                data['charged_department_id'],
                data['charged_department_id'],
                user_id,
                data.get('notes'),
                data.get('config')
            ),
            commit=True
        )
        
        dept = execute_query(
            "SELECT manager_id FROM departments WHERE id = %s",
            (data['charged_department_id'],),
            fetch_one=True
        )
        
        if dept and dept['manager_id']:
            create_notification(
                dept['manager_id'],
                'sop_failure',
                'SOP Failure Charged',
                f'Your department has been charged with SOP failure {ticket_number}',
                'sop_ticket',
                ticket_id,
                f'/sop/tickets/{ticket_id}',
                'high'
            )
        
        log_audit(user_id, 'CREATE', 'sop_ticket', ticket_id, None, data)
        
        return success_response({'id': ticket_id, 'ticket_number': ticket_number},
                              'SOP ticket created successfully', 201)
    except Exception as e:
        return error_response(str(e), 500)

@sop_bp.route('/tickets/<int:id>/reassign', methods=['POST'])
@token_required
def reassign_sop_ticket(id):
    data = request.get_json()
    user_id = request.current_user['user_id']
    
    new_dept_id = data.get('new_department_id')
    reason = data.get('reason')
    
    if not new_dept_id or not reason:
        return error_response('New department and reason are required', 400)
    
    ticket = execute_query(
        "SELECT charged_department_id, original_charged_department_id FROM sop_failure_tickets WHERE id = %s",
        (id,),
        fetch_one=True
    )
    
    if ticket['charged_department_id'] != ticket['original_charged_department_id']:
        return error_response('Ticket has already been reassigned once and cannot be reassigned again', 400)
    
    execute_query(
        """UPDATE sop_failure_tickets 
           SET charged_department_id = %s, status = 'reassigned', reassignment_reason = %s
           WHERE id = %s""",
        (new_dept_id, reason, id),
        commit=True
    )
    
    dept = execute_query(
        "SELECT manager_id FROM departments WHERE id = %s",
        (new_dept_id,),
        fetch_one=True
    )
    
    if dept and dept['manager_id']:
        create_notification(
            dept['manager_id'],
            'sop_reassigned',
            'SOP Ticket Reassigned',
            f'SOP ticket #{id} has been reassigned to your department',
            'sop_ticket',
            id,
            priority='high'
        )
    
    log_audit(user_id, 'REASSIGN', 'sop_ticket', id, None, {'new_department_id': new_dept_id, 'reason': reason})
    
    return success_response(message='SOP ticket reassigned successfully')

@sop_bp.route('/tickets/<int:id>/reject', methods=['POST'])
@token_required
def reject_sop_ticket(id):
    data = request.get_json()
    user_id = request.current_user['user_id']
    
    reason = data.get('reason')
    if not reason:
        return error_response('Rejection reason is required', 400)
    
    execute_query(
        """UPDATE sop_failure_tickets 
           SET status = 'rejected', rejection_reason = %s, escalated_to_hod = TRUE
           WHERE id = %s""",
        (reason, id),
        commit=True
    )
    
    log_audit(user_id, 'REJECT', 'sop_ticket', id, None, {'reason': reason})
    
    return success_response(message='SOP ticket rejected and escalated to HOD')

@sop_bp.route('/tickets/<int:id>/ncr', methods=['POST'])
@token_required
def create_ncr(id):
    data = request.get_json()
    user_id = request.current_user['user_id']
    
    required_fields = ['root_cause_analysis', 'corrective_actions', 'preventive_measures']
    for field in required_fields:
        if not data.get(field):
            return error_response(f'{field} is required', 400)
    
    query = """
        INSERT INTO ncr_reports
        (sop_ticket_id, root_cause_analysis, corrective_actions, preventive_measures,
         responsible_person_id, target_completion_date, completed_by_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    
    try:
        ncr_id = execute_query(
            query,
            (
                id,
                data['root_cause_analysis'],
                data['corrective_actions'],
                data['preventive_measures'],
                data.get('responsible_person_id'),
                data.get('target_completion_date'),
                user_id
            ),
            commit=True
        )
        
        execute_query(
            """UPDATE sop_failure_tickets 
               SET status = 'ncr_completed', ncr_completed_at = NOW(), closed_at = NOW()
               WHERE id = %s""",
            (id,),
            commit=True
        )
        
        log_audit(user_id, 'CREATE_NCR', 'sop_ticket', id, None, data)
        
        return success_response({'id': ncr_id}, 'NCR completed and ticket closed', 201)
    except Exception as e:
        return error_response(str(e), 500)
