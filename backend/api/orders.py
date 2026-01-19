from flask import Blueprint, request
from backend.config.database import execute_query
from backend.utils.auth import token_required, permission_required
from backend.utils.response import success_response, error_response
from backend.utils.audit import log_audit
import pandas as pd
from datetime import datetime

orders_bp = Blueprint('orders', __name__, url_prefix='/api/orders')

@orders_bp.route('', methods=['GET'])
@token_required
def get_orders():
    status = request.args.get('status')
    customer = request.args.get('customer')
    
    query = """
        SELECT o.*, p.product_name
        FROM orders o
        LEFT JOIN products p ON o.product_id = p.id
        WHERE 1=1
    """
    
    params = []
    if status:
        query += " AND o.status = %s"
        params.append(status)
    
    if customer:
        query += " AND o.customer_name LIKE %s"
        params.append(f'%{customer}%')
    
    query += " ORDER BY o.created_at DESC"
    
    orders = execute_query(query, tuple(params) if params else None, fetch_all=True)
    return success_response(orders)

@orders_bp.route('/<int:id>', methods=['GET'])
@token_required
def get_order(id):
    query = """
        SELECT o.*, p.product_name
        FROM orders o
        LEFT JOIN products p ON o.product_id = p.id
        WHERE o.id = %s
    """
    order = execute_query(query, (id,), fetch_one=True)
    
    if not order:
        return error_response('Order not found', 404)
    
    schedules_query = """
        SELECT js.*, d.name as department_name, ps.stage_name,
               m.machine_name, CONCAT(e.first_name, ' ', e.last_name) as employee_name
        FROM job_schedules js
        LEFT JOIN departments d ON js.department_id = d.id
        LEFT JOIN production_stages ps ON js.stage_id = ps.id
        LEFT JOIN machines m ON js.machine_id = m.id
        LEFT JOIN employees e ON js.assigned_employee_id = e.id
        WHERE js.order_id = %s
        ORDER BY js.scheduled_date, d.name
    """
    schedules = execute_query(schedules_query, (id,), fetch_all=True)
    order['schedules'] = schedules
    
    return success_response(order)

@orders_bp.route('', methods=['POST'])
@token_required
@permission_required('planning', 'write')
def create_order():
    data = request.get_json()
    user_id = request.current_user['user_id']
    
    required_fields = ['order_number', 'customer_name', 'quantity']
    for field in required_fields:
        if not data.get(field):
            return error_response(f'{field} is required', 400)
    
    query = """
        INSERT INTO orders
        (order_number, sales_order_number, customer_name, product_id,
         quantity, order_value, start_date, end_date, priority, status, notes, config)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    try:
        order_id = execute_query(
            query,
            (
                data['order_number'],
                data.get('sales_order_number'),
                data['customer_name'],
                data.get('product_id'),
                data['quantity'],
                data.get('order_value'),
                data.get('start_date'),
                data.get('end_date'),
                data.get('priority', 'normal'),
                data.get('status', 'unscheduled'),
                data.get('notes'),
                data.get('config')
            ),
            commit=True
        )
        
        log_audit(user_id, 'CREATE', 'order', order_id, None, data)
        
        return success_response({'id': order_id}, 'Order created successfully', 201)
    except Exception as e:
        return error_response(str(e), 500)

@orders_bp.route('/<int:id>', methods=['PUT'])
@token_required
@permission_required('planning', 'write')
def update_order(id):
    data = request.get_json()
    user_id = request.current_user['user_id']
    
    old_data = execute_query("SELECT * FROM orders WHERE id = %s", (id,), fetch_one=True)
    if not old_data:
        return error_response('Order not found', 404)
    
    query = """
        UPDATE orders SET
            order_number = %s, sales_order_number = %s, customer_name = %s,
            product_id = %s, quantity = %s, order_value = %s,
            start_date = %s, end_date = %s, priority = %s, status = %s,
            hold_reason = %s, notes = %s, config = %s
        WHERE id = %s
    """
    
    try:
        execute_query(
            query,
            (
                data.get('order_number', old_data['order_number']),
                data.get('sales_order_number', old_data['sales_order_number']),
                data.get('customer_name', old_data['customer_name']),
                data.get('product_id', old_data['product_id']),
                data.get('quantity', old_data['quantity']),
                data.get('order_value', old_data['order_value']),
                data.get('start_date', old_data['start_date']),
                data.get('end_date', old_data['end_date']),
                data.get('priority', old_data['priority']),
                data.get('status', old_data['status']),
                data.get('hold_reason', old_data['hold_reason']),
                data.get('notes', old_data['notes']),
                data.get('config', old_data['config']),
                id
            ),
            commit=True
        )
        
        log_audit(user_id, 'UPDATE', 'order', id, old_data, data)
        
        return success_response(message='Order updated successfully')
    except Exception as e:
        return error_response(str(e), 500)

@orders_bp.route('/import/preview', methods=['POST'])
@token_required
@permission_required('planning', 'write')
def preview_import():
    if 'file' not in request.files:
        return error_response('No file provided', 400)
    
    file = request.files['file']
    
    try:
        df = pd.read_excel(file)
        
        columns = df.columns.tolist()
        preview_data = df.head(5).to_dict('records')
        
        return success_response({
            'columns': columns,
            'preview': preview_data,
            'total_rows': len(df)
        })
    except Exception as e:
        return error_response(f'Failed to read file: {str(e)}', 500)

@orders_bp.route('/import', methods=['POST'])
@token_required
@permission_required('planning', 'write')
def import_orders():
    user_id = request.current_user['user_id']
    
    if 'file' not in request.files:
        return error_response('No file provided', 400)
    
    file = request.files['file']
    mapping = request.form.get('mapping')
    
    if mapping:
        import json
        mapping = json.loads(mapping)
    else:
        mapping = {
            'order_number': 'order_number',
            'sales_order_number': 'sales_order_number',
            'customer_name': 'customer_name',
            'product_id': 'product_id',
            'quantity': 'quantity',
            'order_value': 'order_value',
            'start_date': 'start_date',
            'end_date': 'end_date',
            'priority': 'priority'
        }
    
    try:
        df = pd.read_excel(file)
        imported_count = 0
        failed_rows = []
        
        for idx, row in df.iterrows():
            try:
                order_data = {}
                for db_field, excel_col in mapping.items():
                    if excel_col and excel_col in df.columns:
                        order_data[db_field] = row.get(excel_col)
                
                query = """
                    INSERT INTO orders
                    (order_number, sales_order_number, customer_name, product_id,
                     quantity, order_value, start_date, end_date, priority, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'unscheduled')
                """
                
                execute_query(
                    query,
                    (
                        order_data.get('order_number'),
                        order_data.get('sales_order_number'),
                        order_data.get('customer_name'),
                        order_data.get('product_id'),
                        order_data.get('quantity'),
                        order_data.get('order_value'),
                        order_data.get('start_date'),
                        order_data.get('end_date'),
                        order_data.get('priority', 'normal')
                    ),
                    commit=True
                )
                imported_count += 1
            except Exception as row_error:
                failed_rows.append({'row': idx + 1, 'error': str(row_error)})
        
        log_audit(user_id, 'IMPORT', 'orders', None, None, {
            'count': imported_count,
            'failed': len(failed_rows)
        })
        
        return success_response({
            'imported_count': imported_count,
            'failed_count': len(failed_rows),
            'failed_rows': failed_rows[:10]
        }, f'Successfully imported {imported_count} orders')
    except Exception as e:
        return error_response(f'Import failed: {str(e)}', 500)

@orders_bp.route('/<int:id>/schedule', methods=['POST'])
@token_required
@permission_required('planning', 'schedule')
def schedule_order(id):
    data = request.get_json()
    user_id = request.current_user['user_id']
    
    required_fields = ['department_id', 'scheduled_date', 'scheduled_quantity']
    for field in required_fields:
        if not data.get(field):
            return error_response(f'{field} is required', 400)
    
    if data.get('machine_id'):
        machine = execute_query(
            "SELECT status FROM machines WHERE id = %s",
            (data['machine_id'],),
            fetch_one=True
        )
        
        if not machine:
            return error_response('Machine not found', 404)
        
        if machine['status'] in ['maintenance', 'broken', 'retired']:
            return error_response(f'Machine is not available - current status: {machine["status"]}', 400)
        
        conflicting_jobs = execute_query(
            """SELECT COUNT(*) as count FROM job_schedules 
               WHERE machine_id = %s 
               AND scheduled_date = %s 
               AND status IN ('scheduled', 'in_progress')""",
            (data['machine_id'], data['scheduled_date']),
            fetch_one=True
        )
        
        if conflicting_jobs['count'] > 0:
            return error_response('Machine is already scheduled for this date', 400)
    
    query = """
        INSERT INTO job_schedules
        (order_id, department_id, stage_id, scheduled_date, scheduled_quantity,
         machine_id, assigned_employee_id, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, 'scheduled')
    """
    
    try:
        schedule_id = execute_query(
            query,
            (
                id,
                data['department_id'],
                data.get('stage_id'),
                data['scheduled_date'],
                data['scheduled_quantity'],
                data.get('machine_id'),
                data.get('assigned_employee_id')
            ),
            commit=True
        )
        
        execute_query(
            "UPDATE orders SET status = 'scheduled' WHERE id = %s",
            (id,),
            commit=True
        )
        
        log_audit(user_id, 'SCHEDULE', 'order', id, None, data)
        
        return success_response({'id': schedule_id}, 'Order scheduled successfully', 201)
    except Exception as e:
        return error_response(str(e), 500)

@orders_bp.route('/<int:id>/hold', methods=['POST'])
@token_required
@permission_required('planning', 'write')
def hold_order(id):
    data = request.get_json()
    user_id = request.current_user['user_id']
    
    hold_reason = data.get('hold_reason')
    if not hold_reason:
        return error_response('Hold reason is required', 400)
    
    execute_query(
        "UPDATE orders SET status = 'on_hold', hold_reason = %s WHERE id = %s",
        (hold_reason, id),
        commit=True
    )
    
    log_audit(user_id, 'HOLD', 'order', id, None, {'hold_reason': hold_reason})
    
    return success_response(message='Order placed on hold')

@orders_bp.route('/suggest-alternatives', methods=['POST'])
@token_required
@permission_required('planning', 'read')
def suggest_alternative_orders():
    data = request.get_json()
    
    department_id = data.get('department_id')
    scheduled_date = data.get('scheduled_date')
    quantity_needed = data.get('quantity_needed', 0)
    product_id = data.get('product_id')
    
    if not department_id or not scheduled_date:
        return error_response('department_id and scheduled_date are required', 400)
    
    query = """
        SELECT o.*, p.product_name, p.product_code, p.category,
               (SELECT COUNT(*) FROM job_schedules js WHERE js.order_id = o.id) as times_scheduled
        FROM orders o
        LEFT JOIN products p ON o.product_id = p.id
        WHERE o.status = 'unscheduled'
    """
    
    params = []
    
    if product_id:
        query += " AND (o.product_id = %s OR p.category = (SELECT category FROM products WHERE id = %s))"
        params.extend([product_id, product_id])
    
    if quantity_needed > 0:
        query += " AND o.quantity BETWEEN %s AND %s"
        params.extend([quantity_needed * 0.7, quantity_needed * 1.3])
    
    query += " ORDER BY times_scheduled ASC, o.priority DESC, o.created_at ASC LIMIT 10"
    
    suggestions = execute_query(query, tuple(params) if params else None, fetch_all=True)
    
    for suggestion in suggestions:
        dept_query = """
            SELECT d.id, d.name, d.capacity_target,
                   COALESCE(SUM(CASE WHEN js.status IN ('scheduled', 'in_progress') 
                   THEN js.scheduled_quantity ELSE 0 END), 0) as current_load
            FROM departments d
            LEFT JOIN job_schedules js ON d.id = js.department_id 
                AND js.scheduled_date = %s
            WHERE d.id = %s
            GROUP BY d.id
        """
        dept_info = execute_query(dept_query, (scheduled_date, department_id), fetch_one=True)
        
        if dept_info:
            available_capacity = (dept_info.get('capacity_target') or 1000) - dept_info['current_load']
            suggestion['fits_capacity'] = suggestion['quantity'] <= available_capacity
            suggestion['available_capacity'] = available_capacity
        else:
            suggestion['fits_capacity'] = True
            suggestion['available_capacity'] = 1000
    
    return success_response({
        'suggestions': suggestions,
        'count': len(suggestions)
    })

@orders_bp.route('/<int:id>/items', methods=['GET'])
@token_required
def get_order_items(id):
    query = """
        SELECT oi.*, p.product_name, p.product_code
        FROM order_items oi
        LEFT JOIN products p ON oi.product_id = p.id
        WHERE oi.order_id = %s
        ORDER BY oi.item_sequence
    """
    items = execute_query(query, (id,), fetch_all=True)
    return success_response(items)

@orders_bp.route('/<int:id>/items', methods=['POST'])
@token_required
@permission_required('planning', 'write')
def add_order_item(id):
    data = request.get_json()
    user_id = request.current_user['user_id']
    
    required_fields = ['product_id', 'quantity']
    for field in required_fields:
        if not data.get(field):
            return error_response(f'{field} is required', 400)
    
    max_seq = execute_query(
        "SELECT COALESCE(MAX(item_sequence), 0) as max_seq FROM order_items WHERE order_id = %s",
        (id,),
        fetch_one=True
    )
    
    query = """
        INSERT INTO order_items
        (order_id, product_id, item_sequence, quantity, unit_price, specifications)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    
    try:
        item_id = execute_query(
            query,
            (
                id,
                data['product_id'],
                max_seq['max_seq'] + 1,
                data['quantity'],
                data.get('unit_price'),
                data.get('specifications')
            ),
            commit=True
        )
        
        log_audit(user_id, 'CREATE', 'order_item', item_id, None, data)
        
        return success_response({'id': item_id}, 'Order item added successfully', 201)
    except Exception as e:
        return error_response(str(e), 500)

@orders_bp.route('/<int:order_id>/items/<int:item_id>', methods=['PUT'])
@token_required
@permission_required('planning', 'write')
def update_order_item(order_id, item_id):
    data = request.get_json()
    user_id = request.current_user['user_id']
    
    old_data = execute_query(
        "SELECT * FROM order_items WHERE id = %s AND order_id = %s",
        (item_id, order_id),
        fetch_one=True
    )
    
    if not old_data:
        return error_response('Order item not found', 404)
    
    query = """
        UPDATE order_items SET
            quantity = %s, unit_price = %s, status = %s, specifications = %s
        WHERE id = %s
    """
    
    try:
        execute_query(
            query,
            (
                data.get('quantity', old_data['quantity']),
                data.get('unit_price', old_data['unit_price']),
                data.get('status', old_data['status']),
                data.get('specifications', old_data['specifications']),
                item_id
            ),
            commit=True
        )
        
        log_audit(user_id, 'UPDATE', 'order_item', item_id, old_data, data)
        
        return success_response(message='Order item updated successfully')
    except Exception as e:
        return error_response(str(e), 500)

@orders_bp.route('/<int:order_id>/items/<int:item_id>', methods=['DELETE'])
@token_required
@permission_required('planning', 'write')
def delete_order_item(order_id, item_id):
    user_id = request.current_user['user_id']
    
    old_data = execute_query(
        "SELECT * FROM order_items WHERE id = %s AND order_id = %s",
        (item_id, order_id),
        fetch_one=True
    )
    
    if not old_data:
        return error_response('Order item not found', 404)
    
    try:
        execute_query("DELETE FROM order_items WHERE id = %s", (item_id,), commit=True)
        log_audit(user_id, 'DELETE', 'order_item', item_id, old_data, None)
        
        return success_response(message='Order item deleted successfully')
    except Exception as e:
        return error_response(str(e), 500)

@orders_bp.route('/<int:id>/suggestions', methods=['GET'])
@token_required
def get_order_suggestions(id):
    order = execute_query("SELECT * FROM orders WHERE id = %s", (id,), fetch_one=True)
    
    if not order:
        return error_response('Order not found', 404)
    
    suggestions = []
    
    if order['status'] == 'on_hold':
        if 'material' in str(order.get('hold_reason', '')).lower():
            suggestions.append({
                'type': 'material_check',
                'title': 'Check Material Availability',
                'description': 'Review inventory for required materials',
                'action': 'check_inventory',
                'priority': 'high'
            })
        
        if 'capacity' in str(order.get('hold_reason', '')).lower():
            similar_orders = execute_query(
                """SELECT DISTINCT department_id, COUNT(*) as dept_jobs
                   FROM job_schedules
                   WHERE status IN ('scheduled', 'in_progress')
                   GROUP BY department_id
                   ORDER BY dept_jobs ASC
                   LIMIT 3""",
                fetch_all=True
            )
            
            if similar_orders:
                suggestions.append({
                    'type': 'reschedule',
                    'title': 'Alternative Departments Available',
                    'description': f'Consider scheduling to departments with lower workload',
                    'action': 'reschedule',
                    'priority': 'medium',
                    'departments': [dept['department_id'] for dept in similar_orders]
                })
        
        if 'machine' in str(order.get('hold_reason', '')).lower():
            available_machines = execute_query(
                """SELECT id, machine_name FROM machines
                   WHERE status = 'operational'
                   AND id NOT IN (
                       SELECT machine_id FROM job_schedules
                       WHERE status = 'in_progress' AND machine_id IS NOT NULL
                   )
                   LIMIT 5""",
                fetch_all=True
            )
            
            if available_machines:
                suggestions.append({
                    'type': 'machine_allocation',
                    'title': 'Available Machines Found',
                    'description': f'{len(available_machines)} machines currently available',
                    'action': 'allocate_machine',
                    'priority': 'high',
                    'machines': available_machines
                })
    
    if order.get('priority') == 'low' and order['status'] == 'unscheduled':
        suggestions.append({
            'type': 'priority_review',
            'title': 'Consider Priority Adjustment',
            'description': 'Low priority unscheduled order - review if priority should be increased',
            'action': 'review_priority',
            'priority': 'low'
        })
    
    return success_response(suggestions)

@orders_bp.route('/<int:id>/production-path', methods=['GET'])
@token_required
def get_order_production_path(id):
    query = """
        SELECT opp.*, d.name as department_name, ps.stage_name,
               CONCAT(u.first_name, ' ', u.last_name) as created_by_name
        FROM order_production_paths opp
        LEFT JOIN departments d ON opp.department_id = d.id
        LEFT JOIN production_stages ps ON opp.stage_id = ps.id
        LEFT JOIN users u ON opp.created_by_id = u.id
        WHERE opp.order_id = %s
        ORDER BY opp.path_sequence
    """
    
    paths = execute_query(query, (id,), fetch_all=True)
    return success_response(paths)

@orders_bp.route('/<int:id>/production-path', methods=['POST'])
@token_required
@permission_required('planning', 'write')
def set_order_production_path(id):
    data = request.get_json()
    user_id = request.current_user['user_id']
    
    paths = data.get('paths', [])
    if not paths:
        return error_response('At least one production path is required', 400)
    
    try:
        execute_query("DELETE FROM order_production_paths WHERE order_id = %s", (id,), commit=True)
        
        for idx, path in enumerate(paths):
            if not path.get('department_id'):
                return error_response(f'department_id is required for path {idx + 1}', 400)
            
            query = """
                INSERT INTO order_production_paths
                (order_id, path_sequence, department_id, stage_id, 
                 estimated_duration_minutes, is_required, notes, created_by_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            execute_query(
                query,
                (
                    id,
                    idx + 1,
                    path['department_id'],
                    path.get('stage_id'),
                    path.get('estimated_duration_minutes'),
                    path.get('is_required', True),
                    path.get('notes'),
                    user_id
                ),
                commit=True
            )
        
        log_audit(user_id, 'SET_PRODUCTION_PATH', 'order', id, None, {'paths_count': len(paths)})
        
        return success_response(message=f'Production path set with {len(paths)} stages')
    except Exception as e:
        return error_response(str(e), 500)

@orders_bp.route('/<int:id>/production-path/<int:path_id>', methods=['PUT'])
@token_required
@permission_required('planning', 'write')
def update_production_path_step(id, path_id):
    data = request.get_json()
    user_id = request.current_user['user_id']
    
    old_data = execute_query(
        "SELECT * FROM order_production_paths WHERE id = %s AND order_id = %s",
        (path_id, id),
        fetch_one=True
    )
    
    if not old_data:
        return error_response('Production path step not found', 404)
    
    query = """
        UPDATE order_production_paths SET
            department_id = %s, stage_id = %s, estimated_duration_minutes = %s,
            is_required = %s, notes = %s
        WHERE id = %s
    """
    
    try:
        execute_query(
            query,
            (
                data.get('department_id', old_data['department_id']),
                data.get('stage_id', old_data['stage_id']),
                data.get('estimated_duration_minutes', old_data['estimated_duration_minutes']),
                data.get('is_required', old_data['is_required']),
                data.get('notes', old_data['notes']),
                path_id
            ),
            commit=True
        )
        
        log_audit(user_id, 'UPDATE', 'order_production_path', path_id, old_data, data)
        
        return success_response(message='Production path step updated successfully')
    except Exception as e:
        return error_response(str(e), 500)

@orders_bp.route('/<int:id>/production-path/<int:path_id>', methods=['DELETE'])
@token_required
@permission_required('planning', 'write')
def delete_production_path_step(id, path_id):
    user_id = request.current_user['user_id']
    
    old_data = execute_query(
        "SELECT * FROM order_production_paths WHERE id = %s AND order_id = %s",
        (path_id, id),
        fetch_one=True
    )
    
    if not old_data:
        return error_response('Production path step not found', 404)
    
    try:
        execute_query("DELETE FROM order_production_paths WHERE id = %s", (path_id,), commit=True)
        
        execute_query(
            """UPDATE order_production_paths 
               SET path_sequence = path_sequence - 1 
               WHERE order_id = %s AND path_sequence > %s""",
            (id, old_data['path_sequence']),
            commit=True
        )
        
        log_audit(user_id, 'DELETE', 'order_production_path', path_id, old_data, None)
        
        return success_response(message='Production path step deleted successfully')
    except Exception as e:
        return error_response(str(e), 500)
