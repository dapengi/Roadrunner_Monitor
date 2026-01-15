"""
Pushover Notifications Module

Sends push notifications for:
- Successful video processing completions
- Processing failures
- Daily summaries
"""

import os
import json
import logging
import requests
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Pushover API configuration
PUSHOVER_API_URL = "https://api.pushover.net/1/messages.json"
PUSHOVER_API_TOKEN = os.getenv("PUSHOVER_API_TOKEN")
PUSHOVER_USER_KEY = os.getenv("PUSHOVER_USER_KEY")

# Daily stats file for tracking
STATS_FILE = Path(__file__).parent.parent / "data" / "daily_stats.json"


def _send_pushover(message: str, title: str = None, priority: int = 0, url: str = None, url_title: str = None) -> bool:
    """
    Send a notification via Pushover API.
    
    Args:
        message: The notification message body
        title: Optional title (defaults to app name)
        priority: -2 to 2 (-2=lowest, 0=normal, 1=high, 2=emergency)
        url: Optional supplementary URL
        url_title: Optional title for the URL
    
    Returns:
        True if successful, False otherwise
    """
    if not PUSHOVER_API_TOKEN or not PUSHOVER_USER_KEY:
        logger.error("Pushover credentials not configured in .env file")
        return False
    
    payload = {
        "token": PUSHOVER_API_TOKEN,
        "user": PUSHOVER_USER_KEY,
        "message": message,
        "priority": priority,
    }
    
    if title:
        payload["title"] = title
    
    if url:
        payload["url"] = url
        if url_title:
            payload["url_title"] = url_title
    
    try:
        response = requests.post(PUSHOVER_API_URL, data=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if result.get("status") == 1:
                logger.info(f"Pushover notification sent successfully: {title or 'No title'}")
                return True
            else:
                logger.error(f"Pushover API error: {result.get('errors', 'Unknown error')}")
                return False
        else:
            logger.error(f"Pushover HTTP error {response.status_code}: {response.text}")
            return False
            
    except requests.RequestException as e:
        logger.error(f"Failed to send Pushover notification: {e}")
        return False


def notify_success(committee: str, meeting_date: str, meeting_time: str, 
                   processing_duration: float, filename: str = None) -> bool:
    """
    Send notification for successful video processing.
    
    Args:
        committee: Committee name (e.g., "House Appropriations and Finance")
        meeting_date: Meeting date string (e.g., "January 12, 2026")
        meeting_time: Meeting time range (e.g., "9:11 AM - 12:31 PM")
        processing_duration: Processing time in seconds
        filename: Optional uploaded filename
    
    Returns:
        True if notification sent successfully
    """
    # Format duration nicely
    duration_mins = int(processing_duration // 60)
    duration_secs = int(processing_duration % 60)
    if duration_mins > 0:
        duration_str = f"{duration_mins}m {duration_secs}s"
    else:
        duration_str = f"{duration_secs}s"
    
    message = f"Committee: {committee}\n"
    message += f"Date: {meeting_date}\n"
    message += f"Time: {meeting_time}\n"
    message += f"Processing Duration: {duration_str}"
    
    if filename:
        message += f"\nFile: {filename}"
    
    title = "✓ Video Processed Successfully"
    
    # Track success for daily summary
    _track_stats("success", {
        "committee": committee,
        "meeting_date": meeting_date,
        "meeting_time": meeting_time,
        "processing_duration": processing_duration,
        "filename": filename
    })
    
    return _send_pushover(message, title=title, priority=0)


def notify_failure(committee: str, meeting_date: str, meeting_time: str,
                   error_stage: str, error_message: str) -> bool:
    """
    Send notification for processing failure.
    
    Args:
        committee: Committee name
        meeting_date: Meeting date string
        meeting_time: Meeting time range
        error_stage: Stage where failure occurred (download, transcription, upload, etc.)
        error_message: Description of the error
    
    Returns:
        True if notification sent successfully
    """
    message = f"Committee: {committee}\n"
    message += f"Date: {meeting_date}\n"
    message += f"Time: {meeting_time}\n"
    message += f"Stage: {error_stage}\n"
    message += f"Error: {error_message}"
    
    title = "✗ Processing Failed"
    
    # Track failure for daily summary
    _track_stats("failure", {
        "committee": committee,
        "meeting_date": meeting_date,
        "meeting_time": meeting_time,
        "error_stage": error_stage,
        "error_message": error_message
    })
    
    return _send_pushover(message, title=title, priority=1)


def notify_failure_simple(error_stage: str, error_message: str, context: str = None) -> bool:
    """
    Send notification for failures where meeting info isn't available.
    
    Args:
        error_stage: Stage where failure occurred
        error_message: Description of the error
        context: Additional context about what was being processed
    
    Returns:
        True if notification sent successfully
    """
    message = f"Stage: {error_stage}\n"
    message += f"Error: {error_message}"
    
    if context:
        message += f"\nContext: {context}"
    
    title = "✗ Processing Failed"
    
    # Track failure for daily summary
    _track_stats("failure", {
        "error_stage": error_stage,
        "error_message": error_message,
        "context": context
    })
    
    return _send_pushover(message, title=title, priority=1)


def _track_stats(event_type: str, details: dict) -> None:
    """
    Track processing stats for daily summary.
    
    Args:
        event_type: "success" or "failure"
        details: Event details dictionary
    """
    try:
        # Ensure data directory exists
        STATS_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing stats or create new
        if STATS_FILE.exists():
            with open(STATS_FILE, "r") as f:
                stats = json.load(f)
        else:
            stats = {"successes": [], "failures": [], "date": None}
        
        # Check if we need to reset for a new day
        today = datetime.now().strftime("%Y-%m-%d")
        if stats.get("date") != today:
            stats = {"successes": [], "failures": [], "date": today}
        
        # Add event with timestamp
        details["timestamp"] = datetime.now().isoformat()
        
        if event_type == "success":
            stats["successes"].append(details)
        else:
            stats["failures"].append(details)
        
        # Save stats
        with open(STATS_FILE, "w") as f:
            json.dump(stats, f, indent=2)
            
    except Exception as e:
        logger.error(f"Failed to track stats: {e}")


def send_daily_summary() -> bool:
    """
    Send daily summary of processing activity.
    Called by cron job at 9pm MST.
    
    Returns:
        True if notification sent successfully
    """
    try:
        if not STATS_FILE.exists():
            message = "No processing activity today."
            title = "📊 Daily Summary"
            return _send_pushover(message, title=title, priority=-1)
        
        with open(STATS_FILE, "r") as f:
            stats = json.load(f)
        
        today = datetime.now().strftime("%Y-%m-%d")
        if stats.get("date") != today:
            message = "No processing activity today."
            title = "📊 Daily Summary"
            return _send_pushover(message, title=title, priority=-1)
        
        successes = stats.get("successes", [])
        failures = stats.get("failures", [])
        
        success_count = len(successes)
        failure_count = len(failures)
        total = success_count + failure_count
        
        if total == 0:
            message = "No processing activity today."
        else:
            message = f"Videos Processed: {success_count}\n"
            message += f"Failures: {failure_count}\n"
            
            if success_count > 0:
                # Calculate total processing time
                total_duration = sum(s.get("processing_duration", 0) for s in successes)
                total_mins = int(total_duration // 60)
                message += f"Total Processing Time: {total_mins} minutes\n"
                
                # List successful committees
                committees = [s.get("committee", "Unknown") for s in successes]
                message += f"\nCompleted:\n"
                for comm in committees:
                    message += f"  • {comm}\n"
            
            if failure_count > 0:
                message += f"\nFailed:\n"
                for f in failures:
                    stage = f.get("error_stage", "Unknown")
                    comm = f.get("committee", f.get("context", "Unknown"))
                    message += f"  • {comm} ({stage})\n"
        
        title = "📊 Daily Summary"
        priority = 0 if failure_count == 0 else 1
        
        result = _send_pushover(message, title=title, priority=priority)
        
        # Clear stats file after sending summary
        if result:
            STATS_FILE.unlink(missing_ok=True)
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to send daily summary: {e}")
        return False


def test_notification() -> bool:
    """
    Send a test notification to verify Pushover is configured correctly.
    
    Returns:
        True if test notification sent successfully
    """
    message = "Pushover integration is working correctly!\n"
    message += f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    title = "🔔 Test Notification"
    
    return _send_pushover(message, title=title, priority=0)


if __name__ == "__main__":
    # Test the module
    logging.basicConfig(level=logging.INFO)
    print("Testing Pushover notification...")
    
    if test_notification():
        print("Test notification sent successfully!")
    else:
        print("Failed to send test notification. Check credentials.")
