# Twilio Quick Start Guide

## 🚀 Quick Setup

Your Twilio integration is ready! Here's everything you need to know:

### Active Configuration
```
Account SID: your_account_sid_here
Auth Token: your_auth_token_here
Webhook URL: https://pms-production-ccc7.up.railway.app/api/whatsapp/twilio-webhook
App URL: https://pms-production-ccc7.up.railway.app
```

## 📋 Available API Endpoints

### 1. Check Service Status
```bash
GET /api/twilio/health
```

### 2. Send SMS Message
```bash
POST /api/twilio/send-sms
Body: {
  "to_phone": "+27123456789",
  "message": "Your message here",
  "send_to_user_id": 1
}
```

### 3. Send Bulk SMS
```bash
POST /api/twilio/send-bulk-sms
Body: {
  "message": "Message to all recipients",
  "recipients": [
    {"phone": "+27123456789", "user_id": 1},
    {"phone": "+27987654321", "user_id": 2}
  ]
}
```

### 4. Send SMS to Department
```bash
POST /api/twilio/send-to-department
Body: {
  "department_id": 1,
  "message": "Department announcement"
}
```

### 5. Send Alert
```bash
POST /api/twilio/send-alert
Body: {
  "user_id": 1,
  "alert_type": "maintenance",
  "alert_data": {
    "machine_id": 1,
    "machine_name": "Machine Name",
    "issue": "Issue description"
  }
}
```

### 6. Make Voice Call
```bash
POST /api/twilio/make-call
Body: {
  "to_phone": "+27123456789",
  "message": "Emergency alert message",
  "user_id": 1
}
```

### 7. Get Communication History
```bash
GET /api/twilio/communications?user_id=1&limit=50
```

### 8. Get Delivery Status
```bash
GET /api/twilio/delivery-status?message_sid=SM1234567890
```

## 🔑 Authentication

All endpoints require JWT token in header:
```
Authorization: Bearer YOUR_JWT_TOKEN
```

## 📱 Test Credentials

Use these credentials to get a JWT token:

**Admin User:**
- Username: `admin@barron`
- Password: `Admin@2026!`

**Operator User:**
- Username: `operator.mike`
- Password: `Operator@2026!`

**Manager User:**
- Username: `manager.john`
- Password: `Manager@2026!`

**Finance User:**
- Username: `finance.david`
- Password: `Finance@2026!`

## 💻 Complete Test Script (Python)

```python
import requests
import json

# Configuration
BASE_URL = "https://pms-production-ccc7.up.railway.app"
USERNAME = "operator.mike"
PASSWORD = "Operator@2026!"

# Step 1: Login to get JWT token
print("🔐 Logging in...")
login_response = requests.post(
    f"{BASE_URL}/api/auth/login",
    json={"username": USERNAME, "password": PASSWORD}
)

if login_response.status_code != 200:
    print(f"❌ Login failed: {login_response.text}")
    exit(1)

token = login_response.json()['data']['token']
print(f"✅ Login successful! Token: {token[:20]}...")

# Setup headers
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

# Step 2: Check Twilio health
print("\n📡 Checking Twilio service health...")
health_response = requests.get(f"{BASE_URL}/api/twilio/health", headers=headers)
print(f"Status: {health_response.json()}")

# Step 3: Send test SMS
print("\n📱 Sending test SMS...")
sms_response = requests.post(
    f"{BASE_URL}/api/twilio/send-sms",
    headers=headers,
    json={
        "to_phone": "+27123456789",  # Replace with your number
        "message": "Hello from PMS! This is a test SMS.",
        "send_to_user_id": 1
    }
)

if sms_response.status_code == 200:
    result = sms_response.json()['data']
    print(f"✅ SMS sent successfully!")
    print(f"   Message SID: {result['message_sid']}")
    print(f"   Status: {result['status']}")
else:
    print(f"❌ SMS failed: {sms_response.text}")

# Step 4: Send bulk SMS
print("\n📤 Sending bulk SMS...")
bulk_response = requests.post(
    f"{BASE_URL}/api/twilio/send-bulk-sms",
    headers=headers,
    json={
        "message": "Production update: Orders completed successfully!",
        "recipients": [
            {"phone": "+27123456789", "user_id": 1},
            {"phone": "+27987654321", "user_id": 2}
        ]
    }
)

if bulk_response.status_code == 200:
    result = bulk_response.json()['data']
    print(f"✅ Bulk SMS sent!")
    print(f"   Total sent: {result['total_sent']}")
    print(f"   Successful: {result['successful']}")
    print(f"   Failed: {result['failed']}")

# Step 5: Get communication history
print("\n📜 Fetching communication history...")
history_response = requests.get(
    f"{BASE_URL}/api/twilio/communications?user_id=1&limit=10",
    headers=headers
)

if history_response.status_code == 200:
    communications = history_response.json()['data']
    print(f"✅ Retrieved {len(communications)} communications")
    for comm in communications[:3]:
        print(f"   - {comm['message_type']}: {comm['contact_phone']} ({comm['status']})")

print("\n✨ Test completed!")
```

## 🧪 Test with cURL

**Login:**
```bash
curl -X POST https://pms-production-ccc7.up.railway.app/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "operator.mike", "password": "Operator@2026!"}'
```

**Check Twilio Health:**
```bash
curl -X GET https://pms-production-ccc7.up.railway.app/api/twilio/health \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

**Send SMS:**
```bash
curl -X POST https://pms-production-ccc7.up.railway.app/api/twilio/send-sms \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "to_phone": "+27123456789",
    "message": "Test SMS from PMS",
    "send_to_user_id": 1
  }'
```

## ⚠️ Important Notes

1. **Phone Number Format:** Always use E.164 format (`+country_code + number`)
   - South Africa: `+27123456789`
   - USA: `+12025551234`
   - UK: `+441632960000`

2. **Twilio Account:** You must have credits/active subscription to send SMS
   - Free trial credits: $15.50
   - SMS rates: ~$0.0075 per SMS (varies by region)

3. **Rate Limiting:** API implements 100 requests/minute per user

4. **Webhooks:** SMS delivery receipts are automatically logged to the database

5. **Authentication:** All endpoints require valid JWT token

## 📊 Monitoring

### Check Message Status
```bash
curl -X GET "https://pms-production-ccc7.up.railway.app/api/twilio/delivery-status?message_sid=SM1234567890" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### View Twilio Console
- URL: https://www.twilio.com/console
- Account SID: your_account_sid_here
- View message logs, call history, and account metrics

## 🔧 Troubleshooting

**Error: "Twilio credentials not found"**
- Check `.env` file has `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`

**Error: "Invalid phone number"**
- Verify phone is in E.164 format with + prefix

**Error: "Authentication failed"**
- Ensure JWT token is valid
- Re-login if token expired

**SMS not sent**
- Check Twilio account has available credits
- Verify Twilio phone number is active in console
- Check recipient number is valid

## 🎯 Integration Examples

### Auto-send maintenance alerts
```python
# When maintenance needed
twilio_service.send_sms(
    to_phone=supervisor_phone,
    message=f"⚠️ Machine {machine_name} requires urgent maintenance!"
)
```

### Production completion notification
```python
# When order completed
twilio_service.send_sms(
    to_phone=customer_phone,
    message=f"✅ Order {order_id} is ready! Status: {status}"
)
```

### Emergency broadcast
```python
# System failure alert
twilio_service.make_call(
    to_phone=manager_phone,
    message="🚨 EMERGENCY: Critical system failure in Production!"
)
```

## 📞 Support

- Twilio Support: https://support.twilio.com
- API Docs: https://www.twilio.com/docs/sms/api
- Status: https://status.twilio.com

---

**Status:** ✅ ACTIVE
**Last Updated:** January 20, 2026
**Account:** your_account_sid_here
