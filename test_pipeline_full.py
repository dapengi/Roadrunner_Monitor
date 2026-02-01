#!/usr/bin/env python3
"""
Test the complete Canary pipeline end-to-end.
Tests: Transcription, Formatting, and outputs (no upload yet).
"""

import sys
import os
from datetime import datetime
from pathlib import Path

# Add modules to path
sys.path.insert(0, str(Path(__file__).parent))

print("=" * 70)
print("TESTING COMPLETE CANARY PIPELINE")
print("=" * 70)

# Test imports
print("\n📦 Testing imports...")
try:
    from modules.transcript_pipeline_canary import TranscriptPipeline
    print("  ✅ Canary pipeline imported")
except ImportError as e:
    print(f"  ❌ Failed to import pipeline: {e}")
    sys.exit(1)

try:
    from modules.proxy_manager import ProxyManager
    print("  ✅ Proxy manager imported")
except ImportError as e:
    print(f"  ❌ Failed to import proxy: {e}")
    sys.exit(1)

# Initialize pipeline
print("\n🚀 Initializing pipeline...")
pipeline = TranscriptPipeline(use_canary=True)
print("  ✅ Pipeline initialized with Canary GPU transcription")

# Test with existing audio file
audio_file = "067a-ac85-4fab-9d40-370df38f07b9_mono.wav"

if not os.path.exists(audio_file):
    print(f"\n❌ Audio file not found: {audio_file}")
    print("   Please ensure the test audio file exists")
    sys.exit(1)

print(f"\n🎵 Testing with: {audio_file}")

# Process meeting (without Seafile upload for now)
print("\n🔄 Processing meeting...")
print("   - Transcribing with Canary + Diarization")
print("   - Detecting audio events")
print("   - Formatting outputs (JSON, CSV, TXT)")
print("   - Skipping Seafile upload (test mode)")

result = pipeline.process_meeting(
    audio_path=audio_file,
    committee="TEST",
    meeting_date=datetime(2025, 1, 5),
    start_time="9:00 AM",
    end_time="12:00 PM",
    committee_type="Interim",
    upload_to_seafile=False  # Skip upload for now
)

# Check results
print("\n" + "=" * 70)
print("RESULTS")
print("=" * 70)

if result['success']:
    print("✅ Pipeline completed successfully!")
    print(f"\n📊 Statistics:")
    print(f"  - Segments: {len(result['segments'])}")
    print(f"  - Audio events: {len(result['audio_events'])}")
    print(f"  - Duration: {result.get('audio_duration', 0):.1f} seconds")
    
    print(f"\n📝 Generated formats:")
    for format_type in result['formatted_transcripts'].keys():
        content = result['formatted_transcripts'][format_type]
        print(f"  - {format_type.upper()}: {len(content)} characters")
    
    # Save outputs
    print(f"\n💾 Saving outputs...")
    base_name = "test_output"
    
    for format_type, content in result['formatted_transcripts'].items():
        filename = f"{base_name}.{format_type}"
        with open(filename, 'w') as f:
            f.write(content)
        print(f"  ✅ Saved: {filename}")
    
    print(f"\n🎉 Test completed successfully!")
    print(f"   Check the output files: {base_name}.{{json,csv,txt}}")
    
else:
    print(f"❌ Pipeline failed: {result.get('error', 'Unknown error')}")
    sys.exit(1)
