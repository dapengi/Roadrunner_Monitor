"""
IBM Granite Speech 3.3-8B transcription module.
Provides high-accuracy speech recognition optimized for AMD hardware with ROCm support.
"""

import logging
import os
import tempfile
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
# Ensure .env is loaded for HF_TOKEN
load_dotenv()

import torch
import torchaudio

logger = logging.getLogger(__name__)

# Check for transformers availability
try:
    from transformers import AutoProcessor, AutoModelForSpeechSeq2Seq
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logger.warning("transformers not available - Granite transcription will not work")


class GraniteTranscriber:
    """
    IBM Granite Speech 3.3-8B transcriber.
    Optimized for AMD ROCm and CPU inference.
    """

    def __init__(
        self,
        model_name: str = "ibm-granite/granite-speech-3.3-8b",
        device: str = "auto",
        dtype: Optional[torch.dtype] = None
    ):
        """
        Initialize Granite transcriber.

        Args:
            model_name: HuggingFace model name (default: ibm-granite/granite-speech-3.3-8b)
            device: Device to use ('auto', 'cuda', 'cpu'). Auto detects ROCm as 'cuda'.
            dtype: Model dtype (default: bfloat16 for efficiency)
        """
        if not TRANSFORMERS_AVAILABLE:
            raise ImportError(
                "transformers is not installed. Install with: pip install transformers>=4.52.4 peft"
            )

        self.model_name = model_name
        self.device = self._resolve_device(device)
        self.dtype = dtype or torch.bfloat16
        self.model = None
        self.processor = None
        self.tokenizer = None

    def _resolve_device(self, device: str) -> str:
        """Resolve device string to actual device."""
        if device == "auto":
            # torch.cuda.is_available() returns True for both CUDA and ROCm
            if torch.cuda.is_available():
                logger.info("GPU detected (CUDA/ROCm)")
                return "cuda"
            else:
                logger.info("No GPU detected, using CPU")
                return "cpu"
        return device

    def load_model(self):
        """Load the Granite model and processor."""
        if self.model is not None:
            logger.info("Granite model already loaded")
            return

        try:
            logger.info(f"Loading Granite Speech model: {self.model_name}")
            logger.info(f"Device: {self.device}, dtype: {self.dtype}")

            # Get HuggingFace token (optional - Granite models are not gated)
            hf_token = os.getenv("HF_TOKEN")
            if hf_token:
                logger.info("Using HuggingFace token for authentication")

            # Load processor and tokenizer
            self.processor = AutoProcessor.from_pretrained(
                self.model_name,
                token=hf_token
            )
            self.tokenizer = self.processor.tokenizer

            # Load model with appropriate settings
            self.model = AutoModelForSpeechSeq2Seq.from_pretrained(
                self.model_name,
                device_map=self.device,
                torch_dtype=self.dtype,
                token=hf_token
            )

            logger.info(f"Granite model loaded successfully on {self.device}")

        except Exception as e:
            logger.error(f"Failed to load Granite model: {e}")
            raise

    def _load_audio(self, audio_path: str) -> torch.Tensor:
        """
        Load and preprocess audio file.
        Granite requires mono 16kHz audio.

        Args:
            audio_path: Path to audio file

        Returns:
            Preprocessed audio tensor
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        # Try multiple backends to avoid torchcodec dependency
        wav = None
        sr = None

        # Try soundfile backend first (no torchcodec needed)
        try:
            wav, sr = torchaudio.load(audio_path, normalize=True, backend="soundfile")
        except (RuntimeError, TypeError):
            pass

        # Try sox backend if soundfile failed
        if wav is None:
            try:
                wav, sr = torchaudio.load(audio_path, normalize=True, backend="sox")
            except (RuntimeError, TypeError):
                pass

        # Fall back to librosa + torch conversion
        if wav is None:
            import librosa
            audio_np, sr = librosa.load(audio_path, sr=16000, mono=True)
            wav = torch.from_numpy(audio_np).unsqueeze(0)
            sr = 16000

        # Resample to 16kHz if needed
        if sr != 16000:
            resampler = torchaudio.transforms.Resample(sr, 16000)
            wav = resampler(wav)

        # Convert to mono if stereo
        if wav.shape[0] > 1:
            wav = wav.mean(dim=0, keepdim=True)

        return wav

    def transcribe(self, audio_path: str, max_new_tokens: int = 4096) -> str:
        """
        Transcribe an audio file.

        Args:
            audio_path: Path to audio file (supports WAV, MP3, etc.)
            max_new_tokens: Maximum tokens to generate

        Returns:
            Transcribed text
        """
        # Load model if not already loaded
        if self.model is None:
            self.load_model()

        try:
            logger.info(f"Transcribing: {audio_path}")

            # Load and preprocess audio
            wav = self._load_audio(audio_path)

            # Create chat-style prompt for transcription
            system_prompt = "You are a helpful assistant that transcribes speech accurately."
            user_prompt = "<|audio|>Transcribe the speech verbatim."

            chat = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]

            prompt = self.tokenizer.apply_chat_template(
                chat,
                tokenize=False,
                add_generation_prompt=True
            )

            # Process inputs
            model_inputs = self.processor(
                prompt,
                wav,
                device=self.device,
                return_tensors="pt"
            ).to(self.device)

            # Generate transcription
            with torch.no_grad():
                outputs = self.model.generate(
                    **model_inputs,
                    max_new_tokens=max_new_tokens,
                    do_sample=False,
                    num_beams=1
                )

            # Decode output (skip input tokens)
            num_input_tokens = model_inputs["input_ids"].shape[-1]
            new_tokens = outputs[0, num_input_tokens:]
            transcript = self.tokenizer.decode(new_tokens, skip_special_tokens=True)

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


def transcribe_with_granite(
    audio_path: str,
    device: str = "auto",
    model_name: str = "ibm-granite/granite-speech-3.3-8b"
) -> str:
    """
    Convenience function to transcribe audio with Granite.

    Args:
        audio_path: Path to audio file
        device: Device to use ('auto', 'cuda', 'cpu')
        model_name: Granite model name

    Returns:
        Transcribed text
    """
    transcriber = GraniteTranscriber(model_name=model_name, device=device)
    return transcriber.transcribe(audio_path)


def test_granite():
    """Test Granite transcription setup."""
    print("=" * 60)
    print("IBM Granite Speech 3.3-8B Transcriber")
    print("=" * 60)

    if not TRANSFORMERS_AVAILABLE:
        print("transformers not installed")
        print("\nInstall with:")
        print("  pip install transformers>=4.52.4 peft")
        return

    print("transformers available")

    # Check device
    if torch.cuda.is_available():
        device_name = torch.cuda.get_device_name(0)
        print(f"GPU available: {device_name}")
    else:
        print("No GPU detected, will use CPU")

    print("\nTo transcribe:")
    print("  from modules.granite_transcription import transcribe_with_granite")
    print("  text = transcribe_with_granite('audio.wav')")


if __name__ == "__main__":
    test_granite()
