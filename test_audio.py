#!/usr/bin/env python3
"""
Simple script to test audio transcription and formatting.
Usage: python test_audio.py <path_to_audio_file>
"""

import sys
import os
from datetime import datetime
from modules.transcript_pipeline import TranscriptPipeline

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_audio.py <path_to_audio_file>")
        print("Example: python test_audio.py ~/Downloads/meeting.mp3")
        sys.exit(1)

    audio_path = sys.argv[1]

    if not os.path.exists(audio_path):
        print(f"❌ Error: File not found: {audio_path}")
        sys.exit(1)

    print("=" * 70)
    print("🎤 Legislative Monitor - Audio Test")
    print("=" * 70)
    print(f"Audio file: {audio_path}")
    print(f"File size: {os.path.getsize(audio_path) / 1024 / 1024:.2f} MB")
    print()

    # Initialize pipeline
    print("🔧 Initializing pipeline...")
    pipeline = TranscriptPipeline()

    # Process the audio (no upload, just test)
    print("🎯 Processing audio...")
    print()

    result = pipeline.process_meeting(
        audio_path=audio_path,
        committee="TEST",
        meeting_date=datetime.now(),
        start_time="9:00 AM",
        end_time="10:00 AM",
        committee_type="Interim",
        upload_to_seafile=False  # Don't upload during test
    )

    print()
    print("=" * 70)
    print("📊 Results")
    print("=" * 70)

    if result['success']:
        print("✅ Processing successful!")
        print()
        print(f"Segments transcribed: {len(result['segments'])}")
        print(f"Audio events detected: {len(result['audio_events'])}")

        if result['audio_events']:
            print("\nAudio Events:")
            for event in result['audio_events']:
                print(f"  - {event['type']} at {event['start']:.1f}s - {event['end']:.1f}s")

        print("\nSpeakers:")
        speakers = set(seg['speaker_id'] for seg in result['segments'])
        print(f"  {', '.join(sorted(speakers))}")

        # Save outputs locally
        print("\n📝 Saving outputs...")

        base_name = os.path.splitext(os.path.basename(audio_path))[0]

        with open(f"{base_name}.json", 'w') as f:
            f.write(result['formatted_transcripts']['json'])
        print(f"  ✅ Saved: {base_name}.json")

        with open(f"{base_name}.csv", 'w') as f:
            f.write(result['formatted_transcripts']['csv'])
        print(f"  ✅ Saved: {base_name}.csv")

        with open(f"{base_name}.txt", 'w') as f:
            f.write(result['formatted_transcripts']['txt'])
        print(f"  ✅ Saved: {base_name}.txt")

        print()
        print("🎉 Test complete! Check the output files.")

    else:
        print(f"❌ Processing failed: {result.get('error', 'Unknown error')}")
        sys.exit(1)

if __name__ == "__main__":
    main()
