from backend.config.database import execute_query
from flask import request
import json

def log_audit(user_id, action, entity_type, entity_id, old_values=None, new_values=None):
    ip_address = request.remote_addr if request else None
    user_agent = request.headers.get('User-Agent') if request else None
    
    query = """
        INSERT INTO audit_logs 
        (user_id, action, entity_type, entity_id, old_values, new_values, ip_address, user_agent)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    execute_query(
        query,
        (
            user_id,
            action,
            entity_type,
            entity_id,
            json.dumps(old_values) if old_values else None,
            json.dumps(new_values) if new_values else None,
            ip_address,
            user_agent
        ),
        commit=True
    )
