import jwt
import bcrypt
import os
import json
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify
from backend.config.database import execute_query

SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'your-secret-key-change-this')

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password, hashed):
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def generate_token(user_id, username, role_id):
    payload = {
        'user_id': user_id,
        'username': username,
        'role_id': role_id,
        'exp': datetime.utcnow() + timedelta(hours=24),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')

def decode_token(token):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(' ')[1]
            except IndexError:
                return jsonify({'error': 'Invalid token format'}), 401
        
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        
        payload = decode_token(token)
        if not payload:
            return jsonify({'error': 'Token is invalid or expired'}), 401
        
        request.current_user = payload
        return f(*args, **kwargs)
    
    return decorated

def permission_required(module, action):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user = request.current_user
            
            query = """
                SELECT r.permissions 
                FROM roles r
                JOIN users u ON u.role_id = r.id
                WHERE u.id = %s
            """
            role = execute_query(query, (user['user_id'],), fetch_one=True)
            
            if not role:
                return jsonify({'error': 'Unauthorized'}), 403
            
            permissions = role.get('permissions', '{}')
            
            # Parse permissions if it's a JSON string
            if isinstance(permissions, str):
                try:
                    permissions = json.loads(permissions)
                except (json.JSONDecodeError, TypeError, ValueError):
                    permissions = {}
            
            # Ensure permissions is a dict
            if not isinstance(permissions, dict):
                permissions = {}
            
            if permissions.get('all'):
                return f(*args, **kwargs)
            
            module_perms = permissions.get(module, {})
            if module_perms.get(action) or module_perms.get('all'):
                return f(*args, **kwargs)
            
            return jsonify({'error': 'Insufficient permissions'}), 403
        
        return decorated
    return decorator
