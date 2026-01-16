#!/usr/bin/env python3
"""
Legislative Caption Downloader
Downloads closed captions from New Mexico Legislature Harmony/Sliq.net streaming system.
"""

import requests
import re
import json
import csv
from datetime import datetime
from urllib.parse import urlparse
import argparse
import sys
import logging

logger = logging.getLogger(__name__)


class CaptionDownloader:
    # N8N Webhook URL for notifications
    WEBHOOK_URL = "http://192.168.4.52:5678/webhook/nextcloud-transcription"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })

    def send_webhook(self, filename, folder_path):
        """Send webhook notification to n8n after successful download."""
        try:
            payload = {
                "filename": filename,
                "folder_path": folder_path,
            }

            response = requests.post(
                self.WEBHOOK_URL,
                json=payload,
                timeout=10
            )

            if response.status_code == 200:
                logger.info(f"✅ Webhook sent to n8n: {filename}")
                return True
            else:
                logger.warning(f"⚠️ Webhook failed: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"❌ Webhook error: {e}")
            return False

    def fetch_page(self, url):
        """Fetch the HTML page containing caption data"""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching page: {e}")
            return None

    def extract_captions(self, html_content):
        """Extract caption data from HTML content"""
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
            # Handle JavaScript boolean values and other JS-specific syntax
            cc_items_str = re.sub(r'(\w+):', r'"\1":', cc_items_str)  # Quote keys
            cc_items_str = re.sub(r'True', 'true', cc_items_str)
            cc_items_str = re.sub(r'False', 'false', cc_items_str)
            
            cc_items = json.loads(cc_items_str)
            return cc_items
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing caption data: {e}")
            
            # Fallback: try to extract captions with regex
            return self._extract_captions_regex(html_content)

    def _extract_captions_regex(self, html_content):
        """Fallback method to extract captions using regex"""
        logger.info("Trying regex fallback method...")
        
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

    def extract_metadata(self, html_content):
        """Extract video metadata from the page"""
        metadata = {}
        
        # Extract title
        title_match = re.search(r'<title>([^<]+)</title>', html_content)
        if title_match:
            metadata['title'] = title_match.group(1).strip()
            
        # Extract OG meta tags
        og_patterns = {
            'og_title': r'<meta\s+property="og:title"\s+content="([^"]+)"',
            'og_description': r'<meta\s+property="og:description"\s+content="([^"]+)"',
        }
        
        for key, pattern in og_patterns.items():
            match = re.search(pattern, html_content)
            if match:
                metadata[key] = match.group(1)
                
        # Extract video duration if available
        duration_match = re.search(r'"Duration"\s*:\s*(\d+)', html_content)
        if duration_match:
            metadata['duration_seconds'] = int(duration_match.group(1))
            
        return metadata

    def save_as_webvtt(self, captions, filename):
        """Save captions in WebVTT format"""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("WEBVTT\n\n")
            
            for i, caption in enumerate(captions, 1):
                # Convert timestamp format
                start_time = self._convert_timestamp(caption['Begin'])
                end_time = self._convert_timestamp(caption['End'])
                
                f.write(f"{i}\n")
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{caption['Content']}\n\n")

    def save_as_srt(self, captions, filename):
        """Save captions in SRT format"""
        with open(filename, 'w', encoding='utf-8') as f:
            for i, caption in enumerate(captions, 1):
                # Convert timestamp format for SRT
                start_time = self._convert_timestamp_srt(caption['Begin'])
                end_time = self._convert_timestamp_srt(caption['End'])
                
                f.write(f"{i}\n")
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{caption['Content']}\n\n")

    def save_as_txt(self, captions, filename):
        """Save captions as plain text transcript"""
        with open(filename, 'w', encoding='utf-8') as f:
            for caption in captions:
                f.write(f"{caption['Content']} ")
            f.write("\n")

    def save_as_csv(self, captions, filename):
        """Save captions as CSV with timestamps"""
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Start Time', 'End Time', 'Content'])
            
            for caption in captions:
                writer.writerow([caption['Begin'], caption['End'], caption['Content']])

    def save_as_json(self, captions, filename):
        """Save captions as JSON"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(captions, f, indent=2, ensure_ascii=False)

    def _convert_timestamp(self, iso_timestamp):
        """Convert ISO timestamp to WebVTT format (HH:MM:SS.mmm)"""
        try:
            dt = datetime.fromisoformat(iso_timestamp.replace('Z', '+00:00'))
            return dt.strftime("%H:%M:%S.%f")[:-3]  # Remove last 3 digits of microseconds
        except:
            return "00:00:00.000"

    def _convert_timestamp_srt(self, iso_timestamp):
        """Convert ISO timestamp to SRT format (HH:MM:SS,mmm)"""
        try:
            dt = datetime.fromisoformat(iso_timestamp.replace('Z', '+00:00'))
            return dt.strftime("%H:%M:%S,%f")[:-3]  # Remove last 3 digits, use comma
        except:
            return "00:00:00,000"

    def generate_filename(self, url, metadata, extension):
        """Generate a filename based on URL and metadata"""
        # Extract date and ID from URL
        url_parts = url.split('/')
        date_part = ""
        id_part = ""
        
        for part in url_parts:
            if re.match(r'\d{8}', part):  # 8-digit date
                date_part = part
            elif re.match(r'\d+$', part):  # Numeric ID at the end
                id_part = part
                
        # Use title if available, otherwise use URL components
        if metadata.get('og_title'):
            title = re.sub(r'[^\w\s-]', '', metadata['og_title'])[:50]
            title = re.sub(r'\s+', '_', title)
        else:
            title = "legislative_captions"
            
        filename = f"{title}_{date_part}_{id_part}.{extension}"
        return filename

    def download_captions(self, url, output_formats=None, output_dir="."):
        """Main method to download captions from a URL"""
        if output_formats is None:
            output_formats = ['txt']
            
        logger.info(f"Fetching captions from: {url}")
        
        # Fetch the page
        html_content = self.fetch_page(url)
        if not html_content:
            return False
            
        # Extract captions
        caption_data = self.extract_captions(html_content)
        if not caption_data:
            logger.warning("No captions found on this page")
            return False
            
        # Extract metadata
        metadata = self.extract_metadata(html_content)
        
        # Get captions for English (default language)
        captions = caption_data.get('en', [])
        if not captions:
            logger.warning("No English captions found")
            return False
            
        logger.info(f"Found {len(captions)} caption segments")
        
        # Save in requested formats
        success = True
        saved_files = []

        for format_type in output_formats:
            try:
                filename = self.generate_filename(url, metadata, format_type)
                filepath = f"{output_dir}/{filename}"

                if format_type == 'vtt':
                    self.save_as_webvtt(captions, filepath)
                elif format_type == 'srt':
                    self.save_as_srt(captions, filepath)
                elif format_type == 'txt':
                    self.save_as_txt(captions, filepath)
                elif format_type == 'csv':
                    self.save_as_csv(captions, filepath)
                elif format_type == 'json':
                    self.save_as_json(captions, filepath)
                else:
                    logger.warning(f"Unknown format: {format_type}")
                    continue

                logger.info(f"Saved {format_type.upper()}: {filepath}")
                saved_files.append(filename)

            except Exception as e:
                logger.error(f"Error saving {format_type}: {e}")
                success = False

        # Send webhook notification for successfully saved files
        if success and saved_files:
            # Send webhook for the first file (typically the txt file)
            self.send_webhook(saved_files[0], output_dir)

        return success


def main():
    parser = argparse.ArgumentParser(description='Download captions from New Mexico Legislature videos')
    parser.add_argument('url', help='URL of the legislative video page')
    parser.add_argument('--formats', nargs='+', 
                       choices=['vtt', 'srt', 'txt', 'csv', 'json'],
                       default=['txt'],
                       help='Output formats (default: txt)')
    parser.add_argument('--output-dir', default='.',
                       help='Output directory (default: current directory)')
    
    args = parser.parse_args()
    
    downloader = CaptionDownloader()
    success = downloader.download_captions(args.url, args.formats, args.output_dir)
    
    if success:
        logger.info("Caption download completed successfully!")
        sys.exit(0)
    else:
        logger.error("Caption download failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()