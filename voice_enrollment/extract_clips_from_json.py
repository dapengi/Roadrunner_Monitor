#!/usr/bin/env python3
"""
Extract audio clips from existing diarization JSON.
Helps with manual labeling by letting you hear each speaker.
"""

import json
import librosa
import soundfile as sf
from pathlib import Path
from collections import defaultdict
import sys

def extract_speaker_clips(diarization_file, audio_file, output_dir='voice_enrollment/speaker_clips'):
    """Extract one 10-second clip per detected speaker."""
    
    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    print(f"Loading diarization from: {diarization_file}")
    with open(diarization_file, 'r') as f:
        diarization = json.load(f)
    
    segments = diarization['segments']
    
    # Group by speaker
    speaker_segments = defaultdict(list)
    
    for seg in segments:
        speaker_segments[seg['speaker']].append({
            'start': seg['start'],
            'end': seg['end'],
            'duration': seg['end'] - seg['start']
        })
    
    print(f"Found {len(speaker_segments)} speakers.")
    print(f"Loading audio: {audio_file}")
    audio, sr = librosa.load(audio_file, sr=16000, mono=True)
    print("Extracting clips...\n")
    
    # Extract one good clip per speaker
    for speaker_label in sorted(speaker_segments.keys()):
        segs = speaker_segments[speaker_label]
        
        # Find a good segment (5-15 seconds long, prefer middle)
        good_segments = [s for s in segs if 5.0 <= s['duration'] <= 15.0]
        
        if not good_segments:
            # Use any segment >= 3 seconds
            good_segments = [s for s in segs if s['duration'] >= 3.0]
        
        if good_segments:
            # Pick middle segment
            segment = good_segments[len(good_segments)//2]
            
            # Extract up to 10 seconds
            start_time = segment['start']
            end_time = min(segment['start'] + 10.0, segment['end'])
            
            start_sample = int(start_time * sr)
            end_sample = int(end_time * sr)
            
            clip = audio[start_sample:end_sample]
            
            # Save
            output_file = f"{output_dir}/{speaker_label}.wav"
            sf.write(output_file, clip, sr)
            
            total_time = sum(s['duration'] for s in segs)
            print(f"✓ {speaker_label:12s}: {len(segs):3d} segments, {total_time:7.1f}s total → saved")
        else:
            print(f"⚠ {speaker_label}: No suitable segments found")
    
    print(f"\n✅ Done! Clips saved to {output_dir}/")
    print(f"   Files: {output_dir}/SPEAKER_*.wav")

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python3 extract_clips_from_json.py <diarization.json> <audio_file> [output_dir]")
        sys.exit(1)
    
    # Get output directory from argument or use default
    output_dir = sys.argv[3] if len(sys.argv) > 3 else 'speaker_clips'
    
    extract_speaker_clips(sys.argv[1], sys.argv[2], output_dir)
