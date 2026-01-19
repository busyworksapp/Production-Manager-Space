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

def execute_sql_file(filepath):
    print(f"Reading SQL file: {filepath}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    statements = []
    current_statement = []
    in_delimiter = False
    
    for line in sql_content.split('\n'):
        stripped = line.strip()
        
        if stripped.upper().startswith('DELIMITER'):
            in_delimiter = not in_delimiter
            continue
        
        if not stripped or stripped.startswith('--'):
            continue
        
        current_statement.append(line)
        
        if not in_delimiter and stripped.endswith(';'):
            statement = '\n'.join(current_statement).strip()
            if statement and statement != ';':
                statements.append(statement)
            current_statement = []
    
    if current_statement:
        statement = '\n'.join(current_statement).strip()
        if statement and statement != ';':
            statements.append(statement)
    
    print(f"Found {len(statements)} SQL statements to execute\n")
    
    connection = get_connection()
    cursor = connection.cursor()
    
    executed = 0
    failed = 0
    
    for i, statement in enumerate(statements, 1):
        statement = statement.strip()
        if not statement or statement == ';':
            continue
        
        if statement.upper().startswith('USE '):
            print(f"[{i}/{len(statements)}] Skipping USE statement (database already selected)")
            continue
        
        if statement.upper().startswith('CREATE DATABASE'):
            print(f"[{i}/{len(statements)}] Skipping CREATE DATABASE statement (database already exists)")
            continue
        
        try:
            preview = statement[:80].replace('\n', ' ')
            if len(statement) > 80:
                preview += '...'
            
            print(f"[{i}/{len(statements)}] Executing: {preview}")
            
            cursor.execute(statement)
            connection.commit()
            executed += 1
            
        except pymysql.Error as e:
            if e.args[0] == 1050:
                print(f"  [!] Table already exists, skipping")
            elif e.args[0] == 1061:
                print(f"  [!] Duplicate key/index, skipping")
            elif e.args[0] == 1062:
                print(f"  [!] Duplicate entry, skipping")
            else:
                print(f"  [X] Error: {e}")
                failed += 1
        except Exception as e:
            print(f"  [X] Unexpected error: {e}")
            failed += 1
    
    cursor.close()
    connection.close()
    
    print(f"\n{'='*60}")
    print(f"Database setup completed!")
    print(f"  [OK] Successfully executed: {executed} statements")
    if failed > 0:
        print(f"  [FAIL] Failed: {failed} statements")
    print(f"{'='*60}\n")

if __name__ == '__main__':
    schema_path = os.path.join(
        os.path.dirname(__file__), 
        '..', 
        'database', 
        'schema.sql'
    )
    
    if not os.path.exists(schema_path):
        print(f"Error: Schema file not found at {schema_path}")
        sys.exit(1)
    
    print("="*60)
    print("PMS Database Setup Script")
    print("="*60)
    print(f"Target Database: {os.getenv('DB_NAME')} on {os.getenv('DB_HOST')}")
    print("="*60)
    print()
    
    try:
        execute_sql_file(schema_path)
        print("[SUCCESS] Database setup successful!")
    except Exception as e:
        print(f"\n[ERROR] Database setup failed: {e}")
        sys.exit(1)
