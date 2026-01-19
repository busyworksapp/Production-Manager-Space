import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import os
from datetime import datetime

def send_email(recipients, subject, body, attachments=None):
    smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
    smtp_port = int(os.getenv('SMTP_PORT', 587))
    smtp_user = os.getenv('SMTP_USER')
    smtp_password = os.getenv('SMTP_PASSWORD')
    sender_email = os.getenv('SENDER_EMAIL', smtp_user)
    
    if not smtp_user or not smtp_password:
        raise Exception('SMTP credentials not configured')
    
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = ', '.join(recipients) if isinstance(recipients, list) else recipients
    msg['Subject'] = subject
    msg['Date'] = datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')
    
    msg.attach(MIMEText(body, 'html'))
    
    if attachments:
        for attachment in attachments:
            with open(attachment['path'], 'rb') as f:
                part = MIMEApplication(f.read(), Name=attachment['name'])
                part['Content-Disposition'] = f'attachment; filename="{attachment["name"]}"'
                msg.attach(part)
    
    try:
        server = smtplib.SMTP(smtp_host, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Email sending failed: {str(e)}")
        return False
