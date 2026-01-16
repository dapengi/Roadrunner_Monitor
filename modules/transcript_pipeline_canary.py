"""
Updated transcript pipeline with NVIDIA Canary-1b-v2 integration.
Uses GPU-accelerated transcription with speaker diarization.
"""

import logging
import os
import librosa
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Import Canary transcription with diarization
from modules.canary_diarization import transcribe_with_canary_and_diarization
from modules.audio_event_detector import AudioEventDetector
from modules.transcript_formatters import TranscriptFormatter
from modules.transcript_uploader import TranscriptUploader
from modules.video_processor import download_video, extract_audio_from_video

logger = logging.getLogger(__name__)


class TranscriptPipeline:
    """Complete pipeline with Canary GPU transcription."""

    def __init__(self, use_canary=True):
        """
        Initialize the pipeline.
        
        Args:
            use_canary: Use Canary (default) or fallback to Whisper
        """
        self.use_canary = use_canary
        self.event_detector = AudioEventDetector()
        self.formatter = TranscriptFormatter()
        self.uploader = TranscriptUploader()

    def parse_canary_transcript(self, transcript_text: str, audio_duration: float) -> List[Dict]:
        """
        Parse Canary transcript with speaker labels into segments.
        
        Canary with diarization returns format:
        "[00:05 - 00:10] Speaker A: Text here"
        
        Args:
            transcript_text: Formatted transcript from Canary
            audio_duration: Total audio duration in seconds
            
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
                # Parse format: "[MM:SS - MM:SS] Speaker X: Text"
                if line.startswith('['):
                    end_bracket = line.index(']')
                    timestamp_str = line[1:end_bracket]
                    
                    # Parse times
                    times = timestamp_str.split(' - ')
                    if len(times) == 2:
                        # Parse timestamp - supports both MM:SS and HH:MM:SS formats
                        def parse_timestamp(ts):
                            parts = ts.split(":")
                            if len(parts) == 2:  # MM:SS
                                return int(parts[0]) * 60 + int(parts[1])
                            elif len(parts) == 3:  # HH:MM:SS
                                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                            else:
                                raise ValueError(f"Invalid timestamp format: {ts}")
                        
                        start_seconds = parse_timestamp(times[0])
                        end_seconds = parse_timestamp(times[1])
                        
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
        
        logger.info(f"Parsed {len(segments)} segments from Canary transcript")
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
        Process a meeting with Canary GPU transcription.
        
        Args:
            audio_path: Path to audio file
            committee: Committee acronym
            meeting_date: Meeting date
            start_time: Meeting start time
            end_time: Meeting end time
            committee_type: Committee type
            upload_to_seafile: Upload to Seafile
            
        Returns:
            Processing results
        """
        logger.info(f"Processing meeting: {committee} on {meeting_date}")
        
        try:
            # Get audio duration
            audio, sr = librosa.load(audio_path, sr=16000, mono=True)
            audio_duration = len(audio) / sr
            logger.info(f"Audio duration: {audio_duration:.1f} seconds")
            
            # Step 1: Transcribe with Canary + Diarization
            logger.info("Step 1/4: Transcribing with Canary-1b-v2 + Speaker Diarization...")
            
            if self.use_canary:
                try:
                    transcript_text = transcribe_with_canary_and_diarization(
                        audio_path,
                        device="cuda",  # Use GPU
                        include_timestamps=True
                    )
                except Exception as e:
                    logger.error(f"Canary transcription failed: {e}")
                    # Fallback to Whisper if Canary fails
                    logger.warning("Falling back to Whisper transcription")
                    from modules.transcription import transcribe_with_whisperx
                    transcript_text = transcribe_with_whisperx(
                        audio_path,
                        engine="whisper",
                        include_timestamps=True
                    )
            else:
                # Use Whisper directly
                from modules.transcription import transcribe_with_whisperx
                transcript_text = transcribe_with_whisperx(
                    audio_path,
                    engine="whisper",
                    include_timestamps=True
                )
            
            if not transcript_text:
                logger.error("Transcription failed")
                return {'success': False, 'error': 'Transcription failed'}
            
            # Parse transcript into segments
            segments = self.parse_canary_transcript(transcript_text, audio_duration)
            
            if not segments:
                logger.error("No segments extracted from transcript")
                return {'success': False, 'error': 'No segments extracted'}
            
            # Step 2: Audio events detection (DISABLED - not needed for legislative meetings)
            logger.info("Step 2/4: Skipping audio event detection (disabled)")
            audio_events = []  # Empty list - audio events disabled

            # Step 3: Format transcripts
            logger.info("Step 3/4: Formatting transcripts (JSON, CSV, TXT)...")
            formatted_transcripts = self.formatter.format_all(segments, audio_events)
            logger.info(f"Generated {len(formatted_transcripts)} formats")
            
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
                    logger.info(f"✅ Upload successful: {upload_result['folder_path']}")
                else:
                    logger.error(f"❌ Upload failed: {upload_result.get('errors', 'Unknown error')}")
            else:
                logger.info("Step 4/4: Skipping Seafile upload")
            
            return {
                'success': True,
                'segments': segments,
                'audio_events': audio_events,
                'formatted_transcripts': formatted_transcripts,
                'upload_result': upload_result,
                'raw_transcript': transcript_text,
                'audio_duration': audio_duration
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
                                   video_url: str,
                                   committee: str,
                                   meeting_date: datetime,
                                   start_time: str = None,
                                   end_time: str = None,
                                   committee_type: str = "Interim",
                                   upload_to_seafile: bool = True,
                                   proxy_manager=None) -> Dict:
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
            logger.info("Step 0a: Downloading video with Oxylabs proxy...")
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
            
            # Cleanup temporary files
            try:
                os.remove(video_path)
                os.remove(audio_path)
                logger.info("Cleaned up temporary files")
            except Exception as e:
                logger.warning(f"Could not remove temp files: {e}")
            
            return result
            
        except Exception as e:
            logger.error(f"Video processing error: {e}")
            return {'success': False, 'error': str(e)}


def test_pipeline():
    """Test the Canary pipeline."""
    pipeline = TranscriptPipeline(use_canary=True)
    
    print("=" * 70)
    print("CANARY TRANSCRIPT PIPELINE")
    print("=" * 70)
    print("\nFeatures:")
    print("  ✅ NVIDIA Canary-1b-v2 GPU transcription")
    print("  ✅ Sherpa-ONNX speaker diarization")
    print("  ✅ Audio event detection (applause, laughter)")
    print("  ✅ Multi-format output (JSON, CSV, TXT)")
    print("  ✅ Seafile upload integration")
    print("  ✅ Oxylabs proxy support")
    print("\nTo process a meeting from video URL:")
    print("  from modules.proxy_manager import ProxyManager")
    print("  proxy = ProxyManager()")
    print("  result = pipeline.process_meeting_from_video(")
    print("      video_url='https://...',")
    print("      committee='CCJ',")
    print("      meeting_date=datetime(2025, 1, 15),")
    print("      proxy_manager=proxy")
    print("  )")


if __name__ == "__main__":
    test_pipeline()
