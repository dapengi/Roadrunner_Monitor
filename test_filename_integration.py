#!/usr/bin/env python3
"""Test filename generation and upload paths."""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from modules.filename_generator import get_filename_generator

def test_filename_integration():
    """Test complete filename and path generation."""
    
    print("="*80)
    print("LEGISLATIVE TRANSCRIPT FILENAME & PATH TEST")
    print("="*80)
    
    gen = get_filename_generator()
    
    # Test cases with real meeting examples
    test_cases = [
        {
            'title': 'IC - Legislative Finance (Room 307)',
            'date': datetime(2025, 11, 20, 8, 37),
            'description': 'Interim Committee - LFC'
        },
        {
            'title': 'HAFC - House Appropriations and Finance Committee',
            'date': datetime(2025, 10, 1, 1, 27),
            'description': 'House Session Committee'
        },
        {
            'title': 'Senate Judiciary Committee - SB 123 Discussion',
            'date': datetime(2025, 10, 1, 14, 16),
            'description': 'Senate Session Committee'
        },
        {
            'title': 'Interim - Water and Natural Resources',
            'date': datetime(2025, 12, 15, 9, 0),
            'description': 'Interim Committee - WNR'
        },
        {
            'title': 'IC - LESC Meeting on Education Funding',
            'date': datetime(2025, 11, 20, 11, 53),
            'description': 'Interim Committee - LESC'
        },
    ]
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n{'='*80}")
        print(f"TEST CASE {i}: {test['description']}")
        print(f"{'='*80}")
        print(f"\nMeeting Title: {test['title']}")
        print(f"Meeting Date:  {test['date'].strftime('%Y-%m-%d %I:%M %p')}")
        
        # Generate filename info
        info = gen.generate_filename(test['title'], test['date'])
        
        print(f"\n📝 GENERATED FILENAME:")
        print(f"   {info['base_name']}")
        
        print(f"\n📊 COMPONENTS:")
        print(f"   Date:         {info['date']}")
        print(f"   Session Type: {info['session_type']}")
        print(f"   Committee:    {info['committee']}")
        print(f"   Start Time:   {info['start_time']}")
        print(f"   End Time:     {info['end_time']}")
        
        # Get paths
        seafile_path = gen.get_seafile_path(info)
        sftp_path = gen.get_sftp_path()
        
        print(f"\n☁️  SEAFILE UPLOAD PATHS:")
        print(f"   {seafile_path}/{info['base_name']}.json")
        print(f"   {seafile_path}/{info['base_name']}.csv")
        print(f"   {seafile_path}/{info['base_name']}.txt")
        
        print(f"\n📤 SFTP UPLOAD PATHS:")
        print(f"   {sftp_path}/{info['base_name']}.json")
        print(f"   {sftp_path}/{info['base_name']}.csv")
        print(f"   {sftp_path}/{info['base_name']}.txt")
    
    # Summary
    print(f"\n\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    print("\n✅ Filename Format: YYYYMMDD-{TYPE}-{COMMITTEE}-{START}-{END}")
    print("\n✅ Seafile Structure:")
    print("   Interim:  /Legislative Transcription/Interim/{COMMITTEE}/{YYYY-MM-DD}/captions/")
    print("   Session:  /Legislative Transcription/Session/{HOUSE|SENATE}/{COMMITTEE}/{YYYY-MM-DD}/captions/")
    print("\n✅ SFTP Structure:")
    print("   All files: /private_html/inbound_uploads/ristra_data/incoming/")
    print("\n✅ File Formats: .json, .csv, .txt")
    print(f"{'='*80}")
    
    return True

if __name__ == "__main__":
    test_filename_integration()
