#!/usr/bin/env python3
"""
Voice Enrollment Script
Processes selected meetings to build voice database with speaker embeddings.
"""

import os
import sys
import json
import numpy as np
from typing import List, Dict, Tuple, Optional
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from difflib import SequenceMatcher

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from voice_enrollment.caption_parser import CaptionParser
from voice_enrollment.voice_embedder import VoiceEmbedder
from data.committee_rosters import COMMITTEE_ROSTERS


class VoiceEnrollment:
    """Main voice enrollment orchestrator."""

    def __init__(self, temp_dir: str = "voice_enrollment/temp"):
        """
        Initialize voice enrollment system.

        Args:
            temp_dir: Directory for temporary audio segments
        """
        self.parser = CaptionParser()
        self.embedder = VoiceEmbedder()
        self.temp_dir = temp_dir

        # Ensure temp directory exists
        Path(temp_dir).mkdir(parents=True, exist_ok=True)

        # Statistics
        self.stats = {
            'meetings_processed': 0,
            'segments_processed': 0,
            'embeddings_generated': 0,
            'speakers_identified': 0,
            'errors': []
        }

    def load_selected_meetings(self, selection_file: str) -> List[Dict]:
        """
        Load selected meetings from JSON file.

        Args:
            selection_file: Path to selected_meetings.json

        Returns:
            List of meeting dictionaries
        """
        with open(selection_file, 'r') as f:
            data = json.load(f)

        meetings = data.get('meetings', [])
        print(f"\n📂 Loaded {len(meetings)} selected meetings from {selection_file}")

        return meetings

    def process_meeting(self, meeting: Dict) -> Dict[str, List[Dict]]:
        """
        Process a single meeting to extract speaker segments and embeddings.

        Args:
            meeting: Meeting metadata dictionary

        Returns:
            Dictionary mapping speaker names to list of embedding data
        """
        caption_file = meeting.get('caption_file')
        audio_file = meeting.get('audio_file')
        meeting_id = f"{meeting.get('date')}-{meeting.get('committee')}"

        print(f"\n⚙️  Processing: {meeting_id}")

        # Parse captions
        try:
            segments = self.parser.parse_file(caption_file)
            print(f"   Parsed {len(segments)} caption segments")
        except Exception as e:
            error_msg = f"Caption parsing failed for {meeting_id}: {e}"
            print(f"   ❌ {error_msg}")
            self.stats['errors'].append(error_msg)
            return {}

        # Group segments by speaker
        speaker_segments = defaultdict(list)
        for segment in segments:
            speaker = segment.get('speaker')
            if speaker and speaker != 'Unknown':
                speaker_segments[speaker].append(segment)

        print(f"   Found {len(speaker_segments)} unique speakers")

        # Generate embeddings for each speaker
        speaker_embeddings = {}

        for speaker, segments_list in speaker_segments.items():
            print(f"   Processing speaker: {speaker} ({len(segments_list)} segments)")

            embeddings = []
            successful_segments = 0

            # Process up to 10 segments per speaker (for efficiency)
            sample_segments = segments_list[:10]

            for segment in sample_segments:
                try:
                    start = segment.get('start')
                    end = segment.get('end')

                    # Skip very short segments (< 2 seconds)
                    if end - start < 2.0:
                        continue

                    # Generate embedding
                    embedding = self.embedder.generate_embedding(
                        audio_file, start, end
                    )

                    if embedding is not None:
                        embeddings.append(embedding)
                        successful_segments += 1
                        self.stats['embeddings_generated'] += 1

                except Exception as e:
                    error_msg = f"Embedding failed for {speaker} in {meeting_id}: {e}"
                    self.stats['errors'].append(error_msg)
                    continue

            self.stats['segments_processed'] += len(sample_segments)

            # Store embeddings if we got at least 2 good samples
            if len(embeddings) >= 2:
                speaker_embeddings[speaker] = {
                    'embeddings': embeddings,
                    'segment_count': len(embeddings),
                    'total_segments': len(segments_list),
                    'meeting_id': meeting_id,
                    'meeting_date': meeting.get('date'),
                    'committee': meeting.get('committee')
                }
                print(f"      ✓ Generated {len(embeddings)} embeddings")
            else:
                print(f"      ⚠️  Insufficient samples ({len(embeddings)}/2)")

        self.stats['meetings_processed'] += 1

        return speaker_embeddings

    def match_speaker_to_legislator(self, speaker_name: str, committee: str) -> Optional[Dict]:
        """
        Match a speaker name to a legislator in committee roster.

        Uses fuzzy matching to handle variations:
        - "Sen. Figueroa" -> "Senator Figueroa"
        - "Rep Martinez" -> "Representative Martinez"

        Args:
            speaker_name: Speaker name from captions
            committee: Committee acronym (e.g., 'HAFC')

        Returns:
            Legislator info dict or None if no match
        """
        # Get committee members
        members = COMMITTEE_ROSTERS.get(committee, [])

        if not members:
            return None

        # Normalize speaker name
        speaker_normalized = speaker_name.lower().strip()
        speaker_normalized = speaker_normalized.replace('sen.', 'senator')
        speaker_normalized = speaker_normalized.replace('rep.', 'representative')
        speaker_normalized = speaker_normalized.replace('rep', 'representative')

        best_match = None
        best_score = 0.0

        for member in members:
            member_name = member.get('name', '').lower()

            # Calculate similarity score
            score = SequenceMatcher(None, speaker_normalized, member_name).ratio()

            # Also check if last name matches (higher weight)
            speaker_parts = speaker_normalized.split()
            member_parts = member_name.split()

            if speaker_parts and member_parts:
                last_name_match = speaker_parts[-1] == member_parts[-1]
                if last_name_match:
                    score += 0.3  # Boost score for last name match

            if score > best_score:
                best_score = score
                best_match = member

        # Require minimum 70% similarity
        if best_score >= 0.7:
            return {
                **best_match,
                'match_confidence': best_score,
                'original_caption_name': speaker_name
            }

        return None

    def build_voice_database(self, all_speaker_embeddings: Dict[str, List[Dict]]) -> Dict:
        """
        Build voice database from collected embeddings.

        Args:
            all_speaker_embeddings: Nested dict of {speaker: [embedding_data_from_meetings]}

        Returns:
            Voice database dictionary
        """
        print("\n🔨 Building voice database...")

        voice_db = {
            'version': '1.0',
            'created': datetime.now().isoformat(),
            'description': 'Voice embeddings database for NM legislative speaker identification',
            'model': 'pyannote/wespeaker-voxceleb-resnet34-LM',
            'embedding_dim': 192,
            'legislators': {}
        }

        identified_count = 0

        for speaker_name, meeting_embeddings_list in all_speaker_embeddings.items():
            # Get committee from first meeting (to help with matching)
            committee = meeting_embeddings_list[0].get('committee', '')

            # Match to legislator
            legislator = self.match_speaker_to_legislator(speaker_name, committee)

            if not legislator:
                print(f"   ⚠️  Could not match: {speaker_name}")
                continue

            legislator_name = legislator.get('name')
            print(f"   ✓ Matched: {speaker_name} -> {legislator_name} ({legislator.get('match_confidence', 0):.2f})")

            # Collect all embeddings across meetings
            all_embeddings = []
            meeting_sources = []

            for meeting_data in meeting_embeddings_list:
                all_embeddings.extend(meeting_data['embeddings'])
                meeting_sources.append({
                    'meeting_id': meeting_data['meeting_id'],
                    'date': meeting_data['meeting_date'],
                    'committee': meeting_data['committee'],
                    'sample_count': meeting_data['segment_count']
                })

            # Average embeddings to create robust voice profile
            if all_embeddings:
                avg_embedding = self.embedder.average_embeddings(all_embeddings)

                # Store in database
                legislator_id = legislator_name.lower().replace(' ', '_')

                voice_db['legislators'][legislator_id] = {
                    'name': legislator_name,
                    'chamber': legislator.get('chamber', 'Unknown'),
                    'district': legislator.get('district', 'Unknown'),
                    'party': legislator.get('party', 'Unknown'),
                    'committees': legislator.get('committees', []),
                    'embedding': avg_embedding.tolist(),  # Convert numpy to list for JSON
                    'enrollment': {
                        'sample_count': len(all_embeddings),
                        'meeting_count': len(meeting_sources),
                        'meetings': meeting_sources,
                        'match_confidence': legislator.get('match_confidence', 0),
                        'original_names': [speaker_name]
                    }
                }

                identified_count += 1

        self.stats['speakers_identified'] = identified_count

        print(f"\n✅ Database created with {identified_count} legislators")

        return voice_db

    def save_voice_database(self, voice_db: Dict, output_file: str) -> None:
        """
        Save voice database to JSON file.

        Args:
            voice_db: Voice database dictionary
            output_file: Output JSON file path
        """
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w') as f:
            json.dump(voice_db, f, indent=2)

        print(f"💾 Voice database saved to: {output_file}")

        # Save human-readable summary
        summary_file = output_file.replace('.json', '_summary.txt')
        with open(summary_file, 'w') as f:
            f.write("VOICE DATABASE ENROLLMENT SUMMARY\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Created: {voice_db['created']}\n")
            f.write(f"Model: {voice_db['model']}\n")
            f.write(f"Legislators enrolled: {len(voice_db['legislators'])}\n\n")

            f.write("ENROLLED LEGISLATORS:\n")
            f.write("-" * 80 + "\n")

            for leg_id, leg_data in sorted(voice_db['legislators'].items()):
                f.write(f"\n{leg_data['name']}\n")
                f.write(f"  Chamber: {leg_data['chamber']} | District: {leg_data['district']} | Party: {leg_data['party']}\n")
                f.write(f"  Samples: {leg_data['enrollment']['sample_count']} from {leg_data['enrollment']['meeting_count']} meetings\n")
                f.write(f"  Confidence: {leg_data['enrollment']['match_confidence']:.2f}\n")

                meetings = leg_data['enrollment']['meetings']
                f.write(f"  Meetings:\n")
                for meeting in meetings:
                    f.write(f"    - {meeting['date']} {meeting['committee']} ({meeting['sample_count']} samples)\n")

        print(f"📄 Summary saved to: {summary_file}")

    def generate_enrollment_report(self, output_file: str) -> None:
        """
        Generate detailed enrollment report.

        Args:
            output_file: Output report file path
        """
        report_path = Path(output_file)
        report_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w') as f:
            f.write("VOICE ENROLLMENT REPORT\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            f.write("STATISTICS:\n")
            f.write("-" * 80 + "\n")
            f.write(f"Meetings processed: {self.stats['meetings_processed']}\n")
            f.write(f"Segments processed: {self.stats['segments_processed']}\n")
            f.write(f"Embeddings generated: {self.stats['embeddings_generated']}\n")
            f.write(f"Speakers identified: {self.stats['speakers_identified']}\n\n")

            if self.stats['errors']:
                f.write("ERRORS:\n")
                f.write("-" * 80 + "\n")
                for error in self.stats['errors']:
                    f.write(f"- {error}\n")
            else:
                f.write("✅ No errors encountered\n")

        print(f"📊 Enrollment report saved to: {output_file}")

    def run_enrollment(self, selection_file: str, output_dir: str = "voice_enrollment/database") -> None:
        """
        Run complete enrollment process.

        Args:
            selection_file: Path to selected_meetings.json
            output_dir: Output directory for database and reports
        """
        print("\n" + "=" * 80)
        print("🎙️  VOICE ENROLLMENT - STARTING")
        print("=" * 80)

        # Load selected meetings
        meetings = self.load_selected_meetings(selection_file)

        if not meetings:
            print("\n❌ No meetings to process. Exiting.")
            return

        # Process each meeting
        all_speaker_embeddings = defaultdict(list)

        for meeting in meetings:
            speaker_embeddings = self.process_meeting(meeting)

            # Aggregate across meetings
            for speaker, data in speaker_embeddings.items():
                all_speaker_embeddings[speaker].append(data)

        if not all_speaker_embeddings:
            print("\n❌ No speaker embeddings generated. Check audio/caption files.")
            return

        # Build voice database
        voice_db = self.build_voice_database(all_speaker_embeddings)

        # Save database
        db_file = os.path.join(output_dir, 'voice_database.json')
        self.save_voice_database(voice_db, db_file)

        # Generate report
        report_file = os.path.join(output_dir, 'enrollment_report.txt')
        self.generate_enrollment_report(report_file)

        print("\n" + "=" * 80)
        print("✅ VOICE ENROLLMENT - COMPLETED")
        print("=" * 80)
        print(f"\n📂 Database: {db_file}")
        print(f"📊 Report: {report_file}")
        print(f"\n🎯 Next step: Test speaker identification on new meetings")


def main():
    """Main entry point for command-line usage."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Enroll voices from selected meetings into voice database'
    )
    parser.add_argument(
        '--selection-file',
        default='voice_enrollment/database/selected_meetings.json',
        help='Path to selected meetings JSON file'
    )
    parser.add_argument(
        '--output-dir',
        default='voice_enrollment/database',
        help='Output directory for database and reports'
    )
    parser.add_argument(
        '--temp-dir',
        default='voice_enrollment/temp',
        help='Temporary directory for audio segments'
    )

    args = parser.parse_args()

    # Check if selection file exists
    if not os.path.exists(args.selection_file):
        print(f"\n❌ Selection file not found: {args.selection_file}")
        print("\nRun meeting selector first:")
        print("  python voice_enrollment/meeting_selector.py")
        sys.exit(1)

    # Create enrollment instance
    enrollment = VoiceEnrollment(temp_dir=args.temp_dir)

    # Run enrollment
    enrollment.run_enrollment(args.selection_file, args.output_dir)


if __name__ == '__main__':
    main()
