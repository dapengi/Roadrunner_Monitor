#!/usr/bin/env python3
"""Test Seafile upload functionality"""

import os
import sys
from pathlib import Path

# Add modules directory to path
sys.path.insert(0, str(Path(__file__).parent / 'modules'))

from seafile_client import SeafileClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_seafile_upload():
    """Test uploading a file to Seafile"""
    
    print("="*70)
    print("TESTING SEAFILE UPLOAD")
    print("="*70)
    
    # Initialize Seafile client
    print("\n📦 Initializing Seafile client...")
    try:
        seafile = SeafileClient(
            url=os.getenv('SEAFILE_URL'),
            token=os.getenv('SEAFILE_API_TOKEN'),
            library_id=os.getenv('SEAFILE_LIBRARY_ID')
        )
        print("  ✅ Seafile client initialized")
        print(f"  🔗 URL: {os.getenv('SEAFILE_URL')}")
        print(f"  📚 Library: {os.getenv('SEAFILE_LIBRARY_ID')}")
    except Exception as e:
        print(f"  ❌ Failed to initialize: {e}")
        return False
    
    # Test file to upload
    test_file = "test_output.txt"
    
    if not os.path.exists(test_file):
        print(f"\n❌ Test file not found: {test_file}")
        return False
    
    print(f"\n📤 Uploading test file: {test_file}")
    print(f"   Size: {os.path.getsize(test_file)} bytes")
    
    try:
        # Upload to transcripts folder
        remote_path = f"/transcripts/test/{test_file}"
        result = seafile.upload_file(test_file, remote_path)
        
        if result:
            print(f"  ✅ File uploaded successfully to: {remote_path}")
            print(f"  📊 Result: {result}")
            return True
        else:
            print("  ❌ Upload failed - no result returned")
            return False
            
    except Exception as e:
        print(f"  ❌ Upload failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_seafile_upload()
    
    print("\n" + "="*70)
    if success:
        print("🎉 SEAFILE UPLOAD TEST PASSED!")
    else:
        print("❌ SEAFILE UPLOAD TEST FAILED!")
    print("="*70)
    
    sys.exit(0 if success else 1)
