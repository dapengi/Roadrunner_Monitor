#!/usr/bin/env python3
"""Reprocess 9:11 AM HAFC meeting"""

import logging
import datetime
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from config import *
from modules.video_processor import download_video, extract_audio_from_video
from modules.transcript_pipeline_canary import TranscriptPipeline
from modules.seafile_client import SeafileClient
from modules.sftp_client import SFTPClient
from modules.filename_generator import get_filename_generator
from modules.proxy_manager import ProxyManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("reprocess_911am.log"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def reprocess_from_url(video_url, title, meeting_date):
    """Reprocess a meeting from URL with the fixed code."""
    try:
        logger.info("="*70)
        logger.info(f"REPROCESSING: {title}")
        logger.info(f"URL: {video_url}")
        logger.info(f"Meeting Date: {meeting_date}")
        logger.info("="*70)
        
        # Initialize proxy
        proxy_manager = ProxyManager()
        if not proxy_manager.test_proxy_connection(max_retries=3):
            logger.error("Proxy not working")
            return False
        
        # Download video
        logger.info("Step 1/5: Downloading video...")
        video_path = download_video(video_url, proxy_manager=proxy_manager)
        if not video_path:
            logger.error("Failed to download video")
            return False
        logger.info(f"Downloaded: {video_path}")
        
        # Extract audio
        logger.info("Step 2/5: Extracting audio...")
        audio_path = extract_audio_from_video(video_path)
        if not audio_path:
            logger.error("Failed to extract audio")
            return False
        logger.info(f"Extracted: {audio_path}")
        
        # Generate filename with correct date
        filename_gen = get_filename_generator()
        filename_info = filename_gen.generate_filename(title=title, meeting_date=meeting_date)
        base_name = filename_info["base_name"]
        
        logger.info(f"Filename: {base_name}")
        logger.info(f"Committee: {filename_info['committee']}")
        
        # Initialize clients
        seafile_client = SeafileClient(url=SEAFILE_URL, token=SEAFILE_API_TOKEN, library_id=SEAFILE_LIBRARY_ID)
        sftp_client = SFTPClient(host=SFTP_HOST, port=SFTP_PORT, username=SFTP_USERNAME, password=SFTP_PASSWORD, upload_path=SFTP_UPLOAD_PATH)
        
        # Transcribe with Canary + updated diarization
        logger.info("Step 3/5: Transcribing with Canary + Diarization...")
        pipeline = TranscriptPipeline()
        
        result = pipeline.process_meeting(
            audio_path=audio_path,
            committee=filename_info["committee"],
            meeting_date=meeting_date,
            start_time=filename_info.get("start_time"),
            end_time=filename_info.get("end_time"),
            committee_type=filename_info["session_type"],
            upload_to_seafile=False
        )
        
        if not result or not result.get("success"):
            logger.error("Transcription failed")
            return False
        
        # Count unique speakers
        segments = result.get("segments", [])
        unique_speakers = set()
        for seg in segments:
            if "speaker" in seg:
                unique_speakers.add(seg["speaker"])
        
        logger.info(f"*** SPEAKERS DETECTED: {len(unique_speakers)} ***")
        logger.info(f"Speakers: {sorted(unique_speakers)}")
        
        # Save files
        formatted_transcripts = result.get("formatted_transcripts", {})
        saved_files = {}
        
        for fmt in ["json", "csv", "txt"]:
            content = formatted_transcripts.get(fmt)
            if content:
                output_path = os.path.join(DOWNLOAD_DIR, f"{base_name}.{fmt}")
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(content)
                saved_files[fmt] = output_path
                logger.info(f"Saved {fmt.upper()}: {output_path}")
        
        # Upload to Seafile
        logger.info("Step 4/5: Uploading to Seafile...")
        seafile_base_path = filename_gen.get_seafile_path(filename_info)
        for fmt in ["json", "csv", "txt"]:
            local_file = saved_files.get(fmt)
            if local_file and Path(local_file).exists():
                remote_path = f"{seafile_base_path}/{base_name}.{fmt}"
                try:
                    if seafile_client.upload_file(local_file, remote_path):
                        logger.info(f"  Uploaded {fmt.upper()} to Seafile")
                except Exception as e:
                    logger.error(f"  Seafile upload error: {e}")
        
        # Upload to SFTP
        logger.info("Step 5/5: Uploading to SFTP...")
        files_to_upload = [f for f in saved_files.values() if Path(f).exists()]
        if files_to_upload:
            try:
                sftp_client.upload_files(files_to_upload, subfolder=None)
                for f in files_to_upload:
                    os.unlink(f)
            except Exception as e:
                logger.error(f"  SFTP upload error: {e}")
        
        # Cleanup temp files
        logger.info("Cleaning up temp files...")
        for f in [video_path, audio_path]:
            if f and os.path.exists(f):
                os.unlink(f)
                logger.info(f"  Removed: {f}")
        
        logger.info("="*70)
        logger.info("REPROCESSING COMPLETE!")
        logger.info(f"Filename: {base_name}")
        logger.info(f"Segments: {len(segments)}")
        logger.info(f"UNIQUE SPEAKERS: {len(unique_speakers)}")
        logger.info("="*70)
        
        return True
        
    except Exception as e:
        logger.error(f"Reprocessing failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Reprocess the 9:11 AM - 12:31 PM HAFC meeting from Jan 12, 2026
    video_url = "https://sg001-harmony.sliq.net/00293/Harmony/en/PowerBrowser/PowerBrowserV2/20250522/-1/77958"
    title = "House - Appropriations and Finance (Room 307) 9:11 AM-12:31 PM Mon, Jan 12, 2026"
    meeting_date = datetime.datetime(2026, 1, 12, 9, 11)  # Jan 12, 2026 at 9:11 AM
    
    success = reprocess_from_url(video_url, title, meeting_date)
    sys.exit(0 if success else 1)
