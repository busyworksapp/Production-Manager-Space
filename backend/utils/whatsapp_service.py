import os
import requests
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from threading import Thread
from backend.utils.logger import app_logger
from backend.config.db_pool import get_db_connection

class WhatsAppService:
    def __init__(self):
        self.api_url = os.getenv('WHATSAPP_API_URL', 'https://graph.facebook.com/v18.0')
        self.phone_number_id = os.getenv('WHATSAPP_PHONE_NUMBER_ID')
        self.access_token = os.getenv('WHATSAPP_ACCESS_TOKEN')
        self.verify_token = os.getenv('WHATSAPP_VERIFY_TOKEN')
        self.business_account_id = os.getenv('WHATSAPP_BUSINESS_ACCOUNT_ID')
        self.twilio_service = None  # Lazy load
        
    def _get_twilio_service(self):
        """Lazy load Twilio service to avoid circular imports"""
        if self.twilio_service is None:
            try:
                from backend.utils.twilio_service import twilio_service
                self.twilio_service = twilio_service
            except Exception as e:
                app_logger.debug(f"Could not load Twilio: {e}")
        return self.twilio_service
    
    def _log_message_async(self, phone: str, direction: str, msg_type: str,
                           content: str, payload: Dict, status: str = 'sent'):
        """Log message asynchronously to avoid blocking message processing"""
        thread = Thread(
            target=self._log_message,
            args=(phone, direction, msg_type, content, payload, status),
            daemon=True
        )
        thread.start()
    
    def send_text_message(self, to: str, message: str) -> Dict[str, Any]:
        # Try Twilio first (for Twilio WhatsApp integration)
        twilio_svc = self._get_twilio_service()
        if twilio_svc:
            try:
                result = twilio_svc.send_whatsapp_message(to, message)
                if result.get('success'):
                    # Log message asynchronously to avoid blocking
                    self._log_message_async(
                        to,
                        'outbound',
                        'text',
                        message,
                        result
                    )
                    app_logger.info(
                        f"Message sent via Twilio to {to}: "
                        f"{message[:50]}..."
                    )
                    return result
            except Exception as e:
                app_logger.debug(
                    f"Twilio send failed, trying Graph API: {e}"
                )
        
        # Fallback to Graph API (for Meta WhatsApp Business)
        url = f"{self.api_url}/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": message}
        }
        
        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            result = response.json()
            
            # Log message asynchronously to avoid blocking
            self._log_message_async(to, 'outbound', 'text', message, result)
            app_logger.info(
                f"Message sent via Graph API to {to}: "
                f"{message[:50]}..."
            )
            return result
        except Exception as e:
            app_logger.error(
                f"Failed to send message to {to}: {str(e)}"
            )
            self._log_message_async(
                to,
                'outbound',
                'text',
                message,
                {'error': str(e)},
                status='failed'
            )
            raise
    
    def send_interactive_buttons(self, to: str, body_text: str, buttons: List[Dict[str, str]]) -> Dict[str, Any]:
        url = f"{self.api_url}/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        button_components = []
        for btn in buttons[:3]:
            button_components.append({
                "type": "reply",
                "reply": {
                    "id": btn.get("id"),
                    "title": btn.get("title")
                }
            })
        
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": body_text},
                "action": {"buttons": button_components}
            }
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            response.raise_for_status()
            result = response.json()
            
            # Log asynchronously
            self._log_message_async(to, 'outbound', 'interactive', body_text, result)
            app_logger.info(f"Interactive buttons sent to {to}")
            return result
        except Exception as e:
            app_logger.error(f"Failed to send interactive buttons to {to}: {str(e)}")
            self._log_message_async(to, 'outbound', 'interactive', body_text, {'error': str(e)}, status='failed')
            raise
    
    def send_interactive_list(self, to: str, body_text: str, button_text: str, sections: List[Dict[str, Any]]) -> Dict[str, Any]:
        url = f"{self.api_url}/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "list",
                "body": {"text": body_text},
                "action": {
                    "button": button_text,
                    "sections": sections
                }
            }
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            response.raise_for_status()
            result = response.json()
            
            # Log asynchronously
            self._log_message_async(to, 'outbound', 'list', body_text, result)
            app_logger.info(f"Interactive list sent to {to}")
            return result
        except Exception as e:
            app_logger.error(f"Failed to send interactive list to {to}: {str(e)}")
            self._log_message_async(to, 'outbound', 'list', body_text, {'error': str(e)}, status='failed')
            raise
    
    def _log_message(self, phone: str, direction: str, msg_type: str, content: str, payload: Dict, status: str = 'sent'):
        """Log message to database (non-blocking for outbound)"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            session_id = self._get_or_create_session(phone)
            
            message_id = payload.get('messages', [{}])[0].get('id') if direction == 'outbound' else payload.get('id')
            
            cursor.execute("""
                INSERT INTO whatsapp_messages 
                (session_id, phone_number, message_id, direction, message_type, message_content, payload, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (session_id, phone, message_id, direction, msg_type, content, json.dumps(payload), status))
            
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            app_logger.error(f"Failed to log message: {type(e).__name__}: {str(e)}", exc_info=True)
    
    def _get_or_create_session(self, phone: str) -> int:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id FROM whatsapp_sessions 
            WHERE phone_number = %s AND (expires_at IS NULL OR expires_at > NOW())
            ORDER BY created_at DESC LIMIT 1
        """, (phone,))
        
        result = cursor.fetchone()
        
        if result:
            # Result is a dict from DictCursor
            session_id = result['id'] if isinstance(result, dict) else result[0]
            cursor.execute("""
                UPDATE whatsapp_sessions 
                SET last_message_at = NOW(), expires_at = DATE_ADD(NOW(), INTERVAL 24 HOUR)
                WHERE id = %s
            """, (session_id,))
        else:
            employee_id = self._get_employee_by_phone(phone)
            cursor.execute("""
                INSERT INTO whatsapp_sessions 
                (phone_number, employee_id, session_state, expires_at)
                VALUES (%s, %s, 'idle', DATE_ADD(NOW(), INTERVAL 24 HOUR))
            """, (phone, employee_id))
            session_id = cursor.lastrowid
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return session_id
    
    def _get_employee_by_phone(self, phone: str) -> Optional[int]:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            clean_phone = phone.replace('+', '').replace(' ', '').replace('-', '')
            
            cursor.execute("""
                SELECT id FROM employees 
                WHERE REPLACE(REPLACE(REPLACE(phone, '+', ''), ' ', ''), '-', '') = %s
                AND is_active = TRUE
                LIMIT 1
            """, (clean_phone,))
            
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            
            return result[0] if result else None
        except Exception as e:
            app_logger.error(f"Failed to get employee by phone: {str(e)}")
            return None
    
    def get_session(self, phone: str) -> Optional[Dict[str, Any]]:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM whatsapp_sessions 
                WHERE phone_number = %s 
                AND (expires_at IS NULL OR expires_at > NOW())
                ORDER BY created_at DESC LIMIT 1
            """, (phone,))
            
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if (
                result
                and result.get('context_data')
            ):
                context_data = result['context_data']
                if isinstance(context_data, str):
                    result['context_data'] = json.loads(context_data)
            
            return result
        except Exception as e:
            app_logger.error(f"Failed to get session: {str(e)}")
            return None
    
    def update_session(self, session_id: int, state: str = None, flow: str = None, context: Dict = None):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            updates = []
            params = []
            
            if state:
                updates.append("session_state = %s")
                params.append(state)
            
            if flow is not None:
                updates.append("current_flow = %s")
                params.append(flow)
            
            if context is not None:
                updates.append("context_data = %s")
                params.append(json.dumps(context))
            
            if updates:
                params.append(session_id)
                query = f"UPDATE whatsapp_sessions SET {', '.join(updates)}, last_message_at = NOW() WHERE id = %s"
                cursor.execute(query, params)
                conn.commit()
            
            cursor.close()
            conn.close()
        except Exception as e:
            app_logger.error(f"Failed to update session: {str(e)}")
    
    def log_interaction(self, session_id: int, employee_id: Optional[int], interaction_type: str, 
                       action: str, reference_id: int = None, reference_type: str = None,
                       request_data: Dict = None, response_data: Dict = None, status: str = 'initiated') -> int:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO whatsapp_interactions 
                (session_id, employee_id, interaction_type, action_taken, reference_id, reference_type, 
                 request_data, response_data, status, completed_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (session_id, employee_id, interaction_type, action, reference_id, reference_type,
                  json.dumps(request_data) if request_data else None,
                  json.dumps(response_data) if response_data else None,
                  status,
                  datetime.now() if status == 'completed' else None))
            
            interaction_id = cursor.lastrowid
            conn.commit()
            cursor.close()
            conn.close()
            
            return interaction_id
        except Exception as e:
            app_logger.error(f"Failed to log interaction: {str(e)}")
            return 0
    
    def update_interaction(self, interaction_id: int, status: str, response_data: Dict = None):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE whatsapp_interactions 
                SET status = %s, response_data = %s, completed_at = NOW()
                WHERE id = %s
            """, (status, json.dumps(response_data) if response_data else None, interaction_id))
            
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            app_logger.error(f"Failed to update interaction: {str(e)}")

whatsapp_service = WhatsAppService()
