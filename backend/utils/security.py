from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask import request
import os
import hashlib
import secrets
from backend.utils.logger import security_logger

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{os.getenv('RATE_LIMIT_PER_MINUTE', 60)}/minute"],
    storage_uri=os.getenv('REDIS_URL'),
    strategy="fixed-window"
)

def get_client_ip():
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    return request.remote_addr

def generate_csrf_token():
    return secrets.token_hex(32)

def validate_csrf_token(token, stored_token):
    if not token or not stored_token:
        return False
    return secrets.compare_digest(token, stored_token)

def hash_data(data):
    return hashlib.sha256(data.encode()).hexdigest()

def validate_file_upload(file, allowed_extensions={'xlsx', 'xls', 'csv'}, max_size_mb=50):
    if not file:
        return False, "No file provided"
    
    if file.filename == '':
        return False, "Empty filename"
    
    ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
    if ext not in allowed_extensions:
        return False, f"File type not allowed. Allowed types: {', '.join(allowed_extensions)}"
    
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    
    max_size_bytes = max_size_mb * 1024 * 1024
    if file_size > max_size_bytes:
        return False, f"File too large. Maximum size: {max_size_mb}MB"
    
    return True, "File valid"

def sanitize_filename(filename):
    import re
    filename = re.sub(r'[^\w\s.-]', '', filename)
    filename = re.sub(r'[-\s]+', '-', filename)
    return filename.strip('.-')

def log_security_event(event_type, details, user_id=None):
    security_logger.warning(f"Security Event: {event_type}", extra={
        'event_type': event_type,
        'details': details,
        'user_id': user_id,
        'ip': get_client_ip(),
        'user_agent': request.user_agent.string if request else None
    })

def check_suspicious_activity(user_id, action):
    pass

class SecurityHeaders:
    @staticmethod
    def apply(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
        return response

def init_security(app):
    limiter.init_app(app)
    
    @app.after_request
    def apply_security_headers(response):
        return SecurityHeaders.apply(response)
    
    security_logger.info("Security module initialized with rate limiting and security headers")
