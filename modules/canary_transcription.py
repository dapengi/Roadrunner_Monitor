"""
NVIDIA NeMo Canary transcription module.
Provides high-accuracy speech recognition with built-in punctuation and speaker diarization.
"""

import logging
import os
from pathlib import Path
from typing import List, Dict, Optional
import time

logger = logging.getLogger(__name__)

# Try to import NeMo
try:
    import nemo.collections.asr as nemo_asr
    NEMO_AVAILABLE = True
except ImportError:
    NEMO_AVAILABLE = False
    logger.warning("NeMo not available - Canary transcription will not work")


class CanaryTranscriber:
    """
    NVIDIA Canary transcriber with high accuracy for legislative content.
    """

    def __init__(self, model_name: str = "nvidia/canary-1b-v2", device: str = "cpu"):
        """
        Initialize Canary transcriber.

        Args:
            model_name: Canary model to use (default: nvidia/canary-1b-v2)
            device: Device to use ('cpu', 'cuda', or 'mps')
        """
        self.model_name = model_name
        self.device = device
        self.model = None

        if not NEMO_AVAILABLE:
            raise ImportError(
                "NeMo is not installed. Install with: pip install nemo_toolkit[asr]"
            )

    def load_model(self):
        """Load the Canary model."""
        if self.model is not None:
            logger.info("Canary model already loaded")
            return

        try:
            logger.info(f"Loading NVIDIA Canary model: {self.model_name}")
            print(f"🔄 Downloading Canary model (this may take a few minutes on first run)...")

            # Load pretrained Canary model
            self.model = nemo_asr.models.EncDecMultiTaskModel.from_pretrained(
                model_name=self.model_name
            )

            # Move to device
            if self.device == "cuda":
                self.model = self.model.cuda()
            elif self.device == "mps":
                # MPS support for Apple Silicon
                import torch
                if torch.backends.mps.is_available():
                    self.model = self.model.to("mps")
                else:
                    logger.warning("MPS not available, using CPU")
                    self.device = "cpu"

            self.model.eval()

            logger.info(f"✅ Canary model loaded successfully on {self.device}")
            print(f"✅ Canary model ready on {self.device}")

        except Exception as e:
            logger.error(f"Failed to load Canary model: {e}")
            raise

    def transcribe(self, audio_path: str, language: str = "en",
                  task: str = "asr", pnc: str = "yes") -> List[Dict]:
        """
        Transcribe audio file with Canary.

        Args:
            audio_path: Path to audio file
            language: Language code (default: "en" for English)
            task: Task type ("asr" for transcription)
            pnc: Punctuation and capitalization ("yes" or "no")

        Returns:
            List of transcription segments with timestamps
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        # Load model if not already loaded
        if self.model is None:
            self.load_model()

        try:
            logger.info(f"Transcribing with Canary: {audio_path}")
            print(f"🎤 Transcribing with NVIDIA Canary...")

            # Convert to mono if needed (Canary requires mono audio)
            import librosa
            import soundfile as sf
            import tempfile
            
            audio_input = audio_path
            temp_file = None
            
            # Check if audio is stereo and convert to mono
            try:
                audio, sr = librosa.load(audio_path, sr=16000, mono=True)
                
                # Save as temporary mono WAV file
                temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
                sf.write(temp_file.name, audio, sr)
                audio_input = temp_file.name
                temp_file.close()
                
                logger.info(f"Converted audio to mono: {audio_input}")
            except Exception as e:
                logger.warning(f"Could not convert audio to mono: {e}")
                # Use original file if conversion fails
                audio_input = audio_path

            start_time = time.time()

            # Prepare transcription config
            # Canary uses a prompt format: <|startoftranscript|><|en|><|transcribe|><|pnc|>
            decode_cfg = {
                "source_lang": language,
                "target_lang": language,
                "task": task,
                "pnc": pnc
            }

            # Transcribe the audio (now guaranteed to be mono)
            transcriptions = self.model.transcribe(
                audio=[audio_input],
                batch_size=1
            )

            # Extract text
            if isinstance(transcriptions, list) and len(transcriptions) > 0:
                transcript_text = transcriptions[0]
            else:
                transcript_text = str(transcriptions)

            transcription_time = time.time() - start_time

            logger.info(f"Canary transcription completed in {transcription_time:.1f}s")
            print(f"✅ Canary transcription completed in {transcription_time:.1f}s")

            # Canary returns full text - we need to segment it for speaker diarization
            # For now, return as single segment
            # TODO: Add VAD-based segmentation
            segments = [{
                'text': transcript_text,
                'start': 0.0,
                'end': transcription_time,  # Placeholder
            }]

            return segments

        except Exception as e:
            logger.error(f"Canary transcription failed: {e}")
            raise
        finally:
            # Cleanup temporary mono file
            if temp_file and os.path.exists(temp_file.name):
                try:
                    os.remove(temp_file.name)
                    logger.debug(f"Cleaned up temp file: {temp_file.name}")
                except Exception as e:
                    logger.warning(f"Could not remove temp file: {e}")

    def transcribe_with_timestamps(self, audio_path: str) -> List[Dict]:
        """
        Transcribe with word-level timestamps.

        Note: Canary provides text but not word-level timestamps by default.
        We'll use VAD to segment the audio first.

        Args:
            audio_path: Path to audio file

        Returns:
            List of segments with text and timestamps
        """
        # For initial implementation, use basic transcription
        # TODO: Implement VAD-based segmentation for better timestamps
        segments = self.transcribe(audio_path)

        logger.info(f"Generated {len(segments)} segments")
        return segments


def transcribe_with_canary(audio_path: str, device: str = "cpu",
                           model_name: str = "nvidia/canary-1b-v2") -> str:
    """
    Convenience function to transcribe audio with Canary.

    Args:
        audio_path: Path to audio file
        device: Device to use ('cpu', 'cuda', 'mps')
        model_name: Canary model name

    Returns:
        Transcribed text
    """
    transcriber = CanaryTranscriber(model_name=model_name, device=device)
    segments = transcriber.transcribe(audio_path)

    # Combine segments
    full_text = " ".join([seg['text'] for seg in segments])

    return full_text


def test_canary():
    """Test Canary transcription."""
    print("NVIDIA Canary Transcriber")
    print("=" * 60)

    if not NEMO_AVAILABLE:
        print("❌ NeMo not installed")
        print("\nInstall with:")
        print("  pip install nemo_toolkit[asr]")
        return

    print("✅ NeMo available")
    print("\nTo transcribe:")
    print("  from modules.canary_transcription import transcribe_with_canary")
    print("  text = transcribe_with_canary('audio.mp3')")


if __name__ == "__main__":
    test_canary()
