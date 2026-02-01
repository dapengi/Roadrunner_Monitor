#!/usr/bin/env python3
"""
Test script for processing a single meeting through the full workflow.
Usage: python3 test_single_meeting.py <meeting_url>

Tests: Download → Transcription → Diarization → SFTP → Seafile → Manifest → Webhook
"""

import sys
import datetime
import json
import os

from modules.video_processor import download_video, extract_audio_from_video
from modules.transcript_pipeline import TranscriptPipeline
from modules.seafile_client import SeafileClient
from modules.sftp_client import SFTPClient
from modules.filename_generator import get_filename_generator
from modules.proxy_manager import ProxyManager
from modules.n8n_webhook import create_manifest, get_manifest_path, send_webhook
from config import (
    DOWNLOAD_DIR, SFTP_HOST, SFTP_PORT, SFTP_USERNAME,
    SFTP_PASSWORD, SFTP_UPLOAD_PATH
)


def test_meeting(test_url: str):
    """Process a single meeting through the full workflow."""

    print("=" * 70)
    print("TESTING ROADRUNNER GRANITE WORKFLOW (FULL)")
    print("=" * 70)
    print(f"URL: {test_url}")

    # Initialize proxy
    print("\n1. Initializing proxy...")
    proxy_manager = ProxyManager()
    if not proxy_manager.test_proxy_connection(max_retries=3):
        print("ERROR: Proxy not working")
        return False
    print("   Proxy OK")

    # Download video
    print("\n2. Downloading video...")
    video_path = download_video(test_url, proxy_manager=proxy_manager)
    if not video_path:
        print("ERROR: Video download failed")
        return False
    print(f"   Video downloaded: {video_path}")
    video_size_mb = os.path.getsize(video_path) / (1024 * 1024)
    print(f"   Size: {video_size_mb:.2f} MB")

    # Extract audio
    print("\n3. Extracting audio...")
    audio_path = extract_audio_from_video(video_path)
    if not audio_path:
        print("ERROR: Audio extraction failed")
        return False
    print(f"   Audio extracted: {audio_path}")
    audio_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
    print(f"   Size: {audio_size_mb:.2f} MB")

    # Process with pipeline - use Granite with GPU acceleration
    print("\n4. Transcribing with Granite + SpeechBrain Diarization...")
    pipeline = TranscriptPipeline(transcriber="granite")

    # Use test metadata - in production this comes from web scraper
    meeting_date = datetime.datetime(2026, 1, 20, 9, 0)
    committee = "House - Chamber Meeting"
    session_type = "Session"
    start_time = "12:15PM"
    end_time = "3:59PM"
    date_str = meeting_date.strftime('%Y%m%d')
    date_display = meeting_date.strftime('%Y-%m-%d')

    # Generate proper filename
    base_name = f"{date_str}-{session_type}-{committee}-{start_time}-{end_time}"
    print(f"   Filename: {base_name}")

    result = pipeline.process_meeting(
        audio_path=audio_path,
        committee=committee,
        meeting_date=meeting_date,
        start_time=start_time,
        end_time=end_time,
        committee_type=session_type,
        upload_to_seafile=False
    )

    if not result or not result.get("success"):
        print(f"ERROR: Transcription failed: {result}")
        return False

    print("   Transcription complete!")
    segments = result.get("segments", [])
    print(f"   Segments: {len(segments)}")

    # Show first few segments as preview
    if segments:
        print("\n   Preview (first 3 segments):")
        for seg in segments[:3]:
            text_preview = seg.get("text", "")[:80]
            print(f"   [{seg.get('speaker', 'Unknown')}]: {text_preview}...")

    # Save transcripts locally
    print("\n5. Saving transcripts...")
    formatted = result.get("formatted_transcripts", {})
    saved_files = {}

    for fmt in ["json", "csv", "txt"]:
        content = formatted.get(fmt)
        if content:
            path = os.path.join(DOWNLOAD_DIR, f"{base_name}.{fmt}")
            with open(path, "w") as f:
                f.write(content)
            saved_files[fmt] = path
            print(f"   Saved {fmt.upper()}: {path}")

    # Upload to SFTP (Client delivery)
    print("\n6. Uploading to SFTP (Client delivery)...")
    sftp_results = {}
    sftp_client = None

    try:
        sftp_client = SFTPClient(
            host=SFTP_HOST,
            port=SFTP_PORT,
            username=SFTP_USERNAME,
            password=SFTP_PASSWORD,
            upload_path=SFTP_UPLOAD_PATH
        )

        if sftp_client.connect():
            print(f"   Connected to {SFTP_HOST}")

            files_to_upload = list(saved_files.values())
            upload_results = sftp_client.upload_files(files_to_upload)

            for filename, success in upload_results.items():
                if success:
                    print(f"   ✅ Uploaded to SFTP: {filename}")
                    sftp_results[filename] = f"{SFTP_UPLOAD_PATH}/{filename}"
                else:
                    print(f"   ❌ FAILED to upload: {filename}")
        else:
            print("   ❌ SFTP connection failed")

    except Exception as e:
        print(f"   ❌ SFTP error: {e}")

    finally:
        if sftp_client:
            sftp_client.disconnect()
            print("   SFTP disconnected")

    # Upload to Seafile (Archive)
    print("\n7. Uploading to Seafile (Archive)...")
    seafile_client = SeafileClient()
    seafile_results = {}
    seafile_base_path = f"/Interim/{committee}/{date_display}/captions"

    for fmt, local_file in saved_files.items():
        remote_path = f"{seafile_base_path}/{base_name}.{fmt}"
        if seafile_client.upload_file(local_file, remote_path):
            print(f"   ✅ Uploaded {fmt.upper()} to {remote_path}")
            seafile_results[fmt] = remote_path
        else:
            print(f"   ❌ FAILED to upload {fmt.upper()}")

    # Create and upload manifest
    print("\n8. Creating manifest...")
    manifest = create_manifest(
        committee=committee,
        meeting_date=date_display,
        base_name=base_name,
        uploaded_files=seafile_results,
        session_type=session_type,
        start_time=start_time,
        end_time=end_time,
        segments_count=len(segments),
        speakers_count=len(set(s.get('speaker', '') for s in segments))
    )

    manifest_path = get_manifest_path(session_type, committee, date_display)
    manifest_content = json.dumps(manifest, indent=2)

    print(f"   Manifest content:\n{manifest_content}")

    if seafile_client.write_file(manifest_path, manifest_content):
        print(f"   ✅ Manifest uploaded: {manifest_path}")
    else:
        print("   ❌ Manifest upload failed")

    # Send webhook to n8n
    print("\n9. Sending webhook to n8n...")
    webhook_result = send_webhook(
        committee=committee,
        date=date_display,
        manifest_path=manifest_path
    )
    if webhook_result:
        print("   ✅ Webhook: SUCCESS")
    else:
        print("   ⚠️  Webhook: FAILED (activate workflow in n8n)")

    # Cleanup local files
    print("\n10. Cleanup...")
    for f in [video_path, audio_path]:
        try:
            if f and os.path.exists(f):
                os.unlink(f)
                print(f"   Deleted: {os.path.basename(f)}")
        except Exception as e:
            print(f"   Could not delete {f}: {e}")

    for f in saved_files.values():
        try:
            if f and os.path.exists(f):
                os.unlink(f)
                print(f"   Deleted: {os.path.basename(f)}")
        except Exception as e:
            print(f"   Could not delete {f}: {e}")

    # Summary
    print("\n" + "=" * 70)
    print("TEST COMPLETE!")
    print("=" * 70)
    print(f"Transcription: {len(segments)} segments")
    print(f"SFTP uploads:  {len(sftp_results)} files → {SFTP_HOST}:{SFTP_UPLOAD_PATH}")
    print(f"Seafile:       {len(seafile_results)} files → {seafile_base_path}")
    print(f"Manifest:      {manifest_path}")
    print(f"Webhook:       {'SUCCESS' if webhook_result else 'FAILED'}")
    print("=" * 70)

    return len(sftp_results) > 0 and len(seafile_results) > 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Default test URL
        url = "https://sg001-harmony.sliq.net/00293/Harmony/en/PowerBrowser/PowerBrowserV2/20250522/-1/78036"
    else:
        url = sys.argv[1]

    success = test_meeting(url)
    sys.exit(0 if success else 1)
