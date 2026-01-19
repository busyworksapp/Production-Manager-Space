# WhatsApp Integration Setup Guide

## Overview
The PMS system now includes WhatsApp Business API integration, allowing users to interact with the system via WhatsApp messages. Users can submit rejects, returns, SOP failures, track items, and pull data reports.

## Features
- 📦 **Submit Reject**: Report defective products
- 🔄 **Customer Return**: Process customer returns
- ⚠️ **SOP Failure**: Report process failures
- 🔍 **Track Item**: Track orders and tickets
- 📊 **Pull Data**: Get reports and statistics

## Prerequisites
1. WhatsApp Business Account
2. Meta Business Account
3. Meta Developer Account

## Setup Steps

### 1. Create WhatsApp Business App on Meta

1. Go to [Meta for Developers](https://developers.facebook.com/)
2. Create a new app or use existing app
3. Add "WhatsApp" product to your app
4. Navigate to WhatsApp > Getting Started

### 2. Get Your Credentials

From the WhatsApp Business API settings, you'll need:

- **Phone Number ID**: Found in "API Setup" section
- **Business Account ID**: Found in the WhatsApp settings
- **Access Token**: Generate a permanent access token (not the temporary one)
- **Verify Token**: Create your own secure random string

### 3. Configure Environment Variables

Update your `.env` file with the credentials:

```env
WHATSAPP_API_URL=https://graph.facebook.com/v18.0
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id_here
WHATSAPP_ACCESS_TOKEN=your_access_token_here
WHATSAPP_VERIFY_TOKEN=your_custom_verify_token_here
WHATSAPP_BUSINESS_ACCOUNT_ID=your_business_account_id_here
```

**Important**: 
- Keep your access token secure and never commit it to version control
- Use a strong, random verify token (e.g., `openssl rand -hex 32`)

### 4. Set Up Webhook

1. In Meta Developer Console, go to WhatsApp > Configuration
2. Click "Edit" on Webhook section
3. Enter your webhook URL: `https://yourdomain.com/api/whatsapp/webhook`
4. Enter your verify token (same as in `.env`)
5. Subscribe to webhook fields:
   - `messages`
   - `message_status`

### 5. Update Database Schema

Run the database migration to add WhatsApp tables:

```bash
python scripts/setup_database.py
```

Or manually run the SQL commands from `database/schema.sql` (lines 804-862):
- `whatsapp_sessions`
- `whatsapp_messages`
- `whatsapp_interactions`

### 6. Link Employee Phone Numbers

Ensure employees have their WhatsApp phone numbers in the system:

```sql
UPDATE employees 
SET phone = '+27821234567' 
WHERE employee_number = 'EMP001';
```

**Phone Number Format**:
- Include country code (e.g., +27 for South Africa)
- The system will match phone numbers even with different formatting

### 7. Test the Integration

#### Test Webhook Verification:
```bash
curl "https://yourdomain.com/api/whatsapp/webhook?hub.mode=subscribe&hub.verify_token=your_verify_token&hub.challenge=test123"
```

#### Test Sending a Message:
```bash
curl -X POST https://yourdomain.com/api/whatsapp/test/send \
  -H "Content-Type: application/json" \
  -d '{"phone": "+27821234567", "message": "Test message"}'
```

#### Test Main Menu:
```bash
curl -X POST https://yourdomain.com/api/whatsapp/test/menu \
  -H "Content-Type: application/json" \
  -d '{"phone": "+27821234567"}'
```

### 8. Start Using WhatsApp

Users can now interact with the system by:
1. Sending "hi", "hello", or "menu" to the WhatsApp Business number
2. Selecting an option from the interactive menu
3. Following the conversation flow

## User Guide

### Initiating Conversation
Send any of these messages to start:
- `hi`
- `hello`
- `menu`
- `start`
- `help`

### Available Actions

#### 1. Submit Reject
Reports defective products. You'll need to provide:
- Order number or product code
- Defect description
- Quantity of defective items

#### 2. Customer Return
Processes customer returns. You'll need:
- Order number
- Customer name
- Reason for return
- Quantity being returned

#### 3. SOP Failure
Reports process failures. You'll provide:
- Machine number or process name
- Description of the failure

#### 4. Track Item
Track orders or tickets by providing:
- Ticket ID or order number

#### 5. Pull Data
Get reports on:
- Rejects summary (last 7 days)
- Returns cost (last 30 days)
- SOP failures (last 7 days)
- Your submitted tickets

## API Endpoints

### Webhook Endpoints
- `GET /api/whatsapp/webhook` - Webhook verification
- `POST /api/whatsapp/webhook` - Receive messages

### Test Endpoints
- `POST /api/whatsapp/test/send` - Send test message
- `POST /api/whatsapp/test/menu` - Send menu to user

### Management Endpoints
- `GET /api/whatsapp/sessions` - View active sessions
- `GET /api/whatsapp/interactions` - View interaction history
- `GET /api/whatsapp/messages/<phone>` - View message history for a phone number

## Database Tables

### whatsapp_sessions
Stores user conversation sessions with state management.

### whatsapp_messages
Logs all incoming and outgoing messages.

### whatsapp_interactions
Tracks user actions (rejects, returns, etc.) for audit purposes.

## Troubleshooting

### Messages Not Received
1. Check webhook is properly configured in Meta Developer Console
2. Verify webhook URL is publicly accessible (not localhost)
3. Check server logs: `backend/logs/app.log`

### Messages Not Sending
1. Verify access token is valid and not expired
2. Check phone number format includes country code
3. Ensure phone number is registered with WhatsApp Business

### Employee Not Recognized
1. Verify employee has phone number in database
2. Check phone number format matches (system normalizes formats)
3. Ensure employee is marked as active

### Session Expired
Sessions expire after 24 hours of inactivity. User just needs to send "menu" to start a new session.

## Security Considerations

1. **Access Token**: Never expose your access token. Rotate regularly.
2. **Verify Token**: Use a strong, random verify token.
3. **Webhook**: Use HTTPS only for webhook URL.
4. **Data Privacy**: All messages and interactions are logged for audit purposes.
5. **Phone Numbers**: Treat phone numbers as PII (Personally Identifiable Information).

## Rate Limits

WhatsApp Business API has rate limits:
- 1,000 messages per day (can be increased with approval)
- Respect 24-hour conversation windows
- Session-based messaging requires user to initiate

## Support

For issues or questions:
1. Check Meta Developer Console for API status
2. Review server logs in `backend/logs/app.log`
3. Check database for session and message logs
4. Test using the test endpoints

## Next Steps

1. Request higher rate limits from Meta if needed
2. Set up monitoring and alerts for failed messages
3. Create templates for common responses
4. Implement rich media support (images, documents)
5. Add multi-language support
