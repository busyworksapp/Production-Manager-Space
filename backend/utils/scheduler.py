from threading import Thread
from time import sleep
from datetime import datetime, timedelta
from backend.config.database import execute_query
from backend.utils.notifications import create_notification
import json

try:
    from backend.utils.report_generator import execute_scheduled_report
    REPORTS_AVAILABLE = True
except ImportError:
    REPORTS_AVAILABLE = False

class BackgroundScheduler:
    def __init__(self):
        self.running = False
        self.thread = None
    
    def start(self):
        if not self.running:
            self.running = True
            self.thread = Thread(target=self._run, daemon=True)
            self.thread.start()
            print("Background scheduler started")
    
    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()
        print("Background scheduler stopped")
    
    def _run(self):
        while self.running:
            try:
                self.check_sla_breaches()
                self.process_escalations()
                self.check_preventive_maintenance()
                self.process_d365_sync()
                self.process_scheduled_reports()
            except Exception as e:
                print(f"Scheduler error: {str(e)}")
            
            sleep(60)
    
    def check_sla_breaches(self):
        now = datetime.now()
        
        at_risk_response = execute_query(
            """SELECT st.*, sc.sla_name, sc.escalation_levels, sc.notification_rules
               FROM sla_tracking st
               LEFT JOIN sla_configurations sc ON st.sla_config_id = sc.id
               WHERE st.response_due_at BETWEEN %s AND %s
               AND st.responded_at IS NULL
               AND st.status = 'on_track'""",
            (now, now + timedelta(minutes=30)),
            fetch_all=True
        )
        
        for sla in at_risk_response:
            execute_query(
                "UPDATE sla_tracking SET status = 'at_risk' WHERE id = %s",
                (sla['id'],),
                commit=True
            )
            self.send_sla_notification(sla, 'response_at_risk')
        
        breached_response = execute_query(
            """SELECT st.*, sc.sla_name, sc.escalation_levels, sc.notification_rules
               FROM sla_tracking st
               LEFT JOIN sla_configurations sc ON st.sla_config_id = sc.id
               WHERE st.response_due_at < %s
               AND st.responded_at IS NULL
               AND st.status IN ('on_track', 'at_risk')""",
            (now,),
            fetch_all=True
        )
        
        for sla in breached_response:
            execute_query(
                "UPDATE sla_tracking SET status = 'breached' WHERE id = %s",
                (sla['id'],),
                commit=True
            )
            self.send_sla_notification(sla, 'response_breached')
            self.escalate_sla(sla)
        
        breached_resolution = execute_query(
            """SELECT st.*, sc.sla_name, sc.escalation_levels, sc.notification_rules
               FROM sla_tracking st
               LEFT JOIN sla_configurations sc ON st.sla_config_id = sc.id
               WHERE st.resolution_due_at < %s
               AND st.resolved_at IS NULL
               AND st.status != 'breached'""",
            (now,),
            fetch_all=True
        )
        
        for sla in breached_resolution:
            execute_query(
                "UPDATE sla_tracking SET status = 'breached' WHERE id = %s",
                (sla['id'],),
                commit=True
            )
            self.send_sla_notification(sla, 'resolution_breached')
            self.escalate_sla(sla)
    
    def escalate_sla(self, sla):
        escalation_levels = json.loads(sla['escalation_levels']) if sla['escalation_levels'] else []
        current_level = sla['current_escalation_level']
        
        if current_level < len(escalation_levels):
            next_level = escalation_levels[current_level]
            
            escalation_history = json.loads(sla['escalation_history']) if sla['escalation_history'] else []
            escalation_history.append({
                'level': current_level + 1,
                'escalated_at': str(datetime.now()),
                'escalated_to': next_level.get('escalate_to'),
                'reason': 'Automatic escalation due to SLA breach'
            })
            
            execute_query(
                """UPDATE sla_tracking 
                   SET current_escalation_level = %s, escalation_history = %s
                   WHERE id = %s""",
                (current_level + 1, json.dumps(escalation_history), sla['id']),
                commit=True
            )
            
            self.send_sla_notification(sla, 'escalated', next_level.get('escalate_to'))
    
    def send_sla_notification(self, sla, notification_type, recipient_id=None):
        notification_rules = json.loads(sla['notification_rules']) if sla['notification_rules'] else {}
        recipients = notification_rules.get(notification_type, [])
        
        if recipient_id:
            recipients.append(recipient_id)
        
        for recipient in recipients:
            create_notification(
                recipient_id=recipient,
                notification_type='sla_alert',
                title=f"SLA Alert: {sla['sla_name']}",
                message=f"SLA {notification_type.replace('_', ' ')} for {sla['entity_type']} #{sla['entity_id']}",
                related_entity_type=sla['entity_type'],
                related_entity_id=sla['entity_id'],
                priority='high'
            )
    
    def process_escalations(self):
        open_sop_tickets = execute_query(
            """SELECT st.*, 
                      TIMESTAMPDIFF(HOUR, st.created_at, NOW()) as hours_open
               FROM sop_failure_tickets st
               WHERE st.status IN ('open', 'ncr_in_progress')
               AND st.escalated_to_hod = FALSE""",
            fetch_all=True
        )
        
        for ticket in open_sop_tickets:
            if ticket['hours_open'] >= 48:
                execute_query(
                    "UPDATE sop_failure_tickets SET escalated_to_hod = TRUE WHERE id = %s",
                    (ticket['id'],),
                    commit=True
                )
                
                department = execute_query(
                    "SELECT manager_id FROM departments WHERE id = %s",
                    (ticket['charged_department_id'],),
                    fetch_one=True
                )
                
                if department and department['manager_id']:
                    create_notification(
                        recipient_id=department['manager_id'],
                        notification_type='sop_escalation',
                        title=f"SOP Ticket Escalated: {ticket['ticket_number']}",
                        message=f"SOP failure ticket has been open for {ticket['hours_open']} hours without resolution",
                        related_entity_type='sop_ticket',
                        related_entity_id=ticket['id'],
                        priority='urgent'
                    )
    
    def check_preventive_maintenance(self):
        now = datetime.now()
        
        due_schedules = execute_query(
            """SELECT pms.*, m.machine_name, m.department_id,
                      CONCAT(e.first_name, ' ', e.last_name) as technician_name
               FROM preventive_maintenance_schedules pms
               LEFT JOIN machines m ON pms.machine_id = m.id
               LEFT JOIN employees e ON pms.assigned_technician_id = e.id
               WHERE pms.next_due_at <= %s
               AND pms.is_active = TRUE""",
            (now + timedelta(days=3),),
            fetch_all=True
        )
        
        for schedule in due_schedules:
            if schedule['assigned_technician_id']:
                employee_user = execute_query(
                    "SELECT user_id FROM employees WHERE id = %s",
                    (schedule['assigned_technician_id'],),
                    fetch_one=True
                )
                
                if employee_user and employee_user['user_id']:
                    create_notification(
                        recipient_id=employee_user['user_id'],
                        notification_type='maintenance_due',
                        title=f"Preventive Maintenance Due: {schedule['schedule_name']}",
                        message=f"Maintenance for {schedule['machine_name']} is due on {schedule['next_due_at']}",
                        related_entity_type='preventive_maintenance_schedule',
                        related_entity_id=schedule['id'],
                        priority='high' if schedule['priority'] == 'critical' else 'normal'
                    )
            
            if schedule['department_id']:
                department = execute_query(
                    "SELECT manager_id FROM departments WHERE id = %s",
                    (schedule['department_id'],),
                    fetch_one=True
                )
                
                if department and department['manager_id']:
                    create_notification(
                        recipient_id=department['manager_id'],
                        notification_type='maintenance_due',
                        title=f"Preventive Maintenance Due: {schedule['schedule_name']}",
                        message=f"Maintenance for {schedule['machine_name']} is due on {schedule['next_due_at']}",
                        related_entity_type='preventive_maintenance_schedule',
                        related_entity_id=schedule['id'],
                        priority='normal'
                    )
    
    def process_d365_sync(self):
        configs = execute_query(
            """SELECT * FROM d365_integration_config
               WHERE is_active = TRUE
               AND next_sync_at <= NOW()""",
            fetch_all=True
        )
        
        for config in configs:
            print(f"D365 sync triggered for config: {config['config_name']}")
    
    def process_scheduled_reports(self):
        reports = execute_query(
            """SELECT * FROM email_reports
               WHERE is_active = TRUE
               AND next_run_at <= NOW()""",
            fetch_all=True
        )
        
        for report in reports:
            print(f"Scheduled report triggered: {report['report_name']}")
            
            try:
                if REPORTS_AVAILABLE:
                    execute_scheduled_report(report['id'])
                    print(f"Report {report['report_name']} generated and sent successfully")
                else:
                    print(f"Report generation module not available")
            except Exception as e:
                print(f"Failed to generate report {report['report_name']}: {str(e)}")
            
            schedule_config = json.loads(report['schedule_config']) if isinstance(report['schedule_config'], str) else report['schedule_config']
            frequency = schedule_config.get('frequency', 'daily')
            
            if frequency == 'daily':
                next_run = datetime.now() + timedelta(days=1)
            elif frequency == 'weekly':
                next_run = datetime.now() + timedelta(weeks=1)
            elif frequency == 'monthly':
                next_run = datetime.now() + timedelta(days=30)
            else:
                next_run = datetime.now() + timedelta(days=1)
            
            execute_query(
                "UPDATE email_reports SET last_run_at = NOW(), next_run_at = %s WHERE id = %s",
                (next_run, report['id']),
                commit=True
            )

scheduler = BackgroundScheduler()
