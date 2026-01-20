# 🚀 Twilio WhatsApp Configuration for Railway

## Your Twilio Setup is Working! ✅

You have WhatsApp messages flowing through your Twilio account. Now we need to configure the environment variables in Railway.

## What You Need from Twilio Console

1. **Go to:** [Twilio Console](https://console.twilio.com)
2. **Log in** with your Twilio account
3. **Find these values:**

### From Account Info
- **Account SID:** Look for "Account SID" at top of dashboard
- **Auth Token:** Look for "Auth Token" at top of dashboard
- **Phone Number:** Your Twilio phone number (e.g., `+14155238886`)

### From WhatsApp Settings (Optional but Recommended)
- **WhatsApp Phone Number ID:** If using Business API
- **Webhook Token:** For validating incoming messages

## Configuration in Railway Dashboard

### Step 1: Add Twilio Variables

Go to Railway Dashboard → Your App → Variables tab

Add these variables:

| Variable | Value | Example |
|----------|-------|---------|
| `TWILIO_ACCOUNT_SID` | Your Account SID | `ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` |
| `TWILIO_AUTH_TOKEN` | Your Auth Token | `xxxxxxxxxxxxxxxxxxxxxxxxxxxx` |
| `TWILIO_PHONE_NUMBER` | Your Twilio Number | `+14155238886` |

### Step 2: (Optional) WhatsApp-Specific Variables

If using WhatsApp Business API:

| Variable | Value |
|----------|-------|
| `TWILIO_WHATSAPP_NUMBER` | Your WhatsApp sandbox number |
| `WHATSAPP_WEBHOOK_TOKEN` | Your webhook validation token |

### Step 3: Save and Deploy

1. After entering all variables, click **Save** or **Update**
2. Railway automatically redeploys
3. Check **Logs** tab for:
   ```
   Twilio client initialized successfully
   ```

## How to Get Your Twilio Credentials

### Account SID & Auth Token

1. Go to [Twilio Console Home](https://console.twilio.com)
2. You'll see at the very top:
   ```
   Account SID: ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   Auth Token: [Show]  xxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```
3. Click **[Show]** to reveal Auth Token
4. Copy both values

### Phone Number

1. Go to [Twilio Phone Numbers](https://console.twilio.com/phone-numbers/incoming)
2. Find your active phone number
3. It will be in format: `+1XXXXXXXXXX`
4. Copy it

### WhatsApp Sandbox

1. Go to [Twilio Messaging → Try it out → Send WhatsApp Message](https://console.twilio.com/messaging/whatsapp/learn)
2. Or go to [WhatsApp Sandbox](https://console.twilio.com/messaging/whatsapp/sandbox)
3. You'll see your sandbox phone number
4. Messages starting with "Green Tea Bag:" come from this

## Testing Twilio Integration

Once deployed to Railway with Twilio variables:

### Test 1: Send SMS (if enabled)
```python
# From your app
POST /api/notifications/send-sms
{
  "phone": "+27123456789",
  "message": "Hello from Production Manager Space!"
}
```

### Test 2: Send WhatsApp Message
```python
# From your app
POST /api/whatsapp/send
{
  "phone": "+27123456789",
  "message": "Hello from Production Manager Space!"
}
```

### Test 3: Check Logs
Look for these success messages:
```
Twilio client initialized successfully
WhatsApp message sent to +27...
SMS sent to +27...
```

## Current Twilio Features in Your App

✅ **SMS Notifications** - Send SMS to employees
✅ **WhatsApp Messages** - Send WhatsApp via Twilio
✅ **Incoming WhatsApp** - Receive WhatsApp messages in your app
✅ **Message Logging** - All messages logged in database
✅ **Scheduled Messages** - Send messages at specific times
✅ **User Notifications** - Integrate with your notification system

## Common Issues

### Issue: "Twilio credentials not fully configured"
**Solution:** Check that all three variables (`TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`) are set

### Issue: "Unauthorized" error
**Solution:** Verify Account SID and Auth Token are correct (copy from Twilio console again)

### Issue: Messages not sending
**Solution:** 
1. Check phone number format: must include country code (e.g., `+27...`)
2. Verify recipient phone number is correct
3. Check Twilio account has available credit/balance

## What Happens After Setup

1. **Employees can send WhatsApp messages** to the sandbox number
2. **Your app receives and processes** incoming messages
3. **Your app can send messages** to employees via SMS/WhatsApp
4. **All communications logged** in database
5. **Notifications created** for important messages

## Next Steps

1. ✅ Add Twilio variables to Railway
2. ⏳ Wait for auto-redeploy (2-5 minutes)
3. ✅ Check logs for "Twilio client initialized"
4. ✅ Test WhatsApp from your sandbox
5. ✅ Monitor message flows in app

---

**Your WhatsApp sandbox is already receiving messages!** Now just configure the production environment variables and everything will work seamlessly in Railway.
