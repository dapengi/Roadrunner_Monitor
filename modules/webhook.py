#!/usr/bin/env python3
"""
N8N Webhook Module
Sends transcription completion notifications to n8n workflow for client report processing
"""

import logging
import requests
from typing import Dict, Optional
from config import (
    N8N_WEBHOOK_URL_PROD,
    N8N_WEBHOOK_URL_TEST,
    N8N_WEBHOOK_ENABLED,
    N8N_WEBHOOK_MODE
)

logger = logging.getLogger(__name__)


def send_transcription_webhook(transcription_result: Dict, test_mode: Optional[bool] = None) -> bool:
    """
    Send transcription completion webhook to n8n for client report processing.

    Args:
        transcription_result: Dict containing transcription metadata with keys:
            - filename: Name of the transcript file
            - folder_path: Path in Seafile/storage
            - meeting_info: Dict with committee, date, time info
            - seafile_result: Dict with share_link, nextcloud_path, etc.
            - processed_at: Timestamp of processing
            - Additional metadata (processing_time, caption_length, etc.)
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

    # Build webhook payload with all relevant data
    payload = {
        "filename": transcription_result.get("filename", "unknown"),
        "folder_path": transcription_result.get("folder_path", ""),
        "meeting_info": transcription_result.get("meeting_info", {}),
        "processed_at": transcription_result.get("processed_at", ""),
    }

    # Add Seafile/share link info if available
    if "seafile_result" in transcription_result:
        seafile_result = transcription_result["seafile_result"]
        payload.update({
            "share_link": seafile_result.get("share_link", ""),
            "seafile_path": seafile_result.get("nextcloud_path", ""),  # Using nextcloud_path for compatibility
            "meeting_date": seafile_result.get("meeting_date", ""),
            "meeting_time": seafile_result.get("meeting_time", ""),
        })

    # Add processing metrics if available
    if "processing_time_seconds" in transcription_result:
        payload["processing_time_seconds"] = transcription_result["processing_time_seconds"]

    if "caption_length" in transcription_result:
        payload["caption_length"] = transcription_result["caption_length"]

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
            logger.info(f"✅ {mode_label} webhook sent successfully to n8n")
            logger.debug(f"Response: {response.text[:200] if response.text else '(empty response)'}")
            return True
        else:
            logger.warning(f"⚠️ Webhook returned error status: {response.status_code}")
            logger.warning(f"Response: {response.text[:500]}")
            return False

    except requests.exceptions.Timeout:
        logger.error(f"❌ Webhook timeout after 30 seconds")
        return False
    except requests.exceptions.ConnectionError as e:
        logger.error(f"❌ Webhook connection error: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error sending webhook: {e}", exc_info=True)
        return False


def send_test_webhook() -> bool:
    """
    Send a test webhook to verify n8n connectivity.

    Returns:
        bool: True if test webhook succeeded
    """
    test_payload = {
        "filename": "TEST-20260119-IC-TEST-900AM-1000AM.txt",
        "folder_path": "Legislative Transcription/Test",
        "meeting_info": {
            "committee_name": "Test Committee",
            "committee_acronym": "TEST",
            "type": "test",
            "chamber": None,
        },
        "seafile_result": {
            "share_link": "https://seafile.dapengi.party/d/test123456/",
            "txt_file_path": "Legislative Transcription/Test/TEST-20260119-IC-TEST-900AM-1000AM.txt",
            "nextcloud_path": "Legislative Transcription/Test",
            "meeting_date": "January 19, 2026",
            "meeting_time": "900AM - 1000AM"
        },
        "processed_at": "2026-01-19T00:00:00",
        "processing_time_seconds": 100.5,
        "segments_count": 50,
        "speakers_count": 3,
        "test_webhook": True
    }

    logger.info("Sending TEST webhook to n8n")
    return send_transcription_webhook(test_payload, test_mode=True)
