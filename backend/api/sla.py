from flask import Blueprint, request
from backend.config.database import execute_query
from backend.utils.auth import token_required, permission_required
from backend.utils.response import success_response, error_response
from backend.utils.audit import log_audit
from datetime import datetime, timedelta
import json

sla_bp = Blueprint('sla', __name__, url_prefix='/api/sla')

@sla_bp.route('/configurations', methods=['GET'])
@token_required
def get_sla_configurations():
    entity_type = request.args.get('entity_type')
    department_id = request.args.get('department_id')
    is_active = request.args.get('is_active', 'true')
    
    query = """
        SELECT sc.*, d.name as department_name
        FROM sla_configurations sc
        LEFT JOIN departments d ON sc.department_id = d.id
        WHERE 1=1
    """
    params = []
    
    if entity_type:
        query += " AND sc.entity_type = %s"
        params.append(entity_type)
    
    if department_id:
        query += " AND sc.department_id = %s"
        params.append(department_id)
    
    if is_active.lower() == 'true':
        query += " AND sc.is_active = TRUE"
    
    query += " ORDER BY sc.entity_type, sc.priority"
    
    slas = execute_query(query, tuple(params) if params else None, fetch_all=True)
    return success_response(slas)

@sla_bp.route('/configurations/<int:id>', methods=['GET'])
@token_required
def get_sla_configuration(id):
    query = """
        SELECT sc.*, d.name as department_name
        FROM sla_configurations sc
        LEFT JOIN departments d ON sc.department_id = d.id
        WHERE sc.id = %s
    """
    sla = execute_query(query, (id,), fetch_one=True)
    
    if not sla:
        return error_response('SLA configuration not found', 404)
    
    return success_response(sla)

@sla_bp.route('/configurations', methods=['POST'])
@token_required
@permission_required('admin', 'write')
def create_sla_configuration():
    data = request.get_json()
    user_id = request.current_user['user_id']
    
    required_fields = ['sla_name', 'entity_type', 'escalation_levels']
    for field in required_fields:
        if not data.get(field):
            return error_response(f'{field} is required', 400)
    
    query = """
        INSERT INTO sla_configurations
        (sla_name, entity_type, department_id, priority,
         response_time_minutes, resolution_time_minutes,
         escalation_levels, notification_rules, created_by_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    try:
        sla_id = execute_query(
            query,
            (
                data['sla_name'],
                data['entity_type'],
                data.get('department_id'),
                data.get('priority', 'normal'),
                data.get('response_time_minutes'),
                data.get('resolution_time_minutes'),
                json.dumps(data['escalation_levels']),
                json.dumps(data.get('notification_rules', {})),
                user_id
            ),
            commit=True
        )
        
        log_audit(user_id, 'CREATE', 'sla_configuration', sla_id, None, data)
        
        return success_response({'id': sla_id}, 'SLA configuration created successfully', 201)
    except Exception as e:
        return error_response(str(e), 500)

@sla_bp.route('/configurations/<int:id>', methods=['PUT'])
@token_required
@permission_required('admin', 'write')
def update_sla_configuration(id):
    data = request.get_json()
    user_id = request.current_user['user_id']
    
    old_data = execute_query("SELECT * FROM sla_configurations WHERE id = %s", (id,), fetch_one=True)
    if not old_data:
        return error_response('SLA configuration not found', 404)
    
    query = """
        UPDATE sla_configurations SET
            sla_name = %s, entity_type = %s, department_id = %s,
            priority = %s, response_time_minutes = %s,
            resolution_time_minutes = %s, escalation_levels = %s,
            notification_rules = %s
        WHERE id = %s
    """
    
    try:
        execute_query(
            query,
            (
                data.get('sla_name', old_data['sla_name']),
                data.get('entity_type', old_data['entity_type']),
                data.get('department_id', old_data['department_id']),
                data.get('priority', old_data['priority']),
                data.get('response_time_minutes', old_data['response_time_minutes']),
                data.get('resolution_time_minutes', old_data['resolution_time_minutes']),
                json.dumps(data.get('escalation_levels', old_data['escalation_levels'])),
                json.dumps(data.get('notification_rules', old_data['notification_rules'])),
                id
            ),
            commit=True
        )
        
        log_audit(user_id, 'UPDATE', 'sla_configuration', id, old_data, data)
        
        return success_response(message='SLA configuration updated successfully')
    except Exception as e:
        return error_response(str(e), 500)

@sla_bp.route('/tracking', methods=['GET'])
@token_required
def get_sla_tracking():
    entity_type = request.args.get('entity_type')
    entity_id = request.args.get('entity_id')
    status = request.args.get('status')
    
    query = """
        SELECT st.*, sc.sla_name, sc.entity_type
        FROM sla_tracking st
        LEFT JOIN sla_configurations sc ON st.sla_config_id = sc.id
        WHERE 1=1
    """
    params = []
    
    if entity_type:
        query += " AND st.entity_type = %s"
        params.append(entity_type)
    
    if entity_id:
        query += " AND st.entity_id = %s"
        params.append(entity_id)
    
    if status:
        query += " AND st.status = %s"
        params.append(status)
    
    query += " ORDER BY st.response_due_at"
    
    tracking = execute_query(query, tuple(params) if params else None, fetch_all=True)
    return success_response(tracking)

@sla_bp.route('/tracking/<int:id>', methods=['GET'])
@token_required
def get_sla_tracking_record(id):
    query = """
        SELECT st.*, sc.sla_name, sc.escalation_levels, sc.notification_rules
        FROM sla_tracking st
        LEFT JOIN sla_configurations sc ON st.sla_config_id = sc.id
        WHERE st.id = %s
    """
    tracking = execute_query(query, (id,), fetch_one=True)
    
    if not tracking:
        return error_response('SLA tracking record not found', 404)
    
    return success_response(tracking)

@sla_bp.route('/tracking', methods=['POST'])
@token_required
def create_sla_tracking():
    data = request.get_json()
    user_id = request.current_user['user_id']
    
    required_fields = ['sla_config_id', 'entity_type', 'entity_id']
    for field in required_fields:
        if not data.get(field):
            return error_response(f'{field} is required', 400)
    
    sla_config = execute_query(
        "SELECT * FROM sla_configurations WHERE id = %s",
        (data['sla_config_id'],),
        fetch_one=True
    )
    
    if not sla_config:
        return error_response('SLA configuration not found', 404)
    
    now = datetime.now()
    response_due = None
    resolution_due = None
    
    if sla_config['response_time_minutes']:
        response_due = now + timedelta(minutes=sla_config['response_time_minutes'])
    
    if sla_config['resolution_time_minutes']:
        resolution_due = now + timedelta(minutes=sla_config['resolution_time_minutes'])
    
    query = """
        INSERT INTO sla_tracking
        (sla_config_id, entity_type, entity_id, response_due_at, resolution_due_at)
        VALUES (%s, %s, %s, %s, %s)
    """
    
    try:
        tracking_id = execute_query(
            query,
            (
                data['sla_config_id'],
                data['entity_type'],
                data['entity_id'],
                response_due,
                resolution_due
            ),
            commit=True
        )
        
        log_audit(user_id, 'CREATE', 'sla_tracking', tracking_id, None, data)
        
        return success_response({'id': tracking_id}, 'SLA tracking created successfully', 201)
    except Exception as e:
        return error_response(str(e), 500)

@sla_bp.route('/tracking/<int:id>/respond', methods=['POST'])
@token_required
def mark_sla_responded(id):
    user_id = request.current_user['user_id']
    
    execute_query(
        "UPDATE sla_tracking SET responded_at = %s WHERE id = %s",
        (datetime.now(), id),
        commit=True
    )
    
    log_audit(user_id, 'SLA_RESPONDED', 'sla_tracking', id)
    
    return success_response(message='SLA marked as responded')

@sla_bp.route('/tracking/<int:id>/resolve', methods=['POST'])
@token_required
def mark_sla_resolved(id):
    user_id = request.current_user['user_id']
    
    execute_query(
        "UPDATE sla_tracking SET resolved_at = %s, status = 'resolved' WHERE id = %s",
        (datetime.now(), id),
        commit=True
    )
    
    log_audit(user_id, 'SLA_RESOLVED', 'sla_tracking', id)
    
    return success_response(message='SLA marked as resolved')

@sla_bp.route('/tracking/<int:id>/escalate', methods=['POST'])
@token_required
def escalate_sla(id):
    data = request.get_json()
    user_id = request.current_user['user_id']
    
    tracking = execute_query("SELECT * FROM sla_tracking WHERE id = %s", (id,), fetch_one=True)
    if not tracking:
        return error_response('SLA tracking record not found', 404)
    
    new_level = tracking['current_escalation_level'] + 1
    escalation_history = json.loads(tracking['escalation_history']) if tracking['escalation_history'] else []
    escalation_history.append({
        'level': new_level,
        'escalated_at': str(datetime.now()),
        'escalated_by': user_id,
        'reason': data.get('reason', 'Manual escalation')
    })
    
    execute_query(
        """UPDATE sla_tracking 
           SET current_escalation_level = %s, escalation_history = %s, status = 'at_risk'
           WHERE id = %s""",
        (new_level, json.dumps(escalation_history), id),
        commit=True
    )
    
    log_audit(user_id, 'SLA_ESCALATED', 'sla_tracking', id)
    
    return success_response(message='SLA escalated successfully')

@sla_bp.route('/breached', methods=['GET'])
@token_required
def get_breached_slas():
    query = """
        SELECT st.*, sc.sla_name, sc.entity_type
        FROM sla_tracking st
        LEFT JOIN sla_configurations sc ON st.sla_config_id = sc.id
        WHERE st.status IN ('at_risk', 'breached')
        AND st.resolved_at IS NULL
        ORDER BY st.resolution_due_at
    """
    
    breached = execute_query(query, fetch_all=True)
    return success_response(breached)
