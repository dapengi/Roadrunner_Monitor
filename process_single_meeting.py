#!/usr/bin/env python3
"""
Single Meeting Processor
Process a single legislature meeting video with enhanced Sherpa-ONNX transcription
and speaker identification. Similar to test_transcription.py but for production use.
"""

import logging
import datetime
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables BEFORE importing config
load_dotenv()

from modules.video_processor import download_video, extract_audio_from_video
from modules.transcription import transcribe_with_whisperx
from modules.speaker_id import get_committee_members_for_meeting
from modules.nextcloud import save_transcript_to_nextcloud
from modules.utils import write_processed_entry
import re

def format_transcript_with_speaker_breaks(transcript_text):
    """
    Format transcript to add proper line breaks when speakers change.
    This fixes the issue where multiple speaker segments are concatenated without breaks.
    
    Args:
        transcript_text: Raw transcript text with speaker labels
        
    Returns:
        Formatted transcript with proper speaker line breaks
    """
    try:
        if not transcript_text:
            return transcript_text
        
        # Split the text into lines
        lines = transcript_text.split('\n')
        formatted_lines = []
        current_speaker = None
        current_speaker_text = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if this line starts with a speaker label (now using letters A, B, C, etc.)
            speaker_match = re.match(r'^(Speaker [A-Z]):\s*(.*)$', line)
            if speaker_match:
                speaker_label = speaker_match.group(1)
                text = speaker_match.group(2)
                
                # If we're switching speakers, finalize the previous speaker's text
                if current_speaker and current_speaker != speaker_label:
                    if current_speaker_text:
                        # Join all text for the current speaker and add it as one block
                        combined_text = ' '.join(current_speaker_text)
                        formatted_lines.append(f"{current_speaker}: {combined_text}")
                        formatted_lines.append("")  # Add blank line between speakers
                        current_speaker_text = []
                
                # Update current speaker and add text
                current_speaker = speaker_label
                if text.strip():  # Only add non-empty text
                    current_speaker_text.append(text.strip())
            else:
                # This line doesn't start with a speaker label, add it to current speaker
                if line.strip():  # Only add non-empty text
                    current_speaker_text.append(line.strip())
        
        # Don't forget the last speaker
        if current_speaker and current_speaker_text:
            combined_text = ' '.join(current_speaker_text)
            formatted_lines.append(f"{current_speaker}: {combined_text}")
        
        # Join all formatted lines
        result = '\n'.join(formatted_lines)
        
        # Clean up any excessive whitespace
        result = re.sub(r'\n{3,}', '\n\n', result)  # Replace 3+ newlines with 2
        
        return result.strip()
        
    except Exception as e:
        logger.error(f"Error formatting transcript: {e}")
        return transcript_text  # Return original if formatting fails

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("single_meeting_processor.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def process_meeting_from_url(meeting_url, meeting_title, output_file=None, include_timestamps=True, save_to_nextcloud=True):
    """
    Process a single meeting from URL with full pipeline.
    
    Args:
        meeting_url: URL to the meeting video
        meeting_title: Title of the meeting (e.g., "IC - Legislative Finance")
        output_file: Optional local file to save transcript
        include_timestamps: Whether to include timestamps in output
        save_to_nextcloud: Whether to save to Nextcloud
        
    Returns:
        Dict with processing results
    """
    try:
        logger.info(f"🚀 Starting single meeting processing")
        logger.info(f"📺 Meeting: {meeting_title}")
        logger.info(f"🔗 URL: {meeting_url}")
        
        # Download video
        logger.info("📥 Downloading video...")
        video_path = download_video(meeting_url)
        if not video_path:
            logger.error("Failed to download video")
            return None
        logger.info(f"✅ Video downloaded: {video_path}")
        
        # Extract audio
        logger.info("🎵 Extracting audio...")
        audio_path = extract_audio_from_video(video_path)
        if not audio_path:
            logger.error("Failed to extract audio")
            return None
        logger.info(f"✅ Audio extracted: {audio_path}")
        
        # For single meeting processing, use simplified settings:
        # - No committee rosters (generic Speaker 0, Speaker 1 labels)  
        # - No timestamps (cleaner, shorter transcripts)
        committee_members = None  # Don't use rosters for single meeting processing
        include_timestamps = False  # Don't include timestamps for single meeting processing
        
        logger.info("Using simplified transcription settings for single meeting processing:")
        logger.info("  • Generic speaker labels (Speaker 0, Speaker 1, etc.)")
        logger.info("  • No timestamps (cleaner format)")
        
        # Start timing for transcription
        start_time = datetime.datetime.now()
        
        # Transcribe with simplified settings
        logger.info(f"🎤 Starting enhanced transcription with Sherpa-ONNX speaker diarization...")
        enhanced_transcript = transcribe_with_whisperx(
            audio_path,
            include_timestamps=include_timestamps,
            committee_members=committee_members
        )
        
        # End timing and log results
        end_time = datetime.datetime.now()
        processing_time = end_time - start_time
        
        if not enhanced_transcript:
            logger.error("❌ Failed to transcribe audio")
            return None
        
        # Format transcript with proper speaker breaks
        logger.info("📝 Formatting transcript with proper speaker breaks...")
        formatted_transcript = format_transcript_with_speaker_breaks(enhanced_transcript)
        
        # Log transcription results
        logger.info(f"✅ Transcription completed successfully!")
        logger.info(f"⏱️  Processing time: {processing_time}")
        logger.info(f"📄 Original transcript length: {len(enhanced_transcript)} characters")
        logger.info(f"📄 Formatted transcript length: {len(formatted_transcript)} characters")
        
        # Count detected speakers in the formatted transcript
        # Since we're using generic labels for single meeting processing (now with letters)
        speaker_pattern = r'Speaker ([A-Z]):'
        speakers_found_matches = re.findall(speaker_pattern, formatted_transcript)
        unique_speakers = len(set(speakers_found_matches))
        speaker_labels = [f"Speaker {letter}" for letter in sorted(set(speakers_found_matches))]
        logger.info(f"🎭 Detected speakers: {unique_speakers} ({', '.join(speaker_labels)})")
        
        # Save to local file if requested
        if output_file:
            output_path = Path(output_file)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(f"Meeting Processing Results\n")
                f.write(f"========================\n\n")
                f.write(f"Meeting: {meeting_title}\n")
                f.write(f"URL: {meeting_url}\n")
                f.write(f"Video: {video_path}\n")
                f.write(f"Audio: {audio_path}\n")
                f.write(f"Processing time: {processing_time}\n")
                f.write(f"Committee members: {len(committee_members) if committee_members else 0}\n")
                f.write(f"Detected speakers: {unique_speakers}\n")
                f.write(f"Speaker labels: {', '.join(speaker_labels)}\n")
                f.write(f"Original transcript length: {len(enhanced_transcript)} characters\n")
                f.write(f"Formatted transcript length: {len(formatted_transcript)} characters\n")
                f.write(f"Generated: {datetime.datetime.now()}\n\n")
                f.write("TRANSCRIPT:\n")
                f.write("===========\n\n")
                f.write(formatted_transcript)
            logger.info(f"💾 Local transcript saved to: {output_path}")
        
        # Save to Nextcloud if requested
        nextcloud_result = None
        if save_to_nextcloud:
            logger.info("☁️  Saving to Nextcloud...")
            clean_title = re.sub(r'\s+', ' ', meeting_title).strip()
            nextcloud_result = save_transcript_to_nextcloud(
                formatted_transcript, clean_title, meeting_url
            )
            if nextcloud_result:
                logger.info(f"✅ Nextcloud upload successful!")
                logger.info(f"📁 Path: {nextcloud_result.get('nextcloud_path', 'Unknown')}")
                logger.info(f"🔗 Share: {nextcloud_result.get('share_link', 'No link')}")
            else:
                logger.error("❌ Nextcloud upload failed")
        
        # Prepare results
        results = {
            'success': True,
            'meeting_title': meeting_title,
            'meeting_url': meeting_url,
            'video_path': video_path,
            'audio_path': audio_path,
            'transcript': formatted_transcript,
            'processing_time': processing_time,
            'committee_members_count': len(committee_members) if committee_members else 0,
            'speakers_detected': speaker_labels,
            'speakers_count': unique_speakers,
            'transcript_length': len(formatted_transcript),
            'original_transcript_length': len(enhanced_transcript),
            'nextcloud_result': nextcloud_result,
            'processed_at': datetime.datetime.now().isoformat()
        }
        
        # Save processing entry for records
        entry = {
            'text': meeting_title,
            'link': meeting_url,
            'timestamp': datetime.datetime.now().isoformat(),
            'transcription': {
                'video_path': video_path,
                'audio_path': audio_path,
                'nextcloud_result': nextcloud_result,
                'processed_at': datetime.datetime.now().isoformat(),
                'processing_time_seconds': processing_time.total_seconds(),
                'transcript_length': len(formatted_transcript),
                'original_transcript_length': len(enhanced_transcript),
                'committee_members_count': len(committee_members) if committee_members else 0,
                'speakers_detected': speaker_labels,
                'speakers_count': unique_speakers,
                'speaker_diarization': 'Sherpa-ONNX',
                'include_timestamps': include_timestamps,
                'processing_mode': 'single_meeting_simplified'
            }
        }
        write_processed_entry(entry)
        
        # Final success summary
        logger.info("=" * 70)
        logger.info("🎉 SINGLE MEETING PROCESSING COMPLETE!")
        logger.info(f"📊 Mode: Single meeting simplified processing")
        logger.info(f"🎭 Speakers: {unique_speakers} detected")
        logger.info(f"👥 Labels: {', '.join(speaker_labels)}")
        logger.info(f"⏱️  Time: {processing_time}")
        logger.info(f"📄 Length: {len(formatted_transcript)} characters (formatted)")
        logger.info(f"🏷️  Format: No timestamps, generic speaker labels, proper line breaks")
        if nextcloud_result:
            logger.info(f"☁️  Saved to: {nextcloud_result.get('nextcloud_path', 'Unknown')}")
            logger.info(f"🔗 Share: {nextcloud_result.get('share_link', 'No link')}")
        if output_file:
            logger.info(f"💾 Local: {output_file}")
        logger.info("=" * 70)
        
        return results
            
    except Exception as e:
        logger.error(f"Error processing meeting: {e}")
        return None

def main():
    """Main function for single meeting processing."""
    parser = argparse.ArgumentParser(description='Process Single Legislature Meeting')
    parser.add_argument('meeting_url', help='URL to the meeting video')
    parser.add_argument('meeting_title', help='Meeting title (e.g., "IC - Legislative Finance")')
    parser.add_argument('--output', type=str, help='Output file to save transcript locally')
    parser.add_argument('--no-timestamps', action='store_true', 
                       help='Remove timestamps from output')
    parser.add_argument('--no-nextcloud', action='store_true',
                       help='Skip Nextcloud upload')
    parser.add_argument('--preview', action='store_true',
                       help='Show preview of transcript (first 500 chars)')
    
    args = parser.parse_args()
    
    logger.info("=== Single Meeting Processor ===")
    
    # Process meeting
    include_timestamps = not args.no_timestamps
    save_to_nextcloud = not args.no_nextcloud
    
    result = process_meeting_from_url(
        args.meeting_url,
        args.meeting_title,
        args.output,
        include_timestamps,
        save_to_nextcloud
    )
    
    if result:
        print("\n" + "="*60)
        print("✅ MEETING PROCESSING SUCCESSFUL!")
        print("="*60)
        
        if args.preview and result.get('transcript'):
            print("\nPREVIEW (First 500 characters):")
            print("-" * 40)
            transcript = result['transcript']
            print(transcript[:500])
            if len(transcript) > 500:
                print("...")
                print(f"\n[Full transcript is {len(transcript)} characters]")
        
        print(f"\n📊 Processing Summary:")
        print(f"   • Meeting: {result['meeting_title']}")
        print(f"   • Speakers: {result['speakers_count']} detected")
        print(f"   • Names: {', '.join(result['speakers_detected'])}")
        print(f"   • Time: {result['processing_time']}")
        print(f"   • Length: {result['transcript_length']} characters")
        
        print("\n" + "="*60)
        
    else:
        print("\n" + "="*60)
        print("❌ MEETING PROCESSING FAILED!")
        print("="*60)
        print("Check the logs for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()