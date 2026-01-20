"""
Reset admin password
"""
import pymysql
import os
import bcrypt
from dotenv import load_dotenv

load_dotenv()

print("🔐 Resetting admin password...")

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
    
    # Hash the new password
    new_password = 'Admin@2026!'
    password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    # Update admin user
    sql = "UPDATE users SET password_hash = %s WHERE username = %s"
    cursor.execute(sql, (password_hash, 'admin@barron'))
    connection.commit()
    
    print(f"✓ Admin password reset to: {new_password}")
    print(f"  Hash: {password_hash[:40]}...")
    
    # Verify it worked
    cursor.execute("SELECT password_hash FROM users WHERE username = 'admin@barron'")
    result = cursor.fetchone()
    
    if result:
        verify_result = bcrypt.checkpw(new_password.encode('utf-8'), result['password_hash'].encode('utf-8'))
        if verify_result:
            print(f"✓ Verification: PASSWORD MATCHES!")
        else:
            print(f"✗ Verification FAILED")
    
    connection.close()
    
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
