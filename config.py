#!/usr/bin/env python3.12
"""
Configuration settings for the Legislature Monitoring System
Contains all environment variables, constants, and configuration settings
"""

import os
import datetime
from dotenv import load_dotenv

# Optional torch import (not needed for Parakeet/ONNX)
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    torch = None
    TORCH_AVAILABLE = False

# Load environment variables from .env file
load_dotenv()

# ===============================
# WEB SCRAPING CONFIGURATION
# ===============================
URL = "https://sg001-harmony.sliq.net/00293/Harmony/en/View/RecentEnded/20250522/-1"

# ===============================
# FILE PATHS AND STORAGE
# ===============================
ENTRIES_FILE = "latest_entries.txt"
PROCESSED_ENTRIES_FILE = "processed_entries.txt"
DOWNLOAD_DIR = "downloads"
CAPTIONS_DIR = "captions"
LAST_CLEANUP_FILE = "last_cleanup.txt"
PROXY_LIST_FILE = "proxy_list.txt" # Still used by ProxyManager for internal tracking
LAST_PROXY_UPDATE_FILE = "last_proxy_update.txt" # Still used by ProxyManager for internal tracking

# ===============================
# EMAIL CONFIGURATION
# ===============================
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
EMAIL_RECIPIENTS = ["joshua@lwe.digital", "skyedevore@gmail.com"]

# Legacy variables for compatibility
EMAIL_USER = SMTP_USER
EMAIL_PASSWORD = SMTP_PASS

# ===============================
# TRANSCRIPTION ENGINE CONFIGURATION
# ===============================
# Primary transcription engine: "parakeet", "granite", or "whisper"
TRANSCRIBER = os.getenv("TRANSCRIBER", "parakeet")

# Parakeet TDT 0.6b-v2 configuration (NVIDIA via ONNX - 60x faster than real-time)
PARAKEET_MODEL = os.getenv("PARAKEET_MODEL", "nemo-parakeet-tdt-0.6b-v2")
PARAKEET_DEVICE = os.getenv("PARAKEET_DEVICE", "cpu")  # cpu, migraphx (AMD GPU)
PARAKEET_CHUNK_DURATION = int(os.getenv("PARAKEET_CHUNK_DURATION", "60"))  # 60 sec chunks

# Granite Speech configuration (IBM Granite Speech 3.3-2B - optimized for integrated GPU)
GRANITE_MODEL = os.getenv("GRANITE_MODEL", "ibm-granite/granite-speech-3.3-2b")
GRANITE_WORKERS = int(os.getenv("GRANITE_WORKERS", "2"))
GRANITE_CHUNK_DURATION = int(os.getenv("GRANITE_CHUNK_DURATION", "1200"))  # 20 min in seconds
GRANITE_DEVICE = os.getenv("GRANITE_DEVICE", "auto")  # auto, cuda, cpu

# ===============================
# WHISPER CONFIGURATION (Fallback)
# ===============================
WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "large-v3")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "auto")
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "auto")

# Legacy WhisperX settings (deprecated)
WHISPERX_MODEL_SIZE = "medium"
WHISPERX_DEVICE = "cpu"
WHISPERX_COMPUTE_TYPE = "float32"
WHISPERX_BATCH_SIZE = 32
HF_TOKEN = os.getenv("HF_TOKEN")  # Hugging Face token for models

# ===============================
# OXYLABS ISP PROXY CONFIGURATION
# ===============================
OXYLABS_PROXY_HOST = "isp.oxylabs.io"
OXYLABS_PROXY_PORT = "8001"
OXYLABS_USERNAME = os.getenv("OXYLABS_USERNAME")
OXYLABS_PASSWORD = os.getenv("OXYLABS_PASSWORD")
OXYLABS_LOCATION_URL = "https://ip.oxylabs.io/location"
PROXY_UPDATE_INTERVAL_HOURS = 6  # Check proxy status every 6 hours

# ===============================
# Removed Global proxy configuration variables
# proxy_config = None
# proxy_working = False
# ===============================

# ===============================
# SEAFILE CONFIGURATION (Replaces Nextcloud)
# ===============================
SEAFILE_URL = os.getenv("SEAFILE_URL")
SEAFILE_USERNAME = os.getenv("SEAFILE_USERNAME")
SEAFILE_PASSWORD = os.getenv("SEAFILE_PASSWORD")
SEAFILE_API_TOKEN = os.getenv("SEAFILE_API_TOKEN")  # Alternative to username/password
SEAFILE_LIBRARY_ID = os.getenv("SEAFILE_LIBRARY_ID")

# =====================================================
# SFTP CONFIGURATION
# =====================================================
SFTP_HOST = os.getenv("SFTP_HOST")
SFTP_PORT = int(os.getenv("SFTP_PORT", 22))
SFTP_USERNAME = os.getenv("SFTP_USERNAME")
SFTP_PASSWORD = os.getenv("SFTP_PASSWORD")
SFTP_UPLOAD_PATH = os.getenv("SFTP_UPLOAD_PATH", "/uploads")
SEAFILE_BASE_FOLDER = "Legislative Transcription/Allison_Test"

# Legacy Nextcloud support (deprecated)
NEXTCLOUD_URL = os.getenv("NEXTCLOUD_URL")
NEXTCLOUD_USERNAME = os.getenv("NEXTCLOUD_USERNAME")
NEXTCLOUD_TOKEN = os.getenv("NEXTCLOUD_TOKEN")
NEXTCLOUD_BASE_FOLDER = "Legislative Transcription"

# ===============================
# N8N WEBHOOK CONFIGURATION
# ===============================
# Test URL: https://n8n.dapengi.cloud/webhook-test/legislative-manifest
# Production URL: https://n8n.dapengi.cloud/webhook/legislative-manifest
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "https://n8n.dapengi.cloud/webhook/legislative-manifest")
N8N_WEBHOOK_TIMEOUT = int(os.getenv("N8N_WEBHOOK_TIMEOUT", "10"))  # seconds

# ===============================
# SCHEDULING CONFIGURATION
# ===============================
# GMT times for MST = GMT-7
MONITORING_SCHEDULE = ["16:00", "18:00", "20:00", "22:00", "00:00", "02:00"]

# ===============================
# SPEAKER IDENTIFICATION SETTINGS
# ===============================
SPEAKER_CONFIDENCE_THRESHOLD = 70  # Minimum confidence for real name assignment

# ===============================
# USER AGENT AND HEADERS
# ===============================
DEFAULT_USER_AGENT = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                      'AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/91.0.4472.124 Safari/537.36')

DEFAULT_HEADERS = {
    'User-Agent': DEFAULT_USER_AGENT
}

# ===============================
# LOGGING CONFIGURATION
# ===============================
LOG_FILE = "legislature_monitor.log"
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_LEVEL = "INFO"

# ===============================
# VALIDATION FUNCTIONS
# ===============================
def validate_config():
    """Validate that all required configuration is present."""
    errors = []

    # Check email configuration
    if not SMTP_USER or not SMTP_PASS:
        errors.append("Email configuration missing (SMTP_USER, SMTP_PASS)")

    # Note: HF_TOKEN is optional - SpeechBrain diarization doesn't require it

    # Check Seafile configuration
    if not SEAFILE_URL:
        errors.append("Seafile URL missing (SEAFILE_URL)")

    if not SEAFILE_API_TOKEN and not (SEAFILE_USERNAME and SEAFILE_PASSWORD):
        errors.append("Seafile authentication missing (need either SEAFILE_API_TOKEN or SEAFILE_USERNAME + SEAFILE_PASSWORD)")

    if not SEAFILE_LIBRARY_ID:
        errors.append("Seafile library ID missing (SEAFILE_LIBRARY_ID)")

    # Check proxy configuration
    if not OXYLABS_USERNAME or not OXYLABS_PASSWORD:
        errors.append("Oxylabs proxy configuration missing (OXYLABS_USERNAME, OXYLABS_PASSWORD)")

    return errors

def get_config_summary():
    """Return a summary of current configuration for logging."""
    return {
        'transcriber': TRANSCRIBER,
        'parakeet_model': PARAKEET_MODEL,
        'parakeet_device': PARAKEET_DEVICE,
        'granite_model': GRANITE_MODEL,
        'granite_workers': GRANITE_WORKERS,
        'granite_device': GRANITE_DEVICE,
        'whisper_model': WHISPER_MODEL_SIZE,
        'seafile_url': SEAFILE_URL,
        'monitoring_schedule': MONITORING_SCHEDULE,
        'email_recipients': len(EMAIL_RECIPIENTS),
        'speaker_confidence_threshold': SPEAKER_CONFIDENCE_THRESHOLD,
        'download_directory': DOWNLOAD_DIR,
        'using_gpu': torch.cuda.is_available() if TORCH_AVAILABLE else False
    }


