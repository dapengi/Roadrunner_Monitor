"""
Transcript uploader for Seafile.
Uploads JSON, CSV, and TXT transcripts to organized folders.
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

from modules.seafile_client import SeafileClient
from config import SEAFILE_BASE_FOLDER

logger = logging.getLogger(__name__)


class TranscriptUploader:
    """Uploads transcript files to Seafile with proper organization."""

    def __init__(self, seafile_client: SeafileClient = None):
        """
        Initialize the uploader.

        Args:
            seafile_client: Optional SeafileClient instance (creates one if not provided)
        """
        self.client = seafile_client or SeafileClient()

    def generate_filename(self, committee: str, meeting_date: datetime,
                         start_time: str = None, end_time: str = None,
                         extension: str = "json") -> str:
        """
        Generate filename following the format:
        YYYYMMDD-PREFIX-ACRONYM-STARTTIMEAM-ENDTIMEPM.ext

        Args:
            committee: Committee name/acronym
            meeting_date: Date of the meeting
            start_time: Start time (e.g., "9:14 AM")
            end_time: End time (e.g., "12:06 PM")
            extension: File extension (json, csv, txt)

        Returns:
            Formatted filename
        """
        date_str = meeting_date.strftime("%Y%m%d")

        # Default times if not provided
        if not start_time:
            start_time = "9:00 AM"
        if not end_time:
            end_time = "12:00 PM"

        # Format times (remove spaces and colons)
        start_str = start_time.replace(":", "").replace(" ", "")
        end_str = end_time.replace(":", "").replace(" ", "")

        # Determine prefix (IC = Interim Committee, HC = House Committee, SC = Senate Committee)
        prefix = "IC"  # Default to interim

        filename = f"{date_str}-{prefix}-{committee}-{start_str}-{end_str}.{extension}"
        return filename

    def get_seafile_path(self, committee: str, meeting_date: datetime,
                        committee_type: str = "Interim") -> str:
        """
        Get the Seafile folder path for a meeting.

        Format: /Legislative Transcription/Allison_Test/Interim/[COMMITTEE]/[YYYY-MM-DD]/

        Args:
            committee: Committee name/acronym
            meeting_date: Date of the meeting
            committee_type: Type (Interim, House, Senate)

        Returns:
            Seafile folder path
        """
        date_str = meeting_date.strftime("%Y-%m-%d")
        path = f"/{SEAFILE_BASE_FOLDER}/{committee_type}/{committee}/{date_str}"
        return path

    def upload_transcripts(self,
                          transcript_data: Dict[str, str],
                          committee: str,
                          meeting_date: datetime,
                          start_time: str = None,
                          end_time: str = None,
                          committee_type: str = "Interim") -> Dict[str, str]:
        """
        Upload all three transcript formats to Seafile.

        Args:
            transcript_data: Dictionary with 'json', 'csv', 'txt' keys containing formatted transcripts
            committee: Committee name/acronym (e.g., "CCJ", "LFC")
            meeting_date: Date of the meeting
            start_time: Meeting start time (e.g., "9:14 AM")
            end_time: Meeting end time (e.g., "12:06 PM")
            committee_type: Committee type ("Interim", "House", "Senate")

        Returns:
            Dictionary with status and file paths
        """
        try:
            # Get Seafile folder path
            folder_path = self.get_seafile_path(committee, meeting_date, committee_type)

            logger.info(f"Uploading transcripts to {folder_path}")

            # Ensure folder exists
            self.client.ensure_dir_exists(folder_path)

            uploaded_files = {}
            errors = []

            # Upload each format
            for format_type, content in transcript_data.items():
                try:
                    # Generate filename
                    filename = self.generate_filename(
                        committee, meeting_date, start_time, end_time, extension=format_type
                    )

                    # Full path in Seafile
                    file_path = f"{folder_path}/{filename}"

                    # Upload
                    success = self.client.write_file(file_path, content)

                    if success:
                        uploaded_files[format_type] = file_path
                        logger.info(f"✅ Uploaded {format_type.upper()}: {file_path}")
                    else:
                        errors.append(f"Failed to upload {format_type}")
                        logger.error(f"❌ Failed to upload {format_type}: {file_path}")

                except Exception as e:
                    errors.append(f"Error uploading {format_type}: {e}")
                    logger.error(f"❌ Error uploading {format_type}: {e}")

            # Create share link for the folder
            share_link = None
            try:
                share_link = self.client.get_share_link(folder_path)
                if share_link:
                    logger.info(f"📤 Share link: {share_link}")
            except Exception as e:
                logger.warning(f"Could not create share link: {e}")

            return {
                'success': len(errors) == 0,
                'uploaded_files': uploaded_files,
                'errors': errors,
                'folder_path': folder_path,
                'share_link': share_link
            }

        except Exception as e:
            logger.error(f"Error uploading transcripts: {e}")
            return {
                'success': False,
                'uploaded_files': {},
                'errors': [str(e)],
                'folder_path': None,
                'share_link': None
            }

    def upload_video(self, video_path: str, committee: str, meeting_date: datetime,
                    committee_type: str = "Interim") -> Optional[str]:
        """
        Upload video file to Seafile (optional).

        Args:
            video_path: Local path to video file
            committee: Committee name
            meeting_date: Meeting date
            committee_type: Committee type

        Returns:
            Seafile path if successful, None otherwise
        """
        try:
            folder_path = self.get_seafile_path(committee, meeting_date, committee_type)
            filename = os.path.basename(video_path)
            seafile_path = f"{folder_path}/{filename}"

            logger.info(f"Uploading video to {seafile_path}")

            success = self.client.upload_file(video_path, seafile_path)

            if success:
                logger.info(f"✅ Video uploaded: {seafile_path}")
                return seafile_path
            else:
                logger.error(f"❌ Video upload failed")
                return None

        except Exception as e:
            logger.error(f"Error uploading video: {e}")
            return None


def test_uploader():
    """Test the transcript uploader."""

    # Sample transcript data
    transcript_data = {
        'json': '{"text": "Test transcript", "words": [], "audio_events": []}',
        'csv': 'timestamp,speaker,text\n00:00:05,speaker_0,"Test text"',
        'txt': '00:00:05 | speaker_0 | Test text'
    }

    uploader = TranscriptUploader()

    # Test path generation
    test_date = datetime(2025, 1, 15)
    filename = uploader.generate_filename("CCJ", test_date, "9:14 AM", "12:06 PM", "json")
    print(f"Generated filename: {filename}")

    path = uploader.get_seafile_path("CCJ", test_date, "Interim")
    print(f"Seafile path: {path}")

    # Uncomment to test actual upload:
    # result = uploader.upload_transcripts(transcript_data, "CCJ", test_date, "9:14 AM", "12:06 PM")
    # print(f"Upload result: {result}")


if __name__ == "__main__":
    test_uploader()
