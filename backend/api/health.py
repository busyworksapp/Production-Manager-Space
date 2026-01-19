from flask import Blueprint, jsonify
from backend.config.db_pool import db_pool
from backend.config.redis_config import redis_client
from backend.utils.response import success_response, error_response
from backend.utils.logger import app_logger
from datetime import datetime
import os
import psutil

health_bp = Blueprint('health', __name__, url_prefix='/api/health')

@health_bp.route('', methods=['GET'])
def health_check():
    return success_response({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': os.getenv('APP_VERSION', '1.0.0'),
        'environment': os.getenv('FLASK_ENV', 'production')
    })

@health_bp.route('/detailed', methods=['GET'])
def detailed_health_check():
    health_status = {
        'timestamp': datetime.utcnow().isoformat(),
        'version': os.getenv('APP_VERSION', '1.0.0'),
        'environment': os.getenv('FLASK_ENV', 'production'),
        'services': {}
    }
    
    all_healthy = True
    
    try:
        with db_pool.get_cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        health_status['services']['database'] = {
            'status': 'healthy',
            'pool_size': db_pool._connection_count,
            'max_pool_size': db_pool.max_connections
        }
    except Exception as e:
        all_healthy = False
        health_status['services']['database'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
        app_logger.error(f"Database health check failed: {str(e)}")
    
    try:
        redis_client.ping()
        health_status['services']['redis'] = {
            'status': 'healthy'
        }
    except Exception as e:
        all_healthy = False
        health_status['services']['redis'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
        app_logger.error(f"Redis health check failed: {str(e)}")
    
    try:
        process = psutil.Process()
        health_status['system'] = {
            'cpu_percent': psutil.cpu_percent(interval=0.1),
            'memory_percent': psutil.virtual_memory().percent,
            'process_memory_mb': process.memory_info().rss / 1024 / 1024,
            'disk_percent': psutil.disk_usage('/').percent
        }
    except Exception as e:
        app_logger.warning(f"System metrics unavailable: {str(e)}")
    
    health_status['status'] = 'healthy' if all_healthy else 'degraded'
    
    status_code = 200 if all_healthy else 503
    return jsonify(health_status), status_code

@health_bp.route('/ready', methods=['GET'])
def readiness_check():
    try:
        with db_pool.get_cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        
        redis_client.ping()
        
        return success_response({
            'status': 'ready',
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        app_logger.error(f"Readiness check failed: {str(e)}")
        return error_response('Service not ready', 503)

@health_bp.route('/live', methods=['GET'])
def liveness_check():
    return success_response({
        'status': 'alive',
        'timestamp': datetime.utcnow().isoformat()
    })
