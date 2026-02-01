#!/usr/bin/env python3
"""
Test Transcription Script
Quick testing of transcription and speaker diarization on local audio files
"""

import logging
import datetime
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables BEFORE importing config
load_dotenv()

from modules.transcription import transcribe_with_whisperx
from modules.speaker_id import get_committee_members_for_meeting

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("transcription_test.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def test_transcription(audio_path, model_size="base", output_file=None, include_timestamps=True, committee_name=None):
    """
    Test transcription on a local audio file.
    
    Args:
        audio_path: Path to audio file (mp3, wav, etc.)
        model_size: Whisper model size to use
        output_file: Optional output file to save results
        include_timestamps: Whether to include timestamps in output
        committee_name: Optional committee name for speaker identification
        
    Returns:
        Formatted transcript string
    """
    try:
        audio_path = Path(audio_path)
        if not audio_path.exists():
            logger.error(f"Audio file not found: {audio_path}")
            return None
        
        logger.info(f"Testing transcription on: {audio_path}")
        logger.info(f"File size: {audio_path.stat().st_size / 1024 / 1024:.2f} MB")
        logger.info(f"Model size: {model_size}")
        
        # Start timing
        start_time = datetime.datetime.now()
        
        # Get committee members if committee name provided
        committee_members = None
        if committee_name:
            logger.info(f"Looking up committee members for: {committee_name}")
            committee_members = get_committee_members_for_meeting(committee_name)
            if committee_members:
                logger.info(f"Found {len(committee_members)} committee members")
            else:
                logger.warning(f"No committee members found for: {committee_name}")
        
        # Transcribe
        logger.info("Starting transcription...")
        transcript_data = transcribe_with_whisperx(
            str(audio_path), 
            model_size=model_size, 
            include_timestamps=include_timestamps,
            committee_members=committee_members
        )
        
        # End timing
        end_time = datetime.datetime.now()
        processing_time = end_time - start_time
        
        if transcript_data:
            logger.info(f"Transcription completed successfully!")
            logger.info(f"Processing time: {processing_time}")
            logger.info(f"Transcript length: {len(transcript_data)} characters")
            
            # Count speakers
            speaker_count = len(set(line.split(']:')[1].split(':')[0].strip() 
                                 for line in transcript_data.split('\n') 
                                 if ']:' in line and ':' in line.split(']:')[1]))
            logger.info(f"Detected speakers: {speaker_count}")
            
            # Save to file if requested
            if output_file:
                output_path = Path(output_file)
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(f"Transcription Test Results\n")
                    f.write(f"========================\n\n")
                    f.write(f"Audio file: {audio_path}\n")
                    f.write(f"Model size: {model_size}\n")
                    f.write(f"Processing time: {processing_time}\n")
                    f.write(f"Detected speakers: {speaker_count}\n")
                    f.write(f"Transcript length: {len(transcript_data)} characters\n")
                    f.write(f"Generated: {datetime.datetime.now()}\n\n")
                    f.write("TRANSCRIPT:\n")
                    f.write("===========\n\n")
                    f.write(transcript_data)
                logger.info(f"Results saved to: {output_path}")
            
            return transcript_data
            
        else:
            logger.error("Transcription failed")
            return None
            
    except Exception as e:
        logger.error(f"Error during transcription test: {e}")
        return None

def main():
    """Main function for transcription testing."""
    parser = argparse.ArgumentParser(description='Test Transcription on Local Audio Files')
    parser.add_argument('audio_path', help='Path to audio file (mp3, wav, etc.)')
    parser.add_argument('--model', type=str, default='base', 
                       choices=['tiny', 'base', 'small', 'medium', 'large', 'large-v2', 'large-v3'],
                       help='Whisper model size (default: base)')
    parser.add_argument('--output', type=str, help='Output file to save results')
    parser.add_argument('--preview', action='store_true', 
                       help='Show preview of transcript (first 500 chars)')
    parser.add_argument('--no-timestamps', action='store_true', 
                       help='Remove timestamps from output')
    parser.add_argument('--committee', type=str, 
                       help='Committee name for speaker identification (e.g., "Legislative Finance")')
    
    args = parser.parse_args()
    
    logger.info("=== Transcription Test Script ===")
    
    # Test transcription
    include_timestamps = not args.no_timestamps
    result = test_transcription(
        args.audio_path, 
        args.model, 
        args.output, 
        include_timestamps, 
        args.committee
    )
    
    if result:
        print("\n" + "="*60)
        print("✅ TRANSCRIPTION TEST SUCCESSFUL!")
        print("="*60)
        
        if args.preview:
            print("\nPREVIEW (First 500 characters):")
            print("-" * 40)
            print(result[:500])
            if len(result) > 500:
                print("...")
                print(f"\n[Full transcript is {len(result)} characters]")
        else:
            print("\nFULL TRANSCRIPT:")
            print("-" * 40)
            print(result)
            
        print("\n" + "="*60)
        
    else:
        print("\n" + "="*60)
        print("❌ TRANSCRIPTION TEST FAILED!")
        print("="*60)
        print("Check the logs for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()