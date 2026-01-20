"""
Diagnostic script to check users and test password verification
"""
import pymysql
import os
import bcrypt
from dotenv import load_dotenv

load_dotenv()

# Test passwords
test_passwords = {
    'admin@barron': 'Admin@2026!',
    'manager.john': 'Manager@2026!',
}

print("=" * 70)
print("DATABASE USER DIAGNOSTIC")
print("=" * 70)

try:
    connection = pymysql.connect(
        host=os.getenv('DB_HOST'),
        port=int(os.getenv('DB_PORT', 3306)),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME'),
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )
    
    cursor = connection.cursor()
    
    # Check if users table exists
    cursor.execute("SELECT COUNT(*) as count FROM information_schema.TABLES WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'users'", 
                   (os.getenv('DB_NAME'),))
    if cursor.fetchone()['count'] == 0:
        print("❌ USERS TABLE DOES NOT EXIST!")
        print("Run setup_database.py first")
        exit(1)
    
    # Get all users
    cursor.execute("""
        SELECT u.id, u.username, u.password_hash, u.is_active, r.name as role 
        FROM users u 
        LEFT JOIN roles r ON u.role_id = r.id
        ORDER BY u.id
    """)
    
    users = cursor.fetchall()
    
    if not users:
        print("❌ NO USERS FOUND IN DATABASE!")
        print("The seed_data.py script may not have run successfully")
    else:
        print(f"\n✓ Found {len(users)} users in database:\n")
        
        for user in users:
            print(f"ID: {user['id']}")
            print(f"  Username: {user['username']}")
            print(f"  Role: {user['role']}")
            print(f"  Active: {user['is_active']}")
            print(f"  Hash: {user['password_hash'][:30]}...")
            
            # Test password verification for known users
            if user['username'] in test_passwords:
                test_pwd = test_passwords[user['username']]
                try:
                    result = bcrypt.checkpw(test_pwd.encode('utf-8'), user['password_hash'].encode('utf-8'))
                    status = "✓ MATCHES" if result else "✗ DOES NOT MATCH"
                    print(f"  Password test ({test_pwd}): {status}")
                except Exception as e:
                    print(f"  Password test ERROR: {e}")
            print()
    
    # Check roles
    cursor.execute("SELECT id, name FROM roles ORDER BY id")
    roles = cursor.fetchall()
    
    if roles:
        print(f"✓ Found {len(roles)} roles:")
        for role in roles:
            print(f"  - {role['name']} (ID: {role['id']})")
    else:
        print("❌ NO ROLES FOUND!")
    
    connection.close()
    
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
