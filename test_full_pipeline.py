#!/usr/bin/env python3
"""
Full end-to-end pipeline test with video download.
Tests: download -> extract -> transcribe -> diarize -> format -> upload -> webhook
"""
import sys
import datetime
import json
import os
import time
from pathlib import Path

# Compatibility fix for torchaudio 2.9+ which removed list_audio_backends
# Must be applied before importing speechbrain
import torchaudio
if not hasattr(torchaudio, 'list_audio_backends'):
    def _dummy_list_audio_backends():
        return ['soundfile']
    torchaudio.list_audio_backends = _dummy_list_audio_backends

# Load environment from .env
from dotenv import load_dotenv
load_dotenv()

from modules.video_processor import download_video, extract_audio_from_video
from modules.transcript_pipeline import TranscriptPipeline
from modules.seafile_client import SeafileClient
from modules.sftp_client import SFTPClient
from modules.proxy_manager import ProxyManager
from modules.n8n_webhook import create_manifest, get_manifest_path, send_webhook
from modules.filename_generator import FilenameGenerator
from config import (
    SFTP_HOST, SFTP_PORT, SFTP_USERNAME,
    SFTP_PASSWORD, SFTP_UPLOAD_PATH, SEAFILE_URL, SEAFILE_API_TOKEN, SEAFILE_LIBRARY_ID,
    N8N_WEBHOOK_URL
)

# Test URL - video 78072
test_url = 'https://sg001-harmony.sliq.net/00293/Harmony/en/PowerBrowser/PowerBrowserV2/20260122/-1/78072'

# Output directory
OUTPUT_DIR = 'output'
os.makedirs(OUTPUT_DIR, exist_ok=True)

print('=' * 70)
print('FULL END-TO-END PIPELINE TEST')
print('=' * 70)
print(f'URL: {test_url}')
print(f'Webhook: {N8N_WEBHOOK_URL}')
print('=' * 70)

# Initialize proxy
print('\n1. Initializing proxy...')
proxy_manager = ProxyManager()
if not proxy_manager.test_proxy_connection(max_retries=3):
    print('ERROR: Proxy not working')
    sys.exit(1)
print('   Proxy OK')

# Download video
print('\n2. Downloading video...')
download_start = time.time()
video_path = download_video(test_url, proxy_manager=proxy_manager)
download_time = time.time() - download_start

if not video_path:
    print('ERROR: Video download failed')
    sys.exit(1)
print(f'   Video downloaded: {video_path}')
video_size_mb = os.path.getsize(video_path) / (1024 * 1024)
print(f'   Size: {video_size_mb:.2f} MB')
print(f'   Time: {download_time:.1f}s')

# Extract audio
print('\n3. Extracting audio...')
extract_start = time.time()
audio_path = extract_audio_from_video(video_path)
extract_time = time.time() - extract_start

if not audio_path:
    print('ERROR: Audio extraction failed')
    sys.exit(1)
print(f'   Audio extracted: {audio_path}')
audio_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
print(f'   Size: {audio_size_mb:.2f} MB')
print(f'   Time: {extract_time:.1f}s')

# Get meeting info - use FilenameGenerator to parse from video title
# The video title from the download contains meeting info
# For video 78072: "House - Appropriations and Finance - January 22, 2026"
meeting_title = "House - Appropriations and Finance - January 22, 2026"  # TODO: Extract from video metadata
meeting_date = datetime.datetime(2026, 1, 22)

# Use FilenameGenerator to detect session type and committee
filename_gen = FilenameGenerator()
filename_info = filename_gen.generate_filename(title=meeting_title, meeting_date=meeting_date)
session_type = filename_info.get('session_type', 'HOUSE')  # HOUSE, SENATE, or IC
committee = filename_info.get('committee', 'HAFC')
start_time = filename_info.get('start_time', '0000')
end_time = filename_info.get('end_time', '0000')
date_str = meeting_date.strftime('%Y%m%d')

print(f'   Meeting: {meeting_title}')
print(f'   Session Type: {session_type}')
print(f'   Committee: {committee}')

# Process with Parakeet pipeline
print('\n4. Transcribing with Parakeet TDT + SpeechBrain Diarization...')
pipeline = TranscriptPipeline(transcriber='parakeet')

transcribe_start = time.time()
result = pipeline.process_meeting(
    audio_path=audio_path,
    committee=committee,
    meeting_date=meeting_date,
    start_time=start_time,
    end_time=end_time,
    committee_type=session_type,
    upload_to_seafile=False
)
transcribe_time = time.time() - transcribe_start

if not result or not result.get('success'):
    print(f'ERROR: Transcription failed: {result}')
    sys.exit(1)

print('   Transcription complete!')
print(f'   Processing time: {transcribe_time:.2f} seconds')
segments = result.get('segments', [])
print(f'   Segments: {len(segments)}')

# Count speakers
speakers = set(s.get('speaker', '') for s in segments)
print(f'   Speakers: {len(speakers)}')

# Show preview
if segments:
    print('\n   Preview (first 3 segments):')
    for seg in segments[:3]:
        text = seg.get('text', '')[:80]
        speaker = seg.get('speaker', '?')
        print(f'     [{speaker}]: {text}...')

# Generate filename
base_name = f'{date_str}_{session_type}_{committee}_{start_time}-{end_time}'
print(f'\n   Filename: {base_name}')

# Save files
print('\n5. Saving transcript files...')
formatted = result.get('formatted_transcripts', {})
saved_files = {}
for fmt in ['json', 'csv', 'txt']:
    content = formatted.get(fmt)
    if content:
        output_path = os.path.join(OUTPUT_DIR, f'{base_name}.{fmt}')
        with open(output_path, 'w') as f:
            f.write(content)
        saved_files[fmt] = output_path
        print(f'   Saved {fmt.upper()}: {output_path}')

# Upload to Seafile
print('\n6. Uploading to Seafile...')
try:
    seafile = SeafileClient(
        url=SEAFILE_URL,
        token=SEAFILE_API_TOKEN,
        library_id=SEAFILE_LIBRARY_ID
    )
    seafile_results = {}
    seafile_base = f'/Session/{session_type}/{committee}/{meeting_date.strftime("%Y-%m-%d")}/captions'

    for fmt, local_path in saved_files.items():
        remote_path = f'{seafile_base}/{base_name}.{fmt}'
        if seafile.upload_file(local_path, remote_path):
            print(f'   Uploaded {fmt.upper()} to Seafile')
            seafile_results[fmt] = remote_path
        else:
            print(f'   Failed to upload {fmt.upper()} to Seafile')
except Exception as e:
    print(f'   Seafile error: {e}')
    seafile_results = {}

# Upload to SFTP
print('\n7. Uploading to SFTP...')
try:
    sftp = SFTPClient(
        host=SFTP_HOST,
        port=SFTP_PORT,
        username=SFTP_USERNAME,
        password=SFTP_PASSWORD,
        upload_path=SFTP_UPLOAD_PATH
    )
    sftp_results = {}

    for fmt, local_path in saved_files.items():
        if sftp.upload_file(local_path, f'{base_name}.{fmt}'):
            print(f'   Uploaded {fmt.upper()} to SFTP')
            sftp_results[fmt] = f'{SFTP_UPLOAD_PATH}/{base_name}.{fmt}'
        else:
            print(f'   Failed to upload {fmt.upper()} to SFTP')
except Exception as e:
    print(f'   SFTP error: {e}')
    sftp_results = {}

# Create and upload manifest
print('\n8. Creating manifest...')
manifest_path = None
if seafile_results:
    manifest = create_manifest(
        committee=committee,
        meeting_date=meeting_date.strftime('%Y-%m-%d'),
        base_name=base_name,
        uploaded_files=seafile_results,
        session_type=session_type,
        start_time=start_time,
        end_time=end_time,
        segments_count=len(segments),
        speakers_count=len(speakers)
    )
    manifest_path = get_manifest_path(session_type, committee, meeting_date.strftime('%Y-%m-%d'))

    manifest_content = json.dumps(manifest, indent=2)
    manifest_local = os.path.join(OUTPUT_DIR, f'{base_name}_manifest.json')
    with open(manifest_local, 'w') as f:
        f.write(manifest_content)
    print(f'   Manifest created: {manifest_local}')

    # Upload manifest to Seafile
    try:
        if seafile.write_file(manifest_path, manifest_content):
            print(f'   Manifest uploaded to Seafile: {manifest_path}')
    except Exception as e:
        print(f'   Manifest upload error: {e}')

# Send webhook
print('\n9. Sending webhook to n8n (PRODUCTION)...')
print(f'   URL: {N8N_WEBHOOK_URL}')
if seafile_results and manifest_path:
    webhook_success = send_webhook(
        committee=committee,
        date=meeting_date.strftime('%Y-%m-%d'),
        manifest_path=manifest_path
    )
    if webhook_success:
        print('   Webhook sent successfully!')
    else:
        print('   Webhook failed')
else:
    print('   Skipped (no files uploaded)')

# Cleanup temporary files
print('\n10. Cleaning up temporary files...')
for path in [video_path, audio_path]:
    if path and os.path.exists(path):
        try:
            os.remove(path)
            print(f'   Removed: {path}')
        except Exception as e:
            print(f'   Could not remove {path}: {e}')

# Summary
total_time = download_time + extract_time + transcribe_time
print('\n' + '=' * 70)
print('PIPELINE COMPLETE')
print('=' * 70)
print(f'Video URL: {test_url}')
print(f'Download time: {download_time:.1f}s')
print(f'Extract time: {extract_time:.1f}s')
print(f'Transcribe time: {transcribe_time:.1f}s')
print(f'Total time: {total_time:.1f}s')
print(f'Segments: {len(segments)}')
print(f'Speakers: {len(speakers)}')
print(f'Files: {list(saved_files.keys())}')
print('=' * 70)

# Show transcript sample
txt_file = saved_files.get('txt')
if txt_file and os.path.exists(txt_file):
    print('\nTRANSCRIPT PREVIEW (first 1000 chars):')
    print('-' * 70)
    with open(txt_file) as f:
        content = f.read()
        print(content[:1000])
        print('...')
