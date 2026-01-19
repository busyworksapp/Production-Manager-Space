import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

def setup_database():
    print("Starting database setup...")
    
    try:
        connection = pymysql.connect(
            host=os.getenv('DB_HOST'),
            port=int(os.getenv('DB_PORT', 3306)),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            charset='utf8mb4'
        )
        
        cursor = connection.cursor()
        
        print("Reading SQL file...")
        with open('database/schema.sql', 'r', encoding='utf-8') as f:
            sql_script = f.read()
        
        print("Executing SQL statements...")
        statements = sql_script.split(';')
        
        for statement in statements:
            statement = statement.strip()
            if statement:
                try:
                    cursor.execute(statement)
                    connection.commit()
                except Exception as e:
                    print(f"Warning: {e}")
                    continue
        
        print("Database setup completed successfully!")
        print("\nDefault admin credentials:")
        print("Username: admin@barron")
        print("Password: password (Please change this immediately!)")
        
        cursor.close()
        connection.close()
        
    except Exception as e:
        print(f"Error setting up database: {e}")
        return False
    
    return True

if __name__ == '__main__':
    setup_database()
