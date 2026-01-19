from flask import Blueprint, request
from backend.config.database import execute_query
from backend.utils.auth import token_required, permission_required
from backend.utils.response import success_response, error_response
from backend.utils.audit import log_audit

finance_bp = Blueprint('finance', __name__, url_prefix='/api/finance')

@finance_bp.route('/bom', methods=['GET'])
@token_required
def get_boms():
    product_id = request.args.get('product_id')
    is_active = request.args.get('is_active', 'true')
    
    query = """
        SELECT b.*, p.product_name, p.product_code,
               CONCAT(created.first_name, ' ', created.last_name) as created_by_name,
               CONCAT(approved.first_name, ' ', approved.last_name) as approved_by_name
        FROM bom b
        LEFT JOIN products p ON b.product_id = p.id
        LEFT JOIN users created ON b.created_by_id = created.id
        LEFT JOIN users approved ON b.approved_by_id = approved.id
        WHERE 1=1
    """
    
    params = []
    if product_id:
        query += " AND b.product_id = %s"
        params.append(product_id)
    
    if is_active.lower() == 'true':
        query += " AND b.is_active = TRUE"
    
    query += " ORDER BY b.effective_date DESC"
    
    boms = execute_query(query, tuple(params) if params else None, fetch_all=True)
    return success_response(boms)

@finance_bp.route('/bom/<int:id>', methods=['GET'])
@token_required
def get_bom(id):
    query = """
        SELECT b.*, p.product_name, p.product_code,
               CONCAT(created.first_name, ' ', created.last_name) as created_by_name
        FROM bom b
        LEFT JOIN products p ON b.product_id = p.id
        LEFT JOIN users created ON b.created_by_id = created.id
        WHERE b.id = %s
    """
    bom = execute_query(query, (id,), fetch_one=True)
    
    if not bom:
        return error_response('BOM not found', 404)
    
    items_query = "SELECT * FROM bom_items WHERE bom_id = %s ORDER BY item_code"
    items = execute_query(items_query, (id,), fetch_all=True)
    bom['items'] = items
    
    total_cost = sum([item['total_cost'] for item in items])
    bom['total_bom_cost'] = total_cost
    
    return success_response(bom)

@finance_bp.route('/bom', methods=['POST'])
@token_required
@permission_required('finance', 'write')
def create_bom():
    data = request.get_json()
    user_id = request.current_user['user_id']
    
    required_fields = ['product_id', 'version', 'effective_date']
    for field in required_fields:
        if not data.get(field):
            return error_response(f'{field} is required', 400)
    
    if not data.get('items') or len(data['items']) == 0:
        return error_response('At least one BOM item is required', 400)
    
    query = """
        INSERT INTO bom
        (product_id, version, effective_date, notes, created_by_id)
        VALUES (%s, %s, %s, %s, %s)
    """
    
    try:
        bom_id = execute_query(
            query,
            (
                data['product_id'],
                data['version'],
                data['effective_date'],
                data.get('notes'),
                user_id
            ),
            commit=True
        )
        
        for item in data['items']:
            item_query = """
                INSERT INTO bom_items
                (bom_id, item_code, item_description, quantity_per_unit,
                 unit_of_measure, unit_cost, material_type, supplier, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            execute_query(
                item_query,
                (
                    bom_id,
                    item['item_code'],
                    item['item_description'],
                    item['quantity_per_unit'],
                    item['unit_of_measure'],
                    item['unit_cost'],
                    item.get('material_type'),
                    item.get('supplier'),
                    item.get('notes')
                ),
                commit=True
            )
        
        log_audit(user_id, 'CREATE', 'bom', bom_id, None, data)
        
        return success_response({'id': bom_id}, 'BOM created successfully', 201)
    except Exception as e:
        return error_response(str(e), 500)

@finance_bp.route('/bom/<int:id>', methods=['PUT'])
@token_required
@permission_required('finance', 'write')
def update_bom(id):
    data = request.get_json()
    user_id = request.current_user['user_id']
    
    old_data = execute_query("SELECT * FROM bom WHERE id = %s", (id,), fetch_one=True)
    if not old_data:
        return error_response('BOM not found', 404)
    
    query = """
        UPDATE bom SET
            version = %s, effective_date = %s, notes = %s, is_active = %s
        WHERE id = %s
    """
    
    try:
        execute_query(
            query,
            (
                data.get('version', old_data['version']),
                data.get('effective_date', old_data['effective_date']),
                data.get('notes', old_data['notes']),
                data.get('is_active', old_data['is_active']),
                id
            ),
            commit=True
        )
        
        if data.get('items'):
            execute_query("DELETE FROM bom_items WHERE bom_id = %s", (id,), commit=True)
            
            for item in data['items']:
                item_query = """
                    INSERT INTO bom_items
                    (bom_id, item_code, item_description, quantity_per_unit,
                     unit_of_measure, unit_cost, material_type, supplier, notes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                execute_query(
                    item_query,
                    (
                        id,
                        item['item_code'],
                        item['item_description'],
                        item['quantity_per_unit'],
                        item['unit_of_measure'],
                        item['unit_cost'],
                        item.get('material_type'),
                        item.get('supplier'),
                        item.get('notes')
                    ),
                    commit=True
                )
        
        log_audit(user_id, 'UPDATE', 'bom', id, old_data, data)
        
        return success_response(message='BOM updated successfully')
    except Exception as e:
        return error_response(str(e), 500)

@finance_bp.route('/bom/<int:id>/approve', methods=['POST'])
@token_required
@permission_required('finance', 'approve')
def approve_bom(id):
    user_id = request.current_user['user_id']
    
    execute_query(
        "UPDATE bom SET approved_by_id = %s, approved_at = NOW() WHERE id = %s",
        (user_id, id),
        commit=True
    )
    
    log_audit(user_id, 'APPROVE', 'bom', id)
    
    return success_response(message='BOM approved successfully')

@finance_bp.route('/cost-analysis/defects', methods=['GET'])
@token_required
@permission_required('finance', 'read')
def defects_cost_analysis():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    query = """
        SELECT rt.id, rt.ticket_number, rt.quantity_rejected, rt.created_at,
               o.order_number, p.product_name, d.name as department_name,
               b.id as bom_id, 
               SUM(bi.total_cost * rt.quantity_rejected) as total_cost
        FROM replacement_tickets rt
        LEFT JOIN orders o ON rt.order_id = o.id
        LEFT JOIN products p ON rt.product_id = p.id
        LEFT JOIN departments d ON rt.department_id = d.id
        LEFT JOIN bom b ON b.product_id = p.id AND b.is_active = TRUE
        LEFT JOIN bom_items bi ON bi.bom_id = b.id
        WHERE 1=1
    """
    
    params = []
    if start_date:
        query += " AND rt.created_at >= %s"
        params.append(start_date)
    
    if end_date:
        query += " AND rt.created_at <= %s"
        params.append(end_date)
    
    query += " GROUP BY rt.id ORDER BY rt.created_at DESC"
    
    analysis = execute_query(query, tuple(params) if params else None, fetch_all=True)
    
    total_cost = sum([item['total_cost'] or 0 for item in analysis])
    
    return success_response({
        'defects': analysis,
        'total_cost': total_cost,
        'count': len(analysis)
    })
