#!/usr/bin/env python3
"""
Voice Enrollment from Existing Diarization Output
Uses pre-computed diarization JSON + manual labeling to build voice database.
Bypasses audio loading issues by using existing diarization results.
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

from data.committee_rosters import COMMITTEE_ROSTERS


def load_diarization(diarization_file: str) -> Dict:
    """Load existing diarization JSON."""
    with open(diarization_file, 'r') as f:
        return json.load(f)


def group_segments_by_speaker(segments: List[Dict]) -> Dict:
    """Group diarization segments by speaker."""
    speaker_segments = defaultdict(list)
    
    for seg in segments:
        speaker_segments[seg['speaker']].append({
            'start': seg['start'],
            'end': seg['end'],
            'duration': seg['end'] - seg['start']
        })
    
    return dict(speaker_segments)


def print_speaker_summary(speaker_segments: Dict):
    """Print summary of detected speakers."""
    print(f"\n📊 DETECTED SPEAKERS: {len(speaker_segments)}")
    print("=" * 80)
    
    for speaker in sorted(speaker_segments.keys()):
        segments = speaker_segments[speaker]
        total_time = sum(s['duration'] for s in segments)
        print(f"{speaker:12s}: {len(segments):3d} segments, {total_time:7.1f}s total")


def create_labeling_interface(speaker_segments: Dict, committee: str) -> Dict:
    """Interactive speaker labeling."""
    print("\n" + "=" * 80)
    print("🏷️  SPEAKER LABELING INTERFACE")
    print("=" * 80)
    
    roster = COMMITTEE_ROSTERS.get(committee, [])
    
    if not roster:
        print(f"\n⚠️  No roster found for committee: {committee}")
        print("Available committees:", list(COMMITTEE_ROSTERS.keys()))
        return {}
    
    print(f"\nCommittee: {committee}")
    print(f"Members in roster: {len(roster)}")
    
    # Show roster
    print("\n👥 COMMITTEE ROSTER:")
    print("-" * 80)
    for idx, member in enumerate(roster, 1):
        print(f"{idx:2d}. {member['name']:30s} ({member['party']:10s}, District {member['district']})")
    
    # Manual labeling
    print("\n" + "=" * 80)
    print("LABELING INSTRUCTIONS:")
    print("-" * 80)
    print("For each detected speaker, enter the member number from the roster.")
    print("Enter 'skip' to skip a speaker.")
    print("Enter 'done' when finished.")
    print("=" * 80)
    
    labeled_speakers = {}
    
    for speaker in sorted(speaker_segments.keys()):
        data = speaker_segments[speaker]
        total_time = sum(s['duration'] for s in data)
        
        print(f"\n🎤 {speaker}")
        print(f"   Segments: {len(data)}, Total: {total_time:.1f}s")
        
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
                        'speaker_label': speaker,
                        'segment_count': len(data),
                        'total_duration': total_time
                    }
                    print(f"   ✓ Labeled as: {member['name']}")
                    break
                else:
                    print(f"   ❌ Invalid number. Enter 1-{len(roster)}")
            except ValueError:
                print(f"   ❌ Invalid input. Enter number, 'skip', or 'done'")
    
    print("\n✓ Labeling complete")
    return labeled_speakers


def save_mapping(labeled_speakers: Dict, audio_file: str, diarization_file: str, output_file: str):
    """Save speaker mapping (without embeddings for now)."""
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    mapping = {
        'version': '1.0',
        'created': datetime.now().isoformat(),
        'description': 'Speaker ID mapping from diarization',
        'source_audio': audio_file,
        'source_diarization': diarization_file,
        'legislators': {}
    }
    
    for speaker_label, data in labeled_speakers.items():
        legislator_id = data['name'].lower().replace(' ', '_')
        
        mapping['legislators'][legislator_id] = {
            'name': data['name'],
            'chamber': data['chamber'],
            'district': data['district'],
            'party': data['party'],
            'committees': data['committees'],
            'diarization': {
                'speaker_label': data['speaker_label'],
                'segment_count': data['segment_count'],
                'total_duration': data['total_duration']
            }
        }
    
    with open(output_file, 'w') as f:
        json.dump(mapping, f, indent=2)
    
    print(f"\n💾 Speaker mapping saved to: {output_file}")
    print(f"   Labeled legislators: {len(mapping['legislators'])}")
    
    # Save summary
    summary_file = output_file.replace('.json', '_summary.txt')
    with open(summary_file, 'w') as f:
        f.write("SPEAKER MAPPING SUMMARY\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Created: {mapping['created']}\n")
        f.write(f"Source: {audio_file}\n")
        f.write(f"Legislators labeled: {len(mapping['legislators'])}\n\n")
        
        f.write("LABELED LEGISLATORS:\n")
        f.write("-" * 80 + "\n")
        
        for leg_id, leg_data in sorted(mapping['legislators'].items()):
            f.write(f"\n{leg_data['name']}\n")
            f.write(f"  {leg_data['chamber']} | District {leg_data['district']} | {leg_data['party']}\n")
            f.write(f"  Segments: {leg_data['diarization']['segment_count']}\n")
            f.write(f"  Duration: {leg_data['diarization']['total_duration']:.1f}s\n")
            f.write(f"  Speaker label: {leg_data['diarization']['speaker_label']}\n")
    
    print(f"📄 Summary saved to: {summary_file}")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Create speaker mapping from existing diarization output'
    )
    parser.add_argument(
        'diarization_file',
        help='Path to diarization JSON file'
    )
    parser.add_argument(
        '--audio-file',
        required=True,
        help='Path to corresponding audio file (for reference)'
    )
    parser.add_argument(
        '--committee',
        required=True,
        choices=['HAFC', 'HJC', 'HRDLC'],
        help='Committee acronym'
    )
    parser.add_argument(
        '--output',
        default='voice_enrollment/database/speaker_mapping.json',
        help='Output mapping file'
    )
    
    args = parser.parse_args()
    
    if not os.path.exists(args.diarization_file):
        print(f"❌ Diarization file not found: {args.diarization_file}")
        sys.exit(1)
    
    print("\n" + "=" * 80)
    print("🎙️  SPEAKER LABELING FROM EXISTING DIARIZATION")
    print("=" * 80)
    print(f"Diarization file: {args.diarization_file}")
    print(f"Audio file: {args.audio_file}")
    print(f"Committee: {args.committee}")
    print("=" * 80)
    
    # Load diarization
    print("\n📍 Loading diarization...")
    diarization = load_diarization(args.diarization_file)
    segments = diarization['segments']
    
    # Group by speaker
    speaker_segments = group_segments_by_speaker(segments)
    print_speaker_summary(speaker_segments)
    
    # Manual labeling
    print("\n📍 Manual Speaker Labeling")
    labeled_speakers = create_labeling_interface(speaker_segments, args.committee)
    
    if not labeled_speakers:
        print("\n⚠️  No speakers labeled. Exiting.")
        sys.exit(1)
    
    # Save mapping
    print("\n📍 Saving Speaker Mapping")
    save_mapping(labeled_speakers, args.audio_file, args.diarization_file, args.output)
    
    print("\n" + "=" * 80)
    print("✅ LABELING COMPLETE")
    print("=" * 80)


if __name__ == '__main__':
    main()
