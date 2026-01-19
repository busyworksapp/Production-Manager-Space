from backend.config.database import execute_query
from datetime import datetime

def create_notification(recipient_id, notification_type, title, message, 
                       related_entity_type=None, related_entity_id=None, 
                       action_url=None, priority='normal'):
    query = """
        INSERT INTO notifications 
        (recipient_id, notification_type, title, message, related_entity_type, 
         related_entity_id, action_url, priority)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    execute_query(
        query,
        (recipient_id, notification_type, title, message, related_entity_type,
         related_entity_id, action_url, priority),
        commit=True
    )

def get_user_notifications(user_id, unread_only=False, limit=50):
    query = """
        SELECT * FROM notifications 
        WHERE recipient_id = %s
    """
    
    if unread_only:
        query += " AND is_read = FALSE"
    
    query += " ORDER BY created_at DESC LIMIT %s"
    
    return execute_query(query, (user_id, limit), fetch_all=True)

def mark_notification_read(notification_id, user_id):
    query = """
        UPDATE notifications 
        SET is_read = TRUE, read_at = %s
        WHERE id = %s AND recipient_id = %s
    """
    
    execute_query(query, (datetime.now(), notification_id, user_id), commit=True)
