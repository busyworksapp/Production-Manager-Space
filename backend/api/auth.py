from flask import Blueprint, request
from backend.config.database import execute_query
from backend.utils.auth import hash_password, verify_password, generate_token, token_required
from backend.utils.response import success_response, error_response
from backend.utils.audit import log_audit
from datetime import datetime

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return error_response('Username and password are required', 400)
    
    query = """
        SELECT u.id, u.username, u.password_hash, u.email, u.first_name, 
               u.last_name, u.role_id, r.name as role_name, r.permissions
        FROM users u
        LEFT JOIN roles r ON u.role_id = r.id
        WHERE u.username = %s AND u.is_active = TRUE
    """
    
    user = execute_query(query, (username,), fetch_one=True)
    
    if not user or not verify_password(password, user['password_hash']):
        return error_response('Invalid username or password', 401)
    
    execute_query(
        "UPDATE users SET last_login = %s WHERE id = %s",
        (datetime.now(), user['id']),
        commit=True
    )
    
    token = generate_token(user['id'], user['username'], user['role_id'])
    
    log_audit(user['id'], 'LOGIN', 'user', user['id'])
    
    return success_response({
        'token': token,
        'user': {
            'id': user['id'],
            'username': user['username'],
            'email': user['email'],
            'first_name': user['first_name'],
            'last_name': user['last_name'],
            'role_name': user['role_name'],
            'permissions': user['permissions']
        }
    })

@auth_bp.route('/me', methods=['GET'])
@token_required
def get_current_user():
    user_id = request.current_user['user_id']
    
    query = """
        SELECT u.id, u.username, u.email, u.first_name, u.last_name,
               r.name as role_name, r.permissions
        FROM users u
        LEFT JOIN roles r ON u.role_id = r.id
        WHERE u.id = %s
    """
    
    user = execute_query(query, (user_id,), fetch_one=True)
    
    if not user:
        return error_response('User not found', 404)
    
    return success_response(user)

@auth_bp.route('/change-password', methods=['POST'])
@token_required
def change_password():
    data = request.get_json()
    current_password = data.get('current_password')
    new_password = data.get('new_password')
    user_id = request.current_user['user_id']
    
    if not current_password or not new_password:
        return error_response('Current and new passwords are required', 400)
    
    user = execute_query(
        "SELECT password_hash FROM users WHERE id = %s",
        (user_id,),
        fetch_one=True
    )
    
    if not verify_password(current_password, user['password_hash']):
        return error_response('Current password is incorrect', 401)
    
    new_hash = hash_password(new_password)
    execute_query(
        "UPDATE users SET password_hash = %s WHERE id = %s",
        (new_hash, user_id),
        commit=True
    )
    
    log_audit(user_id, 'CHANGE_PASSWORD', 'user', user_id)
    
    return success_response(message='Password changed successfully')
