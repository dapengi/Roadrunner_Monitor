# main.py

import time
import schedule
import logging
import datetime
import re
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables BEFORE importing config
load_dotenv()

from config import *
from modules.web_scraper import get_current_entries
from modules.video_processor import download_video, extract_audio_from_video
from modules.transcription import transcribe_with_whisperx
from modules.speaker_id import identify_speakers_in_transcript, get_committee_members_for_meeting
from modules.nextcloud import save_transcript_to_nextcloud
from modules.notifications import send_notification
from modules.utils import (
    read_stored_entries, write_entries, read_processed_entries, write_processed_entry,
    should_run_daily_cleanup, cleanup_downloads_directory, is_test_meeting
)
from modules.proxy_manager import ProxyManager # Import the new ProxyManager

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


def process_new_entry(entry, proxy_manager): # Added proxy_manager parameter
    """Process a new entry: download video, transcribe, and save to Nextcloud."""
    try:
        if not entry.get('link'):
            logger.error("Entry has no link, cannot process")
            return None
        
        video_path = download_video(entry['link'], proxy_manager=proxy_manager) # Pass proxy_manager
        if not video_path:
            logger.error("Failed to download video")
            return None
        
        audio_path = extract_audio_from_video(video_path)
        if not audio_path:
            logger.error("Failed to extract audio")
            return None
        
        # For automatic monitoring, use simplified settings:
        # - No committee rosters (generic Speaker 0, Speaker 1 labels)
        # - No timestamps (cleaner, shorter transcripts)
        committee_members = None  # Don't use rosters for automatic processing
        include_timestamps = False  # Don't include timestamps for automatic processing
        
        logger.info("Using simplified transcription settings for automatic monitoring:")
        logger.info("  • Generic speaker labels (Speaker 0, Speaker 1, etc.)")
        logger.info("  • No timestamps (cleaner format)")
        
        # Start timing for transcription
        import datetime
        start_time = datetime.datetime.now()
        
        # Transcribe with simplified settings
        logger.info(f"Starting enhanced transcription with Sherpa-ONNX speaker diarization...")
        enhanced_transcript = transcribe_with_whisperx(
            audio_path, 
            include_timestamps=include_timestamps,
            committee_members=committee_members
        )
        
        # End timing and log results
        end_time = datetime.datetime.now()
        processing_time = end_time - start_time
        
        if not enhanced_transcript:
            logger.error("Failed to transcribe audio")
            return None
        
        # Log transcription results
        logger.info(f"Transcription completed successfully!")
        logger.info(f"Processing time: {processing_time}")
        logger.info(f"Transcript length: {len(enhanced_transcript)} characters")
        
        # Count detected speakers in the transcript
        import re
        # Since we're using generic labels for automatic processing (now with letters)
        speaker_pattern = r'Speaker ([A-Z]):'
        speakers_found = re.findall(speaker_pattern, enhanced_transcript)
        unique_speakers = len(set(speakers_found))
        speaker_labels = [f"Speaker {letter}" for letter in sorted(set(speakers_found))]
        logger.info(f"Detected speakers: {unique_speakers} ({', '.join(speaker_labels)})")
        
        # Clean title for use in filename and document
        title_text = entry['text']
        clean_title = re.sub(r'\s+', ' ', title_text).strip()
        
        nextcloud_result = save_transcript_to_nextcloud(
            enhanced_transcript, clean_title, entry['link']
        )
        
        # Prepare transcription metadata
        transcription_metadata = {
            'video_path': video_path,
            'audio_path': audio_path,
            'nextcloud_result': nextcloud_result,
            'processed_at': datetime.datetime.now().isoformat(),
            'processing_time_seconds': processing_time.total_seconds(),
            'transcript_length': len(enhanced_transcript),
            'committee_members_count': 0,  # Not using rosters for automatic processing
            'speaker_diarization': 'Sherpa-ONNX',
            'include_timestamps': include_timestamps,
            'processing_mode': 'automatic_simplified'
        }
        
        # Add speaker detection results (generic labels)
        transcription_metadata['speakers_detected'] = speaker_labels
        transcription_metadata['speakers_count'] = unique_speakers
        
        entry['transcription'] = transcription_metadata
        
        write_processed_entry(entry)
        
        # Final success summary
        logger.info("=" * 70)
        logger.info("🎉 TRANSCRIPTION PROCESSING COMPLETE!")
        logger.info(f"📊 Mode: Automatic simplified processing")
        logger.info(f"🎭 Speakers: {transcription_metadata['speakers_count']} detected")
        logger.info(f"👥 Labels: {', '.join(transcription_metadata['speakers_detected'])}")
        logger.info(f"⏱️  Time: {processing_time}")
        logger.info(f"📄 Length: {len(enhanced_transcript)} characters")
        logger.info(f"🏷️  Format: No timestamps, generic speaker labels")
        logger.info(f"☁️  Saved to: {nextcloud_result.get('nextcloud_path', 'Unknown')}")
        logger.info(f"🔗 Share: {nextcloud_result.get('share_link', 'No link')}")
        logger.info("=" * 70)
        
        return nextcloud_result
    
    except Exception as e:
        logger.error(f"Error processing entry: {e}")
        return None


def check_for_new_entries(proxy_manager): # Added proxy_manager parameter
    """Check for new entries and process them if found."""
    
    # Check if we need to test proxy
    if proxy_manager.should_update_proxy_list():
        logger.info("Testing Oxylabs proxy...")
        proxy_manager.test_proxy_connection() # Use the manager's test method
    
    # Check if we need to run daily cleanup
    if should_run_daily_cleanup():
        logger.info("Running daily cleanup of downloads directory...")
        cleanup_downloads_directory()
    
    logger.info(f"Checking for new entries at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    current_entries = get_current_entries(proxy_manager=proxy_manager) # Pass proxy_manager
    stored_entries = read_stored_entries()
    
    stored_texts = [entry['text'] for entry in stored_entries]
    new_entries = [entry for entry in current_entries if entry['text'] not in stored_texts]
    
    # Filter out test meetings
    filtered_new_entries = []
    skipped_test_meetings = 0
    
    for entry in new_entries:
        if is_test_meeting(entry['text']):
            logger.info(f"Skipping test meeting: {entry['text'][:50]}...")
            skipped_test_meetings += 1
        else:
            filtered_new_entries.append(entry)
    
    if skipped_test_meetings > 0:
        logger.info(f"Skipped {skipped_test_meetings} test meeting(s)")
    
    if filtered_new_entries:
        logger.info(f"Found {len(filtered_new_entries)} new entries to process!")
        
        transcript_results = []
        for entry in filtered_new_entries:
            logger.info(f"Processing entry: {entry['text'][:50]}...")
            result = process_new_entry(entry, proxy_manager) # Pass proxy_manager
            transcript_results.append(result)
        
        send_notification(filtered_new_entries, transcript_results)
        write_entries(current_entries)  # Still save all entries (including test meetings) to avoid reprocessing
    else:
        if new_entries:
            logger.info("All new entries were test meetings - no processing needed")
        else:
            logger.info("No new entries found")


def main():
    """Main function to schedule and run the monitoring."""
    logger.info("Built by LWE.Vote | Starting Legislature page monitoring with yt-dlp, WhisperX, Nextcloud integration, and Oxylabs Proxy")
    
    # Check Nextcloud configuration
    if not all([NEXTCLOUD_URL, NEXTCLOUD_USERNAME, NEXTCLOUD_TOKEN]):
        logger.error("Nextcloud configuration missing. Please check NEXTCLOUD_URL, NEXTCLOUD_USERNAME, and NEXTCLOUD_TOKEN in .env file")
        return
    else:
        logger.info(f"Nextcloud configured: {NEXTCLOUD_URL}")
    
    # Initialize Oxylabs proxy system
    logger.info("Initializing Oxylabs proxy system...")
    proxy_manager = ProxyManager() # Instantiate ProxyManager
    
    if not proxy_manager.test_proxy_connection(): # Use manager's test method
        logger.warning("Failed to connect to Oxylabs proxy. Script will attempt to run without proxy.")
    else:
        logger.info("Oxylabs proxy system initialized successfully")
        proxy_manager.test_proxy_connectivity() # Use manager's connectivity test
    
    # Check for required dependencies
    try:
        import yt_dlp
        logger.info("yt-dlp is available")
    except ImportError:
        logger.error("yt-dlp not found. Please install with: pip install yt-dlp")
        return
    
    try:
        from docx import Document
        logger.info("python-docx is available")
    except ImportError:
        logger.error("python-docx not found. Please install with: pip install python-docx")
        return
    
    # Check for ffmpeg (optional, for fallback)
    import subprocess
    try:
        subprocess.run(['ffmpeg', '-version'], check=True, capture_output=True)
        logger.info("ffmpeg is available (for fallback audio extraction)")
    except (subprocess.SubprocessError, FileNotFoundError):
        logger.warning("ffmpeg not found. Audio extraction will rely on yt-dlp only.")
    
    if not HF_TOKEN:
        logger.warning("Hugging Face token not found. Speaker diarization will not work.")
    
    logger.info("All dependencies checked. Starting monitoring system...")
    
    # Run immediately on startup
    check_for_new_entries(proxy_manager) # Pass proxy_manager
    
    # Schedule checks every few hours, Monday through Friday only (GMT times for MST = GMT-7)
    gmt_slots = ["16:00", "18:00", "20:00", "22:00", "00:00", "02:00"]

    for t in gmt_slots:
        # Use a lambda to pass proxy_manager to the scheduled function
        schedule.every().monday.at(t).do(lambda: check_for_new_entries(proxy_manager))
        schedule.every().tuesday.at(t).do(lambda: check_for_new_entries(proxy_manager))
        schedule.every().wednesday.at(t).do(lambda: check_for_new_entries(proxy_manager))
        schedule.every().thursday.at(t).do(lambda: check_for_new_entries(proxy_manager))
        schedule.every().friday.at(t).do(lambda: check_for_new_entries(proxy_manager))
    
    logger.info(f"Scheduled monitoring Monday-Friday at GMT times: {', '.join(gmt_slots)}")
    logger.info("Legislature monitoring system is now running (weekdays only)...")
    
    # Keep the script running
    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    main()


