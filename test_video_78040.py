#!/usr/bin/env python3
"""
Test script for video 78040 - Senate Committees Committee
"""
import sys
import datetime
import json
import os
from pathlib import Path

# Load environment from .env
from dotenv import load_dotenv
load_dotenv()

from modules.video_processor import download_video, extract_audio_from_video
from modules.transcript_pipeline import TranscriptPipeline
from modules.seafile_client import SeafileClient
from modules.sftp_client import SFTPClient
from modules.filename_generator import get_filename_generator
from modules.proxy_manager import ProxyManager
from modules.n8n_webhook import create_manifest, get_manifest_path, send_webhook
from config import (
    DOWNLOAD_DIR, SFTP_HOST, SFTP_PORT, SFTP_USERNAME,
    SFTP_PASSWORD, SFTP_UPLOAD_PATH, SEAFILE_URL, SEAFILE_API_TOKEN, SEAFILE_LIBRARY_ID
)

test_url = 'https://sg001-harmony.sliq.net/00293/Harmony/en/PowerBrowser/PowerBrowserV2/20260121/-1/78040'

print('=' * 70)
print('TESTING ROADRUNNER GRANITE WORKFLOW')
print('=' * 70)
print(f'URL: {test_url}')
print()
print('Meeting: Senate - Committees Committee')
print('Date: January 20, 2026')
print('Time: 4:27 PM - 4:41 PM (~14 min)')
print('=' * 70)

# Initialize proxy
print('\n1. Initializing proxy...')
proxy_manager = ProxyManager()
if not proxy_manager.test_proxy_connection(max_retries=3):
    print('ERROR: Proxy not working')
    sys.exit(1)
print('   ✅ Proxy OK')

# Download video
print('\n2. Downloading video...')
video_path = download_video(test_url, proxy_manager=proxy_manager)
if not video_path:
    print('ERROR: Video download failed')
    sys.exit(1)
print(f'   ✅ Video downloaded: {video_path}')
video_size_mb = os.path.getsize(video_path) / (1024 * 1024)
print(f'   Size: {video_size_mb:.2f} MB')

# Extract audio
print('\n3. Extracting audio...')
audio_path = extract_audio_from_video(video_path)
if not audio_path:
    print('ERROR: Audio extraction failed')
    sys.exit(1)
print(f'   ✅ Audio extracted: {audio_path}')
audio_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
print(f'   Size: {audio_size_mb:.2f} MB')

# Process with pipeline
print('\n4. Transcribing with Granite 2b + SpeechBrain Diarization...')
pipeline = TranscriptPipeline(transcriber='granite')

meeting_date = datetime.datetime(2026, 1, 20, 16, 27)
committee = 'SCC'  # Senate Committees Committee
session_type = 'SENATE'
start_time = '427PM'
end_time = '441PM'
date_str = meeting_date.strftime('%Y%m%d')

base_name = f'{date_str}_SENATE_{committee}_{start_time}-{end_time}'
print(f'   Filename: {base_name}')

result = pipeline.process_meeting(
    audio_path=audio_path,
    committee=committee,
    meeting_date=meeting_date,
    start_time=start_time,
    end_time=end_time,
    committee_type=session_type,
    upload_to_seafile=False
)

if not result or not result.get('success'):
    print(f'ERROR: Transcription failed: {result}')
    sys.exit(1)

print('   ✅ Transcription complete!')
segments = result.get('segments', [])
print(f'   Segments: {len(segments)}')

# Show preview
if segments:
    print('\n   Preview (first 3 segments):')
    for seg in segments[:3]:
        text = seg.get('text', '')[:80]
        speaker = seg.get('speaker', '?')
        print(f'     [{speaker}]: {text}...')

# Save files
print('\n5. Saving transcript files...')
formatted = result.get('formatted_transcripts', {})
saved_files = {}
for fmt in ['json', 'csv', 'txt']:
    content = formatted.get(fmt)
    if content:
        output_path = os.path.join(DOWNLOAD_DIR, f'{base_name}.{fmt}')
        with open(output_path, 'w') as f:
            f.write(content)
        saved_files[fmt] = output_path
        print(f'   ✅ Saved {fmt.upper()}: {output_path}')

# Upload to Seafile
print('\n6. Uploading to Seafile...')
try:
    seafile = SeafileClient(
        url=SEAFILE_URL,
        token=SEAFILE_API_TOKEN,
        library_id=SEAFILE_LIBRARY_ID
    )
    seafile_results = {}
    seafile_base = f'/Session/SENATE/{committee}/{meeting_date.strftime("%Y-%m-%d")}/captions'

    for fmt, local_path in saved_files.items():
        remote_path = f'{seafile_base}/{base_name}.{fmt}'
        if seafile.upload_file(local_path, remote_path):
            print(f'   ✅ Uploaded {fmt.upper()} to Seafile')
            seafile_results[fmt] = remote_path
        else:
            print(f'   ❌ Failed to upload {fmt.upper()} to Seafile')
except Exception as e:
    print(f'   ❌ Seafile error: {e}')
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
            print(f'   ✅ Uploaded {fmt.upper()} to SFTP')
            sftp_results[fmt] = f'{SFTP_UPLOAD_PATH}/{base_name}.{fmt}'
        else:
            print(f'   ❌ Failed to upload {fmt.upper()} to SFTP')
    sftp.close()
except Exception as e:
    print(f'   ❌ SFTP error: {e}')
    sftp_results = {}

# Create and upload manifest
print('\n8. Creating manifest...')
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
        speakers_count=len(set(s.get('speaker', '') for s in segments))
    )
    manifest_path = get_manifest_path(session_type, committee, meeting_date.strftime('%Y-%m-%d'))

    manifest_content = json.dumps(manifest, indent=2)
    manifest_local = os.path.join(DOWNLOAD_DIR, f'{base_name}_manifest.json')
    with open(manifest_local, 'w') as f:
        f.write(manifest_content)
    print(f'   ✅ Manifest created: {manifest_local}')

    # Upload manifest to Seafile
    try:
        if seafile.write_file(manifest_path, manifest_content):
            print(f'   ✅ Manifest uploaded to Seafile: {manifest_path}')
    except Exception as e:
        print(f'   ❌ Manifest upload error: {e}')

# Send webhook
print('\n9. Sending webhook to n8n...')
if seafile_results:
    webhook_success = send_webhook(
        committee=committee,
        date=meeting_date.strftime('%Y-%m-%d'),
        manifest_path=manifest_path
    )
    if webhook_success:
        print('   ✅ Webhook sent to n8n')
    else:
        print('   ⚠️ Webhook failed (non-critical)')

print('\n' + '=' * 70)
print('TEST COMPLETE')
print('=' * 70)
print(f'Saved files: {list(saved_files.values())}')
