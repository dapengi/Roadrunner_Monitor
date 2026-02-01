#!/usr/bin/env python3
"""
Single Video Processor for Legislature Monitoring System
Process individual videos by providing a URL
"""

import logging
import datetime
import re
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables BEFORE importing config
load_dotenv()

from config import *
from modules.video_processor import download_video, extract_audio_from_video
from modules.transcription import transcribe_with_whisperx
from modules.speaker_id import identify_speakers_in_transcript, get_committee_members_for_meeting
from modules.nextcloud import save_transcript_to_nextcloud
from modules.notifications import send_notification
from modules.utils import write_processed_entry
from modules.proxy_manager import ProxyManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("single_video_processor.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Create download directory if it doesn't exist
Path(DOWNLOAD_DIR).mkdir(exist_ok=True)


def get_video_url_from_user():
    """Get video URL from user via command line input."""
    try:
        print("\n" + "="*60)
        print("LEGISLATURE VIDEO PROCESSOR")
        print("="*60)
        print("\nEnter the video page URL:")
        print("Example: https://sg001-harmony.sliq.net/00293/Harmony/en/PowerBrowser/PowerBrowserV2/20250522/-1/77330")
        print("")
        
        url = input("Video URL: ").strip()
        
        if not url:
            print("No URL provided.")
            return None
            
        return url
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        return None
    except Exception as e:
        logger.error(f"Error getting URL from user: {e}")
        return None


def get_meeting_title_from_user():
    """Get meeting title from user via command line input."""
    try:
        print("\n" + "-"*60)
        print("Enter the meeting title:")
        print("Example: IC - Water and Natural Resources Committee")
        print("(This will be used for file naming and organization)")
        print("")
        
        title = input("Meeting Title: ").strip()
        
        if not title:
            print("No title provided.")
            return None
            
        return title
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        return None
    except Exception as e:
        logger.error(f"Error getting title from user: {e}")
        return None


def process_single_video(video_url, meeting_title, proxy_manager):
    """Process a single video: download, transcribe, and save to Nextcloud."""
    try:
        logger.info(f"Processing video: {video_url}")
        logger.info(f"Meeting title: {meeting_title}")
        
        # Create entry object similar to what main.py uses
        entry = {
            'link': video_url,
            'text': meeting_title,
            'timestamp': datetime.datetime.now().isoformat()
        }
        
        if not entry.get('link'):
            logger.error("No video URL provided")
            return None
        
        # Download video
        logger.info("Starting video download...")
        video_path = download_video(entry['link'], proxy_manager=proxy_manager)
        if not video_path:
            logger.error("Failed to download video")
            return None
        
        # Extract audio
        logger.info("Extracting audio from video...")
        audio_path = extract_audio_from_video(video_path)
        if not audio_path:
            logger.error("Failed to extract audio")
            return None
        
        # Transcribe with WhisperX (using optimized settings)
        logger.info("Starting transcription with WhisperX (optimized mode)...")
        transcript_data = transcribe_with_whisperx(audio_path, model_size="base")
        if not transcript_data:
            logger.error("Failed to transcribe audio")
            return None
        
        # Get committee members for speaker identification
        logger.info("Getting committee members for speaker identification...")
        committee_members = get_committee_members_for_meeting(entry['text'])
        
        # Identify speakers in transcript
        logger.info("Identifying speakers in transcript...")
        enhanced_transcript = identify_speakers_in_transcript(
            transcript_data, committee_members
        )
        
        # Clean title for use in filename and document
        title_text = entry['text']
        clean_title = re.sub(r'\s+', ' ', title_text).strip()
        
        # Save to Nextcloud
        logger.info("Saving transcript to Nextcloud...")
        nextcloud_result = save_transcript_to_nextcloud(
            enhanced_transcript, clean_title, entry['link']
        )
        
        if nextcloud_result:
            logger.info(f"Successfully saved to Nextcloud: {nextcloud_result['nextcloud_path']}")
            if nextcloud_result.get('share_link'):
                logger.info(f"Share link: {nextcloud_result['share_link']}")
        
        # Store processing information
        entry['transcription'] = {
            'video_path': video_path,
            'audio_path': audio_path,
            'nextcloud_result': nextcloud_result,
            'processed_at': datetime.datetime.now().isoformat()
        }
        
        # Write to processed entries log
        write_processed_entry(entry)
        
        # Send notification email (optional)
        try:
            logger.info("Sending notification email...")
            send_notification([entry], [nextcloud_result])
        except Exception as e:
            logger.warning(f"Failed to send notification email: {e}")
        
        return nextcloud_result
    
    except Exception as e:
        logger.error(f"Error processing video: {e}")
        return None


def show_result_message(result):
    """Show processing result to user."""
    try:
        print("\n" + "="*60)
        
        if result:
            print("✅ VIDEO PROCESSED SUCCESSFULLY!")
            print("="*60)
            print(f"Saved to: {result['nextcloud_path']}")
            print(f"Filename: {result['filename']}")
            if result.get('share_link'):
                print(f"Share link: {result['share_link']}")
        else:
            print("❌ FAILED TO PROCESS VIDEO")
            print("="*60)
            print("Check the logs for details.")
            
        print("="*60)
        
    except Exception as e:
        logger.error(f"Error showing result message: {e}")


def main():
    """Main function for single video processing."""
    logger.info("=== Legislature Single Video Processor ===")
    
    # Check dependencies
    if not all([NEXTCLOUD_URL, NEXTCLOUD_USERNAME, NEXTCLOUD_TOKEN]):
        logger.error("Nextcloud configuration missing. Please check your .env file")
        print("❌ Configuration Error: Nextcloud configuration missing. Please check your .env file")
        return
    
    if not HF_TOKEN:
        logger.warning("Hugging Face token not found. Speaker diarization may not work properly.")
    
    # Initialize proxy manager
    logger.info("Initializing proxy system...")
    proxy_manager = ProxyManager()
    
    # Test proxy connection
    if not proxy_manager.test_proxy_connection():
        logger.warning("Failed to connect to proxy. Will attempt to run without proxy.")
    else:
        logger.info("Proxy system initialized successfully")
    
    # Get video URL from user
    video_url = get_video_url_from_user()
    if not video_url:
        logger.info("No URL provided, exiting")
        return
    
    # Get meeting title from user
    meeting_title = get_meeting_title_from_user()
    if not meeting_title:
        logger.info("No meeting title provided, exiting")
        return
    
    # Validate URL format
    if not video_url.startswith(('http://', 'https://')):
        logger.error("Invalid URL format")
        print("❌ Invalid URL: Please provide a valid HTTP/HTTPS URL")
        return
    
    logger.info(f"Processing video from: {video_url}")
    logger.info(f"Meeting title: {meeting_title}")
    
    # Process the video
    result = process_single_video(video_url, meeting_title, proxy_manager)
    
    # Show result to user
    show_result_message(result)
    
    if result:
        logger.info("=== Video processing completed successfully! ===")
    else:
        logger.error("=== Video processing failed! ===")


if __name__ == "__main__":
    main()