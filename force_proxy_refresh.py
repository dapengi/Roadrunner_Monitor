#!/usr/bin/env python3
"""
Force refresh Oxylabs proxy connection by resetting the update timer
"""

import sys
import os
import datetime
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

from modules.proxy_manager import ProxyManager
from config import LAST_PROXY_UPDATE_FILE

def force_proxy_refresh(max_retries=3):
    """Force a fresh proxy test by clearing the last update timestamp."""
    
    print(f"🔄 Forcing Oxylabs Proxy Refresh (will try {max_retries} different IPs)")
    print("=" * 60)
    
    # Remove the last update file to force immediate refresh
    if os.path.exists(LAST_PROXY_UPDATE_FILE):
        try:
            os.remove(LAST_PROXY_UPDATE_FILE)
            print(f"✅ Cleared proxy update timestamp: {LAST_PROXY_UPDATE_FILE}")
        except Exception as e:
            print(f"❌ Error clearing timestamp file: {e}")
            return False
    else:
        print("ℹ️  No existing proxy update timestamp found")
    
    # Initialize proxy manager and force new connection test
    proxy_manager = ProxyManager()
    
    print(f"\n🧪 Testing new proxy connection with {max_retries} retry attempts...")
    success = proxy_manager.test_proxy_connection(max_retries=max_retries)
    
    if success:
        print("✅ Proxy refresh successful!")
        print(f"   New proxy endpoint: {proxy_manager.proxy_config.get('ip', 'unknown')}")
        
        # Test connectivity to verify it's working
        print("\n🔗 Testing proxy connectivity...")
        proxy_manager.test_proxy_connectivity()
        
        return True
    else:
        print("❌ Proxy refresh failed after all attempts!")
        print("   Script will fall back to direct connection (no proxy)")
        return False

def get_proxy_status():
    """Check current proxy status without forcing refresh."""
    proxy_manager = ProxyManager()
    
    print("📊 Current Proxy Status")
    print("=" * 30)
    
    if os.path.exists(LAST_PROXY_UPDATE_FILE):
        with open(LAST_PROXY_UPDATE_FILE, 'r') as f:
            last_update = datetime.datetime.fromisoformat(f.read().strip())
        
        now = datetime.datetime.now()
        hours_since = (now - last_update).total_seconds() / 3600
        
        print(f"Last update: {last_update.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Hours since: {hours_since:.1f}")
        print(f"Should update: {'Yes' if proxy_manager.should_update_proxy_list() else 'No'}")
    else:
        print("No previous update found - proxy will be tested on next run")
    
    print(f"Proxy working: {proxy_manager.proxy_working}")
    if proxy_manager.proxy_config:
        print(f"Proxy host: {proxy_manager.proxy_config.get('ip', 'unknown')}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Manage Oxylabs proxy refresh')
    parser.add_argument('--status', action='store_true', help='Show current proxy status')
    parser.add_argument('--force', action='store_true', help='Force proxy refresh')
    parser.add_argument('--retries', type=int, default=3, help='Number of IP attempts (default: 3)')
    
    args = parser.parse_args()
    
    if args.status:
        get_proxy_status()
    elif args.force:
        force_proxy_refresh(max_retries=args.retries)
    else:
        # Default action: show status first, then ask if user wants to force refresh
        get_proxy_status()
        print("\n" + "=" * 40)
        response = input(f"Force proxy refresh with {args.retries} attempts? (y/n): ").lower().strip()
        if response in ['y', 'yes']:
            print()
            force_proxy_refresh(max_retries=args.retries)