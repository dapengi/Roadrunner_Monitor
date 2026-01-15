#!/usr/bin/env python3
"""
Test script for the caption downloader
"""

from caption_downloader import CaptionDownloader

def test_download():
    """Test the caption downloader with the example URL"""
    url = "https://sg001-harmony.sliq.net/00293/Harmony/en/PowerBrowser/PowerBrowserV2/20250819/-1/77483"
    
    downloader = CaptionDownloader()
    
    # Test with multiple formats
    formats = ['txt', 'vtt', 'srt', 'csv', 'json']
    
    print("Testing caption downloader...")
    success = downloader.download_captions(url, formats)
    
    if success:
        print("✅ Test completed successfully!")
    else:
        print("❌ Test failed!")
    
    return success

if __name__ == "__main__":
    test_download()