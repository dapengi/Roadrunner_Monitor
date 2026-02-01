#!/usr/bin/env python3
"""
Voice Enrollment Batch Orchestrator for New Mexico Legislature.

Orchestrates the full enrollment workflow for processing multiple meetings:
1. Discover audio files
2. Run diarization on each
3. Extract speaker clips
4. Track progress and coverage

Usage:
  python enroll_batch.py status           - Show current status
  python enroll_batch.py list             - List audio files and their status
  python enroll_batch.py process <file>   - Process a single audio file
  python enroll_batch.py process-all      - Process all unprocessed audio files
  python enroll_batch.py coverage         - Show legislator enrollment coverage

Example:
  python enroll_batch.py process audio/hjc_012325.mp3
"""

import json
import sys
import os
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import re

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from database.profile_manager import ProfileManager


# Paths
BASE_DIR = Path("/home/josh/roadrunner_granite")
AUDIO_DIR = BASE_DIR / "voice_enrollment" / "audio"
TEMP_DIR = BASE_DIR / "voice_enrollment" / "temp"
CLIPS_DIR = BASE_DIR / "voice_enrollment" / "speaker_clips"
DATABASE_DIR = BASE_DIR / "voice_enrollment" / "database"
PYTHON_BIN = BASE_DIR / "venv_pyannote" / "bin" / "python"
PROGRESS_FILE = DATABASE_DIR / "enrollment_progress.json"


def load_progress() -> Dict:
    """Load enrollment progress tracking data."""
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    return {
        "meetings": {},
        "last_updated": None
    }


def save_progress(progress: Dict) -> None:
    """Save enrollment progress."""
    progress["last_updated"] = datetime.now().isoformat()
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, indent=2)


def parse_audio_filename(filename: str) -> Optional[Dict]:
    """Parse audio filename to extract meeting info.
    
    Expected formats:
      - hjc_012325.mp3 -> committee=HJC, date=2025-01-23
      - House_Judiciary_012325.mp3 -> committee=HJC, date=2025-01-23
    
    Returns:
        Dict with meeting_id, committee, date or None if can't parse
    """
    name = Path(filename).stem
    
    # Try to match: prefix_MMDDYY
    match = re.search(r'(\d{6})$', name)
    if not match:
        return None
    
    date_str = match.group(1)
    month = date_str[0:2]
    day = date_str[2:4]
    year = "20" + date_str[4:6]
    
    # Extract committee from prefix
    prefix = name[:name.rfind('_')].lower()
    
    # Common mappings
    committee_map = {
        'hjc': 'HJC',
        'house_judiciary': 'HJC',
        'hafc': 'HAFC',
        'house_appropriations': 'HAFC',
        'hced': 'HCED',
        'hcpa': 'HCPA',
        'hed': 'HED',
        'heea': 'HEEA',
        'heeb': 'HEEB',
        'henr': 'HENR',
        'hgeia': 'HGEIA',
        'hhhs': 'HHHS',
        'hlvma': 'HLVMA',
        'hps': 'HPS',
        'hrdlc': 'HRDLC',
        'htpwci': 'HTPWCI',
        'htr': 'HTR',
        'hxrc': 'HXRC',
        'haaw': 'HAAW',
        'sfc': 'SFC',
        'sjc': 'SJC',
        'scc': 'SCC',
        'scon': 'SCON',
        'sed': 'SED',
        'shpa': 'SHPA',
        'sirca': 'SIRCA',
        'srules': 'SRULES',
        'stbt': 'STBT',
        'lfc': 'LFC',
        'lesc': 'LESC',
    }
    
    committee = committee_map.get(prefix, prefix.upper())
    
    return {
        'meeting_id': name.lower(),
        'committee': committee,
        'date': f"{year}-{month}-{day}",
        'filename': filename
    }


def discover_audio_files() -> List[Dict]:
    """Discover audio files in the audio directory."""
    audio_extensions = {'.mp3', '.wav', '.m4a', '.flac', '.ogg'}
    files = []
    
    for f in AUDIO_DIR.iterdir():
        if f.suffix.lower() in audio_extensions:
            info = parse_audio_filename(f.name)
            if info:
                info['path'] = str(f)
                info['size_mb'] = f.stat().st_size / (1024 * 1024)
                files.append(info)
    
    return sorted(files, key=lambda x: x['meeting_id'])


def get_meeting_status(meeting_id: str, progress: Dict) -> str:
    """Get processing status for a meeting."""
    if meeting_id not in progress.get('meetings', {}):
        return 'pending'
    
    meeting = progress['meetings'][meeting_id]
    
    if meeting.get('labeled', False):
        return 'labeled'
    elif meeting.get('clips_extracted', False):
        return 'clips_ready'
    elif meeting.get('diarized', False):
        return 'diarized'
    else:
        return 'pending'


def run_diarization(audio_path: str, meeting_id: str) -> Tuple[bool, str]:
    """Run diarization on an audio file.
    
    Returns:
        Tuple of (success, output_file_or_error)
    """
    output_file = TEMP_DIR / f"{meeting_id}_diarization.json"
    
    # Check if already done
    if output_file.exists():
        print(f"  ℹ️  Diarization already exists: {output_file}")
        return True, str(output_file)
    
    print(f"  🔄 Running diarization (this may take 60-90 minutes)...")
    
    cmd = [
        str(PYTHON_BIN),
        str(BASE_DIR / "run_diarization_only.py"),
        audio_path,
        str(output_file)
    ]
    
    env = os.environ.copy()
    env['HF_TOKEN'] = os.environ.get('HF_TOKEN', '')
    
    try:
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        if result.returncode == 0:
            return True, str(output_file)
        else:
            return False, result.stderr
    except Exception as e:
        return False, str(e)


def extract_clips(diarization_file: str, audio_path: str, meeting_id: str) -> Tuple[bool, str]:
    """Extract speaker clips from diarization.
    
    Returns:
        Tuple of (success, clips_dir_or_error)
    """
    clips_dir = CLIPS_DIR / meeting_id
    
    # Check if already done
    if clips_dir.exists() and list(clips_dir.glob("SPEAKER_*.wav")):
        print(f"  ℹ️  Clips already exist: {clips_dir}")
        return True, str(clips_dir)
    
    print(f"  🔄 Extracting speaker clips...")
    
    cmd = [
        str(PYTHON_BIN),
        str(BASE_DIR / "voice_enrollment" / "extract_clips_from_json.py"),
        diarization_file,
        audio_path,
        str(clips_dir)
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return True, str(clips_dir)
        else:
            return False, result.stderr
    except Exception as e:
        return False, str(e)


def process_meeting(audio_info: Dict, progress: Dict) -> bool:
    """Process a single meeting through diarization and clip extraction.
    
    Returns:
        True if processing succeeded
    """
    meeting_id = audio_info['meeting_id']
    audio_path = audio_info['path']
    
    print(f"\n{'='*60}")
    print(f"Processing: {meeting_id}")
    print(f"Committee: {audio_info['committee']}")
    print(f"Date: {audio_info['date']}")
    print(f"File: {audio_info['filename']} ({audio_info['size_mb']:.1f} MB)")
    print(f"{'='*60}")
    
    # Initialize progress entry
    if meeting_id not in progress['meetings']:
        progress['meetings'][meeting_id] = {
            'committee': audio_info['committee'],
            'date': audio_info['date'],
            'audio_file': audio_info['filename'],
            'started': datetime.now().isoformat()
        }
    
    meeting = progress['meetings'][meeting_id]
    
    # Step 1: Diarization
    if not meeting.get('diarized', False):
        success, result = run_diarization(audio_path, meeting_id)
        if success:
            meeting['diarized'] = True
            meeting['diarization_file'] = result
            meeting['diarized_at'] = datetime.now().isoformat()
            save_progress(progress)
        else:
            print(f"  ❌ Diarization failed: {result}")
            return False
    
    diarization_file = meeting.get('diarization_file', str(TEMP_DIR / f"{meeting_id}_diarization.json"))
    
    # Step 2: Extract clips
    if not meeting.get('clips_extracted', False):
        success, result = extract_clips(diarization_file, audio_path, meeting_id)
        if success:
            meeting['clips_extracted'] = True
            meeting['clips_dir'] = result
            meeting['clips_at'] = datetime.now().isoformat()
            save_progress(progress)
        else:
            print(f"  ❌ Clip extraction failed: {result}")
            return False
    
    clips_dir = meeting.get('clips_dir', str(CLIPS_DIR / meeting_id))
    
    # Count speakers
    clip_files = list(Path(clips_dir).glob("SPEAKER_*.wav"))
    print(f"\n✅ Processing complete!")
    print(f"   Diarization: {diarization_file}")
    print(f"   Clips: {clips_dir} ({len(clip_files)} speakers)")
    
    print(f"""
📋 NEXT STEPS:
1. Download clips to local machine:
   scp -r josh@10.0.0.173:{clips_dir} ~/Roadrunner_Monitor_Granite/voice_enrollment/speaker_clips/

2. Download diarization JSON:
   scp josh@10.0.0.173:{diarization_file} ~/Roadrunner_Monitor_Granite/voice_enrollment/temp/

3. Run local labeling:
   cd ~/Roadrunner_Monitor_Granite/voice_enrollment
   python label_local.py temp/{meeting_id}_diarization.json {meeting_id} {audio_info['committee']}

4. Upload labels and apply:
   scp database/{meeting_id}_labels.json josh@10.0.0.173:/home/josh/roadrunner_granite/voice_enrollment/database/
   ssh josh@10.0.0.173 "cd /home/josh/roadrunner_granite && python voice_enrollment/label_meeting.py --batch voice_enrollment/database/{meeting_id}_labels.json"
""")
    
    return True


def show_status() -> None:
    """Show overall enrollment status."""
    pm = ProfileManager()
    progress = load_progress()
    
    # Enrollment status
    status = pm.get_enrollment_status()
    
    print("\n" + "="*60)
    print("VOICE ENROLLMENT STATUS")
    print("="*60)
    
    print(f"\n📊 Legislator Coverage:")
    print(f"   Total legislators: {status['total_legislators']}")
    print(f"   Enrolled (1+ sample): {status['enrolled']}")
    print(f"   Not enrolled: {status['not_enrolled']}")
    print(f"   Weak profiles (<3 samples): {status['weak_profiles']}")
    pct = status['enrolled'] / status['total_legislators'] * 100
    print(f"   Coverage: {pct:.1f}%")
    
    # Meeting status
    audio_files = discover_audio_files()
    meetings = progress.get('meetings', {})
    
    labeled = sum(1 for m in meetings.values() if m.get('labeled', False))
    clips_ready = sum(1 for m in meetings.values() if m.get('clips_extracted', False) and not m.get('labeled', False))
    diarized = sum(1 for m in meetings.values() if m.get('diarized', False) and not m.get('clips_extracted', False))
    pending = len(audio_files) - labeled - clips_ready - diarized
    
    print(f"\n🎬 Meeting Progress:")
    print(f"   Audio files found: {len(audio_files)}")
    print(f"   Labeled: {labeled}")
    print(f"   Clips ready (awaiting labels): {clips_ready}")
    print(f"   Diarized: {diarized}")
    print(f"   Pending: {pending}")


def list_files() -> None:
    """List all audio files and their status."""
    progress = load_progress()
    audio_files = discover_audio_files()
    
    print("\n" + "="*80)
    print("AUDIO FILES")
    print("="*80)
    print(f"{'Meeting ID':<25} {'Committee':<8} {'Date':<12} {'Size':>8} {'Status':<12}")
    print("-"*80)
    
    status_icons = {
        'pending': '⏳',
        'diarized': '🔄',
        'clips_ready': '📂',
        'labeled': '✅'
    }
    
    for info in audio_files:
        status = get_meeting_status(info['meeting_id'], progress)
        icon = status_icons.get(status, '❓')
        print(f"{info['meeting_id']:<25} {info['committee']:<8} {info['date']:<12} {info['size_mb']:>6.1f}MB {icon} {status:<12}")
    
    print("-"*80)
    print(f"Total: {len(audio_files)} files")


def show_coverage() -> None:
    """Show detailed legislator enrollment coverage."""
    pm = ProfileManager()
    
    legislators = pm.list_all_legislators()
    
    print("\n" + "="*70)
    print("LEGISLATOR ENROLLMENT COVERAGE")
    print("="*70)
    
    # Group by chamber
    house = [l for l in legislators if l['chamber'] == 'House']
    senate = [l for l in legislators if l['chamber'] == 'Senate']
    
    for chamber, members in [('House', house), ('Senate', senate)]:
        enrolled = sum(1 for m in members if m['enrolled'])
        print(f"\n{chamber}: {enrolled}/{len(members)} enrolled")
        print("-"*60)
        
        for leg in members:
            status = "✓" if leg['enrolled'] else " "
            samples = f"({leg['samples']} samples)" if leg['samples'] > 0 else ""
            party = leg['party'][0] if leg['party'] else '?'
            print(f"  [{status}] D{leg['district']:>2} ({party}) {leg['name']:<30} {samples}")
    
    # Not enrolled list
    not_enrolled = [l for l in legislators if not l['enrolled']]
    if not_enrolled:
        print(f"\n⚠️  Not enrolled ({len(not_enrolled)}):")
        for leg in not_enrolled[:20]:
            print(f"    - {leg['name']} ({leg['chamber']} D{leg['district']})")
        if len(not_enrolled) > 20:
            print(f"    ... and {len(not_enrolled) - 20} more")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == 'status':
        show_status()
    
    elif command == 'list':
        list_files()
    
    elif command == 'coverage':
        show_coverage()
    
    elif command == 'process':
        if len(sys.argv) < 3:
            print("Usage: python enroll_batch.py process <audio_file>")
            sys.exit(1)
        
        audio_path = sys.argv[2]
        if not Path(audio_path).exists():
            # Try prepending audio dir
            audio_path = str(AUDIO_DIR / audio_path)
        
        if not Path(audio_path).exists():
            print(f"Error: Audio file not found: {audio_path}")
            sys.exit(1)
        
        info = parse_audio_filename(Path(audio_path).name)
        if not info:
            print(f"Error: Could not parse filename: {audio_path}")
            sys.exit(1)
        
        info['path'] = audio_path
        info['size_mb'] = Path(audio_path).stat().st_size / (1024 * 1024)
        
        progress = load_progress()
        process_meeting(info, progress)
    
    elif command == 'process-all':
        audio_files = discover_audio_files()
        progress = load_progress()
        
        pending = [f for f in audio_files if get_meeting_status(f['meeting_id'], progress) == 'pending']
        
        if not pending:
            print("All audio files have been processed!")
            sys.exit(0)
        
        print(f"Found {len(pending)} pending audio files.")
        confirm = input("Process all? (y/n): ").strip().lower()
        
        if confirm != 'y':
            print("Cancelled.")
            sys.exit(0)
        
        for i, info in enumerate(pending, 1):
            print(f"\n[{i}/{len(pending)}]")
            process_meeting(info, progress)
    
    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == '__main__':
    main()
