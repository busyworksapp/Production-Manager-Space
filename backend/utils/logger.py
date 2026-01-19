import logging
import os
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from datetime import datetime
import json

LOG_DIR = 'logs'
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        if hasattr(record, 'user_id'):
            log_data['user_id'] = record.user_id
        
        if hasattr(record, 'ip_address'):
            log_data['ip_address'] = record.ip_address
        
        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id
        
        return json.dumps(log_data)

class CustomFormatter(logging.Formatter):
    grey = "\x1b[38;21m"
    blue = "\x1b[38;5;39m"
    yellow = "\x1b[38;5;226m"
    red = "\x1b[38;5;196m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"

    FORMATS = {
        logging.DEBUG: grey + "%(asctime)s - %(name)s - %(levelname)s - %(message)s" + reset,
        logging.INFO: blue + "%(asctime)s - %(name)s - %(levelname)s - %(message)s" + reset,
        logging.WARNING: yellow + "%(asctime)s - %(name)s - %(levelname)s - %(message)s" + reset,
        logging.ERROR: red + "%(asctime)s - %(name)s - %(levelname)s - %(message)s" + reset,
        logging.CRITICAL: bold_red + "%(asctime)s - %(name)s - %(levelname)s - %(message)s" + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt='%Y-%m-%d %H:%M:%S')
        return formatter.format(record)

def setup_logger(name, level=None):
    if level is None:
        level = logging.DEBUG if os.getenv('FLASK_ENV') == 'development' else logging.INFO
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    if logger.handlers:
        return logger
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(CustomFormatter())
    logger.addHandler(console_handler)
    
    app_file_handler = RotatingFileHandler(
        os.path.join(LOG_DIR, 'app.log'),
        maxBytes=10 * 1024 * 1024,
        backupCount=10
    )
    app_file_handler.setLevel(logging.INFO)
    app_file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    logger.addHandler(app_file_handler)
    
    error_file_handler = RotatingFileHandler(
        os.path.join(LOG_DIR, 'error.log'),
        maxBytes=10 * 1024 * 1024,
        backupCount=10
    )
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s\n%(exc_info)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    logger.addHandler(error_file_handler)
    
    json_handler = TimedRotatingFileHandler(
        os.path.join(LOG_DIR, 'app.json.log'),
        when='midnight',
        interval=1,
        backupCount=30
    )
    json_handler.setLevel(logging.INFO)
    json_handler.setFormatter(JSONFormatter())
    logger.addHandler(json_handler)
    
    logger.propagate = False
    
    return logger

def get_logger(name):
    return logging.getLogger(name) if logging.getLogger(name).handlers else setup_logger(name)

app_logger = setup_logger('pms')
db_logger = setup_logger('pms.database')
api_logger = setup_logger('pms.api')
auth_logger = setup_logger('pms.auth')
security_logger = setup_logger('pms.security')
audit_logger = setup_logger('pms.audit')
