"""
Parallel transcription module for long audio files.
Orchestrates multiple Granite transcription workers for efficient processing.
"""

import logging
import os
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import List, Optional

logger = logging.getLogger(__name__)


def _transcribe_chunk_worker(args: tuple) -> dict:
    """
    Worker function for parallel transcription.
    Each worker loads its own model instance (required for multiprocessing).

    Args:
        args: Tuple of (chunk_path, start_time, model_name, device)

    Returns:
        Dict with transcript and timing info
    """
    chunk_path, start_time, model_name, device = args

    # Import inside worker to avoid pickling issues
    from modules.granite_transcription import GraniteTranscriber

    try:
        transcriber = GraniteTranscriber(model_name=model_name, device=device)
        transcript = transcriber.transcribe(chunk_path)

        return {
            'start_time': start_time,
            'transcript': transcript,
            'chunk_path': chunk_path,
            'success': True,
            'error': None
        }
    except Exception as e:
        logger.error(f"Worker failed on chunk {chunk_path}: {e}")
        return {
            'start_time': start_time,
            'transcript': '',
            'chunk_path': chunk_path,
            'success': False,
            'error': str(e)
        }


class ParallelTranscriber:
    """
    Parallel transcription orchestrator using Granite Speech.
    Splits audio into chunks and processes them concurrently.
    """

    def __init__(
        self,
        num_workers: int = 2,
        model_name: str = "ibm-granite/granite-speech-3.3-2b",
        device: str = "auto",
        chunk_duration: int = 1200,  # 20 minutes
        overlap: int = 30
    ):
        """
        Initialize parallel transcriber.

        Args:
            num_workers: Number of parallel workers (default: 2)
            model_name: Granite model name
            device: Device for each worker ('auto', 'cuda', 'cpu')
            chunk_duration: Chunk duration in seconds
            overlap: Overlap between chunks in seconds
        """
        self.num_workers = num_workers
        self.model_name = model_name
        self.device = self._resolve_device(device)
        self.chunk_duration = chunk_duration
        self.overlap = overlap

    def _resolve_device(self, device: str) -> str:
        """Resolve device string."""
        if device == "auto":
            import torch
            if torch.cuda.is_available():
                return "cuda"
            return "cpu"
        return device

    def transcribe(self, audio_path: str) -> str:
        """
        Transcribe audio file using parallel processing.

        Args:
            audio_path: Path to audio file

        Returns:
            Full transcribed text
        """
        from modules.audio_chunker import (
            chunk_audio, merge_transcripts, cleanup_chunks, get_audio_duration
        )

        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        # Get audio duration for logging
        duration = get_audio_duration(audio_path)
        logger.info(f"Starting parallel transcription of {duration/60:.1f} minute audio")
        logger.info(f"Using {self.num_workers} workers, device: {self.device}")

        start_time = time.time()

        # Split audio into chunks
        logger.info("Splitting audio into chunks...")
        chunks = chunk_audio(
            audio_path,
            chunk_duration=self.chunk_duration,
            overlap=self.overlap
        )
        logger.info(f"Created {len(chunks)} chunks")

        # Prepare worker arguments
        work_items = [
            (chunk_path, chunk_start, self.model_name, self.device)
            for chunk_path, chunk_start in chunks
        ]

        # Process chunks in parallel
        results = []
        failed_chunks = []

        try:
            # Use ProcessPoolExecutor for true parallelism
            # Note: For GPU, consider using sequential processing or
            # ThreadPoolExecutor to share GPU memory
            if self.device == "cpu" and self.num_workers > 1:
                logger.info(f"Processing {len(chunks)} chunks with {self.num_workers} parallel workers...")
                with ProcessPoolExecutor(max_workers=self.num_workers) as executor:
                    futures = {
                        executor.submit(_transcribe_chunk_worker, item): item
                        for item in work_items
                    }

                    for future in as_completed(futures):
                        result = future.result()
                        if result['success']:
                            results.append(result)
                        else:
                            failed_chunks.append(result)
                            logger.warning(f"Chunk failed: {result['error']}")
            else:
                # Sequential processing for GPU (memory constraints)
                # or single worker mode
                logger.info(f"Processing {len(chunks)} chunks sequentially on {self.device}...")
                for item in work_items:
                    result = _transcribe_chunk_worker(item)
                    if result['success']:
                        results.append(result)
                    else:
                        failed_chunks.append(result)
                        logger.warning(f"Chunk failed: {result['error']}")

            # Report any failures
            if failed_chunks:
                logger.warning(f"{len(failed_chunks)} chunks failed transcription")

            # Merge transcripts
            logger.info("Merging transcripts...")
            merged_transcript = merge_transcripts(results, self.overlap)

            elapsed = time.time() - start_time
            rtf = elapsed / duration  # Real-time factor
            logger.info(f"Transcription complete in {elapsed:.1f}s (RTF: {rtf:.2f}x)")

            return merged_transcript

        finally:
            # Cleanup chunk files
            logger.info("Cleaning up temporary chunk files...")
            cleanup_chunks(chunks)

    def transcribe_with_fallback(
        self,
        audio_path: str,
        fallback_to_whisper: bool = True
    ) -> str:
        """
        Transcribe with fallback to Whisper if Granite fails.

        Args:
            audio_path: Path to audio file
            fallback_to_whisper: Whether to fall back to Whisper on failure

        Returns:
            Transcribed text
        """
        try:
            return self.transcribe(audio_path)
        except Exception as e:
            if fallback_to_whisper:
                logger.warning(f"Granite failed: {e}, falling back to Whisper")
                return self._whisper_fallback(audio_path)
            else:
                raise

    def _whisper_fallback(self, audio_path: str) -> str:
        """
        Fallback transcription using Whisper large-v3.

        Args:
            audio_path: Path to audio file

        Returns:
            Transcribed text
        """
        try:
            from faster_whisper import WhisperModel

            logger.info("Loading Whisper large-v3 model...")
            model = WhisperModel(
                "large-v3",
                device=self.device if self.device != "cuda" else "auto",
                compute_type="auto"
            )

            logger.info("Transcribing with Whisper...")
            segments, info = model.transcribe(audio_path)

            # Combine segments
            transcript = " ".join([seg.text for seg in segments])
            logger.info(f"Whisper transcription complete: {len(transcript)} chars")

            return transcript.strip()

        except Exception as e:
            logger.error(f"Whisper fallback failed: {e}")
            raise


def transcribe_parallel(
    audio_path: str,
    num_workers: int = 2,
    model_name: str = "ibm-granite/granite-speech-3.3-2b",
    device: str = "auto"
) -> str:
    """
    Convenience function for parallel transcription.

    Args:
        audio_path: Path to audio file
        num_workers: Number of parallel workers
        model_name: Granite model name
        device: Device to use

    Returns:
        Transcribed text
    """
    transcriber = ParallelTranscriber(
        num_workers=num_workers,
        model_name=model_name,
        device=device
    )
    return transcriber.transcribe(audio_path)


def test_parallel_transcriber():
    """Test parallel transcriber setup."""
    print("=" * 60)
    print("Parallel Transcriber (Granite Speech)")
    print("=" * 60)

    import torch

    device = "GPU (CUDA/ROCm)" if torch.cuda.is_available() else "CPU"
    print(f"\nDevice: {device}")
    print("\nUsage:")
    print("  from modules.parallel_transcriber import ParallelTranscriber")
    print("  transcriber = ParallelTranscriber(num_workers=2)")
    print("  text = transcriber.transcribe('long_audio.wav')")
    print("\nOr with fallback:")
    print("  text = transcriber.transcribe_with_fallback('audio.wav')")


if __name__ == "__main__":
    test_parallel_transcriber()
