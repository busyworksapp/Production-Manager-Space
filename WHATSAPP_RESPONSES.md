# 🤖 WhatsApp Bot Response Guide

## What Happens When You Say "Hi"

When a user sends **"hi"**, **"hello"**, **"menu"**, **"start"**, or **"help"** to the WhatsApp bot, they get:

### Response: Interactive Main Menu

```
📋 *Main Menu*

Please select an option:

Available Actions
├─ 📦 Submit Reject
│  └─ Report a defective product
├─ 🔄 Customer Return
│  └─ Process a customer return
├─ ⚠️ SOP Failure
│  └─ Report a process failure
├─ 🔍 Track Item
│  └─ Track an order or ticket
└─ 📊 Pull Data
   └─ Get reports and statistics
```

---

## Available Flows

After selecting an option, the bot guides users through a multi-step conversation:

### 1. 📦 Submit Reject Flow
- Asks for: Order Number / Product Code
- Asks for: Quantity Rejected
- Asks for: Rejection Reason
- Submits defect ticket to system

### 2. 🔄 Customer Return Flow
- Asks for: Order Number / Product Code
- Asks for: Quantity Returned
- Asks for: Return Reason
- Submits return ticket to system

### 3. ⚠️ SOP Failure Flow
- Asks for: Department / Process
- Asks for: Issue Description
- Asks for: Severity Level
- Submits SOP failure ticket

### 4. 🔍 Track Item Flow
- Asks for: Ticket Number or Order Number
- Retrieves status and details
- Shows current status

### 5. 📊 Pull Data Flow
- Asks for: Report Type
- Provides statistics and summaries
- Returns requested data

---

## Current Responses Configured

### Greeting Messages
When user sends: `hi`, `hello`, `menu`, `start`, `help`
**Response:** Shows interactive menu (buttons above)

### Flow Responses
Each flow sends prompts asking for specific information step-by-step.

### Error Handling
If error occurs:
```
❌ An error occurred. Please try again or type 'menu' to start over.
```

---

## How to Test

1. **Open Twilio Console** → WhatsApp Sandbox
2. **Send message:** `Hi`
3. **Expected response:** Main menu appears with 5 buttons
4. **Click a button** (e.g., "Submit Reject")
5. **Bot will ask:** "Please provide Order Number..."

---

## How to Customize Responses

If you want to change responses (e.g., "Say something different"), edit:

**File:** `backend/utils/whatsapp_flow_handler.py`

### Change the Main Menu (Lines 10-21)
```python
MAIN_MENU = {
    "text": "📋 *Main Menu*\n\nPlease select an option:",
    "sections": [{
        "title": "Available Actions",
        "rows": [
            {"id": "reject", "title": "📦 Submit Reject", "description": "Report a defective product"},
            # Add or modify buttons here
        ]
    }]
}
```

### Change Greeting Responses (Line 48)
```python
if message_lower in ['hi', 'hello', 'menu', 'start', 'help']:
    # Add more trigger words here
    return self._show_main_menu(phone, session)
```

### Add Custom Responses (Add before Line 48)
```python
# Custom greeting
if message_lower == 'thanks':
    whatsapp_service.send_text_message(phone, "You're welcome! 😊 Type 'menu' to continue.")
    return {"status": "ok"}

# Custom help text
if message_lower == 'what can you do':
    whatsapp_service.send_text_message(phone, "I can help you with: rejects, returns, SOP failures, tracking, and reports. Type 'menu' to get started!")
    return {"status": "ok"}
```

---

## Current Workflow Example

```
User: "Hi"
Bot: Shows interactive menu

User: Clicks "Submit Reject"
Bot: "📦 *Submit Reject*
      Please provide the following information:
      1️⃣ Order Number or Product Code"

User: "ORD-12345"
Bot: "Got it! How many items were rejected?"

User: "5"
Bot: "What's the reason for rejection?"

User: "Defective components"
Bot: "✅ Reject ticket submitted as ticket #REJ-2026-001
      Your request has been recorded."

User: Type 'menu' to start over
Bot: Shows main menu again
```

---

## To Send Custom Responses

Edit the flow handlers in `whatsapp_flow_handler.py` to customize messages at each step.

For example, to add a greeting when user first arrives:
```python
def _show_main_menu(self, phone: str, session: Dict) -> Dict[str, Any]:
    # Add custom welcome
    whatsapp_service.send_text_message(
        phone, 
        "👋 Welcome to Production Manager Bot!\n\nI'm here to help you submit tickets and track orders."
    )
    
    # Then show menu
    whatsapp_service.send_interactive_list(...)
```

---

## Quick Command Reference

| User Says | Bot Does |
|-----------|----------|
| `hi` | Show Main Menu |
| `hello` | Show Main Menu |
| `menu` | Show Main Menu |
| `start` | Show Main Menu |
| `help` | Show Main Menu |
| Clicks button | Start selected flow |
| Answers prompts | Process through flow steps |
| `menu` (during flow) | Return to Main Menu |

---

**Your bot is ready!** When users text, they get an interactive experience to submit tickets and track orders. 🎉
