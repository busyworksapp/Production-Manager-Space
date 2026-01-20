# Twilio Integration Setup Guide

## ✅ Current Configuration (ACTIVE)

### Your Twilio Credentials
```
TWILIO_ACCOUNT_SID=your_account_sid_here
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_FROM_PHONE=+14155238886
TWILIO_WEBHOOK_URL=https://pms-production-ccc7.up.railway.app/api/whatsapp/twilio-webhook
```

### Webhook Endpoint
The webhook has been configured to receive SMS and call status updates at:
```
https://pms-production-ccc7.up.railway.app/api/whatsapp/twilio-webhook
```

---

This guide will help you set up Twilio integration with the Production Manager Space application for SMS and voice capabilities.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Twilio Account Setup](#twilio-account-setup)
3. [Configuration](#configuration)
4. [API Endpoints](#api-endpoints)
5. [Usage Examples](#usage-examples)
6. [Webhooks](#webhooks)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

- Active Twilio account (free trial available at https://www.twilio.com/try-twilio)
- Python 3.9+
- Twilio Python SDK (already installed: `twilio` package)

---

## Twilio Account Setup

### 1. Create a Twilio Account

1. Go to [https://www.twilio.com/try-twilio](https://www.twilio.com/try-twilio)
2. Sign up for a free trial account
3. Verify your email and phone number
4. Complete the account setup

### 2. Get Your Credentials

1. Log in to your Twilio Console: https://www.twilio.com/console
2. Find your **Account SID** and **Auth Token** on the main dashboard
3. Keep these credentials safe (use .env file, not hardcoded)

### 3. Get a Twilio Phone Number

1. In the Twilio Console, go to **Phone Numbers** → **Manage** → **Active Numbers**
2. Click "Get your first Twilio phone number"
3. Accept the suggested number (or choose your own)
4. Confirm and save the number (format: +1XXXXXXXXXX for US numbers)

### 4. Enable SMS and Voice Capabilities

1. In the Console, go to **Phone Numbers** → **Manage** → **Active Numbers**
2. Click on your phone number
3. Ensure both SMS and Voice are enabled
4. For SMS: Set the webhook (can be configured later)
5. For Voice: Set the webhook for incoming calls (can be configured later)

---

## Configuration

### 1. Update Your .env File

Add the following environment variables:

```env
# Twilio Configuration for SMS and Voice
TWILIO_ACCOUNT_SID=your_twilio_account_sid_here
TWILIO_AUTH_TOKEN=your_twilio_auth_token_here
TWILIO_FROM_PHONE=+1XXXXXXXXXX
```

**Example:**
```env
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_FROM_PHONE=+12125551234
```

### 2. Verify Configuration

Check that Twilio is properly configured by calling the health endpoint:

```bash
curl -X GET http://localhost:5000/api/twilio/health \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

You should see: `{"status": "connected", "message": "Twilio service is active"}`

---

## API Endpoints

### 1. Check Twilio Service Health

**Endpoint:** `GET /api/twilio/health`

**Authentication:** Required

**Response:**
```json
{
  "status": "connected",
  "message": "Twilio service is active"
}
```

---

### 2. Send SMS

**Endpoint:** `POST /api/twilio/send-sms`

**Authentication:** Required

**Request Body:**
```json
{
  "to_phone": "+27123456789",
  "message": "Hello! This is a test message from Production Manager Space.",
  "send_to_user_id": 3
}
```

**Response:**
```json
{
  "success": true,
  "message_sid": "SM1234567890abcdef",
  "status": "queued",
  "to": "+27123456789"
}
```

---

### 3. Send Bulk SMS

**Endpoint:** `POST /api/twilio/send-bulk-sms`

**Authentication:** Required

**Request Body:**
```json
{
  "recipients": [
    {"phone": "+27123456789", "user_id": 3},
    {"phone": "+27987654321", "user_id": 4}
  ],
  "message": "Urgent: Please check the production schedule."
}
```

**Response:**
```json
{
  "total": 2,
  "successful": 2,
  "failed": 0,
  "details": [
    {
      "phone": "+27123456789",
      "success": true,
      "message_sid": "SM1234567890abcdef",
      "status": "queued"
    },
    {
      "phone": "+27987654321",
      "success": true,
      "message_sid": "SM0987654321fedcba",
      "status": "queued"
    }
  ]
}
```

---

### 4. Send SMS to Department

**Endpoint:** `POST /api/twilio/send-to-department`

**Authentication:** Required

**Request Body:**
```json
{
  "department_id": 1,
  "message": "Department meeting at 2 PM today. Please confirm attendance.",
  "exclude_user_ids": [3]
}
```

**Response:**
```json
{
  "total": 4,
  "successful": 4,
  "failed": 0,
  "details": [...]
}
```

---

### 5. Make Outbound Call

**Endpoint:** `POST /api/twilio/make-call`

**Authentication:** Required

**Request Body:**
```json
{
  "to_phone": "+27123456789",
  "twiml": "<Response><Say voice=\"woman\">Hello, this is a production alert.</Say><Hangup/></Response>",
  "user_id": 3
}
```

**Response:**
```json
{
  "success": true,
  "call_sid": "CA1234567890abcdef",
  "status": "queued",
  "to": "+27123456789"
}
```

---

### 6. Get Message Status

**Endpoint:** `GET /api/twilio/message-status/<message_sid>`

**Authentication:** Required

**Response:**
```json
{
  "success": true,
  "sid": "SM1234567890abcdef",
  "status": "delivered",
  "to": "+27123456789",
  "from": "+12125551234",
  "date_sent": "2026-01-20T10:30:00Z",
  "price": "-0.0075"
}
```

---

### 7. Get Call Status

**Endpoint:** `GET /api/twilio/call-status/<call_sid>`

**Authentication:** Required

**Response:**
```json
{
  "success": true,
  "sid": "CA1234567890abcdef",
  "status": "completed",
  "to": "+27123456789",
  "from": "+12125551234",
  "duration": 45,
  "start_time": "2026-01-20T10:30:00Z",
  "end_time": "2026-01-20T10:31:00Z"
}
```

---

## Usage Examples

### Example 1: Send Alert SMS to Operators

```bash
curl -X POST http://localhost:5000/api/twilio/send-sms \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "to_phone": "+27123456789",
    "message": "Machine MACH001 requires immediate maintenance. Please halt operations.",
    "send_to_user_id": 3
  }'
```

### Example 2: Send Department-Wide Notification

```bash
curl -X POST http://localhost:5000/api/twilio/send-to-department \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "department_id": 1,
    "message": "Production target for today: 500 units. Current progress: 350 units. Push to reach target!"
  }'
```

### Example 3: Make Automated Call with TwiML

```bash
curl -X POST http://localhost:5000/api/twilio/make-call \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "to_phone": "+27123456789",
    "twiml": "<Response><Say voice=\"woman\">Production alert: Order PO-2026-001 is delayed. Please call back for details.</Say><Gather numDigits=\"1\"><Say>Press 1 to acknowledge.</Say></Gather></Response>",
    "user_id": 3
  }'
```

---

## Webhooks

### SMS Webhook Setup

1. Go to Phone Numbers → Manage Active Numbers
2. Click your phone number
3. Under "Messaging", set:
   - **A message comes in:** `http://your-app.com/api/twilio/webhook/sms` (POST)

4. Verify the webhook is working by sending an SMS to your Twilio number

### Call Webhook Setup

1. Go to Phone Numbers → Manage Active Numbers
2. Click your phone number
3. Under "Voice & Fax", set:
   - **A call comes in:** `http://your-app.com/api/twilio/webhook/call` (POST)

---

## Troubleshooting

### Issue: "Twilio service not configured"

**Solution:** Ensure all three environment variables are set:
- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_FROM_PHONE`

Check your .env file and restart the application.

### Issue: "Invalid phone number"

**Solution:** Phone numbers must be in E.164 format: `+[country_code][number]`
- ✓ Correct: `+27123456789`
- ✗ Wrong: `0123456789`, `123456789`

### Issue: SMS not delivering

**Solution:**
1. Check message status using the status endpoint
2. Verify recipient phone number is correct
3. For free trial accounts, recipient must be verified
4. Check Twilio account balance/credits

### Issue: Authentication failure

**Solution:**
1. Ensure you're including the JWT token in the header
2. Verify the token is still valid
3. Check that you're passing: `Authorization: Bearer <token>`

### Issue: Webhook not being called

**Solution:**
1. Verify your app is publicly accessible (not localhost)
2. Check firewall/security group settings
3. Review Twilio logs: Console → Logs → Debugger
4. Ensure webhook URL is exactly correct

---

## Database Schema

The Twilio service stores communication logs in the `communication_log` table:

```sql
CREATE TABLE communication_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    type VARCHAR(50),  -- 'sms' or 'call'
    to_phone VARCHAR(50),
    message TEXT,
    external_id VARCHAR(100),  -- Twilio SID
    status VARCHAR(50),
    error TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

---

## Best Practices

1. **Rate Limiting:** Twilio has rate limits. For bulk operations, implement delays between messages.
2. **Cost Management:** SMS costs money. Use bulk sending to reduce overhead.
3. **Security:** Never expose your auth token in frontend code or public repositories.
4. **Opt-in:** Always ensure recipients have opted in to receive SMS/calls.
5. **Testing:** Use Twilio's free trial credits for testing before production deployment.
6. **Logging:** Always enable logging and monitoring for communication issues.

---

## Next Steps

1. Test each API endpoint in Postman or similar tool
2. Configure webhooks for incoming messages/calls
3. Integrate SMS notifications into your business workflows
4. Set up monitoring and alerting for failed messages
5. Consider SMS as part of your disaster recovery plan

---

For more information:
- Twilio Documentation: https://www.twilio.com/docs
- Twilio Python SDK: https://github.com/twilio/twilio-python
- TwiML Reference: https://www.twilio.com/docs/voice/twiml
