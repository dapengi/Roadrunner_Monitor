import logging
import gc
from pathlib import Path

# NOTE: WhisperX is currently not used (Sherpa-ONNX is primary)
# Uncomment these imports if switching to WhisperX:
# import whisperx
# import torch

# Sherpa-ONNX is the primary transcription system

logger = logging.getLogger(__name__)

class WhisperXTranscriber:
    def __init__(self, model_size="large-v3", batch_size=16):
        self.model_size = model_size
        self.batch_size = batch_size
        self.model = None
        self.align_model = None
        self.align_metadata = None
        self.diarize_model = None
        
        # WhisperX doesn't support MPS yet, use CPU with optimizations
        self.device = "cpu"
        self.compute_type = "float32"
        logger.info("Using CPU for WhisperX (MPS not yet supported by WhisperX)")
        
        logger.info(f"WhisperX will use device: {self.device}, compute_type: {self.compute_type}")

    def load_model(self):
        """Load the WhisperX model"""
        if self.model is None:
            logger.info(f"Loading WhisperX model: {self.model_size}")
            try:
                self.model = whisperx.load_model(
                    self.model_size, 
                    self.device, 
                    compute_type=self.compute_type
                )
                logger.info("WhisperX model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load WhisperX model: {e}")
                raise

    def transcribe_audio(self, audio_path):
        """
        Transcribe audio file using WhisperX
        Returns dict with transcription results
        """
        try:
            audio_path = Path(audio_path)
            if not audio_path.exists():
                raise FileNotFoundError(f"Audio file not found: {audio_path}")
            
            logger.info(f"Starting WhisperX transcription for: {audio_path}")
            
            # Load model if not already loaded
            self.load_model()
            
            # Load audio
            logger.info("Loading audio file...")
            audio = whisperx.load_audio(str(audio_path))
            
            # Transcribe
            logger.info("Transcribing audio...")
            result = self.model.transcribe(
                audio, 
                batch_size=self.batch_size,
                language="en"  # Assuming English, adjust as needed
            )
            
            # Skip alignment step for better performance
            logger.info("Skipping alignment step for faster transcription")
            
            # Speaker diarization (requires HF_TOKEN)
            try:
                import os
                hf_token = os.getenv("HF_TOKEN")
                if hf_token:
                    logger.info("Performing speaker diarization...")
                    
                    # Load diarization model only once
                    if self.diarize_model is None:
                        logger.info("Loading speaker diarization model...")
                        from pyannote.audio import Pipeline
                        self.diarize_model = Pipeline.from_pretrained(
                            "pyannote/speaker-diarization-3.1",
                            use_auth_token=hf_token
                        )
                        # Move to device if CUDA available
                        if self.device != "cpu":
                            self.diarize_model.to(torch.device(self.device))
                    
                    # Perform diarization - use file path instead of loaded audio
                    diarize_segments = self.diarize_model(str(audio_path))
                    
                    # Assign speakers to words using WhisperX function
                    result = whisperx.assign_word_speakers(diarize_segments, result)
                    logger.info("Speaker diarization completed")
                else:
                    logger.info("No HF_TOKEN found, skipping speaker diarization")
                    
            except Exception as e:
                logger.warning(f"Speaker diarization failed: {e}")
            
            # Clean up GPU memory
            if hasattr(self, 'align_model') and self.align_model:
                del self.align_model
                self.align_model = None
            
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            logger.info("WhisperX transcription completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Error in WhisperX transcription process: {e}")
            raise

    def format_transcript(self, result):
        """
        Format the transcription result into readable text
        """
        try:
            segments = result.get("segments", [])
            if not segments:
                return "No transcription available."
            
            transcript_lines = []
            
            for segment in segments:
                start_time = segment.get("start", 0)
                end_time = segment.get("end", 0)
                text = segment.get("text", "").strip()
                speaker = segment.get("speaker", "Unknown")
                
                # Format timestamp
                start_min = int(start_time // 60)
                start_sec = int(start_time % 60)
                end_min = int(end_time // 60)
                end_sec = int(end_time % 60)
                
                timestamp = f"[{start_min:02d}:{start_sec:02d} - {end_min:02d}:{end_sec:02d}]"
                
                if "speaker" in segment:
                    line = f"{timestamp} {speaker}: {text}"
                else:
                    line = f"{timestamp} {text}"
                
                transcript_lines.append(line)
            
            return "\n".join(transcript_lines)
            
        except Exception as e:
            logger.error(f"Error formatting transcript: {e}")
            return "Error formatting transcription."

def transcribe_audio_file(audio_path, model_size="large-v3"):
    """
    Convenience function to transcribe an audio file
    """
    transcriber = WhisperXTranscriber(model_size=model_size)
    result = transcriber.transcribe_audio(audio_path)
    formatted_transcript = transcriber.format_transcript(result)
    return formatted_transcript, result

# Compatibility function for existing import
# Global transcriber instance for caching
_global_transcriber = None

def get_transcriber(model_size="medium"):
    """Get or create a cached transcriber instance"""
    global _global_transcriber
    if _global_transcriber is None or _global_transcriber.model_size != model_size:
        _global_transcriber = WhisperXTranscriber(model_size=model_size)
    return _global_transcriber

def transcribe_with_whisperx(audio_path, model_size="medium", include_timestamps=True, committee_members=None, engine="canary"):
    """
    Transcribe audio with speaker diarization.

    Supports two engines:
    - "canary": NVIDIA Canary (high accuracy, best for production)
    - "whisper": faster-whisper (fallback, good for development)

    Args:
        audio_path: Path to audio file
        model_size: Model size to use (for whisper engine)
        include_timestamps: Whether to include timestamps in output
        committee_members: Optional list of committee member names for speaker identification
        engine: Transcription engine ("canary" or "whisper")
    """
    # Try Canary first if requested
    if engine == "canary":
        try:
            from modules.canary_diarization import transcribe_with_canary_and_diarization
            logger.info(f"Using NVIDIA Canary for transcription: {audio_path}")
            return transcribe_with_canary_and_diarization(
                audio_path,
                device="cpu",  # Will auto-detect GPU if available
                include_timestamps=include_timestamps
            )
        except ImportError as e:
            logger.warning(f"Canary not available, falling back to Whisper: {e}")
            engine = "whisper"  # Fall through to Whisper
        except Exception as e:
            logger.error(f"Canary failed, falling back to Whisper: {e}")
            engine = "whisper"  # Fall through to Whisper

    # Use Whisper (original implementation)
    if engine == "whisper":
        logger.info(f"Using faster-whisper for transcription: {audio_path}")
    
    # Map model sizes to faster-whisper format
    model_mapping = {
        "tiny": "tiny.en",
        "base": "base.en", 
        "small": "small.en",
        "medium": "base.en",      # Use base.en for faster processing
        "large": "small.en",      # Use small.en for faster processing
        "large-v2": "small.en",   # Use small.en for faster processing
        "large-v3": "small.en"    # Use small.en for faster processing
    }
    
    whisper_model = model_mapping.get(model_size, "base.en")
    
    try:
        # Try Sherpa-ONNX approach first (most accurate, no authentication required)
        from .sherpa_diarization import transcribe_with_sherpa_diarization
        formatted_transcript = transcribe_with_sherpa_diarization(
            audio_path, 
            whisper_model, 
            include_timestamps=include_timestamps
        )
        
        # Apply speaker identification if committee members are provided
        if committee_members and formatted_transcript:
            from .speaker_id import identify_speakers_in_transcript
            enhanced_transcript = identify_speakers_in_transcript(formatted_transcript, committee_members)
            logger.info("Applied speaker identification to Sherpa-ONNX transcript")
            return enhanced_transcript
        
        logger.info("Sherpa-ONNX based transcription with speaker diarization completed successfully")
        return formatted_transcript
        
    except Exception as e:
        logger.error(f"Sherpa-ONNX based transcription failed: {e}")
        logger.warning("No fallback transcription methods available. Please check Sherpa-ONNX setup.")
        return "Transcription failed - Sherpa-ONNX system unavailable."