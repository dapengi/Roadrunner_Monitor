#!/usr/bin/env python3
"""Test both Seafile and SFTP uploads with new filename convention."""

import os
import sys
import tempfile
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Add modules to path
sys.path.insert(0, str(Path(__file__).parent))

from modules.seafile_client import SeafileClient
from modules.sftp_client import SFTPClient
from modules.filename_generator import get_filename_generator

def create_test_files(base_name):
    """Create test transcript files."""
    test_files = {}
    
    # JSON content
    json_content = f'''{{
    "meeting": "Test Legislative Meeting",
    "filename": "{base_name}",
    "date": "{datetime.now().isoformat()}",
    "transcript": [
        {{
            "speaker": "Speaker A",
            "text": "Senator Figueroa from Albuquerque spoke about the LFC budget at Santa Fe.",
            "start": 0.0,
            "end": 5.2
        }},
        {{
            "speaker": "Speaker B",
            "text": "Representatives Martinez, Gonzales, and Roybal testified on the HAFC proposal.",
            "start": 5.2,
            "end": 10.5
        }}
    ]
}}'''
    
    # CSV content
    csv_content = f'''speaker,text,start,end
Speaker A,"Senator Figueroa from Albuquerque spoke about the LFC budget at Santa Fe.",0.0,5.2
Speaker B,"Representatives Martinez, Gonzales, and Roybal testified on the HAFC proposal.",5.2,10.5'''
    
    # TXT content
    txt_content = f'''Legislative Meeting Transcript
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Filename: {base_name}

Speaker A: Senator Figueroa from Albuquerque spoke about the LFC budget at Santa Fe.

Speaker B: Representatives Martinez, Gonzales, and Roybal testified on the HAFC proposal.

--- End of Transcript ---'''
    
    # Create temporary files
    for ext, content in [('json', json_content), ('csv', csv_content), ('txt', txt_content)]:
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix=f'.{ext}', delete=False)
        temp_file.write(content)
        temp_file.close()
        test_files[ext] = temp_file.name
    
    return test_files

def test_dual_upload():
    """Test uploading to both Seafile and SFTP."""
    
    print("="*80)
    print("DUAL UPLOAD TEST - SEAFILE & SFTP")
    print("="*80)
    
    # Test meeting info
    test_meeting = {
        'title': 'IC - Legislative Finance Committee',
        'date': datetime(2025, 11, 20, 8, 37)
    }
    
    print(f"\n📋 Test Meeting:")
    print(f"   Title: {test_meeting['title']}")
    print(f"   Date: {test_meeting['date'].strftime('%Y-%m-%d %I:%M %p')}")
    
    # Generate filename
    print(f"\n🔤 Generating Filename...")
    filename_gen = get_filename_generator()
    filename_info = filename_gen.generate_filename(
        title=test_meeting['title'],
        meeting_date=test_meeting['date']
    )
    
    base_name = filename_info['base_name']
    print(f"   ✅ Generated: {base_name}")
    print(f"   Session Type: {filename_info['session_type']}")
    print(f"   Committee: {filename_info['committee']}")
    
    # Create test files
    print(f"\n📝 Creating Test Files...")
    test_files = create_test_files(base_name)
    print(f"   ✅ Created 3 test files")
    for ext, path in test_files.items():
        size = os.path.getsize(path)
        print(f"      - {ext.upper()}: {size} bytes")
    
    # Initialize Seafile
    print(f"\n☁️  SEAFILE UPLOAD TEST")
    print("   " + "="*76)
    
    try:
        seafile = SeafileClient(
            url=os.getenv('SEAFILE_URL'),
            token=os.getenv('SEAFILE_API_TOKEN'),
            library_id=os.getenv('SEAFILE_LIBRARY_ID')
        )
        print(f"   ✅ Connected to Seafile: {os.getenv('SEAFILE_URL')}")
    except Exception as e:
        print(f"   ❌ Failed to connect to Seafile: {e}")
        return False
    
    # Get Seafile path
    seafile_base_path = filename_gen.get_seafile_path(filename_info)
    print(f"   📁 Upload Path: {seafile_base_path}")
    
    # Upload to Seafile
    seafile_results = {}
    for ext, local_file in test_files.items():
        remote_path = f"{seafile_base_path}/{base_name}.{ext}"
        print(f"\n   Uploading {ext.upper()}...")
        
        try:
            success = seafile.upload_file(local_file, remote_path)
            if success:
                print(f"   ✅ SUCCESS: {remote_path}")
                seafile_results[ext] = remote_path
            else:
                print(f"   ❌ FAILED: {remote_path}")
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
    
    # Initialize SFTP
    print(f"\n\n📤 SFTP UPLOAD TEST")
    print("   " + "="*76)
    
    try:
        sftp = SFTPClient(
            host=os.getenv('SFTP_HOST'),
            port=int(os.getenv('SFTP_PORT', 22)),
            username=os.getenv('SFTP_USERNAME'),
            password=os.getenv('SFTP_PASSWORD'),
            upload_path=os.getenv('SFTP_UPLOAD_PATH')
        )
        
        if sftp.connect():
            print(f"   ✅ Connected to SFTP: {os.getenv('SFTP_HOST')}:{os.getenv('SFTP_PORT')}")
        else:
            print(f"   ❌ Failed to connect to SFTP")
            return False
            
    except Exception as e:
        print(f"   ❌ Failed to initialize SFTP: {e}")
        return False
    
    # Get SFTP path
    sftp_path = filename_gen.get_sftp_path()
    print(f"   📁 Upload Path: {sftp_path}")
    
    # Rename files for SFTP upload
    renamed_files = []
    for ext, local_file in test_files.items():
        proper_name = f"{base_name}.{ext}"
        proper_path = os.path.join(os.path.dirname(local_file), proper_name)
        
        # Rename
        import shutil
        shutil.copy2(local_file, proper_path)
        renamed_files.append(proper_path)
    
    # Upload to SFTP
    print(f"\n   Uploading batch of {len(renamed_files)} files...")
    sftp_results = {}
    
    try:
        upload_results = sftp.upload_files(renamed_files, subfolder=None)
        
        for filename, success in upload_results.items():
            ext = filename.split('.')[-1].upper()
            if success:
                print(f"   ✅ SUCCESS: {filename}")
                sftp_results[filename] = True
            else:
                print(f"   ❌ FAILED: {filename}")
                
    except Exception as e:
        print(f"   ❌ ERROR during batch upload: {e}")
    
    # Disconnect SFTP
    sftp.disconnect()
    
    # Cleanup
    print(f"\n🧹 Cleaning up test files...")
    for local_file in test_files.values():
        try:
            os.unlink(local_file)
        except:
            pass
    
    for renamed_file in renamed_files:
        try:
            os.unlink(renamed_file)
        except:
            pass
    
    print(f"   ✅ Cleanup complete")
    
    # Summary
    print(f"\n\n{'='*80}")
    print("📊 UPLOAD SUMMARY")
    print(f"{'='*80}")
    print(f"\n📄 Filename: {base_name}")
    print(f"\n☁️  Seafile Results: {len(seafile_results)}/3 files uploaded")
    for ext, path in seafile_results.items():
        print(f"   ✅ {ext.upper()}: {path}")
    
    print(f"\n📤 SFTP Results: {len(sftp_results)}/3 files uploaded")
    for filename in sftp_results.keys():
        print(f"   ✅ {filename}")
    
    print(f"\n{'='*80}")
    
    # Overall result
    total_success = len(seafile_results) + len(sftp_results)
    if total_success == 6:
        print("🎉 ALL UPLOADS SUCCESSFUL! (6/6)")
        print(f"{'='*80}")
        return True
    else:
        print(f"⚠️  PARTIAL SUCCESS: {total_success}/6 uploads completed")
        print(f"{'='*80}")
        return False

if __name__ == "__main__":
    try:
        success = test_dual_upload()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
