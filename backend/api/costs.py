from flask import Blueprint, request
from backend.config.database import execute_query
from backend.utils.auth import token_required, permission_required
from backend.utils.response import success_response, error_response
from backend.utils.audit import log_audit
from datetime import datetime
import json

costs_bp = Blueprint('costs', __name__, url_prefix='/api/costs')

@costs_bp.route('/job-profitability', methods=['GET'])
@token_required
def get_job_profitability():
    """Get job profitability analysis from view"""
    department_id = request.args.get('department_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    query = """
        SELECT * FROM v_job_profitability
        WHERE 1=1
    """
    
    params = []
    if department_id:
        query += " AND department_name IN (SELECT name FROM departments WHERE id = %s)"
        params.append(department_id)
    
    if start_date:
        query += " AND scheduled_date >= %s"
        params.append(start_date)
    
    if end_date:
        query += " AND scheduled_date <= %s"
        params.append(end_date)
    
    query += " ORDER BY scheduled_date DESC LIMIT 100"
    
    jobs = execute_query(query, tuple(params) if params else None, fetch_all=True)
    return success_response(jobs)

@costs_bp.route('/department-analysis', methods=['GET'])
@token_required
def get_department_cost_analysis():
    """Get department cost analysis from view"""
    department_id = request.args.get('department_id')
    month_year = request.args.get('month_year')
    
    query = """
        SELECT * FROM v_department_cost_analysis
        WHERE 1=1
    """
    
    params = []
    if department_id:
        query += " AND department_id = %s"
        params.append(department_id)
    
    if month_year:
        query += " AND month_year = %s"
        params.append(month_year)
    
    query += " ORDER BY month_year DESC, department_name LIMIT 50"
    
    analysis = execute_query(query, tuple(params) if params else None, fetch_all=True)
    return success_response(analysis)

@costs_bp.route('/labor-models', methods=['GET'])
@token_required
def get_labor_cost_models():
    """Get all active labor cost models"""
    department_id = request.args.get('department_id')
    
    query = """
        SELECT lcm.*, d.name as department_name,
               CONCAT(u.first_name, ' ', u.last_name) as created_by_name
        FROM labor_cost_models lcm
        LEFT JOIN departments d ON lcm.department_id = d.id
        LEFT JOIN users u ON lcm.created_by_id = u.id
        WHERE lcm.is_active = TRUE
    """
    
    params = []
    if department_id:
        query += " AND lcm.department_id = %s"
        params.append(department_id)
    
    query += " ORDER BY d.name, lcm.position"
    
    models = execute_query(query, tuple(params) if params else None, fetch_all=True)
    return success_response(models)

@costs_bp.route('/labor-models', methods=['POST'])
@token_required
@permission_required('finance', 'write')
def create_labor_cost_model():
    """Create a new labor cost model"""
    data = request.get_json()
    user_id = request.current_user['user_id']
    
    required_fields = ['department_id', 'position', 'hourly_rate', 'effective_from']
    for field in required_fields:
        if not data.get(field):
            return error_response(f'{field} is required', 400)
    
    query = """
        INSERT INTO labor_cost_models
        (department_id, position, hourly_rate, overtime_rate, benefits_percentage,
         effective_from, effective_to, created_by_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    try:
        model_id = execute_query(
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
        
        log_audit(user_id, 'CREATE', 'labor_cost_model', model_id, None, data)
        
        return success_response({'id': model_id}, 'Labor cost model created successfully', 201)
    except Exception as e:
        return error_response(str(e), 500)

@costs_bp.route('/labor-models/<int:id>', methods=['PUT'])
@token_required
@permission_required('finance', 'write')
def update_labor_cost_model(id):
    """Update a labor cost model"""
    data = request.get_json()
    user_id = request.current_user['user_id']
    
    old_data = execute_query("SELECT * FROM labor_cost_models WHERE id = %s", (id,), fetch_one=True)
    if not old_data:
        return error_response('Labor cost model not found', 404)
    
    query = """
        UPDATE labor_cost_models SET
            hourly_rate = %s,
            overtime_rate = %s,
            benefits_percentage = %s,
            effective_to = %s,
            is_active = %s
        WHERE id = %s
    """
    
    try:
        execute_query(
            query,
            (
                data.get('hourly_rate', old_data['hourly_rate']),
                data.get('overtime_rate', old_data['overtime_rate']),
                data.get('benefits_percentage', old_data['benefits_percentage']),
                data.get('effective_to', old_data['effective_to']),
                data.get('is_active', old_data['is_active']),
                id
            ),
            commit=True
        )
        
        log_audit(user_id, 'UPDATE', 'labor_cost_model', id, old_data, data)
        
        return success_response(message='Labor cost model updated successfully')
    except Exception as e:
        return error_response(str(e), 500)

@costs_bp.route('/overhead-models', methods=['GET'])
@token_required
def get_overhead_cost_models():
    """Get all active overhead cost models"""
    department_id = request.args.get('department_id')
    
    query = """
        SELECT ocm.*, d.name as department_name,
               CONCAT(u.first_name, ' ', u.last_name) as created_by_name
        FROM overhead_cost_models ocm
        LEFT JOIN departments d ON ocm.department_id = d.id
        LEFT JOIN users u ON ocm.created_by_id = u.id
        WHERE ocm.is_active = TRUE
    """
    
    params = []
    if department_id:
        query += " AND ocm.department_id = %s"
        params.append(department_id)
    
    query += " ORDER BY d.name, ocm.cost_category"
    
    models = execute_query(query, tuple(params) if params else None, fetch_all=True)
    return success_response(models)

@costs_bp.route('/overhead-models', methods=['POST'])
@token_required
@permission_required('finance', 'write')
def create_overhead_cost_model():
    """Create a new overhead cost model"""
    data = request.get_json()
    user_id = request.current_user['user_id']
    
    required_fields = ['department_id', 'cost_category', 'cost_type', 'allocation_method', 'cost_amount', 'effective_from']
    for field in required_fields:
        if not data.get(field):
            return error_response(f'{field} is required', 400)
    
    query = """
        INSERT INTO overhead_cost_models
        (department_id, cost_category, cost_description, cost_type, allocation_method,
         cost_amount, effective_from, effective_to, created_by_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    try:
        model_id = execute_query(
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
        
        log_audit(user_id, 'CREATE', 'overhead_cost_model', model_id, None, data)
        
        return success_response({'id': model_id}, 'Overhead cost model created successfully', 201)
    except Exception as e:
        return error_response(str(e), 500)

@costs_bp.route('/overhead-models/<int:id>', methods=['PUT'])
@token_required
@permission_required('finance', 'write')
def update_overhead_cost_model(id):
    """Update an overhead cost model"""
    data = request.get_json()
    user_id = request.current_user['user_id']
    
    old_data = execute_query("SELECT * FROM overhead_cost_models WHERE id = %s", (id,), fetch_one=True)
    if not old_data:
        return error_response('Overhead cost model not found', 404)
    
    query = """
        UPDATE overhead_cost_models SET
            cost_amount = %s,
            effective_to = %s,
            is_active = %s
        WHERE id = %s
    """
    
    try:
        execute_query(
            query,
            (
                data.get('cost_amount', old_data['cost_amount']),
                data.get('effective_to', old_data['effective_to']),
                data.get('is_active', old_data['is_active']),
                id
            ),
            commit=True
        )
        
        log_audit(user_id, 'UPDATE', 'overhead_cost_model', id, old_data, data)
        
        return success_response(message='Overhead cost model updated successfully')
    except Exception as e:
        return error_response(str(e), 500)

@costs_bp.route('/job/<int:job_id>/calculate', methods=['POST'])
@token_required
def calculate_job_cost(job_id):
    """Manually trigger cost calculation for a job"""
    user_id = request.current_user['user_id']
    
    job = execute_query(
        "SELECT * FROM job_schedules WHERE id = %s",
        (job_id,),
        fetch_one=True
    )
    
    if not job:
        return error_response('Job not found', 404)
    
    if job['status'] != 'completed':
        return error_response('Can only calculate costs for completed jobs', 400)
    
    # Force recalculation by updating a timestamp
    try:
        execute_query(
            "UPDATE job_schedules SET updated_at = NOW() WHERE id = %s",
            (job_id,),
            commit=True
        )
        
        # Get updated job with calculated costs
        updated_job = execute_query(
            "SELECT * FROM job_schedules WHERE id = %s",
            (job_id,),
            fetch_one=True
        )
        
        log_audit(user_id, 'CALCULATE_COST', 'job_schedule', job_id, job, updated_job)
        
        return success_response({
            'material_cost': updated_job['material_cost'],
            'labor_cost': updated_job['labor_cost'],
            'overhead_cost': updated_job['overhead_cost'],
            'total_cost': updated_job['total_cost']
        }, 'Cost calculated successfully')
    except Exception as e:
        return error_response(str(e), 500)
