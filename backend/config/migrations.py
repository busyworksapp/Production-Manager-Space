"""Database migrations - run automatically on app startup"""
import os
from backend.config.db_pool import get_db_connection
from backend.utils.logger import app_logger


def run_migrations():
    """Run all database migrations"""
    try:
        # Migration 1: Add cost_impact column to replacement_tickets
        add_cost_impact_to_replacement_tickets()
        # Migration 2: Ensure admin user has full permissions
        ensure_admin_has_full_permissions()
        # Migration 3: Update all role permissions
        update_role_permissions()
    except Exception as e:
        app_logger.error(f"Migration error: {e}", exc_info=True)


def add_cost_impact_to_replacement_tickets():
    """Add cost_impact column to replacement_tickets if missing"""
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
            app_logger.info("Adding cost_impact column to replacement_tickets")
            cursor.execute("""
                ALTER TABLE replacement_tickets
                ADD COLUMN cost_impact DECIMAL(12,2) DEFAULT 0
                AFTER rejection_type
            """)
            conn.commit()
            app_logger.info("Successfully added cost_impact column")
        else:
            app_logger.debug("cost_impact column already exists")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        app_logger.error(f"Failed to migrate replacement_tickets: {e}")
        raise


def ensure_admin_has_full_permissions():
    """Ensure admin user has System Admin role with all permissions"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if System Admin role exists
        cursor.execute("""
            SELECT id FROM roles WHERE name = 'System Admin'
        """)
        
        role_result = cursor.fetchone()
        
        if not role_result:
            # Create System Admin role if it doesn't exist
            app_logger.info("Creating System Admin role")
            cursor.execute("""
                INSERT INTO roles (name, description, permissions)
                VALUES (%s, %s, %s)
            """, ('System Admin', 'Full system access', '{"all": true}'))
            conn.commit()
            system_admin_id = cursor.lastrowid
            app_logger.info(f"Created System Admin role ID {system_admin_id}")
        else:
            system_admin_id = role_result['id']
        
        # Ensure admin user has System Admin role
        cursor.execute("""
            UPDATE users
            SET role_id = %s
            WHERE username = %s
        """, (system_admin_id, 'admin@barron'))
        
        conn.commit()
        app_logger.info("Ensured admin@barron has System Admin role")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        app_logger.error(f"Failed to ensure admin permissions: {e}")
        raise


def update_role_permissions():
    """Update all role permissions to match navigation modules"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        import json
        
        # Define role permissions aligned with frontend navigation
        role_permissions = {
            'System Admin': {'all': True},
            'Department Manager': {
                'planning': {'read': True, 'write': True},
                'qc': {'read': True},
                'maintenance': {'read': True},
                'admin': {'read': True}
            },
            'Planner': {
                'planning': {'read': True, 'write': True}
            },
            'Operator': {
                'planning': {'read': True},
                'sop': {'read': True, 'write': True}
            },
            'QC Coordinator': {
                'qc': {'read': True, 'write': True}
            },
            'Maintenance Technician': {
                'maintenance': {'read': True, 'write': True}
            },
            'admin': {'all': True},
            'manager': {
                'planning': {'read': True, 'write': True},
                'qc': {'read': True},
                'maintenance': {'read': True},
                'admin': {'read': True}
            },
            'supervisor': {
                'planning': {'read': True},
                'sop': {'read': True, 'write': True}
            },
            'finance': {
                'finance': {'read': True, 'write': True},
                'reports': {'read': True}
            }
        }
        
        updated_count = 0
        for role_name, permissions in role_permissions.items():
            permissions_json = json.dumps(permissions)
            
            cursor.execute("""
                UPDATE roles
                SET permissions = %s
                WHERE name = %s
            """, (permissions_json, role_name))
            
            if cursor.rowcount > 0:
                updated_count += 1
                app_logger.debug(f"Updated {role_name} permissions")
        
        conn.commit()
        if updated_count > 0:
            app_logger.info(f"Updated {updated_count} role permissions")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        app_logger.error(f"Failed to update role permissions: {e}")
        raise
