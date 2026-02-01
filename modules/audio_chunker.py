"""
Audio chunking module for parallel transcription.
Splits long audio files into manageable chunks with overlap for seamless merging.
"""

import logging
import os
import tempfile
from pathlib import Path
from typing import List, Tuple

import librosa
import soundfile as sf

logger = logging.getLogger(__name__)

# Default chunk settings
DEFAULT_CHUNK_DURATION = 20 * 60  # 20 minutes in seconds
DEFAULT_OVERLAP_DURATION = 30     # 30 seconds overlap


def chunk_audio(
    audio_path: str,
    chunk_duration: int = DEFAULT_CHUNK_DURATION,
    overlap: int = DEFAULT_OVERLAP_DURATION,
    output_dir: str = None,
    sample_rate: int = 16000
) -> List[Tuple[str, float]]:
    """
    Split audio file into chunks with overlap.

    Args:
        audio_path: Path to input audio file
        chunk_duration: Duration of each chunk in seconds (default: 20 min)
        overlap: Overlap between chunks in seconds (default: 30s)
        output_dir: Directory for chunk files (default: temp directory)
        sample_rate: Target sample rate (default: 16000 Hz)

    Returns:
        List of (chunk_path, start_time) tuples
    """
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    # Load audio
    logger.info(f"Loading audio: {audio_path}")
    audio, sr = librosa.load(audio_path, sr=sample_rate, mono=True)
    total_duration = len(audio) / sr
    logger.info(f"Audio duration: {total_duration/60:.1f} minutes")

    # Create output directory
    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="granite_chunks_")
    else:
        os.makedirs(output_dir, exist_ok=True)

    # Calculate chunk parameters
    chunk_samples = int(chunk_duration * sr)
    overlap_samples = int(overlap * sr)
    step_samples = chunk_samples - overlap_samples

    chunks = []
    start_sample = 0
    chunk_idx = 0

    while start_sample < len(audio):
        # Calculate end sample
        end_sample = min(start_sample + chunk_samples, len(audio))
        chunk_audio = audio[start_sample:end_sample]

        # Skip very short chunks (less than 5 seconds)
        chunk_duration_actual = len(chunk_audio) / sr
        if chunk_duration_actual < 5:
            logger.debug(f"Skipping short final chunk: {chunk_duration_actual:.1f}s")
            break

        # Save chunk to file
        chunk_filename = f"chunk_{chunk_idx:04d}.wav"
        chunk_path = os.path.join(output_dir, chunk_filename)
        sf.write(chunk_path, chunk_audio, sr)

        # Record chunk info
        start_time = start_sample / sr
        chunks.append((chunk_path, start_time))

        logger.debug(f"Created chunk {chunk_idx}: {start_time/60:.1f} min, "
                    f"duration: {chunk_duration_actual/60:.1f} min")

        # Move to next chunk
        start_sample += step_samples
        chunk_idx += 1

    logger.info(f"Split audio into {len(chunks)} chunks")
    return chunks


def merge_transcripts(
    results: List[dict],
    overlap_duration: int = DEFAULT_OVERLAP_DURATION
) -> str:
    """
    Merge transcripts from chunks, handling overlap regions.

    Args:
        results: List of dicts with 'start_time', 'transcript', 'chunk_path'
        overlap_duration: Duration of overlap in seconds

    Returns:
        Merged transcript text
    """
    if not results:
        return ""

    # Sort by start time
    sorted_results = sorted(results, key=lambda x: x['start_time'])

    if len(sorted_results) == 1:
        return sorted_results[0]['transcript']

    # Simple concatenation with overlap handling
    # For basic implementation, we just concatenate
    # More sophisticated merging could use fuzzy matching in overlap regions
    merged_parts = []

    for i, result in enumerate(sorted_results):
        transcript = result['transcript'].strip()

        if i == 0:
            # First chunk: use full transcript
            merged_parts.append(transcript)
        else:
            # Subsequent chunks: try to detect and remove duplicated content
            # Simple approach: skip first few words that might be duplicated
            words = transcript.split()
            if len(words) > 10:
                # Skip potential overlap (rough estimate: ~5 words per second of overlap)
                skip_words = min(int(overlap_duration * 2), len(words) // 4)
                transcript = ' '.join(words[skip_words:])
            merged_parts.append(transcript)

    return ' '.join(merged_parts)


def cleanup_chunks(chunks: List[Tuple[str, float]], remove_dir: bool = True):
    """
    Clean up temporary chunk files.

    Args:
        chunks: List of (chunk_path, start_time) tuples
        remove_dir: Whether to remove the parent directory
    """
    if not chunks:
        return

    parent_dir = None

    for chunk_path, _ in chunks:
        if os.path.exists(chunk_path):
            try:
                os.remove(chunk_path)
                logger.debug(f"Removed chunk: {chunk_path}")

                if parent_dir is None:
                    parent_dir = os.path.dirname(chunk_path)
            except Exception as e:
                logger.warning(f"Failed to remove chunk {chunk_path}: {e}")

    # Remove parent directory if empty
    if remove_dir and parent_dir and os.path.isdir(parent_dir):
        try:
            os.rmdir(parent_dir)
            logger.debug(f"Removed chunk directory: {parent_dir}")
        except OSError:
            # Directory not empty, that's fine
            pass


def get_audio_duration(audio_path: str) -> float:
    """
    Get duration of audio file in seconds.

    Args:
        audio_path: Path to audio file

    Returns:
        Duration in seconds
    """
    audio, sr = librosa.load(audio_path, sr=None, mono=True)
    return len(audio) / sr


def estimate_chunks(
    audio_path: str,
    chunk_duration: int = DEFAULT_CHUNK_DURATION,
    overlap: int = DEFAULT_OVERLAP_DURATION
) -> int:
    """
    Estimate number of chunks without loading full audio.

    Args:
        audio_path: Path to audio file
        chunk_duration: Duration of each chunk in seconds
        overlap: Overlap between chunks in seconds

    Returns:
        Estimated number of chunks
    """
    import subprocess
    import json

    # Try to get duration from ffprobe
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'quiet', '-print_format', 'json',
             '-show_format', audio_path],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            info = json.loads(result.stdout)
            duration = float(info['format']['duration'])
        else:
            # Fall back to librosa
            duration = get_audio_duration(audio_path)
    except Exception:
        duration = get_audio_duration(audio_path)

    # Calculate number of chunks
    step = chunk_duration - overlap
    num_chunks = max(1, int((duration - overlap) / step) + 1)

    return num_chunks


def test_chunker():
    """Test audio chunker."""
    print("=" * 60)
    print("Audio Chunker for Parallel Transcription")
    print("=" * 60)
    print(f"\nDefault settings:")
    print(f"  Chunk duration: {DEFAULT_CHUNK_DURATION/60:.0f} minutes")
    print(f"  Overlap: {DEFAULT_OVERLAP_DURATION} seconds")
    print("\nUsage:")
    print("  from modules.audio_chunker import chunk_audio, merge_transcripts")
    print("  chunks = chunk_audio('long_audio.wav')")
    print("  # Process each chunk...")
    print("  merged = merge_transcripts(results)")


if __name__ == "__main__":
    test_chunker()
