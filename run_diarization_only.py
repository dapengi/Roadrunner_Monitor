#!/usr/bin/env python3
"""Run diarization only on an audio file."""

import sys
import json
from modules.pyannote_diarization import PyannoteDiarizer

def main():
    if len(sys.argv) < 3:
        print("Usage: python3 run_diarization_only.py <audio_file> <output_json>")
        sys.exit(1)
    
    audio_file = sys.argv[1]
    output_file = sys.argv[2]
    
    print(f"Running diarization on: {audio_file}")
    print("This may take 10-20 minutes...")
    
    diarizer = PyannoteDiarizer(device="cpu", max_speakers=25)
    segments = diarizer.diarize(audio_file)
    
    output_data = {'segments': segments}
    
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"\n✓ Diarization saved to: {output_file}")
    print(f"   Detected {len(set(s['speaker'] for s in segments))} speakers")
    print(f"   Total segments: {len(segments)}")


if __name__ == '__main__':
    main()
