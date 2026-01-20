#!/usr/bin/env python3
"""Debug script to check user and role permissions"""
import sys
import os
from dotenv import load_dotenv

load_dotenv()

# Import after loading env
from backend.config.db_pool import get_db_connection

def check_admin_user():
    """Check the admin user's role and permissions"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check admin user
        cursor.execute("""
            SELECT u.id, u.username, u.email, r.name as role_name, r.permissions
            FROM users u
            LEFT JOIN roles r ON u.role_id = r.id
            WHERE u.username = 'admin@barron'
        """)
        
        user = cursor.fetchone()
        if user:
            print("✓ Admin User Found:")
            print(f"  Username: {user['username']}")
            print(f"  Email: {user['email']}")
            print(f"  Role: {user['role_name']}")
            print(f"  Permissions: {user['permissions']}")
        else:
            print("✗ Admin user not found")
        
        # Check all roles
        print("\n✓ All Roles in Database:")
        cursor.execute("SELECT id, name, permissions FROM roles ORDER BY id")
        roles = cursor.fetchall()
        for role in roles:
            print(f"  ID {role['id']}: {role['name']}")
            print(f"    Permissions: {role['permissions']}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    check_admin_user()
