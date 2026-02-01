#!/usr/bin/env python3
"""
Daily Summary Script for Roadrunner Monitor

Sends a Pushover notification with daily processing summary.
Designed to be called by cron at 9pm MST daily.
"""

import sys
import logging
from pathlib import Path

# Add the project root to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from modules.pushover_notifications import send_daily_summary

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Path(__file__).parent / "daily_summary.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("Sending daily summary notification...")
    
    try:
        success = send_daily_summary()
        if success:
            logger.info("Daily summary sent successfully!")
            sys.exit(0)
        else:
            logger.error("Failed to send daily summary")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Error sending daily summary: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
