# Production Management System (PMS)

A comprehensive production management system for manufacturing operations, supporting job planning, quality control, SOP management, maintenance tracking, and more.

## Features

### Core Modules
1. **Job Planning** - Order scheduling, capacity planning, and production tracking
2. **Defects Management** - Internal rejects and customer returns tracking
3. **SOP Failure & NCR** - Non-conformance reporting and workflow
4. **Machinery Maintenance** - Equipment maintenance and tracking
5. **Finance (BOM)** - Bill of Materials management and cost analysis
6. **Master Data** - Departments, employees, products, machines
7. **Operator Interface** - Mobile-friendly job tracking for operators
8. **Reporting** - Automated reports and analytics

### Technical Features
- Role-based access control (RBAC)
- Dynamic form builder with JSON configuration
- Workflow and SLA engine
- Real-time notifications
- Comprehensive audit logging
- Mobile-optimized operator interface
- Industrial-grade UI design

## Technology Stack

- **Backend**: Python Flask
- **Database**: MySQL
- **Cache**: Redis
- **Frontend**: HTML5, CSS3, JavaScript (vanilla)
- **Architecture**: REST API with JWT authentication

## Setup Instructions

### Prerequisites
- Python 3.8+
- MySQL database access (Railway provided)
- Redis instance (Railway provided)

### Installation

1. **Clone or navigate to the project directory**
   ```bash
   cd pms
   ```

2. **Create a virtual environment (recommended)**
   ```bash
   python -m venv venv
   ```

3. **Activate the virtual environment**
   - Windows:
     ```bash
     venv\Scripts\activate
     ```
   - Linux/Mac:
     ```bash
     source venv/bin/activate
     ```

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Set up the database**
   The database connection is already configured in `.env` file.
   
   Import the database schema:
   ```bash
   mysql -h mainline.proxy.rlwy.net -u root -pJMucYiEZITlFFDdvYxgSQtgYnAwCDjvG --port 51104 --protocol=TCP railway < database/schema.sql
   ```

6. **Run the application**
   ```bash
   python app.py
   ```

7. **Access the application**
   - Open browser: http://localhost:5000
   - Default admin credentials:
     - Username: `admin@barron`
     - Password: `password` (should be changed immediately)

## Project Structure

```
pms/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── .env                  # Environment configuration
├── backend/
│   ├── api/             # API route handlers
│   ├── config/          # Database and Redis configuration
│   ├── models/          # Data models (future)
│   └── utils/           # Utility functions (auth, audit, notifications)
├── static/
│   ├── css/            # Stylesheets
│   └── js/             # JavaScript files
├── templates/           # HTML templates
│   ├── admin/          # Admin module templates
│   ├── planning/       # Planning module templates
│   ├── defects/        # Defects module templates
│   ├── sop/            # SOP module templates
│   ├── maintenance/    # Maintenance module templates
│   ├── finance/        # Finance module templates
│   └── operator/       # Operator interface templates
└── database/
    └── schema.sql      # Database schema
```

## Database Configuration

The system uses MySQL with the following connection:
- Host: mainline.proxy.rlwy.net
- Port: 51104
- Database: railway
- Credentials provided in `.env`

## API Endpoints

### Authentication
- `POST /api/auth/login` - User login
- `GET /api/auth/me` - Get current user
- `POST /api/auth/change-password` - Change password

### Departments
- `GET /api/departments` - List all departments
- `POST /api/departments` - Create department
- `PUT /api/departments/{id}` - Update department
- `POST /api/departments/{id}/stages` - Add production stage

### Employees
- `GET /api/employees` - List employees
- `POST /api/employees` - Create employee
- `PUT /api/employees/{id}` - Update employee

### Orders
- `GET /api/orders` - List orders
- `POST /api/orders` - Create order
- `POST /api/orders/{id}/schedule` - Schedule order
- `POST /api/orders/{id}/hold` - Place order on hold

### Defects
- `GET /api/defects/replacement-tickets` - List replacement tickets
- `POST /api/defects/replacement-tickets` - Create ticket
- `POST /api/defects/replacement-tickets/{id}/approve` - Approve ticket

### SOP
- `GET /api/sop/tickets` - List SOP tickets
- `POST /api/sop/tickets` - Create ticket
- `POST /api/sop/tickets/{id}/ncr` - Complete NCR

### Maintenance
- `GET /api/maintenance/tickets` - List maintenance tickets
- `POST /api/maintenance/tickets` - Create ticket
- `POST /api/maintenance/tickets/{id}/assign` - Assign ticket

### Finance
- `GET /api/finance/bom` - List BOMs
- `POST /api/finance/bom` - Create BOM
- `GET /api/finance/cost-analysis/defects` - Defect cost analysis

### Operator
- `POST /api/operator/login` - Operator login (employee number)
- `GET /api/operator/my-jobs` - Get assigned jobs
- `POST /api/operator/job/{id}/start` - Start job
- `POST /api/operator/job/{id}/complete` - Complete job

## User Roles

1. **System Admin** - Full system access
2. **Department Manager** - Manage department operations
3. **Planner** - Schedule and plan production
4. **Operator** - Execute production jobs
5. **QC Coordinator** - Quality control and defects
6. **Maintenance Technician** - Machinery maintenance
7. **Finance** - BOM and cost management

## Security

- JWT-based authentication
- Password hashing with bcrypt
- Role-based authorization
- Audit logging for all actions
- Input validation on frontend and backend

## Mobile Support

The operator interface is optimized for mobile devices:
- Large touch targets
- Simplified navigation
- Lightweight design
- Works on older smartphones

## Development

### Running in Development Mode
```bash
python app.py
```

### Running in Production
Update `.env`:
```
FLASK_ENV=production
FLASK_DEBUG=False
```

Use a production WSGI server:
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## Troubleshooting

### Database Connection Issues
- Verify database credentials in `.env`
- Check network connectivity to Railway
- Ensure database schema is imported

### Module Import Errors
- Verify all dependencies are installed
- Check Python version (3.8+)
- Activate virtual environment

### Permission Errors
- Check user role assignments
- Verify role permissions in database
- Review audit logs for access attempts

## Support

For issues or questions, contact the development team or refer to the system documentation.

## License

Proprietary - Barron (Pty) Ltd
