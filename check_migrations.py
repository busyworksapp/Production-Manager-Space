#!/usr/bin/env python3
"""Check what migrations were applied and verify database structure"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from backend.config.db_pool import get_db_connection

def main():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print("Applied Migrations:")
    print("=" * 60)
    cursor.execute("SELECT version, name, executed_at FROM schema_migrations ORDER BY version")
    for row in cursor.fetchall():
        print(f"  {row['version']} - {row['name']} ({row['executed_at']})")
    
    print("\nChecking replacement_tickets table structure:")
    print("=" * 60)
    cursor.execute("""
        SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'replacement_tickets'
        AND TABLE_SCHEMA = DATABASE()
        AND COLUMN_NAME IN ('order_item_id', 'cost_impact', 'material_cost', 'labor_cost', 'total_cost')
        ORDER BY ORDINAL_POSITION
    """)
    columns = cursor.fetchall()
    if columns:
        for col in columns:
            print(f"  {col['COLUMN_NAME']}: {col['COLUMN_TYPE']} (NULL: {col['IS_NULLABLE']}, Default: {col['COLUMN_DEFAULT']})")
    else:
        print("  No cost tracking columns found")
    
    print("\nChecking job_schedules table structure:")
    print("=" * 60)
    cursor.execute("""
        SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'job_schedules'
        AND TABLE_SCHEMA = DATABASE()
        AND COLUMN_NAME IN ('material_cost', 'labor_cost', 'overhead_cost', 'total_cost', 'actual_hours')
        ORDER BY ORDINAL_POSITION
    """)
    columns = cursor.fetchall()
    if columns:
        for col in columns:
            print(f"  {col['COLUMN_NAME']}: {col['COLUMN_TYPE']} (NULL: {col['IS_NULLABLE']}, Default: {col['COLUMN_DEFAULT']})")
    else:
        print("  No cost tracking columns found")
    
    print("\nChecking for triggers:")
    print("=" * 60)
    cursor.execute("""
        SELECT TRIGGER_NAME, EVENT_MANIPULATION, EVENT_OBJECT_TABLE
        FROM INFORMATION_SCHEMA.TRIGGERS
        WHERE TRIGGER_SCHEMA = DATABASE()
        AND TRIGGER_NAME IN ('trg_calculate_replacement_cost', 'trg_calculate_job_costs')
    """)
    triggers = cursor.fetchall()
    if triggers:
        for trig in triggers:
            print(f"  {trig['TRIGGER_NAME']} on {trig['EVENT_OBJECT_TABLE']} ({trig['EVENT_MANIPULATION']})")
    else:
        print("  No triggers found")
    
    print("\nChecking for views:")
    print("=" * 60)
    cursor.execute("""
        SELECT TABLE_NAME
        FROM INFORMATION_SCHEMA.VIEWS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME IN ('v_defect_cost_analysis', 'v_customer_returns_cost_analysis', 
                          'v_job_profitability', 'v_department_cost_analysis')
    """)
    views = cursor.fetchall()
    if views:
        for view in views:
            print(f"  {view['TABLE_NAME']}")
    else:
        print("  No views found")
    
    cursor.close()
    conn.close()

if __name__ == '__main__':
    main()
