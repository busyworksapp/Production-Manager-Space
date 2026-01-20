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
    if auth_type == 'oauth':
        access_token = get_oauth_token(auth_creds)
        return {
            'Authorization': f"Bearer {access_token}",
            'Content-Type': 'application/json',
            'OData-MaxVersion': '4.0',
            'OData-Version': '4.0'
        }
    elif auth_type == 'api_key':
        return {
            'Authorization': f"Bearer {auth_creds.get('api_key')}",
            'Content-Type': 'application/json'
        }
    elif auth_type == 'basic':
        import base64
        credentials = f"{auth_creds.get('username')}:{auth_creds.get('password')}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return {
            'Authorization': f'Basic {encoded}',
            'Content-Type': 'application/json'
        }
    else:
        return {'Content-Type': 'application/json'}

def get_oauth_token(auth_creds):
    token_url = auth_creds.get('token_url')
    client_id = auth_creds.get('client_id')
    client_secret = auth_creds.get('client_secret')
    resource = auth_creds.get('resource')
    
    if not all([token_url, client_id, client_secret, resource]):
        raise ValueError('Missing OAuth credentials')
    
    payload = {
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret,
        'resource': resource
    }
    
    response = requests.post(token_url, data=payload, timeout=10)
    
    if response.status_code == 200:
        return response.json().get('access_token')
    else:
        raise Exception(f'OAuth token request failed: {response.text}')

def fetch_from_d365(endpoint_url, entity_type, headers):
    entity_endpoints = {
        'sales_orders': '/salesorders',
        'products': '/products',
        'customers': '/accounts'
    }
    
    entity_path = entity_endpoints.get(entity_type, f'/{entity_type}')
    full_url = f"{endpoint_url.rstrip('/')}{entity_path}"
    
    try:
        response = requests.get(full_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        if 'value' in data:
            return data['value']
        elif isinstance(data, list):
            return data
        else:
            return [data]
            
    except requests.exceptions.RequestException as e:
        raise Exception(f'Failed to fetch {entity_type} from D365: {str(e)}')

def import_records(entity_type, records, field_mapping):
    if entity_type == 'sales_orders':
        import_sales_orders(records, field_mapping)
    elif entity_type == 'products':
        import_products(records, field_mapping)
    elif entity_type == 'customers':
        import_customers(records, field_mapping)

def import_sales_orders(orders, field_mapping):
    for d365_order in orders:
        try:
            order_number = map_field(d365_order, field_mapping, 'order_number', 'SalesOrderNumber')
            customer_name = map_field(d365_order, field_mapping, 'customer_name', 'CustomerName')
            quantity = map_field(d365_order, field_mapping, 'quantity', 'Quantity', default=0)
            order_value = map_field(d365_order, field_mapping, 'order_value', 'TotalAmount', default=0)
            start_date = map_field(d365_order, field_mapping, 'start_date', 'RequestedDeliveryDate')
            
            existing = execute_query(
                "SELECT id FROM orders WHERE order_number = %s",
                (order_number,),
                fetch_one=True
            )
            
            if existing:
                execute_query(
                    """UPDATE orders SET
                       customer_name = %s, quantity = %s, order_value = %s,
                       start_date = %s, d365_sync_id = %s, last_d365_sync = NOW()
                       WHERE order_number = %s""",
                    (customer_name, quantity, order_value, start_date, 
                     d365_order.get('Id') or d365_order.get('SalesOrderId'), order_number),
                    commit=True
                )
            else:
                execute_query(
                    """INSERT INTO orders
                       (order_number, customer_name, quantity, order_value,
                        start_date, status, d365_sync_id, last_d365_sync)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())""",
                    (order_number, customer_name, quantity, order_value,
                     start_date, 'unscheduled', d365_order.get('Id') or d365_order.get('SalesOrderId')),
                    commit=True
                )
                
        except Exception as e:
            print(f"Failed to import order {d365_order.get('SalesOrderNumber', 'unknown')}: {str(e)}")
            continue

def import_products(products, field_mapping):
    for d365_product in products:
        try:
            product_name = map_field(d365_product, field_mapping, 'product_name', 'Name')
            product_code = map_field(d365_product, field_mapping, 'product_code', 'ProductNumber')
            category = map_field(d365_product, field_mapping, 'category', 'Category')
            
            existing = execute_query(
                "SELECT id FROM products WHERE product_code = %s",
                (product_code,),
                fetch_one=True
            )
            
            if existing:
                execute_query(
                    """UPDATE products SET
                       product_name = %s, category = %s, d365_sync_id = %s
                       WHERE product_code = %s""",
                    (product_name, category, d365_product.get('Id') or d365_product.get('ProductId'), product_code),
                    commit=True
                )
            else:
                execute_query(
                    """INSERT INTO products
                       (product_name, product_code, category, d365_sync_id)
                       VALUES (%s, %s, %s, %s)""",
                    (product_name, product_code, category, d365_product.get('Id') or d365_product.get('ProductId')),
                    commit=True
                )
                
        except Exception as e:
            print(f"Failed to import product {d365_product.get('ProductNumber', 'unknown')}: {str(e)}")
            continue

def import_customers(customers, field_mapping):
    pass

def fetch_from_pms(entity_type):
    if entity_type == 'sales_orders':
        return execute_query(
            """SELECT * FROM orders 
               WHERE status = 'completed' 
               AND (last_d365_sync IS NULL OR updated_at > last_d365_sync)
               ORDER BY completed_at DESC
               LIMIT 100""",
            fetch_all=True
        ) or []
    elif entity_type == 'products':
        return execute_query(
            "SELECT * FROM products WHERE is_active = TRUE",
            fetch_all=True
        ) or []
    else:
        return []

def export_to_d365(endpoint_url, entity_type, records, headers, field_mapping):
    entity_endpoints = {
        'sales_orders': '/salesorders',
        'products': '/products'
    }
    
    entity_path = entity_endpoints.get(entity_type, f'/{entity_type}')
    full_url = f"{endpoint_url.rstrip('/')}{entity_path}"
    
    for record in records:
        try:
            d365_payload = map_pms_to_d365(entity_type, record, field_mapping)
            
            if record.get('d365_sync_id'):
                update_url = f"{full_url}({record['d365_sync_id']})"
                response = requests.patch(update_url, json=d365_payload, headers=headers, timeout=30)
            else:
                response = requests.post(full_url, json=d365_payload, headers=headers, timeout=30)
            
            response.raise_for_status()
            
            if not record.get('d365_sync_id') and response.status_code == 201:
                new_id = response.json().get('Id') or response.json().get('SalesOrderId')
                execute_query(
                    f"UPDATE {get_pms_table(entity_type)} SET d365_sync_id = %s, last_d365_sync = NOW() WHERE id = %s",
                    (new_id, record['id']),
                    commit=True
                )
            else:
                execute_query(
                    f"UPDATE {get_pms_table(entity_type)} SET last_d365_sync = NOW() WHERE id = %s",
                    (record['id'],),
                    commit=True
                )
                
        except Exception as e:
            print(f"Failed to export {entity_type} record {record.get('id')}: {str(e)}")
            continue

def map_field(source_record, field_mapping, pms_field, default_d365_field, default=None):
    d365_field = field_mapping.get(pms_field, default_d365_field)
    return source_record.get(d365_field, default)

def map_pms_to_d365(entity_type, pms_record, field_mapping):
    if entity_type == 'sales_orders':
        return {
            field_mapping.get('order_number', 'SalesOrderNumber'): pms_record.get('order_number'),
            field_mapping.get('customer_name', 'CustomerName'): pms_record.get('customer_name'),
            field_mapping.get('quantity', 'Quantity'): pms_record.get('quantity'),
            field_mapping.get('order_value', 'TotalAmount'): pms_record.get('order_value'),
            field_mapping.get('status', 'Status'): pms_record.get('status')
        }
    return {}

def get_pms_table(entity_type):
    tables = {
        'sales_orders': 'orders',
        'products': 'products',
        'customers': 'customers'
    }
    return tables.get(entity_type, entity_type)
