# modules/caption_processor.py

import os
import re
import json
import datetime
import logging
from pathlib import Path

from config import CAPTIONS_DIR
from modules.web_scraper import make_request_with_proxy

logger = logging.getLogger(__name__)


class CaptionProcessor:
    """
    Downloads closed captions from New Mexico Legislature videos.
    Integrates with the proxy system and saves captions to the captions directory.
    """

    def __init__(self, proxy_manager=None):
        self.proxy_manager = proxy_manager

    def fetch_page(self, url):
        """Fetch the HTML page containing caption data using proxy."""
        try:
            response = make_request_with_proxy(url, proxy_manager=self.proxy_manager)
            return response.text
        except Exception as e:
            logger.error(f"Error fetching page: {e}")
            return None

    def extract_captions(self, html_content):
        """Extract caption data from HTML content."""
        # Look for ccItems JavaScript object
        pattern = r'ccItems\s*:\s*({[^}]+(?:\{[^}]*\}[^}]*)*})'
        match = re.search(pattern, html_content, re.DOTALL)

        if not match:
            logger.warning("No ccItems found in the page")
            return None

        try:
            # Extract the JSON data
            cc_items_str = match.group(1)

            # Clean up the JavaScript to make it valid JSON
            cc_items_str = re.sub(r'(\w+):', r'"\1":', cc_items_str)  # Quote keys
            cc_items_str = re.sub(r'True', 'true', cc_items_str)
            cc_items_str = re.sub(r'False', 'false', cc_items_str)

            cc_items = json.loads(cc_items_str)
            return cc_items
        except json.JSONDecodeError as e:
            logger.warning(f"Error parsing caption data: {e}")

            # Fallback: try to extract captions with regex
            return self._extract_captions_regex(html_content)

    def _extract_captions_regex(self, html_content):
        """Fallback method to extract captions using regex."""
        logger.info("Trying regex fallback method for caption extraction...")

        # Look for caption entries with Begin/End/Content pattern
        pattern = r'"Begin"\s*:\s*"([^"]+)"[^}]*"End"\s*:\s*"([^"]+)"[^}]*"Content"\s*:\s*"([^"]+)"'
        matches = re.findall(pattern, html_content, re.DOTALL)

        if not matches:
            return None

        captions = []
        for begin, end, content in matches:
            captions.append({
                "Begin": begin,
                "End": end,
                "Content": content.replace('\\"', '"')  # Unescape quotes
            })

        return {"en": captions}

    def save_as_txt(self, captions, filename):
        """Save captions as plain text transcript."""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                for caption in captions:
                    f.write(f"{caption['Content']} ")
                f.write("\n")

            file_size_mb = os.path.getsize(filename) / (1024 * 1024)
            logger.info(f"Caption text saved successfully to {filename} (size: {file_size_mb:.2f} MB)")
            return True
        except Exception as e:
            logger.error(f"Error saving caption text: {e}")
            return False

    def download_captions(self, entry_url):
        """
        Main method to download captions from an entry URL.
        Returns the caption text as a string, or None if failed.
        """
        try:
            logger.info(f"Fetching captions from: {entry_url}")

            # Fetch the page
            html_content = self.fetch_page(entry_url)
            if not html_content:
                logger.error("Failed to fetch page")
                return None

            # Extract captions
            caption_data = self.extract_captions(html_content)
            if not caption_data:
                logger.error("No captions found on this page")
                return None

            # Get English captions
            captions = caption_data.get('en', [])
            if not captions:
                logger.error("No English captions found")
                return None

            logger.info(f"Found {len(captions)} caption segments")

            # Convert captions to plain text string
            caption_text = ' '.join([caption['Content'] for caption in captions]) + '\n'

            return caption_text

        except Exception as e:
            logger.error(f"Error in caption download process: {e}")
            return None

    def save_caption_with_filename(self, caption_text, base_filename):
        """
        Save caption text using the provided filename (replacing .docx with .txt).
        Returns the path to the saved file.
        """
        try:
            # Create captions directory if it doesn't exist
            Path(CAPTIONS_DIR).mkdir(exist_ok=True)

            # Replace .docx with .txt
            txt_filename = base_filename.replace('.docx', '.txt')
            filepath = os.path.join(CAPTIONS_DIR, txt_filename)

            # Save as plain text
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(caption_text)

            file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
            logger.info(f"Caption text saved successfully to {filepath} (size: {file_size_mb:.2f} MB)")
            return filepath

        except Exception as e:
            logger.error(f"Error saving caption text: {e}")
            return None
