import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pymysql
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    return pymysql.connect(
        host=os.getenv('DB_HOST'),
        port=int(os.getenv('DB_PORT', 3306)),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME'),
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

def verify_database():
    print("="*60)
    print("PMS Database Verification")
    print("="*60)
    print(f"Target Database: {os.getenv('DB_NAME')} on {os.getenv('DB_HOST')}")
    print("="*60)
    print()
    
    connection = get_connection()
    cursor = connection.cursor()
    
    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()
    
    print(f"Total Tables: {len(tables)}\n")
    
    table_names = [list(table.values())[0] for table in tables]
    table_names.sort()
    
    for i, table_name in enumerate(table_names, 1):
        cursor.execute(f"SELECT COUNT(*) as count FROM `{table_name}`")
        count = cursor.fetchone()['count']
        
        cursor.execute(f"SHOW COLUMNS FROM `{table_name}`")
        columns = cursor.fetchall()
        
        print(f"{i:2d}. {table_name:35s} | {len(columns):2d} columns | {count:5d} rows")
    
    cursor.close()
    connection.close()
    
    print("\n" + "="*60)
    print("[SUCCESS] Database verification completed!")
    print("="*60)

if __name__ == '__main__':
    try:
        verify_database()
    except Exception as e:
        print(f"\n[ERROR] Database verification failed: {e}")
        sys.exit(1)
