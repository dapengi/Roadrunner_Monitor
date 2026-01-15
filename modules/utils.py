# modules/utils.py

import os
import json
import datetime
import glob
import logging

from config import (
    ENTRIES_FILE, PROCESSED_ENTRIES_FILE, DOWNLOAD_DIR, CAPTIONS_DIR, LAST_CLEANUP_FILE
)

logger = logging.getLogger(__name__)

# Removed global proxy_config and proxy_working


def cleanup_downloads_directory():
    """Delete all files in the downloads directory."""
    try:
        files_pattern = os.path.join(DOWNLOAD_DIR, "*")
        files_to_delete = glob.glob(files_pattern)

        if not files_to_delete:
            logger.info("Downloads directory is already empty")
            return

        deleted_count = 0
        total_size = 0

        for file_path in files_to_delete:
            try:
                if os.path.isfile(file_path):
                    file_size = os.path.getsize(file_path)
                    total_size += file_size
                    os.remove(file_path)
                    deleted_count += 1
                    logger.info(f"Deleted: {os.path.basename(file_path)} ({file_size / (1024*1024):.2f} MB)")

            except Exception as e:
                logger.error(f"Error deleting {file_path}: {e}")

        logger.info(f"Cleanup completed: {deleted_count} files deleted, {total_size / (1024*1024):.2f} MB freed")

        with open(LAST_CLEANUP_FILE, 'w') as f:
            f.write(datetime.datetime.now().strftime('%Y-%m-%d'))

    except Exception as e:
        logger.error(f"Error during downloads cleanup: {e}")


def cleanup_captions_directory():
    """Delete all files in the captions directory."""
    try:
        files_pattern = os.path.join(CAPTIONS_DIR, "*")
        files_to_delete = glob.glob(files_pattern)

        if not files_to_delete:
            logger.info("Captions directory is already empty")
            return

        deleted_count = 0
        total_size = 0

        for file_path in files_to_delete:
            try:
                if os.path.isfile(file_path):
                    file_size = os.path.getsize(file_path)
                    total_size += file_size
                    os.remove(file_path)
                    deleted_count += 1
                    logger.info(f"Deleted: {os.path.basename(file_path)} ({file_size / (1024*1024):.2f} MB)")

            except Exception as e:
                logger.error(f"Error deleting {file_path}: {e}")

        logger.info(f"Cleanup completed: {deleted_count} files deleted, {total_size / (1024*1024):.2f} MB freed")

        with open(LAST_CLEANUP_FILE, 'w') as f:
            f.write(datetime.datetime.now().strftime('%Y-%m-%d'))

    except Exception as e:
        logger.error(f"Error during captions cleanup: {e}")


def should_run_daily_cleanup():
    """Check if daily cleanup should be run."""
    try:
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        
        if not os.path.exists(LAST_CLEANUP_FILE):
            return True
        
        with open(LAST_CLEANUP_FILE, 'r') as f:
            last_cleanup_date = f.read().strip()
        
        return last_cleanup_date != today
        
    except Exception as e:
        logger.error(f"Error checking cleanup date: {e}")
        return True


def read_stored_entries():
    """Read the previously stored entries."""
    if not os.path.exists(ENTRIES_FILE):
        return []
    
    try:
        with open(ENTRIES_FILE, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        logger.error(f"Error parsing {ENTRIES_FILE}, starting with empty entries")
        return []


def write_entries(entries):
    """Write entries to the storage file."""
    with open(ENTRIES_FILE, 'w') as f:
        json.dump(entries, f, indent=2)


def read_processed_entries():
    """Read the previously processed entries with error handling for format changes."""
    if not os.path.exists(PROCESSED_ENTRIES_FILE):
        return []
    
    try:
        with open(PROCESSED_ENTRIES_FILE, 'r') as f:
            content = f.read().strip()
            if not content:
                return []
            
            entries = json.loads(content)
            
            # Validate that entries is a list
            if not isinstance(entries, list):
                logger.error(f"Processed entries file contains invalid format (not a list), resetting...")
                return []
            
            # Check if entries have expected structure and clean up if needed
            valid_entries = []
            for entry in entries:
                if isinstance(entry, dict) and 'text' in entry:
                    # Convert old Google Docs format to new Nextcloud format if needed
                    if 'transcription' in entry:
                        transcription = entry['transcription']
                        if isinstance(transcription, dict):
                            # Update old google_doc_url to nextcloud_result format
                            if 'google_doc_url' in transcription and 'nextcloud_result' not in transcription:
                                transcription['nextcloud_result'] = {
                                    'legacy_google_doc': transcription.pop('google_doc_url'),
                                    'migrated_to_nextcloud': True
                                }
                    
                    valid_entries.append(entry)
                else:
                    logger.warning(f"Skipping invalid entry format: {entry}")
            
            return valid_entries
            
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing {PROCESSED_ENTRIES_FILE}: {e}")
        logger.info(f"Backing up corrupted file and starting fresh...")
        
        # Backup the corrupted file
        backup_file = f"{PROCESSED_ENTRIES_FILE}.backup.{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        try:
            os.rename(PROCESSED_ENTRIES_FILE, backup_file)
            logger.info(f"Backed up corrupted file to: {backup_file}")
        except Exception as backup_error:
            logger.error(f"Could not backup corrupted file: {backup_error}")
        
        return []
    except Exception as e:
        logger.error(f"Unexpected error reading processed entries: {e}")
        return []


def write_processed_entry(entry):
    """Add an entry to the processed entries file."""
    processed = read_processed_entries()
    processed.append(entry)
    
    with open(PROCESSED_ENTRIES_FILE, 'w') as f:
        json.dump(processed, f, indent=2)


def is_test_meeting(entry_text):
    """Check if an entry is a test meeting that should be skipped."""
    # Convert to lowercase for case-insensitive matching
    text_lower = entry_text.lower()

    # Check for "test meeting" anywhere in the text
    if "test meeting" in text_lower:
        return True

    return False


# Retry tracking for failed entries
RETRY_COUNTS_FILE = os.path.join(os.path.dirname(ENTRIES_FILE), "retry_counts.json")
MAX_RETRY_COUNT = 3


def read_retry_counts():
    """Read the retry counts tracking file."""
    if not os.path.exists(RETRY_COUNTS_FILE):
        return {}

    try:
        with open(RETRY_COUNTS_FILE, 'r') as f:
            content = f.read().strip()
            if not content:
                return {}
            return json.loads(content)
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing {RETRY_COUNTS_FILE}: {e}")
        return {}
    except Exception as e:
        logger.error(f"Error reading retry counts: {e}")
        return {}


def write_retry_counts(retry_counts):
    """Write retry counts to the tracking file."""
    try:
        with open(RETRY_COUNTS_FILE, 'w') as f:
            json.dump(retry_counts, f, indent=2)
    except Exception as e:
        logger.error(f"Error writing retry counts: {e}")


def get_retry_count(entry_link):
    """Get the current retry count for an entry."""
    retry_counts = read_retry_counts()
    entry_data = retry_counts.get(entry_link, {})
    return entry_data.get('count', 0)


def increment_retry_count(entry_link, reason="Unknown"):
    """
    Increment retry count for an entry and return the new count.

    Args:
        entry_link: The URL of the entry
        reason: The reason for the failure

    Returns:
        The new retry count after incrementing
    """
    retry_counts = read_retry_counts()

    if entry_link not in retry_counts:
        retry_counts[entry_link] = {
            'count': 0,
            'first_failure': datetime.datetime.now().isoformat(),
            'failures': []
        }

    retry_counts[entry_link]['count'] += 1
    retry_counts[entry_link]['last_failure'] = datetime.datetime.now().isoformat()
    retry_counts[entry_link]['last_reason'] = reason
    retry_counts[entry_link]['failures'].append({
        'timestamp': datetime.datetime.now().isoformat(),
        'reason': reason
    })

    new_count = retry_counts[entry_link]['count']
    write_retry_counts(retry_counts)

    logger.info(f"Retry count for entry: {new_count}/{MAX_RETRY_COUNT} (reason: {reason})")

    return new_count


def clear_retry_count(entry_link):
    """Clear retry count for an entry after successful processing."""
    retry_counts = read_retry_counts()

    if entry_link in retry_counts:
        del retry_counts[entry_link]
        write_retry_counts(retry_counts)
        logger.info(f"Cleared retry count for successfully processed entry")


def has_exceeded_max_retries(entry_link):
    """Check if an entry has exceeded the maximum retry count."""
    return get_retry_count(entry_link) >= MAX_RETRY_COUNT


