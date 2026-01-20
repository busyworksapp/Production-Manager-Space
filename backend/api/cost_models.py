from flask import Blueprint, request
from backend.config.database import execute_query
from backend.utils.auth import token_required, permission_required
from backend.utils.response import success_response, error_response
from backend.utils.audit import log_audit
from datetime import datetime
import json

cost_models_bp = Blueprint('cost_models', __name__, url_prefix='/api/cost-models')

@cost_models_bp.route('/labor', methods=['GET'])
@token_required
def get_labor_costs():
    department_id = request.args.get('department_id')
    position = request.args.get('position')
    is_active = request.args.get('is_active', 'true')
    
    query = """
        SELECT lc.*, d.name as department_name
        FROM labor_cost_models lc
        LEFT JOIN departments d ON lc.department_id = d.id
        WHERE 1=1
    """
    params = []
    
    if department_id:
        query += " AND lc.department_id = %s"
        params.append(department_id)
    
    if position:
        query += " AND lc.position = %s"
        params.append(position)
    
    if is_active.lower() == 'true':
        query += " AND lc.is_active = TRUE"
        query += " AND (lc.effective_to IS NULL OR lc.effective_to >= CURDATE())"
    
    query += " ORDER BY d.name, lc.position"
    
    labor_costs = execute_query(query, tuple(params) if params else None, fetch_all=True)
    return success_response(labor_costs)

@cost_models_bp.route('/labor/<int:id>', methods=['GET'])
@token_required
def get_labor_cost(id):
    query = """
        SELECT lc.*, d.name as department_name
        FROM labor_cost_models lc
        LEFT JOIN departments d ON lc.department_id = d.id
        WHERE lc.id = %s
    """
    labor_cost = execute_query(query, (id,), fetch_one=True)
    
    if not labor_cost:
        return error_response('Labor cost model not found', 404)
    
    return success_response(labor_cost)

@cost_models_bp.route('/labor', methods=['POST'])
@token_required
@permission_required('finance', 'write')
def create_labor_cost():
    data = request.get_json()
    user_id = request.current_user['user_id']
    
    required_fields = ['department_id', 'position', 'hourly_rate', 'effective_from']
    for field in required_fields:
        if not data.get(field):
            return error_response(f'{field} is required', 400)
    
    query = """
        INSERT INTO labor_cost_models
        (department_id, position, hourly_rate, overtime_rate,
         benefits_percentage, effective_from, effective_to, created_by_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    try:
        cost_id = execute_query(
            query,
            (
                data['department_id'],
                data['position'],
                data['hourly_rate'],
                data.get('overtime_rate'),
                data.get('benefits_percentage'),
                data['effective_from'],
                data.get('effective_to'),
                user_id
            ),
            commit=True
        )
        
        log_audit(user_id, 'CREATE', 'labor_cost_model', cost_id, None, data)
        
        return success_response({'id': cost_id}, 'Labor cost model created successfully', 201)
    except Exception as e:
        return error_response(str(e), 500)

@cost_models_bp.route('/labor/<int:id>', methods=['PUT'])
@token_required
@permission_required('finance', 'write')
def update_labor_cost(id):
    data = request.get_json()
    user_id = request.current_user['user_id']
    
    old_data = execute_query("SELECT * FROM labor_cost_models WHERE id = %s", (id,), fetch_one=True)
    if not old_data:
        return error_response('Labor cost model not found', 404)
    
    query = """
        UPDATE labor_cost_models SET
            hourly_rate = %s, overtime_rate = %s, benefits_percentage = %s,
            effective_from = %s, effective_to = %s
        WHERE id = %s
    """
    
    try:
        execute_query(
            query,
            (
                data.get('hourly_rate', old_data['hourly_rate']),
                data.get('overtime_rate', old_data['overtime_rate']),
                data.get('benefits_percentage', old_data['benefits_percentage']),
                data.get('effective_from', old_data['effective_from']),
                data.get('effective_to', old_data['effective_to']),
                id
            ),
            commit=True
        )
        
        log_audit(user_id, 'UPDATE', 'labor_cost_model', id, old_data, data)
        
        return success_response(message='Labor cost model updated successfully')
    except Exception as e:
        return error_response(str(e), 500)

@cost_models_bp.route('/overhead', methods=['GET'])
@token_required
def get_overhead_costs():
    department_id = request.args.get('department_id')
    cost_category = request.args.get('cost_category')
    is_active = request.args.get('is_active', 'true')
    
    query = """
        SELECT oc.*, d.name as department_name
        FROM overhead_cost_models oc
        LEFT JOIN departments d ON oc.department_id = d.id
        WHERE 1=1
    """
    params = []
    
    if department_id:
        query += " AND oc.department_id = %s"
        params.append(department_id)
    
    if cost_category:
        query += " AND oc.cost_category = %s"
        params.append(cost_category)
    
    if is_active.lower() == 'true':
        query += " AND oc.is_active = TRUE"
        query += " AND (oc.effective_to IS NULL OR oc.effective_to >= CURDATE())"
    
    query += " ORDER BY d.name, oc.cost_category"
    
    overhead_costs = execute_query(query, tuple(params) if params else None, fetch_all=True)
    return success_response(overhead_costs)

@cost_models_bp.route('/overhead/<int:id>', methods=['GET'])
@token_required
def get_overhead_cost(id):
    query = """
        SELECT oc.*, d.name as department_name
        FROM overhead_cost_models oc
        LEFT JOIN departments d ON oc.department_id = d.id
        WHERE oc.id = %s
    """
    overhead_cost = execute_query(query, (id,), fetch_one=True)
    
    if not overhead_cost:
        return error_response('Overhead cost model not found', 404)
    
    return success_response(overhead_cost)

@cost_models_bp.route('/overhead', methods=['POST'])
@token_required
@permission_required('finance', 'write')
def create_overhead_cost():
    data = request.get_json()
    user_id = request.current_user['user_id']
    
    required_fields = ['department_id', 'cost_category', 'cost_type', 'allocation_method', 'cost_amount', 'effective_from']
    for field in required_fields:
        if not data.get(field):
            return error_response(f'{field} is required', 400)
    
    query = """
        INSERT INTO overhead_cost_models
        (department_id, cost_category, cost_description, cost_type,
         allocation_method, cost_amount, effective_from, effective_to, created_by_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    try:
        cost_id = execute_query(
            query,
            (
                data['department_id'],
                data['cost_category'],
                data.get('cost_description'),
                data['cost_type'],
                data['allocation_method'],
                data['cost_amount'],
                data['effective_from'],
                data.get('effective_to'),
                user_id
            ),
            commit=True
        )
        
        log_audit(user_id, 'CREATE', 'overhead_cost_model', cost_id, None, data)
        
        return success_response({'id': cost_id}, 'Overhead cost model created successfully', 201)
    except Exception as e:
        return error_response(str(e), 500)

@cost_models_bp.route('/overhead/<int:id>', methods=['PUT'])
@token_required
@permission_required('finance', 'write')
def update_overhead_cost(id):
    data = request.get_json()
    user_id = request.current_user['user_id']
    
    old_data = execute_query("SELECT * FROM overhead_cost_models WHERE id = %s", (id,), fetch_one=True)
    if not old_data:
        return error_response('Overhead cost model not found', 404)
    
    query = """
        UPDATE overhead_cost_models SET
            cost_category = %s, cost_description = %s, cost_type = %s,
            allocation_method = %s, cost_amount = %s,
            effective_from = %s, effective_to = %s
        WHERE id = %s
    """
    
    try:
        execute_query(
            query,
            (
                data.get('cost_category', old_data['cost_category']),
                data.get('cost_description', old_data['cost_description']),
                data.get('cost_type', old_data['cost_type']),
                data.get('allocation_method', old_data['allocation_method']),
                data.get('cost_amount', old_data['cost_amount']),
                data.get('effective_from', old_data['effective_from']),
                data.get('effective_to', old_data['effective_to']),
                id
            ),
            commit=True
        )
        
        log_audit(user_id, 'UPDATE', 'overhead_cost_model', id, old_data, data)
        
        return success_response(message='Overhead cost model updated successfully')
    except Exception as e:
        return error_response(str(e), 500)

@cost_models_bp.route('/production-costs', methods=['GET'])
@token_required
def get_production_costs():
    order_id = request.args.get('order_id')
    job_schedule_id = request.args.get('job_schedule_id')
    
    query = """
        SELECT pc.*, o.order_number, o.customer_name
        FROM production_cost_tracking pc
        LEFT JOIN orders o ON pc.order_id = o.id
        WHERE 1=1
    """
    params = []
    
    if order_id:
        query += " AND pc.order_id = %s"
        params.append(order_id)
    
    if job_schedule_id:
        query += " AND pc.job_schedule_id = %s"
        params.append(job_schedule_id)
    
    query += " ORDER BY pc.calculated_at DESC"
    
    costs = execute_query(query, tuple(params) if params else None, fetch_all=True)
    return success_response(costs)

@cost_models_bp.route('/production-costs/calculate', methods=['POST'])
@token_required
@permission_required('finance', 'write')
def calculate_production_cost():
    data = request.get_json()
    user_id = request.current_user['user_id']
    
    order_id = data.get('order_id')
    job_schedule_id = data.get('job_schedule_id')
    
    if not order_id:
        return error_response('order_id is required', 400)
    
    material_cost = calculate_material_cost(order_id)
    labor_cost = calculate_labor_cost(job_schedule_id) if job_schedule_id else 0
    overhead_cost = calculate_overhead_cost(job_schedule_id) if job_schedule_id else 0
    
    query = """
        INSERT INTO production_cost_tracking
        (order_id, job_schedule_id, material_cost, labor_cost, overhead_cost, cost_details, calculated_by_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    
    cost_details = {
        'material_breakdown': data.get('material_breakdown', {}),
        'labor_breakdown': data.get('labor_breakdown', {}),
        'overhead_breakdown': data.get('overhead_breakdown', {})
    }
    
    try:
        cost_id = execute_query(
            query,
            (order_id, job_schedule_id, material_cost, labor_cost, overhead_cost, json.dumps(cost_details), user_id),
            commit=True
        )
        
        log_audit(user_id, 'CALCULATE_COST', 'production_cost_tracking', cost_id)
        
        return success_response({
            'id': cost_id,
            'material_cost': material_cost,
            'labor_cost': labor_cost,
            'overhead_cost': overhead_cost,
            'total_cost': material_cost + labor_cost + overhead_cost
        }, 'Production cost calculated successfully', 201)
    except Exception as e:
        return error_response(str(e), 500)

def calculate_material_cost(order_id):
    order = execute_query("SELECT product_id, quantity FROM orders WHERE id = %s", (order_id,), fetch_one=True)
    
    if not order or not order['product_id']:
        return 0
    
    bom = execute_query(
        "SELECT id FROM bom WHERE product_id = %s AND is_active = TRUE ORDER BY effective_date DESC LIMIT 1",
        (order['product_id'],),
        fetch_one=True
    )
    
    if not bom:
        return 0
    
    items = execute_query(
        "SELECT SUM(total_cost) as total FROM bom_items WHERE bom_id = %s",
        (bom['id'],),
        fetch_one=True
    )
    
    return float(items['total'] or 0) * order['quantity']

def calculate_labor_cost(job_schedule_id):
    return 0

def calculate_overhead_cost(job_schedule_id):
    return 0
