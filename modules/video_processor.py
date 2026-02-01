# modules/video_processor.py

import os
import re
import json
import random
import time
import datetime
import subprocess
import logging
from pathlib import Path
import yt_dlp

from config import DOWNLOAD_DIR
# Removed: from config import proxy_config, proxy_working # No longer needed
# Removed: from modules.web_scraper import make_request_with_proxy # No longer needed, will pass proxy_manager

logger = logging.getLogger(__name__)

# Minimum valid file size in bytes - files smaller than this are likely
# corrupted, truncated, or contain only error messages rather than actual
# video/audio content. 1KB is a reasonable threshold as even a few seconds
# of audio/video would be larger than this.
MIN_VALID_FILE_SIZE = 1024


# Removed: get_proxy_status and get_proxy_url functions


def extract_hls_stream_url(entry_url, proxy_manager=None):
    """Extract the HLS stream URL from the entry page using proxy."""
    try:
        logger.info(f"Accessing entry page to extract HLS stream: {entry_url}")
        
        # Use proxy-enabled request
        # Pass the proxy_manager instance to make_request_with_proxy
        from modules.web_scraper import make_request_with_proxy # Import here to avoid circular dependency
        response = make_request_with_proxy(entry_url, proxy_manager=proxy_manager)

        # First try to find the availableStreams JSON data
        available_streams_pattern = r'var\s+availableStreams\s*=\s*(\[.*?\]);'
        available_streams_match = re.search(available_streams_pattern,
                                            response.text,
                                            re.DOTALL)
        if available_streams_match:
            streams_json_str = available_streams_match.group(1)
            try:
                streams_data = json.loads(streams_json_str)
                logger.info(f"Found {len(streams_data)} streams in availableStreams JSON")
                
                # Look for the best stream (non-live, enabled, with URL ending in .m3u8)
                best_stream = None
                for stream in streams_data:
                    url = stream.get('Url', '')
                    is_live = stream.get('IsLive', True)
                    enabled = stream.get('Enabled', False)
                    
                    logger.info(f"Stream: URL={url[:80]}{'...' if len(url) > 80 else ''}, IsLive={is_live}, Enabled={enabled}")
                    
                    if url.endswith('.m3u8') and enabled and not is_live:
                        # This is a good recorded stream
                        best_stream = stream
                        break
                    elif url.endswith('.m3u8') and enabled:
                        # Fallback to any enabled stream
                        if best_stream is None:
                            best_stream = stream
                
                if best_stream:
                    # Clean up the URL - replace escaped forward slashes but preserve URL encoding
                    hls_url = best_stream['Url'].replace('\\/', '/')
                    logger.info(f"Selected stream: IsLive={best_stream.get('IsLive')}, Duration={best_stream.get('Duration')}s")
                    logger.info(f"Extracted HLS URL from JSON: {hls_url}")
                    return hls_url
                else:
                    logger.warning("No suitable streams found in availableStreams JSON")
                    
            except json.JSONDecodeError as e:
                logger.error(f"Could not parse availableStreams JSON: {e}")
                logger.debug(f"JSON string was: {streams_json_str[:200]}...")

        # Enhanced fallback patterns - look for VOD URLs first
        vod_patterns = [
            # Pattern for VOD URLs with _definst_ and encoded title (most specific)
            r'(https?://[^"\'\s]+vod-2/_definst_/[^"\'\s]+\.mp4/playlist\.m3u8 )',
            # Pattern for any VOD URL
            r'(https?://[^"\'\s]+vod[^"\'\s]*\.m3u8 )',
            # General m3u8 pattern but prioritize those with dates/times
            r'(https?://[^"\'\s]+/\d{4}/\d{2}/\d{2}/[^"\'\s]+\.m3u8 )',
        ]
        
        for i, pattern in enumerate(vod_patterns):
            matches = re.findall(pattern, response.text, re.IGNORECASE)
            if matches:
                logger.info(f"Found {len(matches)} matches with pattern {i+1}")
                # Filter out live streams if we have multiple matches
                for match in matches:
                    if 'live' not in match.lower():
                        logger.info(f"Found VOD HLS URL via regex pattern {i+1}: {match}")
                        return match
                # If all have 'live', take the first one
                logger.info(f"Found HLS URL via regex pattern {i+1} (might be live): {matches[0]}")
                return matches[0]

        # Last resort - any m3u8 URL
        general_m3u8_pattern = r'(https?://[^"\'\s]+\.m3u8 )'
        matches = re.findall(general_m3u8_pattern, response.text)
        if matches:
            logger.info(f"Found {len(matches)} m3u8 URLs as last resort")
            # Filter out known live stream patterns
            for match in matches:
                if '/live/' not in match and 'playlist.m3u8' in match:
                    logger.info(f"Found potential HLS URL via fallback: {match}")
                    return match
            
            # If no good matches, return first one
            logger.warning(f"Using first available HLS URL (may be live stream): {matches[0]}")
            return matches[0]

        logger.error("No HLS stream URLs found on the page")
        return None

    except Exception as e:
        logger.error(f"Error extracting HLS stream URL: {e}")
        return None


def download_hls_with_ytdlp(hls_url, output_file, max_retries=10, proxy_manager=None):
    """Download HLS stream using yt-dlp with smart proxy fallback."""
    try:
        output_dir = os.path.dirname(output_file)
        if output_dir:
            Path(output_dir).mkdir(exist_ok=True)
        
        logger.info(f"Downloading HLS stream with yt-dlp from {hls_url} to {output_file}")
        
        # Try with proxy only - do NOT fallback to direct connection to protect home IP
        if not (proxy_manager and proxy_manager.proxy_working):
            logger.error("Proxy is not available or not working. Cannot proceed without proxy to protect home IP.")
            return None

        proxy_attempts = max_retries
        total_attempt = 0

        # Try with proxy only
        if proxy_attempts > 0:
            logger.info(f"Phase 1: Trying {proxy_attempts} attempts with Oxylabs proxy")
            for proxy_attempt in range(proxy_attempts):
                total_attempt += 1
                try:
                    ydl_opts = {
                        'outtmpl': output_file.replace('.mp4', '.%(ext)s'),
                        'format': 'best[ext=mp4]/best',
                        'writesubtitles': False,
                        'writeautomaticsub': False,
                        'ignoreerrors': False,
                        'no_warnings': False,
                        'extractaudio': False,
                        'socket_timeout': 120,  # Increased timeout for video streams
                        'retries': 2,
                        'fragment_retries': 3,
                        'http_chunk_size': 10485760,
                        'hls_prefer_native': True,
                    }
                    
                    ydl_opts['proxy'] = proxy_manager.get_yt_dlp_proxy_url()
                    logger.info(f"Attempt {total_attempt}: Using Oxylabs proxy {proxy_manager.proxy_config['ip']}:{proxy_manager.proxy_config['port']} with yt-dlp")
                    
                    ydl_opts['http_headers'] = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                    }
                    
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.download([hls_url])
                    
                    # Check if download succeeded
                    downloaded_file = check_download_success(output_file)
                    if downloaded_file:
                        file_size_mb = os.path.getsize(downloaded_file) / (1024 * 1024)
                        logger.info(f"✅ Successfully downloaded video via proxy to {downloaded_file} (size: {file_size_mb:.2f} MB)")
                        return downloaded_file
                    else:
                        logger.warning("Proxy download completed but no valid file found")
                        
                except Exception as e:
                    error_msg = str(e)
                    logger.warning(f"yt-dlp proxy attempt {proxy_attempt + 1}/{proxy_attempts} failed: {e}")
                    
                    # Always try to get a fresh proxy IP on any failure
                    if proxy_attempt < proxy_attempts - 1:
                        logger.info(f"Refreshing proxy to get new IP from Oxylabs (attempt {proxy_attempt + 2}/{proxy_attempts})...")
                        # Force proxy refresh to get a new IP from Oxylabs
                        if proxy_manager.test_proxy_connection(max_retries=3, force_new_ip=True):
                            logger.info("✅ Successfully obtained new proxy IP from Oxylabs")
                        else:
                            logger.warning("⚠️ Could not get new proxy IP, will retry with current config")
                        
                        wait_time = 3 + random.uniform(1, 2)
                        logger.info(f"Waiting {wait_time:.1f} seconds before retry...")
                        time.sleep(wait_time)
                    else:
                        logger.error("All proxy attempts exhausted. Cannot proceed without proxy to protect home IP.")

        logger.error(f"All {max_retries} proxy attempts failed. Not attempting direct connection to protect home IP.")
        return None
        
    except Exception as e:
        logger.error(f"Error in yt-dlp download process: {e}")
        return None


def check_download_success(output_file):
    """Check if download was successful and return the actual file path."""
    possible_files = [
        output_file,
        output_file.replace('.mp4', '.mkv'),
        output_file.replace('.mp4', '.webm'),
        output_file.replace('.mp4', '.m4v')
    ]
    
    for possible_file in possible_files:
        if os.path.exists(possible_file) and os.path.getsize(possible_file) > MIN_VALID_FILE_SIZE:
            if possible_file != output_file:
                os.rename(possible_file, output_file)
                return output_file
            return possible_file
    
    return None


def download_with_ytdlp_fallback(hls_url, output_file, proxy_manager=None):
    """Download with yt-dlp, fallback to direct if proxy fails."""
    # First try with proxy
    result = download_hls_with_ytdlp(hls_url, output_file, proxy_manager=proxy_manager)
    if result:
        return result
    
    # Fallback to direct connection (download_hls_with_ytdlp already handles this internally if proxy_manager is None or not working)
    # The current implementation of download_hls_with_ytdlp already attempts direct if proxy fails.
    # So, this function can simply return the result of the first call.
    return result


def download_video(entry_url, proxy_manager=None):
    """Download video from the entry page using HLS stream extraction with yt-dlp."""
    try:
        hls_url = extract_hls_stream_url(entry_url, proxy_manager=proxy_manager)
        if not hls_url:
            logger.error("Could not find HLS stream URL on the page")
            return None
        
        video_filename = os.path.join(
            DOWNLOAD_DIR, 
            f"video_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        )
        
        return download_with_ytdlp_fallback(hls_url, video_filename, proxy_manager=proxy_manager)
    
    except Exception as e:
        logger.error(f"Error in video download process: {e}")
        return None


def extract_audio_from_video(video_path):
    """Extract audio from video file using ffmpeg directly (more reliable for local files)."""
    try:
        if not os.path.exists(video_path):
            logger.error(f"Video file not found: {video_path}")
            return None
        
        audio_path = video_path.replace('.mp4', '.mp3')
        
        logger.info(f"Extracting audio from {video_path} to {audio_path}")
        
        try:
            result = subprocess.run([
                'ffmpeg', '-i', video_path, 
                '-vn',  # No video
                '-acodec', 'libmp3lame',  # MP3 codec
                '-ab', '192k',  # 192kbps bitrate
                '-ar', '44100',  # Sample rate
                '-y',  # Overwrite output file
                audio_path
            ], check=True, capture_output=True, text=True)
            
            if os.path.exists(audio_path) and os.path.getsize(audio_path) > MIN_VALID_FILE_SIZE:
                file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
                logger.info(f"Audio extracted successfully to {audio_path} (size: {file_size_mb:.2f} MB)")
                return audio_path
            else:
                logger.error("Audio extraction failed - output file not created or too small")
                return None
                
        except subprocess.CalledProcessError as e:
            logger.error(f"ffmpeg failed: {e.stderr}")
            return extract_audio_with_alternative_ffmpeg(video_path)
            
        except FileNotFoundError:
            logger.error("ffmpeg not found. Cannot extract audio.")
            return None
    
    except Exception as e:
        logger.error(f"Error extracting audio: {e}")
        return None


def extract_audio_with_alternative_ffmpeg(video_path):
    """Alternative ffmpeg method with different parameters."""
    try:
        audio_path = video_path.replace('.mp4', '.mp3')
        
        logger.info(f"Trying alternative ffmpeg method...")
        
        result = subprocess.run([
            'ffmpeg', '-i', video_path, 
            '-q:a', '2',  # High quality audio
            '-map', 'a',  # Map audio stream
            '-y',  # Overwrite
            audio_path
        ], check=True, capture_output=True, text=True)
        
        if os.path.exists(audio_path) and os.path.getsize(audio_path) > MIN_VALID_FILE_SIZE:
            file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
            logger.info(f"Audio extracted with alternative method to {audio_path} (size: {file_size_mb:.2f} MB)")
            return audio_path
        else:
            logger.error("Alternative audio extraction failed")
            return None
            
    except Exception as e:
        logger.error(f"Alternative ffmpeg method failed: {e}")
        return None


