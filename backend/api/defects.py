from flask import Blueprint, request
from backend.config.database import execute_query
from backend.utils.auth import token_required, permission_required
from backend.utils.response import success_response, error_response
from backend.utils.audit import log_audit
from backend.utils.notifications import create_notification
from backend.utils.email_sender import send_email
from datetime import datetime, timedelta
import os

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
    
    order_item_id = data.get('order_item_id')
    product_id = data.get('product_id')
    
    if order_item_id:
        item = execute_query(
            "SELECT product_id FROM order_items WHERE id = %s AND order_id = %s",
            (order_item_id, data['order_id']),
            fetch_one=True
        )
        if not item:
            return error_response('Order item not found', 404)
        product_id = item['product_id']
    
    query = """
        INSERT INTO replacement_tickets
        (ticket_number, order_id, product_id, order_item_id, quantity_rejected, department_id,
         stage_id, rejection_reason, rejection_type, created_by_id, notes, config)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    try:
        ticket_id = execute_query(
            query,
            (
                ticket_number,
                data['order_id'],
                product_id,
                order_item_id,
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
        
        material_cost = calculate_defect_cost(product_id, data['quantity_rejected'])
        
        if material_cost > 0:
            update_query = """
                UPDATE replacement_tickets 
                SET material_cost = %s, cost_impact = %s
                WHERE id = %s
            """
            execute_query(update_query, (material_cost, material_cost, ticket_id), commit=True)
        
        dept_manager_query = "SELECT manager_id FROM departments WHERE id = %s"
        dept = execute_query(dept_manager_query, (data['department_id'],), fetch_one=True)
        
        if dept and dept['manager_id']:
            create_notification(
                dept['manager_id'],
                'replacement_ticket',
                'New Replacement Ticket',
                f'A new replacement ticket {ticket_number} requires your approval (Material Cost: R{material_cost:.2f})',
                'replacement_ticket',
                ticket_id,
                f'/defects/replacement-tickets/{ticket_id}',
                'high'
            )
        
        log_audit(user_id, 'CREATE', 'replacement_ticket', ticket_id, None, data)
        
        return success_response({
            'id': ticket_id, 
            'ticket_number': ticket_number,
            'material_cost': material_cost
        }, 'Replacement ticket created successfully', 201)
    except Exception as e:
        return error_response(str(e), 500)


def calculate_defect_cost(product_id, quantity):
    """Calculate material cost impact from BOM for given product and quantity"""
    if not product_id or not quantity:
        return 0.0
    
    bom_query = """
        SELECT SUM(bi.total_cost) as unit_cost
        FROM bom b
        JOIN bom_items bi ON b.id = bi.bom_id
        WHERE b.product_id = %s AND b.is_active = TRUE
        GROUP BY b.id
        ORDER BY b.effective_date DESC
        LIMIT 1
    """
    
    bom_result = execute_query(bom_query, (product_id,), fetch_one=True)
    
    if bom_result and bom_result['unit_cost']:
        return float(bom_result['unit_cost']) * float(quantity)
    
    return 0.0

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
            """SELECT rt.id, rt.ticket_number, rt.order_id, rt.department_id,
                      o.order_number, o.customer_name, p.product_name, rt.quantity_rejected
               FROM replacement_tickets rt
               LEFT JOIN orders o ON rt.order_id = o.id
               LEFT JOIN products p ON rt.product_id = p.id
               WHERE rt.id = %s""",
            (id,),
            fetch_one=True
        )
        
        if ticket:
            execute_query(
                "UPDATE orders SET status = 'on_hold', hold_reason = 'No stock for replacement' WHERE id = %s",
                (ticket['order_id'],),
                commit=True
            )
            
            dept_managers = execute_query(
                """SELECT d.manager_id, u.email as manager_email, u.first_name, u.last_name,
                          pm.id as planning_manager_id, pm.email as planning_manager_email,
                          hod.id as hod_id, hod.email as hod_email
                   FROM departments d
                   LEFT JOIN users u ON d.manager_id = u.id
                   LEFT JOIN roles r ON r.name = 'Planning Manager'
                   LEFT JOIN users pm ON pm.role_id = r.id
                   LEFT JOIN roles hr ON hr.name = 'HOD'
                   LEFT JOIN users hod ON hod.role_id = hr.id
                   WHERE d.id = %s""",
                (ticket['department_id'],),
                fetch_one=True
            )
            
            email_body = f"""
            <h2>No Stock Alert - Urgent Action Required</h2>
            <p><strong>Replacement Ticket:</strong> {ticket['ticket_number']}</p>
            <p><strong>Order Number:</strong> {ticket['order_number']}</p>
            <p><strong>Customer:</strong> {ticket['customer_name']}</p>
            <p><strong>Product:</strong> {ticket['product_name']}</p>
            <p><strong>Quantity Rejected:</strong> {ticket['quantity_rejected']}</p>
            <hr>
            <p style="color: red;"><strong>Status:</strong> No Stock Available for Replacement</p>
            <p>The order has been automatically placed on hold. Please take immediate action to resolve this stock issue.</p>
            <p><a href="{os.getenv('APP_URL', 'http://localhost:5000')}/defects/replacement-tickets/{id}">View Ticket Details</a></p>
            """
            
            recipients_to_notify = []
            
            if dept_managers and dept_managers['manager_id']:
                create_notification(
                    dept_managers['manager_id'],
                    'no_stock_alert',
                    'No Stock Alert - Urgent',
                    f'Replacement ticket {ticket["ticket_number"]} marked as no stock - Order {ticket["order_number"]} placed on hold',
                    'replacement_ticket',
                    ticket['order_id'],
                    priority='urgent'
                )
                if dept_managers['manager_email']:
                    recipients_to_notify.append(dept_managers['manager_email'])
                    execute_query(
                        "INSERT INTO defect_notifications (replacement_ticket_id, notification_type, recipient_id) VALUES (%s, %s, %s)",
                        (id, 'no_stock_manager', dept_managers['manager_id']),
                        commit=True
                    )
            
            if dept_managers and dept_managers['planning_manager_id']:
                create_notification(
                    dept_managers['planning_manager_id'],
                    'no_stock_alert',
                    'No Stock Alert - Planning Action Required',
                    f'Replacement ticket {ticket["ticket_number"]} marked as no stock',
                    'replacement_ticket',
                    ticket['order_id'],
                    priority='urgent'
                )
                if dept_managers['planning_manager_email']:
                    recipients_to_notify.append(dept_managers['planning_manager_email'])
                    execute_query(
                        "INSERT INTO defect_notifications (replacement_ticket_id, notification_type, recipient_id) VALUES (%s, %s, %s)",
                        (id, 'no_stock_planning_manager', dept_managers['planning_manager_id']),
                        commit=True
                    )
            
            if dept_managers and dept_managers['hod_id']:
                create_notification(
                    dept_managers['hod_id'],
                    'no_stock_alert',
                    'No Stock Alert - HOD Escalation',
                    f'Replacement ticket {ticket["ticket_number"]} marked as no stock - Order on hold',
                    'replacement_ticket',
                    ticket['order_id'],
                    priority='urgent'
                )
                if dept_managers['hod_email']:
                    recipients_to_notify.append(dept_managers['hod_email'])
                    execute_query(
                        "INSERT INTO defect_notifications (replacement_ticket_id, notification_type, recipient_id) VALUES (%s, %s, %s)",
                        (id, 'no_stock_hod', dept_managers['hod_id']),
                        commit=True
                    )
            
            if recipients_to_notify:
                try:
                    send_email(
                        to_emails=recipients_to_notify,
                        subject=f'URGENT: No Stock Alert - Order {ticket["order_number"]} On Hold',
                        body=email_body
                    )
                except Exception as email_error:
                    app_logger = __import__('backend.utils.logger', fromlist=['app_logger']).app_logger
                    app_logger.error(f"Failed to send no-stock email notification: {str(email_error)}")
    
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
    
    order_item_id = data.get('order_item_id')
    product_id = data.get('product_id')
    
    if order_item_id:
        item = execute_query(
            "SELECT product_id FROM order_items WHERE id = %s AND order_id = %s",
            (order_item_id, data['order_id']),
            fetch_one=True
        )
        if not item:
            return error_response('Order item not found', 404)
        product_id = item['product_id']
    
    query = """
        INSERT INTO customer_returns
        (return_number, order_id, product_id, order_item_id, quantity_returned, return_reason,
         customer_complaint, return_date, return_type, recorded_by_id, notes, config)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    try:
        return_id = execute_query(
            query,
            (
                return_number,
                data['order_id'],
                product_id,
                order_item_id,
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
        
        material_cost = calculate_defect_cost(product_id, data['quantity_returned'])
        
        if material_cost > 0:
            update_query = """
                UPDATE customer_returns 
                SET material_cost = %s, cost_impact = %s
                WHERE id = %s
            """
            execute_query(update_query, (material_cost, material_cost, return_id), commit=True)
        
        log_audit(user_id, 'CREATE', 'customer_return', return_id, None, data)
        
        return success_response({
            'id': return_id, 
            'return_number': return_number,
            'material_cost': material_cost
        }, 'Customer return recorded successfully', 201)
    except Exception as e:
        return error_response(str(e), 500)

@defects_bp.route('/cost-analysis', methods=['GET'])
@token_required
@permission_required('finance', 'read')
def get_cost_analysis():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    department_id = request.args.get('department_id')
    
    if not start_date:
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')
    
    query = """
        SELECT 
            d.id as department_id,
            d.name as department_name,
            COUNT(rt.id) as total_defects,
            SUM(rt.quantity_rejected) as total_quantity_rejected,
            SUM(rt.material_cost) as total_material_cost,
            SUM(rt.cost_impact) as total_cost_impact
        FROM departments d
        LEFT JOIN replacement_tickets rt ON d.id = rt.department_id
            AND rt.created_at BETWEEN %s AND %s
        WHERE d.is_active = TRUE
    """
    
    params = [start_date, end_date]
    
    if department_id:
        query += " AND d.id = %s"
        params.append(department_id)
    
    query += """
        GROUP BY d.id, d.name
        ORDER BY total_cost_impact DESC
    """
    
    department_costs = execute_query(query, tuple(params), fetch_all=True)
    
    top_defects_query = """
        SELECT 
            rt.rejection_reason,
            COUNT(*) as defect_count,
            SUM(rt.quantity_rejected) as total_quantity,
            SUM(rt.cost_impact) as total_cost
        FROM replacement_tickets rt
        WHERE rt.created_at BETWEEN %s AND %s
    """
    
    defect_params = [start_date, end_date]
    
    if department_id:
        top_defects_query += " AND rt.department_id = %s"
        defect_params.append(department_id)
    
    top_defects_query += """
        GROUP BY rt.rejection_reason
        ORDER BY total_cost DESC
        LIMIT 10
    """
    
    top_defects = execute_query(top_defects_query, tuple(defect_params), fetch_all=True)
    
    monthly_trend_query = """
        SELECT 
            DATE_FORMAT(rt.created_at, '%Y-%m') as month,
            COUNT(*) as defect_count,
            SUM(rt.material_cost) as material_cost,
            SUM(rt.cost_impact) as total_cost
        FROM replacement_tickets rt
        WHERE rt.created_at BETWEEN %s AND %s
    """
    
    trend_params = [start_date, end_date]
    
    if department_id:
        monthly_trend_query += " AND rt.department_id = %s"
        trend_params.append(department_id)
    
    monthly_trend_query += """
        GROUP BY DATE_FORMAT(rt.created_at, '%Y-%m')
        ORDER BY month ASC
    """
    
    monthly_trends = execute_query(monthly_trend_query, tuple(trend_params), fetch_all=True)
    
    total_costs = {
        'total_material_cost': sum(float(d.get('total_material_cost') or 0) for d in department_costs),
        'total_cost_impact': sum(float(d.get('total_cost_impact') or 0) for d in department_costs),
        'total_defects': sum(int(d.get('total_defects') or 0) for d in department_costs),
        'total_quantity_rejected': sum(int(d.get('total_quantity_rejected') or 0) for d in department_costs)
    }
    
    return success_response({
        'summary': total_costs,
        'department_costs': department_costs,
        'top_defects': top_defects,
        'monthly_trends': monthly_trends,
        'date_range': {'start_date': start_date, 'end_date': end_date}
    })
