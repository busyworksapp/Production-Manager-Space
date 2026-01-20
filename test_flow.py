#!/usr/bin/env python3
"""Test the complete WhatsApp flow - webhook to response"""
from backend.api.whatsapp import process_incoming_message

print("\n" + "="*60)
print("Testing complete WhatsApp flow: Message reception -> Response")
print("="*60)

# Simulate the message that comes from Twilio
message_data = {
    'from': 'whatsapp:+27788494933',
    'body': 'hi',
    'message_type': 'text',
    'MessageSid': 'SMtest123'
}

print("\n1. Processing incoming message:")
print(f"   From: {message_data['from']}")
print(f"   Body: {message_data['body']}")
print(f"   Type: {message_data['message_type']}")

try:
    process_incoming_message(message_data)
    print("\nOK - Message processed successfully!")
    print("   Response should have been sent via Twilio WhatsApp")
    print("\nCheck your WhatsApp in the next few seconds...")
except Exception as e:
    print(f"\nERROR processing message: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
