#!/usr/bin/env python3
"""
Reprocess the HAFC meeting from Jan 14, 2026 (8:34 AM - 1:59 PM)
"""

import logging
import sys
import os

# Add parent directory to path
sys.path.insert(0, '/home/josh/Roadrunner_Monitor')
os.chdir('/home/josh/Roadrunner_Monitor')

from dotenv import load_dotenv
load_dotenv()

from config import *
from modules.proxy_manager import ProxyManager
from modules.seafile_client import SeafileClient
from modules.sftp_client import SFTPClient

# Import the main processing function
from main_hourly import process_entry_with_canary

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('hafc_reprocess.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def main():
    # The entry that failed
    entry = {
        'link': 'https://sg001-harmony.sliq.net/00293/Harmony/en/PowerBrowser/PowerBrowserV2/20250522/-1/77978',
        'text': 'House - Appropriations and Finance (Room 307) House Appropriations and Finance 8:34 AM-1:59 PM Wed, Jan 14, 2026'
    }
    
    logger.info('='*70)
    logger.info('REPROCESSING HAFC MEETING')
    logger.info('Date: Jan 14, 2026')
    logger.info('Time: 8:34 AM - 1:59 PM')
    logger.info('='*70)
    
    # Initialize proxy manager and TEST IT FIRST
    logger.info('Initializing and testing proxy manager...')
    proxy_manager = ProxyManager()
    
    # Force test the proxy connection before proceeding
    if not proxy_manager.test_proxy_connection(max_retries=3, force_new_ip=False):
        logger.error('Proxy connection test failed!')
        return 1
    
    logger.info(f'Proxy working: {proxy_manager.proxy_config}')
    
    logger.info('Initializing Seafile client...')
    seafile_client = SeafileClient(
        url=SEAFILE_URL,
        token=SEAFILE_API_TOKEN,
        library_id=SEAFILE_LIBRARY_ID
    )
    
    logger.info('Initializing SFTP client...')
    sftp_client = SFTPClient(
        host=SFTP_HOST,
        port=SFTP_PORT,
        username=SFTP_USERNAME,
        password=SFTP_PASSWORD,
        upload_path=SFTP_UPLOAD_PATH
    )
    
    # Process the entry
    logger.info('Starting processing...')
    result = process_entry_with_canary(entry, proxy_manager, seafile_client, sftp_client)
    
    if result:
        logger.info('='*70)
        logger.info('✅ REPROCESSING SUCCESSFUL!')
        logger.info('='*70)
        return 0
    else:
        logger.error('❌ REPROCESSING FAILED')
        return 1

if __name__ == '__main__':
    sys.exit(main())
