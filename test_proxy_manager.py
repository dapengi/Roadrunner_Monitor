#!/usr/bin/env python3
"""
Test the ProxyManager specifically to see where the real IP is coming from
"""

import sys
import os
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

from modules.proxy_manager import ProxyManager

def test_proxy_manager_detailed():
    """Test ProxyManager with detailed logging."""
    
    print("🧪 TESTING PROXY MANAGER DETAILED")
    print("=" * 40)
    
    # Create proxy manager
    proxy_manager = ProxyManager()
    
    # Clear any existing state
    proxy_manager._proxy_working = False
    proxy_manager._proxy_config = None
    
    print("Testing proxy connection with max_retries=1...")
    result = proxy_manager.test_proxy_connection(max_retries=1)
    
    print(f"\nResult: {result}")
    print(f"Proxy working: {proxy_manager.proxy_working}")
    print(f"Proxy config: {proxy_manager.proxy_config}")

if __name__ == "__main__":
    test_proxy_manager_detailed()