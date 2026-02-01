#!/usr/bin/env python3
"""Run full transcription + diarization pipeline on House Chamber meeting."""

import os
import sys
import time
import json
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

# Setup logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    audio_path = "downloads/house_chamber_78143.wav"
    diarization_path = "output/house_chamber_78143_diarization.json"
    
    print("="*60)
    print("FULL PIPELINE: House Chamber Meeting 78143")
    print("="*60)
    
    # Step 1: Load pre-computed diarization
    print("\n[1/3] Loading pre-computed Pyannote diarization...")
    with open(diarization_path) as f:
        diar_data = json.load(f)
    diarization_segments = diar_data["segments"]
    speakers = set(seg["speaker"] for seg in diarization_segments)
    print(f"      Loaded {len(diarization_segments)} segments, {len(speakers)} speakers")
    
    # Step 2: Transcribe with Parakeet
    print("\n[2/3] Transcribing with Parakeet TDT...")
    from modules.parakeet_transcription import ParakeetTranscriber
    
    transcriber = ParakeetTranscriber(device="cpu", chunk_duration=60)
    start = time.time()
    transcript = transcriber.transcribe(audio_path)
    transcribe_time = time.time() - start
    print(f"      Transcription complete in {transcribe_time:.1f}s")
    print(f"      Transcript length: {len(transcript)} chars")
    
    # Step 3: Align transcript with diarization
    print("\n[3/3] Aligning transcript with speaker segments...")
    
    # Get audio duration
    import librosa
    y, sr = librosa.load(audio_path, sr=16000, mono=True, duration=1)
    import soundfile as sf
    info = sf.info(audio_path)
    audio_duration = info.duration
    
    # Simple proportional alignment
    words = transcript.split()
    total_words = len(words)
    total_speaking_time = sum(seg["end"] - seg["start"] for seg in diarization_segments)
    
    aligned_segments = []
    word_idx = 0
    
    for seg in diarization_segments:
        seg_duration = seg["end"] - seg["start"]
        # Proportional word count
        seg_word_count = int((seg_duration / total_speaking_time) * total_words)
        seg_word_count = max(1, min(seg_word_count, total_words - word_idx))
        
        seg_words = words[word_idx:word_idx + seg_word_count]
        aligned_segments.append({
            "speaker": seg["speaker"],
            "start": seg["start"],
            "end": seg["end"],
            "text": " ".join(seg_words)
        })
        word_idx += seg_word_count
    
    # Remaining words to last segment
    if word_idx < total_words and aligned_segments:
        aligned_segments[-1]["text"] += " " + " ".join(words[word_idx:])
    
    print(f"      Aligned {len(aligned_segments)} segments")
    
    # Format output
    print("\n" + "="*60)
    print("TRANSCRIPT WITH SPEAKER LABELS")
    print("="*60)
    
    # Merge consecutive same-speaker segments
    merged = []
    for seg in aligned_segments:
        if merged and merged[-1]["speaker"] == seg["speaker"]:
            merged[-1]["text"] += " " + seg["text"]
            merged[-1]["end"] = seg["end"]
        else:
            merged.append(seg.copy())
    
    # Print first 20 merged segments
    for i, seg in enumerate(merged[:20]):
        start_fmt = f"{int(seg['start']//60):02d}:{int(seg['start']%60):02d}"
        end_fmt = f"{int(seg['end']//60):02d}:{int(seg['end']%60):02d}"
        text_preview = seg["text"][:100] + "..." if len(seg["text"]) > 100 else seg["text"]
        print(f"\n[{start_fmt}-{end_fmt}] {seg['speaker']}:")
        print(f"  {text_preview}")
    
    if len(merged) > 20:
        print(f"\n... ({len(merged) - 20} more segments)")
    
    # Save full transcript
    output_path = "output/house_chamber_78143_transcript.json"
    with open(output_path, "w") as f:
        json.dump({
            "meeting_id": "78143",
            "meeting_title": "House Chamber Meeting",
            "date": "2026-01-26",
            "audio_duration": audio_duration,
            "transcription_time": transcribe_time,
            "num_speakers": len(speakers),
            "num_segments": len(merged),
            "segments": merged
        }, f, indent=2)
    print(f"\nFull transcript saved to: {output_path}")
    
    # Also save text version
    txt_path = "output/house_chamber_78143_transcript.txt"
    with open(txt_path, "w") as f:
        f.write("House Chamber Meeting - January 26, 2026\n")
        f.write("="*50 + "\n\n")
        for seg in merged:
            start_fmt = f"{int(seg['start']//60):02d}:{int(seg['start']%60):02d}"
            f.write(f"[{start_fmt}] {seg['speaker']}:\n")
            f.write(f"{seg['text']}\n\n")
    print(f"Text transcript saved to: {txt_path}")
    
    print("\n" + "="*60)
    print("PIPELINE COMPLETE")
    print("="*60)

if __name__ == "__main__":
    main()
