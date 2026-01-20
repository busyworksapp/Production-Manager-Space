from typing import Dict, Any, Optional
from backend.utils.whatsapp_service import whatsapp_service
from backend.utils.twilio_service import twilio_service
from backend.utils.logger import app_logger
from backend.config.db_pool import get_db_connection
import json

class WhatsAppFlowHandler:

    def _send_message(self, phone: str, message: str) -> bool:
        """
        Send a message via Twilio WhatsApp (preferred) or Graph API.
        Returns True if successful, False otherwise.
        """
        twilio_error = None
        try:
            # Try Twilio first (most likely for webhook)
            result = twilio_service.send_whatsapp_message(phone, message)
            if result.get('success'):
                app_logger.info(
                    f"Message sent via Twilio to {phone}"
                )
                return True
        except Exception as e:
            twilio_error = e
            app_logger.debug(
                f"Twilio send failed: {e}, trying Graph API..."
            )
        
        try:
            # Fallback to Graph API (for Meta WhatsApp)
            whatsapp_service.send_text_message(phone, message)
            app_logger.info(f"Message sent via Graph API to {phone}")
            return True
        except Exception as graph_error:
            app_logger.error(
                f"Both failed for {phone}: "
                f"Twilio: {twilio_error}, Graph: {graph_error}"
            )
            return False

    MAIN_MENU = {
        "text": "📋 *Main Menu*\n\nPlease select an option:",
        "sections": [{
            "title": "Available Actions",
            "rows": [
                {"id": "reject", "title": "📦 Submit Reject", "description": "Report a defective product"},
                {"id": "return", "title": "🔄 Customer Return", "description": "Process a customer return"},
                {"id": "sop_failure", "title": "⚠️ SOP Failure", "description": "Report a process failure"},
                {"id": "track", "title": "🔍 Track Item", "description": "Track an order or ticket"},
                {"id": "pull_data", "title": "📊 Pull Data", "description": "Get reports and statistics"}
            ]
        }]
    }
    
    def __init__(self):
        self.flow_handlers = {
            'reject': self._handle_reject_flow,
            'return': self._handle_return_flow,
            'sop_failure': self._handle_sop_failure_flow,
            'track': self._handle_track_flow,
            'pull_data': self._handle_pull_data_flow
        }
    
    def handle_message(
        self,
        phone: str,
        message_text: str,
        message_type: str = 'text',
        payload: Dict = None
    ) -> Dict[str, Any]:
        try:
            # Skip messages with no text content
            if not message_text:
                app_logger.debug(
                    f"Skipping empty message from {phone}"
                )
                return {"status": "skipped"}
            
            session = whatsapp_service.get_session(phone)
            
            if not session:
                session_id = (
                    whatsapp_service._get_or_create_session(phone)
                )
                session = whatsapp_service.get_session(phone)
            
            # Log incoming message asynchronously
            whatsapp_service._log_message_async(
                phone,
                'inbound',
                message_type,
                message_text,
                payload or {}
            )
            
            message_lower = message_text.lower().strip()
            
            if message_lower in (
                'hi',
                'hello',
                'menu',
                'start',
                'help'
            ):
                return self._show_main_menu(phone, session)
            
            # Handle numeric menu selections (1-5)
            menu_selection_map = {
                '1': 'reject',
                '2': 'return',
                '3': 'sop_failure',
                '4': 'track',
                '5': 'pull_data'
            }
            
            if message_lower in menu_selection_map:
                flow_name = menu_selection_map[message_lower]
                if flow_name in self.flow_handlers:
                    app_logger.info(
                        f"User {phone} selected flow: {flow_name}"
                    )
                    whatsapp_service.update_session(
                        session['id'],
                        state='awaiting_input',
                        flow=flow_name,
                        context={}
                    )
                    # Call the flow handler
                    return self.flow_handlers[flow_name](
                        phone,
                        session,
                        None,
                        'text',
                        {}
                    )
            
            if (
                session.get('current_flow')
                and session.get('session_state') == 'awaiting_input'
            ):
                flow_name = session['current_flow']
                if flow_name in self.flow_handlers:
                    return self.flow_handlers[flow_name](
                        phone,
                        session,
                        message_text,
                        message_type,
                        payload
                    )
            
            if message_type == 'interactive':
                return self._handle_interactive_response(
                    phone,
                    session,
                    payload
                )
            
            return self._show_main_menu(phone, session)
            
        except Exception as e:
            app_logger.error(
                f"Error handling message from {phone}: {str(e)}"
            )
            self._send_message(
                phone,
                "❌ An error occurred. Please try again or "
                "type 'menu' to start over."
            )
            return {"status": "error", "message": str(e)}
    
    def _show_main_menu(self, phone: str, session: Dict) -> Dict[str, Any]:
        whatsapp_service.update_session(
            session['id'],
            state='awaiting_menu',
            flow=None,
            context={}
        )
        
        # For Twilio, send text-based menu
        menu_text = (
            "📋 *Main Menu*\n\n"
            "Please select an option by typing the number:\n\n"
            "1️⃣ 📦 Submit Reject - Report a defective product\n"
            "2️⃣ 🔄 Customer Return - Process a customer return\n"
            "3️⃣ ⚠️ SOP Failure - Report a process failure\n"
            "4️⃣ 🔍 Track Item - Track an order or ticket\n"
            "5️⃣ 📊 Pull Data - Get reports and statistics\n\n"
            "Type: 1, 2, 3, 4, or 5"
        )
        
        self._send_message(phone, menu_text)
        
        return {"status": "menu_shown"}
    
    def _handle_interactive_response(self, phone: str, session: Dict, payload: Dict) -> Dict[str, Any]:
        button_reply = payload.get('button_reply', {})
        list_reply = payload.get('list_reply', {})
        
        selected_id = button_reply.get('id') or list_reply.get('id')
        
        if not selected_id:
            return self._show_main_menu(phone, session)
        
        if selected_id in self.flow_handlers:
            whatsapp_service.update_session(session['id'], state='awaiting_input', flow=selected_id, context={})
            return self.flow_handlers[selected_id](phone, session, None, 'interactive', payload)
        
        return self._show_main_menu(phone, session)
    
    def _handle_reject_flow(self, phone: str, session: Dict, message: str, msg_type: str, payload: Dict) -> Dict[str, Any]:
        context = session.get('context_data') or {}
        step = context.get('step', 0)
        
        if step == 0:
            self._send_message(
                phone,
                "📦 *Submit Reject*\n\n"
                "Please provide the following information:\n\n"
                "1️⃣ Order Number or Product Code"
            )
            context['step'] = 1
            whatsapp_service.update_session(
                session['id'],
                context=context
            )
            return {"status": "awaiting_order_number"}
        
        elif step == 1:
            context['order_number'] = message
            self._send_message(
                phone,
                f"✅ Order: {message}\n\n"
                "2️⃣ Please describe the defect:"
            )
            context['step'] = 2
            whatsapp_service.update_session(
                session['id'],
                context=context
            )
            return {"status": "awaiting_defect_description"}
        
        elif step == 2:
            context['defect_description'] = message
            self._send_message(
                phone,
                f"✅ Defect: {message}\n\n3️⃣ Quantity of defective items:"
            )
            context['step'] = 3
            whatsapp_service.update_session(session['id'], context=context)
            return {"status": "awaiting_quantity"}
        
        elif step == 3:
            try:
                quantity = int(message)
                context['quantity'] = quantity
                
                ticket_id = self._create_reject_ticket(session, context)
                
                whatsapp_service.send_text_message(
                    phone,
                    f"✅ *Reject Submitted Successfully!*\n\n"
                    f"Ticket ID: #{ticket_id}\n"
                    f"Order: {context['order_number']}\n"
                    f"Defect: {context['defect_description']}\n"
                    f"Quantity: {quantity}\n\n"
                    f"Your reject has been logged and the quality team will review it.\n\n"
                    f"Type 'menu' to return to main menu."
                )
                
                whatsapp_service.update_session(session['id'], state='idle', flow=None, context={})
                
                whatsapp_service.log_interaction(
                    session['id'], session.get('employee_id'), 'reject',
                    'submit_reject', ticket_id, 'replacement_ticket',
                    context, {'ticket_id': ticket_id}, 'completed'
                )
                
                return {"status": "completed", "ticket_id": ticket_id}
            except ValueError:
                whatsapp_service.send_text_message(phone, "❌ Please enter a valid number for quantity.")
                return {"status": "invalid_input"}
        
        return {"status": "unknown_step"}
    
    def _handle_return_flow(self, phone: str, session: Dict, message: str, msg_type: str, payload: Dict) -> Dict[str, Any]:
        context = session.get('context_data') or {}
        step = context.get('step', 0)
        
        if step == 0:
            whatsapp_service.send_text_message(
                phone,
                "🔄 *Customer Return*\n\nPlease provide:\n\n1️⃣ Order Number"
            )
            context['step'] = 1
            whatsapp_service.update_session(session['id'], context=context)
            return {"status": "awaiting_order_number"}
        
        elif step == 1:
            context['order_number'] = message
            whatsapp_service.send_text_message(
                phone,
                f"✅ Order: {message}\n\n2️⃣ Customer Name:"
            )
            context['step'] = 2
            whatsapp_service.update_session(session['id'], context=context)
            return {"status": "awaiting_customer_name"}
        
        elif step == 2:
            context['customer_name'] = message
            whatsapp_service.send_text_message(
                phone,
                f"✅ Customer: {message}\n\n3️⃣ Reason for return:"
            )
            context['step'] = 3
            whatsapp_service.update_session(session['id'], context=context)
            return {"status": "awaiting_reason"}
        
        elif step == 3:
            context['return_reason'] = message
            whatsapp_service.send_text_message(
                phone,
                f"✅ Reason: {message}\n\n4️⃣ Quantity being returned:"
            )
            context['step'] = 4
            whatsapp_service.update_session(session['id'], context=context)
            return {"status": "awaiting_quantity"}
        
        elif step == 4:
            try:
                quantity = int(message)
                context['quantity'] = quantity
                
                return_id = self._create_customer_return(session, context)
                
                whatsapp_service.send_text_message(
                    phone,
                    f"✅ *Customer Return Logged!*\n\n"
                    f"Return ID: #{return_id}\n"
                    f"Order: {context['order_number']}\n"
                    f"Customer: {context['customer_name']}\n"
                    f"Reason: {context['return_reason']}\n"
                    f"Quantity: {quantity}\n\n"
                    f"The return has been processed.\n\n"
                    f"Type 'menu' for main menu."
                )
                
                whatsapp_service.update_session(session['id'], state='idle', flow=None, context={})
                
                whatsapp_service.log_interaction(
                    session['id'], session.get('employee_id'), 'return',
                    'submit_return', return_id, 'customer_return',
                    context, {'return_id': return_id}, 'completed'
                )
                
                return {"status": "completed", "return_id": return_id}
            except ValueError:
                whatsapp_service.send_text_message(phone, "❌ Please enter a valid number.")
                return {"status": "invalid_input"}
        
        return {"status": "unknown_step"}
    
    def _handle_sop_failure_flow(self, phone: str, session: Dict, message: str, msg_type: str, payload: Dict) -> Dict[str, Any]:
        context = session.get('context_data') or {}
        step = context.get('step', 0)
        
        if step == 0:
            whatsapp_service.send_text_message(
                phone,
                "⚠️ *SOP Failure Report*\n\nPlease provide:\n\n1️⃣ Machine Number or Process Name"
            )
            context['step'] = 1
            whatsapp_service.update_session(session['id'], context=context)
            return {"status": "awaiting_machine"}
        
        elif step == 1:
            context['machine_process'] = message
            whatsapp_service.send_text_message(
                phone,
                f"✅ Machine/Process: {message}\n\n2️⃣ Describe the SOP failure:"
            )
            context['step'] = 2
            whatsapp_service.update_session(session['id'], context=context)
            return {"status": "awaiting_description"}
        
        elif step == 2:
            context['failure_description'] = message
            
            ticket_id = self._create_sop_failure_ticket(session, context)
            
            whatsapp_service.send_text_message(
                phone,
                f"✅ *SOP Failure Reported!*\n\n"
                f"Ticket ID: #{ticket_id}\n"
                f"Machine/Process: {context['machine_process']}\n"
                f"Description: {message}\n\n"
                f"The SOP failure has been logged for review.\n\n"
                f"Type 'menu' for main menu."
            )
            
            whatsapp_service.update_session(session['id'], state='idle', flow=None, context={})
            
            whatsapp_service.log_interaction(
                session['id'], session.get('employee_id'), 'sop_failure',
                'report_sop_failure', ticket_id, 'sop_ticket',
                context, {'ticket_id': ticket_id}, 'completed'
            )
            
            return {"status": "completed", "ticket_id": ticket_id}
        
        return {"status": "unknown_step"}
    
    def _handle_track_flow(self, phone: str, session: Dict, message: str, msg_type: str, payload: Dict) -> Dict[str, Any]:
        context = session.get('context_data') or {}
        step = context.get('step', 0)
        
        if step == 0:
            whatsapp_service.send_text_message(
                phone,
                "🔍 *Track Item*\n\nPlease enter:\n\n1️⃣ Ticket ID or Order Number to track"
            )
            context['step'] = 1
            whatsapp_service.update_session(session['id'], context=context)
            return {"status": "awaiting_tracking_number"}
        
        elif step == 1:
            tracking_info = self._get_tracking_info(message)
            
            if tracking_info:
                response_text = f"🔍 *Tracking Information*\n\n{tracking_info}"
            else:
                response_text = f"❌ No information found for: {message}\n\nPlease verify the number and try again."
            
            whatsapp_service.send_text_message(phone, response_text + "\n\nType 'menu' for main menu.")
            
            whatsapp_service.update_session(session['id'], state='idle', flow=None, context={})
            
            whatsapp_service.log_interaction(
                session['id'], session.get('employee_id'), 'track',
                'track_item', None, None,
                {'tracking_number': message}, {'found': bool(tracking_info)}, 'completed'
            )
            
            return {"status": "completed", "found": bool(tracking_info)}
        
        return {"status": "unknown_step"}
    
    def _handle_pull_data_flow(self, phone: str, session: Dict, message: str, msg_type: str, payload: Dict) -> Dict[str, Any]:
        context = session.get('context_data') or {}
        step = context.get('step', 0)
        
        if step == 0:
            whatsapp_service.send_interactive_list(
                phone,
                "📊 *Pull Data*\n\nSelect the type of data you want to retrieve:",
                "Select Report",
                [{
                    "title": "Available Reports",
                    "rows": [
                        {"id": "rejects_summary", "title": "📦 Rejects Summary", "description": "Summary of rejected items"},
                        {"id": "returns_cost", "title": "💰 Returns Cost", "description": "Cost of customer returns"},
                        {"id": "sop_failures", "title": "⚠️ SOP Failures", "description": "Recent SOP failure reports"},
                        {"id": "my_tickets", "title": "🎫 My Tickets", "description": "Your submitted tickets"}
                    ]
                }]
            )
            context['step'] = 1
            whatsapp_service.update_session(session['id'], context=context)
            return {"status": "awaiting_report_selection"}
        
        elif step == 1 and msg_type == 'interactive':
            list_reply = payload.get('list_reply', {})
            report_type = list_reply.get('id')
            
            report_data = self._generate_report(report_type, session.get('employee_id'))
            
            whatsapp_service.send_text_message(phone, report_data + "\n\nType 'menu' for main menu.")
            
            whatsapp_service.update_session(session['id'], state='idle', flow=None, context={})
            
            whatsapp_service.log_interaction(
                session['id'], session.get('employee_id'), 'pull_data',
                f'pull_{report_type}', None, None,
                {'report_type': report_type}, {'generated': True}, 'completed'
            )
            
            return {"status": "completed", "report_type": report_type}
        
        return {"status": "unknown_step"}
    
    def _create_reject_ticket(self, session: Dict, context: Dict) -> int:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO replacement_tickets 
                (order_id, product_id, employee_id, defect_description, quantity, status, reported_by_id)
                VALUES (NULL, NULL, %s, %s, %s, 'pending', %s)
            """, (session.get('employee_id'), context.get('defect_description'), 
                  context.get('quantity'), session.get('employee_id')))
            
            ticket_id = cursor.lastrowid
            conn.commit()
            cursor.close()
            conn.close()
            
            return ticket_id
        except Exception as e:
            app_logger.error(f"Failed to create reject ticket: {str(e)}")
            return 0
    
    def _create_customer_return(self, session: Dict, context: Dict) -> int:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO customer_returns 
                (order_id, customer_name, return_reason, quantity, status, reported_by_id)
                VALUES (NULL, %s, %s, %s, 'pending', %s)
            """, (context.get('customer_name'), context.get('return_reason'),
                  context.get('quantity'), session.get('employee_id')))
            
            return_id = cursor.lastrowid
            conn.commit()
            cursor.close()
            conn.close()
            
            return return_id
        except Exception as e:
            app_logger.error(f"Failed to create customer return: {str(e)}")
            return 0
    
    def _create_sop_failure_ticket(self, session: Dict, context: Dict) -> int:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO sop_tickets 
                (machine_id, employee_id, issue_description, severity, status, reported_by_id)
                VALUES (NULL, %s, %s, 'medium', 'open', %s)
            """, (session.get('employee_id'), 
                  f"{context.get('machine_process')}: {context.get('failure_description')}", 
                  session.get('employee_id')))
            
            ticket_id = cursor.lastrowid
            conn.commit()
            cursor.close()
            conn.close()
            
            return ticket_id
        except Exception as e:
            app_logger.error(f"Failed to create SOP ticket: {str(e)}")
            return 0
    
    def _get_tracking_info(self, identifier: str) -> Optional[str]:
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT 'Order' as type, id, order_number, status, created_at
                FROM orders WHERE order_number = %s
                UNION
                SELECT 'Reject' as type, id, NULL as order_number, status, created_at
                FROM replacement_tickets WHERE id = %s
                UNION
                SELECT 'Return' as type, id, NULL as order_number, status, created_at
                FROM customer_returns WHERE id = %s
                LIMIT 1
            """, (identifier, identifier, identifier))
            
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if result:
                return (f"Type: {result['type']}\n"
                       f"ID: #{result['id']}\n"
                       f"Status: {result['status']}\n"
                       f"Created: {result['created_at']}")
            
            return None
        except Exception as e:
            app_logger.error(f"Failed to get tracking info: {str(e)}")
            return None
    
    def _generate_report(self, report_type: str, employee_id: Optional[int]) -> str:
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            if report_type == 'rejects_summary':
                cursor.execute("""
                    SELECT COUNT(*) as total, SUM(quantity) as qty, status
                    FROM replacement_tickets
                    WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                    GROUP BY status
                """)
                results = cursor.fetchall()
                
                report = "📦 *Rejects Summary (Last 7 Days)*\n\n"
                for row in results:
                    report += f"• {row['status'].title()}: {row['total']} tickets ({row['qty']} items)\n"
                
            elif report_type == 'returns_cost':
                cursor.execute("""
                    SELECT COUNT(*) as total, SUM(quantity) as qty
                    FROM customer_returns
                    WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                """)
                result = cursor.fetchone()
                
                report = "💰 *Returns Cost (Last 30 Days)*\n\n"
                report += f"• Total Returns: {result['total']}\n"
                report += f"• Total Items: {result['qty']}\n"
                
            elif report_type == 'sop_failures':
                cursor.execute("""
                    SELECT COUNT(*) as total, severity, status
                    FROM sop_tickets
                    WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                    GROUP BY severity, status
                """)
                results = cursor.fetchall()
                
                report = "⚠️ *SOP Failures (Last 7 Days)*\n\n"
                for row in results:
                    report += f"• {row['severity'].title()} - {row['status'].title()}: {row['total']}\n"
                
            elif report_type == 'my_tickets':
                if not employee_id:
                    report = "❌ No employee linked to this phone number."
                else:
                    cursor.execute("""
                        SELECT 'Reject' as type, id, status, created_at
                        FROM replacement_tickets WHERE employee_id = %s
                        UNION ALL
                        SELECT 'Return' as type, id, status, created_at
                        FROM customer_returns WHERE reported_by_id = %s
                        UNION ALL
                        SELECT 'SOP' as type, id, status, created_at
                        FROM sop_tickets WHERE employee_id = %s
                        ORDER BY created_at DESC LIMIT 5
                    """, (employee_id, employee_id, employee_id))
                    results = cursor.fetchall()
                    
                    report = "🎫 *My Recent Tickets*\n\n"
                    for row in results:
                        report += f"• {row['type']} #{row['id']} - {row['status']} ({row['created_at'].strftime('%Y-%m-%d')})\n"
            else:
                report = "❌ Invalid report type."
            
            cursor.close()
            conn.close()
            
            return report if report else "📊 No data available."
            
        except Exception as e:
            app_logger.error(f"Failed to generate report: {str(e)}")
            return "❌ Error generating report."

flow_handler = WhatsAppFlowHandler()
