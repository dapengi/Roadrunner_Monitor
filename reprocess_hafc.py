#!/usr/bin/env python3
"""
Manual reprocessing script for HAFC videos
Processes existing audio files and uploads with fixed code
"""

import logging
import datetime
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from config import *
from modules.transcript_pipeline_canary import TranscriptPipeline
from modules.seafile_client import SeafileClient
from modules.sftp_client import SFTPClient
from modules.filename_generator import get_filename_generator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("reprocess.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def reprocess_video(audio_path, title, meeting_date_str, start_time, end_time):
    """Reprocess a single video with fixed code."""
    try:
        logger.info(f"="*70)
        logger.info(f"Reprocessing: {title}")
        logger.info(f"Audio: {audio_path}")
        logger.info(f"="*70)
        
        # Initialize clients
        logger.info("Initializing Seafile client...")
        seafile_client = SeafileClient(
            url=SEAFILE_URL,
            token=SEAFILE_API_TOKEN,
            library_id=SEAFILE_LIBRARY_ID
        )
        
        logger.info("Initializing SFTP client...")
        sftp_client = SFTPClient(
            host=SFTP_HOST,
            port=SFTP_PORT,
            username=SFTP_USERNAME,
            password=SFTP_PASSWORD,
            upload_path=SFTP_UPLOAD_PATH
        )
        
        # Generate filename
        filename_gen = get_filename_generator()
        meeting_date = datetime.datetime.strptime(meeting_date_str, '%Y-%m-%d')
        filename_info = filename_gen.generate_filename(
            title=title,
            meeting_date=meeting_date
        )
        base_name = filename_info['base_name']
        
        logger.info(f"Generated filename: {base_name}")
        logger.info(f"  Committee: {filename_info['committee']}")
        logger.info(f"  Session Type: {filename_info['session_type']}")
        
        # Process with Canary pipeline
        logger.info("Transcribing with Canary + Diarization...")
        pipeline = TranscriptPipeline()
        
        result = pipeline.process_meeting(
            audio_path=audio_path,
            committee=filename_info['committee'],
            meeting_date=meeting_date,
            start_time=start_time,
            end_time=end_time,
            committee_type=filename_info['session_type'],
            upload_to_seafile=False
        )
        
        if not result or not result.get('success'):
            logger.error("Transcription failed")
            return False
        
        # Save formatted transcripts to files
        formatted_transcripts = result.get('formatted_transcripts', {})
        saved_files = {}
        
        for fmt in ['json', 'csv', 'txt']:
            content = formatted_transcripts.get(fmt)
            if content:
                output_path = os.path.join(DOWNLOAD_DIR, f"{base_name}.{fmt}")
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                saved_files[fmt] = output_path
                logger.info(f"  Saved {fmt.upper()}: {output_path}")
        
        # Upload to Seafile
        logger.info("Uploading to Seafile...")
        seafile_results = {}
        seafile_base_path = filename_gen.get_seafile_path(filename_info)
        
        for fmt in ['json', 'csv', 'txt']:
            local_file = saved_files.get(fmt)
            if local_file and Path(local_file).exists():
                remote_path = f"{seafile_base_path}/{base_name}.{fmt}"
                try:
                    upload_success = seafile_client.upload_file(local_file, remote_path)
                    if upload_success:
                        logger.info(f"  ✅ Uploaded {fmt.upper()} to Seafile: {remote_path}")
                        seafile_results[fmt] = remote_path
                    else:
                        logger.warning(f"  ❌ Failed to upload {fmt.upper()} to Seafile")
                except Exception as e:
                    logger.error(f"  ❌ Error uploading {fmt.upper()} to Seafile: {e}")
        
        # Upload to SFTP
        logger.info("Uploading to SFTP...")
        sftp_results = {}
        files_to_upload = [f for f in saved_files.values() if Path(f).exists()]
        
        if files_to_upload:
            try:
                upload_results_sftp = sftp_client.upload_files(files_to_upload, subfolder=None)
                
                for filename, success in upload_results_sftp.items():
                    if success:
                        logger.info(f"  ✅ Uploaded to SFTP: {filename}")
                        sftp_results[filename] = filename
                    else:
                        logger.warning(f"  ❌ Failed to upload to SFTP: {filename}")
                
                # Cleanup local files
                for f in files_to_upload:
                    try:
                        os.unlink(f)
                        logger.info(f"  Cleaned up: {f}")
                    except:
                        pass
            except Exception as e:
                logger.error(f"  ❌ Error during SFTP upload: {e}")
        
        logger.info("="*70)
        logger.info("✅ REPROCESSING COMPLETE!")
        logger.info(f"   Filename: {base_name}")
        logger.info(f"   Segments: {len(result.get('segments', []))}")
        logger.info(f"   Seafile: {len(seafile_results)} files")
        logger.info(f"   SFTP: {len(sftp_results)} files")
        logger.info("="*70)
        
        return True
        
    except Exception as e:
        logger.error(f"Reprocessing failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Video 1: 77963 - 1:34 PM-5:35 PM (4 hours)
    # Video 2: 77958 - 9:11 AM-12:31 PM (3.3 hours)
    
    videos = [
        {
            'audio_path': '/home/josh/Roadrunner_Monitor/downloads/video_20260113_020013.mp3',
            'title': 'House - Appropriations and Finance',
            'meeting_date_str': '2026-01-12',
            'start_time': '1:34 PM',
            'end_time': '5:35 PM'
        },
        {
            'audio_path': '/home/josh/Roadrunner_Monitor/downloads/video_20260113_022735.mp3',
            'title': 'House - Appropriations and Finance',
            'meeting_date_str': '2026-01-12',
            'start_time': '9:11 AM',
            'end_time': '12:31 PM'
        }
    ]
    
    logger.info("Starting manual reprocessing of HAFC videos")
    logger.info(f"Total videos to process: {len(videos)}")
    
    success_count = 0
    for i, video in enumerate(videos, 1):
        logger.info(f"\n\nProcessing video {i}/{len(videos)}")
        if reprocess_video(**video):
            success_count += 1
    
    logger.info(f"\n\nReprocessing complete: {success_count}/{len(videos)} successful")
