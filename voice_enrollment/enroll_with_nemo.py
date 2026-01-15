#!/usr/bin/env python3
"""
Voice Enrollment using Sherpa-ONNX Diarization + NeMo TitaNet Embeddings
Hybrid approach: Sherpa for speaker detection, NeMo TitaNet for voice prints
"""

import os
import sys
import json
import numpy as np
from typing import List, Dict, Optional
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import Sherpa diarization (already working)
from modules.sherpa_diarization import SherpaDiarizer
from data.committee_rosters import COMMITTEE_ROSTERS


class NeMoEnrollment:
    """Voice enrollment using Sherpa diarization + NeMo TitaNet embeddings."""

    def __init__(self, temp_dir: str = "voice_enrollment/temp"):
        """Initialize enrollment system."""
        self.temp_dir = temp_dir
        Path(temp_dir).mkdir(parents=True, exist_ok=True)
        
        # Load Sherpa for diarization
        print("Loading Sherpa-ONNX diarization system...")
        self.diarizer = SherpaDiarizer()
        if not self.diarizer.load_models():
            raise RuntimeError("Failed to load Sherpa models")
        print("✓ Sherpa-ONNX loaded")
        
        # Load NeMo TitaNet for embeddings
        print("Loading NeMo TitaNet speaker embedding model...")
        self._load_nemo_model()

    def _load_nemo_model(self):
        """Load NeMo TitaNet speaker verification model."""
        try:
            from nemo.collections.asr.models import EncDecSpeakerLabelModel
            
            # Try TitaNet-Large first (best quality)
            print("   Attempting to load TitaNet-Large...")
            try:
                self.speaker_model = EncDecSpeakerLabelModel.from_pretrained(
                    "nvidia/speakerverification_en_titanet_large"
                )
                self.model_name = "titanet_large"
                print("✓ NeMo TitaNet-Large loaded (256-dim embeddings)")
                return
            except Exception as e:
                print(f"   TitaNet-Large failed: {e}")
                print("   Trying TitaNet-Small...")
            
            # Fallback to TitaNet-Small (faster, still good)
            try:
                self.speaker_model = EncDecSpeakerLabelModel.from_pretrained(
                    "nvidia/speakerverification_en_titanet_small"
                )
                self.model_name = "titanet_small"
                print("✓ NeMo TitaNet-Small loaded (192-dim embeddings)")
                return
            except Exception as e:
                print(f"   TitaNet-Small failed: {e}")
                raise RuntimeError("Could not load any NeMo TitaNet model")
                
        except ImportError as e:
            print(f"❌ NeMo not available: {e}")
            print("   You have NeMo for Canary, but speaker models might need installation")
            raise

    def diarize_meeting(self, audio_file: str) -> Dict:
        """
        Run Sherpa speaker diarization on meeting audio.

        Args:
            audio_file: Path to audio file

        Returns:
            Diarization result with speaker segments
        """
        print(f"\n🎙️  Running Sherpa diarization on: {os.path.basename(audio_file)}")
        print(f"   This may take several minutes...")

        try:
            # Run Sherpa diarization
            diarization = self.diarizer.diarize_audio(audio_file)

            if not diarization:
                return None

            # Convert to structured format
            speaker_segments = defaultdict(list)

            for start_time, end_time, speaker_label in diarization:
                speaker_segments[speaker_label].append({
                    'start': start_time,
                    'end': end_time,
                    'duration': end_time - start_time
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
            import traceback
            traceback.print_exc()
            return None

    def generate_speaker_embeddings(self, diarization_result: Dict, samples_per_speaker: int = 10) -> Dict:
        """
        Generate NeMo TitaNet voice embeddings for each detected speaker.

        Args:
            diarization_result: Output from diarize_meeting()
            samples_per_speaker: Number of segments to sample per speaker

        Returns:
            Dict mapping speaker labels to embeddings
        """
        audio_file = diarization_result['audio_file']
        speaker_segments = diarization_result['speaker_segments']

        print(f"\n🔊 Generating NeMo TitaNet embeddings for {len(speaker_segments)} speakers...")

        speaker_embeddings = {}

        for speaker, segments in speaker_segments.items():
            print(f"   Processing {speaker}...")

            # Filter segments by duration (NeMo prefers 3-10 second segments)
            good_segments = [s for s in segments if 3.0 <= s['duration'] <= 10.0]

            if len(good_segments) < 2:
                print(f"      ⚠️  Insufficient good segments ({len(good_segments)}/2)")
                continue

            # Sample up to N segments
            import random
            sampled = random.sample(good_segments, min(samples_per_speaker, len(good_segments)))

            # Generate NeMo embeddings
            embeddings = []
            for segment in sampled:
                embedding = self._generate_nemo_embedding(
                    audio_file,
                    segment['start'],
                    segment['end']
                )

                if embedding is not None:
                    embeddings.append(embedding)

            if len(embeddings) >= 2:
                # Average embeddings
                avg_embedding = self._average_embeddings(embeddings)

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

    def _generate_nemo_embedding(self, audio_file: str, start_time: float, end_time: float) -> Optional[np.ndarray]:
        """Generate NeMo TitaNet embedding for audio segment."""
        try:
            import torch
            import librosa
            import soundfile as sf
            import tempfile

            # Load audio segment
            audio, sr = librosa.load(audio_file, sr=16000, mono=True)
            start_sample = int(start_time * sr)
            end_sample = int(end_time * sr)
            segment = audio[start_sample:end_sample]

            # NeMo expects audio files, so save to temp file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
                temp_path = tmp_file.name
                sf.write(temp_path, segment, 16000)

            try:
                # Generate embedding using NeMo
                # NeMo returns embeddings as tensors
                embedding = self.speaker_model.get_embedding(temp_path)
                
                # Convert to numpy and normalize
                if torch.is_tensor(embedding):
                    embedding = embedding.cpu().detach().numpy()
                
                # Flatten if needed
                if len(embedding.shape) > 1:
                    embedding = embedding.flatten()
                
                # Normalize for cosine similarity
                embedding = embedding / np.linalg.norm(embedding)

                return embedding
                
            finally:
                # Clean up temp file
                try:
                    os.unlink(temp_path)
                except:
                    pass

        except Exception as e:
            print(f"      ⚠️  NeMo embedding failed: {e}")
            return None

    def _average_embeddings(self, embeddings: List[np.ndarray]) -> np.ndarray:
        """Average multiple embeddings."""
        valid_embeddings = [e for e in embeddings if e is not None]
        stacked = np.stack(valid_embeddings, axis=0)
        avg = np.mean(stacked, axis=0)
        avg = avg / np.linalg.norm(avg)
        return avg

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

        # Show speaker summary (sorted by speaking time)
        print("\n📊 DETECTED SPEAKERS (sorted by speaking time):")
        print("-" * 80)
        
        # Sort by total duration descending
        sorted_speakers = sorted(
            speaker_embeddings.items(),
            key=lambda x: x[1]['total_duration'],
            reverse=True
        )
        
        for speaker, data in sorted_speakers:
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
        print("LABELING TIPS:")
        print("-" * 80)
        print("• Speaker with most time is usually the committee chair")
        print("• For HAFC, #1 Nathan P. Small is the chair (likely top speaker)")
        print("• Short speaking times might be staff or witnesses - skip these")
        print("• Watch the meeting video to help identify speakers")
        print("=" * 80)
        print("\nCOMMANDS:")
        print("  Enter 1-{}: Assign speaker to committee member".format(len(roster)))
        print("  Enter 'skip': Skip this speaker (not a committee member)")
        print("  Enter 'done': Finish labeling")
        print("=" * 80)

        labeled_speakers = {}

        # Label in order of speaking time (most first)
        for speaker, data in sorted_speakers:
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
        """Save voice database to JSON."""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Determine embedding dimension from first speaker
        embedding_dim = len(next(iter(labeled_speakers.values()))['embedding']) if labeled_speakers else 192

        voice_db = {
            'version': '1.0',
            'created': datetime.now().isoformat(),
            'description': 'Voice embeddings database from Sherpa diarization + NeMo TitaNet embeddings',
            'diarization_method': 'sherpa-onnx',
            'embedding_model': f'nvidia/speakerverification_en_{self.model_name}',
            'embedding_dim': embedding_dim,
            'source_meeting': meeting_file,
            'legislators': {}
        }

        for speaker_label, data in labeled_speakers.items():
            legislator_id = data['name'].lower().replace(' ', '_').replace('.', '')

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
        print(f"   Embedding model: {self.model_name} ({embedding_dim} dimensions)")

        # Save summary
        summary_file = output_file.replace('.json', '_summary.txt')
        with open(summary_file, 'w') as f:
            f.write("VOICE DATABASE ENROLLMENT SUMMARY\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Created: {voice_db['created']}\n")
            f.write(f"Method: Sherpa-ONNX diarization + NeMo TitaNet embeddings\n")
            f.write(f"Model: nvidia/speakerverification_en_{self.model_name}\n")
            f.write(f"Embedding dimensions: {embedding_dim}\n")
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
        description='Enroll voices using Sherpa diarization + NeMo TitaNet embeddings'
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
    print("🎙️  VOICE ENROLLMENT - SHERPA + NEMO TITANET")
    print("=" * 80)
    print(f"Audio file: {args.audio_file}")
    print(f"Committee: {args.committee}")
    print(f"Method: Sherpa-ONNX diarization + NeMo TitaNet embeddings")
    print("=" * 80)

    # Initialize enrollment
    try:
        enrollment = NeMoEnrollment()
    except Exception as e:
        print(f"\n❌ Failed to initialize: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Step 1: Diarize meeting with Sherpa
    print("\n📍 STEP 1: Speaker Diarization (Sherpa-ONNX)")
    diarization_result = enrollment.diarize_meeting(args.audio_file)

    if not diarization_result:
        print("\n❌ Diarization failed. Exiting.")
        sys.exit(1)

    # Step 2: Generate NeMo TitaNet embeddings
    print("\n📍 STEP 2: Generate Voice Embeddings (NeMo TitaNet)")
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
    print(f"🎯 Next step: Build speaker identification module")
    print(f"\n💡 TIP: NeMo TitaNet embeddings provide superior accuracy for")
    print(f"    distinguishing between 154 different legislators!")


if __name__ == '__main__':
    main()
