#!/usr/bin/env python3
"""
Migration script to add cost_impact column to replacement_tickets table
if it doesn't already exist.
"""
import os
import sys
import pymysql
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def add_cost_impact_column():
    """Add cost_impact column to replacement_tickets table"""
    
    # Get database connection details from environment
    db_config = {
        'host': os.getenv('MYSQL_HOST', 'localhost'),
        'user': os.getenv('MYSQL_USER', 'root'),
        'password': os.getenv('MYSQL_PASSWORD', ''),
        'database': os.getenv('MYSQL_DATABASE', 'railway'),
        'port': int(os.getenv('MYSQL_PORT', 3306))
    }
    
    try:
        # Connect to database
        conn = pymysql.connect(**db_config)
        cursor = conn.cursor()
        
        print(f"🔗 Connected to {db_config['host']}:{db_config['port']}/{db_config['database']}")
        
        # Check if column already exists
        cursor.execute("""
            SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = 'replacement_tickets' AND COLUMN_NAME = 'cost_impact'
            AND TABLE_SCHEMA = %s
        """, (db_config['database'],))
        
        result = cursor.fetchone()
        
        if result:
            print("✓ cost_impact column already exists in replacement_tickets table")
        else:
            print("Adding cost_impact column to replacement_tickets table...")
            cursor.execute("""
                ALTER TABLE replacement_tickets 
                ADD COLUMN cost_impact DECIMAL(12,2) DEFAULT 0 AFTER rejection_type
            """)
            conn.commit()
            print("✓ Successfully added cost_impact column to replacement_tickets table")
        
        cursor.close()
        conn.close()
        print("✓ Migration completed successfully")
        return True
        
    except pymysql.Error as err:
        if err.args[0] == 2003:
            print(f"❌ Cannot connect to MySQL server at {db_config['host']}:{db_config['port']}")
            print("   Make sure your MYSQL_HOST and MYSQL_PORT are correct")
        else:
            print(f"❌ MySQL Error: {err}")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == '__main__':
    success = add_cost_impact_column()
    sys.exit(0 if success else 1)
