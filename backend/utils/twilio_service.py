"""
Twilio Integration Service
Handles SMS and voice communications via Twilio API
"""

import os
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from backend.utils.logger import app_logger
from backend.config.db_pool import get_db_connection

load_dotenv()


class TwilioService:
    """Service for managing Twilio SMS and voice communications"""

    def __init__(self):
        """Initialize Twilio client with credentials from environment"""
        self.account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.from_phone = os.getenv('TWILIO_FROM_PHONE')
        
        if not all([self.account_sid, self.auth_token, self.from_phone]):
            app_logger.warning(
                'Twilio credentials not fully configured. '
                'SMS and voice features will be limited.'
            )
            self.client = None
        else:
            try:
                self.client = Client(self.account_sid, self.auth_token)
                app_logger.info('Twilio client initialized successfully')
            except Exception as e:
                app_logger.error(f'Failed to initialize Twilio client: {e}')
                self.client = None

    def send_sms(
        self,
        to_phone: str,
        message: str,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Send an SMS message via Twilio

        Args:
            to_phone: Recipient phone number in E.164 format
            message: Message content
            user_id: Optional user ID for logging

        Returns:
            Dictionary with status and message SID
        """
        if not self.client:
            app_logger.error('Twilio client not initialized')
            return {'success': False, 'error': 'Twilio not configured'}

        if not self._validate_phone(to_phone):
            app_logger.error(f'Invalid phone number format: {to_phone}')
            return {'success': False, 'error': 'Invalid phone number'}

        try:
            msg = self.client.messages.create(
                body=message,
                from_=self.from_phone,
                to=to_phone
            )

            # Log SMS in database
            if user_id:
                self._log_communication(
                    user_id=user_id,
                    type='sms',
                    to_phone=to_phone,
                    message=message,
                    external_id=msg.sid,
                    status='sent'
                )

            app_logger.info(
                f'SMS sent successfully to {to_phone} (SID: {msg.sid})'
            )
            return {
                'success': True,
                'message_sid': msg.sid,
                'status': msg.status,
                'to': to_phone
            }

        except TwilioRestException as e:
            app_logger.error(
                f'Twilio SMS error to {to_phone}: {e.msg}'
            )
            if user_id:
                self._log_communication(
                    user_id=user_id,
                    type='sms',
                    to_phone=to_phone,
                    message=message,
                    status='failed',
                    error=str(e)
                )
            return {
                'success': False,
                'error': str(e),
                'error_code': e.code
            }

    def send_bulk_sms(
        self,
        recipients: List[Dict[str, Any]],
        message: str
    ) -> Dict[str, Any]:
        """
        Send SMS to multiple recipients

        Args:
            recipients: List of dicts with 'phone' and optional 'user_id'
            message: Message to send

        Returns:
            Dictionary with results summary
        """
        results = {
            'total': len(recipients),
            'successful': 0,
            'failed': 0,
            'details': []
        }

        for recipient in recipients:
            phone = recipient.get('phone')
            user_id = recipient.get('user_id')

            if not phone:
                results['failed'] += 1
                results['details'].append({
                    'phone': phone,
                    'success': False,
                    'error': 'No phone number provided'
                })
                continue

            result = self.send_sms(phone, message, user_id)
            if result['success']:
                results['successful'] += 1
            else:
                results['failed'] += 1

            results['details'].append({
                'phone': phone,
                **result
            })

        app_logger.info(
            f'Bulk SMS sent: {results["successful"]}/{results["total"]} '
            f'successful'
        )
        return results

    def send_sms_to_department(
        self,
        department_id: int,
        message: str,
        exclude_user_ids: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """
        Send SMS to all employees in a department

        Args:
            department_id: Department ID
            message: Message to send
            exclude_user_ids: Optional list of user IDs to exclude

        Returns:
            Results summary
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            sql = """
                SELECT DISTINCT u.id, e.phone
                FROM users u
                JOIN employees e ON u.id = e.user_id
                WHERE e.department_id = %s
                AND e.phone IS NOT NULL
                AND e.phone != ''
                AND u.is_active = TRUE
            """

            params = [department_id]
            if exclude_user_ids:
                placeholders = ','.join(['%s'] * len(exclude_user_ids))
                sql += f' AND u.id NOT IN ({placeholders})'
                params.extend(exclude_user_ids)

            cursor.execute(sql, params)
            employees = cursor.fetchall()

            recipients = [
                {
                    'phone': emp['phone'],
                    'user_id': emp['id']
                }
                for emp in employees
            ]

            cursor.close()
            conn.close()

            return self.send_bulk_sms(recipients, message)

        except Exception as e:
            app_logger.error(
                f'Error sending SMS to department {department_id}: {e}'
            )
            return {
                'success': False,
                'error': str(e)
            }

    def make_call(
        self,
        to_phone: str,
        twiml: str,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Initiate an outbound call via Twilio

        Args:
            to_phone: Recipient phone number
            twiml: TwiML instructions for the call
            user_id: Optional user ID for logging

        Returns:
            Dictionary with call details
        """
        if not self.client:
            return {'success': False, 'error': 'Twilio not configured'}

        try:
            call = self.client.calls.create(
                to=to_phone,
                from_=self.from_phone,
                twiml=twiml
            )

            if user_id:
                self._log_communication(
                    user_id=user_id,
                    type='call',
                    to_phone=to_phone,
                    external_id=call.sid,
                    status='initiated'
                )

            app_logger.info(
                f'Call initiated to {to_phone} (SID: {call.sid})'
            )
            return {
                'success': True,
                'call_sid': call.sid,
                'status': call.status,
                'to': to_phone
            }

        except TwilioRestException as e:
            app_logger.error(f'Twilio call error to {to_phone}: {e.msg}')
            return {
                'success': False,
                'error': str(e),
                'error_code': e.code
            }

    def get_message_status(self, message_sid: str) -> Dict[str, Any]:
        """
        Get the status of a sent message

        Args:
            message_sid: Twilio message SID

        Returns:
            Message status information
        """
        if not self.client:
            return {'success': False, 'error': 'Twilio not configured'}

        try:
            message = self.client.messages(message_sid).fetch()
            return {
                'success': True,
                'sid': message.sid,
                'status': message.status,
                'to': message.to,
                'from': message.from_,
                'date_sent': message.date_sent,
                'price': message.price,
                'error_message': message.error_message
            }
        except TwilioRestException as e:
            app_logger.error(f'Error fetching message status: {e.msg}')
            return {
                'success': False,
                'error': str(e)
            }

    def get_call_status(self, call_sid: str) -> Dict[str, Any]:
        """
        Get the status of a call

        Args:
            call_sid: Twilio call SID

        Returns:
            Call status information
        """
        if not self.client:
            return {'success': False, 'error': 'Twilio not configured'}

        try:
            call = self.client.calls(call_sid).fetch()
            return {
                'success': True,
                'sid': call.sid,
                'status': call.status,
                'to': call.to,
                'from': call.from_,
                'duration': call.duration,
                'start_time': call.start_time,
                'end_time': call.end_time
            }
        except TwilioRestException as e:
            app_logger.error(f'Error fetching call status: {e.msg}')
            return {
                'success': False,
                'error': str(e)
            }

    def _validate_phone(self, phone: str) -> bool:
        """Validate phone number format (E.164)"""
        if not phone:
            return False
        return phone.startswith('+') and len(phone) >= 10

    def send_whatsapp_message(
        self,
        to_phone: str,
        message: str
    ) -> Dict[str, Any]:
        """
        Send a WhatsApp message via Twilio
        
        Args:
            to_phone: Recipient WhatsApp number (e.g., 'whatsapp:+27788494933')
            message: Message content
            
        Returns:
            Dictionary with status and message SID
        """
        if not self.client:
            app_logger.error('Twilio client not initialized')
            return {'success': False, 'error': 'Twilio not configured'}
        
        try:
            # Ensure to_phone has whatsapp: prefix
            if not to_phone.startswith('whatsapp:'):
                to_phone = f'whatsapp:{to_phone}'
            
            msg = self.client.messages.create(
                body=message,
                from_=f'whatsapp:{self.from_phone}',
                to=to_phone
            )
            
            app_logger.info(
                f'WhatsApp message sent successfully to {to_phone} (SID: {msg.sid})'
            )
            return {
                'success': True,
                'message_sid': msg.sid,
                'status': msg.status,
                'to': to_phone
            }
            
        except TwilioRestException as e:
            app_logger.error(
                f'Twilio WhatsApp error to {to_phone}: {e.msg}'
            )
            return {
                'success': False,
                'error': str(e),
                'error_code': e.code
            }
        except Exception as e:
            app_logger.error(
                f'Failed to send WhatsApp message to {to_phone}: {str(e)}'
            )
            return {
                'success': False,
                'error': str(e)
            }

    def _log_communication(
        self,
        user_id: int,
        type: str,
        to_phone: str,
        message: Optional[str] = None,
        external_id: Optional[str] = None,
        status: str = 'pending',
        error: Optional[str] = None
    ) -> None:
        """Log communication in database"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            sql = """
                INSERT INTO communication_log
                (user_id, type, to_phone, message, external_id, status, error)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """

            cursor.execute(sql, (
                user_id,
                type,
                to_phone,
                message,
                external_id,
                status,
                error
            ))

            conn.commit()
            cursor.close()
            conn.close()

        except Exception as e:
            app_logger.error(f'Failed to log communication: {e}')


# Singleton instance
twilio_service = TwilioService()
