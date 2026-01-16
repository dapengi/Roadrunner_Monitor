# modules/web_scraper.py

import requests
from bs4 import BeautifulSoup
import datetime
import random
import time
import logging

from config import URL
# Removed: from config import proxy_config, proxy_working # No longer needed
# Removed: from modules.utils import get_proxy_dict # No longer needed

logger = logging.getLogger(__name__)


# Removed: get_proxy_status and get_proxy_dict functions


def make_request_with_proxy(url, headers=None, max_retries=3, proxy_manager=None):
    """Make a request using Oxylabs proxy with retry logic. Will NOT fallback to direct connection."""
    if headers is None:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/91.0.4472.124 Safari/537.36'
        }

    # Check if proxy is available before attempting any requests
    if not (proxy_manager and proxy_manager.proxy_working):
        logger.error("Proxy is not available or not working. Cannot proceed without proxy to protect home IP.")
        raise Exception("Proxy not available - refusing to make direct connection to protect home IP")

    for attempt in range(max_retries):
        try:
            proxies = proxy_manager.get_requests_proxy_dict()
            logger.info(f"Attempt {attempt + 1}: Using Oxylabs proxy {proxy_manager.proxy_config['ip']}:{proxy_manager.proxy_config['port']}")
            
            response = requests.get(url, headers=headers, proxies=proxies, timeout=30)
            
            response.raise_for_status()
            logger.info(f"Request successful on attempt {attempt + 1}")
            return response
            
        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            logger.warning(f"Request failed on attempt {attempt + 1}: {e}")

            # Check if it's a proxy-related error
            if proxy_manager and proxy_manager.proxy_working and ("503" in error_msg or "Tunnel connection failed" in error_msg or "ProxyError" in error_msg):
                if attempt < max_retries - 1:
                    logger.info("Proxy may be blocked/blacklisted. Refreshing proxy to get new IP from Oxylabs...")
                    # Force proxy refresh to get a new IP from Oxylabs
                    if proxy_manager.test_proxy_connection(max_retries=3):
                        logger.info("✅ Successfully obtained new proxy IP from Oxylabs")
                    else:
                        logger.warning("⚠️ Failed to get new proxy IP, will retry with current proxy")

            if attempt < max_retries - 1:
                wait_time = (2 ** attempt) + random.uniform(1, 3)
                logger.info(f"Waiting {wait_time:.1f} seconds before retry...")
                time.sleep(wait_time)
            else:
                logger.error(f"All {max_retries} attempts failed for URL: {url}")
                raise
    
def get_current_entries(proxy_manager=None):
    """Fetch and parse the current entries from the website using proxy."""
    try:
        # Use proxy-enabled request
        response = make_request_with_proxy(URL, proxy_manager=proxy_manager)
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        entries = []
        
        for entry_element in soup.select('table'):
            entry_text = entry_element.get_text().strip()
            
            parent_a = entry_element.find_parent('a')
            entry_link = None
            if parent_a and 'href' in parent_a.attrs:
                entry_link = parent_a['href']
                if entry_link and not entry_link.startswith('http' ):
                    base_url = '/'.join(URL.split('/')[:3])
                    entry_link = f"{base_url}{entry_link if entry_link.startswith('/') else '/' + entry_link}"
            
            if entry_text:
                entries.append({
                    'text': entry_text,
                    'link': entry_link,
                    'timestamp': datetime.datetime.now().isoformat()
                })
        
        return entries
    
    except Exception as e:
        logger.error(f"Error fetching entries: {e}")
        return []


