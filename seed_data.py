import pymysql
import os
import json
import bcrypt
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

def hash_password(password):
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def seed_database():
    print("🌱 Starting database seeding...")
    
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
        
        # ==================== SEED ROLES ====================
        print("\n📋 Seeding roles...")
        roles_data = [
            {
                'name': 'admin',
                'description': 'System Administrator with full access',
                'permissions': json.dumps({
                    'users': ['read', 'write', 'delete'],
                    'departments': ['read', 'write', 'delete'],
                    'employees': ['read', 'write', 'delete'],
                    'machines': ['read', 'write', 'delete'],
                    'orders': ['read', 'write', 'delete'],
                    'finance': ['read', 'write', 'delete'],
                    'reports': ['read', 'write'],
                    'settings': ['read', 'write']
                })
            },
            {
                'name': 'manager',
                'description': 'Department Manager',
                'permissions': json.dumps({
                    'employees': ['read', 'write'],
                    'machines': ['read', 'write'],
                    'orders': ['read', 'write'],
                    'reports': ['read'],
                    'maintenance': ['read', 'write']
                })
            },
            {
                'name': 'supervisor',
                'description': 'Production Supervisor',
                'permissions': json.dumps({
                    'orders': ['read', 'write'],
                    'employees': ['read'],
                    'maintenance': ['read'],
                    'reports': ['read']
                })
            },
            {
                'name': 'operator',
                'description': 'Machine Operator',
                'permissions': json.dumps({
                    'orders': ['read'],
                    'machines': ['read'],
                    'maintenance': ['read']
                })
            },
            {
                'name': 'finance',
                'description': 'Finance Department Staff',
                'permissions': json.dumps({
                    'finance': ['read', 'write'],
                    'orders': ['read'],
                    'reports': ['read']
                })
            }
        ]
        
        role_ids = {}
        for role in roles_data:
            try:
                sql = """INSERT INTO roles (name, description, permissions, is_active) 
                        VALUES (%s, %s, %s, TRUE)"""
                cursor.execute(sql, (role['name'], role['description'], role['permissions']))
                connection.commit()
                role_ids[role['name']] = cursor.lastrowid
                print(f"  ✓ Created role: {role['name']}")
            except pymysql.err.IntegrityError:
                cursor.execute("SELECT id FROM roles WHERE name = %s", (role['name'],))
                result = cursor.fetchone()
                role_ids[role['name']] = result['id']
                print(f"  ℹ Role already exists: {role['name']}")
        
        # ==================== SEED USERS ====================
        print("\n👥 Seeding users...")
        users_data = [
            {
                'username': 'admin@barron',
                'password': 'Admin@2026!',
                'email': 'admin@barron.com',
                'first_name': 'Admin',
                'last_name': 'User',
                'role_id': role_ids['admin']
            },
            {
                'username': 'manager.john',
                'password': 'Manager@2026!',
                'email': 'john.manager@barron.com',
                'first_name': 'John',
                'last_name': 'Manager',
                'role_id': role_ids['manager']
            },
            {
                'username': 'supervisor.sarah',
                'password': 'Supervisor@2026!',
                'email': 'sarah.supervisor@barron.com',
                'first_name': 'Sarah',
                'last_name': 'Supervisor',
                'role_id': role_ids['supervisor']
            },
            {
                'username': 'operator.mike',
                'password': 'Operator@2026!',
                'email': 'mike.operator@barron.com',
                'first_name': 'Mike',
                'last_name': 'Operator',
                'role_id': role_ids['operator']
            },
            {
                'username': 'operator.jane',
                'password': 'Operator@2026!',
                'email': 'jane.operator@barron.com',
                'first_name': 'Jane',
                'last_name': 'Operator',
                'role_id': role_ids['operator']
            },
            {
                'username': 'finance.david',
                'password': 'Finance@2026!',
                'email': 'david.finance@barron.com',
                'first_name': 'David',
                'last_name': 'Finance',
                'role_id': role_ids['finance']
            }
        ]
        
        user_ids = {}
        for user in users_data:
            try:
                password_hash = hash_password(user['password'])
                sql = """INSERT INTO users (username, password_hash, email, first_name, last_name, role_id, is_active) 
                        VALUES (%s, %s, %s, %s, %s, %s, TRUE)"""
                cursor.execute(sql, (user['username'], password_hash, user['email'], 
                                    user['first_name'], user['last_name'], user['role_id']))
                connection.commit()
                user_ids[user['username']] = cursor.lastrowid
                print(f"  ✓ Created user: {user['username']} (Password: {user['password']})")
            except pymysql.err.IntegrityError:
                cursor.execute("SELECT id FROM users WHERE username = %s", (user['username'],))
                result = cursor.fetchone()
                user_ids[user['username']] = result['id']
                print(f"  ℹ User already exists: {user['username']}")
        
        # ==================== SEED DEPARTMENTS ====================
        print("\n🏭 Seeding departments...")
        departments_data = [
            {
                'code': 'BRANDING',
                'name': 'Branding Department',
                'description': 'Handles all branding and packaging',
                'department_type': 'branding',
                'manager_id': user_ids.get('manager.john'),
                'daily_target': 500,
                'weekly_target': 2500,
                'monthly_target': 10000,
                'capacity_target': 100
            },
            {
                'code': 'PLANNING',
                'name': 'Planning Department',
                'description': 'Order planning and scheduling',
                'department_type': 'planning',
                'manager_id': user_ids.get('manager.john'),
                'daily_target': 100,
                'weekly_target': 500,
                'monthly_target': 2000,
                'capacity_target': 100
            },
            {
                'code': 'QUALITY',
                'name': 'Quality Control',
                'description': 'Quality assurance and testing',
                'department_type': 'quality',
                'manager_id': None,
                'daily_target': 450,
                'weekly_target': 2250,
                'monthly_target': 9000,
                'capacity_target': 100
            },
            {
                'code': 'MAINTENANCE',
                'name': 'Maintenance Department',
                'description': 'Equipment maintenance and support',
                'department_type': 'maintenance',
                'manager_id': None,
                'daily_target': 0,
                'weekly_target': 0,
                'monthly_target': 0,
                'capacity_target': 0
            },
            {
                'code': 'FINANCE',
                'name': 'Finance Department',
                'description': 'Financial management and reporting',
                'department_type': 'finance',
                'manager_id': user_ids.get('finance.david'),
                'daily_target': 0,
                'weekly_target': 0,
                'monthly_target': 0,
                'capacity_target': 0
            }
        ]
        
        department_ids = {}
        for dept in departments_data:
            try:
                sql = """INSERT INTO departments (code, name, description, department_type, manager_id, 
                        daily_target, weekly_target, monthly_target, capacity_target, is_active) 
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE)"""
                cursor.execute(sql, (dept['code'], dept['name'], dept['description'], 
                                    dept['department_type'], dept['manager_id'],
                                    dept['daily_target'], dept['weekly_target'], 
                                    dept['monthly_target'], dept['capacity_target']))
                connection.commit()
                department_ids[dept['code']] = cursor.lastrowid
                print(f"  ✓ Created department: {dept['name']}")
            except pymysql.err.IntegrityError:
                cursor.execute("SELECT id FROM departments WHERE code = %s", (dept['code'],))
                result = cursor.fetchone()
                department_ids[dept['code']] = result['id']
                print(f"  ℹ Department already exists: {dept['name']}")
        
        # ==================== SEED EMPLOYEES ====================
        print("\n👔 Seeding employees...")
        employees_data = [
            {
                'employee_number': 'EMP001',
                'first_name': 'John',
                'last_name': 'Manager',
                'email': 'john.manager@barron.com',
                'phone': '+27 123 456 7890',
                'department_id': department_ids.get('BRANDING'),
                'position': 'Department Manager',
                'employee_type': 'manager',
                'user_id': user_ids.get('manager.john')
            },
            {
                'employee_number': 'EMP002',
                'first_name': 'Sarah',
                'last_name': 'Supervisor',
                'email': 'sarah.supervisor@barron.com',
                'phone': '+27 123 456 7891',
                'department_id': department_ids.get('BRANDING'),
                'position': 'Production Supervisor',
                'employee_type': 'supervisor',
                'user_id': user_ids.get('supervisor.sarah')
            },
            {
                'employee_number': 'EMP003',
                'first_name': 'Mike',
                'last_name': 'Operator',
                'email': 'mike.operator@barron.com',
                'phone': '+27 123 456 7892',
                'department_id': department_ids.get('BRANDING'),
                'position': 'Machine Operator',
                'employee_type': 'operator',
                'user_id': user_ids.get('operator.mike')
            },
            {
                'employee_number': 'EMP004',
                'first_name': 'Jane',
                'last_name': 'Operator',
                'email': 'jane.operator@barron.com',
                'phone': '+27 123 456 7893',
                'department_id': department_ids.get('BRANDING'),
                'position': 'Machine Operator',
                'employee_type': 'operator',
                'user_id': user_ids.get('operator.jane')
            },
            {
                'employee_number': 'EMP005',
                'first_name': 'David',
                'last_name': 'Finance',
                'email': 'david.finance@barron.com',
                'phone': '+27 123 456 7894',
                'department_id': department_ids.get('FINANCE'),
                'position': 'Finance Manager',
                'employee_type': 'manager',
                'user_id': user_ids.get('finance.david')
            }
        ]
        
        for emp in employees_data:
            try:
                sql = """INSERT INTO employees (employee_number, first_name, last_name, email, phone, 
                        department_id, position, employee_type, user_id, is_active) 
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE)"""
                cursor.execute(sql, (emp['employee_number'], emp['first_name'], emp['last_name'], 
                                    emp['email'], emp['phone'], emp['department_id'],
                                    emp['position'], emp['employee_type'], emp['user_id']))
                connection.commit()
                print(f"  ✓ Created employee: {emp['first_name']} {emp['last_name']} ({emp['employee_number']})")
            except pymysql.err.IntegrityError:
                print(f"  ℹ Employee already exists: {emp['employee_number']}")
        
        # ==================== SEED MACHINES ====================
        print("\n🤖 Seeding machines...")
        machines_data = [
            {
                'machine_number': 'MACH001',
                'machine_name': 'Industrial Embroidery Machine A',
                'department_id': department_ids.get('BRANDING'),
                'machine_type': 'Embroidery',
                'manufacturer': 'Brother',
                'model': 'S7300',
                'status': 'available'
            },
            {
                'machine_number': 'MACH002',
                'machine_name': 'Industrial Embroidery Machine B',
                'department_id': department_ids.get('BRANDING'),
                'machine_type': 'Embroidery',
                'manufacturer': 'Brother',
                'model': 'S7300',
                'status': 'available'
            },
            {
                'machine_number': 'MACH003',
                'machine_name': 'Cutting Machine',
                'department_id': department_ids.get('BRANDING'),
                'machine_type': 'Cutting',
                'manufacturer': 'Graphtec',
                'model': 'FC9000',
                'status': 'available'
            }
        ]
        
        for machine in machines_data:
            try:
                sql = """INSERT INTO machines (machine_number, machine_name, 
                        department_id, machine_type, manufacturer, model, status, 
                        is_active) VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE)"""
                cursor.execute(sql, (machine['machine_number'], machine['machine_name'],
                                    machine['department_id'], machine['machine_type'],
                                    machine['manufacturer'], machine['model'],
                                    machine['status']))
                connection.commit()
                print(f"  ✓ Created machine: {machine['machine_name']}")
            except pymysql.err.IntegrityError:
                print(f"  ℹ Machine already exists: {machine['machine_number']}")
        
        cursor.close()
        connection.close()
        
        print("\n" + "="*50)
        print("✅ Database seeding completed successfully!")
        print("="*50)
        print("\n📝 User Credentials:")
        print("-" * 50)
        for user in users_data:
            print(f"  Username: {user['username']}")
            print(f"  Password: {user['password']}")
            print()
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error seeding database: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    seed_database()
