#!/usr/bin/env python3
"""
Extract audio samples for each detected speaker to help with labeling.
Run this before labeling to create sample clips you can listen to.
"""

import sys
import json
import librosa
import soundfile as sf
from pathlib import Path

def extract_samples(diarization_file, audio_file, output_dir="voice_enrollment/samples"):
    """Extract 10-second sample from each speaker."""
    
    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Load diarization results (you'd need to save this from the enrollment)
    # For now, we'll work with the audio file directly
    
    print(f"Loading audio: {audio_file}")
    audio, sr = librosa.load(audio_file, sr=16000, mono=True)
    
    # Extract samples at different points in the file
    # This is a manual approach - extract samples every 10 minutes
    duration = len(audio) / sr
    
    for i in range(0, int(duration), 600):  # Every 10 minutes
        start = i
        end = min(i + 10, duration)  # 10-second sample
        
        start_sample = int(start * sr)
        end_sample = int(end * sr)
        
        segment = audio[start_sample:end_sample]
        
        output_file = f"{output_dir}/sample_{i//60:04d}min_{i%60:02d}sec.wav"
        sf.write(output_file, segment, sr)
        
        print(f"Saved: {output_file} (at {i//60}:{i%60:02d})")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 extract_speaker_samples.py <audio_file>")
        sys.exit(1)
    
    extract_samples(None, sys.argv[1])
    print("\nDone! Listen to samples in voice_enrollment/samples/")
