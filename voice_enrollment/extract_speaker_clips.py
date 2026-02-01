#!/usr/bin/env python3
"""
Extract 10-second audio clips for each detected speaker.
Helps with manual labeling by letting you hear each speaker.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import librosa
import soundfile as sf
from pathlib import Path
from modules.sherpa_diarization import SherpaDiarizer

def extract_speaker_clips(audio_file, output_dir='voice_enrollment/speaker_clips'):
    """Extract one 10-second clip per detected speaker."""
    
    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    print("Running Sherpa diarization to identify speakers...")
    diarizer = SherpaDiarizer()
    if not diarizer.load_models():
        print("Failed to load Sherpa models")
        return
    
    # Get diarization results
    diarization = diarizer.diarize_audio(audio_file)
    
    if not diarization:
        print("Diarization failed")
        return
    
    # Group by speaker
    from collections import defaultdict
    speaker_segments = defaultdict(list)
    
    for start_time, end_time, speaker_label in diarization:
        speaker_segments[speaker_label].append({
            'start': start_time,
            'end': end_time,
            'duration': end_time - start_time
        })
    
    print(f"\nFound {len(speaker_segments)} speakers. Extracting clips...")
    
    # Load audio
    print("Loading audio...")
    audio, sr = librosa.load(audio_file, sr=16000, mono=True)
    
    # Extract one good clip per speaker
    for speaker_label in sorted(speaker_segments.keys()):
        segments = speaker_segments[speaker_label]
        
        # Find a good segment (5-15 seconds long, prefer middle of their speaking time)
        good_segments = [s for s in segments if 5.0 <= s['duration'] <= 15.0]
        
        if not good_segments:
            # Use any segment >= 3 seconds
            good_segments = [s for s in segments if s['duration'] >= 3.0]
        
        if good_segments:
            # Pick a segment from the middle of their speaking time
            segment = good_segments[len(good_segments)//2]
            
            # Extract 10 seconds (or full segment if shorter)
            start_time = segment['start']
            end_time = min(segment['start'] + 10.0, segment['end'])
            
            start_sample = int(start_time * sr)
            end_sample = int(end_time * sr)
            
            clip = audio[start_sample:end_sample]
            
            # Save
            output_file = f"{output_dir}/{speaker_label}.wav"
            sf.write(output_file, clip, sr)
            
            total_time = sum(s['duration'] for s in segments)
            print(f"✓ {speaker_label}: {len(segments)} segments, {total_time:.1f}s total → {output_file}")
        else:
            print(f"⚠ {speaker_label}: No suitable segments found")
    
    print(f"\nDone! Clips saved to {output_dir}/")
    print("Download with: scp 'josh@192.168.4.50:~/Roadrunner_Monitor/voice_enrollment/speaker_clips/*.wav' ~/Desktop/")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 extract_speaker_clips.py <audio_file>")
        sys.exit(1)
    
    extract_speaker_clips(sys.argv[1])
