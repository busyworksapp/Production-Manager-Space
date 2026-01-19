from flask import jsonify, request
from werkzeug.exceptions import HTTPException
import traceback
from backend.utils.logger import app_logger, security_logger
from backend.utils.response import error_response
import pymysql

class PMSException(Exception):
    def __init__(self, message, status_code=400, payload=None):
        super().__init__()
        self.message = message
        self.status_code = status_code
        self.payload = payload
    
    def to_dict(self):
        rv = dict(self.payload or ())
        rv['error'] = self.message
        rv['status'] = self.status_code
        return rv

class ValidationError(PMSException):
    def __init__(self, message, payload=None):
        super().__init__(message, status_code=400, payload=payload)

class AuthenticationError(PMSException):
    def __init__(self, message="Authentication required", payload=None):
        super().__init__(message, status_code=401, payload=payload)

class AuthorizationError(PMSException):
    def __init__(self, message="Insufficient permissions", payload=None):
        super().__init__(message, status_code=403, payload=payload)

class NotFoundError(PMSException):
    def __init__(self, message="Resource not found", payload=None):
        super().__init__(message, status_code=404, payload=payload)

class ConflictError(PMSException):
    def __init__(self, message="Resource conflict", payload=None):
        super().__init__(message, status_code=409, payload=payload)

class DatabaseError(PMSException):
    def __init__(self, message="Database operation failed", payload=None):
        super().__init__(message, status_code=500, payload=payload)

class BusinessLogicError(PMSException):
    def __init__(self, message, payload=None):
        super().__init__(message, status_code=422, payload=payload)

def register_error_handlers(app):
    
    @app.errorhandler(PMSException)
    def handle_pms_exception(error):
        app_logger.warning(f"PMS Exception: {error.message}", extra={
            'status_code': error.status_code,
            'path': request.path,
            'method': request.method
        })
        return jsonify(error.to_dict()), error.status_code
    
    @app.errorhandler(ValidationError)
    def handle_validation_error(error):
        app_logger.warning(f"Validation Error: {error.message}", extra={
            'path': request.path,
            'method': request.method,
            'payload': error.payload
        })
        return error_response(error.message, error.status_code)
    
    @app.errorhandler(AuthenticationError)
    def handle_auth_error(error):
        security_logger.warning(f"Authentication Error: {error.message}", extra={
            'path': request.path,
            'method': request.method,
            'ip': request.remote_addr
        })
        return error_response(error.message, error.status_code)
    
    @app.errorhandler(AuthorizationError)
    def handle_authz_error(error):
        security_logger.warning(f"Authorization Error: {error.message}", extra={
            'path': request.path,
            'method': request.method,
            'ip': request.remote_addr
        })
        return error_response(error.message, error.status_code)
    
    @app.errorhandler(404)
    def handle_not_found(error):
        app_logger.info(f"404 Not Found: {request.path}")
        return error_response("Resource not found", 404)
    
    @app.errorhandler(405)
    def handle_method_not_allowed(error):
        app_logger.warning(f"405 Method Not Allowed: {request.method} {request.path}")
        return error_response(f"Method {request.method} not allowed for this endpoint", 405)
    
    @app.errorhandler(413)
    def handle_request_entity_too_large(error):
        app_logger.warning(f"413 Request Entity Too Large: {request.path}")
        return error_response("File upload too large", 413)
    
    @app.errorhandler(429)
    def handle_rate_limit_exceeded(error):
        security_logger.warning(f"429 Rate Limit Exceeded: {request.path}", extra={
            'ip': request.remote_addr
        })
        return error_response("Rate limit exceeded. Please try again later.", 429)
    
    @app.errorhandler(pymysql.Error)
    def handle_database_error(error):
        app_logger.error(f"Database Error: {str(error)}", extra={
            'path': request.path,
            'method': request.method,
            'error_code': error.args[0] if error.args else None
        }, exc_info=True)
        
        if isinstance(error, pymysql.IntegrityError):
            return error_response("Data integrity violation. Please check your input.", 409)
        elif isinstance(error, pymysql.OperationalError):
            return error_response("Database connection error. Please try again.", 503)
        else:
            return error_response("Database operation failed", 500)
    
    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        app_logger.warning(f"HTTP Exception: {error.code} - {error.description}", extra={
            'path': request.path,
            'method': request.method
        })
        return error_response(error.description, error.code)
    
    @app.errorhandler(Exception)
    def handle_generic_exception(error):
        app_logger.error(f"Unhandled Exception: {str(error)}", extra={
            'path': request.path,
            'method': request.method,
            'ip': request.remote_addr,
            'user_agent': request.user_agent.string
        }, exc_info=True)
        
        trace = traceback.format_exc()
        app_logger.error(f"Stack trace:\n{trace}")
        
        if app.debug:
            return error_response(f"Internal server error: {str(error)}", 500)
        else:
            return error_response("An unexpected error occurred. Please contact support.", 500)
    
    @app.before_request
    def log_request_info():
        app_logger.debug(f"Request: {request.method} {request.path}", extra={
            'ip': request.remote_addr,
            'user_agent': request.user_agent.string
        })
    
    @app.after_request
    def log_response_info(response):
        app_logger.debug(f"Response: {response.status_code} for {request.method} {request.path}")
        return response
