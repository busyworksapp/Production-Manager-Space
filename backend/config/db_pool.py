import pymysql
import os
from dotenv import load_dotenv
from queue import Queue, Empty
from threading import Lock
from contextlib import contextmanager
from backend.utils.logger import db_logger

load_dotenv()

class DatabaseConnectionPool:
    def __init__(self, min_connections=5, max_connections=20):
        self.min_connections = min_connections
        self.max_connections = max_connections
        self._pool = Queue(maxsize=max_connections)
        self._lock = Lock()
        self._connection_count = 0
        
        self.config = {
            'host': os.getenv('DB_HOST'),
            'port': int(os.getenv('DB_PORT', 3306)),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD'),
            'database': os.getenv('DB_NAME'),
            'charset': 'utf8mb4',
            'cursorclass': pymysql.cursors.DictCursor,
            'autocommit': False,
            'connect_timeout': 10,
            'read_timeout': 30,
            'write_timeout': 30
        }
        
        self._initialize_pool()
        db_logger.info(f"Database connection pool initialized with {self.min_connections} connections")
    
    def _create_connection(self):
        try:
            connection = pymysql.connect(**self.config)
            connection.ping(reconnect=True)
            db_logger.debug("Created new database connection")
            return connection
        except Exception as e:
            db_logger.error(f"Failed to create database connection: {str(e)}")
            raise
    
    def _initialize_pool(self):
        for _ in range(self.min_connections):
            try:
                conn = self._create_connection()
                self._pool.put(conn)
                self._connection_count += 1
            except Exception as e:
                db_logger.error(f"Failed to initialize connection pool: {str(e)}")
                raise
    
    def get_connection(self, timeout=5):
        try:
            connection = self._pool.get(timeout=timeout)
            
            if not connection.open:
                db_logger.warning("Retrieved dead connection, creating new one")
                connection = self._create_connection()
            else:
                connection.ping(reconnect=True)
            
            return connection
        except Empty:
            with self._lock:
                if self._connection_count < self.max_connections:
                    connection = self._create_connection()
                    self._connection_count += 1
                    db_logger.info(f"Created additional connection. Pool size: {self._connection_count}")
                    return connection
                else:
                    db_logger.error("Connection pool exhausted")
                    raise Exception("Connection pool exhausted, no available connections")
    
    def return_connection(self, connection):
        try:
            if connection and connection.open:
                connection.rollback()
                self._pool.put(connection)
            else:
                db_logger.warning("Attempted to return dead connection")
                with self._lock:
                    self._connection_count -= 1
        except Exception as e:
            db_logger.error(f"Error returning connection to pool: {str(e)}")
    
    def close_all(self):
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                conn.close()
                self._connection_count -= 1
            except Empty:
                break
        db_logger.info("All database connections closed")
    
    @contextmanager
    def get_cursor(self, commit=False):
        connection = None
        cursor = None
        try:
            connection = self.get_connection()
            cursor = connection.cursor()
            yield cursor
            if commit:
                connection.commit()
                db_logger.debug("Transaction committed")
        except Exception as e:
            if connection:
                connection.rollback()
                db_logger.error(f"Transaction rolled back due to error: {str(e)}")
            raise
        finally:
            if cursor:
                cursor.close()
            if connection:
                self.return_connection(connection)

db_pool = DatabaseConnectionPool(
    min_connections=int(os.getenv('DB_POOL_MIN', 5)),
    max_connections=int(os.getenv('DB_POOL_MAX', 20))
)

def get_db_connection():
    return db_pool.get_connection()

def return_db_connection(connection):
    db_pool.return_connection(connection)

@contextmanager
def get_db_cursor(commit=False):
    with db_pool.get_cursor(commit=commit) as cursor:
        yield cursor

def execute_query(query, params=None, fetch_one=False, fetch_all=False, commit=False):
    try:
        with get_db_cursor(commit=commit) as cursor:
            cursor.execute(query, params or ())
            
            if commit:
                last_id = cursor.lastrowid
                db_logger.debug(f"Query executed and committed. Last ID: {last_id}")
                return last_id
            
            if fetch_one:
                result = cursor.fetchone()
                db_logger.debug("Query executed, fetched one row")
                return result
            
            if fetch_all:
                result = cursor.fetchall()
                db_logger.debug(f"Query executed, fetched {len(result)} rows")
                return result
            
            return cursor
    except pymysql.Error as e:
        db_logger.error(f"Database query error: {str(e)}, Query: {query[:100]}...")
        raise
    except Exception as e:
        db_logger.error(f"Unexpected error during query execution: {str(e)}")
        raise

def execute_many(query, params_list, commit=True):
    try:
        with get_db_cursor(commit=commit) as cursor:
            cursor.executemany(query, params_list)
            affected = cursor.rowcount
            db_logger.info(f"Batch query executed, {affected} rows affected")
            return affected
    except pymysql.Error as e:
        db_logger.error(f"Database batch query error: {str(e)}")
        raise
    except Exception as e:
        db_logger.error(f"Unexpected error during batch query execution: {str(e)}")
        raise
