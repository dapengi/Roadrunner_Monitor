#!/usr/bin/env python3
"""
Direct test of Parakeet TDT pipeline using existing audio file.
Skips video download to test transcription -> formatting -> upload chain.
"""
import sys
import datetime
import json
import os
import time
from pathlib import Path

# Load environment from .env
from dotenv import load_dotenv
load_dotenv()

from modules.transcript_pipeline import TranscriptPipeline
from modules.seafile_client import SeafileClient
from modules.sftp_client import SFTPClient
from modules.n8n_webhook import create_manifest, get_manifest_path, send_webhook
from config import (
    SFTP_HOST, SFTP_PORT, SFTP_USERNAME,
    SFTP_PASSWORD, SFTP_UPLOAD_PATH, SEAFILE_URL, SEAFILE_API_TOKEN, SEAFILE_LIBRARY_ID
)

# Use output directory for results (downloads may have permission issues from Docker runs)
OUTPUT_DIR = 'output'
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Use existing audio from video 78040 test
audio_path = 'downloads/test_parakeet.wav'

if not os.path.exists(audio_path):
    print(f'ERROR: Audio file not found: {audio_path}')
    sys.exit(1)

audio_size_mb = os.path.getsize(audio_path) / (1024 * 1024)

print('=' * 70)
print('TESTING PARAKEET TDT 0.6b-v2 PIPELINE (Direct Audio)')
print('=' * 70)
print(f'Audio: {audio_path}')
print(f'Size: {audio_size_mb:.2f} MB')
print()
print('Meeting: Senate - Committees Committee')
print('Date: January 20, 2026')
print('Time: 4:27 PM - 4:41 PM (~14 min)')
print('=' * 70)

# Process with Parakeet pipeline
print('\n1. Transcribing with Parakeet TDT 0.6b-v2 + SpeechBrain Diarization...')
pipeline = TranscriptPipeline(transcriber='parakeet')

meeting_date = datetime.datetime(2026, 1, 20, 16, 27)
committee = 'SCC'  # Senate Committees Committee
session_type = 'SENATE'
start_time = '427PM'
end_time = '441PM'
date_str = meeting_date.strftime('%Y%m%d')

base_name = f'{date_str}_SENATE_{committee}_{start_time}-{end_time}'
print(f'   Filename: {base_name}')

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

# Show preview
if segments:
    print('\n   Preview (first 3 segments):')
    for seg in segments[:3]:
        text = seg.get('text', '')[:80]
        speaker = seg.get('speaker', '?')
        print(f'     [{speaker}]: {text}...')

# Save files
print('\n2. Saving transcript files...')
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
print('\n3. Uploading to Seafile...')
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
            print(f'   Uploaded {fmt.upper()} to Seafile')
            seafile_results[fmt] = remote_path
        else:
            print(f'   Failed to upload {fmt.upper()} to Seafile')
except Exception as e:
    print(f'   Seafile error: {e}')
    seafile_results = {}

# Upload to SFTP
print('\n4. Uploading to SFTP...')
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
    sftp.close()
except Exception as e:
    print(f'   SFTP error: {e}')
    sftp_results = {}

# Create and upload manifest
print('\n5. Creating manifest...')
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
print('\n6. Sending webhook to n8n...')
if seafile_results:
    webhook_success = send_webhook(
        committee=committee,
        date=meeting_date.strftime('%Y-%m-%d'),
        manifest_path=manifest_path
    )
    if webhook_success:
        print('   Webhook sent to n8n')
    else:
        print('   Webhook failed (non-critical)')

print('\n' + '=' * 70)
print('TEST COMPLETE')
print('=' * 70)
print(f'Transcription engine: Parakeet TDT 0.6b-v2')
print(f'Processing time: {transcribe_time:.2f} seconds')
print(f'Saved files: {list(saved_files.values())}')

# Show transcript sample
txt_file = saved_files.get('txt')
if txt_file and os.path.exists(txt_file):
    print('\n' + '-' * 70)
    print('TRANSCRIPT PREVIEW (first 500 chars):')
    print('-' * 70)
    with open(txt_file) as f:
        content = f.read()
        print(content[:500])
        print('...')
