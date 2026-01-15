#!/usr/bin/env python3
"""
Debug the exact proxy URL being created by ProxyManager
"""

import sys
import os
import requests
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

from modules.proxy_manager import ProxyManager
from config import OXYLABS_PROXY_HOST, OXYLABS_PROXY_PORT, OXYLABS_USERNAME, OXYLABS_PASSWORD

def debug_proxy_manager_url():
    """Debug the exact proxy URL creation process."""
    
    print("🔍 DEBUGGING PROXY MANAGER URL CREATION")
    print("=" * 50)
    
    # Manual proxy URL (like debug_proxy.py uses)
    manual_proxy_url = f"http://{OXYLABS_USERNAME}:{OXYLABS_PASSWORD}@{OXYLABS_PROXY_HOST}:{OXYLABS_PROXY_PORT}"
    manual_safe_url = f"http://{OXYLABS_USERNAME}:***@{OXYLABS_PROXY_HOST}:{OXYLABS_PROXY_PORT}"
    
    print(f"1️⃣ Manual proxy URL: {manual_safe_url}")
    
    # Test manual URL
    manual_proxies = {
        "http": manual_proxy_url,
        "https": manual_proxy_url
    }
    
    try:
        response = requests.get("http://httpbin.org/ip", proxies=manual_proxies, timeout=15)
        response.raise_for_status()
        manual_ip = response.json().get('origin', 'unknown')
        print(f"   ✅ Manual URL result: {manual_ip}")
    except Exception as e:
        print(f"   ❌ Manual URL failed: {e}")
    
    print()
    
    # ProxyManager URL
    print("2️⃣ ProxyManager URL creation:")
    proxy_manager = ProxyManager()
    
    # Simulate the config creation from ProxyManager
    proxy_manager._proxy_config = {
        'ip': OXYLABS_PROXY_HOST,
        'port': OXYLABS_PROXY_PORT,
        'username': OXYLABS_USERNAME,
        'password': OXYLABS_PASSWORD
    }
    
    manager_proxy_url = proxy_manager.get_requests_proxy_url()
    manager_safe_url = manager_proxy_url.replace(OXYLABS_PASSWORD, '***') if manager_proxy_url else 'None'
    
    print(f"   ProxyManager URL: {manager_safe_url}")
    
    # Test ProxyManager URL
    if manager_proxy_url:
        manager_proxies = {
            "http": manager_proxy_url,
            "https": manager_proxy_url
        }
        
        try:
            response = requests.get("http://httpbin.org/ip", proxies=manager_proxies, timeout=15)
            response.raise_for_status()
            manager_ip = response.json().get('origin', 'unknown')
            print(f"   ✅ ProxyManager URL result: {manager_ip}")
        except Exception as e:
            print(f"   ❌ ProxyManager URL failed: {e}")
    else:
        print("   ❌ ProxyManager URL is None!")
    
    print()
    
    # Compare URLs
    print("3️⃣ URL Comparison:")
    print(f"   Manual URL:  {manual_safe_url}")
    print(f"   Manager URL: {manager_safe_url}")
    print(f"   URLs match:  {manual_proxy_url == manager_proxy_url}")
    
    # Test the exact same method ProxyManager uses
    print("\n4️⃣ Simulating ProxyManager test method:")
    proxy_manager._proxy_working = False  # Reset state
    
    try:
        # Use the exact same logic as the updated test_proxy_connection method
        proxies = {
            "http": manager_proxy_url,
            "https": manager_proxy_url
        }
        
        print("   Testing with httpbin.org...")
        test_response = requests.get(
            "http://httpbin.org/ip",
            proxies=proxies,
            timeout=15
        )
        test_response.raise_for_status()
        test_ip = test_response.json().get('origin', 'unknown')
        print(f"   Test IP: {test_ip}")
        
        # Check direct connection
        print("   Checking direct connection...")
        direct_response = requests.get("http://httpbin.org/ip", timeout=10)
        direct_ip = direct_response.json().get('origin', 'unknown')
        print(f"   Direct IP: {direct_ip}")
        
        if test_ip == direct_ip:
            print("   ❌ PROBLEM: Same IP - proxy not working!")
        else:
            print("   ✅ Different IPs - proxy working!")
        
    except Exception as e:
        print(f"   ❌ Simulation failed: {e}")

if __name__ == "__main__":
    debug_proxy_manager_url()