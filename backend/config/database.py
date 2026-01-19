from backend.config.db_pool import execute_query, execute_many, get_db_cursor
from backend.utils.logger import db_logger

db_logger.warning("database.py is deprecated. All imports now use db_pool.py")

def get_db():
    """DEPRECATED: Use get_db_cursor context manager from db_pool instead"""
    from backend.config.db_pool import get_db_connection
    db_logger.warning("get_db() is deprecated. Use context manager get_db_cursor() instead")
    return get_db_connection()

__all__ = ['execute_query', 'execute_many', 'get_db_cursor', 'get_db']
