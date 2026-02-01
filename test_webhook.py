#!/usr/bin/env python3
"""Test webhook to n8n"""

import requests

payload = {
    "filename": "20251015-IC-LFC-SUB-206PM-414PM.txt",
    "folder_path": "Legislative Transcription/Interim/LFC/2025-10-15",
}

print(f"Sending test webhook to n8n...")
print(f"Payload: {payload}")

try:
    response = requests.post(
        "http://192.168.4.52:5678/webhook-test/nextcloud-transcription",
        json=payload,
        timeout=10
    )

    print(f"Response status: {response.status_code}")
    print(f"Response body: {response.text}")

    if response.status_code == 200:
        print("✅ Webhook sent successfully!")
    else:
        print(f"⚠️ Webhook returned non-200 status code")

except Exception as e:
    print(f"❌ Error sending webhook: {e}")
