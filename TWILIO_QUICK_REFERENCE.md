# Twilio Integration - Quick Reference & Test Guide

## 🚀 Quick Start

Your Twilio integration is now active with:
- **Account SID**: your_account_sid_here
- **From Phone**: +14155238886
- **Status**: ✅ Connected

## 📱 Send SMS Example

```bash
curl -X POST http://localhost:5000/api/notifications/send-sms \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "phone": "+27123456789",
    "message": "Your order #12345 is ready for pickup",
    "type": "order_status"
  }'
```

## ☎️ Send Voice Call Example

```bash
curl -X POST http://localhost:5000/api/notifications/send-voice \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "phone": "+27123456789",
    "message": "Critical maintenance alert for machine MACH001"
  }'
```

## 📧 Send Email Example

```bash
curl -X POST http://localhost:5000/api/notifications/send-email \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "email": "user@example.com",
    "subject": "Order Status Update",
    "message": "Your order has been completed",
    "type": "order_status"
  }'
```

## 🔑 Getting JWT Token

1. Login with test credentials:
```bash
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin@barron",
    "password": "Admin@2026!"
  }'
```

2. Copy the `access_token` from response
3. Use it in Authorization header for other requests

## 📝 Available Notification Types

### SMS Types
- `order_status` - Order updates
- `maintenance_alert` - Equipment alerts
- `production_update` - Production news
- `shift_reminder` - Shift notifications
- `sla_escalation` - SLA alerts
- `test` - Test message

### Voice Types
- `critical_alert` - Critical alerts
- `sla_escalation` - SLA calls
- `maintenance_urgent` - Urgent maintenance
- `test` - Test call

## 🧪 Test Credentials

**Admin User:**
- Username: `admin@barron`
- Password: `Admin@2026!`
- Role: Admin (full access)

**Operator User:**
- Username: `operator.mike`
- Password: `Operator@2026!`
- Role: Operator

## 📊 Check Notification Status

Query the database to see sent notifications:

```sql
SELECT * FROM notifications 
WHERE created_at >= DATE_SUB(NOW(), INTERVAL 1 DAY) 
ORDER BY created_at DESC;
```

## 🔗 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/notifications/send-sms` | Send SMS |
| POST | `/api/notifications/send-voice` | Make call |
| POST | `/api/notifications/send-email` | Send email |
| POST | `/api/whatsapp/twilio-webhook` | Receive messages |
| GET | `/api/whatsapp/twilio-webhook` | Verify webhook |

## 🐛 Debugging

### Enable Verbose Logging
Check `/logs` directory for detailed logs:
```bash
tail -f logs/pms.log | grep -i twilio
```

### Test Message Response Format

Successful SMS:
```json
{
  "success": true,
  "message": "SMS sent successfully",
  "sid": "SM1234567890abcdefghijklmnop",
  "to": "+27123456789",
  "from": "+14155238886"
}
```

Error Response:
```json
{
  "success": false,
  "error": "Invalid phone number format",
  "code": "INVALID_PHONE"
}
```

## ⚙️ Configuration Files

- `.env` - Main configuration (includes Twilio credentials)
- `backend/utils/whatsapp_service.py` - Twilio service
- `backend/api/whatsapp.py` - Webhook handlers
- `TWILIO_SETUP.md` - Detailed setup guide

## 🌐 Twilio Dashboard

Access your Twilio account:
- **URL**: https://www.twilio.com/console
- **Account SID**: your_account_sid_here

Monitor:
- Message logs
- Call logs
- Webhook delivery
- Usage and billing

## 💡 Common Issues

### "Invalid phone number"
- Use E.164 format: +1234567890
- Include country code
- No spaces or special characters

### "Authentication failed"
- Verify JWT token is valid
- Check Authorization header format
- Ensure user has notification permissions

### "Webhook not received"
- Verify webhook URL in Twilio dashboard
- Check firewall/security rules
- Ensure Railway app is running
- Verify webhook endpoint is accessible

## 🎯 Next Steps

1. ✅ Get JWT token by logging in
2. Send a test SMS to verify integration
3. Configure notification rules in admin panel
4. Set up automated alerts
5. Monitor webhook deliveries

## 📞 Support

- **Twilio Status**: https://status.twilio.com
- **Twilio Docs**: https://www.twilio.com/docs
- **Account Dashboard**: https://www.twilio.com/console
