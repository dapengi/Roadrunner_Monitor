#!/usr/bin/env python3
"""
Check what IP address Oxylabs is assigning to your proxy connection
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

def check_assigned_ip():
    """Check what IP Oxylabs is actually assigning."""
    
    print("🔍 Checking Oxylabs Assigned IP Address")
    print("=" * 45)
    
    # Show configuration
    print(f"Proxy endpoint: {OXYLABS_PROXY_HOST}:{OXYLABS_PROXY_PORT}")
    print(f"Username: {OXYLABS_USERNAME}")
    print()
    
    # Create proxy configuration
    proxy_url = f"http://{OXYLABS_USERNAME}:{OXYLABS_PASSWORD}@{OXYLABS_PROXY_HOST}:{OXYLABS_PROXY_PORT}"
    proxies = {
        "http": proxy_url,
        "https": proxy_url
    }
    
    # Test with multiple IP checking services
    test_urls = [
        ("httpbin.org", "http://httpbin.org/ip"),
        ("Oxylabs Location", "https://ip.oxylabs.io/location"),
        ("IPify", "https://api.ipify.org?format=json")
    ]
    
    for service_name, url in test_urls:
        print(f"🌐 Testing with {service_name}...")
        try:
            response = requests.get(url, proxies=proxies, timeout=15)
            response.raise_for_status()
            
            if 'json' in response.headers.get('content-type', ''):
                data = response.json()
                if service_name == "Oxylabs Location":
                    ip = data.get('ip', 'unknown')
                    providers = data.get('providers', {})
                    location_info = []
                    for provider, info in providers.items():
                        if info.get('country'):
                            location_info.append(f"{info.get('city', 'Unknown')}, {info.get('country', 'Unknown')}")
                    
                    print(f"   ✅ IP: {ip}")
                    if location_info:
                        print(f"   📍 Location: {', '.join(location_info)}")
                elif service_name == "httpbin.org":
                    print(f"   ✅ IP: {data.get('origin', 'unknown')}")
                elif service_name == "IPify":
                    print(f"   ✅ IP: {data.get('ip', 'unknown')}")
            else:
                print(f"   ✅ Response: {response.text.strip()}")
                
        except Exception as e:
            print(f"   ❌ Failed: {e}")
        
        print()
    
    # Also check direct connection for comparison
    print("🔗 Direct connection (no proxy):")
    try:
        response = requests.get("http://httpbin.org/ip", timeout=10)
        response.raise_for_status()
        data = response.json()
        print(f"   ✅ Your real IP: {data.get('origin', 'unknown')}")
    except Exception as e:
        print(f"   ❌ Failed: {e}")

if __name__ == "__main__":
    check_assigned_ip()