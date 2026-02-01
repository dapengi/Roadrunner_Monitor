#!/usr/bin/env python3
"""Check what title elements exist on the page"""

from dotenv import load_dotenv
load_dotenv()

from modules.caption_processor import CaptionProcessor
from modules.proxy_manager import ProxyManager
from bs4 import BeautifulSoup

# Initialize proxy
proxy_manager = ProxyManager()
if not proxy_manager.test_proxy_connection():
    print("Failed to connect to proxy")
    exit(1)

caption_processor = CaptionProcessor(proxy_manager=proxy_manager)
entry_url = "https://sg001-harmony.sliq.net/00293/Harmony/en/PowerBrowser/PowerBrowserV2/20251018/-1/77762"

html_content = caption_processor.fetch_page(entry_url)
soup = BeautifulSoup(html_content, 'html.parser')

# Try different ways to find the title
print("Looking for title elements...")

title = soup.find('title')
if title:
    print(f"<title>: {title.get_text(strip=True)}")

h1 = soup.find('h1')
if h1:
    print(f"<h1>: {h1.get_text(strip=True)}")

h2 = soup.find('h2')
if h2:
    print(f"<h2>: {h2.get_text(strip=True)}")

meeting_title = soup.find('span', class_='meetingViewTitle')
if meeting_title:
    print(f"span.meetingViewTitle: {meeting_title.get_text(strip=True)}")

# Print all spans with class containing 'title' or 'meeting'
for span in soup.find_all('span'):
    class_names = span.get('class', [])
    for cls in class_names:
        if 'title' in cls.lower() or 'meeting' in cls.lower():
            print(f"Found span.{cls}: {span.get_text(strip=True)[:100]}")
