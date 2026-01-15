# main-captions.py

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
from modules.caption_processor import CaptionProcessor
from modules.nextcloud import save_transcript_to_nextcloud
from modules.notifications import send_notification
from modules.utils import (
    read_stored_entries, write_entries, read_processed_entries, write_processed_entry,
    should_run_daily_cleanup, cleanup_captions_directory, is_test_meeting
)
from modules.proxy_manager import ProxyManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("legislature_monitor_captions.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Create captions directory if it doesn't exist
Path(CAPTIONS_DIR).mkdir(exist_ok=True)


def process_new_entry(entry, proxy_manager):
    """Process a new entry: download captions and save to Nextcloud."""
    try:
        if not entry.get('link'):
            logger.error("Entry has no link, cannot process")
            return None

        # Initialize caption processor with proxy manager
        caption_processor = CaptionProcessor(proxy_manager=proxy_manager)

        # Start timing for caption download
        start_time = datetime.datetime.now()

        logger.info(f"Starting caption download for: {entry['text'][:60]}...")

        # Download captions (returns text content, not saved yet)
        caption_content = caption_processor.download_captions(entry['link'])

        # End timing
        end_time = datetime.datetime.now()
        processing_time = end_time - start_time

        if not caption_content:
            logger.error("Failed to download captions")
            return None

        # Log caption results
        logger.info(f"Caption download completed successfully!")
        logger.info(f"Processing time: {processing_time}")
        logger.info(f"Caption length: {len(caption_content)} characters")

        # Clean title for use in filename and document
        title_text = entry['text']
        clean_title = re.sub(r'\s+', ' ', title_text).strip()

        # Save to Nextcloud as plain text file (this generates the proper filename)
        nextcloud_result = save_transcript_to_nextcloud(
            caption_content, clean_title, entry['link'], save_as_txt=True
        )

        # Now save the caption locally using the same filename from Nextcloud
        if nextcloud_result and nextcloud_result.get('filename'):
            caption_path = caption_processor.save_caption_with_filename(
                caption_content,
                nextcloud_result['filename']
            )
        else:
            logger.warning("No filename from Nextcloud, using fallback naming")
            # Fallback to timestamp naming
            now = datetime.datetime.now()
            fallback_filename = now.strftime("%y%m%d-%H%M%S.txt")
            caption_path = caption_processor.save_caption_with_filename(
                caption_content,
                fallback_filename
            )

        # Prepare caption metadata
        caption_metadata = {
            'caption_path': caption_path,
            'nextcloud_result': nextcloud_result,
            'processed_at': datetime.datetime.now().isoformat(),
            'processing_time_seconds': processing_time.total_seconds(),
            'caption_length': len(caption_content),
            'processing_mode': 'automatic_captions'
        }

        entry['captioning'] = caption_metadata

        write_processed_entry(entry)

        # Final success summary
        logger.info("=" * 70)
        logger.info("🎉 CAPTION PROCESSING COMPLETE!")
        logger.info(f"📊 Mode: Automatic caption download")
        logger.info(f"⏱️  Time: {processing_time}")
        logger.info(f"📄 Length: {len(caption_content)} characters")
        logger.info(f"💾 Saved to: {caption_path}")
        logger.info(f"☁️  Nextcloud: {nextcloud_result.get('nextcloud_path', 'Unknown')}")
        logger.info(f"🔗 Share: {nextcloud_result.get('share_link', 'No link')}")
        logger.info("=" * 70)

        return nextcloud_result

    except Exception as e:
        logger.error(f"Error processing entry: {e}")
        return None


def check_for_new_entries(proxy_manager):
    """Check for new entries and process them if found."""

    # Check if we need to test proxy
    if proxy_manager.should_update_proxy_list():
        logger.info("Testing Oxylabs proxy...")
        proxy_manager.test_proxy_connection()

    # Check if we need to run daily cleanup (cleanup captions directory)
    if should_run_daily_cleanup():
        logger.info("Running daily cleanup of captions directory...")
        cleanup_captions_directory()

    logger.info(f"Checking for new entries at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")

    current_entries = get_current_entries(proxy_manager=proxy_manager)
    stored_entries = read_stored_entries()
    processed_entries = read_processed_entries()

    # Skip entries that are in either stored_entries OR processed_entries
    stored_texts = [entry['text'] for entry in stored_entries]
    processed_texts = [entry['text'] for entry in processed_entries]
    new_entries = [entry for entry in current_entries
                   if entry['text'] not in stored_texts and entry['text'] not in processed_texts]

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

        caption_results = []
        for entry in filtered_new_entries:
            logger.info(f"Processing entry: {entry['text'][:50]}...")
            result = process_new_entry(entry, proxy_manager)
            caption_results.append(result)

        send_notification(filtered_new_entries, caption_results)
        write_entries(current_entries)  # Save all entries (including test meetings) to avoid reprocessing
    else:
        if new_entries:
            logger.info("All new entries were test meetings - no processing needed")
        else:
            logger.info("No new entries found")


def main():
    """Main function to schedule and run the monitoring."""
    logger.info("Built by LWE.Vote | Starting Legislature page monitoring with Caption Download, Nextcloud integration, and Oxylabs Proxy")

    # Check Nextcloud configuration
    if not all([NEXTCLOUD_URL, NEXTCLOUD_USERNAME, NEXTCLOUD_TOKEN]):
        logger.error("Nextcloud configuration missing. Please check NEXTCLOUD_URL, NEXTCLOUD_USERNAME, and NEXTCLOUD_TOKEN in .env file")
        return
    else:
        logger.info(f"Nextcloud configured: {NEXTCLOUD_URL}")

    # Initialize Oxylabs proxy system
    logger.info("Initializing Oxylabs proxy system...")
    proxy_manager = ProxyManager()

    if not proxy_manager.test_proxy_connection():
        logger.error("Failed to connect to Oxylabs proxy. Captions cannot be downloaded without proxy to protect home IP.")
        return
    else:
        logger.info("Oxylabs proxy system initialized successfully")
        proxy_manager.test_proxy_connectivity()

    logger.info("All dependencies checked. Starting caption monitoring system...")

    # Run immediately on startup
    check_for_new_entries(proxy_manager)

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
    logger.info("Legislature caption monitoring system is now running (weekdays only)...")

    # Keep the script running
    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    main()
