#!/usr/bin/env python3
"""
Interactive Voice Labeling Tool for New Mexico Legislature.

Labels speakers from diarized meeting audio and adds samples to legislator profiles.
Supports both interactive CLI mode and JSON input for batch processing.

Usage:
  Interactive: python label_meeting.py <diarization.json> <meeting_id> <committee>
  Batch:       python label_meeting.py --batch <labels.json>
  
Example:
  python label_meeting.py temp/hjc_012325_diarization.json hjc_012325 HJC
"""

import json
import sys
import os
import readline  # Enable line editing in input
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "data"))
sys.path.insert(0, str(Path(__file__).parent))

from database.profile_manager import ProfileManager, slugify


def parse_meeting_date(meeting_id: str) -> str:
    """Extract date from meeting_id in MMDDYY format.
    
    Args:
        meeting_id: e.g., 'hjc_012325' -> January 23, 2025
        
    Returns:
        ISO date string YYYY-MM-DD
    """
    parts = meeting_id.split('_')
    if len(parts) >= 2:
        date_str = parts[-1]
        if len(date_str) == 6:
            month = date_str[0:2]
            day = date_str[2:4]
            year = "20" + date_str[4:6]
            return f"{year}-{month}-{day}"
    return datetime.now().strftime("%Y-%m-%d")


def load_diarization_stats(diarization_file: str) -> Dict[str, Dict]:
    """Load diarization and compute speaker statistics.
    
    Returns:
        Dict mapping speaker_id -> {segments, total_time, sample_times}
    """
    with open(diarization_file, 'r') as f:
        data = json.load(f)
    
    segments = data.get('segments', [])
    speaker_stats = defaultdict(lambda: {
        'segments': 0,
        'total_time': 0.0,
        'sample_times': []
    })
    
    for seg in segments:
        speaker = seg['speaker']
        duration = seg['end'] - seg['start']
        speaker_stats[speaker]['segments'] += 1
        speaker_stats[speaker]['total_time'] += duration
        speaker_stats[speaker]['sample_times'].append((seg['start'], seg['end']))
    
    return dict(speaker_stats)


def format_time(seconds: float) -> str:
    """Format seconds as MM:SS or HH:MM:SS."""
    if seconds >= 3600:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours}:{minutes:02d}:{secs:02d}"
    else:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}:{secs:02d}"


def display_speakers(speaker_stats: Dict[str, Dict]) -> None:
    """Display speakers sorted by total speaking time."""
    print("\n" + "="*70)
    print("DETECTED SPEAKERS")
    print("="*70)
    
    # Sort by total time (most speaking time first)
    sorted_speakers = sorted(
        speaker_stats.items(),
        key=lambda x: x[1]['total_time'],
        reverse=True
    )
    
    print(f"{'#':<3} {'Speaker':<12} {'Segments':>8} {'Time':>10} {'Avg':>8}")
    print("-"*70)
    
    for i, (speaker, stats) in enumerate(sorted_speakers, 1):
        avg_duration = stats['total_time'] / stats['segments'] if stats['segments'] > 0 else 0
        print(f"{i:<3} {speaker:<12} {stats['segments']:>8} {format_time(stats['total_time']):>10} {avg_duration:>7.1f}s")
    
    print("-"*70)
    total_time = sum(s['total_time'] for s in speaker_stats.values())
    total_segs = sum(s['segments'] for s in speaker_stats.values())
    print(f"    {'TOTAL':<12} {total_segs:>8} {format_time(total_time):>10}")
    print("="*70 + "\n")


def display_committee_roster(pm: ProfileManager, committee: str) -> List[str]:
    """Display committee roster and return member list."""
    members = pm.get_committee_roster(committee)
    
    print(f"\n📋 {committee} Committee Roster ({len(members)} members):")
    print("-"*50)
    for i, name in enumerate(members, 1):
        profile = pm.get_profile(name)
        samples = profile['stats']['total_samples'] if profile else 0
        indicator = f"({samples})" if samples > 0 else ""
        print(f"  {i:>2}. {name} {indicator}")
    print("-"*50)
    
    return members


def search_and_select_legislator(pm: ProfileManager, query: str, committee_members: List[str]) -> Optional[str]:
    """Search for a legislator and return selected name.
    
    Args:
        pm: ProfileManager instance
        query: Search query (can be partial name)
        committee_members: List of committee members (shown first in results)
        
    Returns:
        Selected legislator name or None
    """
    # Handle special inputs
    if query.lower() in ['skip', 's', '']:
        return None
    if query.lower() in ['unknown', 'u']:
        return "UNKNOWN"
    if query.lower() in ['staff', 'witness', 'public', 'other']:
        return query.upper()
        
    # Try numeric selection from roster
    try:
        idx = int(query) - 1
        if 0 <= idx < len(committee_members):
            return committee_members[idx]
    except ValueError:
        pass
    
    # Search by name
    matches = pm.search_legislators(query)
    
    if not matches:
        print(f"  ⚠️  No matches for '{query}'")
        return None
    
    if len(matches) == 1:
        return matches[0]
    
    # Show matches for selection
    print(f"\n  Multiple matches for '{query}':")
    
    # Prioritize committee members
    member_matches = [m for m in matches if m in committee_members]
    other_matches = [m for m in matches if m not in committee_members]
    
    all_matches = member_matches + other_matches
    
    for i, name in enumerate(all_matches, 1):
        marker = " [member]" if name in committee_members else ""
        print(f"    {i}. {name}{marker}")
    
    choice = input("  Select (number or 'skip'): ").strip()
    
    if choice.lower() in ['skip', 's', '']:
        return None
        
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(all_matches):
            return all_matches[idx]
    except ValueError:
        pass
    
    return None


def interactive_label_session(
    diarization_file: str,
    meeting_id: str,
    committee: str,
    clips_dir: Optional[str] = None
) -> Dict[str, str]:
    """Run interactive labeling session.
    
    Args:
        diarization_file: Path to diarization JSON
        meeting_id: Meeting identifier
        committee: Committee code
        clips_dir: Optional directory containing speaker clips
        
    Returns:
        Dict mapping speaker_id -> legislator_name
    """
    pm = ProfileManager()
    
    # Load diarization stats
    speaker_stats = load_diarization_stats(diarization_file)
    
    # Display overview
    print(f"\n🎙️  VOICE LABELING SESSION")
    print(f"Meeting: {meeting_id}")
    print(f"Committee: {committee}")
    print(f"Date: {parse_meeting_date(meeting_id)}")
    
    # Show speakers
    display_speakers(speaker_stats)
    
    # Show committee roster
    committee_members = display_committee_roster(pm, committee)
    
    # Check for clips
    if clips_dir and Path(clips_dir).exists():
        print(f"\n🔊 Audio clips available in: {clips_dir}")
        clip_files = list(Path(clips_dir).glob("SPEAKER_*.wav"))
        print(f"   Found {len(clip_files)} clip files")
    else:
        print(f"\n⚠️  No audio clips found. Run extract_clips_from_json.py first.")
    
    # Instructions
    print("""
📝 LABELING INSTRUCTIONS:
  - Enter legislator number from roster (1-N)
  - Or type partial name to search (e.g., 'chan' for Chandler)
  - 'skip' or Enter to skip a speaker
  - 'unknown' for unidentifiable speakers
  - 'staff', 'witness', 'public' for non-legislators
  - 'done' when finished
  - 'save' to save progress and continue
  - 'quit' to exit without saving
""")
    
    labels = {}
    
    # Sort speakers by time for labeling (most speaking time first)
    sorted_speakers = sorted(
        speaker_stats.items(),
        key=lambda x: x[1]['total_time'],
        reverse=True
    )
    
    for speaker, stats in sorted_speakers:
        print(f"\n{'='*50}")
        print(f"Speaker: {speaker}")
        print(f"  Segments: {stats['segments']}")
        print(f"  Time: {format_time(stats['total_time'])} ({stats['total_time']:.1f}s)")
        
        # Show first few time markers
        if stats['sample_times']:
            times = stats['sample_times'][:3]
            time_str = ", ".join(f"{format_time(t[0])}" for t in times)
            print(f"  First appears at: {time_str}")
        
        if clips_dir:
            clip_path = Path(clips_dir) / f"{speaker}.wav"
            if clip_path.exists():
                print(f"  🔊 Clip: {clip_path}")
        
        while True:
            response = input(f"\n  Who is {speaker}? ").strip()
            
            if response.lower() == 'done':
                print("\n✅ Labeling complete!")
                return labels
            elif response.lower() == 'quit':
                print("\n❌ Exiting without saving.")
                return {}
            elif response.lower() == 'save':
                print(f"\n💾 Progress saved ({len(labels)} labels)")
                break
            
            legislator = search_and_select_legislator(pm, response, committee_members)
            
            if legislator is None:
                print("  Skipping...")
                break
            elif legislator in ['UNKNOWN', 'STAFF', 'WITNESS', 'PUBLIC', 'OTHER']:
                labels[speaker] = legislator
                print(f"  ✓ {speaker} → {legislator}")
                break
            else:
                # Confirm selection
                profile = pm.get_profile(legislator)
                if profile:
                    existing = profile['stats']['total_samples']
                    print(f"  Selected: {legislator}")
                    print(f"  ({existing} existing samples in profile)")
                    confirm = input("  Confirm? (y/n) [y]: ").strip().lower()
                    if confirm in ['', 'y', 'yes']:
                        labels[speaker] = legislator
                        print(f"  ✓ {speaker} → {legislator}")
                        break
                    else:
                        print("  Cancelled. Try again.")
                else:
                    print(f"  ⚠️  No profile found for {legislator}")
                    break
    
    return labels


def apply_labels_to_profiles(
    labels: Dict[str, str],
    diarization_file: str,
    meeting_id: str,
    committee: str,
    clips_dir: str
) -> Dict[str, bool]:
    """Apply labels to legislator profiles.
    
    Args:
        labels: Dict mapping speaker_id -> legislator_name
        diarization_file: Path to diarization JSON
        meeting_id: Meeting identifier
        committee: Committee code
        clips_dir: Directory containing speaker clips
        
    Returns:
        Dict mapping legislator_name -> success
    """
    pm = ProfileManager()
    speaker_stats = load_diarization_stats(diarization_file)
    meeting_date = parse_meeting_date(meeting_id)
    
    results = {}
    
    for speaker_id, legislator in labels.items():
        # Skip non-legislator labels
        if legislator in ['UNKNOWN', 'STAFF', 'WITNESS', 'PUBLIC', 'OTHER']:
            results[legislator] = True
            continue
        
        stats = speaker_stats.get(speaker_id, {})
        clip_path = f"{clips_dir}/{speaker_id}.wav"
        
        success = pm.add_voice_sample(
            legislator=legislator,
            meeting_id=meeting_id,
            speaker_id=speaker_id,
            clip_path=clip_path,
            segments=stats.get('segments', 0),
            total_time=stats.get('total_time', 0.0),
            meeting_date=meeting_date,
            committee=committee
        )
        
        results[legislator] = success
        
        if success:
            print(f"✓ Added sample for {legislator} ({stats.get('segments', 0)} segments, {stats.get('total_time', 0.0):.1f}s)")
        else:
            print(f"⚠️  Failed to add sample for {legislator}")
    
    return results


def save_labels_to_file(labels: Dict[str, str], meeting_id: str) -> str:
    """Save labels to a JSON file for reference.
    
    Returns:
        Path to saved file
    """
    output_dir = Path(__file__).parent / "database"
    output_file = output_dir / f"{meeting_id}_labels.json"
    
    output_data = {
        "meeting_id": meeting_id,
        "labeled_at": datetime.now().isoformat(),
        "labels": labels
    }
    
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    return str(output_file)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    # Batch mode
    if sys.argv[1] == '--batch':
        if len(sys.argv) < 3:
            print("Usage: python label_meeting.py --batch <labels.json>")
            sys.exit(1)
        
        with open(sys.argv[2], 'r') as f:
            batch_data = json.load(f)
        
        labels = batch_data['labels']
        meeting_id = batch_data['meeting_id']
        committee = batch_data.get('committee', 'UNKNOWN')
        diarization_file = batch_data.get('diarization_file', f"temp/{meeting_id}_diarization.json")
        clips_dir = batch_data.get('clips_dir', f"speaker_clips/{meeting_id}")
        
        results = apply_labels_to_profiles(labels, diarization_file, meeting_id, committee, clips_dir)
        
        success_count = sum(1 for v in results.values() if v)
        print(f"\n✅ Applied {success_count}/{len(results)} labels to profiles")
        sys.exit(0)
    
    # Interactive mode
    if len(sys.argv) < 4:
        print("Usage: python label_meeting.py <diarization.json> <meeting_id> <committee>")
        print("       python label_meeting.py --batch <labels.json>")
        sys.exit(1)
    
    diarization_file = sys.argv[1]
    meeting_id = sys.argv[2]
    committee = sys.argv[3].upper()
    
    # Default clips directory
    clips_dir = f"speaker_clips/{meeting_id}"
    if len(sys.argv) > 4:
        clips_dir = sys.argv[4]
    
    # Check diarization file exists
    if not Path(diarization_file).exists():
        print(f"Error: Diarization file not found: {diarization_file}")
        sys.exit(1)
    
    # Run interactive session
    labels = interactive_label_session(diarization_file, meeting_id, committee, clips_dir)
    
    if not labels:
        print("No labels collected. Exiting.")
        sys.exit(0)
    
    # Save labels to file
    label_file = save_labels_to_file(labels, meeting_id)
    print(f"\n💾 Labels saved to: {label_file}")
    
    # Apply to profiles
    print("\nApplying labels to profiles...")
    results = apply_labels_to_profiles(labels, diarization_file, meeting_id, committee, clips_dir)
    
    # Summary
    legislators = [k for k in labels.values() if k not in ['UNKNOWN', 'STAFF', 'WITNESS', 'PUBLIC', 'OTHER']]
    print(f"\n" + "="*50)
    print("SUMMARY")
    print("="*50)
    print(f"Meeting: {meeting_id}")
    print(f"Total speakers labeled: {len(labels)}")
    print(f"Legislators identified: {len(legislators)}")
    print(f"Non-legislators: {len(labels) - len(legislators)}")
    
    # Show updated enrollment status
    pm = ProfileManager()
    status = pm.get_enrollment_status()
    print(f"\n📊 Overall Enrollment Status:")
    print(f"   Enrolled: {status['enrolled']}/{status['total_legislators']}")
    print(f"   Weak profiles (< 3 samples): {status['weak_profiles']}")


if __name__ == '__main__':
    main()
