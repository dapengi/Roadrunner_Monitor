"""
NVIDIA Parakeet TDT 0.6b-v2 transcription module.
Provides fast, accurate speech recognition via ONNX Runtime.
Achieves ~60x faster than real-time on CPU with clean output.
"""

import logging
import os
import tempfile
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

# Check for onnx_asr availability
try:
    import onnx_asr
    ONNX_ASR_AVAILABLE = True
except ImportError:
    ONNX_ASR_AVAILABLE = False
    logger.warning("onnx_asr not available - Parakeet transcription will not work")

# Check for soundfile availability
try:
    import soundfile as sf
    import numpy as np
    SOUNDFILE_AVAILABLE = True
except ImportError:
    SOUNDFILE_AVAILABLE = False
    logger.warning("soundfile not available - audio loading may fail")


class ParakeetTranscriber:
    """
    NVIDIA Parakeet TDT 0.6b-v2 transcriber.
    Uses ONNX Runtime for fast CPU/GPU inference.
    """

    def __init__(
        self,
        model_name: str = "nemo-parakeet-tdt-0.6b-v2",
        device: str = "cpu",
        chunk_duration: int = 60
    ):
        """
        Initialize Parakeet transcriber.

        Args:
            model_name: ONNX ASR model name (default: nemo-parakeet-tdt-0.6b-v2)
            device: Device to use ('cpu', 'migraphx'). Default CPU is very fast.
            chunk_duration: Duration of audio chunks in seconds (default: 60)
        """
        if not ONNX_ASR_AVAILABLE:
            raise ImportError(
                "onnx_asr is not installed. Install with: pip install onnx-asr"
            )

        if not SOUNDFILE_AVAILABLE:
            raise ImportError(
                "soundfile is not installed. Install with: pip install soundfile"
            )

        self.model_name = model_name
        self.device = device
        self.chunk_duration = chunk_duration
        self.model = None
        self.sample_rate = 16000  # Parakeet expects 16kHz audio

    def _get_providers(self) -> List[str]:
        """Get ONNX Runtime execution providers based on device setting."""
        if self.device == "migraphx":
            return ["MIGraphXExecutionProvider", "CPUExecutionProvider"]
        elif self.device == "cuda":
            return ["CUDAExecutionProvider", "CPUExecutionProvider"]
        else:
            return ["CPUExecutionProvider"]

    def load_model(self):
        """Load the Parakeet model."""
        if self.model is not None:
            logger.info("Parakeet model already loaded")
            return

        try:
            providers = self._get_providers()
            logger.info(f"Loading Parakeet model: {self.model_name}")
            logger.info(f"Execution providers: {providers}")

            self.model = onnx_asr.load_model(
                self.model_name,
                providers=providers
            )

            logger.info("Parakeet model loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load Parakeet model: {e}")
            raise

    def _load_audio(self, audio_path: str) -> tuple:
        """
        Load and preprocess audio file.
        Parakeet requires mono 16kHz audio.

        Args:
            audio_path: Path to audio file

        Returns:
            Tuple of (audio_data, sample_rate)
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        # Load audio with soundfile
        data, sr = sf.read(audio_path)

        # Convert to mono if stereo
        if len(data.shape) > 1:
            data = np.mean(data, axis=1)

        # Resample to 16kHz if needed
        if sr != self.sample_rate:
            try:
                import scipy.signal
                duration = len(data) / sr
                new_length = int(duration * self.sample_rate)
                data = scipy.signal.resample(data, new_length)
                sr = self.sample_rate
                logger.info(f"Resampled audio to {self.sample_rate}Hz")
            except ImportError:
                logger.warning("scipy not available for resampling")

        return data, sr

    def _chunk_audio(self, audio_data: np.ndarray, sample_rate: int) -> List[np.ndarray]:
        """
        Split audio into chunks for processing.

        Args:
            audio_data: Audio samples
            sample_rate: Sample rate

        Returns:
            List of audio chunks
        """
        chunk_size = self.chunk_duration * sample_rate
        chunks = []

        for i in range(0, len(audio_data), chunk_size):
            chunk = audio_data[i:i + chunk_size]
            if len(chunk) > sample_rate:  # Skip chunks less than 1 second
                chunks.append(chunk)

        return chunks

    def transcribe(self, audio_path: str) -> str:
        """
        Transcribe an audio file.

        Args:
            audio_path: Path to audio file (supports WAV, MP3, etc.)

        Returns:
            Transcribed text
        """
        # Load model if not already loaded
        if self.model is None:
            self.load_model()

        try:
            logger.info(f"Transcribing: {audio_path}")

            # Load audio
            audio_data, sr = self._load_audio(audio_path)
            duration = len(audio_data) / sr
            logger.info(f"Audio duration: {duration/60:.1f} minutes")

            # Check if audio needs chunking
            if duration > self.chunk_duration:
                # Chunk long audio
                chunks = self._chunk_audio(audio_data, sr)
                logger.info(f"Split audio into {len(chunks)} chunks")

                transcripts = []
                for i, chunk in enumerate(chunks):
                    # Write chunk to temp file
                    chunk_path = f"/tmp/parakeet_chunk_{i}.wav"
                    sf.write(chunk_path, chunk, sr)

                    # Transcribe chunk
                    try:
                        result = self.model.recognize(chunk_path)
                        transcripts.append(result)
                        logger.debug(f"Chunk {i+1}/{len(chunks)}: {len(result)} chars")
                    finally:
                        # Cleanup chunk file
                        if os.path.exists(chunk_path):
                            os.remove(chunk_path)

                transcript = " ".join(transcripts)
            else:
                # Short audio - transcribe directly
                # Need to convert to WAV if not already
                if not audio_path.lower().endswith('.wav'):
                    temp_wav = "/tmp/parakeet_input.wav"
                    sf.write(temp_wav, audio_data, sr)
                    transcript = self.model.recognize(temp_wav)
                    os.remove(temp_wav)
                else:
                    transcript = self.model.recognize(audio_path)

            logger.info(f"Transcription complete: {len(transcript)} characters")
            return transcript.strip()

        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise

    def transcribe_chunk(self, audio_path: str, start_time: float) -> dict:
        """
        Transcribe an audio chunk with timing information.

        Args:
            audio_path: Path to audio chunk file
            start_time: Start time offset in seconds

        Returns:
            Dict with transcript and timing info
        """
        transcript = self.transcribe(audio_path)

        return {
            "start_time": start_time,
            "transcript": transcript,
            "chunk_path": audio_path
        }


def transcribe_with_parakeet(
    audio_path: str,
    device: str = "cpu",
    model_name: str = "nemo-parakeet-tdt-0.6b-v2",
    chunk_duration: int = 60
) -> str:
    """
    Convenience function to transcribe audio with Parakeet.

    Args:
        audio_path: Path to audio file
        device: Device to use ('cpu', 'migraphx', 'cuda')
        model_name: Parakeet model name
        chunk_duration: Duration of audio chunks in seconds

    Returns:
        Transcribed text
    """
    transcriber = ParakeetTranscriber(
        model_name=model_name,
        device=device,
        chunk_duration=chunk_duration
    )
    return transcriber.transcribe(audio_path)


def test_parakeet():
    """Test Parakeet transcription setup."""
    print("=" * 60)
    print("NVIDIA Parakeet TDT 0.6b-v2 Transcriber")
    print("=" * 60)

    if not ONNX_ASR_AVAILABLE:
        print("onnx_asr not installed")
        print("\nInstall with:")
        print("  pip install onnx-asr")
        return

    print("onnx_asr available")

    if not SOUNDFILE_AVAILABLE:
        print("soundfile not installed")
        print("\nInstall with:")
        print("  pip install soundfile")
        return

    print("soundfile available")

    # Check ONNX providers
    try:
        import onnxruntime as ort
        providers = ort.get_available_providers()
        print(f"\nAvailable ONNX providers: {providers}")
    except ImportError:
        print("\nonnxruntime not installed")

    print("\nTo transcribe:")
    print("  from modules.parakeet_transcription import transcribe_with_parakeet")
    print("  text = transcribe_with_parakeet('audio.wav')")
    print("\nPerformance: ~60x faster than real-time on CPU")


if __name__ == "__main__":
    test_parakeet()
