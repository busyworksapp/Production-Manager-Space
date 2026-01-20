"""
Twilio API Endpoints
Handles SMS, voice calls, and communication management
"""

from flask import Blueprint, request
from backend.utils.auth import token_required
from backend.utils.response import success_response, error_response
from backend.utils.twilio_service import twilio_service
from backend.utils.logger import app_logger

twilio_bp = Blueprint('twilio', __name__, url_prefix='/api/twilio')


@twilio_bp.route('/health', methods=['GET'])
def twilio_health():
    """Check Twilio service health"""
    if twilio_service.client:
        return success_response(
            {'status': 'connected', 'message': 'Twilio service is active'}
        )
    else:
        return error_response('Twilio service not configured', 503)


@twilio_bp.route('/send-sms', methods=['POST'])
@token_required
def send_sms():
    """
    Send an SMS message
    Required: to_phone, message
    Optional: send_to_user_id (to log against a user)
    """
    try:
        data = request.get_json()
        to_phone = data.get('to_phone')
        message = data.get('message')
        send_to_user_id = data.get('send_to_user_id')

        if not to_phone or not message:
            return error_response(
                'Missing required fields: to_phone, message',
                400
            )

        result = twilio_service.send_sms(
            to_phone=to_phone,
            message=message,
            user_id=send_to_user_id
        )

        if result['success']:
            return success_response(result)
        else:
            return error_response(result.get('error'), 400)

    except Exception as e:
        app_logger.error(f'Error in send_sms: {e}')
        return error_response(str(e), 500)


@twilio_bp.route('/send-bulk-sms', methods=['POST'])
@token_required
def send_bulk_sms():
    """
    Send SMS to multiple recipients
    Required: recipients (list of dicts with 'phone' and optional 'user_id')
              message
    """
    try:
        data = request.get_json()
        recipients = data.get('recipients', [])
        message = data.get('message')

        if not recipients or not message:
            return error_response(
                'Missing required fields: recipients, message',
                400
            )

        result = twilio_service.send_bulk_sms(recipients, message)
        return success_response(result)

    except Exception as e:
        app_logger.error(f'Error in send_bulk_sms: {e}')
        return error_response(str(e), 500)


@twilio_bp.route('/send-to-department', methods=['POST'])
@token_required
def send_to_department():
    """
    Send SMS to all employees in a department
    Required: department_id, message
    Optional: exclude_user_ids (list of user IDs to exclude)
    """
    try:
        data = request.get_json()
        department_id = data.get('department_id')
        message = data.get('message')
        exclude_user_ids = data.get('exclude_user_ids', [])

        if not department_id or not message:
            return error_response(
                'Missing required fields: department_id, message',
                400
            )

        result = twilio_service.send_sms_to_department(
            department_id=department_id,
            message=message,
            exclude_user_ids=exclude_user_ids
        )

        if result.get('success') is False and 'error' in result:
            return error_response(result['error'], 400)

        return success_response(result)

    except Exception as e:
        app_logger.error(f'Error in send_to_department: {e}')
        return error_response(str(e), 500)


@twilio_bp.route('/make-call', methods=['POST'])
@token_required
def make_call():
    """
    Initiate an outbound call
    Required: to_phone, twiml
    Optional: user_id (for logging)

    TwiML Example:
    <Response>
        <Say voice="woman">Hello, this is a test call</Say>
        <Hangup/>
    </Response>
    """
    try:
        data = request.get_json()
        to_phone = data.get('to_phone')
        twiml = data.get('twiml')
        user_id = data.get('user_id')

        if not to_phone or not twiml:
            return error_response(
                'Missing required fields: to_phone, twiml',
                400
            )

        result = twilio_service.make_call(to_phone, twiml, user_id)

        if result['success']:
            return success_response(result)
        else:
            return error_response(result.get('error'), 400)

    except Exception as e:
        app_logger.error(f'Error in make_call: {e}')
        return error_response(str(e), 500)


@twilio_bp.route('/message-status/<message_sid>', methods=['GET'])
@token_required
def get_message_status(message_sid):
    """Get status of a sent message"""
    try:
        result = twilio_service.get_message_status(message_sid)

        if result['success']:
            return success_response(result)
        else:
            return error_response(result.get('error'), 404)

    except Exception as e:
        app_logger.error(f'Error in get_message_status: {e}')
        return error_response(str(e), 500)


@twilio_bp.route('/call-status/<call_sid>', methods=['GET'])
@token_required
def get_call_status(call_sid):
    """Get status of a call"""
    try:
        result = twilio_service.get_call_status(call_sid)

        if result['success']:
            return success_response(result)
        else:
            return error_response(result.get('error'), 404)

    except Exception as e:
        app_logger.error(f'Error in get_call_status: {e}')
        return error_response(str(e), 500)


@twilio_bp.route('/webhook/sms', methods=['POST'])
def sms_webhook():
    """
    Webhook for incoming SMS messages
    Called by Twilio when a message is received
    """
    try:
        from_phone = request.form.get('From')
        to_phone = request.form.get('To')
        message_body = request.form.get('Body')
        message_sid = request.form.get('MessageSid')

        app_logger.info(
            f'Incoming SMS from {from_phone}: {message_body} (SID: {message_sid})'
        )

        # TODO: Process incoming message logic here
        # - Store in database
        # - Trigger notifications
        # - Route to appropriate handler

        return success_response(
            {'status': 'received', 'message_sid': message_sid}
        )

    except Exception as e:
        app_logger.error(f'Error processing SMS webhook: {e}')
        return error_response(str(e), 500)


@twilio_bp.route('/webhook/call', methods=['POST'])
def call_webhook():
    """
    Webhook for call status updates
    Called by Twilio when a call status changes
    """
    try:
        call_sid = request.form.get('CallSid')
        call_status = request.form.get('CallStatus')
        from_phone = request.form.get('From')
        to_phone = request.form.get('To')

        app_logger.info(
            f'Call status update: {call_sid} - {call_status}'
        )

        # TODO: Process call status logic here
        # - Update database
        # - Trigger notifications
        # - Handle call completion

        return success_response(
            {'status': 'updated', 'call_sid': call_sid}
        )

    except Exception as e:
        app_logger.error(f'Error processing call webhook: {e}')
        return error_response(str(e), 500)
