from flask import Blueprint, request
from backend.config.database import execute_query
from backend.utils.auth import token_required
from backend.utils.response import success_response, error_response
from backend.utils.notifications import get_user_notifications, mark_notification_read

notifications_bp = Blueprint('notifications', __name__, url_prefix='/api/notifications')

@notifications_bp.route('', methods=['GET'])
@token_required
def get_notifications():
    user_id = request.current_user['user_id']
    unread_only = request.args.get('unread_only', 'false').lower() == 'true'
    limit = int(request.args.get('limit', 50))
    
    notifications = get_user_notifications(user_id, unread_only, limit)
    return success_response(notifications)

@notifications_bp.route('/<int:id>/read', methods=['POST'])
@token_required
def mark_read(id):
    user_id = request.current_user['user_id']
    
    mark_notification_read(id, user_id)
    
    return success_response(message='Notification marked as read')

@notifications_bp.route('/mark-all-read', methods=['POST'])
@token_required
def mark_all_read():
    user_id = request.current_user['user_id']
    
    execute_query(
        """UPDATE notifications 
           SET is_read = TRUE, read_at = NOW()
           WHERE recipient_id = %s AND is_read = FALSE""",
        (user_id,),
        commit=True
    )
    
    return success_response(message='All notifications marked as read')

@notifications_bp.route('/unread-count', methods=['GET'])
@token_required
def get_unread_count():
    user_id = request.current_user['user_id']
    
    result = execute_query(
        "SELECT COUNT(*) as count FROM notifications WHERE recipient_id = %s AND is_read = FALSE",
        (user_id,),
        fetch_one=True
    )
    
    return success_response({'count': result['count']})
