#!/usr/bin/env python3
"""
Ensure admin user has System Admin role with full permissions
"""
import os
from dotenv import load_dotenv

load_dotenv()

from backend.config.db_pool import get_db_connection
from backend.utils.logger import app_logger


def ensure_admin_permissions():
    """Ensure admin user has System Admin role with all permissions"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # First, ensure System Admin role exists with full permissions
        cursor.execute("""
            SELECT id FROM roles WHERE name = 'System Admin'
        """)
        
        role_result = cursor.fetchone()
        
        if not role_result:
            # Create System Admin role
            print("Creating System Admin role...")
            cursor.execute("""
                INSERT INTO roles (name, description, permissions) 
                VALUES (%s, %s, %s)
            """, ('System Admin', 'Full system access with all permissions', '{"all": true}'))
            conn.commit()
            system_admin_id = cursor.lastrowid
            print(f"✓ System Admin role created with ID {system_admin_id}")
        else:
            system_admin_id = role_result['id']
            print(f"✓ System Admin role already exists with ID {system_admin_id}")
        
        # Now ensure admin user has this role
        cursor.execute("""
            SELECT u.id, u.username, u.role_id, r.name as role_name 
            FROM users u
            LEFT JOIN roles r ON u.role_id = r.id
            WHERE u.username = %s
        """, ('admin@barron',))
        
        user_result = cursor.fetchone()
        
        if not user_result:
            print("✗ Admin user not found!")
            return False
        
        if user_result['role_id'] != system_admin_id:
            print(f"⚠ Admin user has role_id {user_result['role_id']} (was: {user_result['role_name']})")
            print(f"  Updating to System Admin role (ID {system_admin_id})...")
            cursor.execute("""
                UPDATE users SET role_id = %s WHERE username = %s
            """, (system_admin_id, 'admin@barron'))
            conn.commit()
            print("✓ Admin user role updated to System Admin")
        else:
            print(f"✓ Admin user already has System Admin role")
        
        # Verify the permissions
        cursor.execute("""
            SELECT u.username, r.name, r.permissions 
            FROM users u
            JOIN roles r ON u.role_id = r.id
            WHERE u.username = %s
        """, ('admin@barron',))
        
        final_user = cursor.fetchone()
        print(f"\n✓ Final Admin User Status:")
        print(f"  Username: {final_user['username']}")
        print(f"  Role: {final_user['name']}")
        print(f"  Permissions: {final_user['permissions']}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    print("Ensuring admin has full permissions...\n")
    success = ensure_admin_permissions()
    exit(0 if success else 1)
