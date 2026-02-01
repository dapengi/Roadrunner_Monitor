#!/usr/bin/env python3
"""
Properly aligned transcription + diarization pipeline.
Uses Parakeet token timestamps to accurately assign speakers.
"""

import os
import json
import time
from dotenv import load_dotenv
load_dotenv()

import onnx_asr
import soundfile as sf
import numpy as np

def get_speaker_at_time(timestamp, diarization_segments):
    """Find which speaker is talking at a given timestamp."""
    for seg in diarization_segments:
        if seg["start"] <= timestamp <= seg["end"]:
            return seg["speaker"]
    return "UNKNOWN"

def tokens_to_words(tokens, timestamps):
    """Convert sub-word tokens to words with timestamps."""
    words = []
    current_word = ""
    word_start = None
    
    for token, ts in zip(tokens, timestamps):
        if token.startswith(" ") or not current_word:
            # New word starts
            if current_word:
                words.append({
                    "word": current_word.strip(),
                    "start": word_start,
                    "end": ts
                })
            current_word = token
            word_start = ts
        else:
            # Continue current word
            current_word += token
    
    # Don't forget last word
    if current_word:
        words.append({
            "word": current_word.strip(),
            "start": word_start,
            "end": timestamps[-1] if timestamps else word_start
        })
    
    return words

def main():
    audio_path = "downloads/house_chamber_78143.wav"
    diarization_path = "output/house_chamber_78143_diarization.json"
    
    print("="*60)
    print("ALIGNED PIPELINE: House Chamber Meeting 78143")
    print("="*60)
    
    # Load diarization
    print("\n[1/4] Loading diarization...")
    with open(diarization_path) as f:
        diar_data = json.load(f)
    diar_segments = diar_data["segments"]
    print(f"      {len(diar_segments)} segments loaded")
    
    # Load Parakeet with timestamps
    print("\n[2/4] Loading Parakeet model...")
    model = onnx_asr.load_model("nemo-parakeet-tdt-0.6b-v2").with_timestamps()
    
    # Transcribe with timestamps
    print("\n[3/4] Transcribing with timestamps...")
    
    # Get audio duration
    info = sf.info(audio_path)
    duration = info.duration
    print(f"      Audio duration: {duration/60:.1f} minutes")
    
    # For long audio, process in chunks but track offset
    chunk_duration = 60  # seconds
    audio_data, sr = sf.read(audio_path)
    
    all_words = []
    chunk_size = chunk_duration * sr
    
    start_time = time.time()
    for i in range(0, len(audio_data), chunk_size):
        chunk = audio_data[i:i + chunk_size]
        if len(chunk) < sr:  # Skip very short chunks
            continue
            
        offset = i / sr
        chunk_path = f"/tmp/chunk_{i}.wav"
        sf.write(chunk_path, chunk, sr)
        
        try:
            result = model.recognize(chunk_path)
            words = tokens_to_words(result.tokens, result.timestamps)
            
            # Add offset to timestamps
            for w in words:
                w["start"] += offset
                w["end"] += offset
                all_words.append(w)
        finally:
            os.remove(chunk_path)
        
        # Progress
        progress = min(100, (i + chunk_size) / len(audio_data) * 100)
        print(f"      Progress: {progress:.0f}%", end="\r")
    
    transcribe_time = time.time() - start_time
    print(f"\n      Transcribed {len(all_words)} words in {transcribe_time:.1f}s")
    
    # Assign speakers to words
    print("\n[4/4] Assigning speakers to words...")
    for word in all_words:
        word["speaker"] = get_speaker_at_time(word["start"], diar_segments)
    
    # Group consecutive same-speaker words into segments
    segments = []
    current_seg = None
    
    for word in all_words:
        if current_seg is None or current_seg["speaker"] != word["speaker"]:
            if current_seg:
                segments.append(current_seg)
            current_seg = {
                "speaker": word["speaker"],
                "start": word["start"],
                "end": word["end"],
                "text": word["word"]
            }
        else:
            current_seg["end"] = word["end"]
            current_seg["text"] += " " + word["word"]
    
    if current_seg:
        segments.append(current_seg)
    
    print(f"      Created {len(segments)} speaker segments")
    
    # Output
    print("\n" + "="*60)
    print("TRANSCRIPT WITH SPEAKER LABELS")
    print("="*60)
    
    # Print first 30 segments
    for i, seg in enumerate(segments[:30]):
        start_fmt = f"{int(seg['start']//60):02d}:{int(seg['start']%60):02d}"
        end_fmt = f"{int(seg['end']//60):02d}:{int(seg['end']%60):02d}"
        text_preview = seg["text"][:150] + "..." if len(seg["text"]) > 150 else seg["text"]
        print(f"\n[{start_fmt}-{end_fmt}] {seg['speaker']}:")
        print(f"  {text_preview}")
    
    if len(segments) > 30:
        print(f"\n... ({len(segments) - 30} more segments)")
    
    # Save
    output_path = "output/house_chamber_78143_aligned.json"
    with open(output_path, "w") as f:
        json.dump({
            "meeting_id": "78143",
            "audio_duration": duration,
            "num_words": len(all_words),
            "num_segments": len(segments),
            "transcription_time": transcribe_time,
            "segments": segments
        }, f, indent=2)
    print(f"\nSaved to: {output_path}")
    
    # Save text version
    txt_path = "output/house_chamber_78143_aligned.txt"
    with open(txt_path, "w") as f:
        f.write("House Chamber Meeting - January 26, 2026 (Aligned)\n")
        f.write("="*50 + "\n\n")
        for seg in segments:
            start_fmt = f"{int(seg['start']//60):02d}:{int(seg['start']%60):02d}"
            f.write(f"[{start_fmt}] {seg['speaker']}:\n{seg['text']}\n\n")
    print(f"Saved to: {txt_path}")
    
    print("\n" + "="*60)
    print("COMPLETE")
    print("="*60)

if __name__ == "__main__":
    main()
