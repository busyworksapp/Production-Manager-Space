from flask import Blueprint, request
from backend.config.database import execute_query
from backend.utils.auth import token_required, permission_required
from backend.utils.response import success_response, error_response
from backend.utils.audit import log_audit
from datetime import datetime, timedelta
import json
import requests

d365_bp = Blueprint('d365', __name__, url_prefix='/api/d365')

@d365_bp.route('/configurations', methods=['GET'])
@token_required
@permission_required('admin', 'read')
def get_configurations():
    is_active = request.args.get('is_active', 'true')
    
    query = "SELECT * FROM d365_integration_config WHERE 1=1"
    params = []
    
    if is_active.lower() == 'true':
        query += " AND is_active = TRUE"
    
    query += " ORDER BY config_name"
    
    configs = execute_query(query, tuple(params) if params else None, fetch_all=True)
    
    for config in configs:
        config['auth_credentials'] = '***HIDDEN***'
    
    return success_response(configs)

@d365_bp.route('/configurations/<int:id>', methods=['GET'])
@token_required
@permission_required('admin', 'read')
def get_configuration(id):
    config = execute_query("SELECT * FROM d365_integration_config WHERE id = %s", (id,), fetch_one=True)
    
    if not config:
        return error_response('Configuration not found', 404)
    
    config['auth_credentials'] = '***HIDDEN***'
    
    return success_response(config)

@d365_bp.route('/configurations', methods=['POST'])
@token_required
@permission_required('admin', 'write')
def create_configuration():
    data = request.get_json()
    user_id = request.current_user['user_id']
    
    required_fields = ['config_name', 'endpoint_url', 'auth_type', 'auth_credentials', 'sync_entities', 'field_mappings']
    for field in required_fields:
        if not data.get(field):
            return error_response(f'{field} is required', 400)
    
    next_sync = datetime.now() + timedelta(minutes=data.get('sync_frequency_minutes', 60))
    
    query = """
        INSERT INTO d365_integration_config
        (config_name, endpoint_url, auth_type, auth_credentials,
         sync_entities, sync_frequency_minutes, field_mappings,
         next_sync_at, created_by_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    try:
        config_id = execute_query(
            query,
            (
                data['config_name'],
                data['endpoint_url'],
                data['auth_type'],
                json.dumps(data['auth_credentials']),
                json.dumps(data['sync_entities']),
                data.get('sync_frequency_minutes', 60),
                json.dumps(data['field_mappings']),
                next_sync,
                user_id
            ),
            commit=True
        )
        
        log_audit(user_id, 'CREATE', 'd365_integration_config', config_id, None, data)
        
        return success_response({'id': config_id}, 'D365 configuration created successfully', 201)
    except Exception as e:
        return error_response(str(e), 500)

@d365_bp.route('/configurations/<int:id>', methods=['PUT'])
@token_required
@permission_required('admin', 'write')
def update_configuration(id):
    data = request.get_json()
    user_id = request.current_user['user_id']
    
    old_data = execute_query("SELECT * FROM d365_integration_config WHERE id = %s", (id,), fetch_one=True)
    if not old_data:
        return error_response('Configuration not found', 404)
    
    query = """
        UPDATE d365_integration_config SET
            config_name = %s, endpoint_url = %s, auth_type = %s,
            auth_credentials = %s, sync_entities = %s,
            sync_frequency_minutes = %s, field_mappings = %s
        WHERE id = %s
    """
    
    try:
        execute_query(
            query,
            (
                data.get('config_name', old_data['config_name']),
                data.get('endpoint_url', old_data['endpoint_url']),
                data.get('auth_type', old_data['auth_type']),
                json.dumps(data.get('auth_credentials', old_data['auth_credentials'])),
                json.dumps(data.get('sync_entities', old_data['sync_entities'])),
                data.get('sync_frequency_minutes', old_data['sync_frequency_minutes']),
                json.dumps(data.get('field_mappings', old_data['field_mappings'])),
                id
            ),
            commit=True
        )
        
        log_audit(user_id, 'UPDATE', 'd365_integration_config', id, old_data, data)
        
        return success_response(message='D365 configuration updated successfully')
    except Exception as e:
        return error_response(str(e), 500)

@d365_bp.route('/configurations/<int:id>/activate', methods=['POST'])
@token_required
@permission_required('admin', 'write')
def activate_configuration(id):
    user_id = request.current_user['user_id']
    
    execute_query("UPDATE d365_integration_config SET is_active = TRUE WHERE id = %s", (id,), commit=True)
    log_audit(user_id, 'ACTIVATE', 'd365_integration_config', id)
    
    return success_response(message='D365 configuration activated')

@d365_bp.route('/configurations/<int:id>/deactivate', methods=['POST'])
@token_required
@permission_required('admin', 'write')
def deactivate_configuration(id):
    user_id = request.current_user['user_id']
    
    execute_query("UPDATE d365_integration_config SET is_active = FALSE WHERE id = %s", (id,), commit=True)
    log_audit(user_id, 'DEACTIVATE', 'd365_integration_config', id)
    
    return success_response(message='D365 configuration deactivated')

@d365_bp.route('/sync/<int:config_id>', methods=['POST'])
@token_required
@permission_required('admin', 'write')
def trigger_sync(config_id):
    data = request.get_json()
    user_id = request.current_user['user_id']
    
    config = execute_query("SELECT * FROM d365_integration_config WHERE id = %s", (config_id,), fetch_one=True)
    if not config:
        return error_response('Configuration not found', 404)
    
    if not config['is_active']:
        return error_response('Configuration is not active', 400)
    
    entity_types = data.get('entity_types', json.loads(config['sync_entities']))
    
    log_id = execute_query(
        """INSERT INTO d365_sync_logs
           (config_id, entity_type, sync_direction, status)
           VALUES (%s, %s, %s, %s)""",
        (config_id, ','.join(entity_types), data.get('sync_direction', 'import'), 'in_progress'),
        commit=True
    )
    
    try:
        results = perform_sync(config, entity_types, data.get('sync_direction', 'import'))
        
        execute_query(
            """UPDATE d365_sync_logs SET
               records_processed = %s, records_success = %s, records_failed = %s,
               status = %s, sync_completed_at = %s
               WHERE id = %s""",
            (
                results['processed'],
                results['success'],
                results['failed'],
                'completed' if results['failed'] == 0 else 'partial',
                datetime.now(),
                log_id
            ),
            commit=True
        )
        
        execute_query(
            "UPDATE d365_integration_config SET last_sync_at = %s, next_sync_at = %s WHERE id = %s",
            (datetime.now(), datetime.now() + timedelta(minutes=config['sync_frequency_minutes']), config_id),
            commit=True
        )
        
        log_audit(user_id, 'D365_SYNC', 'd365_sync_log', log_id)
        
        return success_response({
            'sync_log_id': log_id,
            'results': results
        }, 'Sync completed successfully')
        
    except Exception as e:
        execute_query(
            """UPDATE d365_sync_logs SET
               status = 'failed', error_details = %s, sync_completed_at = %s
               WHERE id = %s""",
            (json.dumps({'error': str(e)}), datetime.now(), log_id),
            commit=True
        )
        
        return error_response(f'Sync failed: {str(e)}', 500)

@d365_bp.route('/sync-logs', methods=['GET'])
@token_required
@permission_required('admin', 'read')
def get_sync_logs():
    config_id = request.args.get('config_id')
    entity_type = request.args.get('entity_type')
    status = request.args.get('status')
    
    query = """
        SELECT sl.*, dc.config_name
        FROM d365_sync_logs sl
        LEFT JOIN d365_integration_config dc ON sl.config_id = dc.id
        WHERE 1=1
    """
    params = []
    
    if config_id:
        query += " AND sl.config_id = %s"
        params.append(config_id)
    
    if entity_type:
        query += " AND sl.entity_type = %s"
        params.append(entity_type)
    
    if status:
        query += " AND sl.status = %s"
        params.append(status)
    
    query += " ORDER BY sl.sync_started_at DESC LIMIT 100"
    
    logs = execute_query(query, tuple(params) if params else None, fetch_all=True)
    return success_response(logs)

@d365_bp.route('/test-connection/<int:config_id>', methods=['POST'])
@token_required
@permission_required('admin', 'write')
def test_connection(config_id):
    config = execute_query("SELECT * FROM d365_integration_config WHERE id = %s", (config_id,), fetch_one=True)
    
    if not config:
        return error_response('Configuration not found', 404)
    
    try:
        auth_creds = json.loads(config['auth_credentials'])
        headers = get_auth_headers(config['auth_type'], auth_creds)
        
        response = requests.get(config['endpoint_url'], headers=headers, timeout=10)
        
        if response.status_code == 200:
            return success_response({'connected': True}, 'Connection successful')
        else:
            return error_response(f'Connection failed: {response.status_code}', 400)
            
    except Exception as e:
        return error_response(f'Connection test failed: {str(e)}', 500)

def perform_sync(config, entity_types, sync_direction):
    processed = 0
    success = 0
    failed = 0
    
    auth_creds = json.loads(config['auth_credentials'])
    headers = get_auth_headers(config['auth_type'], auth_creds)
    field_mappings = json.loads(config['field_mappings'])
    
    for entity_type in entity_types:
        try:
            if sync_direction == 'import':
                records = fetch_from_d365(config['endpoint_url'], entity_type, headers)
                import_records(entity_type, records, field_mappings.get(entity_type, {}))
                processed += len(records)
                success += len(records)
            elif sync_direction == 'export':
                records = fetch_from_pms(entity_type)
                export_to_d365(config['endpoint_url'], entity_type, records, headers, field_mappings.get(entity_type, {}))
                processed += len(records)
                success += len(records)
        except Exception as e:
            failed += 1
    
    return {
        'processed': processed,
        'success': success,
        'failed': failed
    }

def get_auth_headers(auth_type, auth_creds):
    if auth_type == 'api_key':
        return {'Authorization': f"Bearer {auth_creds.get('api_key')}"}
    elif auth_type == 'basic':
        import base64
        credentials = f"{auth_creds.get('username')}:{auth_creds.get('password')}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return {'Authorization': f'Basic {encoded}'}
    else:
        return {}

def fetch_from_d365(endpoint_url, entity_type, headers):
    return []

def import_records(entity_type, records, field_mapping):
    pass

def fetch_from_pms(entity_type):
    return []

def export_to_d365(endpoint_url, entity_type, records, headers, field_mapping):
    pass
