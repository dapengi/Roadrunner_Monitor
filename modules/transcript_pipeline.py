"""
Integrated transcript pipeline with multiple transcription backends.
Optimized for AMD hardware with ROCm support.

Primary: NVIDIA Parakeet TDT 0.6b-v2 (60x faster than real-time via ONNX)
Alternative: IBM Granite Speech 3.3-2B (parallel processing)
Fallback: Whisper Large-v3
Diarization: Pyannote 3.1 (improved accuracy for many speakers)
"""

import logging
import os
import traceback
from datetime import datetime
from typing import Dict, List, Optional

from dotenv import load_dotenv
# Ensure .env is loaded for GRANITE_DEVICE and other settings
load_dotenv()

import librosa

from modules.audio_event_detector import AudioEventDetector
from modules.transcript_formatters import TranscriptFormatter
from modules.transcript_uploader import TranscriptUploader
from modules.video_processor import download_video, extract_audio_from_video

logger = logging.getLogger(__name__)


class TranscriptPipeline:
    """
    Complete pipeline for processing legislative meeting transcripts.
    Uses Parakeet/Granite/Whisper transcription with Pyannote diarization.
    """

    def __init__(self, transcriber: str = "parakeet", num_workers: int = 2, device: str = None):
        """
        Initialize the pipeline components.

        Args:
            transcriber: Transcription engine ('parakeet', 'granite', or 'whisper')
            num_workers: Number of parallel workers for Granite
            device: Device to use ('auto', 'cuda', 'cpu', 'migraphx'). If None, reads from env.
        """
        self.transcriber = transcriber
        self.num_workers = num_workers
        # Get device from parameter or environment
        self.device = device or os.getenv("GRANITE_DEVICE", "auto")
        self.event_detector = AudioEventDetector()
        self.formatter = TranscriptFormatter()
        self.uploader = TranscriptUploader()

        logger.info(f"Pipeline initialized: transcriber={transcriber}, workers={num_workers}, device={self.device}")

    def _transcribe_with_parakeet(self, audio_path: str) -> str:
        """
        Transcribe audio using NVIDIA Parakeet TDT 0.6b-v2 via ONNX.
        Achieves ~60x faster than real-time on CPU with clean output.

        Args:
            audio_path: Path to audio file

        Returns:
            Transcribed text
        """
        from modules.parakeet_transcription import ParakeetTranscriber

        # Map device setting: 'cuda' -> 'cpu' for Parakeet (CPU is fast enough)
        # 'migraphx' can be used for AMD GPU acceleration
        parakeet_device = "cpu"
        if self.device == "migraphx":
            parakeet_device = "migraphx"

        transcriber = ParakeetTranscriber(
            device=parakeet_device,
            chunk_duration=60  # 60-second chunks work well
        )
        return transcriber.transcribe(audio_path)

    def _transcribe_with_granite(self, audio_path: str) -> str:
        """
        Transcribe audio using Granite Speech with parallel processing.

        Args:
            audio_path: Path to audio file

        Returns:
            Transcribed text
        """
        from modules.parallel_transcriber import ParallelTranscriber

        transcriber = ParallelTranscriber(
            num_workers=self.num_workers,
            device=self.device
        )
        return transcriber.transcribe(audio_path)

    def _transcribe_with_whisper(self, audio_path: str) -> str:
        """
        Transcribe audio using Whisper Large-v3 (fallback).

        Args:
            audio_path: Path to audio file

        Returns:
            Transcribed text
        """
        try:
            from faster_whisper import WhisperModel

            logger.info("Loading Whisper large-v3 model...")
            model = WhisperModel("large-v3", device="auto", compute_type="auto")

            logger.info("Transcribing with Whisper...")
            segments, info = model.transcribe(audio_path)

            # Combine all segments
            transcript = " ".join([seg.text for seg in segments])
            logger.info(f"Whisper transcription complete: {len(transcript)} chars")

            return transcript.strip()

        except Exception as e:
            logger.error(f"Whisper transcription failed: {e}")
            raise

    def _diarize_audio(self, audio_path: str) -> List[Dict]:
        """
        Perform speaker diarization using Pyannote 3.1.

        Args:
            audio_path: Path to audio file

        Returns:
            List of speaker segments
        """
        from modules.pyannote_diarization import PyannoteDiarizer

        diarizer = PyannoteDiarizer(device="cpu", max_speakers=25)
        return diarizer.diarize(audio_path)

    def _align_transcript_with_diarization(
        self,
        transcript: str,
        diarization_segments: List[Dict],
        audio_duration: float
    ) -> List[Dict]:
        """
        Align transcript text with diarization segments.

        Args:
            transcript: Full transcript text
            diarization_segments: Speaker diarization results
            audio_duration: Total audio duration in seconds

        Returns:
            List of segments with speaker, text, start, end
        """
        if not diarization_segments:
            # No diarization, return as single segment
            return [{
                'speaker': 'Speaker A',
                'text': transcript,
                'start': 0.0,
                'end': audio_duration
            }]

        # Split transcript proportionally across diarization segments
        words = transcript.split()
        total_words = len(words)

        if total_words == 0:
            return diarization_segments

        # Calculate total speaking duration
        total_duration = sum(seg['end'] - seg['start'] for seg in diarization_segments)

        if total_duration == 0:
            return diarization_segments

        words_per_second = total_words / total_duration

        segments = []
        word_idx = 0

        for seg in diarization_segments:
            seg_duration = seg['end'] - seg['start']
            seg_word_count = int(seg_duration * words_per_second)

            # Get words for this segment
            seg_words = words[word_idx:word_idx + seg_word_count]
            word_idx += seg_word_count

            if seg_words:
                segments.append({
                    'speaker': seg['speaker'],
                    'text': ' '.join(seg_words),
                    'start': seg['start'],
                    'end': seg['end']
                })

        # Add any remaining words to last segment
        if word_idx < len(words) and segments:
            remaining = ' '.join(words[word_idx:])
            segments[-1]['text'] += ' ' + remaining

        return segments

    def _format_transcript_text(self, segments: List[Dict]) -> str:
        """
        Format segments into readable transcript text.

        Args:
            segments: List of segment dictionaries

        Returns:
            Formatted transcript string
        """
        lines = []

        for seg in segments:
            start_min = int(seg['start'] // 60)
            start_sec = int(seg['start'] % 60)
            end_min = int(seg['end'] // 60)
            end_sec = int(seg['end'] % 60)

            # Support hours for long meetings
            if seg['end'] >= 3600:
                start_hr = int(seg['start'] // 3600)
                start_min = int((seg['start'] % 3600) // 60)
                end_hr = int(seg['end'] // 3600)
                end_min = int((seg['end'] % 3600) // 60)
                timestamp = f"[{start_hr:02d}:{start_min:02d}:{start_sec:02d} - {end_hr:02d}:{end_min:02d}:{end_sec:02d}]"
            else:
                timestamp = f"[{start_min:02d}:{start_sec:02d} - {end_min:02d}:{end_sec:02d}]"

            lines.append(f"{timestamp} {seg['speaker']}: {seg['text']}")

        return '\n\n'.join(lines)

    def extract_segments_from_transcript(self, transcript_text: str) -> List[Dict]:
        """
        Extract structured segments from formatted transcript text.

        Parses format: "[MM:SS - MM:SS] Speaker X: Text here"
        Also supports: "[HH:MM:SS - HH:MM:SS] Speaker X: Text here"

        Args:
            transcript_text: Formatted transcript text

        Returns:
            List of segment dictionaries
        """
        segments = []
        lines = transcript_text.strip().split('\n\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            try:
                if line.startswith('['):
                    end_bracket = line.index(']')
                    timestamp_str = line[1:end_bracket]

                    times = timestamp_str.split(' - ')
                    if len(times) == 2:
                        # Parse timestamp - supports MM:SS and HH:MM:SS
                        def parse_timestamp(ts: str) -> int:
                            parts = ts.split(':')
                            if len(parts) == 2:  # MM:SS
                                return int(parts[0]) * 60 + int(parts[1])
                            elif len(parts) == 3:  # HH:MM:SS
                                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                            return 0

                        start_seconds = parse_timestamp(times[0])
                        end_seconds = parse_timestamp(times[1])

                        remainder = line[end_bracket + 1:].strip()

                        if ':' in remainder:
                            speaker_part, text = remainder.split(':', 1)
                            speaker = speaker_part.strip()
                            text = text.strip()

                            segments.append({
                                'speaker': speaker,
                                'text': text,
                                'start': float(start_seconds),
                                'end': float(end_seconds)
                            })

            except Exception as e:
                logger.warning(f"Could not parse line: {line[:50]}... Error: {e}")
                continue

        logger.info(f"Extracted {len(segments)} segments from transcript")
        return segments

    def process_meeting(
        self,
        audio_path: str,
        committee: str,
        meeting_date: datetime,
        start_time: str = None,
        end_time: str = None,
        committee_type: str = "Interim",
        upload_to_seafile: bool = True
    ) -> Dict:
        """
        Process a complete meeting: transcribe, diarize, format, upload.

        Args:
            audio_path: Path to audio file (MP3 or WAV)
            committee: Committee acronym (e.g., "CCJ", "LFC")
            meeting_date: Date of the meeting
            start_time: Meeting start time (e.g., "9:14 AM")
            end_time: Meeting end time (e.g., "12:06 PM")
            committee_type: Type ("Interim", "House", "Senate")
            upload_to_seafile: Whether to upload to Seafile

        Returns:
            Dictionary with results and file paths
        """
        logger.info(f"Processing meeting: {committee} on {meeting_date}")
        logger.info(f"Transcriber: {self.transcriber}, Workers: {self.num_workers}")

        try:
            # Get audio duration
            audio, sr = librosa.load(audio_path, sr=16000, mono=True)
            audio_duration = len(audio) / sr
            logger.info(f"Audio duration: {audio_duration/60:.1f} minutes")

            # Step 1: Transcribe audio
            logger.info(f"Step 1/4: Transcribing with {self.transcriber.upper()}...")

            if self.transcriber == "parakeet":
                try:
                    transcript_text = self._transcribe_with_parakeet(audio_path)
                except Exception as e:
                    logger.warning(f"Parakeet failed: {e}, falling back to Whisper")
                    transcript_text = self._transcribe_with_whisper(audio_path)
            elif self.transcriber == "granite":
                try:
                    transcript_text = self._transcribe_with_granite(audio_path)
                except Exception as e:
                    logger.warning(f"Granite failed: {e}, falling back to Whisper")
                    transcript_text = self._transcribe_with_whisper(audio_path)
            else:
                transcript_text = self._transcribe_with_whisper(audio_path)

            if not transcript_text:
                logger.error("Transcription failed - no text returned")
                return {'success': False, 'error': 'Transcription failed'}

            logger.info(f"Transcription complete: {len(transcript_text)} characters")

            # Step 2: Speaker diarization with Pyannote
            logger.info("Step 2/4: Speaker diarization with Pyannote...")
            try:
                diarization_segments = self._diarize_audio(audio_path)
                logger.info(f"Diarization complete: {len(diarization_segments)} segments")
            except Exception as e:
                logger.warning(f"Diarization failed: {e}, using single speaker")
                diarization_segments = []

            # Align transcript with diarization
            segments = self._align_transcript_with_diarization(
                transcript_text,
                diarization_segments,
                audio_duration
            )

            if not segments:
                logger.error("No segments extracted from transcript")
                return {'success': False, 'error': 'No segments extracted'}

            # Create formatted transcript text
            formatted_transcript = self._format_transcript_text(segments)

            # Step 3: Format transcripts (JSON, CSV, TXT)
            logger.info("Step 3/4: Formatting transcripts...")
            audio_events = []  # Audio events disabled for legislative meetings
            formatted_transcripts = self.formatter.format_all(segments, audio_events)
            logger.info(f"Generated {len(formatted_transcripts)} transcript formats")

            # Step 4: Upload to Seafile
            upload_result = None
            if upload_to_seafile:
                logger.info("Step 4/4: Uploading to Seafile...")
                upload_result = self.uploader.upload_transcripts(
                    formatted_transcripts,
                    committee,
                    meeting_date,
                    start_time,
                    end_time,
                    committee_type
                )

                if upload_result['success']:
                    logger.info(f"Upload successful: {upload_result['folder_path']}")
                else:
                    logger.error(f"Upload failed: {upload_result.get('errors', 'Unknown')}")
            else:
                logger.info("Step 4/4: Skipping Seafile upload (disabled)")

            return {
                'success': True,
                'segments': segments,
                'audio_events': audio_events,
                'formatted_transcripts': formatted_transcripts,
                'upload_result': upload_result,
                'raw_transcript': formatted_transcript,
                'audio_duration': audio_duration
            }

        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }

    def process_meeting_from_video(
        self,
        video_url: str,
        committee: str,
        meeting_date: datetime,
        start_time: str = None,
        end_time: str = None,
        committee_type: str = "Interim",
        upload_to_seafile: bool = True,
        proxy_manager=None
    ) -> Dict:
        """
        Process meeting from video URL (download, extract audio, transcribe).

        Args:
            video_url: URL to video
            committee: Committee acronym
            meeting_date: Meeting date
            start_time: Start time
            end_time: End time
            committee_type: Committee type
            upload_to_seafile: Upload to Seafile
            proxy_manager: Oxylabs proxy manager instance

        Returns:
            Processing results
        """
        logger.info(f"Processing video URL: {video_url}")

        try:
            # Step 0a: Download video with proxy
            logger.info("Step 0a: Downloading video...")
            video_path = download_video(video_url, proxy_manager=proxy_manager)

            if not video_path or not os.path.exists(video_path):
                return {'success': False, 'error': 'Video download failed'}

            # Step 0b: Extract audio
            logger.info("Step 0b: Extracting audio from video...")
            audio_path = extract_audio_from_video(video_path)

            if not audio_path or not os.path.exists(audio_path):
                return {'success': False, 'error': 'Audio extraction failed'}

            # Process the audio
            result = self.process_meeting(
                audio_path,
                committee,
                meeting_date,
                start_time,
                end_time,
                committee_type,
                upload_to_seafile
            )

            # Cleanup temporary files (check exists to avoid race condition)
            for path in [video_path, audio_path]:
                if path and os.path.exists(path):
                    try:
                        os.remove(path)
                        logger.info(f"Cleaned up: {path}")
                    except Exception as e:
                        logger.warning(f"Could not remove {path}: {e}")

            return result

        except Exception as e:
            logger.error(f"Video processing error: {e}")
            traceback.print_exc()
            return {'success': False, 'error': str(e)}


def test_pipeline():
    """Test the pipeline setup."""
    print("=" * 70)
    print("LEGISLATIVE TRANSCRIPT PIPELINE")
    print("=" * 70)
    print("\nTranscription Engines:")
    print("  Primary: NVIDIA Parakeet TDT 0.6b-v2 (60x real-time via ONNX)")
    print("  Alternative: IBM Granite Speech 3.3-2B (parallel processing)")
    print("  Fallback: Whisper Large-v3")
    print("\nDiarization: Pyannote 3.1 (improved accuracy for many speakers)")
    print("Output: JSON, CSV, TXT formats")
    print("Upload: Seafile + SFTP")
    print("\nUsage:")
    print("  from modules.transcript_pipeline import TranscriptPipeline")
    print("  # Recommended: Parakeet (fast and accurate)")
    print("  pipeline = TranscriptPipeline(transcriber='parakeet')")
    print("  # Alternative: Granite (GPU-accelerated)")
    print("  pipeline = TranscriptPipeline(transcriber='granite', num_workers=2)")
    print("  result = pipeline.process_meeting(")
    print("      audio_path='audio.wav',")
    print("      committee='CCJ',")
    print("      meeting_date=datetime(2026, 1, 15)")
    print("  )")


if __name__ == "__main__":
    test_pipeline()
