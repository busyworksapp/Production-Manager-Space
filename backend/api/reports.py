from flask import Blueprint, request
from backend.config.database import execute_query
from backend.utils.auth import token_required, permission_required
from backend.utils.response import success_response, error_response
from backend.utils.audit import log_audit
from backend.utils.report_generator import execute_scheduled_report
from backend.utils.email_sender import send_email
from datetime import datetime, timedelta
import json

reports_bp = Blueprint('reports', __name__, url_prefix='/api/reports')

@reports_bp.route('/scheduled', methods=['GET'])
@token_required
def get_scheduled_reports():
    query = """
        SELECT er.*, CONCAT(u.first_name, ' ', u.last_name) as created_by_name
        FROM email_reports er
        LEFT JOIN users u ON er.created_by_id = u.id
        WHERE er.is_active = TRUE
        ORDER BY er.report_name
    """
    reports = execute_query(query, fetch_all=True)
    return success_response(reports)

@reports_bp.route('/scheduled', methods=['POST'])
@token_required
@permission_required('qc', 'write')
def create_scheduled_report():
    data = request.get_json()
    user_id = request.current_user['user_id']
    
    required_fields = ['report_name', 'report_type', 'recipients']
    for field in required_fields:
        if not data.get(field):
            return error_response(f'{field} is required', 400)
    
    if not data.get('recipients') or len(data['recipients']) == 0:
        return error_response('At least one recipient email is required', 400)
    
    report_config = {
        'filters': data.get('filters', {}),
        'output_format': data.get('output_format', 'pdf'),
        'include_charts': data.get('include_charts', True),
        'date_range': data.get('date_range', 'last_7_days')
    }
    
    schedule_config = data.get('schedule_config', {'type': 'manual'})
    
    next_run_at = None
    if schedule_config.get('type') != 'manual':
        next_run_at = calculate_next_run_time(schedule_config)
    
    query = """
        INSERT INTO email_reports
        (report_name, report_type, report_config, schedule_config, recipients, 
         next_run_at, created_by_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    
    try:
        report_id = execute_query(
            query,
            (
                data['report_name'],
                data['report_type'],
                json.dumps(report_config),
                json.dumps(schedule_config),
                json.dumps(data.get('recipients', [])),
                next_run_at,
                user_id
            ),
            commit=True
        )
        
        log_audit(user_id, 'CREATE', 'email_report', report_id, None, data)
        
        return success_response({
            'id': report_id,
            'next_run_at': next_run_at.isoformat() if next_run_at else None
        }, 'Scheduled report created successfully', 201)
    except Exception as e:
        return error_response(str(e), 500)


def calculate_next_run_time(schedule_config):
    """Calculate the next run time based on schedule configuration"""
    schedule_type = schedule_config.get('type', 'manual')
    now = datetime.now()
    
    if schedule_type == 'daily':
        hour = schedule_config.get('hour', 8)
        minute = schedule_config.get('minute', 0)
        next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if next_run <= now:
            next_run += timedelta(days=1)
        return next_run
    
    elif schedule_type == 'weekly':
        day_of_week = schedule_config.get('day_of_week', 1)
        hour = schedule_config.get('hour', 8)
        minute = schedule_config.get('minute', 0)
        days_ahead = day_of_week - now.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        next_run = now + timedelta(days=days_ahead)
        next_run = next_run.replace(hour=hour, minute=minute, second=0, microsecond=0)
        return next_run
    
    elif schedule_type == 'monthly':
        day_of_month = schedule_config.get('day_of_month', 1)
        hour = schedule_config.get('hour', 8)
        minute = schedule_config.get('minute', 0)
        next_run = now.replace(day=day_of_month, hour=hour, minute=minute, second=0, microsecond=0)
        if next_run <= now:
            if now.month == 12:
                next_run = next_run.replace(year=now.year + 1, month=1)
            else:
                next_run = next_run.replace(month=now.month + 1)
        return next_run
    
    return None

@reports_bp.route('/scheduled/<int:id>', methods=['GET'])
@token_required
def get_scheduled_report(id):
    query = """
        SELECT er.*, CONCAT(u.first_name, ' ', u.last_name) as created_by_name
        FROM email_reports er
        LEFT JOIN users u ON er.created_by_id = u.id
        WHERE er.id = %s
    """
    report = execute_query(query, (id,), fetch_one=True)
    
    if not report:
        return error_response('Report not found', 404)
    
    return success_response(report)

@reports_bp.route('/scheduled/<int:id>', methods=['PUT'])
@token_required
@permission_required('qc', 'write')
def update_scheduled_report(id):
    data = request.get_json()
    user_id = request.current_user['user_id']
    
    old_data = execute_query("SELECT * FROM email_reports WHERE id = %s", (id,), fetch_one=True)
    if not old_data:
        return error_response('Report not found', 404)
    
    report_config = data.get('report_config')
    if report_config and isinstance(report_config, dict):
        report_config = json.dumps(report_config)
    else:
        report_config = old_data['report_config']
    
    schedule_config = data.get('schedule_config')
    next_run_at = old_data['next_run_at']
    
    if schedule_config and isinstance(schedule_config, dict):
        next_run_at = calculate_next_run_time(schedule_config)
        schedule_config = json.dumps(schedule_config)
    else:
        schedule_config = old_data['schedule_config']
    
    recipients = data.get('recipients')
    if recipients and isinstance(recipients, list):
        recipients = json.dumps(recipients)
    else:
        recipients = old_data['recipients']
    
    query = """
        UPDATE email_reports SET
            report_name = %s,
            report_type = %s,
            report_config = %s,
            schedule_config = %s,
            recipients = %s,
            next_run_at = %s,
            is_active = %s
        WHERE id = %s
    """
    
    try:
        execute_query(
            query,
            (
                data.get('report_name', old_data['report_name']),
                data.get('report_type', old_data['report_type']),
                report_config,
                schedule_config,
                recipients,
                next_run_at,
                data.get('is_active', old_data['is_active']),
                id
            ),
            commit=True
        )
        
        log_audit(user_id, 'UPDATE', 'email_report', id, old_data, data)
        
        return success_response(message='Report updated successfully')
    except Exception as e:
        return error_response(str(e), 500)

@reports_bp.route('/scheduled/<int:id>/run', methods=['POST'])
@token_required
def run_scheduled_report(id):
    user_id = request.current_user['user_id']
    
    report = execute_query("SELECT * FROM email_reports WHERE id = %s", (id,), fetch_one=True)
    if not report:
        return error_response('Report not found', 404)
    
    try:
        result = execute_scheduled_report(id)
        
        execute_query(
            "UPDATE email_reports SET last_run_at = NOW() WHERE id = %s",
            (id,),
            commit=True
        )
        
        log_audit(user_id, 'RUN_REPORT', 'email_report', id)
        
        return success_response(result, 'Report generated and sent successfully')
    except Exception as e:
        return error_response(f'Report execution failed: {str(e)}', 500)


@reports_bp.route('/scheduled/<int:id>/delete', methods=['DELETE'])
@token_required
@permission_required('qc', 'write')
def delete_scheduled_report(id):
    user_id = request.current_user['user_id']
    
    report = execute_query("SELECT * FROM email_reports WHERE id = %s", (id,), fetch_one=True)
    if not report:
        return error_response('Report not found', 404)
    
    try:
        execute_query("DELETE FROM email_reports WHERE id = %s", (id,), commit=True)
        log_audit(user_id, 'DELETE', 'email_report', id, report, None)
        return success_response(message='Report deleted successfully')
    except Exception as e:
        return error_response(str(e), 500)


@reports_bp.route('/templates', methods=['GET'])
@token_required
def get_report_templates():
    """Get available report templates/types"""
    templates = [
        {
            'id': 'defects_summary',
            'name': 'Defects Summary Report',
            'description': 'Summary of internal rejects and customer returns',
            'category': 'defects',
            'available_filters': ['department', 'date_range', 'rejection_type']
        },
        {
            'id': 'defects_detailed',
            'name': 'Detailed Defects Report',
            'description': 'Detailed breakdown of all defects with cost impact',
            'category': 'defects',
            'available_filters': ['department', 'date_range', 'rejection_type', 'product']
        },
        {
            'id': 'customer_returns',
            'name': 'Customer Returns Report',
            'description': 'Analysis of customer returns',
            'category': 'defects',
            'available_filters': ['date_range', 'return_type', 'product', 'customer']
        },
        {
            'id': 'production_summary',
            'name': 'Production Summary Report',
            'description': 'Production performance by department',
            'category': 'production',
            'available_filters': ['department', 'date_range']
        },
        {
            'id': 'maintenance_summary',
            'name': 'Maintenance Summary Report',
            'description': 'Maintenance activities and downtime analysis',
            'category': 'maintenance',
            'available_filters': ['department', 'date_range', 'machine']
        },
        {
            'id': 'sop_summary',
            'name': 'SOP Failures Report',
            'description': 'SOP failure tickets and NCR summary',
            'category': 'sop',
            'available_filters': ['department', 'date_range', 'status']
        },
        {
            'id': 'cost_impact',
            'name': 'Cost Impact Analysis',
            'description': 'Financial impact of defects and returns',
            'category': 'finance',
            'available_filters': ['department', 'date_range', 'product']
        }
    ]
    return success_response(templates)

@reports_bp.route('/defects/summary', methods=['GET'])
@token_required
def defects_summary():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    department_id = request.args.get('department_id')
    
    query = """
        SELECT 
            d.name as department_name,
            rt.rejection_type,
            COUNT(*) as count,
            SUM(rt.quantity_rejected) as total_quantity
        FROM replacement_tickets rt
        LEFT JOIN departments d ON rt.department_id = d.id
        WHERE 1=1
    """
    
    params = []
    if start_date:
        query += " AND rt.created_at >= %s"
        params.append(start_date)
    
    if end_date:
        query += " AND rt.created_at <= %s"
        params.append(end_date)
    
    if department_id:
        query += " AND rt.department_id = %s"
        params.append(department_id)
    
    query += " GROUP BY d.name, rt.rejection_type ORDER BY count DESC"
    
    results = execute_query(query, tuple(params) if params else None, fetch_all=True)
    return success_response(results)

@reports_bp.route('/production/summary', methods=['GET'])
@token_required
def production_summary():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    department_id = request.args.get('department_id')
    
    query = """
        SELECT 
            d.name as department_name,
            COUNT(DISTINCT js.id) as total_jobs,
            SUM(js.scheduled_quantity) as scheduled_quantity,
            SUM(js.actual_quantity) as actual_quantity,
            COUNT(CASE WHEN js.status = 'completed' THEN 1 END) as completed_jobs,
            COUNT(CASE WHEN js.status = 'in_progress' THEN 1 END) as in_progress_jobs
        FROM job_schedules js
        LEFT JOIN departments d ON js.department_id = d.id
        WHERE 1=1
    """
    
    params = []
    if start_date:
        query += " AND js.scheduled_date >= %s"
        params.append(start_date)
    
    if end_date:
        query += " AND js.scheduled_date <= %s"
        params.append(end_date)
    
    if department_id:
        query += " AND js.department_id = %s"
        params.append(department_id)
    
    query += " GROUP BY d.name ORDER BY d.name"
    
    results = execute_query(query, tuple(params) if params else None, fetch_all=True)
    return success_response(results)

@reports_bp.route('/maintenance/summary', methods=['GET'])
@token_required
def maintenance_summary():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    query = """
        SELECT 
            m.machine_name,
            d.name as department_name,
            COUNT(*) as ticket_count,
            AVG(mt.downtime_minutes) as avg_downtime,
            SUM(mt.downtime_minutes) as total_downtime,
            COUNT(CASE WHEN mt.status = 'completed' THEN 1 END) as completed_count,
            COUNT(CASE WHEN mt.status IN ('open', 'assigned', 'in_progress') THEN 1 END) as pending_count
        FROM maintenance_tickets mt
        LEFT JOIN machines m ON mt.machine_id = m.id
        LEFT JOIN departments d ON mt.department_id = d.id
        WHERE 1=1
    """
    
    params = []
    if start_date:
        query += " AND mt.created_at >= %s"
        params.append(start_date)
    
    if end_date:
        query += " AND mt.created_at <= %s"
        params.append(end_date)
    
    query += " GROUP BY m.id, d.name ORDER BY ticket_count DESC"
    
    results = execute_query(query, tuple(params) if params else None, fetch_all=True)
    return success_response(results)

@reports_bp.route('/sop/summary', methods=['GET'])
@token_required
def sop_summary():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    query = """
        SELECT 
            d.name as department_name,
            COUNT(*) as total_tickets,
            COUNT(CASE WHEN st.status = 'ncr_completed' THEN 1 END) as completed_count,
            COUNT(CASE WHEN st.status = 'open' THEN 1 END) as open_count,
            COUNT(CASE WHEN st.status = 'reassigned' THEN 1 END) as reassigned_count,
            COUNT(CASE WHEN st.escalated_to_hod = TRUE THEN 1 END) as escalated_count
        FROM sop_failure_tickets st
        LEFT JOIN departments d ON st.charged_department_id = d.id
        WHERE 1=1
    """
    
    params = []
    if start_date:
        query += " AND st.created_at >= %s"
        params.append(start_date)
    
    if end_date:
        query += " AND st.created_at <= %s"
        params.append(end_date)
    
    query += " GROUP BY d.name ORDER BY total_tickets DESC"
    
    results = execute_query(query, tuple(params) if params else None, fetch_all=True)
    return success_response(results)
