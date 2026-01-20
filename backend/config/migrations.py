"""Database migrations - run automatically on app startup"""
import os
from backend.config.db_pool import get_db_connection
from backend.utils.logger import app_logger


def run_migrations():
    """Run all database migrations"""
    try:
        # Migration 1: Add cost_impact column to replacement_tickets
        add_cost_impact_to_replacement_tickets()
    except Exception as e:
        app_logger.error(f"Migration error: {e}", exc_info=True)


def add_cost_impact_to_replacement_tickets():
    """Add cost_impact column to replacement_tickets table if it doesn't exist"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if column exists
        cursor.execute("""
            SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = 'replacement_tickets' 
            AND COLUMN_NAME = 'cost_impact'
            AND TABLE_SCHEMA = DATABASE()
        """)
        
        if not cursor.fetchone():
            # Column doesn't exist, add it
            app_logger.info("Adding cost_impact column to replacement_tickets...")
            cursor.execute("""
                ALTER TABLE replacement_tickets 
                ADD COLUMN cost_impact DECIMAL(12,2) DEFAULT 0 
                AFTER rejection_type
            """)
            conn.commit()
            app_logger.info("✓ Successfully added cost_impact column")
        else:
            app_logger.debug("cost_impact column already exists")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        app_logger.error(f"Failed to migrate replacement_tickets: {e}")
        raise
