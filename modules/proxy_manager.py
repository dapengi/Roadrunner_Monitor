# modules/proxy_manager.py

import requests
import datetime
import logging
import os
import time
import random
import string

from config import (
    OXYLABS_PROXY_HOST, OXYLABS_PROXY_PORT, OXYLABS_USERNAME, OXYLABS_PASSWORD,
    OXYLABS_LOCATION_URL, LAST_PROXY_UPDATE_FILE, PROXY_UPDATE_INTERVAL_HOURS
)

logger = logging.getLogger(__name__)

class ProxyManager:
    """
    Manages Oxylabs proxy configuration, testing, and status.
    """
    def __init__(self):
        self._proxy_config = None
        self._proxy_working = False
        self._last_update_check = None
        self._load_last_update_check()

    @property
    def proxy_config(self):
        return self._proxy_config

    @property
    def proxy_working(self):
        return self._proxy_working

    def _load_last_update_check(self):
        """Loads the timestamp of the last proxy update check."""
        if os.path.exists(LAST_PROXY_UPDATE_FILE):
            try:
                with open(LAST_PROXY_UPDATE_FILE, 'r') as f:
                    self._last_update_check = datetime.datetime.fromisoformat(f.read().strip())
            except (ValueError, FileNotFoundError):
                logger.warning(f"Could not read {LAST_PROXY_UPDATE_FILE}, assuming no previous check.")
                self._last_update_check = None
        else:
            self._last_update_check = None

    def _save_last_update_check(self):
        """Saves the current timestamp as the last proxy update check."""
        self._last_update_check = datetime.datetime.now()
        with open(LAST_PROXY_UPDATE_FILE, 'w') as f:
            f.write(self._last_update_check.isoformat())

    def should_update_proxy_list(self):
        """Checks if the proxy status should be re-tested based on interval."""
        if not self._last_update_check:
            return True
        
        now = datetime.datetime.now()
        hours_since_update = (now - self._last_update_check).total_seconds() / 3600
        return hours_since_update >= PROXY_UPDATE_INTERVAL_HOURS

    def test_proxy_connection(self, max_retries=3, force_new_ip=True):
        """
        Tests if Oxylabs proxy is working and gets IP location info.
        Tries multiple times to get different IP assignments from Oxylabs.
        Updates internal _proxy_config and _proxy_working status.

        Args:
            max_retries (int): Number of different IPs to try before giving up
            force_new_ip (bool): If True, forces Oxylabs to assign a new IP using random session IDs
        """
        logger.info(f"Testing Oxylabs proxy connection (will try {max_retries} different IPs)...")

        successful_ips = []
        failed_ips = []

        for attempt in range(max_retries):
            logger.info(f"Proxy attempt {attempt + 1}/{max_retries}")

            try:
                # Generate random session ID to force Oxylabs to assign a different IP
                # This is especially useful when IPs get blacklisted
                if force_new_ip:
                    session_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
                    modified_username = f"{OXYLABS_USERNAME}-session-{session_id}"
                    logger.info(f"Using randomized session ID to force new IP assignment: session-{session_id}")
                else:
                    modified_username = OXYLABS_USERNAME

                # Force a fresh connection by recreating config
                self._proxy_config = {
                    'ip': OXYLABS_PROXY_HOST,
                    'port': OXYLABS_PROXY_PORT,
                    'username': modified_username,
                    'password': OXYLABS_PASSWORD
                }
                
                # Create proxy URL directly for testing (don't use get_requests_proxy_url which checks _proxy_working)
                if self._proxy_config['username'] and self._proxy_config['password']:
                    proxy_url = f"http://{self._proxy_config['username']}:{self._proxy_config['password']}@{self._proxy_config['ip']}:{self._proxy_config['port']}"
                else:
                    proxy_url = f"http://{self._proxy_config['ip']}:{self._proxy_config['port']}"
                
                proxies = {
                    "http": proxy_url,
                    "https": proxy_url
                }
                
                # Test with IP check service first (faster)
                test_response = requests.get(
                    "https://api.ipify.org?format=json",
                    proxies=proxies,
                    timeout=15
                )
                test_response.raise_for_status()
                test_ip = test_response.json().get('ip', 'unknown')
                
                # CRITICAL: Check if we got our real IP instead of proxy IP
                # Get direct IP to compare
                try:
                    direct_response = requests.get("https://api.ipify.org?format=json", timeout=10)
                    direct_ip = direct_response.json().get('ip', 'unknown')
                    
                    if test_ip == direct_ip:
                        logger.error(f"❌ Proxy test failed - got direct IP ({test_ip}) instead of proxy IP!")
                        failed_ips.append(test_ip)
                        raise Exception(f"Proxy not working - returned direct IP {test_ip}")
                    
                except Exception as direct_check_error:
                    logger.error(f"❌ Could not verify direct IP for comparison: {direct_check_error}")
                    raise Exception(f"Fail-safe: Cannot verify proxy is working - direct IP check failed: {direct_check_error}")
                
                # Check if we got a different IP than previous attempts
                if test_ip in failed_ips:
                    logger.warning(f"Got same failed IP ({test_ip}) on attempt {attempt + 1}, skipping")
                    continue
                
                # Verify with second IP service for double-checking
                verify_response = requests.get(
                    "https://ifconfig.me/ip",
                    proxies=proxies,
                    timeout=15,
                    headers={'Accept': 'text/plain'}
                )
                verify_response.raise_for_status()
                verify_ip = verify_response.text.strip()
                
                # Both services should show proxy IPs (they might be different due to rotation)
                logger.info(f"Primary IP service: {test_ip}")
                logger.info(f"Verify IP service: {verify_ip}")
                
                # Now test with Oxylabs location service for full validation
                response = requests.get(
                    OXYLABS_LOCATION_URL,
                    proxies=proxies,
                    timeout=30
                )
                response.raise_for_status()
                
                location_data = response.json()
                
                proxy_ip = location_data.get('ip', test_ip)
                country = 'unknown'
                city = 'unknown'
                
                providers = location_data.get('providers', {})
                for provider_name, provider_data in providers.items():
                    if provider_data.get('country') and country == 'unknown':
                        country = provider_data.get('country', 'unknown')
                    if provider_data.get('city') and city == 'unknown':
                        city = provider_data.get('city', 'unknown')
                
                logger.info(f"✅ Proxy working on attempt {attempt + 1} - IP: {proxy_ip}, Location: {city}, {country}")
                logger.info(f"All IP checks passed - using proxy successfully")
                successful_ips.append(proxy_ip)
                self._proxy_working = True
                self._save_last_update_check()
                return True
                
            except Exception as e:
                logger.warning(f"❌ Proxy attempt {attempt + 1} failed: {e}")
                if 'test_ip' in locals():
                    failed_ips.append(test_ip)
                
                # Add delay between attempts to allow Oxylabs to assign different IP
                if attempt < max_retries - 1:
                    logger.info("Waiting 5 seconds before next attempt...")
                    time.sleep(5)
        
        # All attempts failed
        logger.error(f"All {max_retries} proxy attempts failed")
        if failed_ips:
            logger.error(f"Failed IPs: {', '.join(failed_ips)}")
        
        self._proxy_working = False
        self._proxy_config = None
        return False

    def test_proxy_connectivity(self):
        """Tests if Oxylabs proxy is working correctly by making a request to api.ipify.org."""
        logger.info("Testing Oxylabs proxy connectivity..." )
        test_url = "https://api.ipify.org?format=json"

        if self._proxy_working and self._proxy_config:
            proxy_dict = self.get_requests_proxy_dict( )
            try:
                response = requests.get(test_url, proxies=proxy_dict, timeout=10)
                response.raise_for_status()
                ip_data = response.json()
                logger.info(f"Oxylabs proxy connected successfully (IP: {ip_data.get('ip', 'unknown')})")
            except Exception as e:
                logger.warning(f"Oxylabs proxy connectivity test failed: {e}")
        else:
            logger.info("Proxy is not marked as working, skipping connectivity test.")

        # Test direct connection as well for comparison
        try:
            response = requests.get(test_url, timeout=10)
            response.raise_for_status()
            ip_data = response.json()
            logger.info(f"Direct connection - Working (IP: {ip_data.get('ip', 'unknown')})")
        except Exception as e:
            logger.warning(f"Direct connection - Failed: {e}")

    def get_requests_proxy_dict(self):
        """Returns proxy configuration in requests-compatible dict format."""
        if not self._proxy_working or not self._proxy_config:
            return None
        
        proxy_url = self.get_requests_proxy_url()
        return {
            'http': proxy_url,
            'https': proxy_url
        }

    def get_requests_proxy_url(self ):
        """Returns proxy URL in http://user:pass@host:port format for requests."""
        if not self._proxy_working or not self._proxy_config:
            return None
        
        if self._proxy_config['username'] and self._proxy_config['password']:
            return f"http://{self._proxy_config['username']}:{self._proxy_config['password']}@{self._proxy_config['ip']}:{self._proxy_config['port']}"
        else:
            return f"http://{self._proxy_config['ip']}:{self._proxy_config['port']}"

    def get_yt_dlp_proxy_url(self ):
        """Returns proxy URL in http://user:pass@host:port format for yt-dlp."""
        return self.get_requests_proxy_url( ) # Same format for yt-dlp


