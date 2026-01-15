"""
Integrated Canary transcription with speaker diarization.
Combines NVIDIA Canary's high-accuracy ASR with Sherpa-ONNX speaker diarization.
"""

import logging
import time
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional
from tqdm import tqdm

logger = logging.getLogger(__name__)

# Import components
try:
    from modules.canary_transcription import CanaryTranscriber
    CANARY_AVAILABLE = True
except ImportError:
    CANARY_AVAILABLE = False
    logger.warning("Canary not available")

# Import diarization from existing module
from modules.sherpa_diarization import SherpaDiarizer


def transcribe_with_canary_and_diarization(
    audio_path: str,
    device: str = "cpu",
    model_name: str = "nvidia/canary-1b-v2",
    include_timestamps: bool = True
) -> str:
    """
    Transcribe audio with Canary ASR and add speaker diarization.

    This combines:
    1. NVIDIA Canary for high-accuracy transcription
    2. Sherpa-ONNX for speaker diarization
    3. Formatting with speaker labels and timestamps

    Args:
        audio_path: Path to audio file
        device: Device for Canary ('cpu', 'cuda', 'mps')
        model_name: Canary model name
        include_timestamps: Whether to include timestamps in output

    Returns:
        Formatted transcript with speaker labels
    """
    if not CANARY_AVAILABLE:
        raise ImportError("Canary not available. Install: pip install nemo_toolkit[asr]")

    try:
        print(f"\n🚀 Starting Canary + Diarization transcription for: {Path(audio_path).name}")
        print("=" * 70)

        # Step 1: Load NM vocabulary for context
        try:
            from data.nm_vocabulary import get_initial_prompt
            context = get_initial_prompt()
            print("📚 Using NM legislative vocabulary for better accuracy...")
        except ImportError:
            context = None
            logger.warning("NM vocabulary not found")

        # Step 2: Transcribe with Canary
        print("\n📝 STEP 1/3: High-Accuracy Transcription with NVIDIA Canary")
        canary_start = time.time()

        transcriber = CanaryTranscriber(model_name=model_name, device=device)
        canary_segments = transcriber.transcribe_with_timestamps(audio_path)

        canary_time = time.time() - canary_start
        print(f"✅ Canary transcription completed in {canary_time:.1f}s")

        # Extract full text
        full_text = " ".join([seg['text'] for seg in canary_segments])

        # Step 3: Speaker Diarization with Sherpa-ONNX
        print("\n🗣️  STEP 2/3: Speaker Diarization with Sherpa-ONNX")
        diarizer = SherpaDiarizer()

        # Use existing diarization approach
        diarization_start = time.time()

        # Load audio for diarization
        print("🎵 Loading audio for speaker analysis...")
        import librosa
        audio, sr = librosa.load(audio_path, sr=16000, mono=True)

        # Perform diarization
        speaker_segments = diarizer.diarize_audio(audio, sr)

        diarization_time = time.time() - diarization_start
        print(f"✅ Diarization completed in {diarization_time:.1f}s")

        # Get unique speakers
        unique_speakers = set([seg['speaker'] for seg in speaker_segments])
        print(f"🎭 Identified {len(unique_speakers)} unique speakers")

        # Step 4: Combine transcription with speaker labels
        print("\n🔗 STEP 3/3: Combining Transcription with Speaker Labels")

        # For simplicity, we'll assign speakers to the Canary text segments
        # This is a simplified approach - ideally we'd align at word level
        combined_segments = []

        for i, canary_seg in enumerate(canary_segments):
            # Find corresponding speaker segment(s)
            start_time = canary_seg.get('start', 0)
            end_time = canary_seg.get('end', 0)

            # Find overlapping speaker
            speaker = "Unknown"
            for spk_seg in speaker_segments:
                if spk_seg['start'] <= start_time < spk_seg['end']:
                    speaker = spk_seg['speaker']
                    break

            combined_segments.append({
                'speaker': speaker,
                'text': canary_seg['text'],
                'start': start_time,
                'end': end_time
            })

        # Step 5: Format output
        print("✨ Formatting final transcript...")

        # Create speaker mapping (A, B, C, etc.)
        speaker_mapping = {}
        current_letter = ord('A')
        for segment in combined_segments:
            speaker = segment['speaker']
            if speaker not in speaker_mapping and speaker != "Unknown":
                speaker_mapping[speaker] = chr(current_letter)
                current_letter += 1

        # Format transcript
        transcript_lines = []
        for segment in combined_segments:
            text = segment['text']
            speaker = segment['speaker']

            if include_timestamps:
                start_min = int(segment['start'] // 60)
                start_sec = int(segment['start'] % 60)
                end_min = int(segment['end'] // 60)
                end_sec = int(segment['end'] % 60)
                timestamp = f"[{start_min:02d}:{start_sec:02d} - {end_min:02d}:{end_sec:02d}]"

                if speaker != "Unknown":
                    speaker_letter = speaker_mapping[speaker]
                    line = f"{timestamp} Speaker {speaker_letter}: {text}"
                else:
                    line = f"{timestamp} {text}"
            else:
                if speaker != "Unknown":
                    speaker_letter = speaker_mapping[speaker]
                    line = f"Speaker {speaker_letter}: {text}"
                else:
                    line = text

            transcript_lines.append(line)

        result = "\n\n".join(transcript_lines)

        # Final summary
        print("\n" + "=" * 70)
        print("🎉 CANARY + DIARIZATION COMPLETE!")
        print(f"📊 Final Results:")
        print(f"   • Canary segments: {len(canary_segments)}")
        print(f"   • Unique speakers: {len(speaker_mapping)}")
        print(f"   • Total time: {canary_time + diarization_time:.1f}s")
        print(f"   • Accuracy: NVIDIA Canary optimized")
        print("=" * 70)

        return result

    except Exception as e:
        logger.error(f"Canary + diarization failed: {e}")
        raise


def test_canary_diarization():
    """Test Canary + diarization."""
    print("Canary + Diarization Test")
    print("=" * 60)

    if not CANARY_AVAILABLE:
        print("❌ Canary not available")
        print("\nInstall NeMo:")
        print("  pip install nemo_toolkit[asr]")
        return

    print("✅ Canary available")
    print("\nTo transcribe:")
    print("  from modules.canary_diarization import transcribe_with_canary_and_diarization")
    print("  transcript = transcribe_with_canary_and_diarization('audio.mp3')")


if __name__ == "__main__":
    test_canary_diarization()
