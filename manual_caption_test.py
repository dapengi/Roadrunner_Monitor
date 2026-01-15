#!/usr/bin/env python3
"""Manually download captions and trigger webhook for testing"""

import datetime
import re
from dotenv import load_dotenv

load_dotenv()

from config import *
from modules.caption_processor import CaptionProcessor
from modules.nextcloud import save_transcript_to_nextcloud
from modules.proxy_manager import ProxyManager

# Initialize proxy
print("Initializing proxy...")
proxy_manager = ProxyManager()
if not proxy_manager.test_proxy_connection():
    print("Failed to connect to proxy")
    exit(1)

# Initialize caption processor
caption_processor = CaptionProcessor(proxy_manager=proxy_manager)

# Download captions
entry_url = "https://sg001-harmony.sliq.net/00293/Harmony/en/PowerBrowser/PowerBrowserV2/20251018/-1/77762"
print(f"Downloading captions from: {entry_url}")

caption_content = caption_processor.download_captions(entry_url)

if not caption_content:
    print("Failed to download captions")
    exit(1)

print(f"✅ Downloaded {len(caption_content)} characters of caption text")

# Fetch the actual title from the page
from bs4 import BeautifulSoup
html_content = caption_processor.fetch_page(entry_url)
soup = BeautifulSoup(html_content, 'html.parser')

# Try to find the meeting title
title_elem = soup.find('span', class_='headerTitle')
if title_elem:
    test_title = title_elem.get_text(strip=True)
    print(f"Found title: {test_title}")
else:
    test_title = "Unknown Committee Meeting"
    print("Could not find title, using default")

# Save to Nextcloud (this will trigger the webhook)
print("Uploading to Nextcloud and triggering webhook...")
nextcloud_result = save_transcript_to_nextcloud(
    caption_content, test_title, entry_url, save_as_txt=True
)

if nextcloud_result:
    print("✅ Success!")
    print(f"   Filename: {nextcloud_result.get('filename')}")
    print(f"   Folder: {nextcloud_result.get('folder_path')}")
    print(f"   Share link: {nextcloud_result.get('share_link', 'None')}")
    print("   Webhook should have been sent to n8n!")
else:
    print("❌ Failed to save to Nextcloud")
