#!/usr/bin/env python3
"""Test WhatsApp message sending"""
from backend.utils.whatsapp_service import whatsapp_service

print("Testing WhatsApp message via Twilio...")
result = whatsapp_service.send_text_message(
    'whatsapp:+27788494933',
    'Test: Type "hi" to see the main menu!'
)
print(f"Result: {result}")
