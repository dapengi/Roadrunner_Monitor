#!/usr/bin/env python3
"""
Test script to verify Nextcloud connection and functionality
"""

import sys
import os
import tempfile
import datetime
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

from modules.nextcloud import (
    create_nextcloud_folder,
    upload_to_nextcloud,
    get_nextcloud_share_link,
    check_nextcloud_file_exists
)
from config import NEXTCLOUD_URL, NEXTCLOUD_USERNAME, NEXTCLOUD_TOKEN

def test_nextcloud_connection():
    """Test all aspects of Nextcloud connectivity."""
    
    print("🔧 Testing Nextcloud Connection")
    print("=" * 50)
    
    # Check configuration
    print(f"Nextcloud URL: {NEXTCLOUD_URL}")
    print(f"Username: {NEXTCLOUD_USERNAME}")
    print(f"Token: {'*' * (len(NEXTCLOUD_TOKEN) - 4) + NEXTCLOUD_TOKEN[-4:] if NEXTCLOUD_TOKEN else 'Not set'}")
    print()
    
    if not all([NEXTCLOUD_URL, NEXTCLOUD_USERNAME, NEXTCLOUD_TOKEN]):
        print("❌ ERROR: Missing Nextcloud configuration!")
        return False
    
    test_folder = "Test_Connection_" + datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    test_filename = "test_file.txt"
    test_file_content = f"Test file created at {datetime.datetime.now()}"
    
    success_count = 0
    total_tests = 4
    
    try:
        # Test 1: Create folder
        print("1️⃣ Testing folder creation...")
        if create_nextcloud_folder(test_folder):
            print("✅ Folder creation: SUCCESS")
            success_count += 1
        else:
            print("❌ Folder creation: FAILED")
        
        # Test 2: Create and upload test file
        print("\n2️⃣ Testing file upload...")
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp_file:
            tmp_file.write(test_file_content)
            tmp_file_path = tmp_file.name
        
        try:
            nextcloud_path = f"{test_folder}/{test_filename}"
            if upload_to_nextcloud(tmp_file_path, nextcloud_path):
                print("✅ File upload: SUCCESS")
                success_count += 1
            else:
                print("❌ File upload: FAILED")
        finally:
            os.unlink(tmp_file_path)
        
        # Test 3: Check if file exists
        print("\n3️⃣ Testing file existence check...")
        if check_nextcloud_file_exists(nextcloud_path):
            print("✅ File existence check: SUCCESS")
            success_count += 1
        else:
            print("❌ File existence check: FAILED")
        
        # Test 4: Create share link
        print("\n4️⃣ Testing share link creation...")
        share_link = get_nextcloud_share_link(nextcloud_path)
        if share_link:
            print(f"✅ Share link creation: SUCCESS")
            print(f"   Share link: {share_link}")
            success_count += 1
        else:
            print("❌ Share link creation: FAILED")
        
    except Exception as e:
        print(f"❌ Unexpected error during testing: {e}")
    
    # Summary
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {success_count}/{total_tests} tests passed")
    
    if success_count == total_tests:
        print("🎉 All tests passed! Nextcloud integration is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Please check your Nextcloud configuration.")
        return False

if __name__ == "__main__":
    test_nextcloud_connection()