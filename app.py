from flask import Flask, render_template
from flask_cors import CORS
import os
# Force Railway rebuild - LazyPoolWrapper fix v2
from backend.config.env_validator import validate_environment
validate_environment()

from backend.utils.logger import app_logger
from backend.utils.error_handler import register_error_handlers
from backend.utils.security import init_security
from backend.config.migrations import run_migrations

from backend.api.auth import auth_bp
from backend.api.departments import departments_bp
from backend.api.employees import employees_bp
from backend.api.machines import machines_bp
from backend.api.products import products_bp
from backend.api.orders import orders_bp
from backend.api.defects import defects_bp
from backend.api.sop import sop_bp
from backend.api.maintenance import maintenance_bp
from backend.api.finance import finance_bp
from backend.api.operator import operator_bp
from backend.api.forms import forms_bp
from backend.api.notifications_api import notifications_bp
from backend.api.reports import reports_bp
from backend.api.workflows import workflows_bp
from backend.api.sla import sla_bp
from backend.api.preventive_maintenance import preventive_maintenance_bp
from backend.api.cost_models import cost_models_bp
from backend.api.manager_controls import manager_controls_bp
from backend.api.d365_integration import d365_bp
from backend.api.capacity_planning import capacity_planning_bp
from backend.api.field_permissions import field_permissions_bp
from backend.api.health import health_bp
from backend.api.whatsapp import whatsapp_bp
from backend.api.twilio_api import twilio_bp
from backend.api.order_import import order_import_bp
from backend.utils.scheduler import scheduler

app = Flask(__name__, 
            static_folder='static',
            template_folder='templates')

app.config['SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'your-secret-key')
app.config['JSON_SORT_KEYS'] = False
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_UPLOAD_SIZE_MB', 50)) * 1024 * 1024

CORS(app, resources={
    r"/api/*": {
        "origins": os.getenv('CORS_ORIGINS', '*').split(','),
        "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

register_error_handlers(app)
init_security(app)

scheduler.start()
run_migrations()  # Run database migrations on startup
app_logger.info("Application initialized successfully")

app.register_blueprint(auth_bp)
app.register_blueprint(departments_bp)
app.register_blueprint(employees_bp)
app.register_blueprint(machines_bp)
app.register_blueprint(products_bp)
app.register_blueprint(orders_bp)
app.register_blueprint(defects_bp)
app.register_blueprint(sop_bp)
app.register_blueprint(maintenance_bp)
app.register_blueprint(finance_bp)
app.register_blueprint(operator_bp)
app.register_blueprint(forms_bp)
app.register_blueprint(notifications_bp)
app.register_blueprint(reports_bp)
app.register_blueprint(workflows_bp)
app.register_blueprint(sla_bp)
app.register_blueprint(preventive_maintenance_bp)
app.register_blueprint(cost_models_bp)
app.register_blueprint(manager_controls_bp)
app.register_blueprint(d365_bp)
app.register_blueprint(capacity_planning_bp)
app.register_blueprint(field_permissions_bp)
app.register_blueprint(health_bp)
app.register_blueprint(whatsapp_bp)
app.register_blueprint(twilio_bp)
app.register_blueprint(order_import_bp)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/admin/departments')
def admin_departments():
    return render_template('admin/departments.html')

@app.route('/admin/employees')
def admin_employees():
    return render_template('admin/employees.html')

@app.route('/admin/machines')
def admin_machines():
    return render_template('admin/machines.html')

@app.route('/admin/products')
def admin_products():
    return render_template('admin/products.html')

@app.route('/admin/forms')
def admin_forms():
    return render_template('admin/forms.html')

@app.route('/planning/orders')
def planning_orders():
    return render_template('planning/orders.html')

@app.route('/planning/schedule')
def planning_schedule():
    return render_template('planning/schedule.html')

@app.route('/planning/capacity')
def planning_capacity():
    return render_template('planning/capacity.html')

@app.route('/planning/machine-calendar')
def planning_machine_calendar():
    return render_template('planning/machine_calendar.html')

@app.route('/defects/replacement-tickets')
def defects_replacement():
    return render_template('defects/replacement_tickets.html')

@app.route('/defects/customer-returns')
def defects_returns():
    return render_template('defects/customer_returns.html')

@app.route('/defects/cost-analysis')
def defects_cost_analysis():
    return render_template('defects/cost_analysis.html')

@app.route('/sop/tickets')
def sop_tickets():
    return render_template('sop/tickets.html')

@app.route('/maintenance/tickets')
def maintenance_tickets():
    return render_template('maintenance/tickets.html')

@app.route('/maintenance/analytics')
def maintenance_analytics():
    return render_template('maintenance/analytics.html')

@app.route('/finance/bom')
def finance_bom():
    return render_template('finance/bom.html')

@app.route('/operator/dashboard')
def operator_dashboard():
    return render_template('operator/dashboard.html')

@app.route('/admin/workflows')
def admin_workflows():
    return render_template('admin/workflows.html')

@app.route('/admin/sla')
def admin_sla():
    return render_template('admin/sla.html')

@app.route('/admin/roles')
def admin_roles():
    return render_template('admin/roles.html')

@app.route('/admin/d365')
def admin_d365():
    return render_template('admin/d365.html')

@app.route('/maintenance/preventive')
def maintenance_preventive():
    return render_template('maintenance/preventive.html')

@app.route('/finance/costs')
def finance_costs():
    return render_template('finance/costs.html')

@app.route('/manager/dashboard')
def manager_dashboard():
    return render_template('manager/dashboard.html')

@app.route('/reports/configuration')
def reports_configuration():
    return render_template('reports/configuration.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
