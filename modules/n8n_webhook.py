"""
N8N Webhook integration for notifying about new manifest files.
Sends a fire-and-forget POST to n8n when a meeting is processed and manifest uploaded.
"""

import logging
import json
from datetime import datetime
from typing import Dict, Optional, List

# httpx is optional - only used for async version
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

logger = logging.getLogger(__name__)


def create_manifest(
    committee: str,
    meeting_date: str,
    base_name: str,
    uploaded_files: Dict[str, str],
    session_type: str = "IC",
    start_time: str = None,
    end_time: str = None,
    segments_count: int = 0,
    speakers_count: int = 0
) -> Dict:
    """
    Create a manifest dictionary describing the uploaded files.

    Args:
        committee: Committee acronym (e.g., "LFC", "CCJ")
        meeting_date: Meeting date in YYYY-MM-DD format
        base_name: Base filename without extension
        uploaded_files: Dict mapping format -> Seafile path (e.g., {"json": "/Interim/LFC/2025-01-19/captions/file.json"})
        session_type: "IC" for interim, "HOUSE", or "SENATE"
        start_time: Meeting start time
        end_time: Meeting end time
        segments_count: Number of transcript segments
        speakers_count: Number of unique speakers

    Returns:
        Manifest dict
    """
    manifest = {
        "version": "1.0",
        "created_at": datetime.now().isoformat(),
        "meeting": {
            "committee": committee,
            "date": meeting_date,
            "session_type": session_type,
            "start_time": start_time,
            "end_time": end_time
        },
        "transcript": {
            "base_name": base_name,
            "segments_count": segments_count,
            "speakers_count": speakers_count
        },
        "files": []
    }

    for fmt, path in uploaded_files.items():
        manifest["files"].append({
            "format": fmt,
            "path": path,
            "filename": f"{base_name}.{fmt}"
        })

    return manifest


def get_manifest_path(session_type: str, committee: str, meeting_date: str) -> str:
    """
    Get the Seafile path for the manifest file.

    Args:
        session_type: "IC" for interim, "HOUSE", or "SENATE"
        committee: Committee acronym
        meeting_date: Date in YYYY-MM-DD format

    Returns:
        Path like /Interim/CCJ/2025-01-19/manifests/manifest.json
    """
    if session_type == "IC":
        return f"/Interim/{committee}/{meeting_date}/manifests/manifest.json"
    else:
        return f"/Session/{session_type}/{committee}/{meeting_date}/manifests/manifest.json"


async def send_webhook_async(
    committee: str,
    date: str,
    manifest_path: str,
    seafile_url: str = None,
    seafile_library_id: str = None,
    seafile_token: str = None,
    webhook_url: str = None,
    source: str = "roadrunner_monitor",
    timeout: int = 10
) -> bool:
    """
    Send webhook notification to n8n (async version).
    Requires httpx to be installed. Falls back to sync version if not available.

    Args:
        committee: Committee acronym (e.g., "CCJ", "LFC")
        date: Meeting date in YYYY-MM-DD format
        manifest_path: Path to manifest within Seafile (e.g., "/Interim/CCJ/2025-01-19/manifests/manifest.json")
        seafile_url: Seafile server URL (defaults to config)
        seafile_library_id: Seafile library ID (defaults to config)
        seafile_token: Seafile API token (defaults to config)
        webhook_url: n8n webhook URL (defaults to config)
        source: Identifier for sending system
        timeout: Request timeout in seconds

    Returns:
        True if webhook acknowledged (200/202), False otherwise
    """
    if not HTTPX_AVAILABLE:
        logger.warning("httpx not installed, falling back to sync webhook")
        return send_webhook(
            committee, date, manifest_path, seafile_url,
            seafile_library_id, seafile_token, webhook_url, source, timeout
        )

    from config import (
        SEAFILE_URL, SEAFILE_LIBRARY_ID, SEAFILE_API_TOKEN,
        N8N_WEBHOOK_URL, N8N_WEBHOOK_TIMEOUT
    )

    # Use config defaults if not provided
    seafile_url = seafile_url or SEAFILE_URL
    seafile_library_id = seafile_library_id or SEAFILE_LIBRARY_ID
    seafile_token = seafile_token or SEAFILE_API_TOKEN
    webhook_url = webhook_url or N8N_WEBHOOK_URL
    timeout = timeout or N8N_WEBHOOK_TIMEOUT

    payload = {
        "committee": committee,
        "date": date,
        "library_id": seafile_library_id,
        "manifest_path": manifest_path,
        "seafile_url": seafile_url,
        "seafile_token": seafile_token,
        "source": source,
        "timestamp": datetime.now().isoformat()
    }

    logger.info(f"Sending webhook to {webhook_url}")
    logger.debug(f"Webhook payload: {json.dumps(payload, indent=2)}")

    try:
        async with httpx.AsyncClient(timeout=float(timeout)) as client:
            response = await client.post(webhook_url, json=payload)

            if response.status_code in [200, 202]:
                logger.info(f"Webhook sent successfully: {response.status_code}")
                return True
            else:
                logger.error(f"Webhook failed: {response.status_code} - {response.text[:200]}")
                return False

    except httpx.TimeoutException:
        logger.error(f"Webhook timed out after {timeout}s - n8n may not be responding")
        return False
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return False


def send_webhook(
    committee: str,
    date: str,
    manifest_path: str,
    seafile_url: str = None,
    seafile_library_id: str = None,
    seafile_token: str = None,
    webhook_url: str = None,
    source: str = "roadrunner_monitor",
    timeout: int = 10
) -> bool:
    """
    Send webhook notification to n8n (sync version using requests).

    Args:
        committee: Committee acronym (e.g., "CCJ", "LFC")
        date: Meeting date in YYYY-MM-DD format
        manifest_path: Path to manifest within Seafile (e.g., "/Interim/CCJ/2025-01-19/manifests/manifest.json")
        seafile_url: Seafile server URL (defaults to config)
        seafile_library_id: Seafile library ID (defaults to config)
        seafile_token: Seafile API token (defaults to config)
        webhook_url: n8n webhook URL (defaults to config)
        source: Identifier for sending system
        timeout: Request timeout in seconds

    Returns:
        True if webhook acknowledged (200/202), False otherwise
    """
    import requests
    from config import (
        SEAFILE_URL, SEAFILE_LIBRARY_ID, SEAFILE_API_TOKEN,
        N8N_WEBHOOK_URL, N8N_WEBHOOK_TIMEOUT
    )

    # Use config defaults if not provided
    seafile_url = seafile_url or SEAFILE_URL
    seafile_library_id = seafile_library_id or SEAFILE_LIBRARY_ID
    seafile_token = seafile_token or SEAFILE_API_TOKEN
    webhook_url = webhook_url or N8N_WEBHOOK_URL
    timeout = timeout or N8N_WEBHOOK_TIMEOUT

    payload = {
        "committee": committee,
        "date": date,
        "library_id": seafile_library_id,
        "manifest_path": manifest_path,
        "seafile_url": seafile_url,
        "seafile_token": seafile_token,
        "source": source,
        "timestamp": datetime.now().isoformat()
    }

    logger.info(f"Sending webhook to {webhook_url}")
    logger.debug(f"Webhook payload: committee={committee}, date={date}, manifest_path={manifest_path}")

    try:
        response = requests.post(
            webhook_url,
            json=payload,
            timeout=timeout,
            headers={"Content-Type": "application/json"}
        )

        if response.status_code in [200, 202]:
            logger.info(f"Webhook sent successfully: {response.status_code}")
            return True
        else:
            logger.error(f"Webhook failed: {response.status_code} - {response.text[:200]}")
            return False

    except requests.Timeout:
        logger.error(f"Webhook timed out after {timeout}s - n8n may not be responding")
        return False
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return False
