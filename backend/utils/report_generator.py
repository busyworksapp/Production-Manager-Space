from backend.config.database import execute_query
from backend.utils.email_sender import send_email
from datetime import datetime, timedelta
import json

def generate_defects_report(config, recipients):
    filters = config.get('filters', {})
    start_date = filters.get('start_date', (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'))
    end_date = filters.get('end_date', datetime.now().strftime('%Y-%m-%d'))
    
    query = """
        SELECT rt.*, o.order_number, o.customer_name, p.product_name, 
               d.name as department_name,
               CONCAT(u.first_name, ' ', u.last_name) as created_by_name
        FROM replacement_tickets rt
        LEFT JOIN orders o ON rt.order_id = o.id
        LEFT JOIN products p ON rt.product_id = p.id
        LEFT JOIN departments d ON rt.department_id = d.id
        LEFT JOIN users u ON rt.created_by_id = u.id
        WHERE rt.created_at BETWEEN %s AND %s
        ORDER BY rt.created_at DESC
    """
    
    defects = execute_query(query, (start_date, end_date), fetch_all=True)
    
    total_quantity = sum(d['quantity_rejected'] for d in defects)
    
    html_body = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #4CAF50; color: white; }}
            .summary {{ background-color: #f2f2f2; padding: 15px; margin-bottom: 20px; }}
        </style>
    </head>
    <body>
        <h2>Defects Report - {start_date} to {end_date}</h2>
        <div class="summary">
            <p><strong>Total Defects:</strong> {len(defects)}</p>
            <p><strong>Total Quantity Rejected:</strong> {total_quantity}</p>
        </div>
        <table>
            <tr>
                <th>Ticket #</th>
                <th>Order</th>
                <th>Customer</th>
                <th>Product</th>
                <th>Department</th>
                <th>Quantity</th>
                <th>Reason</th>
                <th>Date</th>
            </tr>
    """
    
    for defect in defects:
        html_body += f"""
            <tr>
                <td>{defect['ticket_number']}</td>
                <td>{defect['order_number']}</td>
                <td>{defect['customer_name']}</td>
                <td>{defect['product_name'] or 'N/A'}</td>
                <td>{defect['department_name']}</td>
                <td>{defect['quantity_rejected']}</td>
                <td>{defect['rejection_reason'][:50]}...</td>
                <td>{defect['created_at'].strftime('%Y-%m-%d') if defect['created_at'] else 'N/A'}</td>
            </tr>
        """
    
    html_body += """
        </table>
    </body>
    </html>
    """
    
    subject = f"Defects Report - {start_date} to {end_date}"
    send_email(recipients, subject, html_body)
    
    return True

def generate_customer_returns_report(config, recipients):
    filters = config.get('filters', {})
    start_date = filters.get('start_date', (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'))
    end_date = filters.get('end_date', datetime.now().strftime('%Y-%m-%d'))
    
    query = """
        SELECT cr.*, o.order_number, o.customer_name, p.product_name,
               CONCAT(u.first_name, ' ', u.last_name) as recorded_by_name
        FROM customer_returns cr
        LEFT JOIN orders o ON cr.order_id = o.id
        LEFT JOIN products p ON cr.product_id = p.id
        LEFT JOIN users u ON cr.recorded_by_id = u.id
        WHERE cr.return_date BETWEEN %s AND %s
        ORDER BY cr.return_date DESC
    """
    
    returns = execute_query(query, (start_date, end_date), fetch_all=True)
    
    total_quantity = sum(r['quantity_returned'] for r in returns)
    
    html_body = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #e74c3c; color: white; }}
            .summary {{ background-color: #f2f2f2; padding: 15px; margin-bottom: 20px; }}
        </style>
    </head>
    <body>
        <h2>Customer Returns Report - {start_date} to {end_date}</h2>
        <div class="summary">
            <p><strong>Total Returns:</strong> {len(returns)}</p>
            <p><strong>Total Quantity Returned:</strong> {total_quantity}</p>
        </div>
        <table>
            <tr>
                <th>Return #</th>
                <th>Order</th>
                <th>Customer</th>
                <th>Product</th>
                <th>Quantity</th>
                <th>Reason</th>
                <th>Type</th>
                <th>Date</th>
            </tr>
    """
    
    for ret in returns:
        html_body += f"""
            <tr>
                <td>{ret['return_number']}</td>
                <td>{ret['order_number']}</td>
                <td>{ret['customer_name']}</td>
                <td>{ret['product_name'] or 'N/A'}</td>
                <td>{ret['quantity_returned']}</td>
                <td>{ret['return_reason'][:50]}...</td>
                <td>{ret['return_type']}</td>
                <td>{ret['return_date']}</td>
            </tr>
        """
    
    html_body += """
        </table>
    </body>
    </html>
    """
    
    subject = f"Customer Returns Report - {start_date} to {end_date}"
    send_email(recipients, subject, html_body)
    
    return True

def generate_production_report(config, recipients):
    filters = config.get('filters', {})
    start_date = filters.get('start_date', (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'))
    end_date = filters.get('end_date', datetime.now().strftime('%Y-%m-%d'))
    
    query = """
        SELECT d.name as department_name,
               COUNT(DISTINCT js.id) as total_jobs,
               SUM(js.scheduled_quantity) as scheduled_quantity,
               SUM(js.actual_quantity) as actual_quantity,
               COUNT(CASE WHEN js.status = 'completed' THEN 1 END) as completed_jobs
        FROM job_schedules js
        LEFT JOIN departments d ON js.department_id = d.id
        WHERE js.scheduled_date BETWEEN %s AND %s
        GROUP BY d.name
        ORDER BY d.name
    """
    
    results = execute_query(query, (start_date, end_date), fetch_all=True)
    
    html_body = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #3498db; color: white; }}
            .summary {{ background-color: #f2f2f2; padding: 15px; margin-bottom: 20px; }}
        </style>
    </head>
    <body>
        <h2>Production Report - {start_date} to {end_date}</h2>
        <table>
            <tr>
                <th>Department</th>
                <th>Total Jobs</th>
                <th>Scheduled Qty</th>
                <th>Actual Qty</th>
                <th>Completed Jobs</th>
                <th>Efficiency %</th>
            </tr>
    """
    
    for dept in results:
        efficiency = 0
        if dept['scheduled_quantity'] and dept['scheduled_quantity'] > 0:
            efficiency = round((dept['actual_quantity'] or 0) / dept['scheduled_quantity'] * 100, 2)
        
        html_body += f"""
            <tr>
                <td>{dept['department_name']}</td>
                <td>{dept['total_jobs']}</td>
                <td>{dept['scheduled_quantity'] or 0}</td>
                <td>{dept['actual_quantity'] or 0}</td>
                <td>{dept['completed_jobs']}</td>
                <td>{efficiency}%</td>
            </tr>
        """
    
    html_body += """
        </table>
    </body>
    </html>
    """
    
    subject = f"Production Report - {start_date} to {end_date}"
    send_email(recipients, subject, html_body)
    
    return True

def execute_scheduled_report(report_id):
    report = execute_query("SELECT * FROM email_reports WHERE id = %s", (report_id,), fetch_one=True)
    
    if not report or not report['is_active']:
        return False
    
    config = json.loads(report['report_config']) if isinstance(report['report_config'], str) else report['report_config']
    recipients = json.loads(report['recipients']) if isinstance(report['recipients'], str) else report['recipients']
    
    report_type = report['report_type']
    
    if report_type == 'defects':
        generate_defects_report(config, recipients)
    elif report_type == 'customer_returns':
        generate_customer_returns_report(config, recipients)
    elif report_type == 'production':
        generate_production_report(config, recipients)
    
    execute_query(
        "UPDATE email_reports SET last_run_at = NOW() WHERE id = %s",
        (report_id,),
        commit=True
    )
    
    return True
