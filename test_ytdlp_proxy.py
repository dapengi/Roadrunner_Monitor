#!/usr/bin/env python3
"""
Test yt-dlp with Oxylabs proxy to understand the 503 error
"""

import sys
import os
import tempfile
import yt_dlp
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

from modules.proxy_manager import ProxyManager
from config import OXYLABS_PROXY_HOST, OXYLABS_PROXY_PORT, OXYLABS_USERNAME, OXYLABS_PASSWORD

def test_ytdlp_with_proxy():
    """Test yt-dlp with various proxy configurations."""
    
    print("🧪 TESTING YT-DLP WITH OXYLABS PROXY")
    print("=" * 50)
    
    # Test URLs - start with simple ones
    test_urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Simple test
        "https://sg002-live.sliq.net/00293-vod-2/_definst_/roadshow3/2025-08-18/ROADSHOW3_IC%20-%20Water%20and%20Natural%20Resources_2025-08-18-13.25.09_15680_77483_80.mp4/playlist.m3u8"  # Your actual URL
    ]
    
    # Create proxy manager
    proxy_manager = ProxyManager()
    
    # Test proxy status first
    print("1️⃣ Proxy Status Check:")
    if proxy_manager.test_proxy_connection():
        proxy_url = proxy_manager.get_yt_dlp_proxy_url()
        safe_proxy_url = proxy_url.replace(OXYLABS_PASSWORD, '***') if proxy_url else 'None'
        print(f"   ✅ Proxy working: {safe_proxy_url}")
    else:
        print("   ❌ Proxy not working")
        return
    
    print()
    
    # Test each URL
    for i, test_url in enumerate(test_urls, 1):
        print(f"{i}️⃣ Testing URL {i}:")
        url_display = test_url[:60] + "..." if len(test_url) > 60 else test_url
        print(f"   URL: {url_display}")
        
        # Test without proxy first
        print(f"   🔗 Testing without proxy...")
        try:
            ydl_opts_direct = {
                'quiet': True,
                'no_warnings': True,
                'simulate': True,  # Just simulate, don't download
                'socket_timeout': 10,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts_direct) as ydl:
                info = ydl.extract_info(test_url, download=False)
                print(f"   ✅ Direct connection: Success (title: {info.get('title', 'Unknown')[:30]})")
        except Exception as e:
            print(f"   ❌ Direct connection failed: {e}")
        
        # Test with proxy
        print(f"   🔄 Testing with Oxylabs proxy...")
        try:
            ydl_opts_proxy = {
                'quiet': True,
                'no_warnings': True,
                'simulate': True,  # Just simulate, don't download
                'socket_timeout': 10,
                'proxy': proxy_url,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts_proxy) as ydl:
                info = ydl.extract_info(test_url, download=False)
                print(f"   ✅ Proxy connection: Success (title: {info.get('title', 'Unknown')[:30]})")
        except Exception as e:
            error_msg = str(e)
            if "503 Service Unavailable" in error_msg:
                print(f"   ❌ Proxy connection: 503 Service Unavailable")
                print(f"      This suggests Oxylabs is blocking video streaming domains")
            elif "Tunnel connection failed" in error_msg:
                print(f"   ❌ Proxy connection: Tunnel connection failed")
                print(f"      This suggests HTTPS tunneling issues with the proxy")
            else:
                print(f"   ❌ Proxy connection failed: {e}")
        
        print()
    
    # Test different proxy formats
    print("3️⃣ Testing Alternative Proxy Formats:")
    
    alt_formats = [
        f"http://{OXYLABS_USERNAME}:{OXYLABS_PASSWORD}@{OXYLABS_PROXY_HOST}:{OXYLABS_PROXY_PORT}",
        f"socks5://{OXYLABS_USERNAME}:{OXYLABS_PASSWORD}@{OXYLABS_PROXY_HOST}:{OXYLABS_PROXY_PORT}",
    ]
    
    simple_test_url = "https://httpbin.org/get"  # Simple test
    
    for i, alt_proxy in enumerate(alt_formats, 1):
        protocol = alt_proxy.split('://')[0]
        safe_alt_proxy = alt_proxy.replace(OXYLABS_PASSWORD, '***')
        print(f"   Format {i} ({protocol}): {safe_alt_proxy}")
        
        try:
            ydl_opts_alt = {
                'quiet': True,
                'no_warnings': True,
                'simulate': True,
                'socket_timeout': 5,
                'proxy': alt_proxy,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts_alt) as ydl:
                info = ydl.extract_info(simple_test_url, download=False)
                print(f"   ✅ Success with {protocol}")
        except Exception as e:
            print(f"   ❌ Failed with {protocol}: {e}")

def test_manual_proxy_curl():
    """Test if the proxy works with curl for video URLs."""
    print("\n4️⃣ Testing with curl:")
    
    proxy_url = f"http://{OXYLABS_USERNAME}:{OXYLABS_PASSWORD}@{OXYLABS_PROXY_HOST}:{OXYLABS_PROXY_PORT}"
    test_url = "https://sg002-live.sliq.net/00293-vod-2/_definst_/roadshow3/2025-08-18/ROADSHOW3_IC%20-%20Water%20and%20Natural%20Resources_2025-08-18-13.25.09_15680_77483_80.mp4/playlist.m3u8"
    
    # Test with curl to see if it's a yt-dlp specific issue
    print(f"   Testing video URL with curl through proxy...")
    import subprocess
    try:
        result = subprocess.run([
            'curl', '-s', '-I', '--proxy', proxy_url, '--max-time', '10', test_url
        ], capture_output=True, text=True, timeout=15)
        
        if result.returncode == 0:
            print(f"   ✅ curl success: {result.stdout.split()[1] if result.stdout.split() else 'Unknown status'}")
        else:
            print(f"   ❌ curl failed: {result.stderr}")
    except Exception as e:
        print(f"   ❌ curl test error: {e}")

if __name__ == "__main__":
    test_ytdlp_with_proxy()
    test_manual_proxy_curl()