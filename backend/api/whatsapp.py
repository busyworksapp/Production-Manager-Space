from flask import Blueprint, request, jsonify
from backend.utils.logger import app_logger
from backend.utils.whatsapp_service import whatsapp_service
from backend.utils.whatsapp_flow_handler import flow_handler
import json

whatsapp_bp = Blueprint('whatsapp', __name__, url_prefix='/api/whatsapp')

@whatsapp_bp.route('/webhook', methods=['GET'])
def webhook_verify():
    try:
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        
        app_logger.info(f"Webhook verification request: mode={mode}, token={token}")
        
        result = whatsapp_service.verify_webhook(mode, token, challenge)
        
        if result:
            return result, 200
        else:
            return 'Verification failed', 403
            
    except Exception as e:
        app_logger.error(f"Webhook verification error: {str(e)}")
        return 'Error', 500

@whatsapp_bp.route('/webhook', methods=['POST'])
def webhook_receive():
    try:
        data = request.get_json()
        app_logger.info(f"WhatsApp webhook received: {json.dumps(data)}")
        
        if not data:
            return jsonify({'status': 'error', 'message': 'No data received'}), 400
        
        entry = data.get('entry', [])
        if not entry:
            return jsonify({'status': 'ok'}), 200
        
        for item in entry:
            changes = item.get('changes', [])
            for change in changes:
                value = change.get('value', {})
                
                if 'messages' in value:
                    messages = value.get('messages', [])
                    for message in messages:
                        process_incoming_message(message)
                
                if 'statuses' in value:
                    statuses = value.get('statuses', [])
                    for status in statuses:
                        process_message_status(status)
        
        return jsonify({'status': 'ok'}), 200
        
    except Exception as e:
        app_logger.error(f"Webhook processing error: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Alias for Twilio compatibility
@whatsapp_bp.route('/twilio-webhook', methods=['GET'])
def twilio_webhook_verify():
    """Alias for webhook verification - Twilio uses different endpoint names"""
    return webhook_verify()

@whatsapp_bp.route('/twilio-webhook', methods=['POST'])
def twilio_webhook_receive():
    """Alias for webhook receive - Twilio uses different endpoint names"""
    return webhook_receive()

def process_incoming_message(message: dict):
    try:
        phone = message.get('from')
        message_id = message.get('id')
        message_type = message.get('type')
        timestamp = message.get('timestamp')
        
        app_logger.info(f"Processing message from {phone}, type: {message_type}")
        
        message_text = ""
        payload = {}
        
        if message_type == 'text':
            message_text = message.get('text', {}).get('body', '')
            payload = message
            
        elif message_type == 'interactive':
            interactive = message.get('interactive', {})
            interactive_type = interactive.get('type')
            
            if interactive_type == 'button_reply':
                button_reply = interactive.get('button_reply', {})
                message_text = button_reply.get('title', '')
                payload = {'button_reply': button_reply, 'id': message_id}
                
            elif interactive_type == 'list_reply':
                list_reply = interactive.get('list_reply', {})
                message_text = list_reply.get('title', '')
                payload = {'list_reply': list_reply, 'id': message_id}
        
        elif message_type == 'image':
            image = message.get('image', {})
            message_text = image.get('caption', 'Image received')
            payload = message
            
        elif message_type == 'document':
            document = message.get('document', {})
            message_text = document.get('caption', 'Document received')
            payload = message
        
        else:
            app_logger.warning(f"Unsupported message type: {message_type}")
            whatsapp_service.send_text_message(
                phone,
                "❌ Unsupported message type. Please send text messages only.\n\nType 'menu' to see available options."
            )
            return
        
        flow_handler.handle_message(phone, message_text, message_type, payload)
        
    except Exception as e:
        app_logger.error(f"Error processing incoming message: {str(e)}")
        try:
            phone = message.get('from')
            if phone:
                whatsapp_service.send_text_message(
                    phone,
                    "❌ An error occurred processing your message. Please try again."
                )
        except:
            pass

def process_message_status(status: dict):
    try:
        message_id = status.get('id')
        status_type = status.get('status')
        timestamp = status.get('timestamp')
        
        app_logger.info(f"Message {message_id} status: {status_type}")
        
    except Exception as e:
        app_logger.error(f"Error processing message status: {str(e)}")

@whatsapp_bp.route('/test/send', methods=['POST'])
def test_send_message():
    try:
        data = request.get_json()
        phone = data.get('phone')
        message = data.get('message', 'Test message from PMS')
        
        if not phone:
            return jsonify({'error': 'Phone number required'}), 400
        
        result = whatsapp_service.send_text_message(phone, message)
        
        return jsonify({'status': 'success', 'result': result}), 200
        
    except Exception as e:
        app_logger.error(f"Test send error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@whatsapp_bp.route('/test/menu', methods=['POST'])
def test_send_menu():
    try:
        data = request.get_json()
        phone = data.get('phone')
        
        if not phone:
            return jsonify({'error': 'Phone number required'}), 400
        
        session = whatsapp_service.get_session(phone)
        if not session:
            session_id = whatsapp_service._get_or_create_session(phone)
            session = whatsapp_service.get_session(phone)
        
        result = flow_handler._show_main_menu(phone, session)
        
        return jsonify({'status': 'success', 'result': result}), 200
        
    except Exception as e:
        app_logger.error(f"Test menu error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@whatsapp_bp.route('/sessions', methods=['GET'])
def get_sessions():
    try:
        from backend.config.db_pool import get_db_connection
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT ws.*, e.first_name, e.last_name, e.employee_number
            FROM whatsapp_sessions ws
            LEFT JOIN employees e ON ws.employee_id = e.id
            WHERE ws.expires_at > NOW() OR ws.expires_at IS NULL
            ORDER BY ws.last_message_at DESC
            LIMIT 50
        """)
        
        sessions = cursor.fetchall()
        
        for session in sessions:
            if session.get('context_data'):
                session['context_data'] = json.loads(session['context_data']) if isinstance(session['context_data'], str) else session['context_data']
        
        cursor.close()
        conn.close()
        
        return jsonify(sessions), 200
        
    except Exception as e:
        app_logger.error(f"Error fetching sessions: {str(e)}")
        return jsonify({'error': str(e)}), 500

@whatsapp_bp.route('/interactions', methods=['GET'])
def get_interactions():
    try:
        from backend.config.db_pool import get_db_connection
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        limit = request.args.get('limit', 50, type=int)
        interaction_type = request.args.get('type')
        
        query = """
            SELECT wi.*, e.first_name, e.last_name, e.employee_number
            FROM whatsapp_interactions wi
            LEFT JOIN employees e ON wi.employee_id = e.id
        """
        
        params = []
        if interaction_type:
            query += " WHERE wi.interaction_type = %s"
            params.append(interaction_type)
        
        query += " ORDER BY wi.created_at DESC LIMIT %s"
        params.append(limit)
        
        cursor.execute(query, params)
        
        interactions = cursor.fetchall()
        
        for interaction in interactions:
            if interaction.get('request_data'):
                interaction['request_data'] = json.loads(interaction['request_data']) if isinstance(interaction['request_data'], str) else interaction['request_data']
            if interaction.get('response_data'):
                interaction['response_data'] = json.loads(interaction['response_data']) if isinstance(interaction['response_data'], str) else interaction['response_data']
        
        cursor.close()
        conn.close()
        
        return jsonify(interactions), 200
        
    except Exception as e:
        app_logger.error(f"Error fetching interactions: {str(e)}")
        return jsonify({'error': str(e)}), 500

@whatsapp_bp.route('/messages/<phone>', methods=['GET'])
def get_messages_by_phone(phone: str):
    try:
        from backend.config.db_pool import get_db_connection
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        limit = request.args.get('limit', 50, type=int)
        
        cursor.execute("""
            SELECT * FROM whatsapp_messages
            WHERE phone_number = %s
            ORDER BY created_at DESC
            LIMIT %s
        """, (phone, limit))
        
        messages = cursor.fetchall()
        
        for message in messages:
            if message.get('payload'):
                message['payload'] = json.loads(message['payload']) if isinstance(message['payload'], str) else message['payload']
        
        cursor.close()
        conn.close()
        
        return jsonify(messages), 200
        
    except Exception as e:
        app_logger.error(f"Error fetching messages: {str(e)}")
        return jsonify({'error': str(e)}), 500
