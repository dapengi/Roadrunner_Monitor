#!/usr/bin/env python3
"""Test SFTP upload functionality."""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import tempfile

# Load environment variables
load_dotenv()

# Add modules to path
sys.path.insert(0, str(Path(__file__).parent))

from modules.sftp_client import SFTPClient

def test_sftp_connection():
    """Test SFTP connection and upload."""
    
    print("="*70)
    print("TESTING SFTP CONNECTION AND UPLOAD")
    print("="*70)
    
    # Get credentials from environment
    host = os.getenv('SFTP_HOST')
    port = int(os.getenv('SFTP_PORT', 22))
    username = os.getenv('SFTP_USERNAME')
    password = os.getenv('SFTP_PASSWORD')
    upload_path = os.getenv('SFTP_UPLOAD_PATH')
    
    print(f"\n📡 Connection Details:")
    print(f"   Host: {host}:{port}")
    print(f"   Username: {username}")
    print(f"   Upload Path: {upload_path}")
    
    # Create SFTP client
    print(f"\n🔌 Initializing SFTP client...")
    try:
        sftp = SFTPClient(
            host=host,
            port=port,
            username=username,
            password=password,
            upload_path=upload_path
        )
        print("   ✅ SFTP client initialized")
    except Exception as e:
        print(f"   ❌ Failed to initialize: {e}")
        return False
    
    # Test connection
    print(f"\n🔗 Testing connection...")
    if not sftp.connect():
        print("   ❌ Connection failed")
        return False
    print("   ✅ Connection successful")
    
    # List directory
    print(f"\n📂 Listing remote directory: {upload_path}")
    try:
        files = sftp.list_directory()
        print(f"   Found {len(files)} files/folders:")
        for f in files[:10]:  # Show first 10
            print(f"      - {f}")
        if len(files) > 10:
            print(f"      ... and {len(files) - 10} more")
    except Exception as e:
        print(f"   ⚠️  Could not list directory: {e}")
    
    # Create test file
    print(f"\n📝 Creating test file...")
    test_content = """This is a test upload from Roadrunner Monitor.
    
Timestamp: {datetime}
Purpose: Testing SFTP upload functionality
System: New Mexico Legislative Transcription System

This file verifies that transcript files (JSON, CSV, TXT) can be 
successfully uploaded to the Ristra SFTP server.

If you can read this, the upload is working! 🎉
""".format(datetime=__import__('datetime').datetime.now().isoformat())
    
    # Create temporary test file
    with tempfile.NamedTemporaryFile(mode='w', suffix='_test.txt', delete=False) as f:
        f.write(test_content)
        test_file = f.name
    
    print(f"   Created test file: {test_file}")
    print(f"   Size: {len(test_content)} bytes")
    
    # Upload test file
    print(f"\n📤 Uploading test file...")
    remote_filename = "roadrunner_monitor_test.txt"
    
    try:
        success = sftp.upload_file(test_file, remote_filename)
        
        if success:
            print(f"   ✅ Upload successful!")
            print(f"   Remote path: {upload_path}/{remote_filename}")
        else:
            print(f"   ❌ Upload failed")
            return False
            
    except Exception as e:
        print(f"   ❌ Upload error: {e}")
        return False
    finally:
        # Clean up temp file
        try:
            os.unlink(test_file)
        except:
            pass
    
    # Test multiple file upload
    print(f"\n📦 Testing multiple file upload...")
    
    # Create test files (simulating transcript outputs)
    test_files = []
    for ext in ['json', 'csv', 'txt']:
        content = f"Test {ext.upper()} file - {__import__('datetime').datetime.now().isoformat()}"
        with tempfile.NamedTemporaryFile(mode='w', suffix=f'_test.{ext}', delete=False) as f:
            f.write(content)
            test_files.append(f.name)
    
    print(f"   Created {len(test_files)} test files")
    
    # Upload all test files to a test subfolder
    results = sftp.upload_files(test_files, subfolder="test_batch")
    
    successful_uploads = sum(1 for success in results.values() if success)
    print(f"   Uploaded {successful_uploads}/{len(test_files)} files successfully")
    
    for filename, success in results.items():
        status = "✅" if success else "❌"
        print(f"      {status} {filename}")
    
    # Clean up test files
    for test_file in test_files:
        try:
            os.unlink(test_file)
        except:
            pass
    
    # Disconnect
    print(f"\n🔌 Disconnecting...")
    sftp.disconnect()
    print("   ✅ Disconnected")
    
    # Summary
    print("\n" + "="*70)
    print("🎉 SFTP TEST COMPLETE")
    print("="*70)
    print(f"\n✅ Connection: Working")
    print(f"✅ Single Upload: Working")
    print(f"✅ Batch Upload: {successful_uploads}/{len(test_files)} files")
    print(f"✅ Remote Path: {upload_path}")
    print(f"\n📁 Check your SFTP server at:")
    print(f"   {upload_path}/roadrunner_monitor_test.txt")
    print(f"   {upload_path}/test_batch/ (3 files)")
    print("\n" + "="*70)
    
    return True

if __name__ == "__main__":
    try:
        success = test_sftp_connection()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
