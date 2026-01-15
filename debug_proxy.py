#!/usr/bin/env python3
"""
Debug script to test proxy configuration step by step
"""

import sys
import os
import requests
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

from config import OXYLABS_PROXY_HOST, OXYLABS_PROXY_PORT, OXYLABS_USERNAME, OXYLABS_PASSWORD

def debug_proxy_step_by_step():
    """Debug proxy configuration step by step."""
    
    print("🔍 DEBUGGING OXYLABS PROXY CONFIGURATION")
    print("=" * 50)
    
    # Step 1: Check configuration
    print("1️⃣ Configuration Check:")
    print(f"   Host: {OXYLABS_PROXY_HOST}")
    print(f"   Port: {OXYLABS_PROXY_PORT}")
    print(f"   Username: {OXYLABS_USERNAME}")
    print(f"   Password: {'*' * (len(OXYLABS_PASSWORD) - 4) + OXYLABS_PASSWORD[-4:] if OXYLABS_PASSWORD else 'Not set'}")
    
    if not all([OXYLABS_PROXY_HOST, OXYLABS_PROXY_PORT, OXYLABS_USERNAME, OXYLABS_PASSWORD]):
        print("❌ Missing proxy configuration!")
        return False
    
    # Step 2: Test direct connection first
    print("\n2️⃣ Direct Connection Test:")
    try:
        response = requests.get("http://httpbin.org/ip", timeout=10)
        response.raise_for_status()
        direct_ip = response.json().get('origin', 'unknown')
        print(f"   ✅ Direct IP: {direct_ip}")
    except Exception as e:
        print(f"   ❌ Direct connection failed: {e}")
        return False
    
    # Step 3: Build proxy URL
    print("\n3️⃣ Proxy URL Construction:")
    proxy_url = f"http://{OXYLABS_USERNAME}:{OXYLABS_PASSWORD}@{OXYLABS_PROXY_HOST}:{OXYLABS_PROXY_PORT}"
    safe_proxy_url = f"http://{OXYLABS_USERNAME}:***@{OXYLABS_PROXY_HOST}:{OXYLABS_PROXY_PORT}"
    print(f"   Proxy URL: {safe_proxy_url}")
    
    # Step 4: Test proxy connection with different methods
    print("\n4️⃣ Proxy Connection Tests:")
    
    proxies = {
        "http": proxy_url,
        "https": proxy_url
    }
    
    # Test A: Basic IP check
    print("   Test A - Basic IP check:")
    try:
        response = requests.get("http://httpbin.org/ip", proxies=proxies, timeout=15)
        response.raise_for_status()
        proxy_ip = response.json().get('origin', 'unknown')
        
        if proxy_ip == direct_ip:
            print(f"   ❌ PROBLEM: Got same IP as direct connection ({proxy_ip})")
            print("   🚨 Proxy is NOT working - using direct connection!")
        else:
            print(f"   ✅ Proxy working: {proxy_ip}")
    except Exception as e:
        print(f"   ❌ Proxy test A failed: {e}")
    
    # Test B: HTTPS test
    print("\n   Test B - HTTPS test:")
    try:
        response = requests.get("https://httpbin.org/ip", proxies=proxies, timeout=15)
        response.raise_for_status()
        proxy_ip_https = response.json().get('origin', 'unknown')
        
        if proxy_ip_https == direct_ip:
            print(f"   ❌ PROBLEM: HTTPS also using direct IP ({proxy_ip_https})")
        else:
            print(f"   ✅ HTTPS proxy working: {proxy_ip_https}")
    except Exception as e:
        print(f"   ❌ Proxy test B failed: {e}")
    
    # Test C: Different IP service
    print("\n   Test C - Alternative IP service:")
    try:
        response = requests.get("https://api.ipify.org?format=json", proxies=proxies, timeout=15)
        response.raise_for_status()
        proxy_ip_alt = response.json().get('ip', 'unknown')
        
        if proxy_ip_alt == direct_ip:
            print(f"   ❌ PROBLEM: Alternative service also shows direct IP ({proxy_ip_alt})")
        else:
            print(f"   ✅ Alternative service shows proxy IP: {proxy_ip_alt}")
    except Exception as e:
        print(f"   ❌ Proxy test C failed: {e}")
    
    # Test D: Oxylabs specific test
    print("\n   Test D - Oxylabs location service:")
    try:
        response = requests.get("https://ip.oxylabs.io/location", proxies=proxies, timeout=30)
        response.raise_for_status()
        location_data = response.json()
        oxylabs_ip = location_data.get('ip', 'unknown')
        
        if oxylabs_ip == direct_ip:
            print(f"   ❌ PROBLEM: Even Oxylabs service shows direct IP ({oxylabs_ip})")
            print("   🚨 This confirms proxy authentication is failing!")
        else:
            print(f"   ✅ Oxylabs service shows proxy IP: {oxylabs_ip}")
            
            # Show location info
            providers = location_data.get('providers', {})
            for provider, info in providers.items():
                if info.get('country'):
                    print(f"   📍 Location: {info.get('city', 'Unknown')}, {info.get('country', 'Unknown')}")
                    break
    except Exception as e:
        print(f"   ❌ Oxylabs test failed: {e}")
    
    # Test E: Check if credentials are being sent
    print("\n   Test E - Credential verification:")
    try:
        # Test without credentials to see if we get auth error
        no_auth_proxies = {
            "http": f"http://{OXYLABS_PROXY_HOST}:{OXYLABS_PROXY_PORT}",
            "https": f"http://{OXYLABS_PROXY_HOST}:{OXYLABS_PROXY_PORT}"
        }
        response = requests.get("http://httpbin.org/ip", proxies=no_auth_proxies, timeout=10)
        print(f"   ⚠️  Request without auth succeeded - this might indicate config issue")
    except requests.exceptions.ProxyError as e:
        print(f"   ✅ Request without auth failed as expected: {e}")
    except Exception as e:
        print(f"   ❓ Unexpected response without auth: {e}")

def test_alternative_proxy_formats():
    """Test different proxy URL formats."""
    print("\n🧪 TESTING ALTERNATIVE PROXY FORMATS")
    print("=" * 40)
    
    formats = [
        f"http://{OXYLABS_USERNAME}:{OXYLABS_PASSWORD}@{OXYLABS_PROXY_HOST}:{OXYLABS_PROXY_PORT}",
        f"https://{OXYLABS_USERNAME}:{OXYLABS_PASSWORD}@{OXYLABS_PROXY_HOST}:{OXYLABS_PROXY_PORT}",
        f"socks5://{OXYLABS_USERNAME}:{OXYLABS_PASSWORD}@{OXYLABS_PROXY_HOST}:{OXYLABS_PROXY_PORT}",
    ]
    
    for i, proxy_url in enumerate(formats, 1):
        protocol = proxy_url.split('://')[0]
        safe_url = proxy_url.replace(OXYLABS_PASSWORD, '***')
        print(f"\nFormat {i} ({protocol}): {safe_url}")
        
        try:
            if protocol == 'socks5':
                proxies = {
                    "http": proxy_url,
                    "https": proxy_url
                }
            else:
                proxies = {
                    "http": proxy_url,
                    "https": proxy_url
                }
            
            response = requests.get("http://httpbin.org/ip", proxies=proxies, timeout=10)
            response.raise_for_status()
            ip = response.json().get('origin', 'unknown')
            print(f"   Result: {ip}")
            
        except Exception as e:
            print(f"   Failed: {e}")

if __name__ == "__main__":
    debug_proxy_step_by_step()
    test_alternative_proxy_formats()