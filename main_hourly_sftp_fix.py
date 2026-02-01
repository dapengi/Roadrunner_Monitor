#!/usr/bin/env python3
"""
Hourly runner for Roadrunner Monitor
Designed to be called by cron every hour between 7 AM - 9 PM
Uses Canary pipeline for high-accuracy transcription and uploads to Seafile
"""

import logging
import datetime
import time
import sys
import traceback
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from config import *
from modules.web_scraper import get_current_entries
from modules.video_processor import download_video, extract_audio_from_video
from modules.transcript_pipeline import TranscriptPipeline
from modules.seafile_client import SeafileClient
from modules.sftp_client import SFTPClient
from modules.filename_generator import get_filename_generator
from modules.proxy_manager import ProxyManager
from modules.utils import (
    read_stored_entries, write_entries, read_processed_entries,
    write_processed_entry, should_run_daily_cleanup,
    cleanup_downloads_directory, is_test_meeting,
    increment_retry_count, clear_retry_count, has_exceeded_max_retries,
    MAX_RETRY_COUNT
)
from modules.pushover_notifications import notify_success, notify_failure, notify_failure_simple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("legislature_monitor.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Create download directory if it doesn't exist
Path(DOWNLOAD_DIR).mkdir(exist_ok=True)

def parse_meeting_datetime(entry_text: str):
    """
    Parse meeting date and time from entry text.
    
    Entry text format example:
    "House - Appropriations... 1:34 PM-5:35 PM\nMon, Jan 12, 2026"
    
    Returns:
        datetime object with the meeting date and start time
    """
    import re as regex
    
    # Pattern for date: "Mon, Jan 12, 2026" or similar
    date_pattern = r"(Mon|Tue|Wed|Thu|Fri|Sat|Sun),?\s+(\w+)\s+(\d{1,2}),?\s+(\d{4})"
    date_match = regex.search(date_pattern, entry_text, regex.IGNORECASE)
    
    # Pattern for time range: "1:34 PM-5:35 PM" 
    time_pattern = r"(\d{1,2}):(\d{2})\s*(AM|PM)\s*-\s*(\d{1,2}):(\d{2})\s*(AM|PM)"
    time_match = regex.search(time_pattern, entry_text, regex.IGNORECASE)
    
    if date_match:
        month_name = date_match.group(2)
        day = int(date_match.group(3))
        year = int(date_match.group(4))
        
        # Convert month name to number
        months = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
                  "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}
        month = months.get(month_name.lower()[:3], 1)
        
        # Get hour and minute from time if available
        hour, minute = 9, 0  # Default to 9:00 AM
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2))
            ampm = time_match.group(3).upper()
            
            # Convert to 24-hour format
            if ampm == "PM" and hour < 12:
                hour += 12
            elif ampm == "AM" and hour == 12:
                hour = 0
        
        return datetime.datetime(year, month, day, hour, minute)
    
    # Fallback to now if parsing fails
    logger.warning(f"Could not parse meeting date from: {entry_text[:100]}...")
    return datetime.datetime.now()


def handle_processing_failure(entry_link, reason, committee_name, meeting_date_str, meeting_time_str):
    """
    Handle a processing failure with retry logic.

    Returns:
        tuple: (should_mark_processed, is_max_retries)
    """
    retry_count = increment_retry_count(entry_link, reason)

    if retry_count >= MAX_RETRY_COUNT:
        # Max retries reached - mark as processed so it stops retrying
        logger.error(f"❌ MAX RETRIES ({MAX_RETRY_COUNT}) REACHED - Entry will not be retried")
        notify_failure(committee_name, meeting_date_str, meeting_time_str,
                      f"MAX RETRIES ({MAX_RETRY_COUNT})",
                      f"Failed after {MAX_RETRY_COUNT} attempts. Last error: {reason}. Requires manual attention.")
        return True, True
    else:
        # Still has retries left - don't mark as processed
        logger.warning(f"⚠️ Attempt {retry_count}/{MAX_RETRY_COUNT} failed - will retry on next run")
        notify_failure(committee_name, meeting_date_str, meeting_time_str,
                      reason, f"Attempt {retry_count}/{MAX_RETRY_COUNT} - will retry automatically")
        return False, False


def process_entry(entry, proxy_manager, seafile_client):
    """Process entry using Canary pipeline and upload to Seafile."""
    processing_start_time = time.time()
    
    # Extract meeting info early for notifications
    filename_gen = get_filename_generator()
    meeting_date_parsed = parse_meeting_datetime(entry.get("text", ""))
    filename_info = filename_gen.generate_filename(
        title=entry.get('text', ''),
        meeting_date=meeting_date_parsed
    )
    committee_name = filename_info.get('committee', 'Unknown Committee')
    meeting_date_str = meeting_date_parsed.strftime("%B %d, %Y")
    meeting_time_str = f"{filename_info.get('start_time', '?')} - {filename_info.get('end_time', '?')}"
    
    try:
        if not entry.get('link'):
            logger.error("Entry has no link, cannot process")
            notify_failure(committee_name, meeting_date_str, meeting_time_str,
                          "Validation", "Entry has no video link - cannot retry without link")
            return None

        entry_link = entry['link']
        
        logger.info(f"Processing: {entry['text'][:80]}")
        
        # Download video with proxy
        logger.info("Step 1/4: Downloading video...")
        video_path = download_video(entry_link, proxy_manager=proxy_manager)
        if not video_path:
            logger.error("Failed to download video")
            should_mark, is_max = handle_processing_failure(
                entry_link, "Download Failed", committee_name, meeting_date_str, meeting_time_str)
            if should_mark:
                write_processed_entry(entry_link)
            return None
        
        # Extract audio
        logger.info("Step 2/4: Extracting audio...")
        audio_path = extract_audio_from_video(video_path)
        if not audio_path:
            logger.error("Failed to extract audio")
            should_mark, is_max = handle_processing_failure(
                entry_link, "Audio Extraction Failed", committee_name, meeting_date_str, meeting_time_str)
            if should_mark:
                write_processed_entry(entry_link)
            return None
        
        # Use the filename info we generated at the start
        meeting_date = meeting_date_parsed
        logger.info(f"Parsed meeting date: {meeting_date}")
        base_name = filename_info['base_name']

        logger.info(f"Generated filename: {base_name}")
        logger.info(f"  Session Type: {filename_info['session_type']}")
        logger.info(f"  Committee: {filename_info['committee']}")

        # Process with Canary pipeline
        logger.info("Step 3/4: Transcribing with Canary + Diarization...")
        pipeline = TranscriptPipeline()

        # Extract time range from filename_info
        start_time = filename_info.get('start_time')
        end_time = filename_info.get('end_time')

        # Call process_meeting with correct parameters
        result = pipeline.process_meeting(
            audio_path=audio_path,
            committee=filename_info['committee'],
            meeting_date=meeting_date,
            start_time=start_time,
            end_time=end_time,
            committee_type=filename_info['session_type'],
            upload_to_seafile=False  # We'll handle upload separately
        )

        if not result or not result.get('success'):
            logger.error("Failed to transcribe with Canary pipeline")
            should_mark, is_max = handle_processing_failure(
                entry_link, "Transcription Failed", committee_name, meeting_date_str, meeting_time_str)
            if should_mark:
                write_processed_entry(entry_link)
            return None

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
        logger.info("Step 4/5: Uploading to Seafile...")
        seafile_results = {}

        # Get Seafile path based on session type
        seafile_base_path = filename_gen.get_seafile_path(filename_info)

        # Upload each format to Seafile
        for fmt in ['json', 'csv', 'txt']:
            local_file = saved_files.get(fmt)
            if local_file and Path(local_file).exists():
                # Seafile path: /Legislative Transcription/Interim/LFC/2025-11-20/captions/filename.json
                remote_path = f"{seafile_base_path}/{base_name}.{fmt}"
                try:
                    upload_success = seafile_client.upload_file(local_file, remote_path)
                    if upload_success:
                        logger.info(f"  ✅ Uploaded {fmt.upper()} to Seafile: {remote_path}")
                        seafile_results[fmt] = remote_path
                    else:
                        logger.warning(f"  ❌ Failed to upload {fmt.upper()} to Seafile")
                except Exception as e:
                    logger.error(f"  ❌ Error uploading {fmt.upper()} to Seafile: {e}", exc_info=True)
        
        # Upload to SFTP (Just-In-Time Connection)
        logger.info("Step 5/5: Uploading to SFTP...")
        sftp_results = {}
        sftp_client = None

        # Use saved files for SFTP upload
        files_to_upload = [f for f in saved_files.values() if Path(f).exists()]
        
        if files_to_upload:
            try:
                # Initialize SFTP client with fresh connection (just-in-time)
                logger.info("Connecting to SFTP server...")
                sftp_client = SFTPClient(
                    host=SFTP_HOST,
                    port=SFTP_PORT,
                    username=SFTP_USERNAME,
                    password=SFTP_PASSWORD,
                    upload_path=SFTP_UPLOAD_PATH
                )
                
                if not sftp_client.connect():
                    raise Exception("Failed to connect to SFTP server")
                
                logger.info("✅ SFTP connected")
                
                # Upload all files to flat incoming directory (no subfolders)
                upload_results_sftp = sftp_client.upload_files(files_to_upload, subfolder=None)
                
                for filename, success in upload_results_sftp.items():
                    if success:
                        logger.info(f"  ✅ Uploaded to SFTP: {filename}")
                        sftp_results[filename] = filename
                    else:
                        logger.warning(f"  ❌ Failed to upload to SFTP: {filename}")
                
                # Clean up local files after successful upload
                for f in files_to_upload:
                    try:
                        os.unlink(f)
                    except:
                        pass
                        
            except Exception as e:
                logger.error(f"  ❌ Error during SFTP upload: {e}", exc_info=True)
            
            finally:
                # Always disconnect SFTP after upload attempt
                if sftp_client:
                    try:
                        sftp_client.disconnect()
                        logger.info("SFTP connection closed")
                    except Exception as e:
                        logger.warning(f"Error closing SFTP connection: {e}")
        
        # Cleanup temporary video and audio files
        try:
            if video_path and os.path.exists(video_path):
                os.unlink(video_path)
                logger.info(f"  🗑️ Cleaned up video: {video_path}")
        except Exception as e:
            logger.warning(f"  Could not cleanup video file: {e}")
        
        try:
            if audio_path and os.path.exists(audio_path):
                os.unlink(audio_path)
                logger.info(f"  🗑️ Cleaned up audio: {audio_path}")
        except Exception as e:
            logger.warning(f"  Could not cleanup audio file: {e}")

        # Calculate processing duration
        processing_duration = time.time() - processing_start_time

        # Check if SFTP upload was successful - this determines if we mark as processed
        if sftp_results:
            # Full success! Mark as processed and clear retry count
            write_processed_entry(entry_link)
            clear_retry_count(entry_link)

            logger.info("✅ Entry processed successfully!")
            logger.info(f"   Filename: {base_name}")
            logger.info(f"   Segments: {result.get('segments_count', 0)}")
            logger.info(f"   Speakers: {result.get('speakers_count', 0)}")
            logger.info(f"   Seafile: {len(seafile_results)} files → {seafile_base_path}")
            logger.info(f"   SFTP: {len(sftp_results)} files → {filename_gen.get_sftp_path()}")
            logger.info(f"   Duration: {processing_duration:.1f}s")

            notify_success(
                committee=committee_name,
                meeting_date=meeting_date_str,
                meeting_time=meeting_time_str,
                processing_duration=processing_duration,
                filename=base_name
            )

            return {
                'entry': entry,
                'result': result,
                'filename': base_name,
                'seafile_uploads': seafile_results,
                'sftp_uploads': sftp_results
            }
        else:
            # SFTP upload failed - use retry logic
            logger.error("SFTP upload failed")
            should_mark, is_max = handle_processing_failure(
                entry_link, "SFTP Upload Failed", committee_name, meeting_date_str, meeting_time_str)
            if should_mark:
                write_processed_entry(entry_link)
            return None



    except Exception as e:
        logger.error(f"Error processing entry: {e}", exc_info=True)
        # Use retry logic for unexpected errors too
        entry_link = entry.get('link')
        if entry_link:
            should_mark, is_max = handle_processing_failure(
                entry_link, f"Unexpected Error: {str(e)[:100]}", committee_name, meeting_date_str, meeting_time_str)
            if should_mark:
                write_processed_entry(entry_link)
        else:
            notify_failure(committee_name, meeting_date_str, meeting_time_str,
                          "Unexpected Error", str(e)[:200])
        return None


def run_hourly_check():
    """Run hourly check for new entries."""
    start_time = datetime.datetime.now()
    logger.info("="*70)
    logger.info(f"🕐 HOURLY RUN STARTING: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*70)
    
    # Initialize proxy
    logger.info("Initializing Oxylabs proxy...")
    proxy_manager = ProxyManager()
    
    # Always test proxy on startup or if it needs updating
    if not proxy_manager.proxy_working or proxy_manager.should_update_proxy_list():
        logger.info("Testing proxy connection...")
        if not proxy_manager.test_proxy_connection(max_retries=5):
            logger.error("❌ Proxy not working. Cannot proceed without proxy.")
            return False
    
    if not proxy_manager.proxy_working:
        logger.error("❌ Proxy not available. Cannot proceed without proxy.")
        return False
    
    logger.info("✅ Proxy working")
    
    # Initialize Seafile client
    logger.info("Initializing Seafile client...")
    try:
        seafile_client = SeafileClient(
            url=SEAFILE_URL,
            token=SEAFILE_API_TOKEN,
            library_id=SEAFILE_LIBRARY_ID
        )
        logger.info("✅ Seafile client initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Seafile: {e}", exc_info=True)
        return False

    # Daily cleanup check
    if should_run_daily_cleanup():
        logger.info("Running daily cleanup...")
        cleanup_downloads_directory()
    
    # Get entries
    logger.info("Fetching current entries from website...")
    current_entries = get_current_entries(proxy_manager=proxy_manager)
    stored_entries = read_stored_entries()
    processed_entries = read_processed_entries()
    
    stored_texts = [entry['text'] for entry in stored_entries]
    new_entries = [entry for entry in current_entries 
                   if entry['text'] not in stored_texts 
                   and entry['link'] not in processed_entries]
    
    # Filter out test meetings
    filtered_entries = [e for e in new_entries if not is_test_meeting(e['text'])]
    
    skipped = len(new_entries) - len(filtered_entries)
    if skipped > 0:
        logger.info(f"⏭️  Skipped {skipped} test meeting(s)")
    
    if not filtered_entries:
        logger.info("ℹ️  No new entries to process")
        logger.info("="*70)
        return True
    
    logger.info(f"📋 Found {len(filtered_entries)} new entry/entries to process")
    logger.info("="*70)
    
    # Process each entry
    processed_count = 0
    failed_count = 0
    
    for i, entry in enumerate(filtered_entries, 1):
        logger.info(f"\n📝 Processing entry {i}/{len(filtered_entries)}")
        result = process_entry(entry, proxy_manager, seafile_client)
        
        if result:
            processed_count += 1
        else:
            failed_count += 1
    
    # Update stored entries
    write_entries(current_entries)
    
    # Summary
    end_time = datetime.datetime.now()
    duration = end_time - start_time
    
    logger.info("\n" + "="*70)
    logger.info("📊 HOURLY RUN SUMMARY")
    logger.info("="*70)
    logger.info(f"⏱️  Duration: {duration}")
    logger.info(f"📥 Entries found: {len(current_entries)}")
    logger.info(f"🆕 New entries: {len(new_entries)}")
    logger.info(f"✅ Processed: {processed_count}")
    logger.info(f"❌ Failed: {failed_count}")
    logger.info(f"🏁 Completed: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*70)
    
    return True


if __name__ == "__main__":
    try:
        success = run_hourly_check()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Fatal error in hourly run: {e}", exc_info=True)
        sys.exit(1)
