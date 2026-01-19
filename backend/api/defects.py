from flask import Blueprint, request
from backend.config.database import execute_query
from backend.utils.auth import token_required, permission_required
from backend.utils.response import success_response, error_response
from backend.utils.audit import log_audit
from backend.utils.notifications import create_notification
from datetime import datetime

defects_bp = Blueprint('defects', __name__, url_prefix='/api/defects')

@defects_bp.route('/replacement-tickets', methods=['GET'])
@token_required
def get_replacement_tickets():
    status = request.args.get('status')
    department_id = request.args.get('department_id')
    
    query = """
        SELECT rt.*, o.order_number, o.customer_name,
               p.product_name, d.name as department_name,
               CONCAT(created.first_name, ' ', created.last_name) as created_by_name,
               CONCAT(approved.first_name, ' ', approved.last_name) as approved_by_name
        FROM replacement_tickets rt
        LEFT JOIN orders o ON rt.order_id = o.id
        LEFT JOIN products p ON rt.product_id = p.id
        LEFT JOIN departments d ON rt.department_id = d.id
        LEFT JOIN users created ON rt.created_by_id = created.id
        LEFT JOIN users approved ON rt.approved_by_id = approved.id
        WHERE 1=1
    """
    
    params = []
    if status:
        query += " AND rt.status = %s"
        params.append(status)
    
    if department_id:
        query += " AND rt.department_id = %s"
        params.append(department_id)
    
    query += " ORDER BY rt.created_at DESC"
    
    tickets = execute_query(query, tuple(params) if params else None, fetch_all=True)
    return success_response(tickets)

@defects_bp.route('/replacement-tickets', methods=['POST'])
@token_required
def create_replacement_ticket():
    data = request.get_json()
    user_id = request.current_user['user_id']
    
    required_fields = ['order_id', 'quantity_rejected', 'department_id', 'rejection_reason', 'rejection_type']
    for field in required_fields:
        if not data.get(field):
            return error_response(f'{field} is required', 400)
    
    ticket_number = f"RT-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    query = """
        INSERT INTO replacement_tickets
        (ticket_number, order_id, product_id, quantity_rejected, department_id,
         stage_id, rejection_reason, rejection_type, created_by_id, notes, config)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    try:
        ticket_id = execute_query(
            query,
            (
                ticket_number,
                data['order_id'],
                data.get('product_id'),
                data['quantity_rejected'],
                data['department_id'],
                data.get('stage_id'),
                data['rejection_reason'],
                data['rejection_type'],
                user_id,
                data.get('notes'),
                data.get('config')
            ),
            commit=True
        )
        
        dept_manager_query = "SELECT manager_id FROM departments WHERE id = %s"
        dept = execute_query(dept_manager_query, (data['department_id'],), fetch_one=True)
        
        if dept and dept['manager_id']:
            create_notification(
                dept['manager_id'],
                'replacement_ticket',
                'New Replacement Ticket',
                f'A new replacement ticket {ticket_number} requires your approval',
                'replacement_ticket',
                ticket_id,
                f'/defects/replacement-tickets/{ticket_id}',
                'high'
            )
        
        log_audit(user_id, 'CREATE', 'replacement_ticket', ticket_id, None, data)
        
        return success_response({'id': ticket_id, 'ticket_number': ticket_number}, 
                              'Replacement ticket created successfully', 201)
    except Exception as e:
        return error_response(str(e), 500)

@defects_bp.route('/replacement-tickets/<int:id>/approve', methods=['POST'])
@token_required
@permission_required('department', 'approve')
def approve_replacement_ticket(id):
    user_id = request.current_user['user_id']
    
    query = """
        UPDATE replacement_tickets
        SET status = 'approved', approved_by_id = %s, approved_at = NOW()
        WHERE id = %s AND status = 'pending_approval'
    """
    
    execute_query(query, (user_id, id), commit=True)
    log_audit(user_id, 'APPROVE', 'replacement_ticket', id)
    
    return success_response(message='Replacement ticket approved')

@defects_bp.route('/replacement-tickets/<int:id>/status', methods=['PATCH'])
@token_required
@permission_required('planning', 'write')
def update_replacement_ticket_status(id):
    data = request.get_json()
    user_id = request.current_user['user_id']
    
    status = data.get('status')
    if status not in ['replacement_processed', 'no_stock']:
        return error_response('Invalid status', 400)
    
    execute_query(
        "UPDATE replacement_tickets SET status = %s WHERE id = %s",
        (status, id),
        commit=True
    )
    
    if status == 'no_stock':
        ticket = execute_query(
            "SELECT order_id, department_id FROM replacement_tickets WHERE id = %s",
            (id,),
            fetch_one=True
        )
        
        if ticket:
            execute_query(
                "UPDATE orders SET status = 'on_hold', hold_reason = 'No stock for replacement' WHERE id = %s",
                (ticket['order_id'],),
                commit=True
            )
            
            dept = execute_query(
                "SELECT manager_id FROM departments WHERE id = %s",
                (ticket['department_id'],),
                fetch_one=True
            )
            
            if dept and dept['manager_id']:
                create_notification(
                    dept['manager_id'],
                    'no_stock_alert',
                    'No Stock Alert',
                    f'Replacement ticket #{id} marked as no stock - order placed on hold',
                    'order',
                    ticket['order_id'],
                    priority='urgent'
                )
    
    log_audit(user_id, 'UPDATE_STATUS', 'replacement_ticket', id, None, {'status': status})
    
    return success_response(message='Status updated successfully')

@defects_bp.route('/customer-returns', methods=['GET'])
@token_required
def get_customer_returns():
    return_type = request.args.get('return_type')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    query = """
        SELECT cr.*, o.order_number, o.customer_name, p.product_name,
               CONCAT(u.first_name, ' ', u.last_name) as recorded_by_name
        FROM customer_returns cr
        LEFT JOIN orders o ON cr.order_id = o.id
        LEFT JOIN products p ON cr.product_id = p.id
        LEFT JOIN users u ON cr.recorded_by_id = u.id
        WHERE 1=1
    """
    
    params = []
    if return_type:
        query += " AND cr.return_type = %s"
        params.append(return_type)
    
    if start_date:
        query += " AND cr.return_date >= %s"
        params.append(start_date)
    
    if end_date:
        query += " AND cr.return_date <= %s"
        params.append(end_date)
    
    query += " ORDER BY cr.return_date DESC"
    
    returns = execute_query(query, tuple(params) if params else None, fetch_all=True)
    return success_response(returns)

@defects_bp.route('/customer-returns', methods=['POST'])
@token_required
@permission_required('qc', 'write')
def create_customer_return():
    data = request.get_json()
    user_id = request.current_user['user_id']
    
    required_fields = ['order_id', 'quantity_returned', 'return_reason', 'return_date', 'return_type']
    for field in required_fields:
        if not data.get(field):
            return error_response(f'{field} is required', 400)
    
    return_number = f"CR-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    query = """
        INSERT INTO customer_returns
        (return_number, order_id, product_id, quantity_returned, return_reason,
         customer_complaint, return_date, return_type, recorded_by_id, notes, config)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    try:
        return_id = execute_query(
            query,
            (
                return_number,
                data['order_id'],
                data.get('product_id'),
                data['quantity_returned'],
                data['return_reason'],
                data.get('customer_complaint'),
                data['return_date'],
                data['return_type'],
                user_id,
                data.get('notes'),
                data.get('config')
            ),
            commit=True
        )
        
        log_audit(user_id, 'CREATE', 'customer_return', return_id, None, data)
        
        return success_response({'id': return_id, 'return_number': return_number},
                              'Customer return recorded successfully', 201)
    except Exception as e:
        return error_response(str(e), 500)
