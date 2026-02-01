#!/usr/bin/env python3
"""
Properly aligned transcription + diarization pipeline v2.
Uses nearest-speaker matching to handle gaps in diarization.
"""

import os
import json
import time
from dotenv import load_dotenv
load_dotenv()

import onnx_asr
import soundfile as sf

def get_speaker_at_time(timestamp, diarization_segments):
    """Find speaker at timestamp, or nearest speaker if in a gap."""
    # First, try exact match
    for seg in diarization_segments:
        if seg["start"] <= timestamp <= seg["end"]:
            return seg["speaker"]
    
    # No exact match - find nearest segment
    min_dist = float("inf")
    nearest_speaker = None
    
    for seg in diarization_segments:
        # Distance to segment start or end
        dist_start = abs(timestamp - seg["start"])
        dist_end = abs(timestamp - seg["end"])
        dist = min(dist_start, dist_end)
        
        if dist < min_dist:
            min_dist = dist
            nearest_speaker = seg["speaker"]
    
    # Only use nearest if within 2 seconds
    if min_dist <= 2.0 and nearest_speaker:
        return nearest_speaker
    
    return "UNKNOWN"

def tokens_to_words(tokens, timestamps):
    """Convert sub-word tokens to words with timestamps."""
    words = []
    current_word = ""
    word_start = None
    
    for token, ts in zip(tokens, timestamps):
        if token.startswith(" ") or not current_word:
            if current_word.strip():
                words.append({
                    "word": current_word.strip(),
                    "start": word_start,
                    "end": ts
                })
            current_word = token
            word_start = ts
        else:
            current_word += token
    
    if current_word.strip():
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
    print("ALIGNED PIPELINE v2: House Chamber Meeting 78143")
    print("="*60)
    
    # Load diarization
    print("\n[1/4] Loading diarization...")
    with open(diarization_path) as f:
        diar_data = json.load(f)
    diar_segments = diar_data["segments"]
    print(f"      {len(diar_segments)} segments loaded")
    
    # Load Parakeet
    print("\n[2/4] Loading Parakeet model...")
    model = onnx_asr.load_model("nemo-parakeet-tdt-0.6b-v2").with_timestamps()
    
    # Transcribe
    print("\n[3/4] Transcribing with timestamps...")
    info = sf.info(audio_path)
    duration = info.duration
    print(f"      Audio duration: {duration/60:.1f} minutes")
    
    audio_data, sr = sf.read(audio_path)
    chunk_duration = 60
    chunk_size = chunk_duration * sr
    
    all_words = []
    start_time = time.time()
    
    for i in range(0, len(audio_data), chunk_size):
        chunk = audio_data[i:i + chunk_size]
        if len(chunk) < sr:
            continue
            
        offset = i / sr
        chunk_path = f"/tmp/chunk_{i}.wav"
        sf.write(chunk_path, chunk, sr)
        
        try:
            result = model.recognize(chunk_path)
            words = tokens_to_words(result.tokens, result.timestamps)
            for w in words:
                w["start"] += offset
                w["end"] += offset
                all_words.append(w)
        finally:
            os.remove(chunk_path)
        
        progress = min(100, (i + chunk_size) / len(audio_data) * 100)
        print(f"      Progress: {progress:.0f}%", end="\r")
    
    transcribe_time = time.time() - start_time
    print(f"\n      Transcribed {len(all_words)} words in {transcribe_time:.1f}s")
    
    # Assign speakers
    print("\n[4/4] Assigning speakers (with gap handling)...")
    for word in all_words:
        word["speaker"] = get_speaker_at_time(word["start"], diar_segments)
    
    unknown_count = sum(1 for w in all_words if w["speaker"] == "UNKNOWN")
    print(f"      UNKNOWN words: {unknown_count} ({100*unknown_count/len(all_words):.1f}%)")
    
    # Group into segments
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
    
    # Filter out UNKNOWN segments that are very short
    segments = [s for s in segments if s["speaker"] != "UNKNOWN" or len(s["text"].split()) > 3]
    
    print(f"      Created {len(segments)} speaker segments")
    
    # Output
    print("\n" + "="*60)
    print("TRANSCRIPT WITH SPEAKER LABELS")
    print("="*60)
    
    for i, seg in enumerate(segments[:25]):
        start_fmt = f"{int(seg['start']//60):02d}:{int(seg['start']%60):02d}"
        end_fmt = f"{int(seg['end']//60):02d}:{int(seg['end']%60):02d}"
        text = seg["text"][:200] + "..." if len(seg["text"]) > 200 else seg["text"]
        print(f"\n[{start_fmt}-{end_fmt}] {seg['speaker']}:")
        print(f"  {text}")
    
    if len(segments) > 25:
        print(f"\n... ({len(segments) - 25} more segments)")
    
    # Save
    output_path = "output/house_chamber_78143_aligned_v2.json"
    with open(output_path, "w") as f:
        json.dump({"segments": segments}, f, indent=2)
    print(f"\nSaved to: {output_path}")
    
    txt_path = "output/house_chamber_78143_aligned_v2.txt"
    with open(txt_path, "w") as f:
        f.write("House Chamber Meeting - January 26, 2026\n")
        f.write("="*50 + "\n\n")
        for seg in segments:
            start_fmt = f"{int(seg['start']//60):02d}:{int(seg['start']%60):02d}"
            f.write(f"[{start_fmt}] {seg['speaker']}:\n{seg['text']}\n\n")
    print(f"Saved to: {txt_path}")

if __name__ == "__main__":
    main()
