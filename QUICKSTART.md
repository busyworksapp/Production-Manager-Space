# Quick Start Guide - Production Management System

## Prerequisites
- Python 3.8 or higher installed
- Internet connection (for database access)

## Installation Steps

### 1. Open Terminal/Command Prompt
Navigate to the project directory:
```bash
cd "c:\Users\4667.KevroAD\OneDrive - Barron (Pty) Ltd\Desktop\pms"
```

### 2. Create Virtual Environment (Optional but Recommended)
```bash
python -m venv venv
```

### 3. Activate Virtual Environment

**Windows:**
```bash
venv\Scripts\activate
```

**Linux/Mac:**
```bash
source venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Set Up Database
```bash
python setup_database.py
```

This will:
- Connect to the MySQL database
- Create all required tables
- Insert default roles and admin user

### 6. Run the Application

**Option A: Using the run.bat script (Windows)**
```bash
run.bat
```

**Option B: Using Python directly**
```bash
python app.py
```

### 7. Access the Application

Open your web browser and navigate to:
```
http://localhost:5000
```

### 8. Login

**Default Admin Credentials:**
- **Username:** `admin@barron`
- **Password:** `password`

**IMPORTANT:** Change the admin password immediately after first login!

## Quick Test

After logging in:

1. **Create a Department**
   - Go to Admin → Departments
   - Click "Add Department"
   - Fill in the form and save

2. **Create an Employee**
   - Go to Admin → Employees
   - Click "Add Employee"
   - Fill in the form and save

3. **Create an Order**
   - Go to Planning → Orders
   - Click "Add Order"
   - Fill in the form and save

4. **View Dashboard**
   - Go to Dashboard
   - You should see statistics and recent data

## Troubleshooting

### Database Connection Error
- Verify internet connection
- Check `.env` file has correct database credentials
- Ensure firewall allows MySQL connection

### Module Import Error
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Activate virtual environment if you created one

### Port Already in Use
- Change the port in `app.py`:
  ```python
  app.run(debug=True, host='0.0.0.0', port=5001)
  ```

### Login Not Working
- Ensure database setup completed successfully
- Check browser console for errors
- Clear browser cache/localStorage

## Next Steps

1. **Change Admin Password**
   - Login as admin
   - Go to profile settings
   - Change password

2. **Create Departments**
   - Set up your branding departments
   - Configure production stages
   - Set capacity targets

3. **Add Employees**
   - Create employee records
   - Assign to departments
   - Set up user accounts for login

4. **Configure Products**
   - Add your product catalog
   - Set product specifications

5. **Add Machines**
   - Register all production machines
   - Assign to departments

6. **Create Roles & Permissions**
   - Customize roles for your organization
   - Assign appropriate permissions

## Important URLs

- **Main Application:** http://localhost:5000
- **Login Page:** http://localhost:5000/login
- **Dashboard:** http://localhost:5000/dashboard
- **Admin Panel:** http://localhost:5000/admin/departments
- **Operator Dashboard:** http://localhost:5000/operator/dashboard

## Default Roles

1. System Admin - Full access
2. Department Manager - Manage department operations
3. Planner - Schedule and plan production
4. Operator - Execute production jobs
5. QC Coordinator - Quality control
6. Maintenance Technician - Machinery maintenance

## Support

For issues or questions:
- Check the full README.md
- Review application logs
- Contact your system administrator

## Security Notes

- Always use HTTPS in production
- Change default passwords
- Restrict database access
- Regular backups recommended
- Update JWT secret key in `.env` for production

---

**Production Management System v1.0**
*Barron (Pty) Ltd*
