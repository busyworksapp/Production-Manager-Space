#!/usr/bin/env python3
"""Properly apply migrations by handling DELIMITER commands"""
import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from backend.config.db_pool import get_db_connection

def parse_sql_with_delimiters(sql_content):
    """Parse SQL file that may contain DELIMITER commands"""
    statements = []
    current_delimiter = ';'
    current_statement = []
    
    lines = sql_content.split('\n')
    
    for line in lines:
        stripped = line.strip()
        
        # Skip comments and empty lines
        if not stripped or stripped.startswith('--'):
            continue
        
        # Check for DELIMITER command
        if stripped.upper().startswith('DELIMITER'):
            # Save current statement if any
            if current_statement:
                stmt = '\n'.join(current_statement).strip()
                if stmt:
                    statements.append(stmt)
                current_statement = []
            
            # Update delimiter
            new_delimiter = stripped.split(None, 1)[1].strip()
            current_delimiter = new_delimiter
            continue
        
        # Add line to current statement
        current_statement.append(line)
        
        # Check if statement is complete
        if stripped.endswith(current_delimiter):
            # Remove the delimiter from the end
            stmt = '\n'.join(current_statement).strip()
            if stmt.endswith(current_delimiter):
                stmt = stmt[:-len(current_delimiter)].strip()
            if stmt:
                statements.append(stmt)
            current_statement = []
    
    # Add any remaining statement
    if current_statement:
        stmt = '\n'.join(current_statement).strip()
        if stmt and stmt != current_delimiter:
            if stmt.endswith(';'):
                stmt = stmt[:-1].strip()
            if stmt:
                statements.append(stmt)
    
    return statements

def apply_migration_file(conn, migration_file):
    """Apply a single migration file"""
    print(f"\nApplying {migration_file.name}...")
    
    with open(migration_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # Remove USE database statement - we're already connected
    sql_content = re.sub(r'USE\s+\w+\s*;', '', sql_content, flags=re.IGNORECASE)
    
    statements = parse_sql_with_delimiters(sql_content)
    
    cursor = conn.cursor()
    
    success_count = 0
    error_count = 0
    
    for i, stmt in enumerate(statements, 1):
        if not stmt or stmt.strip() == '':
            continue
            
        try:
            cursor.execute(stmt)
            conn.commit()
            success_count += 1
            
            # Show what was executed (truncated)
            stmt_preview = stmt[:60].replace('\n', ' ')
            if len(stmt) > 60:
                stmt_preview += '...'
            print(f"  ✓ Statement {i}: {stmt_preview}")
            
        except Exception as e:
            error_msg = str(e)
            # Ignore certain errors that are acceptable
            if 'Duplicate column' in error_msg or 'already exists' in error_msg or 'Duplicate key' in error_msg:
                print(f"  ⊙ Statement {i}: Already exists (skipped)")
            else:
                print(f"  ✗ Statement {i} failed: {error_msg}")
                error_count += 1
                # Don't raise - continue with other statements
    
    cursor.close()
    print(f"  Summary: {success_count} successful, {error_count} errors")
    return success_count, error_count

def main():
    """Apply migrations properly"""
    print("Applying database migrations (proper handling)...")
    
    try:
        conn = get_db_connection()
        
        # First, clear the migration records to reapply
        cursor = conn.cursor()
        print("\nClearing previous migration attempts...")
        cursor.execute("DELETE FROM schema_migrations WHERE version IN ('001', '002')")
        conn.commit()
        cursor.close()
        
        migrations_dir = Path(__file__).parent / "database" / "migrations"
        
        migration_files = sorted(
            [f for f in migrations_dir.glob("*.sql")
             if f.name[0].isdigit()],
            key=lambda x: x.name
        )
        
        total_success = 0
        total_errors = 0
        
        for migration_file in migration_files:
            version = migration_file.name.split('_')[0]
            success, errors = apply_migration_file(conn, migration_file)
            total_success += success
            total_errors += errors
            
            # Mark as applied
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO schema_migrations (version, name) VALUES (%s, %s)",
                (version, migration_file.stem)
            )
            conn.commit()
            cursor.close()
            print(f"  ✓ Marked {version} as applied")
        
        conn.close()
        
        print(f"\n{'='*60}")
        print(f"Total: {total_success} successful statements, {total_errors} errors")
        print(f"{'='*60}")
        
        return 0
        
    except Exception as e:
        print(f"\nFailed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
