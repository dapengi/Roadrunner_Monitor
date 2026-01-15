"""
Integrated transcript pipeline.
Orchestrates transcription, audio event detection, formatting, and upload.
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from modules.transcription import transcribe_with_whisperx
from modules.audio_event_detector import AudioEventDetector
from modules.transcript_formatters import TranscriptFormatter
from modules.transcript_uploader import TranscriptUploader
from modules.video_processor import download_video, extract_audio_from_video

logger = logging.getLogger(__name__)


class TranscriptPipeline:
    """Complete pipeline for processing legislative meeting transcripts."""

    def __init__(self):
        """Initialize the pipeline components."""
        self.event_detector = AudioEventDetector()
        self.formatter = TranscriptFormatter()
        self.uploader = TranscriptUploader()

    def extract_segments_from_transcript(self, transcript_text: str) -> List[Dict]:
        """
        Extract structured segments from formatted transcript text.

        The sherpa_diarization function returns formatted text like:
        "[00:05 - 00:10] Speaker A: Text here"

        Args:
            transcript_text: Formatted transcript text

        Returns:
            List of segment dictionaries
        """
        segments = []
        lines = transcript_text.strip().split('\n\n')  # Double line breaks separate speakers

        for line in lines:
            line = line.strip()
            if not line:
                continue

            try:
                # Parse format: "[MM:SS - MM:SS] Speaker X: Text"
                if line.startswith('['):
                    # Extract timestamp
                    end_bracket = line.index(']')
                    timestamp_str = line[1:end_bracket]  # e.g., "00:05 - 00:10"

                    # Parse start and end times
                    times = timestamp_str.split(' - ')
                    if len(times) == 2:
                        start_parts = times[0].split(':')
                        end_parts = times[1].split(':')

                        start_seconds = int(start_parts[0]) * 60 + int(start_parts[1])
                        end_seconds = int(end_parts[0]) * 60 + int(end_parts[1])

                        # Extract speaker and text
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

    def process_meeting(self,
                       audio_path: str,
                       committee: str,
                       meeting_date: datetime,
                       start_time: str = None,
                       end_time: str = None,
                       committee_type: str = "Interim",
                       upload_to_seafile: bool = True) -> Dict:
        """
        Process a complete meeting: transcribe, detect events, format, upload.

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

        try:
            # Step 1: Transcribe audio with speaker diarization
            logger.info("Step 1/4: Transcribing audio with speaker diarization...")
            transcript_text = transcribe_with_whisperx(
                audio_path,
                model_size="large-v3",  # Using large-v3 for better accuracy
                include_timestamps=True
            )

            if not transcript_text or "failed" in transcript_text.lower():
                logger.error("Transcription failed")
                return {'success': False, 'error': 'Transcription failed'}

            # Extract structured segments from transcript
            segments = self.extract_segments_from_transcript(transcript_text)

            if not segments:
                logger.error("No segments extracted from transcript")
                return {'success': False, 'error': 'No segments extracted'}

            # Step 2: Detect audio events (applause, laughter)
            logger.info("Step 2/4: Detecting audio events (applause, laughter)...")
            audio_events = self.event_detector.detect_events_simple(audio_path)

            logger.info(f"Detected {len(audio_events)} audio events")

            # Step 3: Format transcripts (JSON, CSV, TXT)
            logger.info("Step 3/4: Formatting transcripts...")
            formatted_transcripts = self.formatter.format_all(segments, audio_events)

            logger.info(f"Generated {len(formatted_transcripts)} transcript formats")

            # Step 4: Upload to Seafile (if requested)
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
                    logger.info(f"✅ Upload successful: {upload_result['folder_path']}")
                else:
                    logger.error(f"❌ Upload failed: {upload_result['errors']}")
            else:
                logger.info("Step 4/4: Skipping Seafile upload (disabled)")

            return {
                'success': True,
                'segments': segments,
                'audio_events': audio_events,
                'formatted_transcripts': formatted_transcripts,
                'upload_result': upload_result,
                'raw_transcript': transcript_text
            }

        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }

    def process_meeting_from_video(self,
                                   video_path: str,
                                   committee: str,
                                   meeting_date: datetime,
                                   start_time: str = None,
                                   end_time: str = None,
                                   committee_type: str = "Interim",
                                   upload_to_seafile: bool = True) -> Dict:
        """
        Process meeting from video file (extract audio first).

        Args:
            video_path: Path to video file (MP4, etc.)
            committee: Committee acronym
            meeting_date: Meeting date
            start_time: Start time
            end_time: End time
            committee_type: Committee type
            upload_to_seafile: Upload to Seafile

        Returns:
            Processing results
        """
        logger.info(f"Processing video: {video_path}")

        try:
            # Extract audio from video
            logger.info("Extracting audio from video...")
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

            # Clean up audio file
            try:
                os.remove(audio_path)
                logger.info(f"Cleaned up temporary audio file: {audio_path}")
            except Exception as e:
                logger.warning(f"Could not remove audio file: {e}")

            return result

        except Exception as e:
            logger.error(f"Video processing error: {e}")
            return {'success': False, 'error': str(e)}


def test_pipeline():
    """Test the pipeline with a sample audio file."""
    pipeline = TranscriptPipeline()

    print("Transcript Pipeline initialized")
    print("\nTo process a meeting:")
    print("  pipeline = TranscriptPipeline()")
    print("  result = pipeline.process_meeting(")
    print("      audio_path='path/to/audio.mp3',")
    print("      committee='CCJ',")
    print("      meeting_date=datetime(2025, 1, 15),")
    print("      start_time='9:14 AM',")
    print("      end_time='12:06 PM',")
    print("      committee_type='Interim'")
    print("  )")
    print("  print(result)")


if __name__ == "__main__":
    test_pipeline()
