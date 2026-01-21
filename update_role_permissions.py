#!/usr/bin/env python3
"""
Update all role permissions to match navigation modules
"""
from backend.config.db_pool import get_db_connection
from backend.utils.logger import app_logger
import json


ROLE_PERMISSIONS = {
    'System Admin': {"all": True},
    'Department Manager': {
        "planning": {"read": True, "write": True},
        "qc": {"read": True, "write": True},
        "maintenance": {"read": True, "write": True},
        "admin": {"read": True}
    },
    'Planner': {
        "planning": {"read": True, "write": True, "schedule": True}
    },
    'Operator': {
        "planning": {"read": True},
        "sop": {"read": True, "write": True}
    },
    'QC Coordinator': {
        "qc": {"read": True, "write": True, "approve": True}
    },
    'Maintenance Technician': {
        "maintenance": {"read": True, "write": True}
    }
}


def update_role_permissions():
    """Update all role permissions to match navigation modules"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        print("Updating role permissions...\n")
        
        for role_name, permissions in ROLE_PERMISSIONS.items():
            permissions_json = json.dumps(permissions)
            
            cursor.execute("""
                UPDATE roles 
                SET permissions = %s 
                WHERE name = %s
            """, (permissions_json, role_name))
            
            conn.commit()
            print(f"✓ {role_name}")
            print(f"  Permissions: {permissions_json}")
        
        # Verify updates
        print("\n✓ Verifying updates:\n")
        cursor.execute("SELECT name, permissions FROM roles ORDER BY id")
        roles = cursor.fetchall()
        
        for role in roles:
            print(f"{role['name']}: {role['permissions']}")
        
        cursor.close()
        conn.close()
        print("\n✓ All role permissions updated successfully!")
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    update_role_permissions()
