#!/usr/bin/env python3
"""
Voice Enrollment from Diarized Meetings
Uses Pyannote diarization to detect speakers, then manual labeling to build voice database.
"""

import os
import sys

# Add parent directory to path FIRST
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Apply torchaudio compatibility patches BEFORE any pyannote imports
from voice_enrollment.torchaudio_compat import *

# Fix PyTorch 2.6+ compatibility for pyannote model loading
import torch
if hasattr(torch, 'serialization'):
    try:
        torch.serialization.add_safe_globals([torch.torch_version.TorchVersion])
    except:
        pass

# Patch torch.load to disable weights_only for trusted pyannote models
_original_torch_load = torch.load
def _patched_torch_load(*args, **kwargs):
    if 'weights_only' not in kwargs:
        kwargs['weights_only'] = False
    return _original_torch_load(*args, **kwargs)
torch.load = _patched_torch_load

import json
import numpy as np
from typing import List, Dict, Optional
from pathlib import Path
from datetime import datetime
from collections import defaultdict

from voice_enrollment.voice_embedder_fixed import VoiceEmbedder
from data.committee_rosters import COMMITTEE_ROSTERS


class DiarizationEnrollment:
    """Enroll voices using Pyannote diarization + manual labeling."""

    def __init__(self, temp_dir: str = "voice_enrollment/temp"):
        """Initialize enrollment system."""
        self.embedder = VoiceEmbedder()
        self.temp_dir = temp_dir
        Path(temp_dir).mkdir(parents=True, exist_ok=True)

        # Load diarization pipeline
        self.diarization_pipeline = None
        self._load_diarization_pipeline()

    def _load_diarization_pipeline(self):
        """Load Pyannote diarization pipeline."""
        try:
            from pyannote.audio import Pipeline

            print("Loading Pyannote diarization pipeline...")
            self.diarization_pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1"
            )
            print("✓ Diarization pipeline loaded")
        except Exception as e:
            print(f"❌ Error loading diarization pipeline: {e}")
            print("You may need to accept user agreement at:")
            print("https://huggingface.co/pyannote/speaker-diarization-3.1")
            raise

    def diarize_meeting(self, audio_file: str, min_speakers: int = 5, max_speakers: int = 30) -> Dict:
        """
        Run speaker diarization on meeting audio.

        Args:
            audio_file: Path to audio file
            min_speakers: Minimum expected speakers
            max_speakers: Maximum expected speakers

        Returns:
            Diarization result with speaker segments
        """
        print(f"\n🎙️  Running diarization on: {os.path.basename(audio_file)}")
        print(f"   This may take several minutes...")

        try:
            # Run diarization
            diarization = self.diarization_pipeline(
                audio_file,
                min_speakers=min_speakers,
                max_speakers=max_speakers
            )

            # Convert to structured format
            speaker_segments = defaultdict(list)

            for turn, _, speaker in diarization.itertracks(yield_label=True):
                speaker_segments[speaker].append({
                    'start': turn.start,
                    'end': turn.end,
                    'duration': turn.end - turn.start
                })

            print(f"   ✓ Detected {len(speaker_segments)} speakers")

            # Print speaker summary
            for speaker in sorted(speaker_segments.keys()):
                segments = speaker_segments[speaker]
                total_time = sum(s['duration'] for s in segments)
                print(f"   - {speaker}: {len(segments)} segments, {total_time:.1f}s total")

            return {
                'audio_file': audio_file,
                'speaker_segments': dict(speaker_segments),
                'num_speakers': len(speaker_segments)
            }

        except Exception as e:
            print(f"   ❌ Diarization failed: {e}")
            return None

    def generate_speaker_embeddings(self, diarization_result: Dict, samples_per_speaker: int = 10) -> Dict:
        """
        Generate voice embeddings for each detected speaker.

        Args:
            diarization_result: Output from diarize_meeting()
            samples_per_speaker: Number of segments to sample per speaker

        Returns:
            Dict mapping speaker labels to embeddings
        """
        audio_file = diarization_result['audio_file']
        speaker_segments = diarization_result['speaker_segments']

        print(f"\n🔊 Generating embeddings for {len(speaker_segments)} speakers...")

        speaker_embeddings = {}

        for speaker, segments in speaker_segments.items():
            print(f"   Processing {speaker}...")

            # Filter segments by duration (keep 3-30 second segments)
            good_segments = [s for s in segments if 3.0 <= s['duration'] <= 30.0]

            if len(good_segments) < 2:
                print(f"      ⚠️  Insufficient good segments ({len(good_segments)}/2)")
                continue

            # Sample up to N segments
            import random
            sampled = random.sample(good_segments, min(samples_per_speaker, len(good_segments)))

            # Generate embeddings
            embeddings = []
            for segment in sampled:
                embedding = self.embedder.generate_embedding(
                    audio_file,
                    segment['start'],
                    segment['end']
                )

                if embedding is not None:
                    embeddings.append(embedding)

            if len(embeddings) >= 2:
                # Average embeddings
                avg_embedding = self.embedder.average_embeddings(embeddings)

                speaker_embeddings[speaker] = {
                    'embedding': avg_embedding,
                    'sample_count': len(embeddings),
                    'segment_count': len(segments),
                    'total_duration': sum(s['duration'] for s in segments)
                }

                print(f"      ✓ Generated embedding from {len(embeddings)} samples")
            else:
                print(f"      ⚠️  Failed to generate sufficient embeddings ({len(embeddings)}/2)")

        return speaker_embeddings

    def create_labeling_interface(self, speaker_embeddings: Dict, committee: str) -> Dict:
        """
        Interactive interface for manually labeling speakers.

        Args:
            speaker_embeddings: Dict of speaker labels to embedding data
            committee: Committee acronym (e.g., 'HAFC')

        Returns:
            Dict mapping speaker labels to legislator info
        """
        print("\n" + "=" * 80)
        print("🏷️  SPEAKER LABELING INTERFACE")
        print("=" * 80)

        # Get committee roster
        roster = COMMITTEE_ROSTERS.get(committee, [])

        if not roster:
            print(f"\n⚠️  No roster found for committee: {committee}")
            print("Available committees:", list(COMMITTEE_ROSTERS.keys()))
            return {}

        print(f"\nCommittee: {committee}")
        print(f"Members in roster: {len(roster)}")
        print(f"Detected speakers: {len(speaker_embeddings)}")

        # Show speaker summary
        print("\n📊 DETECTED SPEAKERS:")
        print("-" * 80)
        for speaker, data in sorted(speaker_embeddings.items()):
            print(f"{speaker}: {data['sample_count']} samples, "
                  f"{data['segment_count']} segments, "
                  f"{data['total_duration']:.1f}s total")

        # Show roster
        print("\n👥 COMMITTEE ROSTER:")
        print("-" * 80)
        for idx, member in enumerate(roster, 1):
            print(f"{idx:2d}. {member['name']} ({member['party']}, District {member['district']})")

        # Manual labeling
        print("\n" + "=" * 80)
        print("LABELING INSTRUCTIONS:")
        print("-" * 80)
        print("For each detected speaker, enter the member number from the roster above.")
        print("Enter 'skip' to skip a speaker (not a committee member).")
        print("Enter 'done' when finished labeling.")
        print("=" * 80)

        labeled_speakers = {}

        for speaker in sorted(speaker_embeddings.keys()):
            data = speaker_embeddings[speaker]

            print(f"\n🎤 {speaker}")
            print(f"   Samples: {data['sample_count']}, Duration: {data['total_duration']:.1f}s")

            while True:
                response = input(f"   Who is {speaker}? (1-{len(roster)}, 'skip', 'done'): ").strip().lower()

                if response == 'done':
                    print("\n✓ Labeling complete")
                    return labeled_speakers

                if response == 'skip':
                    print(f"   ⊘ Skipping {speaker}")
                    break

                try:
                    member_idx = int(response) - 1
                    if 0 <= member_idx < len(roster):
                        member = roster[member_idx]
                        labeled_speakers[speaker] = {
                            **member,
                            'embedding': data['embedding'],
                            'enrollment': {
                                'sample_count': data['sample_count'],
                                'segment_count': data['segment_count'],
                                'total_duration': data['total_duration'],
                                'original_speaker_label': speaker
                            }
                        }
                        print(f"   ✓ Labeled as: {member['name']}")
                        break
                    else:
                        print(f"   ❌ Invalid number. Enter 1-{len(roster)}")
                except ValueError:
                    print(f"   ❌ Invalid input. Enter number, 'skip', or 'done'")

        print("\n✓ Labeling complete")
        return labeled_speakers

    def save_voice_database(self, labeled_speakers: Dict, meeting_file: str, output_file: str):
        """
        Save voice database to JSON.

        Args:
            labeled_speakers: Dict of labeled speaker data
            meeting_file: Source meeting audio file
            output_file: Output JSON file path
        """
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        voice_db = {
            'version': '1.0',
            'created': datetime.now().isoformat(),
            'description': 'Voice embeddings database from diarized meeting',
            'model': 'pyannote/wespeaker-voxceleb-resnet34-LM',
            'embedding_dim': 192,
            'source_meeting': meeting_file,
            'legislators': {}
        }

        for speaker_label, data in labeled_speakers.items():
            legislator_id = data['name'].lower().replace(' ', '_')

            voice_db['legislators'][legislator_id] = {
                'name': data['name'],
                'chamber': data['chamber'],
                'district': data['district'],
                'party': data['party'],
                'committees': data['committees'],
                'embedding': data['embedding'].tolist(),
                'enrollment': data['enrollment']
            }

        # Save database
        with open(output_file, 'w') as f:
            json.dump(voice_db, f, indent=2)

        print(f"\n💾 Voice database saved to: {output_file}")
        print(f"   Enrolled legislators: {len(voice_db['legislators'])}")

        # Save summary
        summary_file = output_file.replace('.json', '_summary.txt')
        with open(summary_file, 'w') as f:
            f.write("VOICE DATABASE ENROLLMENT SUMMARY\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Created: {voice_db['created']}\n")
            f.write(f"Source: {meeting_file}\n")
            f.write(f"Legislators enrolled: {len(voice_db['legislators'])}\n\n")

            f.write("ENROLLED LEGISLATORS:\n")
            f.write("-" * 80 + "\n")

            for leg_id, leg_data in sorted(voice_db['legislators'].items()):
                f.write(f"\n{leg_data['name']}\n")
                f.write(f"  {leg_data['chamber']} | District {leg_data['district']} | {leg_data['party']}\n")
                f.write(f"  Samples: {leg_data['enrollment']['sample_count']}\n")
                f.write(f"  Duration: {leg_data['enrollment']['total_duration']:.1f}s\n")
                f.write(f"  Speaker label: {leg_data['enrollment']['original_speaker_label']}\n")

        print(f"📄 Summary saved to: {summary_file}")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Enroll voices from diarized meeting audio'
    )
    parser.add_argument(
        'audio_file',
        help='Path to meeting audio file'
    )
    parser.add_argument(
        '--committee',
        required=True,
        choices=['HAFC', 'HJC', 'HRDLC'],
        help='Committee acronym'
    )
    parser.add_argument(
        '--output',
        default='voice_enrollment/database/voice_database.json',
        help='Output voice database file'
    )
    parser.add_argument(
        '--min-speakers',
        type=int,
        default=5,
        help='Minimum expected speakers (default: 5)'
    )
    parser.add_argument(
        '--max-speakers',
        type=int,
        default=30,
        help='Maximum expected speakers (default: 30)'
    )
    parser.add_argument(
        '--samples-per-speaker',
        type=int,
        default=10,
        help='Voice samples per speaker (default: 10)'
    )

    args = parser.parse_args()

    # Check if audio file exists
    if not os.path.exists(args.audio_file):
        print(f"❌ Audio file not found: {args.audio_file}")
        sys.exit(1)

    print("\n" + "=" * 80)
    print("🎙️  VOICE ENROLLMENT FROM DIARIZATION")
    print("=" * 80)
    print(f"Audio file: {args.audio_file}")
    print(f"Committee: {args.committee}")
    print("=" * 80)

    # Initialize enrollment
    enrollment = DiarizationEnrollment()

    # Step 1: Diarize meeting
    print("\n📍 STEP 1: Speaker Diarization")
    diarization_result = enrollment.diarize_meeting(
        args.audio_file,
        min_speakers=args.min_speakers,
        max_speakers=args.max_speakers
    )

    if not diarization_result:
        print("\n❌ Diarization failed. Exiting.")
        sys.exit(1)

    # Step 2: Generate embeddings
    print("\n📍 STEP 2: Generate Voice Embeddings")
    speaker_embeddings = enrollment.generate_speaker_embeddings(
        diarization_result,
        samples_per_speaker=args.samples_per_speaker
    )

    if not speaker_embeddings:
        print("\n❌ No embeddings generated. Exiting.")
        sys.exit(1)

    # Step 3: Manual labeling
    print("\n📍 STEP 3: Manual Speaker Labeling")
    labeled_speakers = enrollment.create_labeling_interface(
        speaker_embeddings,
        args.committee
    )

    if not labeled_speakers:
        print("\n⚠️  No speakers labeled. Exiting.")
        sys.exit(1)

    # Step 4: Save database
    print("\n📍 STEP 4: Save Voice Database")
    enrollment.save_voice_database(
        labeled_speakers,
        args.audio_file,
        args.output
    )

    print("\n" + "=" * 80)
    print("✅ ENROLLMENT COMPLETE")
    print("=" * 80)
    print(f"\n📂 Database: {args.output}")
    print(f"🎯 Next step: Test speaker identification on a new meeting")


if __name__ == '__main__':
    main()
