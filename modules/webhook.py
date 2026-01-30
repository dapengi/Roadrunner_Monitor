#!/usr/bin/env python3
"""
N8N Webhook Module
Sends transcription completion notifications to n8n workflow for client report processing
"""

import logging
import requests
import datetime
from typing import Dict, Optional, List
from config import (
    N8N_WEBHOOK_URL_PROD,
    N8N_WEBHOOK_URL_TEST,
    N8N_WEBHOOK_ENABLED,
    N8N_WEBHOOK_MODE
)

logger = logging.getLogger(__name__)

WEBHOOK_VERSION = "1.0"


def send_transcription_webhook(webhook_data: Dict, test_mode: Optional[bool] = None) -> bool:
    """
    Send transcription completion webhook to n8n for client report processing.

    Args:
        webhook_data: Dict containing transcription data with keys:
            - meeting: Dict with committee, date, session_type, start_time, end_time
            - transcript: Dict with base_name, segments_count, speakers_count
            - files: List of dicts with format, path, filename
        test_mode: Override to use test webhook URL (None = use N8N_WEBHOOK_MODE config)

    Returns:
        bool: True if webhook sent successfully, False otherwise
    """
    if not N8N_WEBHOOK_ENABLED:
        logger.info("N8N webhook disabled in configuration")
        return True

    # Determine which webhook URL to use
    if test_mode is None:
        use_test = N8N_WEBHOOK_MODE.lower() == "test"
    else:
        use_test = test_mode

    webhook_url = N8N_WEBHOOK_URL_TEST if use_test else N8N_WEBHOOK_URL_PROD
    mode_label = "TEST" if use_test else "PRODUCTION"

    logger.info(f"Sending {mode_label} webhook to n8n: {webhook_url}")

    # Build webhook payload in the expected n8n format
    payload = {
        "version": WEBHOOK_VERSION,
        "created_at": webhook_data.get("created_at", datetime.datetime.now().isoformat()),
        "meeting": webhook_data.get("meeting", {}),
        "transcript": webhook_data.get("transcript", {}),
        "files": webhook_data.get("files", []),
    }

    # Add share_link if available (for convenience)
    if "share_link" in webhook_data:
        payload["share_link"] = webhook_data["share_link"]

    logger.debug(f"Webhook payload: {payload}")

    try:
        response = requests.post(
            webhook_url,
            json=payload,
            timeout=30,
            headers={"Content-Type": "application/json"}
        )

        logger.info(f"Webhook response status: {response.status_code}")

        # Accept 200 (OK) and 202 (Accepted) as success codes
        if response.status_code in [200, 202]:
            logger.info(f"Webhook sent successfully to n8n ({mode_label})")
            logger.debug(f"Response: {response.text[:200] if response.text else '(empty response)'}")
            return True
        else:
            logger.warning(f"Webhook returned error status: {response.status_code}")
            logger.warning(f"Response: {response.text[:500]}")
            return False

    except requests.exceptions.Timeout:
        logger.error(f"Webhook timeout after 30 seconds")
        return False
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Webhook connection error: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error sending webhook: {e}", exc_info=True)
        return False


def build_webhook_payload(
    committee: str,
    meeting_date: datetime.date,
    session_type: str,
    start_time: str,
    end_time: str,
    base_name: str,
    segments_count: int,
    speakers_count: int,
    seafile_base_path: str,
    share_link: str = ""
) -> Dict:
    """
    Build a webhook payload in the expected n8n format.

    Args:
        committee: Committee acronym (e.g., "LFC", "HAFC")
        meeting_date: Date of the meeting
        session_type: Session type code (e.g., "IC" for interim)
        start_time: Start time string (e.g., "900AM")
        end_time: End time string (e.g., "1130AM")
        base_name: Base filename without extension
        segments_count: Number of transcript segments
        speakers_count: Number of unique speakers
        seafile_base_path: Seafile folder path
        share_link: Optional public share link for txt file

    Returns:
        Dict: Formatted webhook payload
    """
    # Format date as YYYY-MM-DD string
    date_str = meeting_date.strftime("%Y-%m-%d") if hasattr(meeting_date, 'strftime') else str(meeting_date)

    # Build files list
    files = []
    for fmt in ["json", "csv", "txt"]:
        files.append({
            "format": fmt,
            "path": f"{seafile_base_path}/{base_name}.{fmt}",
            "filename": f"{base_name}.{fmt}"
        })

    payload = {
        "created_at": datetime.datetime.now().isoformat(),
        "meeting": {
            "committee": committee,
            "date": date_str,
            "session_type": session_type,
            "start_time": start_time,
            "end_time": end_time
        },
        "transcript": {
            "base_name": base_name,
            "segments_count": segments_count,
            "speakers_count": speakers_count
        },
        "files": files
    }

    if share_link:
        payload["share_link"] = share_link

    return payload


def send_test_webhook() -> bool:
    """
    Send a test webhook to verify n8n connectivity.

    Returns:
        bool: True if test webhook succeeded
    """
    test_payload = {
        "version": WEBHOOK_VERSION,
        "created_at": datetime.datetime.now().isoformat(),
        "meeting": {
            "committee": "TEST",
            "date": "2026-01-19",
            "session_type": "IC",
            "start_time": "1000AM",
            "end_time": "1030AM"
        },
        "transcript": {
            "base_name": "20260119-IC-TEST-1000AM-1030AM",
            "segments_count": 1,
            "speakers_count": 0
        },
        "files": [
            {
                "format": "json",
                "path": "/Interim/TEST/2026-01-19/captions/20260119-IC-TEST-1000AM-1030AM.json",
                "filename": "20260119-IC-TEST-1000AM-1030AM.json"
            },
            {
                "format": "csv",
                "path": "/Interim/TEST/2026-01-19/captions/20260119-IC-TEST-1000AM-1030AM.csv",
                "filename": "20260119-IC-TEST-1000AM-1030AM.csv"
            },
            {
                "format": "txt",
                "path": "/Interim/TEST/2026-01-19/captions/20260119-IC-TEST-1000AM-1030AM.txt",
                "filename": "20260119-IC-TEST-1000AM-1030AM.txt"
            }
        ],
        "share_link": "https://seafile.dapengi.party/d/test123456/"
    }

    logger.info("Sending TEST webhook to n8n")
    return send_transcription_webhook(test_payload, test_mode=True)
