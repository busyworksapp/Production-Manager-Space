from flask import Blueprint, request
from backend.config.database import execute_query
from backend.utils.auth import token_required, permission_required
from backend.utils.response import success_response, error_response
from backend.utils.audit import log_audit
from datetime import datetime, timedelta

capacity_planning_bp = Blueprint('capacity_planning', __name__, url_prefix='/api/capacity-planning')

@capacity_planning_bp.route('/departments', methods=['GET'])
@token_required
def get_department_capacity():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if not start_date:
        start_date = datetime.now().strftime('%Y-%m-%d')
    if not end_date:
        end_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
    
    query = """
        SELECT 
            d.id, d.name, d.capacity_target,
            COUNT(DISTINCT e.id) as employee_count,
            COUNT(DISTINCT m.id) as machine_count,
            COUNT(DISTINCT CASE WHEN js.status IN ('scheduled', 'in_progress') THEN js.id END) as scheduled_jobs,
            SUM(CASE WHEN js.status IN ('scheduled', 'in_progress') THEN js.scheduled_quantity ELSE 0 END) as scheduled_quantity,
            SUM(CASE WHEN js.status = 'completed' THEN js.actual_quantity ELSE 0 END) as completed_quantity
        FROM departments d
        LEFT JOIN employees e ON d.id = e.department_id AND e.is_active = TRUE
        LEFT JOIN machines m ON d.id = m.department_id AND m.is_active = TRUE
        LEFT JOIN job_schedules js ON d.id = js.department_id 
            AND js.scheduled_date BETWEEN %s AND %s
        WHERE d.is_active = TRUE
        GROUP BY d.id, d.name, d.capacity_target
        ORDER BY d.name
    """
    
    departments = execute_query(query, (start_date, end_date), fetch_all=True)
    
    for dept in departments:
        target = dept.get('capacity_target') or 1000
        scheduled = dept.get('scheduled_quantity') or 0
        
        dept['capacity_target'] = target
        dept['capacity_used'] = scheduled
        dept['capacity_percentage'] = min(100, round((scheduled / target) * 100, 2))
        
        if dept['capacity_percentage'] >= 100:
            dept['capacity_status'] = 'overbooked'
        elif dept['capacity_percentage'] >= 80:
            dept['capacity_status'] = 'high'
        elif dept['capacity_percentage'] >= 50:
            dept['capacity_status'] = 'medium'
        else:
            dept['capacity_status'] = 'low'
    
    return success_response(departments)

@capacity_planning_bp.route('/departments/<int:id>', methods=['GET'])
@token_required
def get_department_capacity_detail(id):
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if not start_date:
        start_date = datetime.now().strftime('%Y-%m-%d')
    if not end_date:
        end_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
    
    dept = execute_query("SELECT * FROM departments WHERE id = %s", (id,), fetch_one=True)
    if not dept:
        return error_response('Department not found', 404)
    
    jobs_query = """
        SELECT js.*, o.order_number, o.customer_name, p.product_name,
               m.machine_name, CONCAT(e.first_name, ' ', e.last_name) as employee_name
        FROM job_schedules js
        LEFT JOIN orders o ON js.order_id = o.id
        LEFT JOIN products p ON o.product_id = p.id
        LEFT JOIN machines m ON js.machine_id = m.id
        LEFT JOIN employees e ON js.assigned_employee_id = e.id
        WHERE js.department_id = %s
        AND js.scheduled_date BETWEEN %s AND %s
        ORDER BY js.scheduled_date, js.status
    """
    
    jobs = execute_query(jobs_query, (id, start_date, end_date), fetch_all=True)
    
    scheduled_quantity = sum(job['scheduled_quantity'] or 0 for job in jobs if job['status'] in ['scheduled', 'in_progress'])
    completed_quantity = sum(job['actual_quantity'] or 0 for job in jobs if job['status'] == 'completed')
    
    target = dept.get('capacity_target') or 1000
    
    return success_response({
        'department': dept,
        'jobs': jobs,
        'capacity_target': target,
        'scheduled_quantity': scheduled_quantity,
        'completed_quantity': completed_quantity,
        'capacity_percentage': min(100, round((scheduled_quantity / target) * 100, 2)),
        'available_capacity': max(0, target - scheduled_quantity)
    })

@capacity_planning_bp.route('/validate', methods=['POST'])
@token_required
@permission_required('planning', 'schedule')
def validate_capacity():
    data = request.get_json()
    
    department_id = data.get('department_id')
    scheduled_date = data.get('scheduled_date')
    quantity = data.get('quantity', 0)
    
    if not department_id or not scheduled_date:
        return error_response('department_id and scheduled_date are required', 400)
    
    dept = execute_query("SELECT capacity_target FROM departments WHERE id = %s", (department_id,), fetch_one=True)
    if not dept:
        return error_response('Department not found', 404)
    
    end_date = (datetime.strptime(scheduled_date, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')
    
    existing_scheduled = execute_query(
        """SELECT SUM(scheduled_quantity) as total
           FROM job_schedules
           WHERE department_id = %s
           AND scheduled_date BETWEEN %s AND %s
           AND status IN ('scheduled', 'in_progress')""",
        (department_id, scheduled_date, end_date),
        fetch_one=True
    )
    
    current_scheduled = existing_scheduled['total'] or 0
    target = dept['capacity_target'] or 1000
    
    new_total = current_scheduled + quantity
    percentage_after = round((new_total / target) * 100, 2)
    
    validation_result = {
        'valid': new_total <= target,
        'capacity_target': target,
        'current_scheduled': current_scheduled,
        'requested_quantity': quantity,
        'total_after_scheduling': new_total,
        'capacity_percentage': percentage_after,
        'available_capacity': max(0, target - current_scheduled),
        'excess_quantity': max(0, new_total - target)
    }
    
    if percentage_after >= 100:
        validation_result['warning'] = 'Department capacity will be exceeded'
        validation_result['severity'] = 'error'
    elif percentage_after >= 80:
        validation_result['warning'] = 'Department capacity is nearly full'
        validation_result['severity'] = 'warning'
    
    return success_response(validation_result)

@capacity_planning_bp.route('/departments/<int:id>/target', methods=['PUT'])
@token_required
@permission_required('admin', 'write')
def update_capacity_target(id):
    data = request.get_json()
    user_id = request.current_user['user_id']
    
    target = data.get('capacity_target')
    if not target or target <= 0:
        return error_response('Valid capacity_target is required', 400)
    
    old_data = execute_query("SELECT capacity_target FROM departments WHERE id = %s", (id,), fetch_one=True)
    if not old_data:
        return error_response('Department not found', 404)
    
    execute_query(
        "UPDATE departments SET capacity_target = %s WHERE id = %s",
        (target, id),
        commit=True
    )
    
    log_audit(user_id, 'UPDATE_CAPACITY_TARGET', 'department', id, old_data, data)
    
    return success_response(message='Capacity target updated successfully')

@capacity_planning_bp.route('/suggest-alternatives', methods=['POST'])
@token_required
@permission_required('planning', 'schedule')
def suggest_alternatives():
    data = request.get_json()
    
    department_id = data.get('department_id')
    scheduled_date = data.get('scheduled_date')
    quantity = data.get('quantity', 0)
    order_id = data.get('order_id')
    
    if not department_id or not scheduled_date or not quantity:
        return error_response('department_id, scheduled_date, and quantity are required', 400)
    
    dept = execute_query(
        "SELECT id, name, capacity_target FROM departments WHERE id = %s",
        (department_id,),
        fetch_one=True
    )
    if not dept:
        return error_response('Department not found', 404)
    
    target = dept['capacity_target'] or 1000
    suggestions = []
    
    current_date = datetime.strptime(scheduled_date, '%Y-%m-%d')
    
    for days_offset in range(1, 15):
        alt_date = current_date + timedelta(days=days_offset)
        alt_date_str = alt_date.strftime('%Y-%m-%d')
        end_date = (alt_date + timedelta(days=1)).strftime('%Y-%m-%d')
        
        existing_scheduled = execute_query(
            """SELECT SUM(scheduled_quantity) as total
               FROM job_schedules
               WHERE department_id = %s
               AND scheduled_date BETWEEN %s AND %s
               AND status IN ('scheduled', 'in_progress')""",
            (department_id, alt_date_str, end_date),
            fetch_one=True
        )
        
        scheduled = existing_scheduled['total'] or 0
        available = target - scheduled
        
        if available >= quantity:
            capacity_after = scheduled + quantity
            percentage = round((capacity_after / target) * 100, 2)
            
            suggestions.append({
                'suggested_date': alt_date_str,
                'days_from_original': days_offset,
                'available_capacity': available,
                'capacity_percentage_after': percentage,
                'current_scheduled': scheduled,
                'reason': f'{available} units available'
            })
            
            if len(suggestions) >= 5:
                break
    
    similar_orders_query = """
        SELECT DISTINCT js.department_id, d.name as department_name, d.capacity_target
        FROM job_schedules js
        JOIN departments d ON js.department_id = d.id
        WHERE js.order_id IN (
            SELECT o2.id FROM orders o2
            JOIN orders o1 ON o1.id = %s
            WHERE o2.product_id = o1.product_id
            AND o2.id != o1.id
        )
        AND d.id != %s
        AND d.is_active = TRUE
        LIMIT 3
    """
    
    similar_depts = []
    if order_id:
        similar_depts = execute_query(
            similar_orders_query,
            (order_id, department_id),
            fetch_all=True
        )
    
    alternative_depts = []
    if not similar_depts:
        similar_depts = execute_query(
            """SELECT id as department_id, name as department_name, capacity_target
               FROM departments
               WHERE id != %s
               AND is_active = TRUE
               AND department_type = (SELECT department_type FROM departments WHERE id = %s)
               LIMIT 3""",
            (department_id, department_id),
            fetch_all=True
        )
    
    for alt_dept in similar_depts:
        end_date = (current_date + timedelta(days=1)).strftime('%Y-%m-%d')
        
        existing_scheduled = execute_query(
            """SELECT SUM(scheduled_quantity) as total
               FROM job_schedules
               WHERE department_id = %s
               AND scheduled_date BETWEEN %s AND %s
               AND status IN ('scheduled', 'in_progress')""",
            (alt_dept['department_id'], scheduled_date, end_date),
            fetch_one=True
        )
        
        scheduled = existing_scheduled['total'] or 0
        target_alt = alt_dept.get('capacity_target') or 1000
        available = target_alt - scheduled
        
        if available >= quantity:
            percentage = round(((scheduled + quantity) / target_alt) * 100, 2)
            
            alternative_depts.append({
                'department_id': alt_dept['department_id'],
                'department_name': alt_dept['department_name'],
                'available_capacity': available,
                'capacity_percentage_after': percentage,
                'reason': 'Similar work performed here previously'
            })
    
    return success_response({
        'original_department': dept['name'],
        'original_date': scheduled_date,
        'requested_quantity': quantity,
        'date_alternatives': suggestions,
        'department_alternatives': alternative_depts,
        'total_suggestions': len(suggestions) + len(alternative_depts)
    })
